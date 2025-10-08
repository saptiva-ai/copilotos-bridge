"""
Chat Strategy Pattern - Pluggable handlers for different chat scenarios.

Implements Strategy Pattern to handle:
- Simple chat (kill switch active)
- Coordinated chat (with research coordinator)
- Future: Streaming chat, multi-modal chat, etc.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import structlog

from ..core.telemetry import trace_span
from ..services.chat_service import ChatService
from ..services.document_service import DocumentService
from ..services.text_sanitizer import sanitize_response_content
from ..services.saptiva_client import get_saptiva_client
from .chat_context import ChatContext, ChatProcessingResult, MessageMetadata


logger = structlog.get_logger(__name__)


class ChatStrategy(ABC):
    """
    Abstract base class for chat processing strategies.

    Defines the interface that all concrete strategies must implement.
    """

    def __init__(self, chat_service: ChatService):
        self.chat_service = chat_service

    @abstractmethod
    async def process(self, context: ChatContext) -> ChatProcessingResult:
        """
        Process a chat message using this strategy.

        Args:
            context: ChatContext with all request information.

        Returns:
            ChatProcessingResult with response and metadata.
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return strategy name for logging/metadata."""
        pass


class SimpleChatStrategy(ChatStrategy):
    """
    Simple chat strategy - direct Saptiva inference.

    This is the main strategy for regular chat interactions.
    Supports document context but no deep research or web search.
    """

    def get_strategy_name(self) -> str:
        return "simple"

    async def process(self, context: ChatContext) -> ChatProcessingResult:
        """
        Process message with Saptiva, optionally including document context.

        Args:
            context: ChatContext with request data and optional documents.

        Returns:
            ChatProcessingResult with AI response.
        """
        start_time = time.time()

        logger.info(
            "Processing chat with simple strategy",
            user_id=context.user_id,
            session_id=context.session_id,
            model=context.model,
            has_documents=bool(context.document_ids)
        )

        # V1: Retrieve and format documents from Redis cache
        document_context = None
        if context.document_ids:
            async with trace_span("retrieve_documents_from_cache", {
                "document_count": len(context.document_ids)
            }):
                # Retrieve text from Redis cache with ownership validation
                doc_texts = await DocumentService.get_document_text_from_cache(
                    document_ids=context.document_ids,
                    user_id=context.user_id
                )

                if doc_texts:
                    document_context = DocumentService.extract_content_for_rag_from_cache(
                        doc_texts=doc_texts,
                        max_chars_per_doc=8000
                    )
                    logger.info(
                        "Retrieved documents for RAG from cache",
                        document_count=len(doc_texts),
                        context_length=len(document_context)
                    )
                else:
                    logger.warning(
                        "No accessible documents found in cache",
                        requested_ids=context.document_ids,
                        user_id=context.user_id
                    )

        async with trace_span("simple_chat_inference"):
            # Use ChatService to process with Saptiva
            coordinated_response = await self.chat_service.process_with_saptiva(
                message=context.message,
                model=context.model,
                user_id=context.user_id,
                chat_id=context.session_id or "",
                tools_enabled=context.tools_enabled,
                document_context=document_context
            )

        # Extract response content from SaptivaResponse object
        response_obj = coordinated_response.get("response")
        if hasattr(response_obj, 'choices') and len(response_obj.choices) > 0:
            # Extract text from Pydantic SaptivaResponse object
            response_content = response_obj.choices[0].get("message", {}).get("content", "")
        else:
            response_content = ""

        # Sanitize response
        sanitized_content = sanitize_response_content(response_content)

        # Build metadata
        metadata = MessageMetadata(
            message_id=coordinated_response.get("message_id", ""),
            chat_id=context.session_id or "",
            user_message_id="",  # Set by caller
            assistant_message_id=coordinated_response.get("message_id"),
            model_used=context.model,
            tokens_used=coordinated_response.get("tokens"),
            latency_ms=coordinated_response.get("processing_time_ms"),
            decision_metadata=coordinated_response.get("decision")
        )

        processing_time = (time.time() - start_time) * 1000

        return ChatProcessingResult(
            content=response_content,
            sanitized_content=sanitized_content,
            metadata=metadata,
            processing_time_ms=processing_time,
            strategy_used=self.get_strategy_name(),
            research_triggered=False,
            session_updated=False
        )


class ChatStrategyFactory:
    """
    Factory for creating appropriate chat strategy.

    For now, always returns SimpleChatStrategy.
    Deep Research and Web Search are handled separately.
    """

    @staticmethod
    def create_strategy(context: ChatContext, chat_service: ChatService) -> ChatStrategy:
        """
        Create chat strategy.

        Args:
            context: ChatContext with request info.
            chat_service: ChatService instance for processing.

        Returns:
            SimpleChatStrategy for all chat interactions.
        """
        logger.debug("Creating SimpleChatStrategy")
        return SimpleChatStrategy(chat_service)
