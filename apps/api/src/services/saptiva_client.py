"""
Cliente HTTP para SAPTIVA APIs.
Maneja la comunicación con los modelos de lenguaje de SAPTIVA.
"""

import asyncio
import os
import time
from typing import Any, Dict, List, Optional, AsyncGenerator

import httpx
from pydantic import BaseModel

from ..core.config import get_settings
from .settings_service import load_saptiva_api_key
import structlog
logger = structlog.get_logger(__name__)


class SaptivaMessage(BaseModel):
    """Mensaje para SAPTIVA API"""
    role: str
    content: str


class SaptivaRequest(BaseModel):
    """Request para SAPTIVA API optimizada para velocidad"""
    model: str
    messages: List[SaptivaMessage]
    temperature: Optional[float] = 0.3  # Reducir para respuestas más directas y rápidas
    max_tokens: Optional[int] = 800  # Reducir para respuestas más concisas
    stream: bool = True  # Habilitar streaming por defecto
    tools: Optional[List[str]] = None


class SaptivaResponse(BaseModel):
    """Respuesta de SAPTIVA API"""
    id: str
    object: str = "chat.completion"
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, Any]] = None
    created: Optional[int] = None


class SaptivaStreamChunk(BaseModel):
    """Chunk de respuesta streaming de SAPTIVA"""
    id: str
    object: str = "chat.completion.chunk"
    model: str
    choices: List[Dict[str, Any]]
    created: Optional[int] = None


