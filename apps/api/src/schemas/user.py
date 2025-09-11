"""
User Pydantic schemas
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from .common import BaseEntity


class UserPreferences(BaseModel):
    """User preferences schema"""
    theme: str = Field(default="auto", description="UI theme preference")
    language: str = Field(default="en", description="Language preference")
    default_model: str = Field(default="SAPTIVA_CORTEX", description="Default model")
    chat_settings: dict = Field(default_factory=dict, description="Chat settings")


class UserCreate(BaseModel):
    """User creation schema"""
    username: str = Field(..., min_length=1, max_length=255, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, max_length=255, description="Password")
    preferences: Optional[UserPreferences] = Field(None, description="User preferences")


class UserUpdate(BaseModel):
    """User update schema"""
    email: Optional[EmailStr] = Field(None, description="Email address")
    preferences: Optional[UserPreferences] = Field(None, description="User preferences")


class User(BaseEntity):
    """User schema"""
    username: str = Field(..., description="Username")
    email: EmailStr = Field(..., description="Email address")
    is_active: bool = Field(default=True, description="Whether user is active")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    preferences: UserPreferences = Field(default_factory=UserPreferences, description="User preferences")