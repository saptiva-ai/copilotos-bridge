"""
Document ingestion router - handles PDF/IMG upload and processing.

V1 Simplified: Uses filesystem temp storage + Redis cache
V2 (Future): Uncomment MinIO code for persistent storage
"""

import uuid
from pathlib import Path
from typing import Optional

import structlog
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import RedirectResponse

from ..core.auth import get_current_user
from ..core.redis_cache import get_redis_cache
from ..models.user import User
from ..models.document import Document, DocumentStatus
from ..schemas.document import IngestResponse, PageContentResponse, DocumentMetadata
from ..services.file_ingest import file_ingest_service

# V2 Future: MinIO persistent storage
# from ..services.minio_service import minio_service

logger = structlog.get_logger(__name__)

# V1: Redis TTL for document text cache (1 hour)
REDIS_DOCUMENT_TTL = 3600

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", deprecated=True, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    ocr: str = Form("auto"),
    dpi: int = Form(350),
    language: str = Form("spa"),
    current_user: User = Depends(get_current_user),
):
    """
    **DEPRECATED**: Use `/api/files/upload` instead.

    This endpoint redirects (307) to the unified files endpoint.
    Legacy params (ocr, dpi, language) are ignored.

    Redirect: POST /api/files/upload
    """
    # Redirect 307: Client re-sends POST with same body to new URL
    return RedirectResponse(
        url="/api/files/upload",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )


@router.post("/upload-legacy", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_legacy(
    request: Request,
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    ocr: str = Form("auto"),
    dpi: int = Form(350),
    language: str = Form("spa"),
    current_user: User = Depends(get_current_user),
):
    """
    **LEGACY FALLBACK**: Direct upload without redirect (for old clients).

    Prefer using `/api/files/upload` for new integrations.
    """
    trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex
    request.state.trace_id = trace_id
    idempotency_key = request.headers.get("Idempotency-Key")

    logger.info(
        "Document upload started",
        filename=file.filename,
        content_type=file.content_type,
        user_id=str(current_user.id),
        trace_id=trace_id,
    )

    # Validate file type
    allowed_types = ["application/pdf", "image/png", "image/jpeg", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: {allowed_types}",
        )

    try:
        ingest_response = await file_ingest_service.ingest_file(
            user_id=str(current_user.id),
            upload=file,
            trace_id=trace_id,
            conversation_id=conversation_id,
            idempotency_key=idempotency_key,
        )

        document = await Document.get(ingest_response.file_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Document not found after ingestion")

        return IngestResponse(
            doc_id=str(document.id),
            filename=document.filename,
            size_bytes=document.size_bytes,
            total_pages=document.total_pages,
            pages=[
                PageContentResponse(
                    page=p.page,
                    text_md=p.text_md[:200] + "..." if len(p.text_md) > 200 else p.text_md,
                    has_table=p.has_table,
                    table_csv_key=p.table_csv_key,
                )
                for p in document.pages
            ],
            status=document.status.value,
            ocr_applied=document.ocr_applied,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Document upload failed", error=str(exc), filename=file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document processing failed",
        ) from exc


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
