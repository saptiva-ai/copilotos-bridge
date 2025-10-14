"""
Server-driven feature flag endpoints for tool visibility.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends

from ..core.config import get_settings, Settings

router = APIRouter(prefix="/features", tags=["features"])


@router.get("/tools")
async def get_tool_visibility(settings: Settings = Depends(get_settings)) -> dict:
    """Expose tool visibility flags so the frontend can toggle UI without redeploy."""
    updated_at = settings.tool_flags_updated_at.isoformat() if settings.tool_flags_updated_at else None

    # Primary flag for the unified files tool. Fallback to legacy flags to ease migration.
    files_enabled = (
        settings.tool_files_enabled
        or settings.tool_add_files_enabled
        or settings.tool_document_review_enabled
    )

    tools: List[dict] = [
        {
            "key": "files",
            "enabled": files_enabled,
            "updated_at": updated_at,
        },
        # Legacy entries kept for backward compatibility with older clients.
        {
            "key": "add-files",
            "enabled": settings.tool_add_files_enabled and not settings.tool_files_enabled,
            "updated_at": updated_at,
        },
        {
            "key": "document-review",
            "enabled": settings.tool_document_review_enabled and not settings.tool_files_enabled,
            "updated_at": updated_at,
        },
    ]

    return {
        "rev": int(datetime.utcnow().timestamp()),
        "tools": tools,
    }
