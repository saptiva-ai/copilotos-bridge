"""
Authentication and user management service layer.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..core.config import get_settings
from ..core.exceptions import AuthenticationError, ConflictError, NotFoundError
from ..models.user import User, UserPreferences as UserPreferencesModel
from ..schemas.auth import AuthResponse, RefreshResponse
from ..schemas.user import (
    User as UserSchema,
    UserCreate,
    UserPreferences as UserPreferencesSchema,
)

logger = structlog.get_logger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return _pwd_context.hash(password)


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored hash."""
    return _pwd_context.verify(plain_password, hashed_password)


async def _get_user_by_username(username: str) -> Optional[User]:
    return await User.find_one(User.username == username)


async def _get_user_by_email(email: str) -> Optional[User]:
    return await User.find_one(User.email == email)


async def _get_user_by_identifier(identifier: str) -> Optional[User]:
    user = await _get_user_by_username(identifier)
    if user:
        return user
    return await _get_user_by_email(identifier)


def _serialize_user(user: User) -> UserSchema:
    """Serialize a User document into an API schema."""
    preferences_source = user.preferences or UserPreferencesModel()
    preferences = UserPreferencesSchema.model_validate(preferences_source)

    return UserSchema(
        id=UUID(str(user.id)),
        created_at=user.created_at,
        updated_at=user.updated_at,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        last_login=user.last_login,
        preferences=preferences,
    )


def _create_token(subject: str, token_type: str, expires_delta: timedelta, extra_claims: Optional[dict] = None) -> str:
    settings = get_settings()
    now = datetime.utcnow()

    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }

    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    logger.debug("Token generated", token_type=token_type, subject=subject)
    return token


async def _create_token_pair(user: User) -> Tuple[str, str, int]:
    settings = get_settings()

    access_expiry = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    refresh_expiry = timedelta(days=settings.jwt_refresh_token_expire_days)

    claims = {
        "username": user.username,
        "email": user.email,
    }

    access_token = _create_token(str(user.id), "access", access_expiry, claims)
    refresh_token = _create_token(str(user.id), "refresh", refresh_expiry, claims)

    return access_token, refresh_token, int(access_expiry.total_seconds())


async def register_user(payload: UserCreate) -> AuthResponse:
    """Create a new user account."""
    logger.info("Registering user", username=payload.username, email=payload.email)

    existing_username = await _get_user_by_username(payload.username)
    if existing_username:
        logger.warning("Username already exists", username=payload.username)
        raise ConflictError("Username is already registered")

    existing_email = await _get_user_by_email(str(payload.email))
    if existing_email:
        logger.warning("Email already exists", email=str(payload.email))
        raise ConflictError("Email is already registered")

    preferences_document: Optional[UserPreferencesModel] = None
    if payload.preferences:
        preferences_document = UserPreferencesModel(**payload.preferences.model_dump())

    user = User(
        username=payload.username,
        email=str(payload.email),
        password_hash=_hash_password(payload.password),
        preferences=preferences_document or UserPreferencesModel(),
    )

    await user.create()
    logger.info("User registered", user_id=str(user.id))

    access_token, refresh_token, expires_in = await _create_token_pair(user)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=_serialize_user(user),
    )


async def authenticate_user(identifier: str, password: str) -> AuthResponse:
    """Authenticate a user and return token payload."""
    logger.info("Authenticating user", identifier=identifier)

    user = await _get_user_by_identifier(identifier)
    if not user:
        logger.warning("User not found for identifier", identifier=identifier)
        raise AuthenticationError("Incorrect username or password")

    if not _verify_password(password, user.password_hash):
        logger.warning("Invalid credentials", user_id=str(user.id))
        raise AuthenticationError("Incorrect username or password")

    if not user.is_active:
        logger.warning("Inactive user attempted login", user_id=str(user.id))
        raise AuthenticationError("User account is inactive")

    now = datetime.utcnow()
    user.last_login = now
    user.updated_at = now
    await user.save()

    access_token, refresh_token, expires_in = await _create_token_pair(user)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=_serialize_user(user),
    )


async def refresh_access_token(refresh_token: str) -> RefreshResponse:
    """Refresh an access token from a valid refresh token."""
    settings = get_settings()

    try:
        payload = jwt.decode(
            refresh_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        logger.warning("Failed to decode refresh token", error=str(exc))
        raise AuthenticationError("Invalid refresh token") from exc

    if payload.get("type") != "refresh":
        logger.warning("Token type mismatch", token_type=payload.get("type"))
        raise AuthenticationError("Invalid refresh token")

    subject = payload.get("sub")
    if not subject:
        logger.error("Refresh token missing subject")
        raise AuthenticationError("Invalid refresh token")

    user = await User.get(subject)
    if not user:
        user = await _get_user_by_identifier(subject)

    if not user:
        logger.warning("User not found for refresh token", subject=subject)
        raise NotFoundError("User not found")

    if not user.is_active:
        logger.warning("Inactive user attempted refresh", user_id=str(user.id))
        raise AuthenticationError("User account is inactive")

    access_expiry = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    claims = {
        "username": user.username,
        "email": user.email,
    }
    access_token = _create_token(str(user.id), "access", access_expiry, claims)

    logger.info("Access token refreshed", user_id=str(user.id))
    return RefreshResponse(
        access_token=access_token,
        expires_in=int(access_expiry.total_seconds()),
    )


async def get_user_profile(user_id: str) -> UserSchema:
    """Retrieve the current user profile."""
    user = await User.get(user_id)
    if not user:
        raise NotFoundError("User not found")
    return _serialize_user(user)
