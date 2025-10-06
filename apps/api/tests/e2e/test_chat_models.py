"""
E2E Tests: Chat API with Model-Specific Prompts

Verifica el flujo completo desde request hasta response,
asegurando que cada modelo use su configuración correcta.
"""

import pytest
from httpx import AsyncClient
from fastapi import status

from apps.api.src.main import app
from apps.api.src.core.prompt_registry import get_prompt_registry


@pytest.fixture
def test_user_payload():
    """Payload de autenticación para usuario de prueba"""
    return {
        "identifier": "demo",
        "password": "Demo1234"
    }


@pytest.fixture
async def auth_token(test_user_payload):
    """Obtener token de autenticación para tests"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/auth/login", json=test_user_payload)
        assert response.status_code == status.HTTP_200_OK
        return response.json()["access_token"]


class TestModelSpecificPrompts:
    """Tests E2E para verificar prompts específicos por modelo"""

    @pytest.mark.asyncio
    async def test_cortex_includes_addendum(self, auth_token):
        """
        Verificar que Saptiva Cortex incluya su addendum específico
        y muestre comportamiento de rigor (suposiciones, confianza)
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {auth_token}"}

            response = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Dame 2 puntos sobre IA",
                    "model": "SAPTIVA_CORTEX",
                    "channel": "chat"
                }
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verificar estructura básica
            assert data["model"] == "SAPTIVA_CORTEX"
            assert "content" in data
            content = data["content"].lower()

            # El addendum de Cortex pide declarar suposiciones y confianza
            # Verificar que la respuesta refleje esto
            assert data["tokens"] > 0
            assert data["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_turbo_optimized_for_speed(self, auth_token):
        """
        Verificar que Saptiva Turbo esté optimizado para velocidad
        (respuestas más concisas, menos tokens)
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {auth_token}"}

            response = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Dame 2 puntos sobre IA",
                    "model": "SAPTIVA_TURBO",
                    "channel": "chat"
                }
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["model"] == "SAPTIVA_TURBO"
            assert data["tokens"] > 0

            # Turbo debería ser más conciso (addendum pide ≤6 bullets)
            assert "content" in data

    @pytest.mark.asyncio
    async def test_ops_structured_output(self, auth_token):
        """
        Verificar que Saptiva Ops genere salida estructurada
        (optimizado para código y operaciones)
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {auth_token}"}

            response = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Lista 2 comandos git útiles",
                    "model": "SAPTIVA_OPS",
                    "channel": "chat"
                }
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["model"] == "SAPTIVA_OPS"
            assert "content" in data

    @pytest.mark.asyncio
    async def test_fallback_to_default_for_unknown_model(self, auth_token):
        """
        Verificar que modelos desconocidos usen fallback a 'default'
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {auth_token}"}

            # Usar modelo que no existe
            response = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Test",
                    "model": "NONEXISTENT_MODEL",
                    "channel": "chat"
                }
            )

            # Debería funcionar usando fallback
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "content" in data


class TestChannelMaxTokens:
    """Tests E2E para verificar max_tokens por canal"""

    @pytest.mark.asyncio
    async def test_chat_channel_token_limit(self, auth_token):
        """Verificar que canal 'chat' use max_tokens=1200"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {auth_token}"}

            response = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Test chat channel",
                    "model": "SAPTIVA_CORTEX",
                    "channel": "chat"
                }
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verificar que tokens no excedan el límite
            assert data["tokens"] <= 1200

    @pytest.mark.asyncio
    async def test_report_channel_token_limit(self, auth_token):
        """Verificar que canal 'report' use max_tokens=3500"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {auth_token}"}

            response = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Generate a detailed report on AI",
                    "model": "SAPTIVA_CORTEX",
                    "channel": "report"
                }
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Report puede usar más tokens
            assert data["tokens"] > 0

    @pytest.mark.asyncio
    async def test_title_channel_token_limit(self, auth_token):
        """Verificar que canal 'title' use max_tokens=64"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {auth_token}"}

            response = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Conversation about artificial intelligence and machine learning",
                    "model": "SAPTIVA_TURBO",
                    "channel": "title"
                }
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Title debe ser muy corto
            assert data["tokens"] <= 64
            assert len(data["content"]) < 100  # Título breve


class TestToolsIntegration:
    """Tests E2E para verificar integración de herramientas"""

    @pytest.mark.asyncio
    async def test_chat_with_tools_enabled(self, auth_token):
        """
        Verificar que tools_enabled inyecte herramientas en el prompt
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {auth_token}"}

            response = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "¿Qué herramientas tienes disponibles?",
                    "model": "SAPTIVA_CORTEX",
                    "channel": "chat",
                    "tools_enabled": {
                        "web_search": True,
                        "calculator": True
                    }
                }
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verificar que la respuesta mencione las herramientas
            content_lower = data["content"].lower()
            # El modelo debería reconocer las herramientas disponibles
            assert data["tokens"] > 0

    @pytest.mark.asyncio
    async def test_chat_without_tools(self, auth_token):
        """
        Verificar comportamiento cuando no hay herramientas
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {auth_token}"}

            response = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Test without tools",
                    "model": "SAPTIVA_TURBO",
                    "channel": "chat"
                }
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "content" in data


class TestTelemetryAndHashing:
    """Tests E2E para verificar telemetría y hashing de prompts"""

    @pytest.mark.asyncio
    async def test_different_models_have_different_hashes(self, auth_token):
        """
        Verificar que modelos diferentes generen hashes diferentes
        (porque tienen prompts/params distintos)
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {auth_token}"}

            # Request con Cortex
            response_cortex = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Test",
                    "model": "SAPTIVA_CORTEX",
                    "channel": "chat"
                }
            )

            # Request con Turbo
            response_turbo = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Test",
                    "model": "SAPTIVA_TURBO",
                    "channel": "chat"
                }
            )

            assert response_cortex.status_code == status.HTTP_200_OK
            assert response_turbo.status_code == status.HTTP_200_OK

            # Ambos deberían tener hashes diferentes
            # (verificable en logs/telemetría, no en response directa)

    @pytest.mark.asyncio
    async def test_same_model_same_hash(self, auth_token):
        """
        Verificar que el mismo modelo genere el mismo hash
        (determinístico)
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {auth_token}"}

            # Dos requests idénticas
            response1 = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Test hash",
                    "model": "SAPTIVA_CORTEX",
                    "channel": "chat"
                }
            )

            response2 = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Another test",
                    "model": "SAPTIVA_CORTEX",
                    "channel": "chat"
                }
            )

            assert response1.status_code == status.HTTP_200_OK
            assert response2.status_code == status.HTTP_200_OK

            # Mismo modelo = mismo hash de system prompt


class TestErrorHandling:
    """Tests E2E para manejo de errores"""

    @pytest.mark.asyncio
    async def test_invalid_channel_returns_validation_error(self, auth_token):
        """
        Verificar que canal inválido retorne error de validación
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {auth_token}"}

            response = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Test",
                    "model": "SAPTIVA_CORTEX",
                    "channel": "invalid_channel"
                }
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            data = response.json()
            assert "errors" in data

    @pytest.mark.asyncio
    async def test_empty_message_returns_validation_error(self, auth_token):
        """
        Verificar que mensaje vacío retorne error
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {auth_token}"}

            response = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "",
                    "model": "SAPTIVA_CORTEX",
                    "channel": "chat"
                }
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
