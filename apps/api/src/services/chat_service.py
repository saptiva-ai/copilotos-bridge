"""
Chat Service - Business Logic Layer

Extracts business logic from chat router for better separation of concerns.
Handles chat session management, message processing, and AI response generation.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import structlog
from fastapi import HTTPException, status

from ..core.config import Settings
from ..core.redis_cache import get_redis_cache
from ..models.chat import ChatSession as ChatSessionModel, ChatMessage as ChatMessageModel, MessageRole
from ..services.saptiva_client import SaptivaClient, build_payload
from ..services.tools import normalize_tools_state
from ..core.telemetry import trace_span

logger = structlog.get_logger(__name__)


class ChatService:
    """Service for chat operations"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.saptiva_client = SaptivaClient()

    async def get_or_create_session(
        self,
        chat_id: Optional[str],
        user_id: str,
        first_message: str,
        tools_enabled: Dict[str, bool]
    ) -> ChatSessionModel:
        """
        Get existing chat session or create new one.

        Args:
            chat_id: Optional existing chat ID
            user_id: User ID
            first_message: First message content (for new session title)
            tools_enabled: Tools configuration

        Returns:
            ChatSession model

        Raises:
            HTTPException: If chat not found or access denied
        """
        tools_map = normalize_tools_state(tools_enabled)

        if chat_id:
            # Get existing session
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

            # Update tools if changed
            existing_tools = normalize_tools_state(getattr(chat_session, 'tools_enabled', None))
            if existing_tools != tools_map:
                await chat_session.update({"$set": {
                    "tools_enabled": tools_map,
                    "updated_at": datetime.utcnow()
                }})
                chat_session.tools_enabled = tools_map

            return chat_session
        else:
            # Create new session
            title = first_message[:50] + "..." if len(first_message) > 50 else first_message
            chat_session = ChatSessionModel(
                title=title,
                user_id=user_id,
                tools_enabled=tools_map
            )
            await chat_session.insert()
            logger.info("Created new chat session", chat_id=chat_session.id, user_id=user_id)
            return chat_session

    async def build_message_context(
        self,
        chat_session: ChatSessionModel,
        current_message: str,
        provided_context: Optional[List[Dict]] = None
    ) -> List[Dict[str, str]]:
        """
        Build conversation context for AI.

        Args:
            chat_session: Chat session
            current_message: Current user message
            provided_context: Optional explicit context

        Returns:
            List of message dicts with role and content
        """
        message_history = []

        if provided_context and len(provided_context) > 0:
            # Use provided context
            for ctx_msg in provided_context:
                message_history.append({
                    "role": ctx_msg.get("role", "user"),
                    "content": ctx_msg.get("content", "")
                })
        else:
            # Get recent messages from session
            recent_messages = await ChatMessageModel.find(
                ChatMessageModel.chat_id == chat_session.id
            ).sort(-ChatMessageModel.created_at).limit(10).to_list()

            # Reverse to chronological order
            for msg in reversed(recent_messages):
                message_history.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        # Add current message
        message_history.append({
            "role": "user",
            "content": current_message
        })

        return message_history

    async def process_with_saptiva(
        self,
        message: str,
        model: str,
        user_id: str,
        chat_id: str,
        tools_enabled: Dict[str, bool],
        channel: str = "chat",
        user_context: Optional[Dict] = None,
        document_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process message using Saptiva (kill switch path).

        Args:
            message: User message
            model: Model name
            user_id: User ID
            chat_id: Chat ID
            tools_enabled: Tools configuration
            channel: Chat channel
            user_context: Additional context
            document_context: Document content for RAG (formatted string)

        Returns:
            Coordinated response format
        """
        async with trace_span(
            "saptiva_simple_chat",
            {
                "chat.id": chat_id,
                "chat.message_length": len(message),
                "chat.model": model,
                "chat.channel": channel
            }
        ):
            # Build context
            context = user_context or {}
            context['chat_id'] = chat_id
            context['user_id'] = user_id

            # Build payload using prompt registry
            payload_data, metadata = build_payload(
                model=model,
                user_prompt=message,
                user_context=context,
                tools_enabled=tools_enabled,
                channel=channel
            )

            # Add document context as system message if provided
            if document_context:
                system_message = {
                    "role": "system",
                    "content": (
                        f"El usuario ha adjuntado documentos para tu referencia. "
                        f"Usa esta información para responder sus preguntas:\n\n{document_context}"
                    )
                }
                # Insert after the main system prompt (usually first message)
                if payload_data["messages"] and payload_data["messages"][0]["role"] == "system":
                    payload_data["messages"].insert(1, system_message)
                else:
                    payload_data["messages"].insert(0, system_message)

                logger.info(
                    "Added document context to prompt",
                    context_length=len(document_context),
                    chat_id=chat_id
                )

            # Log telemetry
            logger.info(
                "Saptiva request metadata",
                request_id=metadata.get("request_id"),
                system_hash=metadata.get("system_hash"),
                prompt_version=metadata.get("prompt_version"),
                model=model,
                channel=channel,
                has_tools=metadata.get("has_tools", False)
            )

            # Call Saptiva
            start_time = time.time()
            saptiva_response = await self.saptiva_client.chat_completion(
                messages=payload_data["messages"],
                model=model,
                temperature=payload_data.get("temperature", 0.7),
                max_tokens=payload_data.get("max_tokens", 1024),
                stream=False,
                tools=payload_data.get("tools")
            )

            # Format as coordinated response
            return {
                "type": "chat",
                "response": saptiva_response,
                "decision": {
                    "complexity": {"score": 0.0, "requires_research": False},
                    "reason": "Kill switch active - simple inference only"
                },
                "escalation_available": False,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "_metadata": metadata
            }

    async def add_user_message(
        self,
        chat_session: ChatSessionModel,
        content: str
    ) -> ChatMessageModel:
        """Add user message to session and invalidate cache."""
        user_message = await chat_session.add_message(
            role=MessageRole.USER,
            content=content,
            metadata={"source": "api"}
        )

        logger.info("Added user message", message_id=user_message.id, chat_id=chat_session.id)

        # Invalidate cache
        cache = await get_redis_cache()
        await cache.invalidate_chat_history(chat_session.id)

        return user_message

    async def add_assistant_message(
        self,
        chat_session: ChatSessionModel,
        content: str,
        model: str,
        task_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tokens: Optional[Dict] = None,
        latency_ms: Optional[int] = None
    ) -> ChatMessageModel:
        """Add assistant message to session and invalidate cache."""
        ai_message = await chat_session.add_message(
            role=MessageRole.ASSISTANT,
            content=content,
            model=model,
            task_id=task_id,
            metadata=metadata or {},
            tokens=tokens,
            latency_ms=latency_ms
        )

        # Invalidate cache
        cache = await get_redis_cache()
        await cache.invalidate_chat_history(chat_session.id)
        if task_id:
            await cache.invalidate_research_tasks(chat_session.id)

        return ai_message
