"""
Chat Stream Producer - Encapsulates LLM streaming producer logic.

REFACTOR-001 Phase 6: Extracted from streaming_handler.py to enable unit testing
and separation of concerns.

This service handles:
- Metadata event emission
- Message context building with memory system
- Token budget management
- Standard LLM synthesis with RAG context
- True streaming mode with SaptivaStreamer
"""

from asyncio import CancelledError, Queue
from dataclasses import dataclass
from typing import Any, Dict, Optional

import structlog

from ...domain import ChatContext
from ...models.chat import ChatMessage, ChatSession
from ...services.chat_service import ChatService
from ...services.empty_response_handler import (
    EmptyResponseScenario,
    ensure_non_empty_content,
)
from ...services.saptiva_client import SaptivaClient
from .chunk_emitter import ChunkEmitter
from .saptiva_streamer import SaptivaStreamer
from .token_budget import TokenBudgetManager

logger = structlog.get_logger(__name__)


@dataclass
class ProducerConfig:
    """Configuration for the ChatStreamProducer."""

    model_limit: int = 8192  # Saptiva Turbo limit
    min_tokens: int = 500
    default_max_tokens: int = 3000


@dataclass
class ProducerResult:
    """Result of producer execution."""

    full_response: str = ""
    error: Optional[Exception] = None
    completed: bool = False
    path_taken: str = ""  # "rag_context", "streaming"


@dataclass
class ProducerContext:
    """All context needed by the producer."""

    event_queue: Queue
    context: ChatContext
    chat_session: ChatSession
    user_message: ChatMessage
    saptiva_client: SaptivaClient
    chat_service: ChatService
    system_prompt: str
    model_params: Dict[str, Any]
    document_context: Optional[str] = None


