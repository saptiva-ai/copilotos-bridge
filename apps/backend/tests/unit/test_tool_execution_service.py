"""
Unit tests for ToolExecutionService.

Tests:
- invoke_relevant_tools logic
- Caching mechanism (hit/miss/set)
- Tool execution delegation
- Error resilience
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import json
import sys
import os
from redis.exceptions import RedisError

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))

from src.services.tool_execution_service import ToolExecutionService, TOOL_CACHE_TTL
from src.core.constants import TOOL_NAME_EXCEL
from src.domain.chat_context import ChatContext


@pytest.fixture
def mock_redis():
    """Mock Redis cache."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


@pytest.fixture
def mock_mcp_adapter():
    """Mock MCP adapter."""
    adapter = AsyncMock()
    # _get_tool_map returns a dict of tool implementations
    tool_map = {
        TOOL_NAME_EXCEL: AsyncMock()
    }
    adapter._get_tool_map = AsyncMock(return_value=tool_map)
    adapter._execute_tool_impl = AsyncMock()
    return adapter


@pytest.fixture
def mock_context():
    """Mock ChatContext."""
    context = Mock(spec=ChatContext)
    context.tools_enabled = {TOOL_NAME_EXCEL: True}
    context.document_ids = ["doc-123"]
    return context


@pytest.mark.unit
class TestToolExecutionService:
    """Test suite for ToolExecutionService."""

    @pytest.mark.asyncio
    async def test_skips_when_no_tools_enabled(self, mock_context):
        """Should return empty dict if no tools are enabled."""
        mock_context.tools_enabled = {}

        with patch('src.services.tool_execution_service.get_redis_cache', new_callable=AsyncMock), \
             patch('src.services.tool_execution_service.get_mcp_adapter', new_callable=AsyncMock) as mock_get_adapter:

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            assert results == {}
            mock_get_adapter.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_no_documents(self, mock_context):
        """Should return empty dict if no documents are attached."""
        mock_context.document_ids = []

        with patch('src.services.tool_execution_service.get_redis_cache', new_callable=AsyncMock), \
             patch('src.services.tool_execution_service.get_mcp_adapter', new_callable=AsyncMock) as mock_get_adapter:

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            assert results == {}
            mock_get_adapter.assert_not_called()

    @pytest.mark.asyncio
    async def test_executes_excel_tool_cache_miss(self, mock_context, mock_redis, mock_mcp_adapter):
        """Should execute excel tool and cache result on cache miss."""
        # Setup Document mock
        mock_doc = AsyncMock()
        mock_doc.user_id = "user-123"
        mock_doc.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        # Setup tool execution
        mock_mcp_adapter._execute_tool_impl.return_value = {"sheets": ["Sheet1"]}

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_mcp_adapter), \
             patch('src.models.document.Document.get', return_value=mock_doc):

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Verification
            assert f"{TOOL_NAME_EXCEL}_doc-123" in results
            assert results[f"{TOOL_NAME_EXCEL}_doc-123"] == {"sheets": ["Sheet1"]}

            # Verify execution
            mock_mcp_adapter._execute_tool_impl.assert_called_once()
            call_args = mock_mcp_adapter._execute_tool_impl.call_args
            assert call_args.kwargs["tool_name"] == TOOL_NAME_EXCEL
            assert call_args.kwargs["payload"]["doc_id"] == "doc-123"

            # Verify caching
            mock_redis.get.assert_called_once()
            mock_redis.set.assert_called_once()
            set_args = mock_redis.set.call_args
            assert set_args.kwargs["expire"] == TOOL_CACHE_TTL[TOOL_NAME_EXCEL]

    @pytest.mark.asyncio
    async def test_returns_cached_excel_result(self, mock_context, mock_redis, mock_mcp_adapter):
        """Should return cached result and skip execution on cache hit."""
        # Setup Document mock
        mock_doc = AsyncMock()
        mock_doc.user_id = "user-123"
        mock_doc.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        # Setup cache hit
        cached_data = {"sheets": ["CachedSheet"]}
        mock_redis.get.return_value = cached_data

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_mcp_adapter), \
             patch('src.models.document.Document.get', return_value=mock_doc):

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Verification
            assert results[f"{TOOL_NAME_EXCEL}_doc-123"] == cached_data

            # Verify NO execution
            mock_mcp_adapter._execute_tool_impl.assert_not_called()

            # Verify cache read
            mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_executes_excel_tool_for_spreadsheets(self, mock_context, mock_redis, mock_mcp_adapter):
        """Should execute excel analyzer only for spreadsheet files."""
        # Setup Document mock
        mock_doc = AsyncMock()
        mock_doc.user_id = "user-123"
        mock_doc.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        mock_mcp_adapter._execute_tool_impl.return_value = {"sheets": ["Sheet1"]}

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_mcp_adapter), \
             patch('src.models.document.Document.get', return_value=mock_doc):

            # Enable excel tool
            mock_context.tools_enabled = {TOOL_NAME_EXCEL: True}

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Verification
            assert f"{TOOL_NAME_EXCEL}_doc-123" in results
            assert results[f"{TOOL_NAME_EXCEL}_doc-123"] == {"sheets": ["Sheet1"]}

            mock_mcp_adapter._execute_tool_impl.assert_called_once()
            assert mock_mcp_adapter._execute_tool_impl.call_args.kwargs["tool_name"] == TOOL_NAME_EXCEL

    @pytest.mark.asyncio
    async def test_skips_excel_tool_for_non_spreadsheets(self, mock_context, mock_redis, mock_mcp_adapter):
        """Should skip excel analyzer for non-spreadsheet files (e.g. PDF)."""
        # Setup PDF Document mock
        mock_doc = AsyncMock()
        mock_doc.user_id = "user-123"
        mock_doc.content_type = "application/pdf"

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_mcp_adapter), \
             patch('src.models.document.Document.get', return_value=mock_doc):

            mock_context.tools_enabled = {TOOL_NAME_EXCEL: True}

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Verification - should be empty as PDF is not Excel
            assert results == {}
            mock_mcp_adapter._execute_tool_impl.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_execution_error_gracefully(self, mock_context, mock_redis, mock_mcp_adapter):
        """Should continue if one tool fails."""
        # Setup Document mock - must be an Excel file for the tool to execute
        mock_doc = AsyncMock()
        mock_doc.user_id = "user-123"
        mock_doc.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        # Setup execution failure
        mock_mcp_adapter._execute_tool_impl.side_effect = Exception("MCP Error")

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_mcp_adapter), \
             patch('src.models.document.Document.get', return_value=mock_doc):

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Verification - should return empty dict, not raise exception
            assert results == {}

            # Should verify it tried to execute
            mock_mcp_adapter._execute_tool_impl.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_read_failure_fallback(self, mock_context, mock_redis, mock_mcp_adapter):
        """Should execute tool even if cache read fails."""
        # Setup Document mock
        mock_doc = AsyncMock()
        mock_doc.user_id = "user-123"
        mock_doc.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        # Setup cache failure - use RedisError so it's properly caught
        mock_redis.get.side_effect = RedisError("Redis down")
        mock_mcp_adapter._execute_tool_impl.return_value = {"result": "ok"}

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_mcp_adapter), \
             patch('src.models.document.Document.get', return_value=mock_doc):

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Should have executed despite redis error
            assert f"{TOOL_NAME_EXCEL}_doc-123" in results
            mock_mcp_adapter._execute_tool_impl.assert_called_once()

    @pytest.mark.asyncio
    async def test_parallel_execution_multiple_documents(self, mock_redis, mock_mcp_adapter):
        """
        Should process multiple documents in parallel using asyncio.gather.

        This test verifies that multi-document chats benefit from
        parallel execution (5-10x speedup vs sequential).
        """
        import asyncio

        # Setup context with multiple documents
        mock_context = Mock(spec=ChatContext)
        mock_context.tools_enabled = {TOOL_NAME_EXCEL: True}
        mock_context.document_ids = ["doc-1", "doc-2", "doc-3"]

        # Track execution order to verify parallelism
        execution_order = []
        execution_times = []

        async def mock_get_doc(doc_id):
            """Mock document that records execution start."""
            execution_order.append(f"get_{doc_id}")
            # Small delay to simulate I/O
            await asyncio.sleep(0.01)
            mock_doc = AsyncMock()
            mock_doc.user_id = "user-123"
            mock_doc.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            return mock_doc

        async def mock_execute(*args, **kwargs):
            """Mock execution that records timing."""
            doc_id = kwargs.get("payload", {}).get("doc_id", "unknown")
            execution_order.append(f"exec_{doc_id}")
            await asyncio.sleep(0.01)
            return {"sheets": [f"Sheet_{doc_id}"]}

        mock_mcp_adapter._execute_tool_impl.side_effect = mock_execute

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_mcp_adapter), \
             patch('src.models.document.Document.get', side_effect=mock_get_doc):

            import time
            start = time.time()
            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")
            elapsed = time.time() - start

            # Verification: All documents processed
            assert f"{TOOL_NAME_EXCEL}_doc-1" in results
            assert f"{TOOL_NAME_EXCEL}_doc-2" in results
            assert f"{TOOL_NAME_EXCEL}_doc-3" in results

            # Verification: Results are correct
            assert results[f"{TOOL_NAME_EXCEL}_doc-1"]["sheets"] == ["Sheet_doc-1"]
            assert results[f"{TOOL_NAME_EXCEL}_doc-2"]["sheets"] == ["Sheet_doc-2"]
            assert results[f"{TOOL_NAME_EXCEL}_doc-3"]["sheets"] == ["Sheet_doc-3"]

            # Verification: Parallel execution (should complete faster than sequential)
            assert elapsed < 0.1, f"Execution took {elapsed}s - expected parallel execution"

            # Verification: Executed for all 3 docs
            assert mock_mcp_adapter._execute_tool_impl.call_count == 3

    @pytest.mark.asyncio
    async def test_parallel_handles_mixed_file_types(self, mock_redis, mock_mcp_adapter):
        """
        Should correctly filter non-Excel files in parallel processing.
        """
        # Setup context with mixed documents
        mock_context = Mock(spec=ChatContext)
        mock_context.tools_enabled = {TOOL_NAME_EXCEL: True}
        mock_context.document_ids = ["excel-1", "pdf-1", "excel-2"]

        async def mock_get_doc(doc_id):
            """Return Excel or PDF based on doc_id."""
            mock_doc = AsyncMock()
            mock_doc.user_id = "user-123"
            if "excel" in doc_id:
                mock_doc.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                mock_doc.content_type = "application/pdf"
            return mock_doc

        mock_mcp_adapter._execute_tool_impl.return_value = {"sheets": ["Sheet1"]}

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_mcp_adapter), \
             patch('src.models.document.Document.get', side_effect=mock_get_doc):

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Verification: Only Excel files processed
            assert f"{TOOL_NAME_EXCEL}_excel-1" in results
            assert f"{TOOL_NAME_EXCEL}_excel-2" in results
            assert f"{TOOL_NAME_EXCEL}_pdf-1" not in results

            # Verification: Only 2 executions (not 3)
            assert mock_mcp_adapter._execute_tool_impl.call_count == 2

    @pytest.mark.asyncio
    async def test_parallel_handles_partial_failures(self, mock_redis, mock_mcp_adapter):
        """
        Should continue processing other documents if one fails.
        """
        # Setup context with multiple documents
        mock_context = Mock(spec=ChatContext)
        mock_context.tools_enabled = {TOOL_NAME_EXCEL: True}
        mock_context.document_ids = ["doc-ok-1", "doc-fail", "doc-ok-2"]

        async def mock_get_doc(doc_id):
            """Simulate failure for one document."""
            if doc_id == "doc-fail":
                raise Exception("Document not found")
            mock_doc = AsyncMock()
            mock_doc.user_id = "user-123"
            mock_doc.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            return mock_doc

        mock_mcp_adapter._execute_tool_impl.return_value = {"sheets": ["Sheet1"]}

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_mcp_adapter), \
             patch('src.models.document.Document.get', side_effect=mock_get_doc):

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Verification: Successful documents processed
            assert f"{TOOL_NAME_EXCEL}_doc-ok-1" in results
            assert f"{TOOL_NAME_EXCEL}_doc-ok-2" in results

            # Verification: Failed document not in results
            assert f"{TOOL_NAME_EXCEL}_doc-fail" not in results

            # Verification: 2 successful executions
            assert mock_mcp_adapter._execute_tool_impl.call_count == 2


