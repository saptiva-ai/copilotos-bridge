"""
OpenTelemetry configuration for observability.
Provides monitoring, tracing, and metrics collection.
"""

import os
import time
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import structlog
from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = structlog.get_logger(__name__)

class TelemetryManager:
    """Manages OpenTelemetry configuration and lifecycle."""

    def __init__(self):
        self.tracer_provider: Optional[TracerProvider] = None
        self.meter_provider: Optional[MeterProvider] = None
        self.jaeger_exporter: Optional[JaegerExporter] = None
        self.prometheus_reader: Optional[PrometheusMetricReader] = None

        # Configuration from environment and settings
        self.service_name = "copilotos-api"
        self.service_version = "0.1.0"
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.jaeger_endpoint = os.getenv("JAEGER_ENDPOINT")
        self.enable_console_exporter = os.getenv("OTEL_CONSOLE_EXPORTER", "false").lower() == "true"

    def setup_tracing(self, settings: Any = None) -> None:
        """Configure OpenTelemetry tracing."""
        try:
            # Create resource
            resource = Resource.create({
                ResourceAttributes.SERVICE_NAME: self.service_name,
                ResourceAttributes.SERVICE_VERSION: self.service_version,
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: self.environment,
            })

            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self.tracer_provider)

            # Setup OTLP exporter if configured
            if settings and hasattr(settings, 'otel_exporter_otlp_endpoint') and settings.otel_exporter_otlp_endpoint:
                otlp_exporter = OTLPSpanExporter(
                    endpoint=settings.otel_exporter_otlp_endpoint,
                    insecure=True,
                )
                otlp_processor = BatchSpanProcessor(otlp_exporter)
                self.tracer_provider.add_span_processor(otlp_processor)
                logger.info("OTLP tracing configured", endpoint=settings.otel_exporter_otlp_endpoint)

            # Setup Jaeger exporter if configured
            if self.jaeger_endpoint:
                self.jaeger_exporter = JaegerExporter(
                    endpoint=self.jaeger_endpoint,
                )
                jaeger_processor = BatchSpanProcessor(self.jaeger_exporter)
                self.tracer_provider.add_span_processor(jaeger_processor)
                logger.info("Jaeger tracing configured", endpoint=self.jaeger_endpoint)

            # Enable console exporter for development
            if self.enable_console_exporter or self.environment == "development":
                console_exporter = ConsoleSpanExporter()
                console_processor = BatchSpanProcessor(console_exporter)
                self.tracer_provider.add_span_processor(console_processor)
                logger.info("Console tracing enabled")

            logger.info("OpenTelemetry tracing configured successfully")

        except Exception as e:
            logger.error("Failed to setup tracing", error=str(e))

    def setup_metrics(self) -> None:
        """Configure OpenTelemetry metrics."""
        try:
            # Create resource
            resource = Resource.create({
                ResourceAttributes.SERVICE_NAME: self.service_name,
                ResourceAttributes.SERVICE_VERSION: self.service_version,
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: self.environment,
            })

            # Setup Prometheus metrics reader
            self.prometheus_reader = PrometheusMetricReader()

            # Create meter provider
            self.meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[self.prometheus_reader]
            )
            metrics.set_meter_provider(self.meter_provider)

            logger.info("OpenTelemetry metrics configured successfully")

        except Exception as e:
            logger.error("Failed to setup metrics", error=str(e))

    def instrument_libraries(self) -> None:
        """Auto-instrument libraries."""
        try:
            # Instrument logging
            LoggingInstrumentor().instrument(set_logging_format=True)

            # Instrument HTTP clients
            HTTPXClientInstrumentor().instrument()

            # Instrument MongoDB
            PymongoInstrumentor().instrument()

            # Instrument Redis
            RedisInstrumentor().instrument()

            logger.info("Library auto-instrumentation completed")

        except Exception as e:
            logger.error("Failed to instrument libraries", error=str(e))

    def get_tracer(self, name: str = __name__):
        """Get a tracer instance."""
        return trace.get_tracer(name)

    def get_meter(self, name: str = __name__):
        """Get a meter instance."""
        return metrics.get_meter(name)

    def shutdown(self) -> None:
        """Shutdown telemetry providers."""
        try:
            if self.tracer_provider:
                self.tracer_provider.shutdown()
            if self.meter_provider:
                self.meter_provider.shutdown()
            logger.info("Telemetry shutdown completed")
        except Exception as e:
            logger.error("Error during telemetry shutdown", error=str(e))

