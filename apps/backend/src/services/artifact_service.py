"""
Artifact Service for managing user-generated artifacts.

This service handles CRUD operations for artifacts including:
- Bank charts (visualizations)
- Markdown documents
- Code snippets
- Graph diagrams
"""

from typing import List, Optional

from structlog import get_logger

from src.models.artifact import Artifact, ArtifactType

logger = get_logger(__name__)


class ArtifactService:
    """Service for managing artifacts across the application."""

    async def get_artifact_by_id(
        self,
        artifact_id: str,
    ) -> Optional[Artifact]:
        """
        Get a single artifact by ID.

        Args:
            artifact_id: Unique artifact ID

        Returns:
            Artifact instance or None if not found

        Example:
            >>> service = ArtifactService()
            >>> artifact = await service.get_artifact_by_id("artifact_abc123")
            >>> if artifact:
            ...     print(artifact.type)
        """
        artifact = await Artifact.get(artifact_id)

        if artifact:
            logger.debug(
                "fetched_artifact_by_id",
                artifact_id=artifact_id,
                type=artifact.type,
            )
        else:
            logger.warning(
                "artifact_not_found",
                artifact_id=artifact_id,
            )

        return artifact

    async def get_artifacts_by_user(
        self,
        user_id: str,
        artifact_type: Optional[ArtifactType] = None,
        limit: int = 20,
    ) -> List[Artifact]:
        """
        Get all artifacts for a user, optionally filtered by type.

        Args:
            user_id: User ID
            artifact_type: Optional type filter (BANK_CHART, MARKDOWN, etc.)
            limit: Maximum number of artifacts to return

        Returns:
            List of Artifact instances, newest first

        Example:
            >>> service = ArtifactService()
            >>> charts = await service.get_artifacts_by_user(
            ...     "user123",
            ...     artifact_type=ArtifactType.BANK_CHART
            ... )
        """
        query = {"user_id": user_id}
        if artifact_type:
            query["type"] = artifact_type

        artifacts = (
            await Artifact.find(query).sort("-created_at").limit(limit).to_list()
        )

        logger.debug(
            "fetched_artifacts_by_user",
            user_id=user_id,
            artifact_type=artifact_type,
            count=len(artifacts),
        )

        return artifacts

    async def delete_artifact(
        self,
        artifact_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete an artifact (with ownership check).

        Args:
            artifact_id: Artifact ID to delete
            user_id: User ID (for ownership verification)

        Returns:
            True if deleted, False if not found or unauthorized

        Example:
            >>> service = ArtifactService()
            >>> deleted = await service.delete_artifact("artifact_abc", "user123")
            >>> print(deleted)  # True
        """
        artifact = await Artifact.get(artifact_id)

        if not artifact:
            logger.warning("artifact_not_found_for_delete", artifact_id=artifact_id)
            return False

        if artifact.user_id != user_id:
            logger.warning(
                "unauthorized_artifact_delete",
                artifact_id=artifact_id,
                user_id=user_id,
                owner_id=artifact.user_id,
            )
            return False

        await artifact.delete()

        logger.info(
            "artifact_deleted",
            artifact_id=artifact_id,
            user_id=user_id,
            type=artifact.type,
        )

        return True



# Singleton instance for dependency injection
_artifact_service_instance: Optional[ArtifactService] = None


def get_artifact_service() -> ArtifactService:
    """
    Get singleton ArtifactService instance.

    Used as FastAPI dependency:
        @router.post("/artifacts")
        async def create_artifact(
            service: ArtifactService = Depends(get_artifact_service)
        ):
            ...

    Returns:
        ArtifactService singleton
    """
    global _artifact_service_instance
    if _artifact_service_instance is None:
        _artifact_service_instance = ArtifactService()
    return _artifact_service_instance
