#!/usr/bin/env python3
"""
Test authentication and chat functionality
Usage: python3 scripts/test-auth-and-chat.py [--api-url URL] [--username USER] [--password PASS]
"""

import argparse
import sys
import requests
from typing import Dict, Any, Optional


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def print_colored(color: str, message: str):
    print(f"{color}{message}{Colors.NC}")


def test_auth(api_url: str, username: str, password: str, email: str) -> Optional[str]:
    """Test authentication and return access token"""
    print_colored(Colors.YELLOW, "\n🔐 Testing authentication...")
    print_colored(Colors.BLUE, "=" * 70)

    # Try login first
    try:
        response = requests.post(
            f"{api_url}/api/auth/login",
            json={"identifier": username, "password": password},
            timeout=10
        )

        if response.status_code == 200:
            token = response.json().get("access_token")
            print_colored(Colors.GREEN, f"✓ Login successful")
            print_colored(Colors.CYAN, f"  Token: {token[:50]}...")
            return token
    except Exception as e:
        print_colored(Colors.YELLOW, f"⚠ Login failed: {str(e)}")

    # Try registration
    print_colored(Colors.YELLOW, "⚠ Attempting registration...")
    try:
        response = requests.post(
            f"{api_url}/api/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "name": f"{username.title()} User"
            },
            timeout=10
        )

        if response.status_code in [200, 201]:
            token = response.json().get("access_token")
            print_colored(Colors.GREEN, f"✓ Registration successful")
            print_colored(Colors.CYAN, f"  Token: {token[:50]}...")
            return token
        else:
            print_colored(Colors.RED, f"✗ Registration failed: {response.status_code}")
            print_colored(Colors.RED, f"  Response: {response.text[:300]}")
            return None
    except Exception as e:
        print_colored(Colors.RED, f"✗ Registration error: {str(e)}")
        return None


def test_chat(api_url: str, token: str, model: str = "Saptiva Turbo") -> bool:
    """Test chat functionality"""
    print_colored(Colors.YELLOW, f"\n💬 Testing chat with {model}...")
    print_colored(Colors.BLUE, "=" * 70)

    messages = [
        "Hola, ¿estás funcionando?",
        "Di brevemente: Funciona correctamente",
        "Responde con: OK"
    ]

    for i, message in enumerate(messages, 1):
        print_colored(Colors.CYAN, f"\n📤 Message {i}: {message}")

        try:
            response = requests.post(
                f"{api_url}/api/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "message": message,
                    "model": model,
                    "stream": False
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                content = data.get("content", "N/A")
                used_model = data.get("model", "N/A")
                chat_id = data.get("chat_id", "N/A")

                print_colored(Colors.GREEN, f"✓ Chat successful")
                print_colored(Colors.GREEN, f"  💬 Response: \"{content[:200]}\"")
                print_colored(Colors.CYAN, f"  🤖 Model: {used_model}")
                print_colored(Colors.CYAN, f"  📝 Chat ID: {chat_id[:50]}...")

                # Only test first message to avoid rate limits
                if i == 1:
                    print_colored(Colors.YELLOW, "\n✓ Skipping remaining messages (chat working)")
                    return True
            else:
                print_colored(Colors.RED, f"✗ Chat failed: {response.status_code}")
                print_colored(Colors.RED, f"  Response: {response.text[:500]}")
                return False

        except Exception as e:
            print_colored(Colors.RED, f"✗ Chat error: {str(e)}")
            return False

    return True


def test_models_endpoint(api_url: str) -> bool:
    """Test models endpoint"""
    print_colored(Colors.YELLOW, "\n🎯 Testing models endpoint...")
    print_colored(Colors.BLUE, "=" * 70)

    try:
        response = requests.get(f"{api_url}/api/models", timeout=10)

        if response.status_code == 200:
            data = response.json()
            default_model = data.get("default_model", "N/A")
            allowed_models = data.get("allowed_models", [])

            print_colored(Colors.GREEN, "✓ Models endpoint working")
            print_colored(Colors.CYAN, f"  Default model: {default_model}")
            print_colored(Colors.CYAN, f"  Available models: {', '.join(allowed_models)}")
            return True
        else:
            print_colored(Colors.RED, f"✗ Models endpoint failed: {response.status_code}")
            return False

    except Exception as e:
        print_colored(Colors.RED, f"✗ Models endpoint error: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test authentication and chat functionality"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8001",
        help="API base URL (default: http://localhost:8001)"
    )
    parser.add_argument(
        "--username",
        default="testuser",
        help="Username for authentication (default: testuser)"
    )
    parser.add_argument(
        "--password",
        default="TestPass123!",
        help="Password for authentication (default: TestPass123!)"
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Email for registration (default: {username}@example.com)"
    )
    parser.add_argument(
        "--model",
        default="Saptiva Turbo",
        help="Model to test (default: Saptiva Turbo)"
    )

    args = parser.parse_args()

    if args.email is None:
        args.email = f"{args.username}@example.com"

    print_colored(Colors.BLUE, "\n" + "=" * 70)
    print_colored(Colors.BLUE, "  Copilotos Bridge - Authentication & Chat Test")
    print_colored(Colors.BLUE, "=" * 70)
    print_colored(Colors.CYAN, f"  API URL: {args.api_url}")
    print_colored(Colors.CYAN, f"  Username: {args.username}")
    print_colored(Colors.CYAN, f"  Model: {args.model}")

    # Test 1: Models endpoint
    if not test_models_endpoint(args.api_url):
        print_colored(Colors.RED, "\n✗ Models endpoint test failed")
        sys.exit(1)

    # Test 2: Authentication
    token = test_auth(args.api_url, args.username, args.password, args.email)
    if not token:
        print_colored(Colors.RED, "\n✗ Authentication test failed")
        sys.exit(1)

    # Test 3: Chat
    if not test_chat(args.api_url, token, args.model):
        print_colored(Colors.RED, "\n✗ Chat test failed")
        sys.exit(1)

    # All tests passed
    print_colored(Colors.BLUE, "\n" + "=" * 70)
    print_colored(Colors.GREEN, "✅ ALL TESTS PASSED - System working correctly!")
    print_colored(Colors.BLUE, "=" * 70 + "\n")
    sys.exit(0)


if __name__ == "__main__":
    main()