#!/usr/bin/env python3
"""
Test module para verificar la integración con SAPTIVA API.
"""

import asyncio
import os
import sys
import time


def _ensure_saptiva_env() -> bool:
    """Ensure required environment variables are configured before running tests."""
    os.environ.setdefault("SAPTIVA_BASE_URL", "https://api.saptiva.ai")
    os.environ.setdefault("SAPTIVA_TIMEOUT", "30")
    os.environ.setdefault("SAPTIVA_MAX_RETRIES", "3")

    if not os.getenv("SAPTIVA_API_KEY"):
        print("❌ SAPTIVA_API_KEY environment variable not set")
        print("   Please set your API key: export SAPTIVA_API_KEY=your-api-key-here")
        return False
    return True

from services.saptiva_client import SaptivaClient, get_saptiva_client


async def test_saptiva_client():
    """Test básico del cliente SAPTIVA"""

    try:
        print("🧪 Iniciando test de integración SAPTIVA...")

        # Crear cliente
        client = SaptivaClient()

        # Test 1: Health check
        print("\n1️⃣ Testing health check...")
        is_healthy = await client.health_check()
        print(f"   Health check: {'✅ PASSED' if is_healthy else '❌ FAILED'}")

        # Test 2: Obtener modelos disponibles
        print("\n2️⃣ Testing available models...")
        models = await client.get_available_models()
        print(f"   Available models: {models}")

        # Test 3: Chat completion simple
        print("\n3️⃣ Testing simple chat completion...")
        messages = [
            {"role": "user", "content": "Hola, ¿puedes decirme brevemente qué eres?"}
        ]

        start_time = time.time()
        response = await client.chat_completion(
            messages=messages,
            model="SAPTIVA_CORTEX",
            temperature=0.7,
            max_tokens=100
        )
        duration = time.time() - start_time

        print(f"   Response time: {duration:.2f}s")
        print(f"   Response ID: {response.id}")
        print(f"   Model: {response.model}")
        print(f"   Content: {response.choices[0]['message']['content'][:100]}...")

        if response.usage:
            print(f"   Tokens used: {response.usage}")

        # Test 4: Chat con contexto
        print("\n4️⃣ Testing chat with context...")
        conversation = [
            {"role": "user", "content": "Mi nombre es Carlos"},
            {"role": "assistant", "content": "Hola Carlos, encantado de conocerte."},
            {"role": "user", "content": "¿Cuál es mi nombre?"}
        ]

        context_response = await client.chat_completion(
            messages=conversation,
            model="SAPTIVA_CORTEX",
            temperature=0.3,
            max_tokens=50
        )

        print(f"   Context response: {context_response.choices[0]['message']['content']}")

        # Test 5: Diferentes modelos
        print("\n5️⃣ Testing different models...")
        for model in ["SAPTIVA_CORTEX", "SAPTIVA_OPS"]:
            try:
                model_response = await client.chat_completion(
                    messages=[{"role": "user", "content": "Responde en máximo 10 palabras: ¿Qué modelo eres?"}],
                    model=model,
                    max_tokens=30
                )
                print(f"   {model}: {model_response.choices[0]['message']['content']}")
            except Exception as e:
                print(f"   {model}: ❌ Error - {e}")

        # Test 6: Streaming (básico)
        print("\n6️⃣ Testing streaming...")
        try:
            print("   Streaming response: ", end="", flush=True)
            async for chunk in client.chat_completion_stream(
                messages=[{"role": "user", "content": "Cuenta del 1 al 5 separado por comas"}],
                model="SAPTIVA_CORTEX",
                max_tokens=50
            ):
                if chunk.choices and chunk.choices[0].get("delta", {}).get("content"):
                    content = chunk.choices[0]["delta"]["content"]
                    print(content, end="", flush=True)
            print("\n   ✅ Streaming completed")
        except Exception as e:
            print(f"\n   ❌ Streaming failed: {e}")

        await client.client.aclose()

        print("\n🎉 Tests completados exitosamente!")
        return True

    except Exception as e:
        print(f"\n❌ Error durante los tests: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_integration_endpoint():
    """Test del endpoint completo simulando request HTTP"""

    print("\n" + "="*50)
    print("🌐 Testing integrated chat endpoint")
    print("="*50)

    try:
        # Test mensaje simple
        client = await get_saptiva_client()

        # Simular histórico de conversación
        message_history = [
            {"role": "user", "content": "Hola, soy un desarrollador trabajando en un proyecto de IA"}
        ]

        # Llamar al cliente como lo haría el endpoint
        saptiva_response = await client.chat_completion(
            messages=message_history,
            model="SAPTIVA_CORTEX",
            temperature=0.7,
            max_tokens=150
        )

        # Extraer información como en el endpoint
        ai_response_content = saptiva_response.choices[0]["message"]["content"]
        usage_info = saptiva_response.usage or {}
        tokens_used = usage_info.get("total_tokens", 0)
        finish_reason = saptiva_response.choices[0].get("finish_reason", "stop")

        print(f"✅ Endpoint simulation successful!")
        print(f"📄 Response: {ai_response_content[:200]}...")
        print(f"🎯 Tokens used: {tokens_used}")
        print(f"🏁 Finish reason: {finish_reason}")
        print(f"🆔 Response ID: {saptiva_response.id}")

        await client.client.aclose()
        return True

    except Exception as e:
        print(f"❌ Endpoint simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Función principal"""
    print("🚀 SAPTIVA Integration Test Suite")
    print("=" * 50)

    if not _ensure_saptiva_env():
        return False

    # Test cliente básico
    client_success = await test_saptiva_client()

    # Test integración endpoint
    endpoint_success = await test_integration_endpoint()

    print("\n" + "="*50)
    print("📊 RESUMEN DE TESTS")
    print("="*50)
    print(f"Cliente SAPTIVA: {'✅ PASSED' if client_success else '❌ FAILED'}")
    print(f"Integración Endpoint: {'✅ PASSED' if endpoint_success else '❌ FAILED'}")

    if client_success and endpoint_success:
        print("\n🎉 ¡Todos los tests pasaron! La integración SAPTIVA está funcionando correctamente.")
        print("🚀 El chat ahora usa modelos reales de SAPTIVA en lugar de mocks.")
    else:
        print("\n⚠️ Algunos tests fallaron. Revisar configuración y conectividad.")

    return client_success and endpoint_success


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Pruebas canceladas por el usuario.")
        result = False
    sys.exit(0 if result else 1)
