#!/usr/bin/env python3
"""
Test con la URL correcta de SAPTIVA API.
"""

import asyncio
import httpx
import os


async def test_real_saptiva():
    print("🚀 Testing Real SAPTIVA API (api.saptiva.com)")
    print("=" * 50)

    base_url = "https://api.saptiva.com"
    api_key = os.getenv("SAPTIVA_API_KEY")

    if not api_key:
        print("❌ SAPTIVA_API_KEY environment variable not set")
        print("   Set it with: export SAPTIVA_API_KEY=your_api_key")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # Test 1: Basic connectivity
        print("\n1️⃣ Testing basic connectivity...")
        try:
            response = await client.get(base_url)
            print(f"   Base URL status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Base URL error: {e}")

        # Test 2: Chat completions endpoint
        print("\n2️⃣ Testing /v1/chat/completions endpoint...")
        try:
            request_data = {
                "model": "Saptiva Cortex",
                "messages": [{"role": "user", "content": "Hola, ¿puedes decirme brevemente qué eres?"}],
                "temperature": 0.7,
                "max_tokens": 100
            }

            response = await client.post(
                f"{base_url}/v1/chat/completions",
                json=request_data,
                headers=headers
            )
            print(f"   Chat endpoint status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Chat completion successful!")
                print(f"   Response ID: {data.get('id', 'N/A')}")
                print(f"   Model: {data.get('model', 'N/A')}")
                if data.get('choices'):
                    content = data['choices'][0]['message']['content']
                    print(f"   Content: {content[:100]}...")
                if data.get('usage'):
                    usage = data['usage']
                    print(f"   Tokens used: {usage.get('total_tokens', 0)}")
                return True
            else:
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"   ❌ Chat endpoint error: {e}")
            return False

        # Test 3: Test different models
        print("\n3️⃣ Testing different models...")
        models_to_test = ["Saptiva Cortex", "Saptiva Turbo", "Saptiva Guard"]

        for model in models_to_test:
            try:
                request_data = {
                    "model": model,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10
                }

                response = await client.post(
                    f"{base_url}/v1/chat/completions",
                    json=request_data,
                    headers=headers
                )

                if response.status_code == 200:
                    print(f"   ✅ {model}: Working")
                else:
                    print(f"   ❌ {model}: {response.status_code}")

            except Exception as e:
                print(f"   ❌ {model}: {e}")


if __name__ == "__main__":
    result = asyncio.run(test_real_saptiva())
    if result:
        print("\n🎉 ¡SAPTIVA API funcionando correctamente!")
    else:
        print("\n⚠️ Verificar credenciales o configuración.")