"""
Stream Response Finalizer Service - Handles post-streaming finalization.

REFACTOR-001 Phase 9: Extracted from streaming_handler.py _stream_chat_response finally block.
"""

import json
import time
from asyncio import CancelledError, Task
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import structlog

from .message_persistence import MessagePersistenceService
from .response_postprocessor import PostProcessResult, ResponsePostProcessor

logger = structlog.get_logger(__name__)


@dataclass
class FinalizerContext:
    """Context for stream response finalization."""

    context: Any  # ChatContext
    chat_session: Any  # ChatSession model
    chat_service: Any  # ChatService instance
    cache: Any  # Redis cache
    doc_warnings: Optional[List[str]]
    start_time: Optional[float] = None  # time.perf_counter() at stream start


@dataclass
class FinalizerResult:
    """Result of stream response finalization."""

    full_response: str
    assistant_message: Any  # Message model
    done_event: Dict[str, Any]
    fallback_chunk: Optional[Dict[str, Any]] = None
    table_append_chunk: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None


class StreamResponseFinalizer:
    """
    Handles post-streaming finalization tasks.

    This service encapsulates:
    1. Producer task cleanup and result extraction
    2. Response post-processing
    3. Message metadata building and persistence
    4. Done event construction
    5. Cache invalidation
    """

    @classmethod
    async def cleanup_producer(
        cls,
        producer_task: Task,
    ) -> Any:
        """
        Clean up producer task and extract result.

        Args:
            producer_task: The asyncio Task running the producer

        Returns:
            ProducerResult if task completed, None if cancelled

        Raises:
            Exception if producer had an error
        """
        producer_result = None

        if not producer_task.done():
            producer_task.cancel()
            try:
                await producer_task
            except CancelledError:
                logger.info("Producer task cancelled in cleanup")
        else:
            producer_result = producer_task.result()

        # Check if producer had an error
        if producer_result and producer_result.error:
            logger.error(
                "Producer error detected in cleanup",
                error=str(producer_result.error),
            )
            raise producer_result.error

        return producer_result

    @classmethod
    def post_process_response(
        cls,
        producer_result: Any,
        ctx: FinalizerContext,
    ) -> tuple:
        """
        Post-process the streaming response.

        Args:
            producer_result: Result from ChatStreamProducer
            ctx: Finalizer context

        Returns:
            Tuple of (full_response, chart_flow_result, post_result, fallback_chunk)
        """
        full_response = producer_result.full_response if producer_result else ""
        chart_flow_result = (
            producer_result.chart_flow_result if producer_result else None
        )

        # Skip post-processing for catalog fast path — response is already final
        if producer_result and producer_result.path_taken == "catalog":
            post_result = PostProcessResult(
                content=full_response,
                was_empty=False,
                was_sanitized=False,
                chars_removed=0,
                truth_violations=[],
                fallback_scenario=None,
            )
            return full_response, chart_flow_result, post_result, None, None

        # Use ResponsePostProcessor for post-processing
        post_result = ResponsePostProcessor.process(
            response=full_response,
            has_documents=bool(ctx.context.document_ids),
            doc_warnings=ctx.doc_warnings,
            model=ctx.context.model,
            context={
                "user_id": ctx.context.user_id,
                "chat_id": str(ctx.chat_session.id),
                "session_id": ctx.context.session_id,
                "model": ctx.context.model,
                "has_documents": bool(ctx.context.document_ids),
                "document_count": (
                    len(ctx.context.document_ids) if ctx.context.document_ids else 0
                ),
                "stream_mode": True,
                "doc_warnings": ctx.doc_warnings if ctx.doc_warnings else None,
            },
        )

        full_response = post_result.content

        # Build fallback chunk if response was empty
        fallback_chunk = None
        if post_result.was_empty:
            fallback_chunk = {
                "event": "chunk",
                "data": json.dumps({"content": full_response}),
            }

        # Build table append chunk if post-processor injected a table
        table_append_chunk = None
        if post_result.table_appended:
            table_append_chunk = {
                "event": "chunk",
                "data": json.dumps({"content": post_result.table_appended}),
            }

        return (
            full_response,
            chart_flow_result,
            post_result,
            fallback_chunk,
            table_append_chunk,
        )

    @classmethod
    async def persist_and_finalize(
        cls,
        full_response: str,
        chart_flow_result: Any,
        ctx: FinalizerContext,
    ) -> tuple:
        """
        Build metadata, persist message, and create done event.

        Args:
            full_response: The processed response content
            chart_flow_result: Result from chart flow handler
            ctx: Finalizer context

        Returns:
            Tuple of (assistant_message, done_event)
        """
        # Calculate latency if start_time was provided
        latency_ms = None
        if ctx.start_time is not None:
            latency_ms = round((time.perf_counter() - ctx.start_time) * 1000, 2)
            logger.info(
                "Response latency calculated",
                latency_ms=latency_ms,
            )

        # Build assistant metadata
        artifact_id_for_metadata = (
            chart_flow_result.artifact_id
            if chart_flow_result and chart_flow_result.artifact_created
            else None
        )
        assistant_metadata = MessagePersistenceService.build_assistant_metadata(
            streaming=True,
            document_ids=ctx.context.document_ids,
            doc_warnings=ctx.doc_warnings,
            artifact_id=artifact_id_for_metadata,
            latency_ms=latency_ms,
        )

        # Save assistant message
        assistant_message = await ctx.chat_service.add_assistant_message(
            chat_session=ctx.chat_session,
            content=full_response,
            model=ctx.context.model,
            metadata=assistant_metadata,
            latency_ms=int(latency_ms) if latency_ms else None,
        )

        # Build done event
        done_event = MessagePersistenceService.build_done_event(
            message_id=str(assistant_message.id),
            chat_id=str(ctx.chat_session.id),
            content=full_response,
        )

        logger.info(
            "✅ Stream finalized",
            message_id=str(assistant_message.id),
            chat_id=str(ctx.chat_session.id),
            content_length=len(full_response),
        )

        # Invalidate cache
        await ctx.cache.invalidate_chat_history(ctx.chat_session.id)

        return assistant_message, done_event

    @classmethod
    async def finalize(
        cls,
        producer_task: Task,
        ctx: FinalizerContext,
    ) -> FinalizerResult:
        """
        Complete finalization of stream response.

        This is the main entry point that orchestrates all finalization steps.

        Args:
            producer_task: The asyncio Task running the producer
            ctx: Finalizer context with all required dependencies

        Returns:
            FinalizerResult with all finalization outputs
        """
        try:
            # 1. Cleanup producer and get result
            producer_result = await cls.cleanup_producer(producer_task)

            # 2. Post-process response
            full_response, chart_flow_result, _, fallback_chunk, table_append_chunk = (
                cls.post_process_response(producer_result, ctx)
            )

            # 3. Persist and finalize
            assistant_message, done_event = await cls.persist_and_finalize(
                full_response=full_response,
                chart_flow_result=chart_flow_result,
                ctx=ctx,
            )

            return FinalizerResult(
                full_response=full_response,
                assistant_message=assistant_message,
                done_event=done_event,
                fallback_chunk=fallback_chunk,
                table_append_chunk=table_append_chunk,
            )

        except Exception as e:
            logger.error("Stream finalization failed", error=str(e), exc_info=True)
            return FinalizerResult(
                full_response="",
                assistant_message=None,
                done_event={},
                error=e,
            )
