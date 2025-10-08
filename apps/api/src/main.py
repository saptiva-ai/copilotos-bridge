"""
FastAPI application for Copilot OS API.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core.config import get_settings
from .core.database import Database
from .core.exceptions import (
    APIError,
    api_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from .core.logging import setup_logging
from .core.telemetry import setup_telemetry, instrument_fastapi, shutdown_telemetry
from .middleware.auth import AuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.telemetry import TelemetryMiddleware
from .routers import auth, chat, deep_research, health, history, reports, stream, metrics, conversations, intent, models, documents, review
from .routers import settings as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    app_settings = get_settings()
    logger = structlog.get_logger()
    
    # Setup logging and telemetry
    setup_logging(app_settings.log_level)
    setup_telemetry(app_settings)
    
    # Connect to MongoDB
    await Database.connect_to_mongo()
    
    logger.info("Starting Copilot OS API", version=app.version)
    
    yield

    # Shutdown telemetry
    shutdown_telemetry()

    # Close database connection
    await Database.close_mongo_connection()
    logger.info("Shutting down Copilot OS API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Copilot OS API",
        description="API for chat and deep research using Aletheia orchestrator",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.parsed_allowed_hosts,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.parsed_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Custom middleware
    app.add_middleware(TelemetryMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Exception handlers
    app.add_exception_handler(APIError, api_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # Include routers
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(intent.router, prefix="/api", tags=["intent"])
    app.include_router(deep_research.router, prefix="/api", tags=["research"])
    app.include_router(stream.router, prefix="/api", tags=["streaming"])
    app.include_router(history.router, prefix="/api", tags=["history"])
    app.include_router(conversations.router, prefix="/api", tags=["conversations"])
    app.include_router(reports.router, prefix="/api", tags=["reports"])
    app.include_router(metrics.router, prefix="/api", tags=["monitoring"])
    app.include_router(settings_router.router, prefix="/api", tags=["settings"])
    app.include_router(models.router, prefix="/api", tags=["models"])
    app.include_router(documents.router, prefix="/api", tags=["documents"])
    app.include_router(review.router, prefix="/api", tags=["review"])
    # app.include_router(files.router, prefix="/api", tags=["files"])  # Temporarily disabled - Phase 3

    # Instrument FastAPI for telemetry
    instrument_fastapi(app)

    return app


app = create_app()


if __name__ == "__main__":
    app_settings = get_settings()
    uvicorn.run(
        "main:app",
        host=app_settings.host,
        port=app_settings.port,
        reload=app_settings.debug,
        log_level=app_settings.log_level.lower(),
    )
