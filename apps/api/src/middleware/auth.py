"""
Authentication middleware for JWT token validation.
"""

from typing import Optional

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..core.config import get_settings

logger = structlog.get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware."""
    
    # Public endpoints that don't require authentication
    PUBLIC_PATHS = {
        "/api/health",
        "/api/health/live",
        "/api/health/ready",
        "/api/feature-flags",  # P0-DR-002: Feature flags need to be public for frontend
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and validate JWT token if required."""

        # Skip authentication for public endpoints and preflight requests
        if request.method == "OPTIONS" or request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Extract JWT token from request
        token = self._extract_token(request)
        if not token:
            logger.warning("Missing authentication token", path=request.url.path)
            return self._unauthorized_response()

        # Validate JWT token
        payload = self._validate_token(token)
        if not payload:
            logger.warning("Invalid JWT token", path=request.url.path)
            return self._unauthorized_response()

        # Add user context to request
        request.state.user_id = payload.get("sub") or payload.get("user_id")
        request.state.authenticated = True
        request.state.user_claims = payload

        logger.debug("Authenticated request", user_id=request.state.user_id, path=request.url.path)

        return await call_next(request)
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from Authorization header."""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return None
            return token
        except ValueError:
            return None
    
    def _validate_token(self, token: str) -> Optional[dict]:
        """Validate JWT token and return payload."""
        try:
            from jose import JWTError, jwt

            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm],
                options={"verify_exp": True},
            )

            logger.debug(
                "JWT token validated successfully",
                user_id=payload.get("sub") or payload.get("user_id"),
            )
            return payload

        except JWTError as exc:
            logger.warning("JWT token validation failed", error=str(exc))
            return None
        except Exception as e:
            logger.error("Unexpected error validating JWT token", error=str(e))
            return None

    def _unauthorized_response(self) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Not authenticated"},
        )
