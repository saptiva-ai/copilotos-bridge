"""
Chat API endpoints - Refactored with Design Patterns.

Uses:
- Dataclasses for type-safe DTOs
- Builder Pattern for response construction
- Strategy Pattern for pluggable chat handlers
- Thin Controller Pattern
"""

import time
from datetime import datetime
from typing import Optional
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse

from ..core.config import get_settings, Settings
from ..core.redis_cache import get_redis_cache
from ..core.telemetry import trace_span, metrics_collector
from ..models.chat import ChatSession as ChatSessionModel, ChatMessage as ChatMessageModel, MessageRole
from ..schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatSessionListResponse,
    ChatSessionUpdateRequest,
    ChatMessage,
    ChatSession
)
from ..schemas.common import ApiResponse
from ..services.text_sanitizer import sanitize_response_content
from ..services.tools import normalize_tools_state
from ..services.chat_service import ChatService
from ..services.history_service import HistoryService
from ..domain import (
    ChatContext,
    ChatResponseBuilder,
    ChatStrategyFactory
)

logger = structlog.get_logger(__name__)
router = APIRouter()

NO_STORE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _build_chat_context(
    request: ChatRequest,
    user_id: str,
    settings: Settings
) -> ChatContext:
    """
    Build ChatContext from request.

    Encapsulates all request data into immutable dataclass.
    """
    return ChatContext(
        user_id=user_id,
        request_id=str(uuid4()),
        timestamp=datetime.utcnow(),
        chat_id=request.chat_id,
        session_id=None,  # Will be resolved during processing
        message=request.message,
        context=request.context,
        document_ids=request.document_ids,
        model=request.model or settings.chat_default_model,
        tools_enabled=normalize_tools_state(request.tools_enabled),
        stream=getattr(request, 'stream', False),
        temperature=getattr(request, 'temperature', None),
        max_tokens=getattr(request, 'max_tokens', None),
        kill_switch_active=settings.deep_research_kill_switch
    )


@router.post("/chat", tags=["chat"])
async def send_chat_message(
    request: ChatRequest,
    http_request: Request,
    response: Response,
    settings: Settings = Depends(get_settings)
) -> JSONResponse:
    """
    Send a chat message and get AI response.

    Refactored using:
    - ChatContext dataclass for type-safe request encapsulation
    - Strategy Pattern for pluggable chat handlers
    - Builder Pattern for declarative response construction

    Handles both new conversations and continuing existing ones.
    """

    start_time = time.time()
    response.headers.update(NO_STORE_HEADERS)
    user_id = getattr(http_request.state, 'user_id', 'mock-user-id')

    try:
        # 1. Build immutable context from request
        context = _build_chat_context(request, user_id, settings)

        logger.info(
            "Processing chat request",
            request_id=context.request_id,
            user_id=context.user_id,
            model=context.model,
            has_documents=bool(context.document_ids)
        )

        # 2. Initialize services
        chat_service = ChatService(settings)
        cache = await get_redis_cache()

        # 3. Get or create session
        chat_session = await chat_service.get_or_create_session(
            chat_id=context.chat_id,
            user_id=context.user_id,
            first_message=context.message,
            tools_enabled=context.tools_enabled
        )

        # Update context with resolved session
        context = context.with_session(chat_session.id)

        # 4. Add user message
        user_message = await chat_service.add_user_message(
            chat_session=chat_session,
            content=context.message
        )

        # 5. Select and execute appropriate strategy
        async with trace_span("chat_strategy_execution", {
            "strategy": "simple",
            "session_id": context.session_id,
            "has_documents": bool(context.document_ids)
        }):
            strategy = ChatStrategyFactory.create_strategy(context, chat_service)
            result = await strategy.process(context)

        # 6. Save assistant message
        assistant_message = await chat_service.add_assistant_message(
            chat_session=chat_session,
            content=result.sanitized_content,
            model=result.metadata.model_used,
            task_id=result.task_id,
            metadata=result.metadata.decision_metadata or {},
            tokens=result.metadata.tokens_used.get("total") if result.metadata.tokens_used else None,
            latency_ms=int(result.metadata.latency_ms) if result.metadata.latency_ms else None
        )

        # Update result with message IDs
        result.metadata.user_message_id = user_message.id
        result.metadata.assistant_message_id = assistant_message.id

        # 7. Invalidate caches
        await cache.invalidate_chat_history(chat_session.id)
        if result.research_triggered:
            await cache.invalidate_research_tasks(chat_session.id)

        # 8. Record metrics
        if result.metadata.tokens_used:
            metrics_collector.record_chat_message(
                model=result.metadata.model_used,
                tokens=result.metadata.tokens_used.get("total", 0),
                duration=(time.time() - start_time)
            )

        # 9. Build and return response using Builder Pattern
        return (ChatResponseBuilder()
            .from_processing_result(result)
            .with_metadata("processing_time_ms", (time.time() - start_time) * 1000)
            .build())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error processing chat message",
            error=str(e),
            user_id=user_id,
            exc_info=True
        )

        return (ChatResponseBuilder()
            .with_error(f"Failed to process message: {str(e)}")
            .with_metadata("user_id", user_id)
            .build_error(status_code=500))


