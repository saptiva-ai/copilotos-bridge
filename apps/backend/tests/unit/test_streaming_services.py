"""
Unit tests for streaming services extracted from streaming_handler.py.

REFACTOR-001: Phase 1 tests for AuditorResultFormatterService.
"""

import pytest

from src.services.streaming import (
    AuditorResultFormatterService,
    ChunkEmitter,
    SaptivaStreamer,
    StreamerConfig,
    CompletionResult,
    AuditResponseBuilder,
    AuditResult,
    AuditSummary,
    AUDITOR_ORDER,
    AUDITOR_DISPLAY_NAMES,
    AUDITOR_HUMANIZE_NAMES,
    SEVERITY_DISPLAY,
)


class TestAuditorResultFormatterService:
    """Tests for AuditorResultFormatterService."""

    def test_normalize_auditor_key_compliance(self):
        """Should normalize compliance-related keys."""
        assert AuditorResultFormatterService.normalize_auditor_key("compliance") == "compliance"
        assert AuditorResultFormatterService.normalize_auditor_key("cumplimiento") == "compliance"
        assert AuditorResultFormatterService.normalize_auditor_key("disclaimer") == "compliance"

    def test_normalize_auditor_key_format(self):
        """Should normalize format-related keys."""
        assert AuditorResultFormatterService.normalize_auditor_key("format") == "format"
        assert AuditorResultFormatterService.normalize_auditor_key("formato") == "format"
        assert AuditorResultFormatterService.normalize_auditor_key("layout") == "format"

    def test_normalize_auditor_key_grammar(self):
        """Should normalize grammar-related keys."""
        assert AuditorResultFormatterService.normalize_auditor_key("grammar") == "grammar"
        assert AuditorResultFormatterService.normalize_auditor_key("gramática") == "grammar"
        assert AuditorResultFormatterService.normalize_auditor_key("ortografia") == "grammar"

    def test_normalize_auditor_key_unknown_returns_other(self):
        """Unknown keys should return 'other'."""
        assert AuditorResultFormatterService.normalize_auditor_key("unknown") == "other"
        assert AuditorResultFormatterService.normalize_auditor_key("") == "other"
        assert AuditorResultFormatterService.normalize_auditor_key(None) == "other"

    def test_aggregate_auditors_groups_by_category(self):
        """Should aggregate findings by auditor category."""
        validation_event = {
            "findings": [
                {"category": "grammar", "severity": "high"},
                {"category": "grammar", "severity": "low"},
                {"category": "format", "severity": "medium"},
            ]
        }
        result = AuditorResultFormatterService.aggregate_auditors(validation_event)

        assert "grammar" in result
        assert result["grammar"]["total"] == 2
        assert result["grammar"]["high"] == 1
        assert result["grammar"]["low"] == 1

        assert "format" in result
        assert result["format"]["total"] == 1
        assert result["format"]["medium"] == 1

    def test_aggregate_auditors_uses_existing_by_auditor(self):
        """Should use existing by_auditor if present in summary."""
        validation_event = {
            "summary": {
                "by_auditor": {
                    "grammar": {"total": 5, "high": 2},
                    "format": {"total": 3, "medium": 1},
                }
            }
        }
        result = AuditorResultFormatterService.aggregate_auditors(validation_event)
        assert result["grammar"]["total"] == 5
        assert result["format"]["total"] == 3

    def test_build_breakdown_markdown_returns_none_for_empty(self):
        """Should return None if no findings."""
        result = AuditorResultFormatterService.build_breakdown_markdown({})
        assert result is None

    def test_build_breakdown_markdown_generates_markdown(self):
        """Should generate proper markdown breakdown."""
        validation_event = {
            "findings": [
                {"category": "grammar", "severity": "high"},
                {"category": "format", "severity": "low"},
            ]
        }
        result = AuditorResultFormatterService.build_breakdown_markdown(validation_event)

        assert result is not None
        assert "### Análisis por auditor" in result

    def test_humanize_auditor_result_no_findings(self):
        """Should return positive message when no findings."""
        result = AuditorResultFormatterService.humanize_auditor_result(
            "Grammar Auditor", 0, []
        )
        assert "impecable" in result or "No se detectaron" in result

    def test_humanize_auditor_result_critical_level(self):
        """Should show critical level for critical findings."""
        findings = [{"severity": "critical"}, {"severity": "critical"}]
        result = AuditorResultFormatterService.humanize_auditor_result(
            "Format Auditor", 2, findings
        )
        assert "Crítico" in result

    def test_humanize_auditor_result_high_level(self):
        """Should show high level for high findings."""
        findings = [{"severity": "high"}]
        result = AuditorResultFormatterService.humanize_auditor_result(
            "Format Auditor", 1, findings
        )
        assert "Alto" in result

    def test_humanize_auditor_result_medium_level(self):
        """Should show medium level for medium findings."""
        findings = [{"severity": "medium"}]
        result = AuditorResultFormatterService.humanize_auditor_result(
            "Format Auditor", 1, findings
        )
        assert "Medio" in result

    def test_humanize_auditor_result_low_level(self):
        """Should show low level for low findings."""
        findings = [{"severity": "low"}]
        result = AuditorResultFormatterService.humanize_auditor_result(
            "Format Auditor", 1, findings
        )
        assert "Bajo" in result

    def test_format_auditor_markdown_adds_sublists(self):
        """Should format auditor analysis as markdown sublists."""
        text = "El auditor encontró problemas.\nLa auditoría detectó errores."
        result = AuditorResultFormatterService.format_auditor_markdown(text)
        assert "   - El auditor" in result
        assert "   - La auditoría" in result

    def test_format_auditor_markdown_preserves_existing_lists(self):
        """Should preserve lines that already start with dash."""
        text = "- Already a list item"
        result = AuditorResultFormatterService.format_auditor_markdown(text)
        assert result == "- Already a list item"


