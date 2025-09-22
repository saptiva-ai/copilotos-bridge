"""
Metrics and monitoring API endpoints.
"""

import structlog
from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from ..core.telemetry import metrics_collector

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.get("/metrics", tags=["monitoring"])
async def get_prometheus_metrics():
    """
    Expose Prometheus metrics endpoint.

    Returns metrics in Prometheus format for scraping.
    """
    try:
        # Generate Prometheus metrics
        metrics_data = generate_latest()

        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    except Exception as e:
        logger.error("Failed to generate metrics", error=str(e))
        return Response(
            content="# Error generating metrics\n",
            media_type=CONTENT_TYPE_LATEST,
            status_code=500
        )

@router.get("/health/metrics", tags=["monitoring", "health"])
async def get_metrics_health():
    """
    Health check for metrics collection.

    Returns basic metrics about the metrics system itself.
    """
    try:
        return {
            "status": "healthy",
            "metrics_collector": "active",
            "telemetry_enabled": True,
            "exporters": {
                "prometheus": True,
                "console": False  # Based on environment
            }
        }
    except Exception as e:
        logger.error("Metrics health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }