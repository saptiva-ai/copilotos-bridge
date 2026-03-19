"""
Artifact model for user-generated canvases and research outputs.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from beanie import Document
from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    """Supported artifact content types."""

    MARKDOWN = "markdown"
    CODE = "code"
    GRAPH = "graph"


class ArtifactVersion(BaseModel):
    """Immutable snapshot of an artifact at a point in time."""

    version: int = Field(..., description="Sequential version number starting at 1")
    content: Union[str, Dict[str, Any]] = Field(
        ...,
        description="Snapshot of the artifact content for this version",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp for this version",
    )


class Artifact(Document):
    """Persisted artifact with version history."""

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    user_id: str = Field(..., description="Owner user ID")
    chat_session_id: Optional[str] = Field(
        None, description="Associated chat session ID"
    )
    title: str = Field(..., description="Artifact title")
    type: ArtifactType = Field(..., description="Artifact content type")
    content: Union[str, Dict[str, Any]] = Field(
        ..., description="Latest artifact content"
    )
    versions: List[ArtifactVersion] = Field(
        default_factory=list, description="Historical versions of the artifact"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(
        None, description="TTL timestamp for automatic cleanup"
    )

    class Settings:
        name = "artifacts"
        indexes = [
            "user_id",
            "chat_session_id",
            "created_at",
            [("user_id", 1), ("created_at", -1)],
            [("chat_session_id", 1), ("created_at", -1)],
            "expires_at",  # TTL index for auto-cleanup
        ]

    def add_version(self, content: Union[str, Dict[str, Any]]) -> ArtifactVersion:
        """Append a new version and refresh timestamps."""
        version_number = len(self.versions) + 1
        version = ArtifactVersion(version=version_number, content=content)
        self.versions.append(version)
        self.content = content
        self.updated_at = datetime.utcnow()
        return version

