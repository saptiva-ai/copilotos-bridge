"""
Chat Response Builder - Builder Pattern Implementation.

Provides a fluent API for constructing complex chat responses
with all required metadata and optional fields.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi.responses import JSONResponse

from .chat_context import ChatProcessingResult, MessageMetadata


class ChatResponseBuilder:
    """
    Builder for constructing ChatResponse JSON.

    Uses Builder Pattern to provide fluent API for complex object construction.

    Example:
        response = (ChatResponseBuilder()
            .with_chat_id("chat-123")
            .with_message("AI response here")
            .with_model("Saptiva Turbo")
            .with_latency(234.5)
            .build())
    """

    def __init__(self):
        self._data: Dict[str, Any] = {
            "type": "chat",
            "response": "",
            "chat_id": None,
            "message_id": None,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._metadata: Dict[str, Any] = {}
        self._headers: Dict[str, str] = {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }

    def with_chat_id(self, chat_id: str) -> 'ChatResponseBuilder':
        """Set chat ID."""
        self._data["chat_id"] = chat_id
        return self

    def with_message(self, content: str, sanitized: bool = True) -> 'ChatResponseBuilder':
        """Set message content."""
        self._data["response"] = content
        if sanitized:
            self._data["sanitized"] = True
        return self

    def with_message_id(self, message_id: str) -> 'ChatResponseBuilder':
        """Set message ID."""
        self._data["message_id"] = message_id
        return self

    def with_model(self, model: str) -> 'ChatResponseBuilder':
        """Set model used."""
        self._data["model"] = model
        return self

    def with_tokens(self, prompt_tokens: int, completion_tokens: int) -> 'ChatResponseBuilder':
        """Set token usage."""
        self._data["tokens"] = {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": prompt_tokens + completion_tokens
        }
        return self

    def with_latency(self, latency_ms: float) -> 'ChatResponseBuilder':
        """Set processing latency."""
        self._data["latency_ms"] = round(latency_ms, 2)
        return self

    def with_decision(self, decision: Dict[str, Any]) -> 'ChatResponseBuilder':
        """Set decision metadata (for coordinated responses)."""
        self._data["decision"] = decision
        return self

    def with_research_task(self, task_id: str) -> 'ChatResponseBuilder':
        """Set research task ID."""
        self._data["task_id"] = task_id
        self._data["research_triggered"] = True
        return self

    def with_session_title(self, title: str) -> 'ChatResponseBuilder':
        """Set session title (for auto-titling)."""
        self._data["session_title"] = title
        return self

    def with_metadata(self, key: str, value: Any) -> 'ChatResponseBuilder':
        """Add custom metadata."""
        self._metadata[key] = value
        return self

    def with_error(self, error_message: str, error_code: Optional[str] = None) -> 'ChatResponseBuilder':
        """Set error information."""
        self._data["error"] = error_message
        if error_code:
            self._data["error_code"] = error_code
        return self

    def from_processing_result(self, result: ChatProcessingResult) -> 'ChatResponseBuilder':
        """
        Populate builder from a ChatProcessingResult.

        Convenience method to build response from domain model.
        """
        self.with_chat_id(result.metadata.chat_id)
        self.with_message(result.sanitized_content, sanitized=True)
        self.with_message_id(result.metadata.assistant_message_id or "")
        self.with_model(result.metadata.model_used)
        self.with_latency(result.processing_time_ms)

        if result.metadata.tokens_used:
            tokens = result.metadata.tokens_used
            self.with_tokens(
                tokens.get("prompt", 0),
                tokens.get("completion", 0)
            )

        if result.metadata.decision_metadata:
            self.with_decision(result.metadata.decision_metadata)

        if result.task_id:
            self.with_research_task(result.task_id)

        if result.session_title:
            self.with_session_title(result.session_title)

        # Add processing metadata
        self.with_metadata("strategy_used", result.strategy_used)
        self.with_metadata("session_updated", result.session_updated)

        return self

    def build(self) -> JSONResponse:
        """
        Build final JSONResponse.

        Returns:
            JSONResponse with constructed data and headers.
        """
        # Merge metadata into response data
        if self._metadata:
            self._data["metadata"] = self._metadata

        return JSONResponse(
            content=self._data,
            headers=self._headers,
            status_code=200
        )

    def build_error(self, status_code: int = 500) -> JSONResponse:
        """
        Build error response.

        Args:
            status_code: HTTP status code for error.

        Returns:
            JSONResponse with error data.
        """
        return JSONResponse(
            content={
                "error": self._data.get("error", "Unknown error"),
                "error_code": self._data.get("error_code"),
                "timestamp": self._data["timestamp"]
            },
            headers=self._headers,
            status_code=status_code
        )


class StreamingResponseBuilder:
    """
    Builder for streaming responses.

    For future implementation of SSE (Server-Sent Events) streaming.
    """

    def __init__(self):
        self._events: List[Dict[str, Any]] = []

    def add_chunk(self, content: str, is_final: bool = False) -> 'StreamingResponseBuilder':
        """Add a content chunk."""
        self._events.append({
            "type": "content",
            "data": content,
            "is_final": is_final
        })
        return self

    def add_metadata(self, metadata: Dict[str, Any]) -> 'StreamingResponseBuilder':
        """Add metadata event."""
        self._events.append({
            "type": "metadata",
            "data": metadata
        })
        return self

    def build(self):
        """Build streaming response (placeholder for future SSE implementation)."""
        # Future: Return StreamingResponse with SSE events
        raise NotImplementedError("Streaming responses not yet implemented")