class TestConstants:
    """Tests for exported constants."""

    def test_auditor_order_contains_all_types(self):
        """AUDITOR_ORDER should contain all standard auditor types."""
        assert "compliance" in AUDITOR_ORDER
        assert "grammar" in AUDITOR_ORDER
        assert "format" in AUDITOR_ORDER
        assert len(AUDITOR_ORDER) >= 8

    def test_display_names_match_order(self):
        """Every key in AUDITOR_ORDER should have a display name."""
        for key in AUDITOR_ORDER:
            assert key in AUDITOR_DISPLAY_NAMES

    def test_humanize_names_match_order(self):
        """Every key in AUDITOR_ORDER should have a humanize name."""
        for key in AUDITOR_ORDER:
            assert key in AUDITOR_HUMANIZE_NAMES

    def test_severity_display_has_all_levels(self):
        """SEVERITY_DISPLAY should have all severity levels."""
        assert "critical" in SEVERITY_DISPLAY
        assert "high" in SEVERITY_DISPLAY
        assert "medium" in SEVERITY_DISPLAY
        assert "low" in SEVERITY_DISPLAY


# ============================================================================
# PHASE 2 TESTS: DocumentContextBuilder
# ============================================================================

from src.services.streaming import DocumentContextBuilder


class TestDocumentContextBuilder:
    """Tests for DocumentContextBuilder (Phase 2)."""

    def test_format_for_prompt_empty_returns_empty(self):
        """Empty context should return empty string."""
        result = DocumentContextBuilder.format_for_prompt("")
        assert result == ""

        result = DocumentContextBuilder.format_for_prompt(None)
        assert result == ""

    def test_format_for_prompt_adds_header(self):
        """Non-empty context should get header added."""
        context = "Document content here"
        result = DocumentContextBuilder.format_for_prompt(context)

        assert "Documentos adjuntos por el usuario" in result
        assert context in result

    def test_init_with_custom_params(self):
        """Should initialize with custom parameters."""
        builder = DocumentContextBuilder(max_segments=5, max_text_chars=8000)
        assert builder.max_segments == 5
        assert builder.max_text_chars == 8000

    def test_init_with_defaults(self):
        """Should initialize with default parameters."""
        builder = DocumentContextBuilder()
        assert builder.max_segments == 5
        assert builder.max_text_chars == 12000


# ============================================================================
# PHASE 3 TESTS: MessagePersistenceService
# ============================================================================

from src.services.streaming import MessagePersistenceService
import json


class TestMessagePersistenceService:
    """Tests for MessagePersistenceService (Phase 3)."""

    def test_build_assistant_metadata_basic(self):
        """Should build basic metadata without extra data."""
        metadata = MessagePersistenceService.build_assistant_metadata(
            streaming=True,
            document_ids=["doc1", "doc2"],
            doc_warnings=["Warning 1"],
        )

        assert metadata["streaming"] is True
        assert metadata["has_documents"] is True
        assert metadata["document_warnings"] == ["Warning 1"]

    def test_build_assistant_metadata_no_documents(self):
        """Should handle case with no documents."""
        metadata = MessagePersistenceService.build_assistant_metadata(
            streaming=True,
            document_ids=None,
            doc_warnings=None,
        )

        assert metadata["streaming"] is True
        assert metadata["has_documents"] is False
        assert metadata["document_warnings"] is None

    def test_build_done_event(self):
        """Should build correct done event structure."""
        event = MessagePersistenceService.build_done_event(
            message_id="msg123",
            chat_id="chat456",
            content="Response content",
        )

        assert event["event"] == "done"
        data = json.loads(event["data"])
        assert data["message_id"] == "msg123"
        assert data["chat_id"] == "chat456"
        assert data["content"] == "Response content"

    def test_build_error_event(self):
        """Should build correct error event structure."""
        event = MessagePersistenceService.build_error_event(
            error_message="Something went wrong",
            error_type="ValueError",
            recoverable=True,
        )

        assert event["event"] == "error"
        data = json.loads(event["data"])
        assert data["error"] == "Something went wrong"
        assert data["type"] == "ValueError"
        assert data["recoverable"] is True

    def test_build_error_content(self):
        """Should build user-friendly error content."""
        error = ValueError("Test error message")
        content = MessagePersistenceService.build_error_content(error)

        assert "Error al procesar" in content
        assert "Test error message" in content
        assert "soporte" in content.lower()

    def test_build_error_metadata(self):
        """Should build error metadata correctly."""
        error = ValueError("Test error")
        metadata = MessagePersistenceService.build_error_metadata(error)

        assert metadata["error"] is True
        assert metadata["error_type"] == "ValueError"
        assert "Test error" in metadata["error_message"]


