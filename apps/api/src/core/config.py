"""
Configuration management for the FastAPI application.
"""

import os
import logging
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Import secrets manager - handle import error gracefully during development
try:
    from .secrets import get_secret, get_database_url, mask_secret
    SECRETS_AVAILABLE = True
except ImportError:
    logging.warning("Secrets manager not available, falling back to environment variables")
    SECRETS_AVAILABLE = False

    def get_secret(name: str, required: bool = True, min_length: int = 8) -> Optional[str]:
        return os.getenv(name)

    def get_database_url(service: str = "mongodb") -> str:
        if service == "mongodb":
            return os.getenv("MONGODB_URL", "")
        elif service == "redis":
            return os.getenv("REDIS_URL", "")
        return ""

    def mask_secret(secret: str, visible_chars: int = 4) -> str:
        if len(secret) <= visible_chars * 2:
            return "*" * len(secret)
        return secret[:visible_chars] + "*" * (len(secret) - visible_chars * 2) + secret[-visible_chars:]

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
    app_name: str = Field(default="Copilot OS API")
    app_version: str = Field(default="0.1.0")
    app_description: str = Field(default="API for chat and deep research")
    
    # Database (MongoDB) - Secure configuration
    db_min_pool_size: int = Field(default=10, description="MongoDB min connection pool size")
    db_max_pool_size: int = Field(default=100, description="MongoDB max connection pool size")
    db_connection_timeout_ms: int = Field(default=5000, description="MongoDB connection timeout")
    db_server_selection_timeout_ms: int = Field(default=5000, description="MongoDB server selection timeout")
    db_max_idle_time_ms: int = Field(default=300000, description="MongoDB max idle time in ms")
    db_connect_timeout_ms: int = Field(default=10000, description="MongoDB connect timeout")

    # Redis - Secure configuration
    redis_pool_size: int = Field(default=10, description="Redis connection pool size")

    @computed_field
    @property
    def mongodb_url(self) -> str:
        """MongoDB connection URL with secure credentials."""
        try:
            return get_database_url("mongodb")
        except Exception:
            # Fallback to environment variable for compatibility
            return os.getenv("MONGODB_URL", "")

    @computed_field
    @property
    def redis_url(self) -> str:
        """Redis connection URL with secure credentials."""
        try:
            return get_database_url("redis")
        except Exception:
            # Fallback to environment variable for compatibility
            return os.getenv("REDIS_URL", "")

    @computed_field
    @property
    def jwt_secret_key(self) -> str:
        """JWT secret key from secure source."""
        try:
            return get_secret("JWT_SECRET_KEY", required=True, min_length=32)
        except Exception:
            # Fallback to environment variable for compatibility
            return os.getenv("JWT_SECRET_KEY", "")

    @computed_field
    @property
    def secret_key(self) -> str:
        """Application secret key from secure source."""
        try:
            return get_secret("SECRET_KEY", required=True, min_length=32)
        except Exception:
            # Fallback to environment variable for compatibility
            return os.getenv("SECRET_KEY", "")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(default=60, description="Access token expiry")
    jwt_refresh_token_expire_days: int = Field(default=7, description="Refresh token expiry")
    
    # Aletheia
    aletheia_base_url: str = Field(
        default="http://aletheia:8000",
        description="Aletheia API base URL"
    )
    aletheia_api_key: str = Field(default="", description="Aletheia API key")
    aletheia_timeout: int = Field(default=120, description="Aletheia request timeout")
    aletheia_max_retries: int = Field(default=3, description="Aletheia max retries")

    # Deep Research Kill Switch (P0-DR-KILL-001)
    # This is a GLOBAL kill switch that completely disables Deep Research
    # When enabled, all research endpoints return 410 GONE
    deep_research_kill_switch: bool = Field(
        default=True,
        description="KILL SWITCH: When True, Deep Research is completely disabled (returns 410 GONE)"
    )

    # Legacy flags (kept for backward compatibility but dominated by kill switch)
    deep_research_enabled: bool = Field(
        default=False,
        description="Master switch for Deep Research feature (overridden by kill_switch)"
    )
    deep_research_auto: bool = Field(
        default=False,
        description="Auto-trigger Deep Research (overridden by kill_switch)"
    )
    deep_research_complexity_threshold: float = Field(
        default=0.7,
        description="Complexity threshold for auto-triggering (0.0-1.0)"
    )

    # Chat Configuration (P0-CHAT-BASE-004)
    # Saptiva model names use spaces, not underscores
    chat_default_model: str = Field(
        default="Saptiva Turbo",
        description="Default model for simple chat when kill switch is active"
    )
    chat_allowed_models: str = Field(
        default="Saptiva Turbo,Saptiva Cortex,Saptiva Ops,Saptiva Coder,Saptiva Legacy",
        description="Comma-separated list of allowed chat models"
    )

    # SAPTIVA
    saptiva_base_url: str = Field(default="https://api.saptiva.com", description="SAPTIVA API base URL")
    saptiva_timeout: int = Field(default=30, description="SAPTIVA request timeout")
    saptiva_max_retries: int = Field(default=3, description="SAPTIVA max retries")

    @computed_field
    @property
    def saptiva_api_key(self) -> str:
        """SAPTIVA API key from secure source."""
        try:
            return get_secret("SAPTIVA_API_KEY", required=False) or ""
        except Exception:
            # Fallback to environment variable
            return os.getenv("SAPTIVA_API_KEY", "")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_calls: int = Field(default=100, description="Rate limit calls per period")
    rate_limit_period: int = Field(default=60, description="Rate limit period in seconds")
    
    # CORS - Parse from environment variable or use defaults
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins (comma-separated or JSON array)"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow CORS credentials")
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="Allowed hosts (comma-separated or JSON array)"
    )

    @computed_field
    @property
    def parsed_cors_origins(self) -> List[str]:
        """Parse CORS origins from environment variable supporting both JSON and CSV format."""
        import json
        cors_str = os.getenv("CORS_ORIGINS", "")

        if not cors_str:
            return self.cors_origins

        # Try parsing as JSON array first
        try:
            parsed = json.loads(cors_str)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: split by comma
        return [origin.strip() for origin in cors_str.split(",") if origin.strip()]

    @computed_field
    @property
    def parsed_allowed_hosts(self) -> List[str]:
        """Parse allowed hosts from environment variable supporting both JSON and CSV format."""
        import json
        hosts_str = os.getenv("ALLOWED_HOSTS", "")

        if not hosts_str:
            return self.allowed_hosts

        # Try parsing as JSON array first
        try:
            parsed = json.loads(hosts_str)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: split by comma
        return [host.strip() for host in hosts_str.split(",") if host.strip()]
    
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

    # Prompt Registry (System Prompts por Modelo)
    prompt_registry_path: str = Field(
        default="apps/api/prompts/registry.yaml",
        description="Ruta al archivo YAML de registro de prompts"
    )
    enable_model_system_prompt: bool = Field(
        default=True,
        description="Feature flag: habilitar system prompts por modelo"
    )

    def log_config_safely(self) -> dict:
        """Return configuration for logging with secrets masked."""
        config = {}
        for field_name, field_info in self.model_fields.items():
            value = getattr(self, field_name)
            if "secret" in field_name.lower() or "password" in field_name.lower() or "key" in field_name.lower():
                config[field_name] = mask_secret(str(value)) if value else "<not_set>"
            elif "url" in field_name.lower() and ("mongodb" in field_name.lower() or "redis" in field_name.lower()):
                # Mask credentials in connection URLs
                if value:
                    # Extract and mask password from URLs like mongodb://user:pass@host
                    import re
                    masked_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', value)
                    config[field_name] = masked_url
                else:
                    config[field_name] = "<not_set>"
            else:
                config[field_name] = value
        return config
    
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