@router.post("/chat/{chat_id}/escalate", response_model=ApiResponse, tags=["chat"])
async def escalate_to_research(
    chat_id: str,
    response: Response,
    message_id: Optional[str] = None,
    http_request: Request = None,
    settings: Settings = Depends(get_settings)
) -> ApiResponse:
    """
    Escalate a chat conversation to deep research.

    Takes the last message or specified message and creates a deep research task.
    """

    response.headers.update(NO_STORE_HEADERS)

    user_id = getattr(http_request.state, 'user_id', 'mock-user-id')

    try:
        # P0-DR-KILL-001: Block escalation when kill switch is active
        if settings.deep_research_kill_switch:
            logger.warning(
                "escalation_blocked",
                message="Escalation blocked by kill switch",
                user_id=user_id,
                chat_id=chat_id,
                kill_switch=True
            )
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={
                    "error": "Deep Research feature is not available",
                    "error_code": "DEEP_RESEARCH_DISABLED",
                    "message": "Escalation to research is not available. This feature has been disabled.",
                    "kill_switch": True
                }
            )
        # Verify chat session (using HistoryService for consistent validation)
        chat_session = await HistoryService.get_session_with_permission_check(chat_id, user_id)

        current_tools = normalize_tools_state(getattr(chat_session, 'tools_enabled', None))
        if not current_tools.get('deep_research', False):
            metrics_collector.record_tool_call_blocked('deep_research', 'disabled')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "TOOL_DISABLED",
                    "message": "Deep research is disabled for this conversation",
                    "tool": "deep_research",
                }
            )

        # Get the message to research
        if message_id:
            target_message = await ChatMessageModel.get(message_id)
            if not target_message or target_message.chat_id != chat_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Message not found in this chat"
                )
        else:
            # Get the last user message
            target_message = await ChatMessageModel.find(
                ChatMessageModel.chat_id == chat_id,
                ChatMessageModel.role == MessageRole.USER
            ).sort(-ChatMessageModel.created_at).first_or_none()

            if not target_message:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No user message found to escalate"
                )

        # Use Research Coordinator to force deep research
        from ..services.research_coordinator import get_research_coordinator

        coordinator = get_research_coordinator()
        coordinated_response = await coordinator.execute_coordinated_research(
            query=target_message.content,
            user_id=user_id,
            chat_id=chat_id,
            force_research=True,  # Force research
            stream=True,
            allow_deep_research=True
        )

        if coordinated_response["type"] == "deep_research":
            # Add escalation message to chat
            escalation_message = (
                f"🔬 Escalated to deep research: \"{target_message.content[:100]}...\"\n\n"
                f"Research task started with ID: {coordinated_response['task_id']}\n"
                f"Estimated time: {coordinated_response['estimated_time_minutes']} minutes"
            )

            await chat_session.add_message(
                role=MessageRole.ASSISTANT,
                content=escalation_message,
                model="research_coordinator",
                metadata={
                    "escalation": True,
                    "original_message_id": target_message.id,
                    "task_id": coordinated_response["task_id"],
                    "stream_url": coordinated_response.get("stream_url")
                }
            )

            cache = await get_redis_cache()
            await cache.invalidate_chat_history(chat_id)
            await cache.invalidate_research_tasks(chat_id)

            logger.info(
                "Escalated chat to research",
                chat_id=chat_id,
                message_id=target_message.id,
                task_id=coordinated_response["task_id"]
            )

            return ApiResponse(
                success=True,
                message="Successfully escalated to deep research",
                data={
                    "task_id": coordinated_response["task_id"],
                    "stream_url": coordinated_response.get("stream_url"),
                    "estimated_time_minutes": coordinated_response["estimated_time_minutes"]
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to escalate to research"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error escalating to research", error=str(e), chat_id=chat_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to escalate to research"
        )


@router.get("/history/{chat_id}", response_model=ChatHistoryResponse, tags=["chat"])
async def get_chat_history(
    chat_id: str,
    response: Response,
    limit: int = 50,
    offset: int = 0,
    include_system: bool = False,
    include_research_tasks: bool = True,
    http_request: Request = None
) -> ChatHistoryResponse:
    """
    Get chat history for a specific chat session with optional research tasks.
    """

    response.headers.update(NO_STORE_HEADERS)

    user_id = getattr(http_request.state, 'user_id', 'mock-user-id')

    try:
        # Check cache first
        cache = await get_redis_cache()
        cached_history = await cache.get_chat_history(
            chat_id=chat_id,
            limit=limit,
            offset=offset,
            include_research=include_research_tasks
        )

        if cached_history:
            logger.debug("Returning cached chat history", chat_id=chat_id)
            return ChatHistoryResponse(**cached_history)

        # Verify access using HistoryService
        chat_session = await HistoryService.get_session_with_permission_check(chat_id, user_id)

        # Query messages with filters
        query = ChatMessageModel.find(ChatMessageModel.chat_id == chat_id)

        if not include_system:
            query = query.find(ChatMessageModel.role != MessageRole.SYSTEM)

        # Get total count
        total_count = await query.count()

        # Get messages with pagination
        messages_docs = await query.sort(-ChatMessageModel.created_at).skip(offset).limit(limit).to_list()

        # Get research tasks for this chat if requested
        research_tasks = {}
        if include_research_tasks:
            from ..models.task import Task as TaskModel

            # Find all research tasks associated with this chat
            task_docs = await TaskModel.find(
                TaskModel.chat_id == chat_id,
                TaskModel.task_type == "deep_research"
            ).to_list()

            # Index by task_id for fast lookup
            research_tasks = {task.id: {
                "task_id": task.id,
                "status": task.status.value,
                "progress": task.progress,
                "current_step": task.current_step,
                "total_steps": task.total_steps,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "error_message": task.error_message,
                "input_data": task.input_data,
                "result_data": task.result_data
            } for task in task_docs}

        # Convert to response schema with research task data
        messages = []
        for msg in messages_docs:
            message_data = ChatMessage(
                id=msg.id,
                chat_id=msg.chat_id,
                role=msg.role,
                content=msg.content,
                status=msg.status,
                created_at=msg.created_at,
                updated_at=msg.updated_at,
                metadata=msg.metadata,
                model=msg.model,
                tokens=msg.tokens,
                latency_ms=msg.latency_ms,
                task_id=msg.task_id
            )

            # Enrich with research task data if available
            if msg.task_id and msg.task_id in research_tasks:
                # Add research task data to metadata
                if not message_data.metadata:
                    message_data.metadata = {}
                message_data.metadata["research_task"] = research_tasks[msg.task_id]

            messages.append(message_data)

        has_more = offset + len(messages) < total_count

        logger.info(
            "Retrieved chat history with research tasks",
            chat_id=chat_id,
            message_count=len(messages),
            research_tasks_count=len(research_tasks),
            total_count=total_count,
            user_id=user_id
        )

        response_data = {
            "chat_id": chat_id,
            "messages": [msg.model_dump(mode='json') for msg in messages],
            "total_count": total_count,
            "has_more": has_more
        }

        # Cache the response
        await cache.set_chat_history(
            chat_id=chat_id,
            data=response_data,
            limit=limit,
            offset=offset,
            include_research=include_research_tasks
        )

        return ChatHistoryResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving chat history", error=str(e), chat_id=chat_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )


@router.get("/sessions", response_model=ChatSessionListResponse, tags=["chat"])
async def get_chat_sessions(
    response: Response,
    limit: int = 20,
    offset: int = 0,
    http_request: Request = None
) -> ChatSessionListResponse:
    """
    Get chat sessions for the authenticated user.
    """

    response.headers.update(NO_STORE_HEADERS)
    user_id = getattr(http_request.state, 'user_id', 'mock-user-id')

    try:
        # Use HistoryService for consistent session retrieval
        result = await HistoryService.get_chat_sessions(
            user_id=user_id,
            limit=limit,
            offset=offset
        )

        logger.info(
            "Retrieved chat sessions",
            user_id=user_id,
            session_count=len(result["sessions"]),
            total_count=result["total_count"]
        )

        return ChatSessionListResponse(
            sessions=result["sessions"],
            total_count=result["total_count"],
            has_more=result["has_more"]
        )

    except Exception as e:
        logger.error("Error retrieving chat sessions", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat sessions"
        )


@router.get("/sessions/{session_id}/research", tags=["chat"])
async def get_session_research_tasks(
    session_id: str,
    response: Response,
    limit: int = 20,
    offset: int = 0,
    status_filter: Optional[str] = None,
    http_request: Request = None
):
    """
    Get all research tasks associated with a chat session.
    """

    response.headers.update(NO_STORE_HEADERS)

    user_id = getattr(http_request.state, 'user_id', 'mock-user-id')

    try:
        # Verify access using HistoryService
        await HistoryService.get_session_with_permission_check(session_id, user_id)

        cache = await get_redis_cache()

        # Check cache first for research tasks list
        cached_tasks = await cache.get_research_tasks(
            session_id=session_id,
            limit=limit,
            offset=offset,
            status_filter=status_filter
        )

        if cached_tasks:
            logger.debug(
                "Returning cached research tasks",
                session_id=session_id,
                limit=limit,
                offset=offset,
                status_filter=status_filter
            )
            return cached_tasks

        # Import here to avoid circular imports
        from ..models.task import Task as TaskModel

        # Build query for research tasks
        query = TaskModel.find(
            TaskModel.chat_id == session_id,
            TaskModel.task_type == "deep_research"
        )

        # Apply status filter if provided
        if status_filter:
            query = query.find(TaskModel.status == status_filter)

        # Get total count
        total_count = await query.count()

        # Get tasks with pagination
        task_docs = await query.sort(-TaskModel.created_at).skip(offset).limit(limit).to_list()

        # Convert to response format
        research_tasks = []
        for task in task_docs:
            research_tasks.append({
                "task_id": task.id,
                "status": task.status.value,
                "progress": task.progress,
                "current_step": task.current_step,
                "total_steps": task.total_steps,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "error_message": task.error_message,
                "input_data": task.input_data,
                "result_data": task.result_data,
                "metadata": task.metadata
            })

        has_more = offset + len(research_tasks) < total_count

        logger.info(
            "Retrieved research tasks for session",
            session_id=session_id,
            task_count=len(research_tasks),
            total_count=total_count,
            user_id=user_id
        )

        response_payload = {
            "session_id": session_id,
            "research_tasks": research_tasks,
            "total_count": total_count,
            "has_more": has_more
        }

        await cache.set_research_tasks(
            session_id=session_id,
            data=response_payload,
            limit=limit,
            offset=offset,
            status_filter=status_filter
        )

        return response_payload

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving research tasks", error=str(e), session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve research tasks"
        )


