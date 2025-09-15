"""
Rate limiting middleware to prevent abuse.
"""

import time
from collections import defaultdict, deque
from typing import Dict, Deque

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..core.config import get_settings

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""
    
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.settings = get_settings()
        
        # In-memory storage for request tracking
        # In production, use Redis for distributed rate limiting
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply rate limiting based on client IP."""
        
        if not self.settings.rate_limit_enabled:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old requests outside the window
        self._cleanup_old_requests(client_ip, current_time)
        
        # Check if rate limit is exceeded
        request_count = len(self._requests[client_ip])
        if request_count >= self.settings.rate_limit_calls:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                request_count=request_count,
                limit=self.settings.rate_limit_calls
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Too many requests. Limit: {self.settings.rate_limit_calls} per {self.settings.rate_limit_period}s",
                    "retry_after": self.settings.rate_limit_period
                },
                headers={"Retry-After": str(self.settings.rate_limit_period)}
            )
        
        # Record this request
        self._requests[client_ip].append(current_time)
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.settings.rate_limit_calls)
        response.headers["X-RateLimit-Remaining"] = str(
            self.settings.rate_limit_calls - request_count - 1
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(current_time + self.settings.rate_limit_period)
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    def _cleanup_old_requests(self, client_ip: str, current_time: float) -> None:
        """Remove requests outside the rate limit window."""
        window_start = current_time - self.settings.rate_limit_period
        
        # Remove old timestamps
        while (self._requests[client_ip] and 
               self._requests[client_ip][0] < window_start):
            self._requests[client_ip].popleft()
        
        # Clean up empty entries to prevent memory leaks
        if not self._requests[client_ip]:
            del self._requests[client_ip]