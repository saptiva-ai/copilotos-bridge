"""
Authentication Pydantic schemas
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AuthRequest(BaseModel):
    """Login request schema"""
    identifier: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Username or email identifier",
    )
    password: str = Field(..., min_length=8, max_length=255, description="Password")


class TokenRefresh(BaseModel):
    """Token refresh request schema"""
    refresh_token: str = Field(..., description="Refresh token")


class AuthResponse(BaseModel):
    """Login response schema"""
    access_token: str = Field(..., description="Access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: "User" = Field(..., description="User information")

    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }
    )


class TokenVerify(BaseModel):
    """Token verification response"""
    valid: bool = Field(..., description="Whether token is valid")
    user_id: Optional[UUID] = Field(None, description="User ID if token is valid")
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")


class RefreshResponse(BaseModel):
    """Access token refresh response"""
    access_token: str = Field(..., description="New access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Seconds until the token expires")


# Forward reference resolution
from .user import User
AuthResponse.model_rebuild()
