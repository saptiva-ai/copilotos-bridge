#!/usr/bin/env python3
"""
E2E coverage of PRD epics (HU1-HU5) from the frontend path.

Scope:
- HU1 Query multi-banco: ranking returns >=10 bancos, data_as_of present.
- HU2 Comparacion multi-banco: 3-bank comparison returns chart+data.
- HU3 Clarificacion UI: ambiguo sin banco debe pedir opciones (bank_clarification).
- HU4 RAG glosario: term queries devolviendo definicion + fuentes.
- HU5 Feedback: usuario puede calificar mensaje y leerlo de vuelta.

These tests hit the public chat API (frontend-equivalent flow) using SSE.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import requests

# Ensure project root and tests dir are on PYTHONPATH for helper imports
ROOT_DIR = Path(__file__).resolve().parents[3]
TESTS_DIR = ROOT_DIR / "tests"
sys.path.append(str(ROOT_DIR))
sys.path.append(str(TESTS_DIR))

from utils.helpers import get_auth_token

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
AUTH_USER = os.environ.get("TEST_AUTH_USER", "demo@example.com")
AUTH_PASS = os.environ.get("TEST_AUTH_PASS", "Demo1234")


def _parse_sse(response) -> Dict[str, Any]:
    """Parse SSE stream capturing chart, clarification, knowledge and meta events."""
    result: Dict[str, Any] = {
        "events": [],
        "bank_chart": None,
        "clarification": None,
        "knowledge": None,
        "meta": None,
        "content": "",
        "error": None,
    }
    current_event: Optional[str] = None

    for line in response.iter_lines():
        if not line:
            continue

        decoded = line.decode("utf-8")

        if decoded.startswith("event:"):
            current_event = decoded.split(":", 1)[1].strip()
            result["events"].append(current_event)
            continue

        if decoded.startswith("data:") and current_event:
            payload = decoded.split(":", 1)[1].strip()
            if payload == "[DONE]":
                continue

            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                parsed = payload

            if current_event == "bank_chart":
                result["bank_chart"] = parsed
            elif current_event in ("bank_clarification", "clarification"):
                result["clarification"] = parsed
            elif current_event == "knowledge":
                result["knowledge"] = parsed
            elif current_event == "meta":
                result["meta"] = parsed
            elif current_event == "chunk":
                if isinstance(parsed, dict) and "content" in parsed:
                    result["content"] += str(parsed["content"])
                else:
                    result["content"] += str(parsed)
            elif current_event == "error":
                result["error"] = parsed
            else:
                extras = result.setdefault("extra", {})
                extras[current_event] = parsed

    return result


def _send_chat(token: str, message: str, *, timeout: int = 45) -> Dict[str, Any]:
    """Send chat message via SSE and parse the response."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
    }
    payload = {
        "message": message,
        "stream": True,
        "tools_enabled": {"bank-advisor": True, "bank_analytics": True},
    }
    resp = requests.post(
        f"{BACKEND_URL}/api/chat",
        json=payload,
        headers=headers,
        stream=True,
        timeout=timeout,
    )
    assert resp.status_code == 200, f"Chat request failed: {resp.status_code} {resp.text}"
    return _parse_sse(resp)


def _count_banks(chart: Dict[str, Any]) -> int:
    """Count unique banks in chart data."""
    if not chart:
        return 0
    banks: List[str] = []
    if chart.get("bank_names"):
        banks.extend(chart["bank_names"])
    plotly_cfg = chart.get("plotly_config", {}) or {}
    for trace in plotly_cfg.get("data", []):
        name = trace.get("name")
        if name:
            banks.append(str(name))
    return len({b.upper() for b in banks})


def _has_numeric_points(chart: Dict[str, Any]) -> bool:
    """
    Accept numeric points whether the chart is vertical (y has numbers) or horizontal (x has numbers).
    """
    plotly_cfg = chart.get("plotly_config", {}) or {}
    for trace in plotly_cfg.get("data", []):
        y_vals = trace.get("y")
        x_vals = trace.get("x")
        if isinstance(y_vals, list) and any(isinstance(v, (int, float)) for v in y_vals):
            return True
        if isinstance(x_vals, list) and any(isinstance(v, (int, float)) for v in x_vals):
            return True
    return False


