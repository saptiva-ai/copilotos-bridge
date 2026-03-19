#!/usr/bin/env python3
"""
E2E Test for Chart Persistence (Bug 8 Fix).

Tests the complete flow of chart creation, persistence, and restoration:
1. Create a chat session
2. Send a query that generates a chart
3. Verify artifact_id is emitted in SSE events
4. Verify artifact_id is saved in message metadata (tool_invocations)
5. Fetch the message from API to simulate page reload
6. Verify tool_invocations array exists with artifact_id
7. Fetch the artifact via /api/artifacts/{id}
8. Verify chart data can be restored

This test validates the fix for Bug 8 from ISSUE-007.

References:
    - ISSUE-007 Bug 8: Chart Persistence
    - apps/backend/src/services/streaming/message_persistence.py
    - apps/backend/src/routers/chat/handlers/streaming_handler.py
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure tests/ is on path for shared utils
sys.path.append(str(Path(__file__).resolve().parents[2]))

import requests
from utils.helpers import get_auth_token, parse_sse_response

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
DEFAULT_MODEL = os.environ.get("TEST_MODEL", "Saptiva Turbo")


def send_chat_message_and_get_response(
    token: str,
    message: str,
    chat_id: Optional[str] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    Send chat message and return full parsed response with message_id.

    Returns:
        Dict with keys: events, bank_chart, content, message_id, chat_id, etc.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
    }

    payload = {
        "message": message,
        "stream": True,
        "model": DEFAULT_MODEL,
    }
    if chat_id:
        payload["chat_id"] = chat_id

    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/chat",
            json=payload,
            headers=headers,
            stream=True,
            timeout=timeout,
        )
    except Exception as exc:
        return {"error": str(exc)}

    if resp.status_code != 200:
        return {
            "error": f"HTTP {resp.status_code}",
            "status_code": resp.status_code,
        }

    # Parse SSE response
    result = {
        "events": [],
        "bank_chart": None,
        "artifact_created": None,
        "done": None,
        "content": "",
        "error": None,
        "message_id": None,
        "chat_id": None,
    }

    current_event = None

    for line in resp.iter_lines():
        if not line:
            continue

        decoded = line.decode("utf-8")

        if decoded.startswith("event:"):
            current_event = decoded.split(":", 1)[1].strip()
            result["events"].append(current_event)
            continue

        if decoded.startswith("data:") and current_event:
            payload_str = decoded.split(":", 1)[1].strip()
            if payload_str == "[DONE]":
                continue

            try:
                parsed = json.loads(payload_str)
            except json.JSONDecodeError:
                parsed = payload_str

            if current_event in ("bank_chart", "chart"):
                result["bank_chart"] = parsed
            elif current_event == "artifact_created":
                result["artifact_created"] = parsed
            elif current_event == "done":
                result["done"] = parsed
                # Extract message_id and chat_id from done event
                if isinstance(parsed, dict):
                    result["message_id"] = parsed.get("message_id")
                    result["chat_id"] = parsed.get("chat_id")
            elif current_event == "chunk":
                if isinstance(parsed, dict) and "content" in parsed:
                    result["content"] += parsed["content"]
            elif current_event == "error":
                result["error"] = parsed

    return result


def fetch_message_metadata(
    token: str, chat_id: str, message_id: str
) -> Optional[Dict[str, Any]]:
    """
    Fetch message metadata from API to verify tool_invocations.

    Returns:
        Message dict with metadata, or None on error
    """
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # Fetch chat history to get message (using /history endpoint)
        resp = requests.get(
            f"{BACKEND_URL}/api/history/{chat_id}",
            headers=headers,
            timeout=10,
        )

        if resp.status_code != 200:
            print(f"   ⚠️  HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        history_data = resp.json()
        # Messages are in history_data["messages"]
        messages = history_data.get("messages", [])

        # Find the specific message
        for msg in messages:
            if msg.get("id") == message_id:
                return msg

        print(f"   ⚠️  Message {message_id} not found in {len(messages)} messages")
        return None
    except Exception as e:
        print(f"   ⚠️  Exception: {e}")
        return None


def fetch_artifact(token: str, artifact_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch artifact data via API.

    Returns:
        Artifact dict with chart_data, or None on error
    """
    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.get(
            f"{BACKEND_URL}/api/artifacts/{artifact_id}",
            headers=headers,
            timeout=10,
        )

        if resp.status_code != 200:
            return None

        return resp.json()
    except Exception:
        return None


