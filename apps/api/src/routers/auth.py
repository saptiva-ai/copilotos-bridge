"""
Authentication routes for the Copilot OS API.
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordBearer

from ..core.exceptions import AuthenticationError
from ..schemas.auth import AuthRequest, AuthResponse, RefreshResponse, TokenRefresh
from ..schemas.user import User as UserSchema, UserCreate
from ..services.auth_service import (
    authenticate_user,
    get_user_profile,
    logout_user,
    refresh_access_token,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate) -> AuthResponse:
    """Register a new user."""
    return await register_user(payload)


@router.post("/login", response_model=AuthResponse)
async def login(payload: AuthRequest) -> AuthResponse:
    """Authenticate a user and issue tokens."""
    return await authenticate_user(payload.identifier, payload.password)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(payload: TokenRefresh) -> RefreshResponse:
    """Refresh an access token using a refresh token."""
    return await refresh_access_token(payload.refresh_token)


@router.get("/me", response_model=UserSchema)
async def me(request: Request) -> UserSchema:
    """Retrieve the current authenticated user profile."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise AuthenticationError("Not authenticated")

    return await get_user_profile(str(user_id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: TokenRefresh, token: str = Depends(oauth2_scheme)) -> None:
    """Logout user and invalidate session.

    P0-LOGOUT-INVALIDATE: Blacklist the refresh token to prevent reuse.
    The access token from the Authorization header is also blacklisted for completeness.
    """
    # Blacklist the refresh token (most important - has longer expiry)
    if payload.refresh_token:
        await logout_user(payload.refresh_token)

    # Also blacklist the access token if provided
    if token:
        await logout_user(token)

    return None
