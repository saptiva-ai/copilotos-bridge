"""Utilities for extracting text/tables from uploaded documents."""

from __future__ import annotations

from pathlib import Path
from typing import List

import structlog

from ..models.document import PageContent

logger = structlog.get_logger(__name__)


async def extract_text_from_file(file_path: Path, content_type: str) -> List[PageContent]:
    """Extract text from PDF or image files."""
    pages: List[PageContent] = []

    try:
        if content_type == "application/pdf":
            try:
                from pypdf import PdfReader
            except ImportError:  # pragma: no cover - fallback
                logger.error("pypdf not installed, falling back to mock extraction")
                return _fallback_mock_pages()

            reader = PdfReader(str(file_path))

            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""

                text = text.strip()
                if not text:
                    text = f"[Página {page_num} sin texto extraíble]"

                pages.append(PageContent(page=page_num, text_md=text, has_table=False))

        elif content_type in ["image/png", "image/jpeg", "image/jpg", "image/heic", "image/heif", "image/gif"]:
            pages.append(
                PageContent(
                    page=1,
                    text_md="[OCR para imágenes no implementado aún - V2 Feature]",
                    has_table=False,
                )
            )
        else:
            pages.append(
                PageContent(
                    page=1,
                    text_md=f"[Formato no soportado: {content_type}]",
                    has_table=False,
                )
            )

    except Exception as exc:  # pragma: no cover - fallback path
        logger.error("Text extraction failed", error=str(exc), file_path=str(file_path))
        pages = _fallback_mock_pages()

    return pages


def _fallback_mock_pages() -> List[PageContent]:
    return [
        PageContent(
            page=1,
            text_md="# Documento de Prueba\n\nEste es un documento de ejemplo (modo fallback).",
            has_table=False,
        )
    ]
