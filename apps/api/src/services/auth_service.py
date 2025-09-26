"""
Authentication and user management service layer.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Optional, Tuple

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..core.config import get_settings
from ..core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    BadRequestError,
)
from ..models.user import User, UserPreferences as UserPreferencesModel
from ..schemas.auth import AuthResponse, RefreshResponse
from ..schemas.user import (
    User as UserSchema,
    UserCreate,
    UserPreferences as UserPreferencesSchema,
)
from .cache_service import add_token_to_blacklist, is_token_blacklisted

logger = structlog.get_logger(__name__)

_pwd_context = CryptContext(
    schemes=["argon2", "bcrypt", "pbkdf2_sha256"],
    default="argon2",
    deprecated=["bcrypt", "pbkdf2_sha256"],
)


_PASSWORD_POLICY = {
    "min_length": 8,
    "uppercase": re.compile(r"[A-Z]"),
    "digits": re.compile(r"\d"),
}


def _hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return _pwd_context.hash(password)


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def _validate_password_strength(password: str) -> Optional[str]:
    """Validate that the password satisfies minimum security requirements."""
    if len(password) < _PASSWORD_POLICY["min_length"]:
        return "La contraseña debe tener al menos 8 caracteres."
    if not _PASSWORD_POLICY["uppercase"].search(password):
        return "Incluye al menos una letra mayúscula."
    if not _PASSWORD_POLICY["digits"].search(password):
        return "Incluye al menos un número."
    return None


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

    # Extract preferences data safely
    if hasattr(preferences_source, 'model_dump'):
        preferences_data = preferences_source.model_dump()
    elif hasattr(preferences_source, 'dict'):
        preferences_data = preferences_source.dict()
    else:
        # Fallback to manual extraction
        preferences_data = {
            'theme': getattr(preferences_source, 'theme', 'auto'),
            'language': getattr(preferences_source, 'language', 'en'),
            'default_model': getattr(preferences_source, 'default_model', 'SAPTIVA_CORTEX'),
            'chat_settings': getattr(preferences_source, 'chat_settings', {}),
        }

    preferences = UserPreferencesSchema(**preferences_data)

    return UserSchema(
        id=str(user.id),
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
    normalized_username = payload.username.strip()
    normalized_email = str(payload.email).strip().lower()

    logger.info("Registering user", username=normalized_username, email=normalized_email)

    password_error = _validate_password_strength(payload.password)
    if password_error:
        logger.warning("Weak password rejected", username=normalized_username)
        raise BadRequestError({
            "code": "WEAK_PASSWORD",
            "message": password_error,
        })

    existing_username = await _get_user_by_username(normalized_username)
    if existing_username:
        logger.warning("Username already exists", username=normalized_username)
        raise ConflictError({
            "code": "USERNAME_EXISTS",
            "field": "username",
            "message": "Ya existe una cuenta con ese usuario.",
        })

    existing_email = await _get_user_by_email(normalized_email)
    if existing_email:
        logger.warning("Email already exists", email=normalized_email)
        raise ConflictError({
            "code": "USER_EXISTS",
            "field": "email",
            "message": "Ya existe una cuenta con ese correo.",
        })

    preferences_document: Optional[UserPreferencesModel] = None
    if payload.preferences:
        preferences_document = UserPreferencesModel(**payload.preferences.model_dump())

    user = User(
        username=normalized_username,
        email=normalized_email,
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
    normalized_identifier = identifier.strip()
    logger.info("Authenticating user", identifier=normalized_identifier)

    user = await _get_user_by_identifier(normalized_identifier)
    if not user:
        logger.warning("User not found for identifier", identifier=normalized_identifier)
        raise AuthenticationError({
            "code": "BAD_CREDENTIALS",
            "message": "Correo o contraseña incorrectos.",
        })

    current_scheme = _pwd_context.identify(user.password_hash)

    try:
        password_valid = _verify_password(password, user.password_hash)
    except (ValueError, TypeError) as exc:  # pragma: no cover - defensive guard
        logger.error(
            "Stored password hash invalid",
            user_id=str(user.id),
            error=str(exc),
        )
        raise AuthenticationError({
            "code": "BAD_CREDENTIALS",
            "message": "Correo o contraseña incorrectos.",
        }) from exc

    if not password_valid:
        logger.warning("Invalid credentials", user_id=str(user.id))
        raise AuthenticationError({
            "code": "BAD_CREDENTIALS",
            "message": "Correo o contraseña incorrectos.",
        })

    if not user.is_active:
        logger.warning("Inactive user attempted login", user_id=str(user.id))
        raise AuthenticationError({
            "code": "ACCOUNT_INACTIVE",
            "message": "La cuenta está inactiva. Contacta al administrador.",
        })

    hash_upgraded = False
    if _pwd_context.needs_update(user.password_hash):
        user.password_hash = _hash_password(password)
        hash_upgraded = True
        logger.info(
            "Password hash upgraded",
            user_id=str(user.id),
            previous_scheme=current_scheme,
        )

    now = datetime.utcnow()
    user.last_login = now
    user.updated_at = now
    await user.save()

    if hash_upgraded:
        logger.debug("Password hash persisted with argon2", user_id=str(user.id))

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

    if await is_token_blacklisted(refresh_token):
        logger.warning("Attempted to refresh with a blacklisted token.")
        raise AuthenticationError({
            "code": "INVALID_TOKEN",
            "message": "El token de sesión ya no es válido.",
        })

    try:
        payload = jwt.decode(
            refresh_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        logger.warning("Failed to decode refresh token", error=str(exc))
        raise AuthenticationError({
            "code": "INVALID_TOKEN",
            "message": "El token de sesión ya no es válido.",
        }) from exc

    if payload.get("type") != "refresh":
        logger.warning("Token type mismatch", token_type=payload.get("type"))
        raise AuthenticationError({
            "code": "INVALID_TOKEN",
            "message": "El token de sesión ya no es válido.",
        })

    subject = payload.get("sub")
    if not subject:
        logger.error("Refresh token missing subject")
        raise AuthenticationError({
            "code": "INVALID_TOKEN",
            "message": "El token de sesión ya no es válido.",
        })

    user = await User.get(subject)
    if not user:
        user = await _get_user_by_identifier(subject)

    if not user:
        logger.warning("User not found for refresh token", subject=subject)
        raise NotFoundError({
            "code": "USER_NOT_FOUND",
            "message": "Usuario no encontrado.",
        })

    if not user.is_active:
        logger.warning("Inactive user attempted refresh", user_id=str(user.id))
        raise AuthenticationError({
            "code": "ACCOUNT_INACTIVE",
            "message": "La cuenta está inactiva. Contacta al administrador.",
        })

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
        raise NotFoundError({
            "code": "USER_NOT_FOUND",
            "message": "Usuario no encontrado.",
        })
    return _serialize_user(user)


async def logout_user(token: str) -> None:
    """Blacklist the provided token to invalidate it."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},  # We need to read the exp claim
        )
    except JWTError as exc:
        logger.warning("Failed to decode token for logout", error=str(exc))
        # Even if the token is invalid, we can proceed without error
        # as the goal is to ensure it can't be used.
        return

    expires_at = payload.get("exp")
    if not expires_at:
        logger.warning("Token for logout has no expiration claim")
        return

    # Add token to blacklist with its original expiry
    await add_token_to_blacklist(token, int(expires_at))
