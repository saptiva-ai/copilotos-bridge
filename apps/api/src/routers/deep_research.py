"""
Deep Research API endpoints.
"""

import time
from datetime import datetime
from typing import Optional
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request

from ..core.config import get_settings, Settings
from ..models.task import Task as TaskModel, TaskStatus
from ..schemas.research import (
    DeepResearchRequest,
    DeepResearchResponse,
    TaskStatusRequest,
    TaskCancelRequest,
    DeepResearchResult,
    ResearchMetrics
)
from ..schemas.common import ApiResponse
from ..services.aletheia_client import get_aletheia_client

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
    task_id = str(uuid4())
    
    try:
        # Create task record
        task = TaskModel(
            id=task_id,
            user_id=user_id,
            task_type="deep_research",
            status=TaskStatus.PENDING,
            input_data={
                "query": request.query,
                "research_type": request.research_type.value,
                "params": request.params.model_dump() if request.params else None,
                "stream": request.stream,
                "context": request.context
            },
            chat_id=request.chat_id,
            created_at=datetime.utcnow()
        )
        await task.insert()
        
        logger.info(
            "Created deep research task",
            task_id=task_id,
            query=request.query,
            user_id=user_id,
            chat_id=request.chat_id
        )
        
        # Submit to Aletheia orchestrator
        try:
            aletheia_client = await get_aletheia_client()
            aletheia_response = await aletheia_client.start_deep_research(
                query=request.query,
                task_id=task_id,
                user_id=user_id,
                params=request.params.model_dump() if request.params else None,
                context=request.context
            )
            
            if aletheia_response.status == "error":
                task.status = TaskStatus.FAILED
                task.error_message = aletheia_response.error
                await task.save()
                
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to start research: {aletheia_response.error}"
                )
            else:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                await task.save()
                
        except HTTPException:
            raise
        except Exception as e:
            # Fallback to mock mode if Aletheia is unavailable
            logger.warning("Aletheia unavailable, using mock mode", error=str(e))
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            await task.save()
        
        # Generate stream URL if requested
        stream_url = None
        if request.stream:
            stream_url = f"/api/stream/{task_id}"
        
        return DeepResearchResponse(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            message="Deep research task started successfully",
            result=None,
            progress=0.0,
            estimated_completion=None,
            created_at=task.created_at,
            stream_url=stream_url
        )
        
    except Exception as e:
        logger.error("Error starting deep research", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start deep research task"
        )


@router.get("/deep-research/{task_id}", response_model=DeepResearchResponse, tags=["research"])
async def get_research_status(
    task_id: str,
    http_request: Request
) -> DeepResearchResponse:
    """
    Get the status and results of a deep research task.
    """
    
    user_id = getattr(http_request.state, 'user_id', 'anonymous')
    
    try:
        # Retrieve task
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
        
        # Build response
        result = None
        if task.status == TaskStatus.COMPLETED and task.result_data:
            # TODO: Parse actual result from Aletheia
            result = DeepResearchResult(
                id=task_id,
                query=task.input_data.get("query", ""),
                summary="Mock research summary",
                key_findings=["Finding 1", "Finding 2"],
                sources=[],
                evidence=[],
                metrics=ResearchMetrics(
                    total_sources=0,
                    sources_processed=0,
                    iterations_completed=1,
                    processing_time_seconds=60.0,
                    tokens_used=1000,
                    cost_estimate=0.01
                ),
                created_at=task.created_at,
                updated_at=task.updated_at
            )
        
        # Calculate progress
        progress = None
        if task.status == TaskStatus.RUNNING:
            # Mock progress calculation
            elapsed = (datetime.utcnow() - task.started_at).total_seconds() if task.started_at else 0
            progress = min(elapsed / 300.0, 0.95)  # Max 95% until completed
        elif task.status == TaskStatus.COMPLETED:
            progress = 1.0
        elif task.status == TaskStatus.FAILED:
            progress = 0.0
        
        logger.info("Retrieved research task status", task_id=task_id, status=task.status)
        
        return DeepResearchResponse(
            task_id=task_id,
            status=task.status,
            message=task.error_message or f"Task is {task.status.value}",
            result=result,
            progress=progress,
            estimated_completion=None,
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
    http_request: Request
) -> ApiResponse:
    """
    Cancel a running deep research task.
    """
    
    user_id = getattr(http_request.state, 'user_id', 'anonymous')
    
    try:
        # Retrieve task
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
        
        # Check if task can be cancelled
        if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel task with status: {task.status.value}"
            )
        
        # Cancel task
        task.status = TaskStatus.CANCELLED
        task.error_message = request.reason or "Cancelled by user"
        task.completed_at = datetime.utcnow()
        await task.save()
        
        # TODO: Cancel task in Aletheia orchestrator
        
        logger.info(
            "Cancelled research task", 
            task_id=task_id, 
            user_id=user_id, 
            reason=request.reason
        )
        
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


@router.get("/tasks", tags=["research"])
async def get_user_tasks(
    limit: int = 20,
    offset: int = 0,
    status_filter: Optional[TaskStatus] = None,
    http_request: Request = None
):
    """
    Get research tasks for the authenticated user.
    """
    
    user_id = getattr(http_request.state, 'user_id', 'anonymous')
    
    try:
        # Build query
        query = TaskModel.find(TaskModel.user_id == user_id)
        
        if status_filter:
            query = query.find(TaskModel.status == status_filter)
        
        # Get total count
        total_count = await query.count()
        
        # Get tasks with pagination
        tasks = await query.sort(-TaskModel.created_at).skip(offset).limit(limit).to_list()
        
        # Convert to response format
        task_responses = []
        for task in tasks:
            task_responses.append({
                "task_id": task.id,
                "status": task.status.value,
                "task_type": task.task_type,
                "query": task.input_data.get("query", ""),
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "chat_id": task.chat_id,
                "error_message": task.error_message
            })
        
        logger.info(
            "Retrieved user tasks",
            user_id=user_id,
            task_count=len(tasks),
            total_count=total_count
        )
        
        return {
            "tasks": task_responses,
            "total_count": total_count,
            "has_more": offset + len(tasks) < total_count
        }
        
    except Exception as e:
        logger.error("Error retrieving user tasks", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks"
        )