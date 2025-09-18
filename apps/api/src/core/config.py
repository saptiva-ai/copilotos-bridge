"""
Configuration management for the FastAPI application.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Server
    host: str = Field(default="0.0.0.0", description="Host to bind the server")
    port: int = Field(default=8000, description="Port to bind the server")
    debug: bool = Field(default=False, description="Enable debug mode")
    reload: bool = Field(default=False, description="Enable auto-reload")
    
    # Application
    app_name: str = Field(default="CopilotOS Bridge API")
    app_version: str = Field(default="0.1.0")
    app_description: str = Field(default="API for chat and deep research")
    
    # Database (MongoDB)
    mongodb_url: str = Field(..., description="MongoDB connection URL")
    db_min_pool_size: int = Field(default=10, description="MongoDB min connection pool size")
    db_max_pool_size: int = Field(default=100, description="MongoDB max connection pool size")
    db_connection_timeout_ms: int = Field(default=5000, description="MongoDB connection timeout")
    db_server_selection_timeout_ms: int = Field(default=5000, description="MongoDB server selection timeout")
    db_max_idle_time_ms: int = Field(default=300000, description="MongoDB max idle time in ms")
    db_connect_timeout_ms: int = Field(default=10000, description="MongoDB connect timeout")
    
    # Redis
    redis_url: str = Field(..., description="Redis connection URL")
    redis_pool_size: int = Field(default=10, description="Redis connection pool size")
    
    # Authentication
    jwt_secret_key: str = Field(..., description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(default=60, description="Access token expiry")
    jwt_refresh_token_expire_days: int = Field(default=7, description="Refresh token expiry")
    
    # Aletheia
    aletheia_base_url: str = Field(..., description="Aletheia API base URL")
    aletheia_api_key: str = Field(default="", description="Aletheia API key")
    aletheia_timeout: int = Field(default=120, description="Aletheia request timeout")
    aletheia_max_retries: int = Field(default=3, description="Aletheia max retries")

    # SAPTIVA
    saptiva_base_url: str = Field(default="https://api.saptiva.ai", description="SAPTIVA API base URL")
    saptiva_api_key: str = Field(default="", description="SAPTIVA API key")
    saptiva_timeout: int = Field(default=30, description="SAPTIVA request timeout")
    saptiva_max_retries: int = Field(default=3, description="SAPTIVA max retries")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_calls: int = Field(default=100, description="Rate limit calls per period")
    rate_limit_period: int = Field(default=60, description="Rate limit period in seconds")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow CORS credentials")
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="Allowed hosts"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format")
    
    # OpenTelemetry
    otel_service_name: str = Field(default="copilotos-api", description="OTel service name")
    otel_exporter_otlp_endpoint: str = Field(
        default="", description="OTel OTLP endpoint"
    )
    
    # Security
    secure_cookies: bool = Field(default=False, description="Use secure cookies")
    https_only: bool = Field(default=False, description="HTTPS only mode")
    secret_key: str = Field(..., description="Secret key for sessions")
    
    # File Upload
    max_file_size: int = Field(default=10485760, description="Max file size in bytes")
    allowed_file_types: List[str] = Field(
        default=["txt", "md", "pdf", "docx"],
        description="Allowed file types"
    )
    
    # Background Tasks
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()