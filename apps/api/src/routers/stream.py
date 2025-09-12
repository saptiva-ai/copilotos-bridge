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
from ..services.streaming_service import get_streaming_service

logger = structlog.get_logger(__name__)
router = APIRouter()


async def generate_task_events(task_id: str, user_id: str) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for a task using the streaming service.
    """
    
    try:
        # Verify task exists and user has access
        task = await TaskModel.get(task_id)
        if not task or task.user_id != user_id:
            logger.warning("Unauthorized or invalid task access", task_id=task_id, user_id=user_id)
            return
        
        logger.info("Starting event stream", task_id=task_id, user_id=user_id)
        
        # Get streaming service
        streaming_service = get_streaming_service()
        
        # Use streaming service to generate SSE events
        async for sse_data in streaming_service.create_sse_generator(task_id, use_mock=True):
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
            
            yield sse_data
        
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
    settings: Settings = Depends(get_settings)
):
    """
    Stream real-time updates for a research task via Server-Sent Events.
    
    This endpoint provides live updates as the research progresses,
    reading from Aletheia's event stream.
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
        
        logger.info("Starting SSE stream", task_id=task_id, user_id=user_id)
        
        return EventSourceResponse(
            generate_task_events(task_id, user_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
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