# ============================================================================
# PHASE 4 TESTS: TokenBudgetManager and ResponsePostProcessor
# ============================================================================

from src.services.streaming import (
    TokenBudgetManager,
    TokenBudgetResult,
    ResponsePostProcessor,
    PostProcessResult,
)


class TestTokenBudgetManager:
    """Tests for TokenBudgetManager (Phase 4)."""

    def test_estimate_tokens_empty_messages(self):
        """Empty messages should return 0 tokens."""
        tokens = TokenBudgetManager.estimate_tokens([])
        assert tokens == 0

    def test_estimate_tokens_basic(self):
        """Should estimate tokens from character count."""
        messages = [
            {"content": "Hello"},  # 5 chars = 1 token
            {"content": "World"},  # 5 chars = 1 token
        ]
        tokens = TokenBudgetManager.estimate_tokens(messages)
        assert tokens == 2  # 10 chars / 4 = 2

    def test_estimate_tokens_long_content(self):
        """Should handle longer content correctly."""
        messages = [
            {"content": "a" * 400},  # 400 chars = 100 tokens
        ]
        tokens = TokenBudgetManager.estimate_tokens(messages)
        assert tokens == 100

    def test_calculate_dynamic_max_tokens_small_prompt(self):
        """Small prompt should allow more response tokens."""
        messages = [
            {"content": "Short prompt"},
        ]
        max_tokens = TokenBudgetManager.calculate_dynamic_max_tokens(
            messages=messages,
            model_limit=8192,
            min_tokens=500,
            max_tokens=3000,
        )
        # Small prompt should get max_tokens (capped at 3000)
        assert max_tokens == 3000

    def test_calculate_dynamic_max_tokens_large_prompt(self):
        """Large prompt should reduce response tokens to min_tokens."""
        messages = [
            {"content": "x" * 32000},  # ~8000 tokens (exceeds model limit)
        ]
        max_tokens = TokenBudgetManager.calculate_dynamic_max_tokens(
            messages=messages,
            model_limit=8192,
            min_tokens=500,
            max_tokens=3000,
        )
        # Large prompt that exceeds limit should get min_tokens (500)
        assert max_tokens == 500

    def test_truncate_messages_under_threshold(self):
        """Messages under threshold should not be truncated."""
        messages = [
            {"content": "System prompt"},
            {"content": "Message 1"},
            {"content": "Current message"},
        ]
        result, truncated = TokenBudgetManager.truncate_messages_if_needed(
            messages=messages,
            threshold=6000,
        )
        assert truncated == 0
        assert len(result) == 3

    def test_truncate_messages_over_threshold(self):
        """Messages over threshold should be truncated."""
        messages = [
            {"content": "System"},  # Keep
            {"content": "x" * 20000},  # ~5000 tokens - remove
            {"content": "x" * 20000},  # ~5000 tokens - remove
            {"content": "Current"},  # Keep (last)
        ]
        result, truncated = TokenBudgetManager.truncate_messages_if_needed(
            messages=messages,
            threshold=6000,
        )
        assert truncated >= 1
        assert len(result) < 4
        # System (first) and Current (last) should be preserved
        assert result[0]["content"] == "System"
        assert result[-1]["content"] == "Current"

    def test_check_token_overflow_under_limit(self):
        """Should return False when under limit."""
        messages = [{"content": "Short message"}]
        overflow = TokenBudgetManager.check_token_overflow(
            messages=messages,
            model_limit=8192,
        )
        assert overflow is False

    def test_check_token_overflow_over_limit(self):
        """Should return True when over critical threshold."""
        messages = [{"content": "x" * 32000}]  # ~8000 tokens
        overflow = TokenBudgetManager.check_token_overflow(
            messages=messages,
            model_limit=8192,
            critical_threshold=7500,
        )
        assert overflow is True

    def test_prepare_messages_for_api(self):
        """Should return complete TokenBudgetResult."""
        messages = [
            {"content": "System prompt"},
            {"content": "User message"},
        ]
        result = TokenBudgetManager.prepare_messages_for_api(
            messages=messages,
            model_limit=8192,
        )

        assert isinstance(result, TokenBudgetResult)
        assert result.max_tokens > 0
        assert result.estimated_prompt_tokens > 0
        assert result.total_chars > 0
        assert result.messages_truncated >= 0
        assert result.will_exceed_limit is False


