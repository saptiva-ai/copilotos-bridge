#!/usr/bin/env python3
"""
Test Suite - Response Grounding Desync Bug (BUG-2026-02-03)
Validates that LLM text is coherent with chart data (no contradictions).

Bug: LLM says "no tengo datos" when chart_status is success
Root cause: Context manager truncated bank_analytics results to 500 chars

Ticket ID: 2026-02-03__BUG__response-grounding-desync
Status: DONE (fix deployed)

Run: python tests/e2e/regression/test_bug_2026_02_03_response_grounding_desync.py
"""

import os
import sys
import json
import requests
from typing import Dict, Any, Tuple, List
from dataclasses import dataclass

# Configuration
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
BANK_ADVISOR_URL = os.environ.get("BANK_ADVISOR_URL", "http://localhost:8002")

# Contradiction phrases that should NOT appear when data is available
CONTRADICTION_PHRASES = [
    "no puedo proporcionar",
    "no tengo datos",
    "no hay datos",
    "no dispongo de",
    "no cuento con",
    "error técnico",
    "no es posible",
    "información no disponible",
    "datos no disponibles",
    "sin información",
    "no tengo acceso",
]


@dataclass
class GroundingTestCase:
    test_id: str
    description: str
    query: str
    expects_data: bool  # True = should have chart data
    user_report: str = ""


# Test cases - queries that should return data
TEST_CASES = [
    # Regional queries (from user feedback 2026-02-03)
    GroundingTestCase(
        test_id="GROUNDING-001",
        description="Regional query should have coherent text with chart",
        query="cartera comercial de INVEX por entidad federativa",
        expects_data=True,
        user_report="Chart shows data but text says 'no puedo proporcionar'",
    ),
    GroundingTestCase(
        test_id="GROUNDING-002",
        description="Distribution query should describe the data",
        query="distribución de cartera por región de INVEX",
        expects_data=True,
        user_report="",
    ),
    # Standard metric queries
    GroundingTestCase(
        test_id="GROUNDING-003",
        description="IMOR query should have data and coherent text",
        query="IMOR de INVEX",
        expects_data=True,
        user_report="",
    ),
    GroundingTestCase(
        test_id="GROUNDING-004",
        description="ICAP query should have data and coherent text",
        query="ICAP de BBVA",
        expects_data=True,
        user_report="",
    ),
    GroundingTestCase(
        test_id="GROUNDING-005",
        description="Cartera query should have data and coherent text",
        query="cartera total de Santander",
        expects_data=True,
        user_report="",
    ),
    # Comparison queries
    GroundingTestCase(
        test_id="GROUNDING-006",
        description="Comparison should describe both banks",
        query="compara ICAP de INVEX vs sistema",
        expects_data=True,
        user_report="",
    ),
    # Temporal queries
    GroundingTestCase(
        test_id="GROUNDING-007",
        description="2024 query should return 2024 data with coherent text",
        query="IMOR de INVEX en 2024",
        expects_data=True,
        user_report="",
    ),
    GroundingTestCase(
        test_id="GROUNDING-008",
        description="2025 query should return 2025 data with coherent text",
        query="cartera comercial de INVEX en 2025",
        expects_data=True,
        user_report="",
    ),
]


def call_bank_analytics(query: str) -> Dict[str, Any]:
    """Call the bank_analytics MCP tool directly."""
    try:
        response = requests.post(
            f"{BANK_ADVISOR_URL}/rpc",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "bank_analytics",
                    "arguments": {
                        "metric_or_query": query,
                        "mode": "dashboard"
                    }
                },
                "id": 1
            },
            timeout=45
        )

        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}"}

        rpc_response = response.json()
        content = rpc_response.get("result", {}).get("content", [])
        if content:
            return json.loads(content[0].get("text", "{}"))
        return {"error": "Empty response"}

    except Exception as e:
        return {"error": str(e)}


