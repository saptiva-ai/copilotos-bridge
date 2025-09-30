"""
Unified history service for managing chat + research timeline
"""

import structlog
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..models.history import (
    HistoryEvent,
    HistoryEventFactory,
    HistoryQuery,
    HistoryEventType
)
from ..models.chat import ChatMessage
from ..models.task import Task
from ..core.redis_cache import get_redis_cache

logger = structlog.get_logger(__name__)


class HistoryService:
    """Service for managing unified chat + research history"""

    @staticmethod
    async def record_chat_message(
        chat_id: str,
        user_id: str,
        message: ChatMessage
    ) -> HistoryEvent:
        """Record a chat message in the unified history"""
        try:
            event = await HistoryEventFactory.create_chat_message_event(
                chat_id=chat_id,
                user_id=user_id,
                message_id=message.id,
                role=message.role.value,
                content=message.content,
                model=message.model,
                tokens=message.tokens,
                latency_ms=message.latency_ms,
                # Additional metadata
                status=message.status.value,
                created_at=message.created_at,
                message_metadata=message.metadata
            )

            # Invalidate cache
            await HistoryService._invalidate_cache(chat_id)

            logger.info(
                "Recorded chat message in history",
                chat_id=chat_id,
                message_id=message.id,
                event_id=event.id
            )

            return event

        except Exception as e:
            logger.error(
                "Failed to record chat message in history",
                chat_id=chat_id,
                message_id=message.id,
                error=str(e)
            )
            # Don't fail the main flow if history fails
            raise

    @staticmethod
    async def record_research_started(
        chat_id: str,
        user_id: str,
        task: Task,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> HistoryEvent:
        """Record research task start"""
        try:
            event = await HistoryEventFactory.create_research_started_event(
                chat_id=chat_id,
                user_id=user_id,
                task_id=task.id,
                query=query,
                # Additional metadata
                task_type=task.task_type,
                params=params,
                created_at=task.created_at
            )

            await HistoryService._invalidate_cache(chat_id)

            logger.info(
                "Recorded research start in history",
                chat_id=chat_id,
                task_id=task.id,
                event_id=event.id
            )

            return event

        except Exception as e:
            logger.error(
                "Failed to record research start in history",
                chat_id=chat_id,
                task_id=task.id,
                error=str(e)
            )
            raise

    @staticmethod
    async def record_research_progress(
        chat_id: str,
        user_id: str,
        task_id: str,
        progress: float,
        current_step: str,
        sources_found: Optional[int] = None,
        iterations_completed: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> HistoryEvent:
        """Record research progress update"""
        try:
            normalized_progress = HistoryService._normalize_progress(progress)
            if normalized_progress is None:
                normalized_progress = 0.0
            event = await HistoryEventFactory.create_research_progress_event(
                chat_id=chat_id,
                user_id=user_id,
                task_id=task_id,
                progress=normalized_progress,
                current_step=current_step,
                sources_found=sources_found,
                iterations_completed=iterations_completed,
                **(metadata or {})
            )

            # Only invalidate cache for significant progress updates (every 10%)
            if normalized_progress is not None and int(normalized_progress) % 10 == 0:
                await HistoryService._invalidate_cache(chat_id)

            logger.debug(
                "Recorded research progress in history",
                chat_id=chat_id,
                task_id=task_id,
                progress=normalized_progress,
                event_id=event.id
            )

            return event

        except Exception as e:
            logger.error(
                "Failed to record research progress in history",
                chat_id=chat_id,
                task_id=task_id,
                error=str(e)
            )
            # Don't fail progress updates if history fails
            return None

    @staticmethod
    async def record_research_completed(
        chat_id: str,
        user_id: str,
        task: Task,
        sources_found: int,
        iterations_completed: int,
        result_metadata: Optional[Dict[str, Any]] = None
    ) -> HistoryEvent:
        """Record research completion"""
        try:
            event = await HistoryEventFactory.create_research_completed_event(
                chat_id=chat_id,
                user_id=user_id,
                task_id=task.id,
                sources_found=sources_found,
                iterations_completed=iterations_completed,
                # Additional metadata
                completed_at=task.completed_at,
                result_data=task.result_data,
                **(result_metadata or {})
            )

            await HistoryService._invalidate_cache(chat_id)

            logger.info(
                "Recorded research completion in history",
                chat_id=chat_id,
                task_id=task.id,
                event_id=event.id
            )

            return event

        except Exception as e:
            logger.error(
                "Failed to record research completion in history",
                chat_id=chat_id,
                task_id=task.id,
                error=str(e)
            )
            raise

    @staticmethod
    async def record_research_failed(
        chat_id: str,
        user_id: str,
        task_id: str,
        error_message: str,
        progress: Optional[float] = None,
        current_step: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> HistoryEvent:
        """Record research failure"""
        try:
            normalized_progress = HistoryService._normalize_progress(progress) if progress is not None else None
            event = await HistoryEventFactory.create_research_failed_event(
                chat_id=chat_id,
                user_id=user_id,
                task_id=task_id,
                error_message=error_message,
                progress=normalized_progress,
                current_step=current_step,
                **(metadata or {})
            )

            await HistoryService._invalidate_cache(chat_id)

            logger.error(
                "Recorded research failure in history",
                chat_id=chat_id,
                task_id=task_id,
                event_id=event.id,
                error=error_message
            )

            return event

        except Exception as e:
            logger.error(
                "Failed to record research failure in history",
                chat_id=chat_id,
                task_id=task_id,
                error=str(e)
            )
            raise

    @staticmethod
    async def record_source_discovery(
        chat_id: str,
        user_id: str,
        task_id: str,
        source_id: str,
        url: str,
        title: str,
        relevance_score: float,
        credibility_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> HistoryEvent:
        """Record source discovery during research"""
        try:
            event = await HistoryEventFactory.create_source_found_event(
                chat_id=chat_id,
                user_id=user_id,
                task_id=task_id,
                source_id=source_id,
                url=url,
                title=title,
                relevance_score=relevance_score,
                credibility_score=credibility_score,
                **(metadata or {})
            )

            logger.debug(
                "Recorded source discovery in history",
                chat_id=chat_id,
                task_id=task_id,
                source_id=source_id,
                event_id=event.id
            )

            return event

        except Exception as e:
            logger.error(
                "Failed to record source discovery in history",
                chat_id=chat_id,
                task_id=task_id,
                source_id=source_id,
                error=str(e)
            )
            # Don't fail source discovery if history fails
            return None

    @staticmethod
    async def get_chat_timeline(
        chat_id: str,
        limit: int = 50,
        offset: int = 0,
        event_types: Optional[List[HistoryEventType]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Get complete timeline for a chat"""

        cache_key = f"chat_timeline:{chat_id}:{limit}:{offset}:{':'.join(event_types or [])}"

        # Try cache first
        if use_cache:
            try:
                cache = await get_redis_cache()
                cached_result = await cache.get(cache_key)
                if cached_result:
                    logger.debug("Returning cached chat timeline", chat_id=chat_id)
                    return cached_result
            except Exception as e:
                logger.warning("Cache retrieval failed", error=str(e))

        try:
            # Get events
            events = await HistoryQuery.get_chat_timeline(
                chat_id=chat_id,
                limit=limit,
                offset=offset,
                event_types=event_types
            )

            # Get total count
            total_count = await HistoryQuery.get_chat_timeline_count(
                chat_id=chat_id,
                event_types=event_types
            )

            result = {
                "chat_id": chat_id,
                "events": [event.model_dump(mode='json') for event in events],
                "total_count": total_count,
                "has_more": offset + len(events) < total_count,
                "limit": limit,
                "offset": offset
            }

            # Cache result
            if use_cache:
                try:
                    cache = await get_redis_cache()
                    await cache.set(cache_key, result, expire=300)  # 5 minutes cache
                except Exception as e:
                    logger.warning("Cache storage failed", error=str(e))

            logger.info(
                "Retrieved chat timeline",
                chat_id=chat_id,
                event_count=len(events),
                total_count=total_count
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to get chat timeline",
                chat_id=chat_id,
                error=str(e)
            )
            raise

    @staticmethod
    async def get_research_timeline(chat_id: str, task_id: str) -> List[HistoryEvent]:
        """Get research-specific timeline for a task"""
        try:
            events = await HistoryQuery.get_research_events_for_task(task_id)

            logger.info(
                "Retrieved research timeline",
                chat_id=chat_id,
                task_id=task_id,
                event_count=len(events)
            )

            return events

        except Exception as e:
            logger.error(
                "Failed to get research timeline",
                chat_id=chat_id,
                task_id=task_id,
                error=str(e)
            )
            raise

    @staticmethod
    async def get_latest_research_status(chat_id: str, task_id: str) -> Optional[HistoryEvent]:
        """Get the latest research status for a task"""
        try:
            return await HistoryQuery.get_latest_research_event(chat_id, task_id)
        except Exception as e:
            logger.error(
                "Failed to get latest research status",
                chat_id=chat_id,
                task_id=task_id,
                error=str(e)
            )
            return None

    @staticmethod
    async def cleanup_old_events(chat_id: str, keep_days: int = 30):
        """Clean up old history events for a chat"""
        try:
            cutoff_date = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=keep_days)

            result = await HistoryEvent.find(
                HistoryEvent.chat_id == chat_id,
                HistoryEvent.created_at < cutoff_date
            ).delete()

            if result.deleted_count > 0:
                await HistoryService._invalidate_cache(chat_id)

            logger.info(
                "Cleaned up old history events",
                chat_id=chat_id,
                deleted_count=result.deleted_count,
                cutoff_date=cutoff_date
            )

            return result.deleted_count

        except Exception as e:
            logger.error(
                "Failed to cleanup old events",
                chat_id=chat_id,
                error=str(e)
            )
            return 0

    @staticmethod
    async def _invalidate_cache(chat_id: str):
        """Invalidate all cache entries for a chat"""
        try:
            cache = await get_redis_cache()
            pattern = f"chat_timeline:{chat_id}:*"
            await cache.delete_pattern(pattern)
        except Exception as e:
            logger.warning("Failed to invalidate cache", chat_id=chat_id, error=str(e))

    @staticmethod
    def _normalize_progress(progress: Optional[float]) -> Optional[float]:
        """Normalize progress values to percentage scale"""
        if progress is None:
            return None

        try:
            if progress <= 1:
                return round(progress * 100, 2)
            return round(progress, 2)
        except TypeError:
            return None