class ChatStreamProducer:
    """
    Producer task for LLM streaming with backpressure support.

    Reads chunks from Saptiva and puts them in queue.
    If queue is full (slow consumer), put() will block, providing backpressure.
    This prevents unbounded memory growth on the server.
    """

    def __init__(self, config: Optional[ProducerConfig] = None):
        """Initialize producer with optional configuration."""
        self.config = config or ProducerConfig()

    async def produce(self, ctx: ProducerContext) -> ProducerResult:
        """
        Execute the producer logic.

        Args:
            ctx: All context needed for production

        Returns:
            ProducerResult with full_response, error, and chart_flow_result
        """
        result = ProducerResult()

        try:
            logger.info(
                "Starting Saptiva stream (producer)",
                model=ctx.context.model,
                user_id=ctx.context.user_id,
                has_document_context=bool(ctx.document_context),
            )

            # Send metadata event first
            await self._emit_metadata_event(ctx)

            # Build message context with memory system
            messages_for_api = await ctx.chat_service.build_message_context_with_memory(
                chat_session=ctx.chat_session,
                current_message=ctx.context.message,
                system_prompt=ctx.system_prompt,
            )

            logger.info(
                "Chat context built with memory system",
                total_messages=len(messages_for_api),
                session_id=str(ctx.chat_session.id),
                memory_enabled=getattr(
                    ctx.chat_service.settings, "memory_enabled", False
                ),
            )

            # Prepare token budget
            token_budget = TokenBudgetManager.prepare_messages_for_api(
                messages=messages_for_api,
                model_limit=self.config.model_limit,
                min_tokens=self.config.min_tokens,
                max_tokens=ctx.model_params.get(
                    "max_tokens", self.config.default_max_tokens
                ),
            )
            dynamic_max_tokens = token_budget.max_tokens

            has_rag_context = bool(ctx.context.document_ids)

            # Execute appropriate response path
            if has_rag_context:
                result = await self._handle_rag_context_path(
                    ctx, result, messages_for_api, dynamic_max_tokens
                )
            else:
                result = await self._handle_streaming_path(
                    ctx, result, messages_for_api, dynamic_max_tokens
                )

            # Signal end of stream
            await ctx.event_queue.put(None)
            result.completed = True

            logger.info(
                "Producer completed successfully",
                response_length=len(result.full_response),
                path_taken=result.path_taken,
            )

        except CancelledError:
            logger.info("Producer cancelled by consumer")
            raise
        except Exception as e:
            logger.error("Producer error", error=str(e), exc_type=type(e).__name__)
            result.error = e
            # Signal error to consumer
            await ctx.event_queue.put(None)

        return result

    async def _emit_metadata_event(self, ctx: ProducerContext) -> None:
        """Emit the initial metadata SSE event."""
        await ctx.event_queue.put(
            {
                "event": "meta",
                "data": json.dumps(
                    {
                        "chat_id": str(ctx.chat_session.id),
                        "user_message_id": str(ctx.user_message.id),
                        "model": ctx.context.model,
                    }
                ),
            }
        )

    async def _handle_rag_context_path(
        self,
        ctx: ProducerContext,
        result: ProducerResult,
        messages_for_api: list,
        dynamic_max_tokens: int,
    ) -> ProducerResult:
        """
        Handle LLM synthesis with RAG context.

        Prefer true streaming for lower TTFB, with non-streaming fallback
        when upstream streaming is unavailable.
        """
        # Prefer true streaming first to reduce time-to-first-token.
        streamed_chunk_count = 0
        streamed_response = ""
        try:
            async for chunk in ctx.saptiva_client.chat_completion_stream(
                messages=messages_for_api,
                model=ctx.context.model,
                temperature=ctx.model_params.get(
                    "temperature", ctx.context.temperature
                ),
                max_tokens=dynamic_max_tokens,
            ):
                content = SaptivaStreamer.extract_chunk_content(chunk)
                if content:
                    await ctx.event_queue.put(ChunkEmitter.build_chunk_event(content))
                    streamed_response += content
                    streamed_chunk_count += 1
        except Exception as stream_err:
            logger.warning(
                "RAG streaming unavailable, falling back to non-streaming",
                error=str(stream_err),
                error_type=type(stream_err).__name__,
            )
            streamed_chunk_count = 0
            streamed_response = ""

        if streamed_chunk_count > 0:
            result.full_response = ensure_non_empty_content(
                streamed_response,
                scenario=EmptyResponseScenario.API_EMPTY_CONTENT,
                model=ctx.context.model,
                has_documents=bool(ctx.context.document_ids),
                document_count=(
                    len(ctx.context.document_ids) if ctx.context.document_ids else 0
                ),
                user_id=ctx.context.user_id,
            )
            logger.info(
                "RAG streaming response extracted",
                chunk_count=streamed_chunk_count,
                response_length=len(result.full_response),
            )
            result.path_taken = "rag_context_streaming"
            return result

        try:
            response = await ctx.saptiva_client.chat_completion(
                messages=messages_for_api,
                model=ctx.context.model,
                temperature=ctx.model_params.get(
                    "temperature", ctx.context.temperature
                ),
                max_tokens=dynamic_max_tokens,
            )
        except Exception as e:
            logger.error(
                "Non-streaming API call failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        # Extract content from response
        response_content, has_reasoning = SaptivaStreamer.extract_content_from_response(
            response
        )

        # Ensure non-empty response
        response_content = ensure_non_empty_content(
            response_content,
            scenario=EmptyResponseScenario.API_EMPTY_CONTENT,
            model=ctx.context.model,
            has_documents=bool(ctx.context.document_ids),
            document_count=(
                len(ctx.context.document_ids) if ctx.context.document_ids else 0
            ),
            user_id=ctx.context.user_id,
        )

        result.full_response = response_content

        logger.info(
            "Non-streaming response extracted",
            response_length=len(result.full_response),
            response_preview=(
                result.full_response[:100] if result.full_response else "(empty)"
            ),
            has_reasoning=has_reasoning,
        )

        # Emit as chunks for uniform frontend handling
        await ChunkEmitter.emit_chunks(
            text=result.full_response,
            queue=ctx.event_queue,
            log_progress=True,
        )

        result.path_taken = "rag_context"
        return result

    async def _handle_streaming_path(
        self,
        ctx: ProducerContext,
        result: ProducerResult,
        messages_for_api: list,
        dynamic_max_tokens: int,
    ) -> ProducerResult:
        """
        Handle true streaming mode with SaptivaStreamer.

        Streams chunks directly from LLM to queue with backpressure.
        """
        full_response = ""

        async for chunk in ctx.saptiva_client.chat_completion_stream(
            messages=messages_for_api,
            model=ctx.context.model,
            temperature=ctx.model_params.get("temperature", ctx.context.temperature),
            max_tokens=dynamic_max_tokens,
        ):
            # Use SaptivaStreamer for normalized chunk extraction
            content = SaptivaStreamer.extract_chunk_content(chunk)

            if content:
                # Backpressure: this blocks if queue is full (maxsize=10)
                await ctx.event_queue.put(ChunkEmitter.build_chunk_event(content))
                full_response += content

        result.full_response = full_response
        result.path_taken = "streaming"
        return result
