"""
Deep Research API endpoints.
"""

from datetime import datetime
import os
from typing import Optional
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request

from ..core.config import get_settings, Settings
from ..core.telemetry import trace_span, metrics_collector
from ..models.task import Task as TaskModel, TaskStatus
from ..models.history import HistoryEventType
from ..schemas.research import (
    DeepResearchRequest,
    DeepResearchResponse,
    TaskCancelRequest,
    DeepResearchResult,
    ResearchMetrics
)
from ..schemas.common import ApiResponse
from ..services.aletheia_client import get_aletheia_client
from ..services.history_service import HistoryService
from ..services.deep_research_service import DeepResearchService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/deep-research", response_model=DeepResearchResponse, tags=["research"])
async def start_deep_research(
    request: DeepResearchRequest,
    http_request: Request,
    settings: Settings = Depends(get_settings)
) -> DeepResearchResponse:
    """
    Start a deep research task.

    Creates a new research task and returns task ID for tracking progress.
    The actual research is delegated to Aletheia orchestrator.
    """
    user_id = getattr(http_request.state, 'user_id', 'anonymous')

    try:
        # Initialize service
        service = DeepResearchService(settings)

        # Validate request (kill switch, enabled flag, explicit flag)
        await service.validate_research_request(request, user_id)

        # Create task record
        task = await service.create_research_task(request, user_id)

        # Submit to Aletheia orchestrator
        await service.start_aletheia_research(task, request, user_id)

        # Generate stream URL if requested
        stream_url = f"/api/stream/{task.id}" if request.stream else None

        return DeepResearchResponse(
            task_id=task.id,
            status=TaskStatus.RUNNING,
            message="Deep research task started successfully",
            result=None,
            progress=0.0,
            estimated_completion=None,
            created_at=task.created_at,
            stream_url=stream_url
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error starting deep research", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start deep research task"
        )


@router.get("/deep-research/{task_id}", response_model=DeepResearchResponse, tags=["research"])
async def get_research_status(
    task_id: str,
    http_request: Request,
    settings: Settings = Depends(get_settings)
) -> DeepResearchResponse:
    """
    Get the status and results of a deep research task.
    """
    user_id = getattr(http_request.state, 'user_id', 'anonymous')

    try:
        # Initialize service
        service = DeepResearchService(settings)

        # Check kill switch
        service.check_kill_switch(user_id)

        # Get task with permission check
        task = await service.get_task_with_permission_check(task_id, user_id)

        # Build research result if completed
        result = await service.build_research_result(task)

        # Calculate progress and estimated completion
        progress, estimated_completion = await service.calculate_progress(task)

        # Sync history events (completed/failed status changes)
        await service.sync_history_events(task, user_id)

        logger.info("Retrieved research task status", task_id=task_id, status=task.status)

        return DeepResearchResponse(
            task_id=task_id,
            status=task.status,
            message=task.error_message or f"Task is {task.status.value}",
            result=result,
            progress=progress,
            estimated_completion=estimated_completion,
            created_at=task.created_at,
            stream_url=f"/api/stream/{task_id}" if task.input_data.get("stream") else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving research status", error=str(e), task_id=task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task status"
        )


@router.post("/deep-research/{task_id}/cancel", response_model=ApiResponse, tags=["research"])
async def cancel_research_task(
    task_id: str,
    request: TaskCancelRequest,
    http_request: Request,
    settings: Settings = Depends(get_settings)
) -> ApiResponse:
    """
    Cancel a running deep research task.
    """
    user_id = getattr(http_request.state, 'user_id', 'anonymous')

    try:
        # Initialize service
        service = DeepResearchService(settings)

        # Check kill switch
        service.check_kill_switch(user_id)

        # Get task with permission check
        task = await service.get_task_with_permission_check(task_id, user_id)

        # Cancel task (updates status, notifies Aletheia)
        await service.cancel_task(task, reason=request.reason)

        return ApiResponse(
            success=True,
            message="Task cancelled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error cancelling task", error=str(e), task_id=task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel task"
        )


@router.get("/report/{task_id}", tags=["research"])
async def get_research_artifacts(
    task_id: str,
    http_request: Request,
    format: str = "json",  # json, markdown, html, pdf
    settings: Settings = Depends(get_settings)
):
    """
    Download research artifacts/reports for a completed task.
    """
    user_id = getattr(http_request.state, 'user_id', 'anonymous')

    try:
        # Initialize service
        service = DeepResearchService(settings)

        # Check kill switch
        service.check_kill_switch(user_id)

        # Get task with permission check
        task = await service.get_task_with_permission_check(task_id, user_id)

        # Get artifacts (validates task is completed)
        return await service.get_research_artifacts(task, format=format)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting research artifacts", error=str(e), task_id=task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get research artifacts"
        )


@router.get("/tasks", tags=["research"])
async def get_user_tasks(
    limit: int = 20,
    offset: int = 0,
    status_filter: Optional[TaskStatus] = None,
    http_request: Request = None,
    settings: Settings = Depends(get_settings)
):
    """
    Get research tasks for the authenticated user.
    """
    user_id = getattr(http_request.state, 'user_id', 'anonymous')

    try:
        # Initialize service
        service = DeepResearchService(settings)

        # Check kill switch
        service.check_kill_switch(user_id)

        # Get user tasks with pagination
        return await service.get_user_tasks(
            user_id=user_id,
            limit=limit,
            offset=offset,
            status_filter=status_filter
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving user tasks", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks"
        )
