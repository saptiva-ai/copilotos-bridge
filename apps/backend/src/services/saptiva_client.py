"""
Cliente HTTP para SAPTIVA APIs.
Maneja la comunicación con los modelos de lenguaje de SAPTIVA.
"""

import asyncio
import os
import time
import uuid
from typing import Any, Dict, List, Optional, AsyncGenerator, Tuple

import httpx
from fastapi import HTTPException  # FIX ISSUE-017: For timeout exception handling
from pydantic import BaseModel

from ..core.config import get_settings
from .settings_service import load_saptiva_api_key
import structlog
logger = structlog.get_logger(__name__)

_global_mock_mode: bool = False
_global_mock_reason: Optional[str] = None


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse truthy environment flags (1/true/yes/on)."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
    tools: Optional[List[Dict[str, Any]]] = None  # JSON schemas for function-calling


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
        global _global_mock_mode, _global_mock_reason
        self.force_mock_reason: Optional[str] = None
        env_force_mock = _env_flag("SAPTIVA_FORCE_MOCK", False)
        if env_force_mock:
            self.force_mock = True
            self.force_mock_reason = "forced_via_env"
        elif _global_mock_mode:
            self.force_mock = True
            self.force_mock_reason = _global_mock_reason or "fallback_on_error"
        else:
            self.force_mock = False
        # Default: do NOT fall back to mock when an API key is configured.
        # You can re-enable fallback by setting SAPTIVA_ALLOW_MOCK_FALLBACK=1.
        self.allow_mock_fallback = _env_flag(
            "SAPTIVA_ALLOW_MOCK_FALLBACK",
            False if self.api_key else True,
        )
        self.mock_mode = False
        self.mock_reason: Optional[str] = None
        self._last_mock_reason: Optional[str] = None

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
            follow_redirects=True,  # Enable redirects: Saptiva redirects /completions to /completions/
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
            "SAPTIVA_OCR": "Saptiva OCR",
            # Aliases en minúsculas para compatibilidad
            "saptiva-cortex": "Saptiva Cortex",
            "saptiva-turbo": "Saptiva Turbo",
            "saptiva-guard": "Saptiva Guard",
            "saptiva-ocr": "Saptiva OCR"
        }
        if self.force_mock:
            self._enable_mock_mode(self.force_mock_reason or "forced_via_env")
        elif not self.api_key:
            self._enable_mock_mode("missing_api_key")
        else:
            self.mock_mode = False
            self.mock_reason = None

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

        retries = self.max_retries
        if self.allow_mock_fallback and not self.force_mock:
            retries = 0

        for attempt in range(retries + 1):
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
                if attempt < retries:
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
        if self.mock_mode:
            if self.mock_reason == "missing_api_key":
                raise RuntimeError(
                    "SAPTIVA API no está configurada (falta SAPTIVA_API_KEY/SAPTIVA_BASE_URL)."
                )
            return self._generate_mock_response(messages, model)

        if not self.api_key:
            if self.allow_mock_fallback:
                self._enable_mock_mode("missing_api_key")
                return self._generate_mock_response(messages, model)
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
            # Note: Saptiva API requires trailing slash (redirects 307 otherwise)
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
            if self.allow_mock_fallback:
                self._enable_mock_mode("fallback_on_error")
                return self._generate_mock_response(messages, model)
            raise

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "SAPTIVA_CORTEX",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        tools: Optional[List[str]] = None,
        timeout: int = 120  # FIX ISSUE-017: Default 2 minutes timeout
    ) -> AsyncGenerator[SaptivaStreamChunk, None]:
        """
        Generar respuesta de chat con streaming usando SAPTIVA API

        Args:
            timeout: Timeout in seconds for the entire streaming operation (default: 120s)
        """

        # Validar API key
        if self.mock_mode:
            async for chunk in self._mock_stream_response(messages, model, temperature, max_tokens, tools):
                yield chunk
            return

        if not self.api_key:
            if self.allow_mock_fallback:
                self._enable_mock_mode("missing_api_key")
                async for chunk in self._mock_stream_response(messages, model, temperature, max_tokens, tools):
                    yield chunk
                return
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
                message_count=len(messages),
                timeout_seconds=timeout
            )

            # FIX ISSUE-017: Wrap streaming with timeout
            try:
                async with asyncio.timeout(timeout):
                    # Hacer streaming request (Saptiva requires trailing slash)
                    url = f"{self.base_url.rstrip('/')}/v1/chat/completions/"
                    async with self.client.stream(
                        "POST",
                        url,
                        json=request_data
                    ) as response:
                        # Log error details before raising
                        if response.status_code >= 400:
                            error_body = await response.aread()
                            logger.error(
                                "Saptiva API error response",
                                status_code=response.status_code,
                                error_body=error_body.decode('utf-8'),
                                request_url=url,
                                model=model
                            )
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

            except asyncio.TimeoutError:
                logger.error(
                    "Saptiva streaming timed out",
                    model=model,
                    timeout=timeout,
                    message_count=len(messages)
                )
                raise HTTPException(
                    status_code=504,  # Gateway Timeout
                    detail=f"Saptiva API timed out after {timeout}s"
                )

        except Exception as e:
            import traceback
            error_info = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc(),
                "model": model,
                "message_count": len(messages),
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            logger.error(
                "🚨 SAPTIVA STREAMING ERROR - CRITICAL",
                **error_info,
                exc_info=True
            )

            # Print to stderr for immediate visibility
            print(f"\n{'='*80}")
            print(f"🚨 SAPTIVA CLIENT STREAMING ERROR")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            print(f"Model: {model}")
            print(f"Traceback:\n{traceback.format_exc()}")
            print(f"{'='*80}\n")

            # Re-raise the exception without fallback
            if self.allow_mock_fallback:
                self._enable_mock_mode("fallback_on_error")
                async for chunk in self._mock_stream_response(messages, model, temperature, max_tokens, tools):
                    yield chunk
                return
            raise

    async def chat_completion_or_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "SAPTIVA_CORTEX",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
        tools: Optional[List[str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        BE-3 MVP: Unified wrapper for streaming and non-streaming completions.

        This wrapper provides a consistent async generator interface regardless
        of whether streaming is enabled. When stream=False, it yields a single
        "final" response. When stream=True, it yields chunks as they arrive.

        This design enables future streaming support without changing calling code.

        Args:
            messages: Lista de mensajes [{"role": "user", "content": "..."}]
            model: Modelo SAPTIVA a usar
            temperature: Temperatura para sampling
            max_tokens: Máximo número de tokens
            stream: Si usar streaming (False por defecto en V1 MVP)
            tools: Herramientas habilitadas

        Yields:
            Dict con estructura:
            - Si stream=False: {"type": "final", "content": str}
            - Si stream=True: SaptivaStreamChunk objects con delta updates

        Example:
            >>> async for chunk in client.chat_completion_or_stream(messages, stream=False):
            ...     if chunk["type"] == "final":
            ...         print(chunk["content"])
        """
        if stream:
            # BE-3: Stream mode - yield chunks as they arrive
            async for chunk in self.chat_completion_stream(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools
            ):
                yield {"type": "chunk", "data": chunk}
        else:
            # BE-3: Non-streaming mode - yield single final response
            response = await self.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                tools=tools
            )

            # Extract content from response
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].get("message", {}).get("content", "")
            else:
                content = ""

            yield {
                "type": "final",
                "content": content,
                "response": response  # Include full response for metadata
            }

    def _enable_mock_mode(self, reason: str) -> None:
        """Enable mock mode and log once per reason."""
        self.mock_mode = True
        self.mock_reason = reason
        global _global_mock_mode, _global_mock_reason
        _global_mock_mode = True
        _global_mock_reason = reason
        if self._last_mock_reason != reason:
            logger.warning(
                "SAPTIVA client running in mock mode",
                reason=reason
            )
            self._last_mock_reason = reason

    def _generate_mock_response(
        self,
        messages: List[Dict[str, str]],
        model: str
    ) -> SaptivaResponse:
        """Generate deterministic mock responses for local development."""
        last_message = messages[-1]["content"] if messages else ""
        message_lower = last_message.lower()

        if "hola" in message_lower or "hello" in message_lower:
            content = "¡Hola! Soy SAPTIVA en modo demo para capital414-chat. ¿En qué puedo ayudarte hoy?"
        elif "?" in last_message:
            content = (
                f"Entiendo tu pregunta sobre \"{last_message}\". "
                "En este entorno de desarrollo respondo con ejemplos mientras la API real no está disponible."
            )
        else:
            content = (
                f"He recibido tu mensaje: \"{last_message}\". "
                "Esta es una respuesta simulada porque la integración con SAPTIVA no está activa."
            )

        prompt_tokens = sum(len(msg.get("content", "").split()) for msg in messages)
        completion_tokens = len(content.split())

        response = SaptivaResponse(
            id=f"mock-{uuid.uuid4()}",
            model=self._get_model_name(model),
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            created=int(time.time())
        )

        logger.info(
            "Generated mock SAPTIVA response",
            model=model,
            reason=self.mock_reason or "mock_mode"
        )

        return response

    async def _mock_stream_response(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[List[str]]
    ) -> AsyncGenerator[SaptivaStreamChunk, None]:
        """Yield mock streaming chunks to emulate SAPTIVA API behaviour."""
        response = self._generate_mock_response(messages, model)
        content = response.choices[0]["message"]["content"]
        chunk_id = response.id
        created_ts = response.created or int(time.time())

        # First chunk includes the assistant role declaration
        yield SaptivaStreamChunk(
            id=chunk_id,
            model=response.model,
            choices=[{
                "index": 0,
                "delta": {
                    "role": "assistant"
                },
                "finish_reason": None
            }],
            created=created_ts
        )

        # Second chunk streams the full content
        yield SaptivaStreamChunk(
            id=chunk_id,
            model=response.model,
            choices=[{
                "index": 0,
                "delta": {
                    "content": content
                },
                "finish_reason": None
            }],
            created=created_ts
        )

        # Final chunk marks completion
        yield SaptivaStreamChunk(
            id=chunk_id,
            model=response.model,
            choices=[{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }],
            created=created_ts
        )

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


# Singleton instance (module-level for synchronous imports)
# This matches the pattern used by languagetool_client for consistency
saptiva_client = SaptivaClient()


# ============================================================================
# PAYLOAD BUILDER — Sistema de prompts por modelo con inyección de tools
# ============================================================================

async def build_messages(
    user_prompt: str,
    user_context: Optional[Dict[str, Any]],
    system_text: str,
    chat_id: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Construir array de mensajes con order: System → Historial → User (con contexto).

    Args:
        user_prompt: Solicitud del usuario
        user_context: Contexto adicional (dict con campos arbitrarios)
        system_text: System prompt completo y resuelto
        chat_id: ID del chat para recuperar historial (opcional)

    Returns:
        Lista de mensajes en formato [{role, content}]

    Example:
        >>> await build_messages("Hola", {"session": "123"}, "Eres un asistente")
        [
            {"role": "system", "content": "Eres un asistente"},
            {"role": "user", "content": "Contexto:\\n{...}\\n\\nSolicitud:\\nHola"}
        ]
    """
    from ..models.chat import ChatMessage as ChatMessageModel
    from ..core.config import get_settings

    messages = []

    # 1. System prompt
    messages.append({
        "role": "system",
        "content": system_text
    })

    # 2. Historial de conversación (si existe chat_id)
    logger.info(
        "🔍 [HISTORY DEBUG] build_messages called",
        has_chat_id=bool(chat_id),
        chat_id=chat_id
    )

    if chat_id:
        try:
            settings = get_settings()
            # Recuperar últimos N mensajes (excluyendo el actual)
            recent_limit = getattr(settings, 'memory_recent_messages', 20)

            # CRITICAL FIX: Skip the most recent message (current user message)
            # because it was already saved to DB before build_messages() is called.
            # We fetch recent_limit + 1 messages, skip the first one (most recent),
            # and use the next recent_limit messages as history.
            all_recent = await ChatMessageModel.find(
                ChatMessageModel.chat_id == chat_id
            ).sort(-ChatMessageModel.created_at).limit(recent_limit + 1).to_list()

            # Skip the first message (most recent = current user message just saved)
            recent_messages = all_recent[1:] if len(all_recent) > 0 else []

            # Agregar en orden cronológico (más antiguo primero)
            for msg in reversed(recent_messages):
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

            logger.info(
                "🔍 [HISTORY DEBUG] Added conversation history to messages",
                chat_id=chat_id,
                history_count=len(recent_messages),
                total_fetched=len(all_recent),
                skipped_current=len(all_recent) > 0,
                recent_messages_preview=[
                    f"{msg.role.value}: {msg.content[:50]}..."
                    for msg in reversed(recent_messages)
                ][:3]
            )
        except Exception as e:
            logger.warning(
                "Failed to load conversation history, continuing without it",
                chat_id=chat_id,
                error=str(e),
                exc_info=True
            )

    # 3. User prompt con contexto opcional
    user_content_parts = []

    if user_context and len(user_context) > 0:
        # Serializar contexto de forma legible
        context_lines = []
        for key, value in user_context.items():
            # Serializar valor (si es dict/list, formatear JSON)
            if isinstance(value, (dict, list)):
                import json
                value_str = json.dumps(value, ensure_ascii=False, indent=2)
            else:
                value_str = str(value)
            context_lines.append(f"- {key}: {value_str}")

        user_content_parts.append("Contexto:\n" + "\n".join(context_lines))

    user_content_parts.append(f"Solicitud:\n{user_prompt}")

    messages.append({
        "role": "user",
        "content": "\n\n".join(user_content_parts)
    })

    logger.debug(
        "Built message array",
        system_length=len(system_text),
        user_length=len(user_prompt),
        has_context=user_context is not None,
        message_count=len(messages)
    )

    return messages


async def build_payload(
    model: str,
    user_prompt: str,
    user_context: Optional[Dict[str, Any]] = None,
    tools_enabled: Optional[Dict[str, bool]] = None,
    channel: str = "chat",
    chat_id: Optional[str] = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Construir payload completo para Saptiva API con system prompt por modelo.

    Esta función orquesta:
    1. Resolución de system prompt desde PromptRegistry
    2. Inyección de herramientas disponibles
    3. Ensamblaje de mensajes (System → Historial → User con contexto)
    4. Aplicación de parámetros por modelo y canal
    5. Generación de metadata para telemetría

    Args:
        model: Nombre del modelo (e.g., "Saptiva Turbo", "Saptiva Cortex")
        user_prompt: Solicitud del usuario
        user_context: Contexto adicional (opcional)
        tools_enabled: Dict de herramientas habilitadas {tool_name: bool} (opcional)
        channel: Canal de comunicación (chat, report, title, etc.)
        chat_id: ID del chat para recuperar historial (opcional)

    Returns:
        Tupla de (payload, metadata) donde:
        - payload: Dict listo para POST a /v1/chat/completions
        - metadata: Dict con info de telemetría (request_id, system_hash, etc.)

    Example:
        >>> payload, meta = build_payload(
        ...     model="Saptiva Turbo",
        ...     user_prompt="¿Qué es Python?",
        ...     channel="chat"
        ... )
        >>> "messages" in payload
        True
        >>> "request_id" in meta
        True
    """
    from ..core.config import get_settings
    from ..core.prompt_registry import get_prompt_registry
    from .tools import build_tools_context, DEFAULT_AVAILABLE_TOOLS

    settings = get_settings()

    # Feature flag: si está deshabilitado, usar comportamiento legacy
    if not settings.enable_model_system_prompt:
        logger.info(
            "Model system prompt feature disabled, using legacy behavior",
            model=model,
            channel=channel
        )
        # Comportamiento legacy: mensajes simples sin system prompt estructurado
        legacy_messages = [{"role": "user", "content": user_prompt}]
        legacy_payload = {
            "model": model,
            "messages": legacy_messages,
            "temperature": 0.7,
            "max_tokens": 1024
        }
        legacy_metadata = {
            "request_id": str(uuid.uuid4()),
            "model": model,
            "channel": channel,
            "legacy_mode": True
        }
        return legacy_payload, legacy_metadata

    # 1. Obtener registro de prompts
    try:
        registry = get_prompt_registry()
    except Exception as e:
        logger.error("Failed to load prompt registry, falling back to legacy", error=str(e))
        # Fallback a legacy si falla la carga
        legacy_messages = [{"role": "user", "content": user_prompt}]
        legacy_payload = {
            "model": model,
            "messages": legacy_messages,
            "temperature": 0.7,
            "max_tokens": 1024
        }
        legacy_metadata = {
            "request_id": str(uuid.uuid4()),
            "model": model,
            "channel": channel,
            "error": "registry_load_failed"
        }
        return legacy_payload, legacy_metadata

    # 2. Construir contexto de herramientas
    # IMPORTANTE: Solo inyectar herramientas si están explícitamente habilitadas
    # No mostrar herramientas disponibles por defecto para evitar que el modelo las sugiera
    tools_markdown = None
    tools_schemas = None

    if tools_enabled and any(tools_enabled.values()):
        # Solo inyectar si al menos una herramienta está activa
        tools_markdown, tools_schemas = build_tools_context(
            tools_enabled=tools_enabled,
            available_tools=DEFAULT_AVAILABLE_TOOLS
        )

    # 3. Resolver system prompt y parámetros
    system_text, params = registry.resolve(
        model=model,
        tools_markdown=tools_markdown,
        channel=channel
    )

    # 4. Construir mensajes (con historial si chat_id está disponible)
    messages = await build_messages(
        user_prompt=user_prompt,
        user_context=user_context,
        system_text=system_text,
        chat_id=chat_id
    )

    # 5. Ensamblar payload
    payload = {
        "model": model,
        "messages": messages,
        "temperature": params.get("temperature", 0.3),
        "top_p": params.get("top_p", 0.9),
        "presence_penalty": params.get("presence_penalty", 0.0),
        "frequency_penalty": params.get("frequency_penalty", 0.2),
        "max_tokens": params.get("max_tokens", 1200),
    }

    # Parámetros opcionales adicionales (solo si están definidos)
    if "stop" in params and params["stop"] is not None:
        payload["stop"] = params["stop"]
    if "n" in params and params["n"] is not None:
        payload["n"] = params["n"]
    if "seed" in params and params["seed"] is not None:
        payload["seed"] = params["seed"]

    # Agregar tools schemas si existen (function-calling)
    if tools_schemas:
        payload["tools"] = tools_schemas

    # 6. Extraer metadata para telemetría (NO incluir en payload)
    metadata = params.get("_metadata", {})
    metadata["request_id"] = str(uuid.uuid4())

    # Limpiar metadata del payload (no enviarlo a la API)
    if "_metadata" in params:
        del params["_metadata"]

    logger.info(
        "Built Saptiva payload with model-specific prompt",
        model=model,
        channel=channel,
        request_id=metadata["request_id"],
        system_hash=metadata.get("system_hash"),
        prompt_version=metadata.get("prompt_version"),
        max_tokens=payload["max_tokens"],
        temperature=payload["temperature"],
        has_tools=tools_schemas is not None,
        message_count=len(messages)
    )

    return payload, metadata