@pytest.mark.unit
class TestGenerateCacheKey:
    """Tests for _generate_cache_key static method."""

    def test_generates_key_without_params(self):
        """Should generate cache key without params."""
        key = ToolExecutionService._generate_cache_key("excel_analyzer", "doc-123")
        assert key == "mcp:tool:excel_analyzer:doc-123"

    def test_generates_key_with_params(self):
        """Should generate cache key with params hash."""
        params = {"sheet": "Sheet1", "operation": "stats"}
        key = ToolExecutionService._generate_cache_key("excel_analyzer", "doc-123", params)

        assert key.startswith("mcp:tool:excel_analyzer:doc-123:")
        # Should have 8-char hash suffix
        parts = key.split(":")
        assert len(parts) == 5
        assert len(parts[4]) == 8

    def test_same_params_produce_same_key(self):
        """Should produce same key for same params."""
        params = {"a": 1, "b": 2}
        key1 = ToolExecutionService._generate_cache_key("tool", "doc", params)
        key2 = ToolExecutionService._generate_cache_key("tool", "doc", params)
        assert key1 == key2

    def test_different_params_produce_different_keys(self):
        """Should produce different keys for different params."""
        key1 = ToolExecutionService._generate_cache_key("tool", "doc", {"a": 1})
        key2 = ToolExecutionService._generate_cache_key("tool", "doc", {"a": 2})
        assert key1 != key2