@router.patch("/sessions/{chat_id}", response_model=ApiResponse, tags=["chat"])
async def update_chat_session(
    chat_id: str,
    update_request: ChatSessionUpdateRequest,
    http_request: Request,
    response: Response
) -> ApiResponse:
    """
    Update a chat session (rename, pin/unpin).
    """

    response.headers.update(NO_STORE_HEADERS)
    user_id = getattr(http_request.state, 'user_id', 'mock-user-id')

    try:
        # Verify access using HistoryService
        chat_session = await HistoryService.get_session_with_permission_check(chat_id, user_id)

        # Update fields if provided
        update_data = {}
        if update_request.title is not None:
            update_data['title'] = update_request.title
        if update_request.pinned is not None:
            update_data['pinned'] = update_request.pinned

        if update_data:
            update_data['updated_at'] = datetime.utcnow()
            await chat_session.update({"$set": update_data})

        logger.info("Chat session updated",
                   chat_id=chat_id,
                   user_id=user_id,
                   updates=update_data)

        return ApiResponse(
            success=True,
            message="Chat session updated successfully",
            data={"chat_id": chat_id, "updated_fields": list(update_data.keys())}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update chat session",
                    error=str(e),
                    chat_id=chat_id,
                    user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update chat session"
        )


@router.delete("/sessions/{chat_id}", response_model=ApiResponse, tags=["chat"])
async def delete_chat_session(
    chat_id: str,
    http_request: Request,
    response: Response
) -> ApiResponse:
    """
    Delete a chat session and all its messages.
    """

    response.headers.update(NO_STORE_HEADERS)
    user_id = getattr(http_request.state, 'user_id', 'mock-user-id')

    try:
        # Verify access using HistoryService
        chat_session = await HistoryService.get_session_with_permission_check(chat_id, user_id)

        cache = await get_redis_cache()

        # Delete all messages in the chat
        await ChatMessageModel.find(ChatMessageModel.chat_id == chat_id).delete()

        # Delete the chat session
        await chat_session.delete()

        await cache.invalidate_all_for_chat(chat_id)

        logger.info("Deleted chat session", chat_id=chat_id, user_id=user_id)

        return ApiResponse(
            success=True,
            message="Chat session deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting chat session", error=str(e), chat_id=chat_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat session"
        )
