"""
Message Persistence Service.

Extracted from streaming_handler.py for better testability.
Handles preparation and persistence of assistant messages with metadata.

REFACTOR-001: Phase 3 extraction.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


class MessagePersistenceService:
    """
    Service for persisting assistant messages with proper metadata.

    Responsibilities:
        - Normalize bank chart/clarification data for persistence
        - Build assistant message metadata
        - Coordinate with ChatService for message saving
        - Handle cache invalidation
    """

    @staticmethod
    def build_assistant_metadata(
        *,
        streaming: bool = True,
        document_ids: Optional[List[str]] = None,
        doc_warnings: Optional[List[str]] = None,
        artifact_id: Optional[str] = None,
        latency_ms: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Build metadata dictionary for assistant message persistence.

        Args:
            streaming: Whether this is a streaming response
            document_ids: List of attached document IDs
            doc_warnings: List of document processing warnings
            artifact_id: Optional artifact ID
            latency_ms: Response latency in milliseconds (for dashboard metrics)

        Returns:
            Metadata dictionary for message persistence
        """
        metadata: Dict[str, Any] = {
            "streaming": streaming,
            "has_documents": bool(document_ids),
            "document_warnings": doc_warnings if doc_warnings else None,
        }

        # Add latency for dashboard metrics tracking
        if latency_ms is not None:
            metadata["latency_ms"] = latency_ms

        if artifact_id:
            metadata["tool_invocations"] = [
                {
                    "tool_name": "create_artifact",
                    "result": {"id": artifact_id},
                }
            ]

        return metadata

    @staticmethod
    def build_done_event(
        *,
        message_id: str,
        chat_id: str,
        content: str,
    ) -> Dict[str, Any]:
        """
        Build the 'done' SSE event for stream completion.

        Args:
            message_id: ID of the persisted assistant message
            chat_id: ID of the chat session
            content: Full response content

        Returns:
            SSE event dictionary
        """
        return {
            "event": "done",
            "data": json.dumps(
                {
                    "message_id": message_id,
                    "chat_id": chat_id,
                    "content": content,
                }
            ),
        }

    @staticmethod
    def build_error_event(
        *,
        error_message: str,
        error_type: str,
        recoverable: bool = True,
    ) -> Dict[str, Any]:
        """
        Build an error SSE event.

        Args:
            error_message: Human-readable error message
            error_type: Exception type name
            recoverable: Whether the error is recoverable

        Returns:
            SSE event dictionary
        """
        return {
            "event": "error",
            "data": json.dumps(
                {
                    "error": error_message,
                    "type": error_type,
                    "recoverable": recoverable,
                }
            ),
        }

    @staticmethod
    def build_error_content(error: Exception) -> str:
        """
        Build user-friendly error content for persistence.

        Args:
            error: The exception that occurred

        Returns:
            Error message content for the assistant message
        """
        return (
            f"❌ Error al procesar la solicitud: {str(error)[:200]}\n\n"
            f"Por favor, intenta nuevamente o contacta al equipo de soporte si el error persiste."
        )

    @staticmethod
    def build_error_metadata(error: Exception) -> Dict[str, Any]:
        """
        Build metadata for error messages.

        Args:
            error: The exception that occurred

        Returns:
            Metadata dictionary for error message
        """
        return {
            "error": True,
            "error_type": type(error).__name__,
            "error_message": str(error)[:500],
        }