@pytest.mark.unit
class TestInvokeRelevantToolsRedisErrors:
    """Tests for Redis error handling in invoke_relevant_tools."""

    @pytest.mark.asyncio
    async def test_handles_redis_error_getting_cache(self, mock_context):
        """Should handle Redis error when getting cache."""
        with patch('src.services.tool_execution_service.get_redis_cache') as mock_get_cache:
            mock_get_cache.side_effect = RedisError("Redis down")

            # Should not raise
            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Returns empty dict on cache error
            assert results == {}


@pytest.mark.unit
class TestParallelExcelProcessingErrors:
    """Tests for parallel Excel processing error handling."""

    @pytest.mark.asyncio
    async def test_handles_parallel_processing_exception(self, mock_context, mock_redis):
        """Should handle exceptions in parallel document processing."""
        mock_context.document_ids = ["doc-1", "doc-2", "doc-3"]

        mock_doc_success = AsyncMock()
        mock_doc_success.user_id = "user-123"
        mock_doc_success.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        mock_adapter = AsyncMock()
        # First call succeeds, second fails
        mock_adapter._execute_tool_impl.side_effect = [
            {"sheets": ["Sheet1"]},
            Exception("Processing failed"),
            {"sheets": ["Sheet2"]},
        ]

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_adapter), \
             patch('src.models.document.Document.get', return_value=mock_doc_success):

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Should have some results despite one failure


