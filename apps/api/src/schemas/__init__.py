"""
Pydantic schemas for Copilot OS API
"""

from .auth import AuthRequest, AuthResponse, TokenRefresh
from .chat import ChatMessage, ChatRequest, ChatResponse, ChatSession
from .health import HealthStatus, ServiceStatus
from .intent import IntentRequest, IntentResponse, IntentLabel, IntentPrediction
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
from .settings import (
    SaptivaKeyStatus,
    SaptivaKeyUpdateRequest,
    SaptivaKeyUpdateResponse,
    SaptivaKeyDeleteResponse,
)

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
    # Intent
    "IntentRequest",
    "IntentResponse",
    "IntentLabel",
    "IntentPrediction",
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
    # Settings
    "SaptivaKeyStatus",
    "SaptivaKeyUpdateRequest",
    "SaptivaKeyUpdateResponse",
    "SaptivaKeyDeleteResponse",
]
