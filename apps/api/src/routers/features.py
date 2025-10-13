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
    tools: List[dict] = [
        {
            "key": "files",
            "enabled": settings.tool_files_enabled,
            "updated_at": settings.tool_flags_updated_at.isoformat() if settings.tool_flags_updated_at else None,
        },
        {
            "key": "add-files",
            "enabled": settings.tool_add_files_enabled,
            "updated_at": settings.tool_flags_updated_at.isoformat() if settings.tool_flags_updated_at else None,
        },
        {
            "key": "document-review",
            "enabled": settings.tool_document_review_enabled,
            "updated_at": settings.tool_flags_updated_at.isoformat() if settings.tool_flags_updated_at else None,
        },
    ]

    return {
        "rev": int(datetime.utcnow().timestamp()),
        "tools": tools,
    }
