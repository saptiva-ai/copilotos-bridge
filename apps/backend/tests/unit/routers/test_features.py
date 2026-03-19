"""
Unit tests for features router.

Tests:
- get_tool_visibility endpoint
- Tool flag combinations
- Backward compatibility with legacy flags
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.routers.features import get_tool_visibility

pytestmark = [pytest.mark.unit]


class TestGetToolVisibility:
    """Test get_tool_visibility endpoint."""

    @pytest.mark.asyncio
    async def test_returns_tools_list(self):
        """Test returns a list of tools."""
        mock_settings = _create_mock_settings()

        result = await get_tool_visibility(settings=mock_settings)

        assert "tools" in result
        assert isinstance(result["tools"], list)
        assert len(result["tools"]) > 0

    @pytest.mark.asyncio
    async def test_returns_rev_timestamp(self):
        """Test returns rev timestamp."""
        mock_settings = _create_mock_settings()

        result = await get_tool_visibility(settings=mock_settings)

        assert "rev" in result
        assert isinstance(result["rev"], int)

    @pytest.mark.asyncio
    async def test_files_tool_enabled(self):
        """Test files tool is enabled when tool_files_enabled is True."""
        mock_settings = _create_mock_settings(tool_files_enabled=True)

        result = await get_tool_visibility(settings=mock_settings)
        files_tool = _find_tool(result["tools"], "files")

        assert files_tool is not None
        assert files_tool["enabled"] is True

    @pytest.mark.asyncio
    async def test_files_tool_disabled(self):
        """Test files tool is disabled when all file flags are False."""
        mock_settings = _create_mock_settings(
            tool_files_enabled=False,
            tool_add_files_enabled=False,
            tool_document_review_enabled=False,
        )

        result = await get_tool_visibility(settings=mock_settings)
        files_tool = _find_tool(result["tools"], "files")

        assert files_tool is not None
        assert files_tool["enabled"] is False

    @pytest.mark.asyncio
    async def test_files_fallback_to_add_files(self):
        """Test files tool uses add_files fallback."""
        mock_settings = _create_mock_settings(
            tool_files_enabled=False,
            tool_add_files_enabled=True,
            tool_document_review_enabled=False,
        )

        result = await get_tool_visibility(settings=mock_settings)
        files_tool = _find_tool(result["tools"], "files")

        assert files_tool["enabled"] is True

    @pytest.mark.asyncio
    async def test_files_fallback_to_document_review(self):
        """Test files tool uses document_review fallback."""
        mock_settings = _create_mock_settings(
            tool_files_enabled=False,
            tool_add_files_enabled=False,
            tool_document_review_enabled=True,
        )

        result = await get_tool_visibility(settings=mock_settings)
        files_tool = _find_tool(result["tools"], "files")

        assert files_tool["enabled"] is True

    @pytest.mark.asyncio
    async def test_legacy_add_files_disabled_when_files_enabled(self):
        """Test legacy add-files is disabled when files tool is enabled."""
        mock_settings = _create_mock_settings(
            tool_files_enabled=True,
            tool_add_files_enabled=True,
        )

        result = await get_tool_visibility(settings=mock_settings)
        add_files_tool = _find_tool(result["tools"], "add-files")

        assert add_files_tool is not None
        assert add_files_tool["enabled"] is False

    @pytest.mark.asyncio
    async def test_legacy_add_files_enabled_when_files_disabled(self):
        """Test legacy add-files is enabled when files tool is disabled."""
        mock_settings = _create_mock_settings(
            tool_files_enabled=False,
            tool_add_files_enabled=True,
        )

        result = await get_tool_visibility(settings=mock_settings)
        add_files_tool = _find_tool(result["tools"], "add-files")

        assert add_files_tool["enabled"] is True

    @pytest.mark.asyncio
    async def test_legacy_document_review_disabled_when_files_enabled(self):
        """Test legacy document-review is disabled when files tool is enabled."""
        mock_settings = _create_mock_settings(
            tool_files_enabled=True,
            tool_document_review_enabled=True,
        )

        result = await get_tool_visibility(settings=mock_settings)
        doc_review_tool = _find_tool(result["tools"], "document-review")

        assert doc_review_tool is not None
        assert doc_review_tool["enabled"] is False

    @pytest.mark.asyncio
    async def test_updated_at_included(self):
        """Test updated_at is included in tool entries."""
        now = datetime.utcnow()
        mock_settings = _create_mock_settings(tool_flags_updated_at=now)

        result = await get_tool_visibility(settings=mock_settings)
        files_tool = _find_tool(result["tools"], "files")

        assert "updated_at" in files_tool
        assert files_tool["updated_at"] == now.isoformat()

    @pytest.mark.asyncio
    async def test_updated_at_none(self):
        """Test updated_at is None when not set."""
        mock_settings = _create_mock_settings(tool_flags_updated_at=None)

        result = await get_tool_visibility(settings=mock_settings)
        files_tool = _find_tool(result["tools"], "files")

        assert files_tool["updated_at"] is None

    @pytest.mark.asyncio
    async def test_all_expected_tools_present(self):
        """Test all expected tools are present."""
        mock_settings = _create_mock_settings()

        result = await get_tool_visibility(settings=mock_settings)
        tool_keys = [t["key"] for t in result["tools"]]

        expected_keys = [
            "files",
            "add-files",
            "document-review",
        ]
        for key in expected_keys:
            assert key in tool_keys


# Helper functions


def _create_mock_settings(
    tool_files_enabled: bool = False,
    tool_add_files_enabled: bool = False,
    tool_document_review_enabled: bool = False,
    tool_flags_updated_at: datetime = None,
) -> MagicMock:
    """Create mock settings object."""
    mock = MagicMock()
    mock.tool_files_enabled = tool_files_enabled
    mock.tool_add_files_enabled = tool_add_files_enabled
    mock.tool_document_review_enabled = tool_document_review_enabled
    mock.tool_flags_updated_at = tool_flags_updated_at
    return mock


def _find_tool(tools: list, key: str) -> dict:
    """Find a tool by key in the tools list."""
    for tool in tools:
        if tool["key"] == key:
            return tool
    return None
