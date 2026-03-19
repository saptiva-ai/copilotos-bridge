from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import httpx

# Add tests/ to path for shared utils
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token


def main() -> int:
    print("=== Testing Conversation Context ===")

    base_url = os.environ.get("BASE_URL", "http://localhost:8000")
    model = os.environ.get("MODEL", "Saptiva Turbo")
    timeout = float(os.environ.get("TIMEOUT", "30"))

    # Get auth token
    token = get_auth_token(backend_url=base_url)
    if not token:
        print("❌ FAIL: Authentication failed")
        return 1

    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(timeout=timeout, headers=headers) as client:
        print("1) Creating new conversation...")
        response = client.post(
            f"{base_url}/api/conversations",
            json={},
        )
        response.raise_for_status()
        conversation_id = response.json().get("id")

        if not conversation_id:
            print("❌ FAIL: Conversation ID missing in response")
            print(response.text)
            return 1

        print(f"Conversation ID: {conversation_id}\n")

        def send_message(message: str, label: str) -> dict:
            print(label)
            message_response = client.post(
                f"{base_url}/api/chat",
                json={
                    "message": message,
                    "chat_id": conversation_id,
                    "model": model,
                    "stream": False,
                },
            )
            message_response.raise_for_status()
            return message_response.json()

        first = send_message("¿cuál es el PDM de INVEX?", "2) Sending first message...")
        first_content = first.get("content", "")
        print("First response preview:")
        print(first_content[:200])
        print("")

        second = send_message("¿cuánto es?", "3) Sending follow-up question...")
        second_content = second.get("content", "")
        print("Second response:")
        print(second_content)
        print("")

        print("=== Checking if context was maintained ===")
        if re.search(r"PDM|INVEX", second_content, re.IGNORECASE):
            print("✅ SUCCESS: Context maintained (response mentions PDM or INVEX)")
            return 0

        print("❌ FAILURE: Context lost (no PDM/INVEX reference)")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