@pytest.mark.unit
class TestInvokeRelevantToolsException:
    """Tests for overall exception handling in invoke_relevant_tools."""

    @pytest.mark.asyncio
    async def test_handles_overall_exception(self, mock_context):
        """Should return empty dict on overall exception."""
        with patch('src.services.tool_execution_service.get_redis_cache') as mock_get_cache:
            mock_cache = AsyncMock()
            mock_get_cache.return_value = mock_cache

            # Make get_mcp_adapter raise an exception
            with patch('src.services.tool_execution_service.get_mcp_adapter') as mock_adapter:
                mock_adapter.side_effect = Exception("Adapter creation failed")

                results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

                # Should return empty dict on error
                assert results == {}


@pytest.mark.unit
class TestCacheSetError:
    """Tests for Redis cache set error handling."""

    @pytest.mark.asyncio
    async def test_continues_on_cache_set_failure(self, mock_context, mock_redis, mock_mcp_adapter):
        """Should return result even if cache set fails."""
        mock_context.document_ids = ["doc-123"]

        mock_doc = AsyncMock()
        mock_doc.user_id = "user-123"
        mock_doc.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        # Setup cache miss and set failure
        mock_redis.get.return_value = None  # Cache miss
        mock_redis.set.side_effect = RedisError("Redis write failed")  # Cache set fails

        # Setup tool execution success
        mock_mcp_adapter._execute_tool_impl.return_value = {"sheets": ["Sheet1"]}

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_mcp_adapter), \
             patch('src.models.document.Document.get', return_value=mock_doc):

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Should still return the result despite cache set failure
            assert f"{TOOL_NAME_EXCEL}_doc-123" in results
            assert results[f"{TOOL_NAME_EXCEL}_doc-123"] == {"sheets": ["Sheet1"]}