@pytest.fixture(scope="module")
def auth_token() -> str:
    token = get_auth_token(
        backend_url=BACKEND_URL,
        identifier=AUTH_USER,
        user_secret=AUTH_PASS,
        timeout=15,
    )
    assert token, "Authentication failed for demo user"
    return token


def test_hu1_ranking_has_ten_banks_and_data_as_of(auth_token: str):
    """Ranking IMOR should return >=10 banks with data and a data_as_of field."""
    res = _send_chat(auth_token, "Ranking IMOR 2024 top 15 bancos")
    chart = res.get("bank_chart")
    assert chart, f"Expected bank_chart event, got events={res.get('events')}"
    assert chart.get("metric_name", "").upper().startswith("IMOR")
    assert chart.get("data_as_of"), "Missing data_as_of in chart metadata"
    assert _count_banks(chart) >= 10, f"Expected at least 10 banks, got {_count_banks(chart)}"
    assert _has_numeric_points(chart), "Chart lacks numeric data points"


def test_hu2_multi_bank_comparison_has_three_traces(auth_token: str):
    """IMOR comparison INVEX vs BBVA vs Santander should return three banks with data."""
    res = _send_chat(auth_token, "IMOR de INVEX vs BBVA vs Santander en 2024")
    chart = res.get("bank_chart")
    assert chart, "Expected bank_chart for multi-bank comparison"
    banks = {b.upper() for b in chart.get("bank_names", [])}
    assert {"INVEX", "BBVA", "SANTANDER"}.issubset(banks), f"Banks returned: {banks}"
    assert _count_banks(chart) >= 3, f"Expected >=3 banks, got {_count_banks(chart)}"
    assert _has_numeric_points(chart), "No numeric data points in chart"
    assert chart.get("response_text") or chart.get("title"), "Missing summary/legend text"


def test_hu3_ambiguous_query_requests_clarification(auth_token: str):
    """Ambiguous query without banco should emit clarification options, not a chart."""
    res = _send_chat(auth_token, "IMOR 2024")
    assert res.get("clarification"), "Expected clarification options for ambiguous bank query"
    assert res.get("bank_chart") is None, "Should not emit bank_chart when bank is ambiguous"
    options = res["clarification"].get("options", [])
    assert options, "Clarification payload missing options"


def test_hu4_glossary_definition_returns_sources(auth_token: str):
    """Glossary query should return knowledge response with sources."""
    res = _send_chat(auth_token, "Que es ICAP?")
    knowledge = res.get("knowledge")
    assert knowledge, f"Expected knowledge event, got events={res.get('events')}"
    assert knowledge.get("response_text"), "Knowledge response missing text"
    assert knowledge.get("source_refs"), "Knowledge response missing source references"


def test_hu5_feedback_roundtrip(auth_token: str):
    """User can submit feedback for the last assistant message and retrieve it."""
    res = _send_chat(auth_token, "IMOR de INVEX en 2024")
    chat_id = res.get("meta", {}).get("chat_id")
    assert chat_id, "Missing chat_id in meta event"

    hist_resp = requests.get(
        f"{BACKEND_URL}/api/history/{chat_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        params={"limit": 10},
        timeout=20,
    )
    assert hist_resp.status_code == 200, f"History fetch failed: {hist_resp.status_code}"
    messages = hist_resp.json().get("messages", [])
    assistant_msg_id = None
    for msg in messages:
        if msg.get("role") == "assistant":
            assistant_msg_id = msg.get("id")
            break
    assert assistant_msg_id, "No assistant message found to rate"

    fb_payload = {
        "message_id": assistant_msg_id,
        "conversation_id": chat_id,
        "rating": "up",
        "reason": "e2e prd coverage",
    }
    fb_resp = requests.post(
        f"{BACKEND_URL}/api/feedback",
        json=fb_payload,
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=10,
    )
    assert fb_resp.status_code == 201, f"Feedback submission failed: {fb_resp.status_code}"
    fb_id = fb_resp.json().get("id")
    assert fb_id, "Feedback response missing id"

    fb_get = requests.get(
        f"{BACKEND_URL}/api/feedback/message/{assistant_msg_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=10,
    )
    assert fb_get.status_code == 200, f"Feedback retrieval failed: {fb_get.status_code}"
    fb_data = fb_get.json()
    assert fb_data, "Empty feedback retrieval payload"
    assert fb_data.get("rating") == "up", f"Unexpected rating returned: {fb_data}"
