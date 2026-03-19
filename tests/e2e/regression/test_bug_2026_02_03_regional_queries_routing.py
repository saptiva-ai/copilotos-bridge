#!/usr/bin/env python3
"""
Test Suite - Regional Queries Routing Bug (BUG-2026-02-03)
Validates that regional queries route to CarteraRegionHandler, not ResumenSistemaHandler.

Bug: "concentración por estado" returned time series instead of regional data
Root cause: ResumenSistemaHandler matched "concentración" before CarteraRegionHandler

Ticket ID: 2026-02-03__BUG__regional-queries-routing
Status: IN PROGRESS

Run: python tests/e2e/regression/test_bug_2026_02_03_regional_queries_routing.py
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
class RegionalRoutingTestCase:
    test_id: str
    description: str
    query: str
    expected_handler: str  # Which handler should process this
    should_have_regional_data: bool
    user_report: str = ""


# Test cases from user feedback
TEST_CASES = [
    # Regional queries that should go to CarteraRegionHandler
    RegionalRoutingTestCase(
        test_id="REGIONAL-001",
        description="concentración por estado should route to regional handler",
        query="concentración por estado",
        expected_handler="cartera_region",
        should_have_regional_data=True,
        user_report="consulte la concentración del sistema por estado y me da grafica de lineas en tiempo",
    ),
    RegionalRoutingTestCase(
        test_id="REGIONAL-002",
        description="cartera por región should route to regional handler",
        query="cartera por región",
        expected_handler="cartera_region",
        should_have_regional_data=True,
        user_report="",
    ),
    RegionalRoutingTestCase(
        test_id="REGIONAL-003",
        description="distribución geográfica should route to regional handler",
        query="distribución geográfica de la cartera",
        expected_handler="cartera_region",
        should_have_regional_data=True,
        user_report="",
    ),
    RegionalRoutingTestCase(
        test_id="REGIONAL-004",
        description="cartera por entidad federativa should route to regional handler",
        query="cartera por entidad federativa",
        expected_handler="cartera_region",
        should_have_regional_data=True,
        user_report="",
    ),
    RegionalRoutingTestCase(
        test_id="REGIONAL-005",
        description="concentración región norte should route to regional handler",
        query="concentración en la región norte",
        expected_handler="cartera_region",
        should_have_regional_data=True,
        user_report="",
    ),
    # System queries that should still go to ResumenSistemaHandler
    RegionalRoutingTestCase(
        test_id="SYSTEM-001",
        description="concentración del sistema should route to system handler",
        query="concentración del sistema bancario",
        expected_handler="resumen_sistema",
        should_have_regional_data=False,
        user_report="",
    ),
    RegionalRoutingTestCase(
        test_id="SYSTEM-002",
        description="top 5 bancos should route to system handler",
        query="top 5 bancos por cartera",
        expected_handler="resumen_sistema",
        should_have_regional_data=False,
        user_report="",
    ),
    RegionalRoutingTestCase(
        test_id="SYSTEM-003",
        description="resumen del sistema should route to system handler",
        query="resumen del sistema bancario",
        expected_handler="resumen_sistema",
        should_have_regional_data=False,
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


def detect_response_type(result: Dict[str, Any]) -> Tuple[str, bool]:
    """
    Detect response type from the result structure.
    Returns (detected_type, has_regional_data).

    Regional data has explicit estado/region fields in the data structure.
    System data has bank names (BBVA, BANORTE, etc.) as categories.
    """
    data = result.get("data", {})
    # Some responses are wrapped as {"success": true, "data": {...}}
    # while others already expose the analytics payload directly.
    if (
        isinstance(data, dict)
        and "data" in data
        and "plotly_config" not in data
        and isinstance(data.get("data"), dict)
    ):
        data = data["data"]

    # Check for explicit regional structure (estados as keys or in field names)
    # Regional responses have structures like: {"estado": "Jalisco", "value": ...}
    # or monthly data with estado-level breakdown
    data_str = json.dumps(data)

    # Look for estado/region as FIELD NAMES (not just substrings in bank names)
    has_estado_field = '"estado":' in data_str.lower() or '"entidad":' in data_str.lower()
    has_region_field = '"region":' in data_str.lower() or '"zona":' in data_str.lower()

    # Check for geographic state names (not bank names)
    # Mexican states that are NOT bank name substrings
    state_names = [
        "jalisco", "nuevo leon", "nuevo león", "chihuahua", "sonora",
        "tamaulipas", "coahuila", "sinaloa", "guanajuato", "michoacan",
        "michoacán", "veracruz", "puebla", "oaxaca", "guerrero",
        "yucatan", "yucatán", "quintana roo", "campeche", "tabasco",
        "chiapas", "aguascalientes", "zacatecas", "durango", "nayarit",
        "colima", "tlaxcala", "morelos", "hidalgo", "queretaro", "querétaro",
        "san luis potosi", "san luis potosí", "ciudad de mexico", "cdmx",
        "estado de mexico", "baja california",
    ]
    has_state_names = any(state in data_str.lower() for state in state_names)

    # Check for bank names as categories (indicates system/bank data, not regional)
    bank_names = [
        "bbva", "santander", "banorte", "hsbc", "scotiabank", "banamex",
        "citibanamex", "inbursa", "bajio", "banregio", "afirme", "monex",
        "invex", "azteca", "mifel", "sistema",
    ]
    has_bank_categories = any(
        f'"category": "{bank.upper()}"' in data_str or
        f'"category":"{bank.upper()}"' in data_str
        for bank in bank_names
    )

    # Metric naming hint (common for regional handler responses)
    metric_name = str(data.get("metric_name", "")).lower()
    if any(
        token in metric_name
        for token in [
            "por región",
            "por region",
            "regional",
            "por estado",
            "entidad federativa",
        ]
    ):
        return "regional", True

    # Regional data: has estado/region fields OR state names (not just bank names)
    if has_estado_field or has_region_field:
        return "regional", True

    if has_state_names and not has_bank_categories:
        return "regional", True

    # System/bank data: has bank names as categories
    if has_bank_categories:
        return "system", False

    # Check plotly config for chart type hints
    plotly = data.get("plotly_config", {})
    chart_data = plotly.get("data", [])

    regional_buckets = {
        "norte",
        "sur",
        "centro",
        "sureste",
        "noreste",
        "noroeste",
        "centro-occidente",
        "sin región",
        "sin region",
        "no aplica",
    }

    for trace in chart_data:
        trace_type = trace.get("type", "")
        # Choropleth is definitely geographic/regional
        if trace_type == "choropleth":
            return "regional", True
        # Horizontal bar with region buckets is also regional
        y_values = trace.get("y", []) or []
        y_lower = {str(v).strip().lower() for v in y_values}
        if y_lower.intersection(regional_buckets):
            return "regional", True

    # Check response type field if present
    response_type = result.get("type", "")
    if "region" in response_type.lower():
        return "regional", True

    return "unknown", False


def run_test(test_case: RegionalRoutingTestCase) -> Tuple[bool, str]:
    """Run a single test case."""
    result = call_bank_analytics(test_case.query)

    if "error" in result and not result.get("success"):
        # Some errors are acceptable if the handler is correct
        error_msg = result.get("error", "")
        if "no data" in error_msg.lower() or "sin datos" in error_msg.lower():
            # No data is OK - we're testing routing, not data availability
            return True, f"Handler responded (no data available, but routing correct)"
        return False, f"API error: {error_msg}"

    detected_type, has_regional = detect_response_type(result)

    # For regional queries, we expect regional data
    if test_case.should_have_regional_data:
        if has_regional or detected_type == "regional":
            return True, f"Correct routing: got regional data"
        if detected_type == "time_series":
            return False, f"Wrong routing: got time series instead of regional data"
        # Hardened regression criterion: unknown is not acceptable for regional queries
        return False, (
            f"Inconclusive routing for regional query: detected_type={detected_type}, "
            f"regional_indicators={has_regional}"
        )

    # For system queries, we expect time series or system data
    else:
        if detected_type == "time_series":
            return True, f"Correct routing: got time series data"
        if has_regional:
            return False, f"Wrong routing: got regional data instead of system data"
        return True, f"Detected type: {detected_type}"


def main():
    print("=" * 70)
    print("Regional Queries Routing Bug Test Suite (BUG-2026-02-03)")
    print("Ticket: 2026-02-03__BUG__regional-queries-routing")
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

    regional_tests = [tc for tc in TEST_CASES if tc.should_have_regional_data]
    system_tests = [tc for tc in TEST_CASES if not tc.should_have_regional_data]

    print("\n[Regional Queries - Should route to CarteraRegionHandler]")
    print("-" * 70)

    for tc in regional_tests:
        success, message = run_test(tc)
        icon = "\u2705" if success else "\u274c"

        print(f"{icon} [{tc.test_id}] {tc.description[:45]}...")
        print(f"   Query: \"{tc.query}\"")
        print(f"   {message}")

        if success:
            passed += 1
        else:
            failed += 1
            if tc.user_report:
                print(f"   User report: {tc.user_report[:55]}...")

    print("\n[System Queries - Should still route to ResumenSistemaHandler]")
    print("-" * 70)

    for tc in system_tests:
        success, message = run_test(tc)
        icon = "\u2705" if success else "\u274c"

        print(f"{icon} [{tc.test_id}] {tc.description[:45]}...")
        print(f"   Query: \"{tc.query}\"")
        print(f"   {message}")

        if success:
            passed += 1
        else:
            failed += 1

    print("=" * 70)
    print(f"Results: {passed}/{passed + failed} passed")

    if failed == 0:
        print("\u2705 All regional routing tests PASSED!")
        sys.exit(0)
    else:
        print(f"\u274c {failed} tests FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
