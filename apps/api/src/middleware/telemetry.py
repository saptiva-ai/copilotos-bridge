"""
Telemetry middleware for request tracking and metrics.
"""

import time
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..core.telemetry import metrics_collector, trace_span

logger = structlog.get_logger(__name__)

class TelemetryMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting telemetry data."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with telemetry tracking."""
        start_time = time.time()
        method = request.method
        path_template = request.url.path

        # Create span for request tracing
        async with trace_span(
            f"{method} {path_template}",
            {
                "http.method": method,
                "http.url": str(request.url),
                "http.user_agent": request.headers.get("user-agent", ""),
                "http.remote_addr": request.client.host if request.client else "",
            }
        ) as span:
            try:
                # Process request
                response = await call_next(request)
                status_code = response.status_code

                # Add response attributes to span
                span.set_attribute("http.status_code", status_code)
                span.set_attribute("http.response_size",
                                 len(response.body) if hasattr(response, 'body') else 0)

                # Record metrics
                duration = time.time() - start_time
                metrics_collector.record_request(
                    method=method,
                    endpoint=path_template,
                    status_code=status_code,
                    duration=duration
                )

                # Log request
                logger.info(
                    "Request completed",
                    method=method,
                    path=path_template,
                    status_code=status_code,
                    duration_ms=duration * 1000,
                    user_agent=request.headers.get("user-agent", ""),
                    remote_addr=request.client.host if request.client else "",
                )

                return response

            except Exception as e:
                # Record error metrics
                duration = time.time() - start_time
                metrics_collector.record_request(
                    method=method,
                    endpoint=path_template,
                    status_code=500,
                    duration=duration
                )

                logger.error(
                    "Request failed",
                    method=method,
                    path=path_template,
                    error=str(e),
                    duration_ms=duration * 1000,
                )

                raise