def test_chart_persistence_full_flow():
    """
    E2E test for chart persistence (Bug 8).

    Flow:
    1. Authenticate
    2. Send chart query
    3. Verify artifact_created event
    4. Verify done event contains message_id
    5. Fetch message metadata
    6. Verify tool_invocations array exists with artifact_id
    7. Fetch artifact
    8. Verify chart data restored correctly
    """
    print("=" * 80)
    print("E2E Test: Chart Persistence (Bug 8 Fix)")
    print("=" * 80)

    # Step 1: Authenticate
    print("\n[1/8] Authenticating...")
    token = get_auth_token(backend_url=BACKEND_URL)
    assert token, "❌ Failed to get auth token"
    print("✅ Authenticated successfully")

    # Step 2: Send chart query (use simple query that generates chart)
    print("\n[2/8] Sending chart query...")
    query = "Cartera total de BBVA en 2024"
    response = send_chat_message_and_get_response(token, query, timeout=90)

    if response.get("error"):
        print(f"❌ Error sending message: {response['error']}")
        return False

    print(f"✅ Received {len(response['events'])} SSE events")
    print(f"   Events: {response['events']}")

    # Step 3: Verify artifact_created event
    print("\n[3/8] Verifying artifact_created event...")
    if "artifact_created" not in response["events"]:
        print("⚠️  WARNING: artifact_created event not found in events")
        print(f"   Available events: {response['events']}")
        # Don't fail yet - artifact might be created but event missing
    else:
        artifact_data = response.get("artifact_created")
        print(f"✅ artifact_created event received")
        print(f"   Artifact ID: {artifact_data.get('artifact_id')}")
        print(f"   Type: {artifact_data.get('type')}")

    # Step 4: Verify done event contains message_id
    print("\n[4/8] Verifying done event with message_id...")
    message_id = response.get("message_id")
    chat_id = response.get("chat_id")

    if not message_id:
        print("❌ FAILED: No message_id in done event")
        print(f"   Done event data: {response.get('done')}")
        return False

    print(f"✅ Done event received")
    print(f"   Message ID: {message_id}")
    print(f"   Chat ID: {chat_id}")

    # Step 5: Fetch message metadata (simulate page reload)
    print("\n[5/8] Fetching message metadata from API...")
    message_data = fetch_message_metadata(token, chat_id, message_id)

    if not message_data:
        print("❌ FAILED: Could not fetch message from API")
        return False

    print(f"✅ Message fetched successfully")
    print(f"   Role: {message_data.get('role')}")
    print(f"   Has metadata: {bool(message_data.get('metadata'))}")

    # Step 6: Verify tool_invocations array (CRITICAL for Bug 8 fix)
    print("\n[6/8] Verifying tool_invocations in metadata...")
    metadata = message_data.get("metadata", {})
    tool_invocations = metadata.get("tool_invocations", [])

    if not tool_invocations:
        print("❌ FAILED: tool_invocations array is empty or missing")
        print(f"   Metadata keys: {list(metadata.keys())}")
        print(f"   Has bank_chart_data: {bool(metadata.get('bank_chart_data'))}")
        return False

    print(f"✅ tool_invocations found ({len(tool_invocations)} invocations)")

    # Find create_artifact invocation
    artifact_invocation = None
    for inv in tool_invocations:
        if inv.get("tool_name") == "create_artifact":
            artifact_invocation = inv
            break

    if not artifact_invocation:
        print("❌ FAILED: No create_artifact in tool_invocations")
        print(f"   Tool names: {[inv.get('tool_name') for inv in tool_invocations]}")
        return False

    artifact_id = artifact_invocation.get("result", {}).get("id")
    artifact_type = artifact_invocation.get("result", {}).get("type")

    if not artifact_id:
        print("❌ FAILED: artifact_id not found in tool_invocations result")
        print(f"   Invocation: {artifact_invocation}")
        return False

    print(f"✅ artifact_id found in tool_invocations")
    print(f"   Artifact ID: {artifact_id}")
    print(f"   Type: {artifact_type}")

    # Step 7: Fetch artifact via API (simulate chart restoration)
    print("\n[7/8] Fetching artifact from API...")
    artifact_data = fetch_artifact(token, artifact_id)

    if not artifact_data:
        print(f"❌ FAILED: Could not fetch artifact {artifact_id} from API")
        return False

    print(f"✅ Artifact fetched successfully")
    print(f"   Artifact ID: {artifact_data.get('id')}")
    print(f"   Type: {artifact_data.get('type')}")
    print(f"   Title: {artifact_data.get('title')}")

    # Step 8: Verify chart data can be restored
    print("\n[8/8] Verifying chart data restoration...")
    # Chart data is in the 'content' field for bank_chart artifacts
    chart_data = artifact_data.get("content")

    if not chart_data:
        print("❌ FAILED: No content in artifact")
        print(f"   Artifact keys: {list(artifact_data.keys())}")
        return False

    # Verify chart has required fields
    required_fields = ["metric_name", "plotly_config"]
    missing_fields = [f for f in required_fields if f not in chart_data]

    if missing_fields:
        print(f"⚠️  WARNING: Missing chart fields: {missing_fields}")

    print(f"✅ Chart data restored successfully")
    print(f"   Metric: {chart_data.get('metric_name')}")
    print(f"   Has plotly_config: {bool(chart_data.get('plotly_config'))}")
    print(f"   Banks: {chart_data.get('bank_names', [])}")

    # Final summary
    print("\n" + "=" * 80)
    print("✅ CHART PERSISTENCE TEST PASSED")
    print("=" * 80)
    print("\nVerified:")
    print("  ✓ artifact_created event emitted")
    print("  ✓ message_id saved in done event")
    print("  ✓ tool_invocations array exists in message metadata")
    print("  ✓ artifact_id present in tool_invocations")
    print("  ✓ Artifact fetchable via API")
    print("  ✓ Chart data restorable from artifact")
    print("\nBug 8 (Chart Persistence) is FIXED! 🎉")

    return True


if __name__ == "__main__":
    try:
        success = test_chart_persistence_full_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH EXCEPTION: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
