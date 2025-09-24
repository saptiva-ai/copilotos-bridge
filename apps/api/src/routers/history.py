"""
Unified history API endpoints for chat + research timeline.
"""

import time
from datetime import datetime, timedelta
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Response
from fastapi.responses import JSONResponse

from ..core.config import get_settings, Settings
from ..models.chat import ChatSession as ChatSessionModel, ChatMessage as ChatMessageModel, MessageRole
from ..models.history import HistoryEventType
from ..schemas.chat import ChatHistoryResponse, ChatMessage, ChatSessionListResponse, ChatSession
from ..services.history_service import HistoryService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/history", response_model=ChatSessionListResponse, tags=["history"])
async def get_chat_history_overview(
    limit: int = Query(default=20, ge=1, le=100, description="Number of sessions to retrieve"),
    offset: int = Query(default=0, ge=0, description="Number of sessions to skip"),
    search: Optional[str] = Query(default=None, description="Search in session titles"),
    date_from: Optional[datetime] = Query(default=None, description="Filter sessions from date"),
    date_to: Optional[datetime] = Query(default=None, description="Filter sessions to date"),
    http_request: Request = None
) -> ChatSessionListResponse:
    """
    Get chat session history overview with optional filtering.
    """
    
    user_id = getattr(http_request.state, 'user_id', 'anonymous')
    
    try:
        # Build query
        query = ChatSessionModel.find(ChatSessionModel.user_id == user_id)
        
        # Apply date filters
        if date_from:
            query = query.find(ChatSessionModel.created_at >= date_from)
        if date_to:
            query = query.find(ChatSessionModel.created_at <= date_to)
        
        # Apply search filter
        if search:
            # Case-insensitive search in title
            query = query.find({"title": {"$regex": search, "$options": "i"}})
        
        # Get total count
        total_count = await query.count()
        
        # Get sessions with pagination, ordered by most recent
        sessions_docs = await query.sort(-ChatSessionModel.updated_at).skip(offset).limit(limit).to_list()
        
        # Convert to response schema
        sessions = []
        for session in sessions_docs:
            sessions.append(ChatSession(
                id=session.id,
                title=session.title,
                user_id=session.user_id,
                created_at=session.created_at,
                updated_at=session.updated_at,
                message_count=session.message_count,
                settings=session.settings.model_dump() if hasattr(session.settings, 'model_dump') else session.settings
            ))
        
        has_more = offset + len(sessions) < total_count
        
        logger.info(
            "Retrieved chat history overview",
            user_id=user_id,
            session_count=len(sessions),
            total_count=total_count,
            search_term=search
        )
        
        return ChatSessionListResponse(
            sessions=sessions,
            total_count=total_count,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error("Error retrieving chat history overview", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )


@router.get("/history/{chat_id}", response_model=ChatHistoryResponse, tags=["history"])
async def get_chat_detailed_history(
    chat_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="Number of messages to retrieve"),
    offset: int = Query(default=0, ge=0, description="Number of messages to skip"),
    include_system: bool = Query(default=False, description="Include system messages"),
    message_type: Optional[MessageRole] = Query(default=None, description="Filter by message role"),
    http_request: Request = None
) -> ChatHistoryResponse:
    """
    Get detailed chat history for a specific session.
    """
    
    user_id = getattr(http_request.state, 'user_id', 'anonymous')
    
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
        
        # Build message query
        query = ChatMessageModel.find(ChatMessageModel.chat_id == chat_id)
        
        # Apply filters
        if not include_system:
            query = query.find(ChatMessageModel.role != MessageRole.SYSTEM)
        
        if message_type:
            query = query.find(ChatMessageModel.role == message_type)
        
        # Get total count
        total_count = await query.count()
        
        # Get messages with pagination (reverse chronological order)
        messages_docs = await query.sort(-ChatMessageModel.created_at).skip(offset).limit(limit).to_list()
        
        # Convert to response schema (reverse to get chronological order for display)
        messages = []
        for msg in reversed(messages_docs):
            messages.append(ChatMessage(
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
            ))
        
        has_more = offset + len(messages) < total_count
        
        logger.info(
            "Retrieved detailed chat history",
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
        logger.error("Error retrieving detailed chat history", error=str(e), chat_id=chat_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )


@router.get("/history/{chat_id}/export", tags=["history"])
async def export_chat_history(
    chat_id: str,
    format: str = Query(default="json", pattern="^(json|csv|txt)$", description="Export format"),
    include_metadata: bool = Query(default=False, description="Include message metadata"),
    http_request: Request = None
):
    """
    Export chat history in various formats.
    """
    
    user_id = getattr(http_request.state, 'user_id', 'anonymous')
    
    try:
        # Verify access
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
        
        # Get all messages
        messages = await ChatMessageModel.find(
            ChatMessageModel.chat_id == chat_id
        ).sort(ChatMessageModel.created_at).to_list()
        
        if format == "json":
            # Export as JSON
            export_data = {
                "chat_session": {
                    "id": chat_session.id,
                    "title": chat_session.title,
                    "created_at": chat_session.created_at.isoformat(),
                    "message_count": len(messages)
                },
                "messages": []
            }
            
            for msg in messages:
                msg_data = {
                    "role": msg.role.value,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                }
                
                if include_metadata:
                    msg_data.update({
                        "id": msg.id,
                        "status": msg.status.value,
                        "model": msg.model,
                        "tokens": msg.tokens,
                        "latency_ms": msg.latency_ms,
                        "metadata": msg.metadata
                    })
                
                export_data["messages"].append(msg_data)
            
            return export_data
        
        elif format == "txt":
            # Export as plain text
            lines = [f"Chat: {chat_session.title}", f"Created: {chat_session.created_at}", "=" * 50, ""]
            
            for msg in messages:
                timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                lines.append(f"[{timestamp}] {msg.role.value.upper()}: {msg.content}")
                lines.append("")
            
            return {"content": "\n".join(lines)}
        
        else:
            # CSV format
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Headers
            headers = ["timestamp", "role", "content"]
            if include_metadata:
                headers.extend(["message_id", "status", "model", "tokens", "latency_ms"])
            
            writer.writerow(headers)
            
            # Data rows
            for msg in messages:
                row = [
                    msg.created_at.isoformat(),
                    msg.role.value,
                    msg.content.replace('\n', '\\n')  # Escape newlines
                ]
                
                if include_metadata:
                    row.extend([
                        msg.id,
                        msg.status.value,
                        msg.model or "",
                        msg.tokens or 0,
                        msg.latency_ms or 0
                    ])
                
                writer.writerow(row)
            
            return {"content": output.getvalue()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error exporting chat history", error=str(e), chat_id=chat_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export chat history"
        )


@router.get("/history/stats", tags=["history"])
async def get_user_chat_stats(
    http_request: Request,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze")
):
    """
    Get chat usage statistics for the user.
    """
    
    user_id = getattr(http_request.state, 'user_id', 'anonymous')
    
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get session stats
        session_count = await ChatSessionModel.find(
            ChatSessionModel.user_id == user_id,
            ChatSessionModel.created_at >= start_date
        ).count()
        
        # Get message stats
        total_messages = await ChatMessageModel.find(
            ChatMessageModel.chat_id.regex(".*"),  # All user's messages
            ChatMessageModel.created_at >= start_date
        ).count()
        
        user_messages = await ChatMessageModel.find(
            ChatMessageModel.role == MessageRole.USER,
            ChatMessageModel.created_at >= start_date
        ).count()
        
        ai_messages = await ChatMessageModel.find(
            ChatMessageModel.role == MessageRole.ASSISTANT,
            ChatMessageModel.created_at >= start_date
        ).count()
        
        # Get most active days
        # This would require aggregation pipeline in production
        # For now, return basic stats
        
        stats = {
            "period_days": days,
            "session_count": session_count,
            "total_messages": total_messages,
            "user_messages": user_messages,
            "ai_messages": ai_messages,
            "avg_messages_per_session": total_messages / session_count if session_count > 0 else 0,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        
        logger.info("Retrieved user chat stats", user_id=user_id, stats=stats)
        
        return stats
        
    except Exception as e:
        logger.error("Error retrieving chat stats", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat statistics"
        )


# ======================================
# UNIFIED HISTORY ENDPOINTS (New)
# ======================================

# Cache headers for history responses
NO_STORE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


@router.get("/history/{chat_id}/unified", tags=["history"])
async def get_unified_chat_history(
    chat_id: str,
    response: Response,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200, description="Number of events to return"),
    offset: int = Query(default=0, ge=0, description="Number of events to skip"),
    event_types: Optional[str] = Query(None, description="Comma-separated event types filter"),
    include_research: bool = Query(default=True, description="Include research events"),
    include_sources: bool = Query(default=False, description="Include source discovery events"),
    settings: Settings = Depends(get_settings)
) -> JSONResponse:
    """
    Get unified chat + research history with pagination and caching.

    Returns events ordered chronologically with support for:
    - Pagination (limit/offset)
    - Event type filtering
    - Redis caching for performance
    - P95 latency <= 600ms target
    """

    start_time = time.time()
    response.headers.update(NO_STORE_HEADERS)
    user_id = getattr(request.state, 'user_id', 'mock-user-id')

    try:
        # Verify chat session exists and user has access
        chat_session = await ChatSessionModel.get(chat_id)
        if not chat_session:
            return JSONResponse(
                content={
                    "error": "Chat session not found",
                    "chat_id": chat_id,
                    "message": "The requested chat session does not exist"
                },
                status_code=status.HTTP_404_NOT_FOUND,
                headers=NO_STORE_HEADERS
            )

        if chat_session.user_id != user_id:
            return JSONResponse(
                content={
                    "error": "Access denied",
                    "chat_id": chat_id,
                    "message": "You don't have permission to access this chat session"
                },
                status_code=status.HTTP_403_FORBIDDEN,
                headers=NO_STORE_HEADERS
            )

        # Parse event types filter
        event_type_filter = None
        if event_types:
            try:
                event_type_filter = [HistoryEventType(t.strip()) for t in event_types.split(',')]
            except ValueError as e:
                return JSONResponse(
                    content={
                        "error": "Invalid event type",
                        "message": f"Invalid event type in filter: {str(e)}"
                    },
                    status_code=status.HTTP_400_BAD_REQUEST,
                    headers=NO_STORE_HEADERS
                )

        # Build event type filter based on parameters
        if event_type_filter is None:
            event_type_filter = [HistoryEventType.CHAT_MESSAGE]

            if include_research:
                event_type_filter.extend([
                    HistoryEventType.RESEARCH_STARTED,
                    HistoryEventType.RESEARCH_PROGRESS,
                    HistoryEventType.RESEARCH_COMPLETED,
                    HistoryEventType.RESEARCH_FAILED
                ])

            if include_sources:
                event_type_filter.extend([
                    HistoryEventType.SOURCE_FOUND,
                    HistoryEventType.EVIDENCE_DISCOVERED
                ])

        # Get timeline from service (includes caching)
        timeline_data = await HistoryService.get_chat_timeline(
            chat_id=chat_id,
            limit=limit,
            offset=offset,
            event_types=event_type_filter,
            use_cache=True
        )

        processing_time = (time.time() - start_time) * 1000

        # Add performance metadata
        timeline_data.update({
            "latency_ms": int(processing_time),
            "user_id": user_id,
            "filters": {
                "include_research": include_research,
                "include_sources": include_sources,
                "event_types": [et.value for et in event_type_filter] if event_type_filter else None
            }
        })

        logger.info(
            "Retrieved unified chat history",
            chat_id=chat_id,
            user_id=user_id,
            event_count=len(timeline_data["events"]),
            total_count=timeline_data["total_count"],
            latency_ms=processing_time,
            limit=limit,
            offset=offset
        )

        return JSONResponse(
            content=timeline_data,
            headers=NO_STORE_HEADERS
        )

    except HTTPException:
        raise
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error(
            "Error retrieving unified chat history",
            chat_id=chat_id,
            user_id=user_id,
            error=str(e),
            latency_ms=processing_time
        )
        return JSONResponse(
            content={
                "error": "Internal server error",
                "chat_id": chat_id,
                "message": "Failed to retrieve chat history",
                "latency_ms": int(processing_time)
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers=NO_STORE_HEADERS
        )


@router.get("/history/{chat_id}/research/{task_id}", tags=["history"])
async def get_research_timeline(
    chat_id: str,
    task_id: str,
    response: Response,
    request: Request,
    settings: Settings = Depends(get_settings)
) -> JSONResponse:
    """
    Get research-specific timeline for a task.

    Returns all research events (started, progress, sources, completed) for a specific task.
    """

    start_time = time.time()
    response.headers.update(NO_STORE_HEADERS)
    user_id = getattr(request.state, 'user_id', 'mock-user-id')

    try:
        # Verify chat session access
        chat_session = await ChatSessionModel.get(chat_id)
        if not chat_session:
            return JSONResponse(
                content={"error": "Chat session not found"},
                status_code=status.HTTP_404_NOT_FOUND,
                headers=NO_STORE_HEADERS
            )

        if chat_session.user_id != user_id:
            return JSONResponse(
                content={"error": "Access denied"},
                status_code=status.HTTP_403_FORBIDDEN,
                headers=NO_STORE_HEADERS
            )

        # Get research timeline
        events = await HistoryService.get_research_timeline(chat_id, task_id)

        processing_time = (time.time() - start_time) * 1000

        result = {
            "chat_id": chat_id,
            "task_id": task_id,
            "events": [event.model_dump() for event in events],
            "event_count": len(events),
            "latency_ms": int(processing_time)
        }

        logger.info(
            "Retrieved research timeline",
            chat_id=chat_id,
            task_id=task_id,
            user_id=user_id,
            event_count=len(events),
            latency_ms=processing_time
        )

        return JSONResponse(
            content=result,
            headers=NO_STORE_HEADERS
        )

    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error(
            "Error retrieving research timeline",
            chat_id=chat_id,
            task_id=task_id,
            user_id=user_id,
            error=str(e),
            latency_ms=processing_time
        )
        return JSONResponse(
            content={
                "error": "Failed to retrieve research timeline",
                "latency_ms": int(processing_time)
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers=NO_STORE_HEADERS
        )


@router.get("/history/{chat_id}/status", tags=["history"])
async def get_chat_status(
    chat_id: str,
    response: Response,
    request: Request,
    settings: Settings = Depends(get_settings)
) -> JSONResponse:
    """
    Get current status of chat including active research tasks.

    Lightweight endpoint for UI status checking.
    """

    start_time = time.time()
    response.headers.update(NO_STORE_HEADERS)
    user_id = getattr(request.state, 'user_id', 'mock-user-id')

    try:
        # Verify chat session access
        chat_session = await ChatSessionModel.get(chat_id)
        if not chat_session:
            return JSONResponse(
                content={"error": "Chat session not found"},
                status_code=status.HTTP_404_NOT_FOUND,
                headers=NO_STORE_HEADERS
            )

        if chat_session.user_id != user_id:
            return JSONResponse(
                content={"error": "Access denied"},
                status_code=status.HTTP_403_FORBIDDEN,
                headers=NO_STORE_HEADERS
            )

        # Get recent events for status check
        recent_timeline = await HistoryService.get_chat_timeline(
            chat_id=chat_id,
            limit=10,
            offset=0,
            event_types=None,  # All types
            use_cache=False  # Always fresh for status
        )

        # Find active research tasks
        active_research = []
        for event in recent_timeline["events"]:
            if (event["event_type"] in ["research_started", "research_progress"] and
                event["status"] == "processing"):
                active_research.append({
                    "task_id": event["task_id"],
                    "progress": event.get("research_data", {}).get("progress", 0),
                    "current_step": event.get("research_data", {}).get("current_step"),
                    "started_at": event["timestamp"]
                })

        processing_time = (time.time() - start_time) * 1000

        result = {
            "chat_id": chat_id,
            "status": "active" if active_research else "idle",
            "message_count": chat_session.message_count,
            "last_activity": chat_session.updated_at.isoformat(),
            "active_research": active_research,
            "active_research_count": len(active_research),
            "latency_ms": int(processing_time)
        }

        return JSONResponse(
            content=result,
            headers=NO_STORE_HEADERS
        )

    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error(
            "Error retrieving chat status",
            chat_id=chat_id,
            user_id=user_id,
            error=str(e),
            latency_ms=processing_time
        )
        return JSONResponse(
            content={
                "error": "Failed to retrieve chat status",
                "latency_ms": int(processing_time)
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers=NO_STORE_HEADERS
        )