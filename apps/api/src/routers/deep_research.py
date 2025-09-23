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
from ..core.telemetry import trace_span, metrics_collector
from ..models.task import Task as TaskModel, TaskStatus
from ..models.history import HistoryEventType
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
from ..services.history_service import HistoryService

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

        # Record unified history event for research start
        if request.chat_id:
            try:
                await HistoryService.record_research_started(
                    chat_id=request.chat_id,
                    user_id=user_id,
                    task=task,
                    query=request.query,
                    params=request.params.model_dump() if request.params else None
                )
            except Exception as history_error:
                logger.warning(
                    "Failed to persist research start in history",
                    error=str(history_error),
                    chat_id=request.chat_id,
                    task_id=task_id
                )
        
        logger.info(
            "Created deep research task",
            task_id=task_id,
            query=request.query,
            user_id=user_id,
            chat_id=request.chat_id
        )
        
        # Submit to Aletheia orchestrator with tracing
        try:
            async with trace_span(
                "start_aletheia_research",
                {
                    "task.id": task_id,
                    "research.query_length": len(request.query),
                    "research.type": request.research_type or "deep_research"
                }
            ):
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
        
        latest_history_event = None
        if task.chat_id:
            latest_history_event = await HistoryService.get_latest_research_status(task.chat_id, task.id)

        # Build response with real Aletheia data when available
        result = None
        if task.status == TaskStatus.COMPLETED and task.result_data:
            # Try to get real results from Aletheia
            try:
                aletheia_client = await get_aletheia_client()
                aletheia_status = await aletheia_client.get_task_status(task_id)

                if aletheia_status.status == "completed" and aletheia_status.data:
                    # Parse real Aletheia results
                    aletheia_data = aletheia_status.data
                    result = DeepResearchResult(
                        id=task_id,
                        query=task.input_data.get("query", ""),
                        summary=aletheia_data.get("summary", "Research completed"),
                        key_findings=aletheia_data.get("key_findings", []),
                        sources=aletheia_data.get("sources", []),
                        evidence=aletheia_data.get("evidence", []),
                        metrics=ResearchMetrics(
                            total_sources=aletheia_data.get("metrics", {}).get("total_sources", 0),
                            sources_processed=aletheia_data.get("metrics", {}).get("sources_processed", 0),
                            iterations_completed=aletheia_data.get("metrics", {}).get("iterations", 1),
                            processing_time_seconds=aletheia_data.get("metrics", {}).get("processing_time", 60.0),
                            tokens_used=aletheia_data.get("metrics", {}).get("tokens_used", 1000),
                            cost_estimate=aletheia_data.get("metrics", {}).get("cost", 0.01)
                        ),
                        created_at=task.created_at,
                        updated_at=task.updated_at
                    )
                else:
                    # Fallback to stored result data
                    result = DeepResearchResult(
                        id=task_id,
                        query=task.input_data.get("query", ""),
                        summary=task.result_data.get("summary", "Research completed"),
                        key_findings=task.result_data.get("key_findings", []),
                        sources=task.result_data.get("sources", []),
                        evidence=task.result_data.get("evidence", []),
                        metrics=ResearchMetrics(
                            total_sources=task.result_data.get("metrics", {}).get("total_sources", 0),
                            sources_processed=task.result_data.get("metrics", {}).get("sources_processed", 0),
                            iterations_completed=task.result_data.get("metrics", {}).get("iterations", 1),
                            processing_time_seconds=task.result_data.get("metrics", {}).get("processing_time", 60.0),
                            tokens_used=task.result_data.get("metrics", {}).get("tokens_used", 1000),
                            cost_estimate=task.result_data.get("metrics", {}).get("cost", 0.01)
                        ),
                        created_at=task.created_at,
                        updated_at=task.updated_at
                    )
            except Exception as aletheia_error:
                logger.warning("Failed to get Aletheia results, using stored data",
                              task_id=task_id,
                              error=str(aletheia_error))

                # Fallback to stored result data
                result = DeepResearchResult(
                    id=task_id,
                    query=task.input_data.get("query", ""),
                    summary=task.result_data.get("summary", "Research completed"),
                    key_findings=task.result_data.get("key_findings", []),
                    sources=task.result_data.get("sources", []),
                    evidence=task.result_data.get("evidence", []),
                    metrics=ResearchMetrics(
                        total_sources=task.result_data.get("metrics", {}).get("total_sources", 0),
                        sources_processed=task.result_data.get("metrics", {}).get("sources_processed", 0),
                        iterations_completed=task.result_data.get("metrics", {}).get("iterations", 1),
                        processing_time_seconds=task.result_data.get("metrics", {}).get("processing_time", 60.0),
                        tokens_used=task.result_data.get("metrics", {}).get("tokens_used", 1000),
                        cost_estimate=task.result_data.get("metrics", {}).get("cost", 0.01)
                    ),
                    created_at=task.created_at,
                    updated_at=task.updated_at
                )
        
        # Calculate progress - try to get real progress from Aletheia
        progress = None
        estimated_completion = None

        if task.status == TaskStatus.RUNNING:
            try:
                aletheia_client = await get_aletheia_client()
                aletheia_status = await aletheia_client.get_task_status(task_id)

                if aletheia_status.data and "progress" in aletheia_status.data:
                    progress = float(aletheia_status.data["progress"])
                    if "estimated_completion" in aletheia_status.data:
                        estimated_completion = aletheia_status.data["estimated_completion"]
                else:
                    # Fallback to time-based estimation
                    elapsed = (datetime.utcnow() - task.started_at).total_seconds() if task.started_at else 0
                    progress = min(elapsed / 300.0, 0.95)  # Max 95% until completed

            except Exception:
                # Fallback to time-based estimation
                elapsed = (datetime.utcnow() - task.started_at).total_seconds() if task.started_at else 0
                progress = min(elapsed / 300.0, 0.95)  # Max 95% until completed

        elif task.status == TaskStatus.COMPLETED:
            progress = 1.0
            # Record metrics for completed research
            if task.completed_at:
                duration = (task.completed_at - task.created_at).total_seconds()
                metrics_collector.record_research_task(
                    task_type="deep_research",
                    status="completed",
                    duration=duration
                )
        elif task.status == TaskStatus.FAILED:
            progress = 0.0
            # Record metrics for failed research
            duration = (datetime.utcnow() - task.created_at).total_seconds()
            metrics_collector.record_research_task(
                task_type="deep_research",
                status="failed",
                duration=duration
            )
        else:
            progress = 0.0

        if task.chat_id:
            try:
                if task.status == TaskStatus.COMPLETED:
                    needs_completion_event = (
                        latest_history_event is None
                        or latest_history_event.event_type != HistoryEventType.RESEARCH_COMPLETED
                    )
                    if needs_completion_event:
                        metrics_data = task.result_data.get("metrics", {}) if task.result_data else {}
                        sources_found = metrics_data.get("total_sources") or metrics_data.get("sources_processed") or 0
                        iterations_completed = metrics_data.get("iterations_completed") or metrics_data.get("iterations") or 0

                        await HistoryService.record_research_completed(
                            chat_id=task.chat_id,
                            user_id=user_id,
                            task=task,
                            sources_found=int(sources_found) if sources_found else 0,
                            iterations_completed=int(iterations_completed) if iterations_completed else 0,
                            result_metadata={
                                "source": "get_research_status",
                                "result_synced": bool(task.result_data),
                            }
                        )

                elif task.status == TaskStatus.FAILED:
                    needs_failure_event = (
                        latest_history_event is None
                        or latest_history_event.event_type != HistoryEventType.RESEARCH_FAILED
                    )
                    if needs_failure_event:
                        await HistoryService.record_research_failed(
                            chat_id=task.chat_id,
                            user_id=user_id,
                            task_id=task.id,
                            error_message=task.error_message or "Research task failed",
                            progress=task.progress,
                            current_step=task.current_step,
                            metadata={
                                "source": "get_research_status",
                                "result_synced": bool(task.result_data),
                            }
                        )
            except Exception as history_error:
                logger.warning(
                    "Failed to sync research history on status poll",
                    task_id=task_id,
                    chat_id=task.chat_id,
                    error=str(history_error)
                )

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
        
        # Cancel task in Aletheia orchestrator
        try:
            aletheia_client = await get_aletheia_client()
            await aletheia_client.cancel_task(task_id, reason=request.reason)
            logger.info("Cancelled task in Aletheia", task_id=task_id)
        except Exception as aletheia_error:
            logger.warning("Failed to cancel task in Aletheia",
                          task_id=task_id,
                          error=str(aletheia_error))
        
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