# Global telemetry manager instance
telemetry_manager = TelemetryManager()

def setup_telemetry(settings: Any = None) -> None:
    """Initialize OpenTelemetry configuration."""
    logger.info("Setting up OpenTelemetry", service_name=telemetry_manager.service_name)

    telemetry_manager.setup_tracing(settings)
    telemetry_manager.setup_metrics()
    telemetry_manager.instrument_libraries()

    logger.info("OpenTelemetry setup completed")

def instrument_fastapi(app: Any) -> None:
    """Instrument FastAPI app after creation."""
    FastAPIInstrumentor.instrument_app(app)

def get_tracer(name: str = __name__) -> trace.Tracer:
    """Get a tracer instance."""
    return telemetry_manager.get_tracer(name)

def get_meter(name: str = __name__):
    """Get a meter instance."""
    return telemetry_manager.get_meter(name)

@asynccontextmanager
async def trace_span(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """Context manager for creating traced spans."""
    tracer = get_tracer()

    with tracer.start_as_current_span(operation_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        start_time = time.time()
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise
        finally:
            duration = time.time() - start_time
            span.set_attribute("duration_ms", duration * 1000)

class MetricsCollector:
    """Centralized metrics collection."""

    def __init__(self):
        self.meter = get_meter("copilotos_metrics")

        # Request metrics
        self.request_counter = self.meter.create_counter(
            "http_requests_total",
            description="Total number of HTTP requests"
        )

        self.request_duration = self.meter.create_histogram(
            "http_request_duration_seconds",
            description="HTTP request duration in seconds"
        )

        # Chat metrics
        self.chat_messages_counter = self.meter.create_counter(
            "chat_messages_total",
            description="Total number of chat messages processed"
        )

        self.chat_response_duration = self.meter.create_histogram(
            "chat_response_duration_seconds",
            description="Chat response generation time"
        )

        # Research metrics
        self.research_tasks_counter = self.meter.create_counter(
            "research_tasks_total",
            description="Total number of research tasks"
        )

        self.research_task_duration = self.meter.create_histogram(
            "research_task_duration_seconds",
            description="Research task completion time"
        )

        # Cache metrics
        self.cache_operations_counter = self.meter.create_counter(
            "cache_operations_total",
            description="Total cache operations"
        )

    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        self.request_counter.add(1, {
            "method": method,
            "endpoint": endpoint,
            "status_code": str(status_code)
        })
        self.request_duration.record(duration, {
            "method": method,
            "endpoint": endpoint
        })

    def record_chat_message(self, model: str, tokens: int, duration: float):
        """Record chat message metrics."""
        self.chat_messages_counter.add(1, {"model": model})
        self.chat_response_duration.record(duration, {"model": model})

    def record_research_task(self, task_type: str, status: str, duration: float):
        """Record research task metrics."""
        self.research_tasks_counter.add(1, {
            "type": task_type,
            "status": status
        })
        if status == "completed":
            self.research_task_duration.record(duration, {"type": task_type})

    def record_cache_operation(self, operation: str, cache_type: str, hit: bool):
        """Record cache operation metrics."""
        self.cache_operations_counter.add(1, {
            "operation": operation,
            "cache_type": cache_type,
            "hit": str(hit)
        })

# Global metrics collector
metrics_collector = MetricsCollector()

def shutdown_telemetry():
    """Shutdown telemetry on application exit."""
    telemetry_manager.shutdown()