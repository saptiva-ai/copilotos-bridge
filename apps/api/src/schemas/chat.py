"""
Chat API schemas
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, validator


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


class ChatMessage(BaseModel):
    """Chat message schema"""
    
    id: Optional[str] = Field(None, description="Message ID")
    chat_id: str = Field(..., description="Chat session ID")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    status: MessageStatus = Field(default=MessageStatus.DELIVERED, description="Message status")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")
    model: Optional[str] = Field(None, description="Model used for generation")
    tokens: Optional[int] = Field(None, description="Token count")
    latency_ms: Optional[int] = Field(None, description="Response latency")
    task_id: Optional[str] = Field(None, description="Associated task ID")


class ChatSettings(BaseModel):
    """Chat settings schema"""
    
    model: str = Field(default="SAPTIVA_CORTEX", description="Selected model")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature setting")
    max_tokens: int = Field(default=1024, ge=1, le=8192, description="Max tokens")
    tools_enabled: Dict[str, bool] = Field(
        default_factory=lambda: {"web_search": False, "deep_research": False},
        description="Enabled tools"
    )
    research_params: Optional[Dict[str, Any]] = Field(None, description="Research parameters")


class ChatSession(BaseModel):
    """Chat session schema"""
    
    id: Optional[str] = Field(None, description="Chat session ID")
    title: str = Field(..., max_length=200, description="Chat session title")
    user_id: str = Field(..., description="User ID")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    message_count: int = Field(default=0, description="Number of messages")
    settings: ChatSettings = Field(default_factory=ChatSettings, description="Chat settings")


class ChatRequest(BaseModel):
    """Chat request schema"""
    
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    chat_id: Optional[str] = Field(None, description="Existing chat session ID")
    model: Optional[str] = Field(None, description="Model to use for response")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature setting")
    max_tokens: Optional[int] = Field(None, ge=1, le=8192, description="Max tokens")
    stream: bool = Field(default=False, description="Enable streaming response")
    tools_enabled: Optional[Dict[str, bool]] = Field(None, description="Tools to enable")
    context: Optional[List[Dict[str, str]]] = Field(None, description="Additional context")

    @validator('message')
    def validate_message_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()


class ChatResponse(BaseModel):
    """Chat response schema"""
    
    chat_id: str = Field(..., description="Chat session ID")
    message_id: str = Field(..., description="Response message ID")
    content: str = Field(..., description="Response content")
    role: MessageRole = Field(default=MessageRole.ASSISTANT, description="Message role")
    model: str = Field(..., description="Model used for response")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    # Response metadata
    tokens: Optional[int] = Field(None, description="Token count")
    latency_ms: Optional[int] = Field(None, description="Response latency")
    finish_reason: Optional[str] = Field(None, description="Completion reason")
    
    # Tool usage
    tools_used: Optional[List[str]] = Field(None, description="Tools used in response")
    task_id: Optional[str] = Field(None, description="Associated task ID for deep research")


class ChatHistoryRequest(BaseModel):
    """Chat history request schema"""
    
    chat_id: str = Field(..., description="Chat session ID")
    limit: int = Field(default=50, ge=1, le=100, description="Number of messages to retrieve")
    offset: int = Field(default=0, ge=0, description="Number of messages to skip")
    include_system: bool = Field(default=False, description="Include system messages")


class ChatHistoryResponse(BaseModel):
    """Chat history response schema"""
    
    chat_id: str = Field(..., description="Chat session ID")
    messages: List[ChatMessage] = Field(..., description="Chat messages")
    total_count: int = Field(..., description="Total number of messages")
    has_more: bool = Field(..., description="Whether there are more messages")


class ChatSessionListResponse(BaseModel):
    """Chat session list response schema"""
    
    sessions: List[ChatSession] = Field(..., description="Chat sessions")
    total_count: int = Field(..., description="Total number of sessions")
    has_more: bool = Field(..., description="Whether there are more sessions")