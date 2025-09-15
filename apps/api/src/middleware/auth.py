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
        
        # For now, we'll skip JWT validation and just pass through
        # TODO: Implement actual JWT validation
        logger.debug("Processing request", path=request.url.path, method=request.method)
        
        # Add user context to request (mock for now)
        request.state.user_id = "mock-user-id"
        request.state.authenticated = True
        
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
        # TODO: Implement JWT token validation
        return {"user_id": "mock-user-id", "sub": "mock@example.com"}