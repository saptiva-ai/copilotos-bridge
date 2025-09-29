#!/usr/bin/env python3
"""
Debug redirects from SAPTIVA API.
"""

import asyncio
import httpx
import os


async def debug_redirects():
    print("🔍 Debug SAPTIVA API Redirects")
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

    # Disable automatic redirects to see what's happening
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        try:
            request_data = {
                "model": "Saptiva Cortex",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }

            response = await client.post(
                f"{base_url}/v1/chat/completions",
                json=request_data,
                headers=headers
            )

            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")

            if 'location' in response.headers:
                redirect_url = response.headers['location']
                print(f"Redirect to: {redirect_url}")

                # Try following the redirect manually
                print(f"\nTrying redirect URL: {redirect_url}")
                redirect_response = await client.post(
                    redirect_url,
                    json=request_data,
                    headers=headers
                )
                print(f"Redirect response status: {redirect_response.status_code}")
                if redirect_response.status_code == 200:
                    data = redirect_response.json()
                    print(f"Success! Response: {data}")

        except Exception as e:
            print(f"Error: {e}")

    # Also try with automatic redirects
    print("\n" + "="*50)
    print("Testing with automatic redirects...")

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            request_data = {
                "model": "Saptiva Cortex",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }

            response = await client.post(
                f"{base_url}/v1/chat/completions",
                json=request_data,
                headers=headers
            )

            print(f"Final status: {response.status_code}")
            print(f"Final URL: {response.url}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success! Response: {data}")
                return True
            else:
                print(f"Response text: {response.text}")
                return False

        except Exception as e:
            print(f"Error: {e}")
            return False


if __name__ == "__main__":
    result = asyncio.run(debug_redirects())