"""
Chat document models
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4

from beanie import Document, Indexed, Link
from pydantic import Field, BaseModel

from .user import User


class MessageRole(str, Enum):
    """Message role enumeration"""
    USER = "user"
    ASSISTANT = "assistant" 
    SYSTEM = "system"


class MessageStatus(str, Enum):
    """Message status enumeration"""
    SENDING = "sending"
    DELIVERED = "delivered"
    ERROR = "error"
    STREAMING = "streaming"


class ChatMessage(Document):
    """Chat message document model"""
    
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    chat_id: Indexed(str) = Field(..., description="Chat session ID")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    status: MessageStatus = Field(default=MessageStatus.DELIVERED, description="Message status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")
    model: Optional[str] = Field(None, description="Model used for generation")
    tokens: Optional[int] = Field(None, description="Token count")
    latency_ms: Optional[int] = Field(None, description="Response latency")
    task_id: Optional[str] = Field(None, description="Associated task ID")

    class Settings:
        name = "messages"
        indexes = [
            "chat_id",
            "created_at",
            "role",
            "status",
            [("chat_id", 1), ("created_at", 1)],  # Compound index for chat history
        ]

    def __str__(self) -> str:
        return f"ChatMessage(id={self.id}, role={self.role}, chat_id={self.chat_id})"


class ChatSettings(BaseModel):
    """Chat settings subdocument"""
    model: str = Field(default="SAPTIVA_CORTEX", description="Selected model")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature setting")
    max_tokens: int = Field(default=1024, ge=1, le=8192, description="Max tokens")
    tools_enabled: Dict[str, bool] = Field(
        default_factory=lambda: {"web_search": False, "deep_research": False},
        description="Enabled tools"
    )
    research_params: Optional[Dict[str, Any]] = Field(None, description="Research parameters")


class ChatSession(Document):
    """Chat session document model"""
    
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    title: str = Field(..., max_length=200, description="Chat session title")
    user_id: Indexed(str) = Field(..., description="User ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    message_count: int = Field(default=0, description="Number of messages")
    settings: ChatSettings = Field(default_factory=ChatSettings, description="Chat settings")
    
    # Optional user reference (for relational queries)
    user: Optional[Link[User]] = Field(None, description="User reference")

    class Settings:
        name = "chat_sessions"
        indexes = [
            "user_id",
            "created_at", 
            "updated_at",
            "title",
            [("user_id", 1), ("updated_at", -1)],  # User's recent chats
        ]

    def __str__(self) -> str:
        return f"ChatSession(id={self.id}, title={self.title}, user_id={self.user_id})"

    async def get_messages(self, limit: int = 50, skip: int = 0) -> List[ChatMessage]:
        """Get messages for this chat session"""
        return await ChatMessage.find(
            ChatMessage.chat_id == self.id
        ).sort(-ChatMessage.created_at).skip(skip).limit(limit).to_list()

    async def add_message(self, role: MessageRole, content: str, **kwargs) -> ChatMessage:
        """Add a new message to this chat session"""
        message = ChatMessage(
            chat_id=self.id,
            role=role,
            content=content,
            **kwargs
        )
        await message.insert()

        # Update session stats
        self.message_count += 1
        self.updated_at = datetime.utcnow()
        await self.save()

        # Invalidate cache for this chat
        try:
            from ..core.redis_cache import get_redis_cache
            cache = await get_redis_cache()
            await cache.invalidate_all_for_chat(self.id)
        except Exception as e:
            # Don't fail if cache invalidation fails
            import structlog
            logger = structlog.get_logger(__name__)
            logger.warning("Failed to invalidate cache", error=str(e), chat_id=self.id)

        # Record in unified history
        try:
            from ..services.history_service import HistoryService
            await HistoryService.record_chat_message(
                chat_id=self.id,
                user_id=self.user_id,
                message=message
            )
        except Exception as e:
            # Don't fail message creation if history fails
            import structlog
            logger = structlog.get_logger(__name__)
            logger.warning(
                "Failed to record message in unified history",
                error=str(e),
                chat_id=self.id,
                message_id=message.id
            )

        return message