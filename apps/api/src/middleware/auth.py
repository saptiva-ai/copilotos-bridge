"""
Authentication middleware for JWT token validation.
"""

from typing import Optional

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


logger = structlog.get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware."""
    
    # Public endpoints that don't require authentication
    PUBLIC_PATHS = {
        "/api/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and validate JWT token if required."""

        # Skip authentication for public endpoints
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Extract JWT token from request
        token = self._extract_token(request)
        if not token:
            # For now, we'll use mock authentication when no token is provided
            logger.debug("No token provided, using mock authentication", path=request.url.path)
            request.state.user_id = "mock-user-id"
            request.state.authenticated = True
            return await call_next(request)

        # Validate JWT token
        payload = self._validate_token(token)
        if not payload:
            logger.warning("Invalid JWT token", path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authentication token"}
            )

        # Add user context to request
        request.state.user_id = payload.get("user_id", payload.get("sub", "unknown"))
        request.state.authenticated = True

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
            import jwt
            from ..core.config import get_settings

            settings = get_settings()

            # For development, we can validate with a simple secret
            # In production, this should use proper JWT validation with public keys
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": True}
            )

            logger.debug("JWT token validated successfully", user_id=payload.get("user_id", payload.get("sub")))
            return payload

        except ImportError:
            logger.warning("PyJWT not installed, falling back to mock validation")
            # Simple mock validation for development
            if token == "dev-token":
                return {"user_id": "dev-user", "sub": "dev@example.com"}
            return None

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None

        except jwt.InvalidTokenError as e:
            logger.warning("Invalid JWT token", error=str(e))
            return None

        except Exception as e:
            logger.error("Unexpected error validating JWT token", error=str(e))
            return None