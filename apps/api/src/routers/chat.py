"""
Chat API endpoints.
"""

import time
from datetime import datetime
from typing import Optional
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse

from ..core.config import get_settings, Settings
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


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
async def send_chat_message(
    request: ChatRequest,
    http_request: Request,
    settings: Settings = Depends(get_settings)
) -> ChatResponse:
    """
    Send a chat message and get AI response.
    
    Handles both new conversations and continuing existing ones.
    Supports streaming and non-streaming responses.
    """
    
    start_time = time.time()
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

        # Generate AI response using SAPTIVA
        from ..services.saptiva_client import get_saptiva_client

        saptiva_client = await get_saptiva_client()
        saptiva_response = await saptiva_client.chat_completion(
            messages=message_history,
            model=request.model or "SAPTIVA_CORTEX",
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 1024,
            stream=request.stream or False
        )

        # Extract response content
        ai_response_content = saptiva_response.choices[0]["message"]["content"]

        # Extract usage info if available
        usage_info = saptiva_response.usage or {}
        tokens_used = usage_info.get("total_tokens", 0)
        
        # Add AI response message
        ai_message = await chat_session.add_message(
            role=MessageRole.ASSISTANT,
            content=ai_response_content,
            model=request.model or "SAPTIVA_CORTEX",
            tokens=tokens_used,
            metadata={
                "saptiva_response_id": saptiva_response.id,
                "usage": usage_info,
                "finish_reason": saptiva_response.choices[0].get("finish_reason", "stop")
            }
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(
            "Generated AI response",
            message_id=ai_message.id,
            chat_id=chat_session.id,
            processing_time_ms=processing_time
        )
        
        return ChatResponse(
            chat_id=chat_session.id,
            message_id=ai_message.id,
            content=ai_response_content,
            role=MessageRole.ASSISTANT,
            model=request.model or "SAPTIVA_CORTEX",
            created_at=ai_message.created_at,
            tokens=tokens_used,
            latency_ms=int(processing_time),
            finish_reason=saptiva_response.choices[0].get("finish_reason", "completed")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error("Error processing chat message", error=str(e), traceback=traceback.format_exc(), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )


@router.get("/history/{chat_id}", response_model=ChatHistoryResponse, tags=["chat"])
async def get_chat_history(
    chat_id: str,
    limit: int = 50,
    offset: int = 0,
    include_system: bool = False,
    http_request: Request = None
) -> ChatHistoryResponse:
    """
    Get chat history for a specific chat session.
    """
    
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
        
        # Query messages with filters
        query = ChatMessageModel.find(ChatMessageModel.chat_id == chat_id)
        
        if not include_system:
            query = query.find(ChatMessageModel.role != MessageRole.SYSTEM)
        
        # Get total count
        total_count = await query.count()
        
        # Get messages with pagination
        messages_docs = await query.sort(-ChatMessageModel.created_at).skip(offset).limit(limit).to_list()
        
        # Convert to response schema
        messages = [
            ChatMessage(
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
            ) for msg in messages_docs
        ]
        
        has_more = offset + len(messages) < total_count
        
        logger.info(
            "Retrieved chat history", 
            chat_id=chat_id, 
            message_count=len(messages),
            total_count=total_count,
            user_id=user_id
        )
        
        return ChatHistoryResponse(
            chat_id=chat_id,
            messages=messages,
            total_count=total_count,
            has_more=has_more
        )
        
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
    limit: int = 20,
    offset: int = 0,
    http_request: Request = None
) -> ChatSessionListResponse:
    """
    Get chat sessions for the authenticated user.
    """
    
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


@router.delete("/sessions/{chat_id}", response_model=ApiResponse, tags=["chat"])
async def delete_chat_session(
    chat_id: str,
    http_request: Request
) -> ApiResponse:
    """
    Delete a chat session and all its messages.
    """
    
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
        
        # Delete all messages in the chat
        await ChatMessageModel.find(ChatMessageModel.chat_id == chat_id).delete()
        
        # Delete the chat session
        await chat_session.delete()
        
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