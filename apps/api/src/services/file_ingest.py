"""
File ingestion service for the unified files tool.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from typing import Optional

import structlog
from fastapi import HTTPException, UploadFile, status

from ..core.redis_cache import get_redis_cache
from ..core.telemetry import (
    increment_pdf_ingest_error,
    increment_tool_invocation,
    record_pdf_ingest_phase,
)
from ..models.document import Document, DocumentStatus
from ..schemas.files import FileError, FileEventPhase, FileEventPayload, FileIngestResponse, FileStatus
from .file_events import file_event_bus
from .idempotency import upload_idempotency_repository
from .storage import FileTooLargeError, storage
from .document_extraction import extract_text_from_file

logger = structlog.get_logger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB per file (V1 MVP limit)
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/heic",
    "image/heif",
    "image/gif",
}


class FileIngestService:
    async def ingest_file(
        self,
        user_id: str,
        upload: UploadFile,
        trace_id: str,
        conversation_id: Optional[str],
        idempotency_key: Optional[str],
    ) -> FileIngestResponse:
        if upload.content_type not in SUPPORTED_MIME_TYPES:
            increment_pdf_ingest_error("unsupported_mime")
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type: {upload.content_type}",
            )

        effective_key = idempotency_key
        if effective_key:
            effective_key = f"{effective_key}:{upload.filename or 'unnamed'}"
            cached = await upload_idempotency_repository.get(user_id, effective_key)
            if cached:
                cached_doc_id = getattr(cached, "doc_id", cached.file_id)
                logger.info(
                    "Idempotent file ingest hit",
                    user_id=user_id,
                    doc_id=cached_doc_id,
                    trace_id=trace_id,
                )
                return cached

        file_id = uuid.uuid4().hex
        await file_event_bus.publish(
            file_id,
            FileEventPayload(
                file_id=file_id,
                trace_id=trace_id,
                phase=FileEventPhase.UPLOAD,
                pct=0.0,
                status=FileStatus.RECEIVED,
            ),
        )

        increment_tool_invocation("files")

        # Persist upload to disk while computing hash
        sha256 = hashlib.sha256()
        bytes_written = 0
        saved_path = None
        upload_started = time.time()
        try:
            saved_path, safe_name, bytes_written = await storage.save_upload(file_id, upload, MAX_UPLOAD_BYTES)
            with saved_path.open("rb") as file_obj:
                while True:
                    chunk = file_obj.read(1024 * 1024)
                    if not chunk:
                        break
                    sha256.update(chunk)
        except FileTooLargeError as exc:
            await self._publish_failure(
                file_id,
                trace_id,
                FileError(code="UPLOAD_TOO_LARGE", detail=str(exc)),
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large: {exc.size_bytes} bytes. Max: {exc.max_bytes} bytes",
            ) from exc
        record_pdf_ingest_phase("upload", time.time() - upload_started)

        digest = sha256.hexdigest()

        if not effective_key:
            effective_key = f"hash:{digest}:{conversation_id or 'no-chat'}"

        document = Document(
            filename=upload.filename,
            content_type=upload.content_type,
            size_bytes=bytes_written,
            minio_key=str(saved_path),
            minio_bucket="temp",
            status=DocumentStatus.PROCESSING,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        await document.insert()

        extract_started = time.time()
        await file_event_bus.publish(
            file_id,
            FileEventPayload(
                file_id=file_id,
                trace_id=trace_id,
                phase=FileEventPhase.EXTRACT,
                pct=33.0,
                status=FileStatus.PROCESSING,
            ),
        )
        try:
            pages = await extract_text_from_file(saved_path, upload.content_type)
        except Exception as exc:
            await self._handle_failure(document, file_id, trace_id, "EXTRACTION_FAILED", str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Document processing failed",
            ) from exc
        record_pdf_ingest_phase("extract", time.time() - extract_started)

        cache_started = time.time()
        await self._cache_pages(file_id, pages)
        record_pdf_ingest_phase("cache", time.time() - cache_started)
        await file_event_bus.publish(
            file_id,
            FileEventPayload(
                file_id=file_id,
                trace_id=trace_id,
                phase=FileEventPhase.CACHE,
                pct=66.0,
                status=FileStatus.PROCESSING,
            ),
        )

        document.pages = pages
        document.total_pages = len(pages)
        document.status = DocumentStatus.READY
        await document.save()

        await file_event_bus.publish(
            file_id,
            FileEventPayload(
                file_id=file_id,
                trace_id=trace_id,
                phase=FileEventPhase.COMPLETE,
                pct=100.0,
                status=FileStatus.READY,
            ),
        )

        response = FileIngestResponse(
            file_id=str(document.id),
            doc_id=str(document.id),
            status=FileStatus.READY,
            mimetype=document.content_type,
            bytes=document.size_bytes,
            pages=document.total_pages,
            name=document.filename,
            filename=document.filename,
        )

        if effective_key:
            await upload_idempotency_repository.set(user_id, effective_key, response)

        return response

    async def _cache_pages(self, file_id: str, pages: list[PageContent]) -> None:
        redis_cache = await get_redis_cache()
        redis_client = redis_cache.client
        full_text = "\n\n---PAGE BREAK---\n\n".join([p.text_md for p in pages])
        await redis_client.setex(
            f"doc:text:{file_id}",
            3600,
            full_text,
        )

    async def _handle_failure(
        self,
        document: Document,
        file_id: str,
        trace_id: str,
        code: str,
        detail: Optional[str],
    ) -> None:
        increment_pdf_ingest_error(code.lower())
        await document.delete()
        storage.delete_document(file_id)
        await self._publish_failure(file_id, trace_id, FileError(code=code, detail=detail))

    async def _publish_failure(self, file_id: str, trace_id: str, error: FileError) -> None:
        await file_event_bus.publish(
            file_id,
            FileEventPayload(
                file_id=file_id,
                trace_id=trace_id,
                phase=FileEventPhase.COMPLETE,
                pct=100.0,
                status=FileStatus.FAILED,
                error=error,
            ),
        )

file_ingest_service = FileIngestService()