class TestResponsePostProcessor:
    """Tests for ResponsePostProcessor (Phase 4)."""

    def test_sanitize_sql_no_sql(self):
        """Non-SQL content should pass through unchanged."""
        content = "This is a normal response without SQL."
        result, chars_removed = ResponsePostProcessor.sanitize_sql(content)
        assert result == content
        assert chars_removed == 0

    def test_sanitize_sql_empty(self):
        """Empty content should return empty."""
        result, chars_removed = ResponsePostProcessor.sanitize_sql("")
        assert result == ""
        assert chars_removed == 0

    def test_process_non_empty_response(self):
        """Non-empty response should pass through post-processing."""
        result = ResponsePostProcessor.process(
            response="Valid response content",
            has_documents=False,
        )

        assert isinstance(result, PostProcessResult)
        assert result.content == "Valid response content"
        assert result.was_empty is False
        assert result.fallback_scenario is None

    def test_process_preserves_content(self):
        """Process should preserve non-empty, non-SQL content."""
        content = "Here is my analysis of the data."
        result = ResponsePostProcessor.process(
            response=content,
            has_documents=False,
            sanitize=True,
            validate_truth=False,  # Skip truth-gating for this test
        )

        assert result.content == content
        assert result.was_empty is False
        assert result.was_sanitized is False

    def test_validate_truth_gating_no_data(self):
        """Should return valid when no chart data."""
        is_valid, violations = ResponsePostProcessor.validate_truth_gating(
            response="Some response",
        )
        assert is_valid is True
        assert violations == []

    def test_validate_truth_gating_empty_response(self):
        """Should return valid for empty response."""
        is_valid, violations = ResponsePostProcessor.validate_truth_gating(
            response="",
        )
        assert is_valid is True
        assert violations == []


class TestPhase4Integration:
    """Integration tests for Phase 4 services."""

    def test_token_budget_with_truncation(self):
        """Test full token budget flow with truncation."""
        # Create messages that will trigger truncation
        messages = [
            {"content": "System prompt"},
            {"content": "x" * 16000},  # ~4000 tokens
            {"content": "x" * 16000},  # ~4000 tokens
            {"content": "Current message"},
        ]

        original_len = len(messages)
        result = TokenBudgetManager.prepare_messages_for_api(
            messages=messages,
            model_limit=8192,
        )

        # Should have truncated some messages
        assert result.messages_truncated > 0 or len(messages) < original_len

    def test_post_processor_full_pipeline(self):
        """Test complete post-processing pipeline."""
        result = ResponsePostProcessor.process(
            response="Analysis shows good performance.",
            has_documents=True,
            doc_warnings=None,
            context={"user_id": "user123"},
            sanitize=True,
            validate_truth=True,
        )

        assert result.content is not None
        assert result.was_empty is False
        assert isinstance(result.truth_violations, list)

# ============================================================================
# PHASE 5 TESTS: ChunkEmitter and SaptivaStreamer
# ============================================================================

import asyncio
import json


class TestChunkEmitter:
    """Tests for ChunkEmitter service (Phase 5.1)."""

    def test_split_text_empty_string(self):
        """Empty string should return empty list."""
        result = ChunkEmitter.split_text("")
        assert result == []

    def test_split_text_none_returns_empty(self):
        """None should return empty list."""
        result = ChunkEmitter.split_text(None)
        assert result == []

    def test_split_text_short_text(self):
        """Text shorter than chunk size should return single chunk."""
        result = ChunkEmitter.split_text("Hello", chunk_size=50)
        assert result == ["Hello"]

    def test_split_text_exact_chunk_size(self):
        """Text exactly chunk size should return single chunk."""
        text = "x" * 50
        result = ChunkEmitter.split_text(text, chunk_size=50)
        assert len(result) == 1
        assert result[0] == text

    def test_split_text_multiple_chunks(self):
        """Text longer than chunk size should split into multiple chunks."""
        text = "a" * 120  # 120 chars
        result = ChunkEmitter.split_text(text, chunk_size=50)

        assert len(result) == 3  # 50 + 50 + 20
        assert len(result[0]) == 50
        assert len(result[1]) == 50
        assert len(result[2]) == 20
        assert "".join(result) == text

    def test_split_text_default_chunk_size(self):
        """Should use DEFAULT_CHUNK_SIZE when not specified."""
        text = "x" * 100
        result = ChunkEmitter.split_text(text)

        assert len(result) == 2  # 50 + 50 with default
        assert len(result[0]) == ChunkEmitter.DEFAULT_CHUNK_SIZE

    def test_build_chunk_event_format(self):
        """Chunk event should have correct SSE format."""
        event = ChunkEmitter.build_chunk_event("Hello world")

        assert event["event"] == "chunk"
        assert "data" in event
        # Verify JSON data
        data = json.loads(event["data"])
        assert data["content"] == "Hello world"

    def test_build_chunk_event_empty_content(self):
        """Should handle empty content."""
        event = ChunkEmitter.build_chunk_event("")

        data = json.loads(event["data"])
        assert data["content"] == ""

    @pytest.mark.asyncio
    async def test_emit_chunks_to_queue(self):
        """Should emit chunks to asyncio queue."""
        queue = asyncio.Queue()
        text = "Hello, this is a test message that is longer than the chunk size."

        chunks_emitted = await ChunkEmitter.emit_chunks(
            text=text,
            queue=queue,
            chunk_size=20,
        )

        # Verify chunks were emitted
        assert chunks_emitted == 4  # ceil(67 / 20) = 4

        # Verify queue contents
        collected = []
        while not queue.empty():
            event = await queue.get()
            collected.append(event)

        assert len(collected) == 4
        # Reconstruct text
        reconstructed = "".join(
            json.loads(e["data"])["content"] for e in collected
        )
        assert reconstructed == text

    @pytest.mark.asyncio
    async def test_emit_chunks_empty_text(self):
        """Should handle empty text gracefully."""
        queue = asyncio.Queue()

        chunks_emitted = await ChunkEmitter.emit_chunks(
            text="",
            queue=queue,
        )

        assert chunks_emitted == 0
        assert queue.empty()

    @pytest.mark.asyncio
    async def test_emit_text_as_chunks_returns_original(self):
        """emit_text_as_chunks should return original text."""
        queue = asyncio.Queue()
        text = "Original text content"

        result = await ChunkEmitter.emit_text_as_chunks(
            text=text,
            queue=queue,
        )

        assert result == text
        assert not queue.empty()


