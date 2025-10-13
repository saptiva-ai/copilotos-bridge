"""
Authentication routes for the Copilot OS API.
"""

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordBearer

from ..core.config import Settings, get_settings
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


def _set_session_cookie(response: Response, token: str, max_age: int, settings: Settings) -> None:
    samesite = (settings.session_cookie_samesite or "lax").lower()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        domain=settings.session_cookie_domain,
        path=settings.session_cookie_path,
        samesite=samesite,
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        domain=settings.session_cookie_domain,
        path=settings.session_cookie_path,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate) -> AuthResponse:
    """Register a new user."""
    return await register_user(payload)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: AuthRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    """Authenticate a user and issue tokens."""
    auth_response = await authenticate_user(payload.identifier, payload.password)
    _set_session_cookie(response, auth_response.access_token, auth_response.expires_in, settings)
    return auth_response


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    payload: TokenRefresh,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> RefreshResponse:
    """Refresh an access token using a refresh token."""
    refreshed = await refresh_access_token(payload.refresh_token)
    _set_session_cookie(response, refreshed.access_token, refreshed.expires_in, settings)
    return refreshed


@router.get("/me", response_model=UserSchema)
async def me(request: Request) -> UserSchema:
    """Retrieve the current authenticated user profile."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise AuthenticationError("Not authenticated")

    return await get_user_profile(str(user_id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: TokenRefresh,
    response: Response,
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
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

    _clear_session_cookie(response, settings)

    return None
