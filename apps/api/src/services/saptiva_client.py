"""
Cliente HTTP para SAPTIVA APIs.
Maneja la comunicación con los modelos de lenguaje de SAPTIVA.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncGenerator
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel

from ..core.config import get_settings
import structlog
logger = structlog.get_logger(__name__)


class SaptivaMessage(BaseModel):
    """Mensaje para SAPTIVA API"""
    role: str
    content: str


class SaptivaRequest(BaseModel):
    """Request para SAPTIVA API"""
    model: str
    messages: List[SaptivaMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    stream: bool = False
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

        # Configurar cliente HTTP
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            follow_redirects=True,  # Re-enable redirects with manual URL construction
            headers={
                "User-Agent": "Copilot-OS/1.0",
                "Content-Type": "application/json"
            }
        )

        # Añadir API key si está configurada
        if self.api_key:
            self.client.headers["Authorization"] = f"Bearer {self.api_key}"

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
        return self.model_mapping.get(model, model.lower())

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

        # Si no hay API key, usar mock
        if not self.api_key:
            return await self._generate_mock_response(messages, model)

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

            # Hacer request (add trailing slash to avoid redirect issues)
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
                "Error calling SAPTIVA API, falling back to mock",
                error=str(e),
                model=model
            )
            # Fallback a mock en caso de error
            return await self._generate_mock_response(messages, model)

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

        # Si no hay API key, usar mock stream
        if not self.api_key:
            async for chunk in self._generate_mock_stream(messages, model):
                yield chunk
            return

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
                "Error in SAPTIVA streaming, falling back to mock",
                error=str(e),
                model=model
            )
            # Fallback a mock stream
            async for chunk in self._generate_mock_stream(messages, model):
                yield chunk

    async def _generate_mock_response(
        self,
        messages: List[Dict[str, str]],
        model: str
    ) -> SaptivaResponse:
        """Generar respuesta mock cuando SAPTIVA no está disponible"""

        last_message = messages[-1]["content"] if messages else "Hello"

        # Respuestas mock más inteligentes basadas en el contenido
        if "hola" in last_message.lower() or "hello" in last_message.lower():
            content = "¡Hola! Soy SAPTIVA, tu asistente de inteligencia artificial. ¿En qué puedo ayudarte hoy?"
        elif "cómo estás" in last_message.lower():
            content = "¡Estoy funcionando perfectamente! Gracias por preguntar. ¿Hay algo específico en lo que pueda asistirte?"
        elif "?" in last_message:
            content = f"Entiendo tu pregunta sobre: '{last_message}'. Como estoy en modo demo, esta es una respuesta de ejemplo. Para respuestas reales, necesito estar conectado a los modelos SAPTIVA."
        else:
            content = f"He recibido tu mensaje: '{last_message}'. Esta es una respuesta de demostración. Para usar los modelos SAPTIVA reales, es necesario configurar las credenciales de API."

        return SaptivaResponse(
            id=f"mock-{int(time.time())}",
            model=model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": len(last_message.split()),
                "completion_tokens": len(content.split()),
                "total_tokens": len(last_message.split()) + len(content.split())
            },
            created=int(time.time())
        )

    async def _generate_mock_stream(
        self,
        messages: List[Dict[str, str]],
        model: str
    ) -> AsyncGenerator[SaptivaStreamChunk, None]:
        """Generar stream mock cuando SAPTIVA no está disponible"""

        # Generar respuesta completa primero
        mock_response = await self._generate_mock_response(messages, model)
        content = mock_response.choices[0]["message"]["content"]

        # Simular streaming dividiendo la respuesta en chunks
        words = content.split()
        chunk_id = f"mock-stream-{int(time.time())}"

        for i, word in enumerate(words):
            chunk = SaptivaStreamChunk(
                id=chunk_id,
                model=model,
                choices=[{
                    "index": 0,
                    "delta": {
                        "content": word + " " if i < len(words) - 1 else word
                    },
                    "finish_reason": None if i < len(words) - 1 else "stop"
                }],
                created=int(time.time())
            )
            yield chunk

            # Simular latencia realista
            await asyncio.sleep(0.05)

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

    return _saptiva_client


async def close_saptiva_client():
    """Cerrar cliente SAPTIVA"""
    global _saptiva_client

    if _saptiva_client:
        await _saptiva_client.client.aclose()
        _saptiva_client = None