class TestSaptivaStreamer:
    """Tests for SaptivaStreamer service (Phase 5.2)."""

    def test_extract_content_from_response_none(self):
        """None response should return empty string."""
        content, has_reasoning = SaptivaStreamer.extract_content_from_response(None)
        assert content == ""
        assert has_reasoning is False

    def test_extract_content_from_response_string(self):
        """String response should be returned as-is."""
        content, has_reasoning = SaptivaStreamer.extract_content_from_response(
            "Direct string response"
        )
        assert content == "Direct string response"
        assert has_reasoning is False

    def test_extract_content_from_response_dict_style(self):
        """Should extract content from dict-style choices."""

        class MockResponse:
            choices = [
                {"message": {"content": "Hello from dict"}}
            ]

        content, has_reasoning = SaptivaStreamer.extract_content_from_response(
            MockResponse()
        )
        assert content == "Hello from dict"
        assert has_reasoning is False

    def test_extract_content_from_response_reasoning_fallback(self):
        """Should fall back to reasoning_content if content is empty."""

        class MockResponse:
            choices = [
                {"message": {"content": "", "reasoning_content": "Reasoning response"}}
            ]

        content, has_reasoning = SaptivaStreamer.extract_content_from_response(
            MockResponse()
        )
        assert content == "Reasoning response"
        assert has_reasoning is True

    def test_extract_content_from_response_no_choices(self):
        """Should handle response with no choices."""

        class MockResponse:
            choices = []

        content, has_reasoning = SaptivaStreamer.extract_content_from_response(
            MockResponse()
        )
        assert content == ""
        assert has_reasoning is False

    def test_extract_content_from_response_object_style(self):
        """Should extract content from object-style choices."""

        class MockMessage:
            content = "Object style content"
            reasoning_content = None

        class MockChoice:
            message = MockMessage()

        class MockResponse:
            choices = [MockChoice()]

        content, has_reasoning = SaptivaStreamer.extract_content_from_response(
            MockResponse()
        )
        assert content == "Object style content"
        assert has_reasoning is False

    def test_extract_chunk_content_dict_style(self):
        """Should extract content from dict-style streaming chunk."""

        class MockChunk:
            choices = [{"delta": {"content": "chunk text"}}]

        content = SaptivaStreamer.extract_chunk_content(MockChunk())
        assert content == "chunk text"

    def test_extract_chunk_content_empty_delta(self):
        """Should handle empty delta gracefully."""

        class MockChunk:
            choices = [{"delta": {}}]

        content = SaptivaStreamer.extract_chunk_content(MockChunk())
        assert content == ""

    def test_extract_chunk_content_none(self):
        """Should handle None chunk."""
        content = SaptivaStreamer.extract_chunk_content(None)
        assert content == ""

    def test_extract_chunk_content_no_choices(self):
        """Should handle chunk with no choices."""

        class MockChunk:
            choices = []

        content = SaptivaStreamer.extract_chunk_content(MockChunk())
        assert content == ""

    def test_extract_chunk_content_object_style(self):
        """Should extract content from object-style chunk."""

        class MockDelta:
            content = "object delta content"

        class MockChoice:
            delta = MockDelta()

        class MockChunk:
            choices = [MockChoice()]

        content = SaptivaStreamer.extract_chunk_content(MockChunk())
        assert content == "object delta content"


