"""
Unit tests for MessagePersistenceService.

Tests cover:
- Building assistant metadata
- Chart data normalization
- Clarification normalization for history
- Event building (done, error)
- Error content and metadata building
"""

import json
import pytest
from unittest.mock import MagicMock

from src.services.streaming.message_persistence import MessagePersistenceService


@pytest.mark.unit
class TestBuildAssistantMetadata:
    """Tests for build_assistant_metadata method."""

    def test_minimal_metadata(self):
        """Should build minimal metadata."""
        metadata = MessagePersistenceService.build_assistant_metadata()

        assert metadata["streaming"] is True
        assert metadata["has_documents"] is False
        assert metadata["document_warnings"] is None

    def test_with_document_ids(self):
        """Should mark has_documents when IDs provided."""
        metadata = MessagePersistenceService.build_assistant_metadata(
            document_ids=["doc-1", "doc-2"]
        )

        assert metadata["has_documents"] is True

    def test_with_doc_warnings(self):
        """Should include document warnings."""
        warnings = ["Password protected", "Large file"]
        metadata = MessagePersistenceService.build_assistant_metadata(
            doc_warnings=warnings
        )

        assert metadata["document_warnings"] == warnings

    def test_streaming_flag(self):
        """Should set streaming flag correctly."""
        metadata = MessagePersistenceService.build_assistant_metadata(streaming=False)

        assert metadata["streaming"] is False

    def test_combined_metadata(self):
        """Should combine all metadata fields."""
        metadata = MessagePersistenceService.build_assistant_metadata(
            streaming=True,
            document_ids=["doc-1"],
            doc_warnings=["Large file"],
        )

        assert metadata["streaming"] is True
        assert metadata["has_documents"] is True
        assert metadata["document_warnings"] == ["Large file"]


@pytest.mark.unit
class TestNormalizeChartData:
    """Tests for _normalize_chart_data method."""

    def test_dict_passthrough(self):
        """Should return dict unchanged."""
        data = {"metric": "IMOR", "value": 1.5}
        result = MessagePersistenceService._normalize_chart_data(data)

        assert result == data

    def test_pydantic_model(self):
        """Should call model_dump for Pydantic models."""
        mock_model = MagicMock()
        mock_model.model_dump.return_value = {"field": "value"}

        result = MessagePersistenceService._normalize_chart_data(mock_model)

        mock_model.model_dump.assert_called_once_with(mode="json")
        assert result == {"field": "value"}

    def test_empty_data(self):
        """Should handle empty/None data."""
        assert MessagePersistenceService._normalize_chart_data(None) == {}
        assert MessagePersistenceService._normalize_chart_data({}) == {}

    def test_other_iterable(self):
        """Should convert other iterables to dict."""

        class DictLike:
            def __iter__(self):
                return iter([("a", 1), ("b", 2)])

        result = MessagePersistenceService._normalize_chart_data(DictLike())
        assert result == {"a": 1, "b": 2}


@pytest.mark.unit
class TestNormalizeClarificationForHistory:
    """Tests for _normalize_clarification_for_history method."""

    def test_preserves_existing_options(self):
        """Should preserve existing options array."""
        data = {
            "type": "clarification",
            "message": "Select option",
            "options": [{"id": "A"}, {"id": "B"}],
        }

        result = MessagePersistenceService._normalize_clarification_for_history(data)

        assert result["options"] == [{"id": "A"}, {"id": "B"}]

    def test_converts_legacy_clarifications(self):
        """Should convert legacy clarifications format to options."""
        data = {
            "type": "clarification",
            "clarifications": [
                {"field": "metric", "question": "Which metric?", "reason": "Required"},
            ],
        }

        result = MessagePersistenceService._normalize_clarification_for_history(data)

        assert "options" in result
        assert len(result["options"]) == 1
        assert result["options"][0]["id"] == "metric"
        assert result["options"][0]["label"] == "Which metric?"
        assert result["options"][0]["description"] == "Required"

    def test_creates_clarifications_array(self):
        """Should create clarifications array for frontend compatibility."""
        data = {
            "type": "clarification",
            "message": "Please choose",
            "options": [
                {"id": "opt1", "label": "Option 1"},
                {"id": "opt2", "label": "Option 2"},
            ],
        }

        result = MessagePersistenceService._normalize_clarification_for_history(data)

        assert "clarifications" in result
        assert len(result["clarifications"]) == 1
        assert result["clarifications"][0]["field"] == "selected_option"
        assert result["clarifications"][0]["question"] == "Please choose"
        assert len(result["clarifications"][0]["options"]) == 2

    def test_frontend_options_format(self):
        """Should create frontend-compatible options format."""
        data = {
            "type": "clarification",
            "message": "Select",
            "options": [{"id": "IMOR", "label": "Morosidad"}],
        }

        result = MessagePersistenceService._normalize_clarification_for_history(data)

        frontend_opts = result["clarifications"][0]["options"]
        assert frontend_opts[0]["value"] == "IMOR"
        assert frontend_opts[0]["label"] == "Morosidad"

    def test_preserves_original_data(self):
        """Should not modify original data."""
        original = {
            "type": "clarification",
            "message": "Test",
            "options": [{"id": "A"}],
            "extra_field": "preserved",
        }

        result = MessagePersistenceService._normalize_clarification_for_history(original)

        assert result["extra_field"] == "preserved"

    def test_handles_missing_fields(self):
        """Should handle clarifications with missing fields."""
        data = {
            "type": "clarification",
            "clarifications": [
                {"question": "What?"},  # Missing field
                {"field": "test"},  # Missing question
            ],
        }

        result = MessagePersistenceService._normalize_clarification_for_history(data)

        # Should use fallback values
        assert len(result["options"]) == 2


