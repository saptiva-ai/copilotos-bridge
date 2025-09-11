"""
FastAPI application for CopilotOS Bridge API.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .core.config import get_settings
from .core.database import Database
from .core.logging import setup_logging
from .core.telemetry import setup_telemetry
from .middleware.auth import AuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .routers import chat, deep_research, health, history, reports, stream


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()
    logger = structlog.get_logger()
    
    # Setup logging and telemetry
    setup_logging(settings.log_level)
    setup_telemetry(settings)
    
    # Connect to MongoDB
    await Database.connect_to_mongo()
    
    logger.info("Starting CopilotOS Bridge API", version=app.version)
    
    yield
    
    # Close database connection
    await Database.close_mongo_connection()
    logger.info("Shutting down CopilotOS Bridge API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="CopilotOS Bridge API",
        description="API for chat and deep research using Aletheia orchestrator",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Custom middleware
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Include routers
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(deep_research.router, prefix="/api", tags=["research"])
    app.include_router(stream.router, prefix="/api", tags=["streaming"])
    app.include_router(history.router, prefix="/api", tags=["history"])
    app.include_router(reports.router, prefix="/api", tags=["reports"])
    
    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )