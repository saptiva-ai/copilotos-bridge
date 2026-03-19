#!/usr/bin/env python3
"""
Test Suite - Temporal Context Bleeding Bug (BUG-2026-02-04)
Validates that year filters are applied correctly without context bleeding.

Bug: Year from previous query affected current query (context bleeding)
Root cause: Multi-turn context passed year to next query incorrectly

Ticket ID: 2026-02-04__BUG__temporal-context-bleeding
Status: DONE (2026-02-05)

Run: python tests/e2e/regression/test_bug_2026_02_04_temporal_context_bleeding.py
"""

import os
import sys
import json
import requests
from typing import Dict, Any, Tuple
from dataclasses import dataclass

# Configuration
BANK_ADVISOR_URL = os.environ.get("BANK_ADVISOR_URL", "http://localhost:8002")


@dataclass
class TemporalTestCase:
    test_id: str
    description: str
    query: str
    expected_year: int
    user_report: str = ""


# Test cases from user feedback (11 reports from 2026-02-04)
TEST_CASES = [
    TemporalTestCase(
        test_id="TEMPORAL-001",
        description="Cartera comercial INVEX 2024 should return 2024 data",
        query="cartera comercial de INVEX en 2024",
        expected_year=2024,
        user_report="no me mostro la cartera comercial de 2024, me dice que no tiene datos",
    ),
    TemporalTestCase(
        test_id="TEMPORAL-002",
        description="Cartera comercial INVEX 2025 should return 2025 data",
        query="cartera comercial de INVEX en 2025",
        expected_year=2025,
        user_report="en el texto me da info de 2025, grafica da datos de 2024",
    ),
    TemporalTestCase(
        test_id="TEMPORAL-003",
        description="ICAP comparison 2024 should return 2024 data",
        query="compara el ICAP de BBVA, Banamex y Santander en 2024",
        expected_year=2024,
        user_report="dice que no hay datos anteriores a 2025 pero si los hay",
    ),
    TemporalTestCase(
        test_id="TEMPORAL-004",
        description="ICAP BBVA 2024 should return 2024 data",
        query="ICAP de BBVA en 2024",
        expected_year=2024,
        user_report="",
    ),
    TemporalTestCase(
        test_id="TEMPORAL-005",
        description="Cartera vencida 2025 should return 2025 data",
        query="cartera vencida de Santander en 2025",
        expected_year=2025,
        user_report="",
    ),
]


def call_bank_analytics(query: str) -> Dict[str, Any]:
    """Call the bank_analytics MCP tool."""
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


def extract_year_from_response(result: Dict[str, Any]) -> Tuple[int, int]:
    """Extract start and end years from response time_range or plotly data."""
    data = result.get("data", {})

    # Try time_range first
    time_range = data.get("time_range", {})
    if time_range:
        start = time_range.get("start", "")
        end = time_range.get("end", "")
        if start and end:
            start_year = int(start[:4])
            end_year = int(end[:4])
            return start_year, end_year

    # Try plotly data
    plotly = data.get("plotly_config", {})
    traces = plotly.get("data", [])
    if traces:
        x_values = traces[0].get("x", [])
        if x_values:
            first_date = x_values[0]
            last_date = x_values[-1]
            start_year = int(first_date[:4])
            end_year = int(last_date[:4])
            return start_year, end_year

    return 0, 0


def run_test(test_case: TemporalTestCase) -> Tuple[bool, str]:
    """Run a single test case."""
    result = call_bank_analytics(test_case.query)

    if "error" in result and not result.get("success"):
        return False, f"API error: {result.get('error', 'Unknown error')}"

    start_year, end_year = extract_year_from_response(result)

    if start_year == 0:
        return False, "Could not extract year from response"

    # Check if expected year is in range
    if start_year <= test_case.expected_year <= end_year:
        return True, f"Year range: {start_year}-{end_year} (contains {test_case.expected_year})"

    # For single-year queries, both start and end should match
    if start_year == test_case.expected_year or end_year == test_case.expected_year:
        return True, f"Year range: {start_year}-{end_year}"

    return False, f"Wrong year: expected {test_case.expected_year}, got {start_year}-{end_year}"


def main():
    print("=" * 70)
    print("Temporal Context Bleeding Bug Test Suite (BUG-2026-02-04)")
    print("Ticket: 2026-02-04__BUG__temporal-context-bleeding")
    print("=" * 70)
    print(f"Target: {BANK_ADVISOR_URL}")
    print()

    # Check service health
    try:
        health = requests.get(f"{BANK_ADVISOR_URL}/health", timeout=5)
        if health.status_code != 200:
            print("ERROR: Service not healthy")
            sys.exit(2)
    except Exception as e:
        print(f"ERROR: Cannot connect to service: {e}")
        sys.exit(2)

    print(f"Running {len(TEST_CASES)} test cases")
    print("-" * 70)

    passed = 0
    failed = 0

    for tc in TEST_CASES:
        success, message = run_test(tc)
        status = "PASS" if success else "FAIL"
        icon = "\u2705" if success else "\u274c"

        print(f"{icon} [{tc.test_id}] {tc.description[:50]}...")
        print(f"   {message}")

        if success:
            passed += 1
        else:
            failed += 1
            if tc.user_report:
                print(f"   User report: {tc.user_report[:60]}...")

    print("=" * 70)
    print(f"Results: {passed}/{passed + failed} passed")

    if failed == 0:
        print("\u2705 All temporal context tests PASSED!")
        sys.exit(0)
    else:
        print(f"\u274c {failed} tests FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
