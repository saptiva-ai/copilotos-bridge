"""
Pydantic schemas for Copilot OS API
"""

from .auth import AuthRequest, AuthResponse, TokenRefresh
from .chat import ChatMessage, ChatRequest, ChatResponse, ChatSession
from .health import HealthStatus, ServiceStatus
from .research import (
    DeepResearchRequest,
    DeepResearchResponse,
    DeepResearchParams,
    DeepResearchResult,
    TaskStatus,
    ResearchSource,
    Evidence,
    ResearchMetrics,
)
from .common import ApiResponse, PaginatedResponse, ApiError
from .user import User, UserPreferences, UserUpdate

__all__ = [
    # Auth
    "AuthRequest",
    "AuthResponse", 
    "TokenRefresh",
    # Chat
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ChatSession",
    # Health
    "HealthStatus",
    "ServiceStatus",
    # Research
    "DeepResearchRequest",
    "DeepResearchResponse",
    "DeepResearchParams",
    "DeepResearchResult",
    "TaskStatus",
    "ResearchSource",
    "Evidence",
    "ResearchMetrics",
    # Common
    "ApiResponse",
    "PaginatedResponse",
    "ApiError",
    # User
    "User",
    "UserPreferences",
    "UserUpdate",
]