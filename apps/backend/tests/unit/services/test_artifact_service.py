"""
Unit tests for artifact_service module.

Tests:
- ArtifactService class
- get_artifact_by_id method
- get_artifacts_by_user method
- delete_artifact method
- get_artifact_service singleton
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.artifact_service import ArtifactService, get_artifact_service

pytestmark = [pytest.mark.unit]


class TestGetArtifactById:
    """Test get_artifact_by_id method."""

    @pytest.mark.asyncio
    async def test_returns_artifact_when_found(self):
        """Test returns artifact when found."""
        service = ArtifactService()
        mock_artifact = MagicMock()
        mock_artifact.type = "document"

        with patch("src.services.artifact_service.Artifact") as mock_artifact_class:
            mock_artifact_class.get = AsyncMock(return_value=mock_artifact)

            result = await service.get_artifact_by_id("artifact_123")

            assert result is mock_artifact

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        """Test returns None when artifact not found."""
        service = ArtifactService()

        with patch("src.services.artifact_service.Artifact") as mock_artifact_class:
            mock_artifact_class.get = AsyncMock(return_value=None)

            result = await service.get_artifact_by_id("artifact_123")

            assert result is None

    @pytest.mark.asyncio
    async def test_logs_warning_when_not_found(self):
        """Test logs warning when artifact not found."""
        service = ArtifactService()

        with patch(
            "src.services.artifact_service.Artifact"
        ) as mock_artifact_class, patch(
            "src.services.artifact_service.logger"
        ) as mock_logger:
            mock_artifact_class.get = AsyncMock(return_value=None)

            await service.get_artifact_by_id("artifact_123")

            mock_logger.warning.assert_called_once()


class TestGetArtifactsByUser:
    """Test get_artifacts_by_user method."""

    @pytest.mark.asyncio
    async def test_returns_all_user_artifacts(self):
        """Test returns all artifacts for user."""
        service = ArtifactService()
        mock_artifacts = [MagicMock(), MagicMock()]

        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.limit = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=mock_artifacts)

        with patch("src.services.artifact_service.Artifact") as mock_artifact:
            mock_artifact.find = MagicMock(return_value=mock_query)

            result = await service.get_artifacts_by_user("user_123")

            assert result == mock_artifacts

    @pytest.mark.asyncio
    async def test_default_limit_is_20(self):
        """Test default limit is 20."""
        service = ArtifactService()

        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.limit = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=[])

        with patch("src.services.artifact_service.Artifact") as mock_artifact:
            mock_artifact.find = MagicMock(return_value=mock_query)

            await service.get_artifacts_by_user("user_123")

            mock_query.limit.assert_called_once_with(20)


class TestDeleteArtifact:
    """Test delete_artifact method."""

    @pytest.mark.asyncio
    async def test_deletes_artifact_successfully(self):
        """Test deletes artifact successfully."""
        service = ArtifactService()

        mock_artifact = MagicMock()
        mock_artifact.user_id = "user_123"
        mock_artifact.type = "document"
        mock_artifact.delete = AsyncMock()

        with patch("src.services.artifact_service.Artifact") as mock_artifact_class:
            mock_artifact_class.get = AsyncMock(return_value=mock_artifact)

            result = await service.delete_artifact("artifact_123", "user_123")

            assert result is True
            mock_artifact.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_artifact_not_found(self):
        """Test returns False when artifact not found."""
        service = ArtifactService()

        with patch("src.services.artifact_service.Artifact") as mock_artifact_class:
            mock_artifact_class.get = AsyncMock(return_value=None)

            result = await service.delete_artifact("artifact_123", "user_123")

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_unauthorized(self):
        """Test returns False when user doesn't own artifact."""
        service = ArtifactService()

        mock_artifact = MagicMock()
        mock_artifact.user_id = "other_user"

        with patch("src.services.artifact_service.Artifact") as mock_artifact_class:
            mock_artifact_class.get = AsyncMock(return_value=mock_artifact)

            result = await service.delete_artifact("artifact_123", "user_123")

            assert result is False

    @pytest.mark.asyncio
    async def test_logs_unauthorized_delete_attempt(self):
        """Test logs unauthorized delete attempt."""
        service = ArtifactService()

        mock_artifact = MagicMock()
        mock_artifact.user_id = "other_user"

        with patch(
            "src.services.artifact_service.Artifact"
        ) as mock_artifact_class, patch(
            "src.services.artifact_service.logger"
        ) as mock_logger:
            mock_artifact_class.get = AsyncMock(return_value=mock_artifact)

            await service.delete_artifact("artifact_123", "user_123")

            mock_logger.warning.assert_called()


class TestGetArtifactService:
    """Test get_artifact_service singleton."""

    def test_returns_artifact_service(self):
        """Test returns ArtifactService instance."""
        import src.services.artifact_service as module

        # Reset singleton
        module._artifact_service_instance = None

        service = get_artifact_service()
        assert isinstance(service, ArtifactService)

    def test_returns_same_instance(self):
        """Test returns same singleton instance."""
        import src.services.artifact_service as module

        # Reset singleton
        module._artifact_service_instance = None

        service1 = get_artifact_service()
        service2 = get_artifact_service()
        assert service1 is service2
