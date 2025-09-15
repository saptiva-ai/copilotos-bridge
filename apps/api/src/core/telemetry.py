"""
OpenTelemetry configuration for distributed tracing.
"""

from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(settings: Any) -> None:
    """Setup OpenTelemetry tracing."""
    
    if not settings.otel_exporter_otlp_endpoint:
        # Skip telemetry setup if no endpoint configured
        return
    
    # Create resource
    resource = Resource.create({
        "service.name": settings.otel_service_name,
        "service.version": settings.app_version,
    })
    
    # Set up trace provider
    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)
    
    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_otlp_endpoint,
        insecure=True,  # TODO: Configure TLS in production
    )
    
    # Add batch processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace_provider.add_span_processor(span_processor)
    
    # Auto-instrument libraries
    LoggingInstrumentor().instrument(set_logging_format=True)
    HTTPXClientInstrumentor().instrument()
    PymongoInstrumentor().instrument()
    RedisInstrumentor().instrument()


def instrument_fastapi(app: Any) -> None:
    """Instrument FastAPI app after creation."""
    FastAPIInstrumentor.instrument_app(app)


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance."""
    return trace.get_tracer(name)