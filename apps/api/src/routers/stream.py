"""
Server-Sent Events (SSE) streaming endpoints.
"""

import json
import time
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from ..core.config import get_settings, Settings
from ..models.task import Task as TaskModel, TaskStatus
from ..schemas.research import StreamEvent
from ..services.aletheia_streaming import get_event_streamer

logger = structlog.get_logger(__name__)
router = APIRouter()


async def generate_task_events(task_id: str, user_id: str, use_mock: bool = False) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for a task using Aletheia event streaming.
    """

    try:
        # Verify task exists and user has access
        task = await TaskModel.get(task_id)
        if not task or task.user_id != user_id:
            logger.warning("Unauthorized or invalid task access", task_id=task_id, user_id=user_id)
            return

        logger.info("Starting Aletheia event stream", task_id=task_id, user_id=user_id, use_mock=use_mock)

        # Get event streamer
        event_streamer = get_event_streamer()

        # Choose streaming method based on availability
        if use_mock:
            # Use mock stream for testing/development
            async for sse_event in event_streamer.create_mock_stream(task_id):
                # Check if task was cancelled
                current_task = await TaskModel.get(task_id)
                if current_task and current_task.status == TaskStatus.CANCELLED:
                    cancellation_event = {
                        "event_type": "task_cancelled",
                        "task_id": task_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {"message": "Task was cancelled by user"}
                    }
                    yield f"data: {json.dumps(cancellation_event)}\n\n"
                    break

                yield sse_event
        else:
            # Use real Aletheia stream
            try:
                async for sse_event in event_streamer.stream_task_events(task_id):
                    # Check if task was cancelled
                    current_task = await TaskModel.get(task_id)
                    if current_task and current_task.status == TaskStatus.CANCELLED:
                        # Stop the stream
                        await event_streamer.stop_stream(task_id)
                        break

                    yield sse_event
            except Exception as aletheia_error:
                logger.warning(
                    "Aletheia streaming failed, falling back to mock",
                    error=str(aletheia_error),
                    task_id=task_id
                )
                # Fallback to mock stream
                async for sse_event in event_streamer.create_mock_stream(task_id):
                    yield sse_event

        logger.info("Event stream completed", task_id=task_id)

    except Exception as e:
        logger.error("Error in event stream", error=str(e), task_id=task_id)
        error_event = {
            "event_type": "stream_error",
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"error": str(e)}
        }
        yield f"data: {json.dumps(error_event)}\n\n"


@router.get("/stream/{task_id}", tags=["streaming"])
async def stream_task_events(
    task_id: str,
    http_request: Request,
    use_mock: bool = False,
    settings: Settings = Depends(get_settings)
):
    """
    Stream real-time updates for a research task via Server-Sent Events.

    This endpoint provides live updates as the research progresses,
    reading from Aletheia's event stream.

    Parameters:
    - task_id: The research task ID
    - use_mock: Use mock events for testing (default: False)
    """

    user_id = getattr(http_request.state, 'user_id', 'anonymous')

    try:
        # Verify task exists
        task = await TaskModel.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Verify user access
        if task.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to task"
            )

        logger.info("Starting SSE stream", task_id=task_id, user_id=user_id, use_mock=use_mock)

        return EventSourceResponse(
            generate_task_events(task_id, user_id, use_mock=use_mock),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
                "X-Accel-Buffering": "no"  # Disable proxy buffering for real-time streaming
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error setting up SSE stream", error=str(e), task_id=task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start event stream"
        )


@router.get("/stream/{task_id}/status", tags=["streaming"])
async def get_stream_status(
    task_id: str,
    http_request: Request
):
    """
    Get the current status of a streaming task without opening SSE connection.
    """
    
    user_id = getattr(http_request.state, 'user_id', 'anonymous')
    
    try:
        # Verify task exists and user has access
        task = await TaskModel.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if task.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to task"
            )
        
        return {
            "task_id": task_id,
            "status": task.status.value,
            "progress": getattr(task, 'progress', None),
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "stream_active": task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting stream status", error=str(e), task_id=task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get stream status"
        )