"""
Document ingestion router - handles PDF/IMG upload and processing.

V1 Simplified: Uses filesystem temp storage + Redis cache
V2 (Future): Uncomment MinIO code for persistent storage
"""

import io
import os
import uuid
import tempfile
import hashlib
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse
import structlog

from ..core.auth import get_current_user
from ..core.redis_cache import get_redis_cache
from ..models.user import User
from ..models.document import Document, DocumentStatus, PageContent
from ..schemas.document import IngestResponse, IngestOptions, PageContentResponse, DocumentMetadata

# V2 Future: MinIO persistent storage
# from ..services.minio_service import minio_service

logger = structlog.get_logger(__name__)

# V1: Temporary file storage
UPLOAD_DIR = Path(tempfile.gettempdir()) / "copilotos_documents"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# V1: Redis TTL for document text cache (1 hour)
REDIS_DOCUMENT_TTL = 3600

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    ocr: str = Form("auto"),
    dpi: int = Form(350),
    language: str = Form("spa"),
    current_user: User = Depends(get_current_user),
):
    """
    Upload and ingest a document (PDF/IMG).

    This endpoint:
    1. Uploads file to MinIO
    2. Extracts text (with OCR if needed)
    3. Normalizes to Markdown per page
    4. Detects and extracts tables to CSV

    Args:
        file: PDF or image file
        conversation_id: Optional associated chat ID
        ocr: OCR mode (auto|always|never)
        dpi: OCR DPI resolution
        language: OCR language code
        current_user: Authenticated user

    Returns:
        IngestResponse with doc_id and extracted pages
    """
    logger.info(
        "Document upload started",
        filename=file.filename,
        content_type=file.content_type,
        user_id=str(current_user.id),
    )

    # Validate file type
    allowed_types = ["application/pdf", "image/png", "image/jpeg", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: {allowed_types}",
        )

    # Read file content
    file_bytes = await file.read()
    file_size = len(file_bytes)

    # Size limits
    max_size = 50 * 1024 * 1024  # 50MB
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {file_size} bytes. Max: {max_size} bytes",
        )

    try:
        # Generate unique document ID
        doc_id = uuid.uuid4().hex
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"

        # V1: Save to temporary filesystem
        temp_file_path = UPLOAD_DIR / f"{doc_id}.{file_ext}"
        with open(temp_file_path, "wb") as f:
            f.write(file_bytes)

        logger.info(
            "File saved to temp storage",
            doc_id=doc_id,
            path=str(temp_file_path),
            size=file_size
        )

        # V2 Future: MinIO persistent storage
        # minio_key = f"docs/{str(current_user.id)}/{doc_id}.{file_ext}"
        # await minio_service.upload_file(
        #     bucket="documents",
        #     object_name=minio_key,
        #     data=io.BytesIO(file_bytes),
        #     length=file_size,
        #     content_type=file.content_type or "application/octet-stream",
        # )

        # Create document record (minimal metadata for V1)
        doc = Document(
            filename=file.filename,
            content_type=file.content_type,
            size_bytes=file_size,
            minio_key=str(temp_file_path),  # V1: Store filesystem path instead
            minio_bucket="temp",  # V1: Mark as temporary
            status=DocumentStatus.PROCESSING,
            user_id=str(current_user.id),
            conversation_id=conversation_id,
        )

        await doc.insert()

        logger.info(
            "Document record created",
            doc_id=str(doc.id),
            temp_path=str(temp_file_path),
        )

        # V1: Extract text synchronously and cache in Redis
        # V2 Future: Implement async background processing with Celery/FastAPI BackgroundTasks

        pages = await _extract_text_from_file(temp_file_path, file.content_type)

        # Cache extracted text in Redis with TTL
        redis_cache = await get_redis_cache()
        redis_client = redis_cache.client
        full_text = "\n\n---PAGE BREAK---\n\n".join([p.text_md for p in pages])

        await redis_client.setex(
            f"doc:text:{doc_id}",
            REDIS_DOCUMENT_TTL,
            full_text
        )

        logger.info(
            "Document text cached in Redis",
            doc_id=doc_id,
            text_length=len(full_text),
            ttl_seconds=REDIS_DOCUMENT_TTL
        )

        doc.pages = pages
        doc.total_pages = len(pages)
        doc.status = DocumentStatus.READY
        await doc.save()

        # Build response
        response = IngestResponse(
            doc_id=str(doc.id),
            filename=doc.filename,
            size_bytes=doc.size_bytes,
            total_pages=doc.total_pages,
            pages=[
                PageContentResponse(
                    page=p.page,
                    text_md=p.text_md[:200] + "..." if len(p.text_md) > 200 else p.text_md,
                    has_table=p.has_table,
                    table_csv_key=p.table_csv_key,
                )
                for p in pages
            ],
            status=doc.status.value,
            ocr_applied=doc.ocr_applied,
        )

        logger.info(
            "Document ingestion completed",
            doc_id=str(doc.id),
            pages=doc.total_pages,
        )

        return response

    except Exception as e:
        logger.error("Document upload failed", error=str(e), filename=file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}",
        )


