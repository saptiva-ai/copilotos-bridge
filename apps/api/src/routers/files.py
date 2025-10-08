"""
File serving router - securely serve document artifacts.

Serves:
- Original documents: /files/docs/{doc_id}/raw.{ext}
- Derived content: /files/docs/{doc_id}/derived/page-{n}.md
- Reports: /files/reports/{doc_id}/report.json
- Annotated PDFs: /files/reports/{doc_id}/annotated.pdf
"""

import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
import structlog

from ..core.auth import get_current_user
from ..models.user import User
from ..models.document import Document
from ..models.review_job import ReviewJob, ReviewStatus

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

# Base storage directory (configurable via env)
STORAGE_BASE = Path(os.getenv("LOCAL_STORAGE_DIR", "/tmp/reviewer"))


def validate_path_security(requested_path: Path, base_path: Path) -> bool:
    """
    Validate that requested path is within base directory (prevent traversal).

    Args:
        requested_path: The resolved path being requested
        base_path: The allowed base directory

    Returns:
        True if path is safe, False otherwise
    """
    try:
        # Resolve both paths to absolute
        requested_abs = requested_path.resolve()
        base_abs = base_path.resolve()

        # Check if requested path is within base path
        return requested_abs.is_relative_to(base_abs)
    except (ValueError, RuntimeError):
        return False


@router.get("/docs/{doc_id}/raw.{ext}")
async def get_document_raw(
    doc_id: str,
    ext: str,
    current_user: User = Depends(get_current_user),
):
    """
    Serve original uploaded document.

    Args:
        doc_id: Document ID
        ext: File extension (pdf, png, jpg)
        current_user: Authenticated user

    Returns:
        File response with original document
    """
    logger.info("Serving raw document", doc_id=doc_id, ext=ext, user_id=str(current_user.id))

    # Validate ownership
    doc = await Document.get(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if doc.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document"
        )

    # Build path
    file_path = STORAGE_BASE / "docs" / doc_id / f"raw.{ext}"

    # Security validation
    if not validate_path_security(file_path, STORAGE_BASE):
        logger.error("Path traversal attempt detected", path=str(file_path), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid file path"
        )

    # Check file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path.name}"
        )

    # Determine media type
    media_types = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }
    media_type = media_types.get(ext.lower(), "application/octet-stream")

    logger.info("Serving file", path=str(file_path), size=file_path.stat().st_size)

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=doc.filename,
    )


@router.get("/docs/{doc_id}/derived/{filename}")
async def get_derived_file(
    doc_id: str,
    filename: str,
    current_user: User = Depends(get_current_user),
):
    """
    Serve derived content (Markdown pages, CSV tables).

    Args:
        doc_id: Document ID
        filename: Derived filename (e.g., page-1.md, page-3.csv)
        current_user: Authenticated user

    Returns:
        File response with derived content
    """
    logger.info("Serving derived file", doc_id=doc_id, filename=filename, user_id=str(current_user.id))

    # Validate ownership
    doc = await Document.get(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if doc.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document"
        )

    # Build path
    file_path = STORAGE_BASE / "docs" / doc_id / "derived" / filename

    # Security validation
    if not validate_path_security(file_path, STORAGE_BASE):
        logger.error("Path traversal attempt detected", path=str(file_path), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid file path"
        )

    # Check file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Derived file not found: {filename}"
        )

    # Determine media type
    if filename.endswith(".md"):
        media_type = "text/markdown"
    elif filename.endswith(".csv"):
        media_type = "text/csv"
    else:
        media_type = "text/plain"

    logger.info("Serving derived file", path=str(file_path), size=file_path.stat().st_size)

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )


@router.get("/reports/{doc_id}/report.json")
async def get_review_report_json(
    doc_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Serve review report as JSON file.

    Args:
        doc_id: Document ID
        current_user: Authenticated user

    Returns:
        JSON report file
    """
    logger.info("Serving report JSON", doc_id=doc_id, user_id=str(current_user.id))

    # Validate ownership via document
    doc = await Document.get(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if doc.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document"
        )

    # Build path
    file_path = STORAGE_BASE / "reports" / doc_id / "report.json"

    # Security validation
    if not validate_path_security(file_path, STORAGE_BASE):
        logger.error("Path traversal attempt detected", path=str(file_path), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid file path"
        )

    # Check file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found. Has the review completed?"
        )

    logger.info("Serving report", path=str(file_path), size=file_path.stat().st_size)

    return FileResponse(
        path=str(file_path),
        media_type="application/json",
        filename=f"report_{doc_id}.json",
    )


@router.get("/reports/{doc_id}/annotated.pdf")
async def get_annotated_pdf(
    doc_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Serve annotated PDF with review highlights (optional feature).

    Args:
        doc_id: Document ID
        current_user: Authenticated user

    Returns:
        Annotated PDF file
    """
    logger.info("Serving annotated PDF", doc_id=doc_id, user_id=str(current_user.id))

    # Validate ownership
    doc = await Document.get(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if doc.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document"
        )

    # Build path
    file_path = STORAGE_BASE / "reports" / doc_id / "annotated.pdf"

    # Security validation
    if not validate_path_security(file_path, STORAGE_BASE):
        logger.error("Path traversal attempt detected", path=str(file_path), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid file path"
        )

    # Check file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotated PDF not available. This feature is optional."
        )

    logger.info("Serving annotated PDF", path=str(file_path), size=file_path.stat().st_size)

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=f"{doc.filename}_annotated.pdf",
    )
