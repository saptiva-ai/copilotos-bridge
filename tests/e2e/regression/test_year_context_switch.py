#!/usr/bin/env python3
"""
E2E Regression Test: Year Context Switch (BUG-2026-02-09)

Problem: In multi-turn conversations, when a user changes the year
         (e.g., "cartera INVEX en 2024" → "ahora en 2025"), the chart
         shows OLD year's data because ContextEnricherService injected
         the stale period from memory_context before the user's query.

Fix: _has_explicit_time_reference() detects user-provided time refs
     and skips stale period injection.

Evidence: 9 instances in 7 days from production feedback.

Run: python tests/e2e/regression/test_year_context_switch.py
"""

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import requests

BANK_ADVISOR_URL = os.environ.get("BANK_ADVISOR_URL", "http://localhost:8002")


@dataclass
class YearSwitchCase:
    test_id: str
    description: str
    turn1_query: str
    turn1_expected_year: int
    turn2_query: str
    turn2_expected_year: int
    turn2_forbidden_year: int


TEST_CASES = [
    YearSwitchCase(
        test_id="YSWITCH-001",
        description="Switch from 2024 → 2025 for cartera comercial INVEX",
        turn1_query="cartera comercial de INVEX en 2024",
        turn1_expected_year=2024,
        turn2_query="ahora en 2025",
        turn2_expected_year=2025,
        turn2_forbidden_year=2024,
    ),
    YearSwitchCase(
        test_id="YSWITCH-002",
        description="Switch from 2025 → 2024 for IMOR BBVA",
        turn1_query="IMOR de BBVA en 2025",
        turn1_expected_year=2025,
        turn2_query="muéstrame en 2024",
        turn2_expected_year=2024,
        turn2_forbidden_year=2025,
    ),
    YearSwitchCase(
        test_id="YSWITCH-003",
        description="Explicit year in follow-up with different metric",
        turn1_query="cartera vencida de Santander en 2024",
        turn1_expected_year=2024,
        turn2_query="ICAP en 2025",
        turn2_expected_year=2025,
        turn2_forbidden_year=2024,
    ),
]


def call_bank_analytics(
    query: str,
    session_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Call the bank_analytics MCP tool, optionally with session context."""
    arguments: Dict[str, Any] = {
        "metric_or_query": query,
        "mode": "dashboard",
    }
    if session_context:
        arguments["session_context"] = session_context

    try:
        response = requests.post(
            f"{BANK_ADVISOR_URL}/rpc",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "bank_analytics", "arguments": arguments},
                "id": 1,
            },
            timeout=60,
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


def extract_year_from_response(result: Dict[str, Any]) -> Tuple[int, int]:
    """Extract start and end years from response."""
    data = result.get("data", {})

    time_range = data.get("time_range", {})
    if time_range:
        start = time_range.get("start", "")
        end = time_range.get("end", "")
        if start and end:
            return int(start[:4]), int(end[:4])

    plotly = data.get("plotly_config", {})
    traces = plotly.get("data", [])
    if traces:
        x_values = traces[0].get("x", [])
        if x_values:
            return int(x_values[0][:4]), int(x_values[-1][:4])

    return 0, 0


def build_session_context(
    turn1_query: str,
    turn1_result: Dict[str, Any],
    expected_year: int,
) -> Dict[str, Any]:
    """Build a session_context dict simulating turn 1 results for turn 2."""
    data = turn1_result.get("data", {})
    metric = data.get("metric_key", "CARTERA_COMERCIAL")
    banks = data.get("banks", ["INVEX"])

    return {
        "recent_messages": [
            {"role": "user", "content": turn1_query},
            {
                "role": "assistant",
                "content": f"Resultado de {metric}...",
                "metadata": {
                    "bank_clarification_data": {
                        "context": {
                            "metric": metric,
                            "banks": banks,
                            "period": f"year_{expected_year}",
                        }
                    }
                },
            },
        ],
        "memory_context": {
            "metric": metric,
            "banks": banks,
            "period": f"year_{expected_year}",
        },
    }


def run_case(tc: YearSwitchCase) -> Tuple[bool, str]:
    """Run a two-turn year-switch test case."""
    # Turn 1
    r1 = call_bank_analytics(tc.turn1_query)
    if "error" in r1 and not r1.get("success"):
        return False, f"Turn 1 API error: {r1.get('error')}"

    sy1, ey1 = extract_year_from_response(r1)
    if sy1 == 0:
        return False, "Turn 1: could not extract year"
    if not (sy1 <= tc.turn1_expected_year <= ey1):
        return False, f"Turn 1: expected {tc.turn1_expected_year}, got {sy1}-{ey1}"

    # Build context from turn 1 for turn 2
    ctx = build_session_context(tc.turn1_query, r1, tc.turn1_expected_year)

    # Turn 2 (with session context carrying old period)
    r2 = call_bank_analytics(tc.turn2_query, session_context=ctx)
    if "error" in r2 and not r2.get("success"):
        return False, f"Turn 2 API error: {r2.get('error')}"

    sy2, ey2 = extract_year_from_response(r2)
    if sy2 == 0:
        return False, "Turn 2: could not extract year"

    if not (sy2 <= tc.turn2_expected_year <= ey2):
        return False, (
            f"Turn 2: expected {tc.turn2_expected_year}, got {sy2}-{ey2} "
            f"(forbidden year was {tc.turn2_forbidden_year})"
        )

    if sy2 <= tc.turn2_forbidden_year <= ey2 and tc.turn2_forbidden_year != tc.turn2_expected_year:
        return False, (
            f"Turn 2: stale year {tc.turn2_forbidden_year} still present "
            f"in range {sy2}-{ey2}"
        )

    return True, f"Turn 1: {sy1}-{ey1}, Turn 2: {sy2}-{ey2}"


def main() -> None:
    print("=" * 70)
    print("Year Context Switch Regression (BUG-2026-02-09)")
    print("=" * 70)
    print(f"Target: {BANK_ADVISOR_URL}")
    print()

    # Health check
    try:
        h = requests.get(f"{BANK_ADVISOR_URL}/health", timeout=5)
        if h.status_code != 200:
            print("ERROR: Service not healthy")
            sys.exit(2)
    except Exception as e:
        print(f"ERROR: Cannot connect to service: {e}")
        sys.exit(2)

    print(f"Running {len(TEST_CASES)} two-turn test cases")
    print("-" * 70)

    passed = 0
    failed = 0

    for tc in TEST_CASES:
        ok, msg = run_case(tc)
        icon = "\u2705" if ok else "\u274c"
        print(f"{icon} [{tc.test_id}] {tc.description}")
        print(f"   {msg}")
        if ok:
            passed += 1
        else:
            failed += 1

    print("=" * 70)
    print(f"Results: {passed}/{passed + failed} passed")

    if failed == 0:
        print("\u2705 All year-context-switch tests PASSED!")
        sys.exit(0)
    else:
        print(f"\u274c {failed} tests FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