@pytest.mark.unit
class TestBuildDoneEvent:
    """Tests for build_done_event method."""

    def test_event_structure(self):
        """Should build correct event structure."""
        event = MessagePersistenceService.build_done_event(
            message_id="msg-123",
            chat_id="chat-456",
            content="Full response here",
        )

        assert event["event"] == "done"
        assert "data" in event

    def test_event_data_content(self):
        """Should include all data fields."""
        event = MessagePersistenceService.build_done_event(
            message_id="msg-123",
            chat_id="chat-456",
            content="Full response here",
        )

        data = json.loads(event["data"])

        assert data["message_id"] == "msg-123"
        assert data["chat_id"] == "chat-456"
        assert data["content"] == "Full response here"


@pytest.mark.unit
class TestBuildErrorEvent:
    """Tests for build_error_event method."""

    def test_event_structure(self):
        """Should build correct error event structure."""
        event = MessagePersistenceService.build_error_event(
            error_message="Something went wrong",
            error_type="ValueError",
        )

        assert event["event"] == "error"
        assert "data" in event

    def test_error_data_content(self):
        """Should include error details."""
        event = MessagePersistenceService.build_error_event(
            error_message="Database error",
            error_type="ConnectionError",
            recoverable=True,
        )

        data = json.loads(event["data"])

        assert data["error"] == "Database error"
        assert data["type"] == "ConnectionError"
        assert data["recoverable"] is True

    def test_non_recoverable_error(self):
        """Should mark non-recoverable errors."""
        event = MessagePersistenceService.build_error_event(
            error_message="Fatal error",
            error_type="SystemError",
            recoverable=False,
        )

        data = json.loads(event["data"])
        assert data["recoverable"] is False


@pytest.mark.unit
class TestBuildErrorContent:
    """Tests for build_error_content method."""

    def test_includes_error_message(self):
        """Should include error message."""
        error = ValueError("Invalid input")
        content = MessagePersistenceService.build_error_content(error)

        assert "Invalid input" in content
        assert "❌" in content

    def test_truncates_long_errors(self):
        """Should truncate very long error messages."""
        error = Exception("x" * 500)
        content = MessagePersistenceService.build_error_content(error)

        # Should not include full 500 chars
        assert len(content) < 700

    def test_includes_retry_instruction(self):
        """Should include retry instruction."""
        error = Exception("Error")
        content = MessagePersistenceService.build_error_content(error)

        assert "intenta nuevamente" in content.lower() or "soporte" in content.lower()


@pytest.mark.unit
class TestBuildErrorMetadata:
    """Tests for build_error_metadata method."""

    def test_includes_error_flag(self):
        """Should set error flag to True."""
        error = ValueError("Test error")
        metadata = MessagePersistenceService.build_error_metadata(error)

        assert metadata["error"] is True

    def test_includes_error_type(self):
        """Should include exception type name."""
        error = TypeError("Wrong type")
        metadata = MessagePersistenceService.build_error_metadata(error)

        assert metadata["error_type"] == "TypeError"

    def test_includes_error_message(self):
        """Should include error message."""
        error = RuntimeError("Runtime issue")
        metadata = MessagePersistenceService.build_error_metadata(error)

        assert metadata["error_message"] == "Runtime issue"

    def test_truncates_long_message(self):
        """Should truncate very long error messages."""
        error = Exception("x" * 1000)
        metadata = MessagePersistenceService.build_error_metadata(error)

        assert len(metadata["error_message"]) <= 500


@pytest.mark.unit
class TestMetadataIntegration:
    """Integration tests for metadata building."""

    def test_full_document_scenario(self):
        """Should handle full document scenario correctly."""
        metadata = MessagePersistenceService.build_assistant_metadata(
            streaming=True,
            document_ids=["doc-1"],
        )

        assert metadata["streaming"] is True
        assert metadata["has_documents"] is True