@router.get("/report/{task_id}", tags=["research"])
async def get_research_artifacts(
    task_id: str,
    http_request: Request,
    format: str = "json"  # json, markdown, html, pdf
):
    """
    Download research artifacts/reports for a completed task.
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

        # Check if task is completed
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot download artifacts for task with status: {task.status.value}"
            )

        # Get artifacts from Aletheia
        try:
            aletheia_client = await get_aletheia_client()
            artifacts = await aletheia_client.get_report_artifacts(task_id)

            if not artifacts:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No artifacts available for this task"
                )

            # Return appropriate artifact based on format
            if format in artifacts:
                artifact_url = artifacts[format]
                return {
                    "task_id": task_id,
                    "format": format,
                    "download_url": artifact_url,
                    "available_formats": list(artifacts.keys()),
                    "expires_at": None  # TODO: Add expiration logic
                }
            else:
                return {
                    "task_id": task_id,
                    "format": format,
                    "error": f"Format '{format}' not available",
                    "available_formats": list(artifacts.keys())
                }

        except Exception as aletheia_error:
            logger.warning("Failed to get artifacts from Aletheia",
                          task_id=task_id,
                          error=str(aletheia_error))

            # Fallback to mock artifacts
            return {
                "task_id": task_id,
                "format": format,
                "download_url": f"/api/mock/artifacts/{task_id}.{format}",
                "available_formats": ["json", "markdown", "html"],
                "error": "Using mock artifacts - Aletheia unavailable"
            }

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