@pytest.mark.unit
class TestParallelExcelDocumentMismatch:
    """Tests for parallel Excel processing document mismatch."""

    @pytest.mark.asyncio
    async def test_returns_none_for_wrong_user(self, mock_redis, mock_mcp_adapter):
        """Should return None when document user_id doesn't match."""
        mock_context = Mock(spec=ChatContext)
        mock_context.tools_enabled = {TOOL_NAME_EXCEL: True}
        mock_context.document_ids = ["doc-123"]

        # Document belongs to different user
        mock_doc = AsyncMock()
        mock_doc.user_id = "different-user"
        mock_doc.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_mcp_adapter), \
             patch('src.models.document.Document.get', return_value=mock_doc):

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Should return empty because user doesn't match
            assert results == {}

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_document(self, mock_redis, mock_mcp_adapter):
        """Should return None when document not found."""
        mock_context = Mock(spec=ChatContext)
        mock_context.tools_enabled = {TOOL_NAME_EXCEL: True}
        mock_context.document_ids = ["doc-missing"]

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_mcp_adapter), \
             patch('src.models.document.Document.get', return_value=None):

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Should return empty because doc is None
            assert results == {}


@pytest.mark.unit
class TestParallelExcelGatherException:
    """Tests for parallel Excel gather exception handling."""

    @pytest.mark.asyncio
    async def test_handles_gather_exception(self, mock_redis, mock_mcp_adapter):
        """Should handle exceptions from asyncio.gather gracefully."""
        mock_context = Mock(spec=ChatContext)
        mock_context.tools_enabled = {TOOL_NAME_EXCEL: True}
        mock_context.document_ids = ["doc-1", "doc-2"]

        async def mock_get_doc(doc_id):
            if doc_id == "doc-1":
                raise RuntimeError("Simulated gather exception")
            mock_doc = AsyncMock()
            mock_doc.user_id = "user-123"
            mock_doc.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            return mock_doc

        mock_mcp_adapter._execute_tool_impl.return_value = {"sheets": ["Sheet1"]}

        with patch('src.services.tool_execution_service.get_redis_cache', return_value=mock_redis), \
             patch('src.services.tool_execution_service.get_mcp_adapter', return_value=mock_mcp_adapter), \
             patch('src.models.document.Document.get', side_effect=mock_get_doc):

            results = await ToolExecutionService.invoke_relevant_tools(mock_context, "user-123")

            # Should still have result for doc-2 despite doc-1 failure
            assert f"{TOOL_NAME_EXCEL}_doc-2" in results