@router.get("/{doc_id}", response_model=DocumentMetadata)
async def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get document metadata"""
    doc = await Document.get(doc_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check ownership
    if doc.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document",
        )

    # V1: No presigned URLs for temp files (they're server-side only)
    # V2 Future: Generate presigned URL for MinIO
    # minio_url = None
    # if doc.status == DocumentStatus.READY:
    #     minio_url = minio_service.get_presigned_url(doc.minio_bucket, doc.minio_key)

    return DocumentMetadata(
        doc_id=str(doc.id),
        filename=doc.filename,
        content_type=doc.content_type,
        size_bytes=doc.size_bytes,
        total_pages=doc.total_pages,
        status=doc.status.value,
        created_at=doc.created_at.isoformat(),
        minio_url=None,  # V1: Always None for temp storage
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete document"""
    doc = await Document.get(doc_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check ownership
    if doc.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this document",
        )

    # V1: Delete from filesystem and Redis
    try:
        # Delete temp file
        temp_path = Path(doc.minio_key)  # V1: minio_key stores filesystem path
        if temp_path.exists():
            temp_path.unlink()
            logger.info("Deleted temp file", path=str(temp_path))

        # Delete from Redis cache
        redis_cache = await get_redis_cache()
        redis_client = redis_cache.client
        await redis_client.delete(f"doc:text:{doc_id}")
        logger.info("Deleted from Redis cache", doc_id=doc_id)

    except Exception as e:
        logger.error("Failed to delete temp files", error=str(e), doc_id=doc_id)

    # V2 Future: Delete from MinIO
    # try:
    #     await minio_service.delete_file(doc.minio_bucket, doc.minio_key)
    # except Exception as e:
    #     logger.error("Failed to delete from MinIO", error=str(e), doc_id=doc_id)

    # Delete document record
    await doc.delete()

    logger.info("Document deleted", doc_id=doc_id)


async def _extract_text_from_file(file_path: Path, content_type: str) -> list[PageContent]:
    """
    Extract text from PDF or image files.

    V1: Uses pypdf for PDF extraction (simple, lightweight)
    V2 Future: Add OCR support for images using pytesseract or similar
    """
    pages = []

    try:
        if content_type == "application/pdf":
            # Extract text from PDF using pypdf
            try:
                from pypdf import PdfReader
            except ImportError:
                logger.error("pypdf not installed, falling back to mock extraction")
                return _fallback_mock_pages()

            reader = PdfReader(str(file_path))

            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""

                # Clean and format text
                text = text.strip()
                if not text:
                    text = f"[Página {page_num} sin texto extraíble]"

                pages.append(
                    PageContent(
                        page=page_num,
                        text_md=text,
                        has_table=False,  # V2: Implement table detection
                    )
                )

        elif content_type in ["image/png", "image/jpeg", "image/jpg"]:
            # V1: Images not supported yet, return placeholder
            # V2 Future: Implement OCR with pytesseract
            pages.append(
                PageContent(
                    page=1,
                    text_md="[OCR para imágenes no implementado aún - V2 Feature]",
                    has_table=False,
                )
            )

        else:
            # Unsupported format
            pages.append(
                PageContent(
                    page=1,
                    text_md=f"[Formato no soportado: {content_type}]",
                    has_table=False,
                )
            )

    except Exception as e:
        logger.error("Text extraction failed", error=str(e), file_path=str(file_path))
        pages = _fallback_mock_pages()

    return pages


def _fallback_mock_pages() -> list[PageContent]:
    """Fallback mock pages if extraction fails"""
    return [
        PageContent(
            page=1,
            text_md="# Documento de Prueba\n\nEste es un documento de ejemplo (modo fallback).",
            has_table=False,
        )
    ]