class TestStreamerConfig:
    """Tests for StreamerConfig dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        config = StreamerConfig(model="test-model")

        assert config.model == "test-model"
        assert config.temperature == 0.7
        assert config.max_tokens == 3000
        assert config.timeout == 120

    def test_custom_values(self):
        """Should accept custom values."""
        config = StreamerConfig(
            model="custom-model",
            temperature=0.3,
            max_tokens=1000,
            timeout=60,
        )

        assert config.model == "custom-model"
        assert config.temperature == 0.3
        assert config.max_tokens == 1000
        assert config.timeout == 60


class TestCompletionResult:
    """Tests for CompletionResult dataclass."""

    def test_basic_creation(self):
        """Should create result with required fields."""
        result = CompletionResult(
            content="Test content",
            has_reasoning=False,
        )

        assert result.content == "Test content"
        assert result.has_reasoning is False
        assert result.raw_response is None

    def test_with_raw_response(self):
        """Should store raw response if provided."""
        raw = {"id": "test", "choices": []}
        result = CompletionResult(
            content="Test",
            has_reasoning=True,
            raw_response=raw,
        )

        assert result.raw_response == raw
        assert result.has_reasoning is True


class TestPhase5Integration:
    """Integration tests for Phase 5 services."""

    @pytest.mark.asyncio
    async def test_chunker_and_streamer_work_together(self):
        """ChunkEmitter and SaptivaStreamer should work in typical flow."""
        # Simulate extracting response and chunking it
        class MockResponse:
            choices = [
                {"message": {"content": "This is a test response from Saptiva."}}
            ]

        # Extract content
        content, _ = SaptivaStreamer.extract_content_from_response(MockResponse())
        assert content == "This is a test response from Saptiva."

        # Chunk it
        queue = asyncio.Queue()
        chunks = await ChunkEmitter.emit_chunks(content, queue, chunk_size=10)

        assert chunks > 0
        # Verify reconstruction
        reconstructed = ""
        while not queue.empty():
            event = await queue.get()
            reconstructed += json.loads(event["data"])["content"]

        assert reconstructed == content

    def test_chunk_event_format_matches_streaming_handler(self):
        """ChunkEmitter events should match streaming_handler format."""
        event = ChunkEmitter.build_chunk_event("test content")

        # Must match the format expected by SSE consumers
        assert event["event"] == "chunk"
        data = json.loads(event["data"])
        assert "content" in data
        assert data["content"] == "test content"


# ============================================================================
# PHASE 5.4 TESTS: AuditResponseBuilder
# ============================================================================


class TestAuditResponseBuilder:
    """Tests for AuditResponseBuilder service (Phase 5.4)."""

    def test_extract_summary(self):
        """Should extract summary from MCP result."""
        mcp_result = {
            "total_findings": 10,
            "findings_by_severity": {"critical": 2, "high": 3, "medium": 4, "low": 1},
            "findings_by_category": {"grammar": 5, "format": 5},
            "validation_duration_ms": 2000,
        }

        summary = AuditResponseBuilder.extract_summary(mcp_result)

        assert summary.total_findings == 10
        assert summary.critical == 2
        assert summary.high == 3
        assert summary.medium == 4
        assert summary.low == 1
        assert summary.duration_ms == 2000
        assert summary.findings_by_category == {"grammar": 5, "format": 5}

    def test_extract_summary_empty_result(self):
        """Should handle empty MCP result gracefully."""
        summary = AuditResponseBuilder.extract_summary({})

        assert summary.total_findings == 0
        assert summary.critical == 0
        assert summary.duration_ms == 0

    def test_build_validation_complete_event(self):
        """Should build correct validation event structure."""
        mcp_result = {
            "job_id": "job-123",
            "status": "completed",
            "total_findings": 5,
            "findings_by_severity": {"high": 5},
            "findings_by_category": {"grammar": 5},
            "top_findings": [{"id": 1}],
            "policy_id": "policy-1",
            "policy_name": "Test Policy",
            "pdf_report_path": "/reports/test.pdf",
            "validation_duration_ms": 1500,
        }

        event = AuditResponseBuilder.build_validation_complete_event(
            mcp_result, "test.pdf"
        )

        assert event["type"] == "validation_complete"
        assert event["job_id"] == "job-123"
        assert event["status"] == "completed"
        assert event["filename"] == "test.pdf"
        assert event["duration_ms"] == 1500
        assert event["summary"]["total_findings"] == 5
        assert event["attachments"]["pdf_report_path"] == "/reports/test.pdf"

    def test_build_result_content_with_critical(self):
        """Should include critical warning in content."""
        summary = AuditSummary(
            total_findings=3,
            critical=2,
            high=1,
            medium=0,
            low=0,
            duration_ms=1000,
        )

        content = AuditResponseBuilder.build_result_content(summary)

        assert "ATENCIÓN" in content
        assert "2" in content

    def test_build_result_content_perfect_document(self):
        """Should show approval for zero findings."""
        summary = AuditSummary(
            total_findings=0,
            critical=0,
            high=0,
            medium=0,
            low=0,
            duration_ms=500,
        )

        content = AuditResponseBuilder.build_result_content(summary)

        assert "Documento aprobado" in content
        assert "estándares de calidad" in content

    def test_build_result_content_with_executive_summary(self):
        """Should include executive summary when provided."""
        summary = AuditSummary(
            total_findings=1,
            critical=0,
            high=0,
            medium=1,
            low=0,
            duration_ms=800,
        )

        content = AuditResponseBuilder.build_result_content(
            summary, executive_summary_md="## Executive Summary\nAll good!"
        )

        assert "Executive Summary" in content
        assert "All good!" in content

    def test_build_audit_artifact(self):
        """Should build correct artifact structure."""
        validation_event = {
            "policy_id": "pol-1",
            "policy_name": "Test Policy",
            "attachments": {"pdf_report_path": "/test.pdf"},
            "validation_report_id": "report-123",
            "summary": {
                "total_findings": 3,
                "findings_by_severity": {"high": 1, "medium": 2},
            },
        }
        findings = [
            {"category": "grammar", "message": "Error 1"},
            {"category": "grammar", "message": "Error 2"},
            {"category": "format", "message": "Error 3"},
        ]

        artifact = AuditResponseBuilder.build_audit_artifact(
            filename="doc.pdf",
            validation_event=validation_event,
            findings=findings,
        )

        assert artifact["type"] == "audit_report_ui"
        assert artifact["doc_name"] == "doc.pdf"
        assert artifact["metadata"]["filename"] == "doc.pdf"
        assert artifact["metadata"]["policy_used"]["id"] == "pol-1"
        assert len(artifact["categories"]["grammar"]) == 2
        assert len(artifact["categories"]["format"]) == 1

    def test_build_message_metadata(self):
        """Should build correct message metadata structure."""
        validation_event = {
            "job_id": "job-123",
            "attachments": {"pdf_report_path": "/report.pdf"},
            "validation_report_id": "val-123",
        }
        artifact = {
            "metadata": {"report_pdf_url": "/report.pdf"},
        }

        metadata = AuditResponseBuilder.build_message_metadata(
            document_id="doc-123",
            filename="test.pdf",
            validation_event=validation_event,
            artifact=artifact,
        )

        assert metadata["audit_completed"] is True
        assert metadata["document_id"] == "doc-123"
        assert metadata["filename"] == "test.pdf"
        assert metadata["job_id"] == "job-123"
        assert metadata["validation_report_id"] == "val-123"
        assert metadata["report_pdf_url"] == "/report.pdf"

    def test_build_start_event(self):
        """Should build correct start content."""
        content = AuditResponseBuilder.build_start_event("document.pdf")
        assert "document.pdf" in content
        assert "Analizando" in content

    def test_build_meta_event(self):
        """Should build correct meta event structure."""
        event = AuditResponseBuilder.build_meta_event(
            chat_id="chat-123",
            user_message_id="msg-123",
            model="saptiva-turbo",
            document_id="doc-123",
            filename="test.pdf",
        )

        assert event["event"] == "meta"
        data = json.loads(event["data"])
        assert data["chat_id"] == "chat-123"
        assert data["audit_streaming"] is True
        assert data["filename"] == "test.pdf"

    def test_build_error_event(self):
        """Should build correct error event structure."""
        event = AuditResponseBuilder.build_error_event(
            error_type="document_not_found",
            message="File not found",
            details="Check path",
        )

        assert event["event"] == "error"
        data = json.loads(event["data"])
        assert data["error"] == "document_not_found"
        assert data["message"] == "File not found"
        assert data["details"] == "Check path"


class TestAuditSummary:
    """Tests for AuditSummary dataclass."""

    def test_basic_creation(self):
        """Should create summary with all fields."""
        summary = AuditSummary(
            total_findings=10,
            critical=1,
            high=2,
            medium=3,
            low=4,
            duration_ms=1500,
            findings_by_category={"grammar": 5, "format": 5},
        )

        assert summary.total_findings == 10
        assert summary.critical == 1
        assert summary.high == 2
        assert summary.medium == 3
        assert summary.low == 4
        assert summary.duration_ms == 1500

    def test_default_findings_by_category(self):
        """Should default to empty dict for findings_by_category."""
        summary = AuditSummary(
            total_findings=0,
            critical=0,
            high=0,
            medium=0,
            low=0,
            duration_ms=0,
        )
        assert summary.findings_by_category == {}


class TestPhase54Integration:
    """Integration tests for Phase 5.4 services."""

    def test_audit_builder_process_mcp_result(self):
        """Should process MCP result into complete audit response."""
        mcp_result = {
            "job_id": "job-123",
            "status": "completed",
            "total_findings": 3,
            "findings_by_severity": {"critical": 1, "medium": 2},
            "findings_by_category": {"grammar": 2, "format": 1},
            "top_findings": [
                {"category": "grammar", "message": "Error 1"},
                {"category": "grammar", "message": "Error 2"},
                {"category": "format", "message": "Error 3"},
            ],
            "validation_duration_ms": 2000,
        }

        result = AuditResponseBuilder.process_mcp_result(
            mcp_result=mcp_result,
            document_id="doc-123",
            user_id="user-123",
            filename="test.pdf",
        )

        assert result.success is True
        assert len(result.content) > 0
        assert result.validation_event is not None
        assert result.artifact is not None
        assert "ATENCIÓN" in result.content  # Critical finding warning


# =============================================================================
# REFACTOR-001 Phase 7: Tests for newly extracted services
# =============================================================================

from src.services.streaming import (
    FileIngestionService,
    AuditDocumentResolver,
    ResolvedDocument,
    ResolutionError,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestAuditDocumentResolver:
    """Tests for AuditDocumentResolver - Phase 7."""

    def test_extract_filename_from_command_basic(self):
        """Should extract filename from audit command."""
        filename = AuditDocumentResolver.extract_filename_from_command(
            "Auditar archivo: documento.pdf"
        )
        assert filename == "documento.pdf"

    def test_extract_filename_from_command_with_spaces(self):
        """Should handle filenames with spaces."""
        filename = AuditDocumentResolver.extract_filename_from_command(
            "Auditar archivo: mi documento importante.pdf"
        )
        assert filename == "mi documento importante.pdf"

    def test_extract_filename_from_command_with_extra_whitespace(self):
        """Should trim extra whitespace."""
        filename = AuditDocumentResolver.extract_filename_from_command(
            "  Auditar archivo:   archivo.pdf  "
        )
        assert filename == "archivo.pdf"

    @pytest.mark.asyncio
    async def test_find_document_by_filename_empty_ids(self):
        """Should return None when document_ids is empty."""
        result = await AuditDocumentResolver.find_document_by_filename(
            filename="test.pdf",
            document_ids=[],
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_find_document_by_filename_none_ids(self):
        """Should return None when document_ids is None."""
        result = await AuditDocumentResolver.find_document_by_filename(
            filename="test.pdf",
            document_ids=None,
        )
        assert result is None

    def test_materialize_pdf_local_file_exists(self):
        """Should return local path when file exists."""
        with patch("pathlib.Path.exists", return_value=True):
            mock_doc = MagicMock()
            mock_doc.minio_key = "/tmp/existing_file.pdf"

            path, is_temp, error = AuditDocumentResolver.materialize_pdf(mock_doc)

            assert error is None
            assert is_temp is False

    def test_materialize_pdf_no_storage(self):
        """Should return error when MinIO storage is unavailable."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch(
                "src.services.streaming.audit_document_resolver.get_minio_storage",
                return_value=None,
            ):
                mock_doc = MagicMock()
                mock_doc.minio_key = "/tmp/missing_file.pdf"

                path, is_temp, error = AuditDocumentResolver.materialize_pdf(mock_doc)

                assert path is None
                assert error is not None
                assert error.error_code == "storage_unavailable"

    def test_resolution_error_dataclass(self):
        """Should create ResolutionError with correct fields."""
        error = ResolutionError(
            error_code="document_not_found",
            error_message="No se encontró el archivo",
        )
        assert error.error_code == "document_not_found"
        assert error.error_message == "No se encontró el archivo"

    @pytest.mark.asyncio
    async def test_resolve_document_not_found(self):
        """Should return error when document is not found."""
        with patch.object(
            AuditDocumentResolver,
            "find_document_by_filename",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resolved, error = await AuditDocumentResolver.resolve(
                message="Auditar archivo: no_existe.pdf",
                document_ids=["doc-123"],
            )

            assert resolved is None
            assert error is not None
            assert error.error_code == "document_not_found"
            assert "no_existe.pdf" in error.error_message


class TestFileIngestionService:
    """Tests for FileIngestionService - Phase 7."""

    @pytest.mark.asyncio
    async def test_ingest_files_if_needed_no_files(self):
        """Should return True immediately when no files provided."""
        result = await FileIngestionService.ingest_files_if_needed(
            session_id="session-123",
            file_ids=[],
            background_tasks=MagicMock(),
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_ingest_files_if_needed_no_background_tasks(self):
        """Should return True when background_tasks is None."""
        result = await FileIngestionService.ingest_files_if_needed(
            session_id="session-123",
            file_ids=["doc-1", "doc-2"],
            background_tasks=None,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_check_all_documents_ready_empty_list(self):
        """Should return True for empty file list."""
        result = await FileIngestionService._check_all_documents_ready([])
        assert result is True

    @pytest.mark.asyncio
    async def test_ingest_files_already_ready(self):
        """Should skip ingestion when all documents are already READY."""
        with patch.object(
            FileIngestionService,
            "_check_all_documents_ready",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await FileIngestionService.ingest_files_if_needed(
                session_id="session-123",
                file_ids=["doc-1"],
                background_tasks=MagicMock(),
            )
            assert result is True

    def test_service_constants(self):
        """Should have correct default constants."""
        assert FileIngestionService.DEFAULT_MAX_WAIT_SECONDS == 30
        assert FileIngestionService.DEFAULT_POLL_INTERVAL == 0.5
        assert FileIngestionService.MONGODB_PROPAGATION_DELAY == 0.1


class TestPhase7Integration:
    """Integration tests for Phase 7 services working together."""

    def test_audit_resolver_command_variations(self):
        """Should handle various audit command formats."""
        test_cases = [
            ("Auditar archivo: test.pdf", "test.pdf"),
            ("Auditar archivo:test.pdf", "test.pdf"),
            ("  Auditar archivo: test.pdf  ", "test.pdf"),
            ("Auditar archivo: archivo con espacios.pdf", "archivo con espacios.pdf"),
        ]

        for command, expected in test_cases:
            result = AuditDocumentResolver.extract_filename_from_command(command)
            assert result == expected, f"Failed for: {command}"