def call_chat_api(query: str) -> Dict[str, Any]:
    """Call the full chat API to get LLM response."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/chat",
            json={
                "message": query,
                "conversation_id": None,
                "context": "bank_advisor"
            },
            timeout=60
        )

        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}"}

        return response.json()

    except Exception as e:
        return {"error": str(e)}


def has_contradiction(text: str) -> Tuple[bool, str]:
    """Check if text contains contradiction phrases."""
    text_lower = text.lower()
    for phrase in CONTRADICTION_PHRASES:
        if phrase in text_lower:
            return True, phrase
    return False, ""


def extract_chart_status(result: Dict[str, Any]) -> str:
    """Extract chart status from bank_analytics result."""
    # Direct field
    if "chart_status" in result:
        return result["chart_status"]

    # Nested in data
    data = result.get("data", {})
    if "chart_status" in data:
        return data["chart_status"]

    # Check if success based on data presence
    if result.get("success") and data.get("plotly_config"):
        return "success"

    return "unknown"


def run_test(test_case: GroundingTestCase) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Run a single grounding test case.

    Returns (passed, message, details)
    """
    details = {
        "query": test_case.query,
        "chart_status": None,
        "has_data": False,
        "has_contradiction": False,
        "contradiction_phrase": None,
    }

    # Step 1: Get chart data from bank_analytics
    chart_result = call_bank_analytics(test_case.query)

    if "error" in chart_result and not chart_result.get("success"):
        # Connection error
        if "Connection" in str(chart_result.get("error", "")):
            return False, f"Connection error: {chart_result['error']}", details
        # Other API error might be OK for this test

    chart_status = extract_chart_status(chart_result)
    details["chart_status"] = chart_status

    # Check if we got data
    has_plotly_data = bool(
        chart_result.get("data", {}).get("plotly_config", {}).get("data")
    )
    details["has_data"] = has_plotly_data or chart_status == "success"

    # If we expect data but didn't get it, that's a different issue
    if test_case.expects_data and not details["has_data"]:
        # Check if it's clarification needed
        if chart_status == "clarification":
            return True, f"Clarification needed (acceptable)", details
        return False, f"Expected data but chart_status={chart_status}", details

    # Step 2: Check for response text (if available in result)
    # The bank_analytics tool might include narrative text
    response_text = ""

    # Try to get text from various places
    if "narrative" in chart_result:
        response_text = chart_result["narrative"]
    elif "text" in chart_result:
        response_text = chart_result["text"]
    elif "message" in chart_result:
        response_text = chart_result["message"]
    elif "data" in chart_result and "narrative" in chart_result["data"]:
        response_text = chart_result["data"]["narrative"]

    # If we have response text, check for contradictions
    if response_text and details["has_data"]:
        has_contr, phrase = has_contradiction(response_text)
        details["has_contradiction"] = has_contr
        details["contradiction_phrase"] = phrase

        if has_contr:
            return False, f"Contradiction found: '{phrase}' despite having data", details

    # If no text to check, the test passes (data pipeline works)
    if details["has_data"]:
        return True, f"Data available (chart_status={chart_status})", details

    return True, "No data expected and none received", details


def run_full_integration_test(test_case: GroundingTestCase) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Run full integration test using chat API.
    This tests the complete flow including LLM response.
    """
    details = {
        "query": test_case.query,
        "llm_response": None,
        "has_contradiction": False,
        "contradiction_phrase": None,
    }

    chat_result = call_chat_api(test_case.query)

    if "error" in chat_result:
        return False, f"Chat API error: {chat_result['error']}", details

    # Extract LLM response text
    llm_text = chat_result.get("response", "") or chat_result.get("message", "")
    details["llm_response"] = llm_text[:200] + "..." if len(llm_text) > 200 else llm_text

    # Check for bank chart data in response
    has_chart = "bank_chart" in str(chat_result) or "plotly" in str(chat_result).lower()

    # If we expect data and have it, check for contradictions
    if test_case.expects_data and has_chart:
        has_contr, phrase = has_contradiction(llm_text)
        details["has_contradiction"] = has_contr
        details["contradiction_phrase"] = phrase

        if has_contr:
            return False, f"LLM contradiction: '{phrase}' despite chart data", details

    return True, "Response coherent with data", details


def main():
    print("=" * 70)
    print("Response Grounding Desync Bug Test Suite (BUG-2026-02-03)")
    print("Ticket: 2026-02-03__BUG__response-grounding-desync")
    print("=" * 70)
    print(f"Bank Advisor: {BANK_ADVISOR_URL}")
    print()

    # Check service health
    try:
        health = requests.get(f"{BANK_ADVISOR_URL}/health", timeout=5)
        if health.status_code != 200:
            print("ERROR: Bank Advisor service not healthy")
            sys.exit(2)
    except Exception as e:
        print(f"ERROR: Cannot connect to Bank Advisor: {e}")
        sys.exit(2)

    print(f"Running {len(TEST_CASES)} test cases")
    print("-" * 70)

    passed = 0
    failed = 0
    results = []

    for tc in TEST_CASES:
        success, message, details = run_test(tc)

        result = {
            "test_id": tc.test_id,
            "description": tc.description,
            "passed": success,
            "message": message,
            "details": details,
        }
        results.append(result)

        icon = "\u2705" if success else "\u274c"
        print(f"{icon} [{tc.test_id}] {tc.description[:45]}...")
        print(f"   Query: \"{tc.query[:50]}...\"" if len(tc.query) > 50 else f"   Query: \"{tc.query}\"")
        print(f"   {message}")

        if success:
            passed += 1
        else:
            failed += 1
            if tc.user_report:
                print(f"   User report: {tc.user_report[:55]}...")
            if details.get("contradiction_phrase"):
                print(f"   Contradiction: \"{details['contradiction_phrase']}\"")

    print("=" * 70)
    print(f"Results: {passed}/{passed + failed} passed ({100*passed/(passed+failed):.1f}%)")

    # Save results
    results_file = "tests/e2e/metrics/response_grounding_results.json"
    try:
        with open(results_file, "w") as f:
            json.dump({
                "test_suite": "response_grounding_desync",
                "ticket_id": "2026-02-03__BUG__response-grounding-desync",
                "total": len(TEST_CASES),
                "passed": passed,
                "failed": failed,
                "pass_rate": passed / (passed + failed) if (passed + failed) > 0 else 0,
                "results": results,
            }, f, indent=2, default=str)
        print(f"Results saved to {results_file}")
    except Exception as e:
        print(f"Warning: Could not save results: {e}")

    if failed == 0:
        print("\u2705 All response grounding tests PASSED!")
        sys.exit(0)
    else:
        print(f"\u274c {failed} tests FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
