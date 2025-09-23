"""Minimal OpenTelemetry configuration for basic observability."""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, Dict, Any

import structlog

logger = structlog.get_logger(__name__)


def setup_telemetry(settings) -> None:
    """Minimal telemetry setup - disabled for production deployment."""
    logger.info("Telemetry setup disabled for production deployment")


def instrument_fastapi(app) -> None:
    """Minimal FastAPI instrumentation - disabled for production deployment."""
    logger.info("FastAPI instrumentation disabled for production deployment")


def shutdown_telemetry() -> None:
    """Shutdown telemetry - minimal implementation."""
    logger.info("Telemetry shutdown complete")


class SpanStub:
    """Stub span object that mimics OpenTelemetry span interface."""

    def __init__(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        self.operation_name = operation_name
        self.attributes = attributes or {}

    def set_attribute(self, key: str, value: Any) -> None:
        """Set attribute on span (no-op for stub)."""
        self.attributes[key] = value
        logger.debug("span.set_attribute", operation=self.operation_name, key=key, value=value)

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add event to span (no-op for stub)."""
        logger.debug("span.add_event", operation=self.operation_name, event=name, attributes=attributes or {})


class MetricsCollector:
    """Stub metrics collector for environments without OTEL."""

    def get_request_count(self) -> int:
        return 0

    def get_error_count(self) -> int:
        return 0

    def get_active_connections(self) -> int:
        return 0

    def record_request(self, method: str, endpoint: str, status_code: int, duration: float) -> None:
        """Record request metrics (no-op for stub)."""
        logger.debug("metrics.record_request",
                    method=method, endpoint=endpoint, status_code=status_code, duration=duration)


metrics_collector = MetricsCollector()


@asynccontextmanager
async def trace_span(operation_name: str, attributes: Optional[Dict[str, Any]] = None) -> AsyncIterator[SpanStub]:
    """Minimal async context manager that mimics an OTEL span."""
    span = SpanStub(operation_name, attributes)
    try:
        logger.debug("trace_span.start", operation=operation_name, attributes=attributes or {})
        yield span
    finally:
        logger.debug("trace_span.end", operation=operation_name)
