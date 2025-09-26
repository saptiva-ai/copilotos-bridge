"""
Global exception handlers for the FastAPI application.
"""

import traceback
from typing import Any, Union

import structlog
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings

logger = structlog.get_logger(__name__)


async def validation_exception_handler(request: Request, exc: Union[RequestValidationError, ValidationError]) -> JSONResponse:
    """Handle validation errors."""
    # Convert errors to JSON serializable format
    errors = []
    for error in exc.errors():
        error_dict = {
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
        }
        # Add input if it exists and is JSON serializable
        if "input" in error:
            try:
                import json
                json.dumps(error["input"])
                error_dict["input"] = error["input"]
            except (TypeError, ValueError):
                # Skip non-serializable input
                pass
        errors.append(error_dict)

    logger.warning(
        "Validation error",
        path=request.url.path,
        method=request.method,
        errors=errors,
        client_ip=request.client.host if request.client else None
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors,
            "type": "validation_error"
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(
        "HTTP exception",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail,
        client_ip=request.client.host if request.client else None
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "type": "http_error"
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    settings = get_settings()

    # Log the full traceback for debugging
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
        traceback=traceback.format_exc() if settings.debug else None,
        client_ip=request.client.host if request.client else None
    )

    # Return sanitized error response
    if settings.debug:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "error_type": type(exc).__name__,
                "traceback": traceback.format_exc(),
                "type": "internal_error"
            }
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "type": "internal_error"
            }
        )


# Custom exception classes
class APIError(Exception):
    """Base API exception."""

    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class DatabaseError(APIError):
    """Database operation error."""

    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(detail, status.HTTP_500_INTERNAL_SERVER_ERROR)


class BadRequestError(APIError):
    """Input validation / bad request error."""

    def __init__(self, detail: Any = "Bad request"):
        super().__init__(detail, status.HTTP_400_BAD_REQUEST)


class AuthenticationError(APIError):
    """Authentication error."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(detail, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(APIError):
    """Authorization error."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(detail, status.HTTP_403_FORBIDDEN)


class NotFoundError(APIError):
    """Resource not found error."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail, status.HTTP_404_NOT_FOUND)


class ConflictError(APIError):
    """Resource conflict error."""

    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(detail, status.HTTP_409_CONFLICT)


async def api_exception_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle custom API exceptions."""
    logger.warning(
        "API exception",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail,
        error_type=type(exc).__name__,
        client_ip=request.client.host if request.client else None
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "type": "api_error"
        }
    )