class SaptivaClient:
    """Cliente HTTP para SAPTIVA APIs"""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = getattr(self.settings, 'saptiva_base_url', 'https://api.saptiva.com')
        self.api_key = getattr(self.settings, 'saptiva_api_key', '')
        self.timeout = getattr(self.settings, 'saptiva_timeout', 30)
        self.max_retries = getattr(self.settings, 'saptiva_max_retries', 3)

        # Configurar cliente HTTP optimizado para velocidad y estabilidad
        # Timeouts más generosos para LLM generativo que puede tomar tiempo
        connect_timeout = float(os.getenv("SAPTIVA_CONNECT_TIMEOUT", "10.0"))
        read_timeout = float(os.getenv("SAPTIVA_READ_TIMEOUT", "120.0"))

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout=self.timeout,           # Total timeout (default 30s)
                connect=connect_timeout,        # Connect timeout (10s)
                read=read_timeout,              # Read timeout (120s para streaming)
                write=10.0                      # Write timeout
            ),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),  # Más conexiones concurrentes
            follow_redirects=False,  # Disabled: Saptiva redirects to /completions/ which returns 404
            http2=True,  # Habilitar HTTP/2 para mejor performance
            headers={
                "User-Agent": "Copilot-OS/1.0",
                "Content-Type": "application/json",
                "Connection": "keep-alive"
            }
        )

        # Añadir API key si está configurada
        self.set_api_key(self.api_key)

    def set_api_key(self, api_key: Optional[str]) -> None:
        """Update the API key used for outbound SAPTIVA requests."""
        self.api_key = api_key or ""
        if self.api_key:
            self.client.headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            self.client.headers.pop("Authorization", None)

        # Mapeo de modelos SAPTIVA (según API reference)
        self.model_mapping = {
            "SAPTIVA_CORTEX": "Saptiva Cortex",
            "SAPTIVA_TURBO": "Saptiva Turbo",
            "SAPTIVA_GUARD": "Saptiva Guard",
            "SAPTIVA_OCR": "Saptiva OCR"
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _get_model_name(self, model: str) -> str:
        """Mapea nombres de modelos internos a nombres de SAPTIVA API"""
        # Saptiva API requires exact case (e.g., "Saptiva Turbo", NOT "saptiva turbo")
        return self.model_mapping.get(model, model)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> httpx.Response:
        """Realizar request HTTP con retry logic"""
        # Construct URL manually to avoid urljoin issues with redirects
        url = f"{self.base_url.rstrip('/')}{endpoint}"

        for attempt in range(self.max_retries + 1):
            try:
                if stream:
                    # Para streaming, no usar context manager
                    response = await self.client.request(
                        method=method,
                        url=url,
                        json=data if data else None
                    )
                else:
                    response = await self.client.request(
                        method=method,
                        url=url,
                        json=data if data else None
                    )

                # Handle redirects explicitly (Saptiva redirects but the target URL may not work)
                if response.status_code in (301, 302, 307, 308):
                    redirect_url = response.headers.get("Location", "")
                    logger.warning(
                        "SAPTIVA API returned redirect, may indicate incorrect endpoint",
                        status_code=response.status_code,
                        redirect_to=redirect_url,
                        original_url=url
                    )

                response.raise_for_status()
                return response

            except httpx.HTTPError as e:
                if attempt < self.max_retries:
                    wait_time = min(2 ** attempt, 10)
                    logger.warning(
                        "SAPTIVA request failed, retrying",
                        error=str(e),
                        attempt=attempt + 1,
                        wait_time=wait_time
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "SAPTIVA request failed after all retries",
                        error=str(e),
                        endpoint=endpoint
                    )
                    raise

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "SAPTIVA_CORTEX",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
        tools: Optional[List[str]] = None
    ) -> SaptivaResponse:
        """
        Generar respuesta de chat usando SAPTIVA API

        Args:
            messages: Lista de mensajes [{"role": "user", "content": "..."}]
            model: Modelo SAPTIVA a usar
            temperature: Temperatura para sampling
            max_tokens: Máximo número de tokens
            stream: Si usar streaming
            tools: Herramientas habilitadas

        Returns:
            Respuesta del modelo SAPTIVA
        """

        # Validar API key
        if not self.api_key:
            raise ValueError("SAPTIVA API key is required but not configured")

        try:
            # Convertir mensajes al formato SAPTIVA
            saptiva_messages = [
                SaptivaMessage(role=msg["role"], content=msg["content"])
                for msg in messages
            ]

            # Preparar request
            request_data = SaptivaRequest(
                model=self._get_model_name(model),
                messages=saptiva_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                tools=tools
            ).model_dump(exclude_none=True)

            logger.info(
                "Making SAPTIVA API request",
                model=model,
                message_count=len(messages),
                stream=stream,
                request_payload=request_data
            )

            # Hacer request
            # Note: Saptiva API requires trailing slash
            response = await self._make_request(
                method="POST",
                endpoint="/v1/chat/completions/",
                data=request_data,
                stream=stream
            )

            result = response.json()

            logger.info(
                "SAPTIVA API response received",
                model=model,
                response_id=result.get("id"),
                usage=result.get("usage")
            )

            return SaptivaResponse(**result)

        except Exception as e:
            logger.error(
                "Error calling SAPTIVA API",
                error=str(e),
                model=model
            )
            # Re-raise the exception without fallback
            raise

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "SAPTIVA_CORTEX",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        tools: Optional[List[str]] = None
    ) -> AsyncGenerator[SaptivaStreamChunk, None]:
        """
        Generar respuesta de chat con streaming usando SAPTIVA API
        """

        # Validar API key
        if not self.api_key:
            raise ValueError("SAPTIVA API key is required but not configured")

        try:
            # Convertir mensajes al formato SAPTIVA
            saptiva_messages = [
                SaptivaMessage(role=msg["role"], content=msg["content"])
                for msg in messages
            ]

            # Preparar request con streaming
            request_data = SaptivaRequest(
                model=self._get_model_name(model),
                messages=saptiva_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                tools=tools
            ).model_dump(exclude_none=True)

            logger.info(
                "Starting SAPTIVA streaming request",
                model=model,
                message_count=len(messages)
            )

            # Hacer streaming request (add trailing slash to avoid redirect issues)
            url = f"{self.base_url.rstrip('/')}/v1/chat/completions/"
            async with self.client.stream(
                "POST",
                url,
                json=request_data
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix

                        if data == "[DONE]":
                            break

                        try:
                            import json
                            chunk_data = json.loads(data)  # Parse JSON safely
                            yield SaptivaStreamChunk(**chunk_data)
                        except Exception as e:
                            logger.warning("Error parsing stream chunk", error=str(e))

        except Exception as e:
            logger.error(
                "Error in SAPTIVA streaming",
                error=str(e),
                model=model
            )
            # Re-raise the exception without fallback
            raise



    async def get_available_models(self) -> List[str]:
        """Obtener lista de modelos disponibles"""
        if not self.api_key:
            return list(self.model_mapping.keys())

        try:
            response = await self._make_request("GET", "/v1/models")
            models_data = response.json()
            return [model["id"] for model in models_data.get("data", [])]
        except Exception as e:
            logger.warning("Could not fetch SAPTIVA models", error=str(e))
            return list(self.model_mapping.keys())

    async def health_check(self) -> bool:
        """Verificar si SAPTIVA API está disponible"""
        if not self.api_key:
            return False

        try:
            url = f"{self.base_url.rstrip('/')}/v1/models"
            response = await self.client.get(url)
            return response.status_code == 200
        except Exception:
            return False


# Instancia singleton del cliente
_saptiva_client: Optional[SaptivaClient] = None


async def get_saptiva_client() -> SaptivaClient:
    """Obtener instancia singleton del cliente SAPTIVA"""
    global _saptiva_client

    if _saptiva_client is None:
        _saptiva_client = SaptivaClient()
        stored_key = await load_saptiva_api_key()
        if stored_key:
            _saptiva_client.set_api_key(stored_key)

    return _saptiva_client


async def close_saptiva_client():
    """Cerrar cliente SAPTIVA"""
    global _saptiva_client

    if _saptiva_client:
        await _saptiva_client.client.aclose()
        _saptiva_client = None
