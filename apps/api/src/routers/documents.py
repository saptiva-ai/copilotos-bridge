"""
Document ingestion router - handles PDF/IMG upload and processing.
"""

import io
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse
import structlog

from ..core.auth import get_current_user
from ..models.user import User
from ..models.document import Document, DocumentStatus, PageContent
from ..schemas.document import IngestResponse, IngestOptions, PageContentResponse, DocumentMetadata
from ..services.minio_service import minio_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


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
        # Generate unique key
        doc_id = uuid.uuid4().hex
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
        minio_key = f"docs/{str(current_user.id)}/{doc_id}.{file_ext}"

        # Upload to MinIO
        await minio_service.upload_file(
            bucket="documents",
            object_name=minio_key,
            data=io.BytesIO(file_bytes),
            length=file_size,
            content_type=file.content_type or "application/octet-stream",
        )

        # Create document record
        doc = Document(
            filename=file.filename,
            content_type=file.content_type,
            size_bytes=file_size,
            minio_key=minio_key,
            minio_bucket="documents",
            status=DocumentStatus.PROCESSING,
            user_id=str(current_user.id),
            conversation_id=conversation_id,
        )

        await doc.insert()

        logger.info(
            "Document record created",
            doc_id=str(doc.id),
            minio_key=minio_key,
        )

        # TODO: Process document asynchronously
        # For now, return minimal response
        # In production: trigger background task for text extraction

        # Mock extraction for demo
        pages = await _mock_extract_pages(file_bytes, file.content_type)

        doc.pages = pages
        doc.total_pages = len(pages)
        doc.status = DocumentStatus.READY
        await doc.save()

        # Build response
        response = IngestResponse(
            doc_id=str(doc.id),
            filename=doc.filename,
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

    # Generate presigned URL
    minio_url = None
    if doc.status == DocumentStatus.READY:
        minio_url = minio_service.get_presigned_url(doc.minio_bucket, doc.minio_key)

    return DocumentMetadata(
        doc_id=str(doc.id),
        filename=doc.filename,
        content_type=doc.content_type,
        size_bytes=doc.size_bytes,
        total_pages=doc.total_pages,
        status=doc.status.value,
        created_at=doc.created_at.isoformat(),
        minio_url=minio_url,
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

    # Delete from MinIO
    try:
        await minio_service.delete_file(doc.minio_bucket, doc.minio_key)
    except Exception as e:
        logger.error("Failed to delete from MinIO", error=str(e), doc_id=doc_id)

    # Delete document record
    await doc.delete()

    logger.info("Document deleted", doc_id=doc_id)


async def _mock_extract_pages(file_bytes: bytes, content_type: str) -> list[PageContent]:
    """
    Mock text extraction for demo.
    In production: use PyMuPDF, pdfplumber, or similar.
    """
    # For demo, return sample pages
    pages = [
        PageContent(
            page=1,
            text_md="# Documento de Prueba\n\nEste es un documento de ejemplo para la revisión.",
            has_table=False,
        ),
        PageContent(
            page=2,
            text_md="## Sección 2\n\nContenido adicional con algunos errores gramaticales intensionales.",
            has_table=False,
        ),
    ]

    return pages
