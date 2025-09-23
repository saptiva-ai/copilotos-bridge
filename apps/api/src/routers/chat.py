"""
Chat API endpoints.
"""

import time
from datetime import datetime
from typing import Optional
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse

from ..core.config import get_settings, Settings
from ..core.redis_cache import get_redis_cache
from ..core.telemetry import trace_span, metrics_collector
from ..models.chat import ChatSession as ChatSessionModel, ChatMessage as ChatMessageModel, MessageRole, MessageStatus
from ..schemas.chat import (
    ChatRequest, 
    ChatResponse, 
    ChatHistoryRequest, 
    ChatHistoryResponse,
    ChatSessionListResponse,
    ChatMessage,
    ChatSession
)
from ..schemas.common import ApiResponse

logger = structlog.get_logger(__name__)
router = APIRouter()

NO_STORE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


@router.post("/chat", tags=["chat"])
async def send_chat_message(
    request: ChatRequest,
    http_request: Request,
    response: Response,
    settings: Settings = Depends(get_settings)
) -> JSONResponse:
    """
    Send a chat message and get AI response.
    
    Handles both new conversations and continuing existing ones.
    Supports streaming and non-streaming responses.
    """
    
    start_time = time.time()
    response.headers.update(NO_STORE_HEADERS)
    user_id = getattr(http_request.state, 'user_id', 'mock-user-id')
    
    try:
        # Get or create chat session
        if request.chat_id:
            chat_session = await ChatSessionModel.get(request.chat_id)
            if not chat_session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )
            
            if chat_session.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to chat session"
                )
        else:
            # Create new chat session
            chat_session = ChatSessionModel(
                title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
                user_id=user_id
            )
            await chat_session.insert()
            logger.info("Created new chat session", chat_id=chat_session.id, user_id=user_id)
        
        # Add user message
        user_message = await chat_session.add_message(
            role=MessageRole.USER,
            content=request.message,
            metadata={"source": "api"}
        )

        logger.info("Added user message", message_id=user_message.id, chat_id=chat_session.id)

        cache = await get_redis_cache()
        await cache.invalidate_chat_history(chat_session.id)
        
        # Get conversation history for context
        message_history = []
        if request.context and len(request.context) > 0:
            # Use provided context
            for ctx_msg in request.context:
                message_history.append({
                    "role": ctx_msg.get("role", "user"),
                    "content": ctx_msg.get("content", "")
                })
        else:
            # Get recent messages from the session for context
            recent_messages = await ChatMessageModel.find(
                ChatMessageModel.chat_id == chat_session.id
            ).sort(-ChatMessageModel.created_at).limit(10).to_list()

            # Reverse to get chronological order and convert to format
            for msg in reversed(recent_messages):
                message_history.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        # Add current user message
        message_history.append({
            "role": "user",
            "content": request.message
        })

        # Use Research Coordinator for intelligent routing
        from ..services.research_coordinator import get_research_coordinator

        coordinator = get_research_coordinator()

        # Check if deep research tools are enabled
        force_research = False
        if request.tools_enabled and request.tools_enabled.get('deep_research', False):
            force_research = True

        # Execute coordinated research (chat or deep research) with tracing
        async with trace_span(
            "coordinate_research",
            {
                "chat.id": chat_session.id,
                "chat.message_length": len(request.message),
                "chat.force_research": force_research,
                "chat.stream": getattr(request, 'stream', False)
            }
        ):
            coordinated_response = await coordinator.execute_coordinated_research(
                query=request.message,
                user_id=user_id,
                chat_id=chat_session.id,
                force_research=force_research,
                stream=getattr(request, 'stream', False)
            )

        if coordinated_response["type"] == "deep_research":
            # Deep research initiated - return task info
            task_id = coordinated_response["task_id"]

            # Add research initiation message
            research_message = (
                f"🔬 Starting deep research: \"{request.message[:100]}...\"\n\n"
                f"Research complexity: {coordinated_response['decision']['complexity']['score']:.2f}\n"
                f"Estimated time: {coordinated_response['estimated_time_minutes']} minutes\n"
                f"Task ID: {task_id}"
            )

            ai_message = await chat_session.add_message(
                role=MessageRole.ASSISTANT,
                content=research_message,
                model="research_coordinator",
                task_id=task_id,
                metadata={
                    "research_initiated": True,
                    "task_id": task_id,
                    "stream_url": coordinated_response.get("stream_url"),
                    "decision": coordinated_response["decision"],
                    "estimated_time_minutes": coordinated_response["estimated_time_minutes"]
                }
            )

            await cache.invalidate_chat_history(chat_session.id)
            await cache.invalidate_research_tasks(chat_session.id)

            response_data = ChatResponse(
                chat_id=chat_session.id,
                message_id=ai_message.id,
                content=research_message,
                role=MessageRole.ASSISTANT,
                model="research_coordinator",
                created_at=ai_message.created_at,
                task_id=task_id,
                latency_ms=int(coordinated_response["processing_time_ms"]),
                finish_reason="research_initiated"
            )
            return JSONResponse(
                content=response_data.model_dump(),
                headers=NO_STORE_HEADERS
            )

        elif coordinated_response["type"] == "chat":
            # Regular chat response
            saptiva_response = coordinated_response["response"]

            # Extract response content
            message = saptiva_response.choices[0]["message"]
            ai_response_content = message.get("content") or message.get("reasoning_content", "")

            # Extract usage info if available
            usage_info = saptiva_response.usage or {}
            tokens_used = usage_info.get("total_tokens", 0)
            finish_reason = saptiva_response.choices[0].get("finish_reason", "stop")

            # Add AI response message
            ai_message = await chat_session.add_message(
                role=MessageRole.ASSISTANT,
                content=ai_response_content,
                model=request.model or "SAPTIVA_CORTEX",
                tokens=tokens_used,
                metadata={
                    "saptiva_response_id": saptiva_response.id,
                    "usage": usage_info,
                    "finish_reason": saptiva_response.choices[0].get("finish_reason", "stop"),
                    "coordination_decision": coordinated_response["decision"],
                    "escalation_available": coordinated_response.get("escalation_available", False)
                }
            )

            await cache.invalidate_chat_history(chat_session.id)

        else:
            # Error fallback
            error_message = f"Processing error: {coordinated_response.get('error', 'Unknown error')}"
            ai_message = await chat_session.add_message(
                role=MessageRole.ASSISTANT,
                content=error_message,
                model="error_handler",
                metadata={
                    "error": True,
                    "error_details": coordinated_response
                }
            )

            await cache.invalidate_chat_history(chat_session.id)

            # Set default values for error case
            ai_response_content = error_message
            tokens_used = 0
            finish_reason = "error"

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            "Generated AI response",
            message_id=ai_message.id,
            chat_id=chat_session.id,
            processing_time_ms=processing_time
        )

        # Record chat metrics
        metrics_collector.record_chat_message(
            model=request.model or "SAPTIVA_CORTEX",
            tokens=tokens_used or 0,
            duration=processing_time / 1000  # Convert to seconds
        )

        response_data = ChatResponse(
            chat_id=chat_session.id,
            message_id=ai_message.id,
            content=ai_response_content,
            role=MessageRole.ASSISTANT,
            model=request.model or "SAPTIVA_CORTEX",
            created_at=ai_message.created_at,
            tokens=tokens_used,
            latency_ms=int(processing_time),
            finish_reason=finish_reason
        )
        logger.info("Setting cache headers", headers=NO_STORE_HEADERS)
        json_response = JSONResponse(
            content=response_data.model_dump(),
            headers=NO_STORE_HEADERS
        )
        logger.info("Response headers set", response_headers=dict(json_response.headers))
        return json_response
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error("Error processing chat message", error=str(e), traceback=traceback.format_exc(), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )


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
        # Verify chat session
        chat_session = await ChatSessionModel.get(chat_id)
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )

        if chat_session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to chat session"
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
            stream=True
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

        # Verify chat session exists and user has access
        chat_session = await ChatSessionModel.get(chat_id)
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )

        if chat_session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to chat session"
            )

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
            "messages": [msg.model_dump() for msg in messages],
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
        # Query user's chat sessions
        query = ChatSessionModel.find(ChatSessionModel.user_id == user_id)
        
        # Get total count
        total_count = await query.count()
        
        # Get sessions with pagination, ordered by most recent
        sessions_docs = await query.sort(-ChatSessionModel.updated_at).skip(offset).limit(limit).to_list()
        
        # Convert to response schema
        sessions = [
            ChatSession(
                id=session.id,
                title=session.title,
                user_id=session.user_id,
                created_at=session.created_at,
                updated_at=session.updated_at,
                message_count=session.message_count,
                settings=session.settings.model_dump() if hasattr(session.settings, 'model_dump') else session.settings
            ) for session in sessions_docs
        ]
        
        has_more = offset + len(sessions) < total_count
        
        logger.info(
            "Retrieved chat sessions",
            user_id=user_id,
            session_count=len(sessions),
            total_count=total_count
        )
        
        return ChatSessionListResponse(
            sessions=sessions,
            total_count=total_count,
            has_more=has_more
        )
        
    except Exception as e:
        import traceback
        logger.error("Error retrieving chat sessions", error=str(e), traceback=traceback.format_exc(), user_id=user_id)
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
        cache = await get_redis_cache()

        # Verify chat session exists and user has access
        chat_session = await ChatSessionModel.get(session_id)
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )

        if chat_session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to chat session"
            )

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
        # Verify chat session exists and user has access
        chat_session = await ChatSessionModel.get(chat_id)
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        if chat_session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to chat session"
            )
        
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
