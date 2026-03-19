#!/usr/bin/env python3
"""
E2E Tests for Multi-Bank Comparison Scenarios

Tests for:
- COMP-001: Bank-to-bank comparisons (vs operator)
- COMP-002: Multi-bank data availability
- COMP-003: Metrics across different banks (ICAP, IMOR, CARTERA)
- COMP-004: Legacy vs new digital bank comparisons

Reference: ETL multi-bank integration (2026-01-13)

NOTE: These tests require the multi-bank ETL to be deployed to production.
As of 2026-01-13, the ETL changes have been made but not yet deployed.
Run ETL with production credentials to enable these tests:
    cd plugins/bank-advisor-private && source envs/.env.prod && \
    python -m etl.core.etl_unified --data-root data/raw

Expected banks after ETL: INVEX, BBVA, SANTANDER, BANORTE, HSBC,
CITIBANAMEX, SCOTIABANK, AZTECA, BAJIO, AFIRME, MIFEL, and more.
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Add tests/ to path for shared helpers
sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token as helper_get_auth_token

import requests

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")


@dataclass
class TestTurn:
    """A single turn in a test conversation."""
    message: str
    expected_type: str = "any"  # "chart", "clarification", "rag", "error", "any"
    expected_metric: Optional[str] = None
    expected_banks: List[str] = field(default_factory=list)
    # Validation functions
    validate_dates: bool = False  # Check dates are valid (not 2017-01-01)
    validate_has_data: bool = False  # Check response has actual data points
    validate_multi_bank: bool = False  # Check multiple banks have data
    description: str = ""


@dataclass
class TestScenario:
    """A complete test scenario."""
    id: str
    bug_id: str
    name: str
    description: str
    turns: List[TestTurn]


# =============================================================================
# TEST SCENARIOS FOR MULTI-BANK COMPARISONS
# =============================================================================

SCENARIOS: List[TestScenario] = [
    # -------------------------------------------------------------------------
    # COMP-001: Bank-to-Bank Comparisons (vs operator)
    # -------------------------------------------------------------------------
    TestScenario(
        id="COMP-001",
        bug_id="MULTI-BANK",
        name="IMOR BBVA vs Santander",
        description="Compare IMOR between two major banks",
        turns=[
            TestTurn(
                message="IMOR de BBVA vs Santander",
                expected_type="chart",
                expected_metric="IMOR",
                expected_banks=["BBVA", "SANTANDER"],
                validate_multi_bank=True,
                validate_has_data=True,
                description="Should return IMOR for both BBVA and Santander",
            ),
        ],
    ),
    TestScenario(
        id="COMP-002",
        bug_id="MULTI-BANK",
        name="ICAP Banorte vs HSBC",
        description="Compare ICAP between two banks",
        turns=[
            TestTurn(
                message="ICAP de Banorte vs HSBC",
                expected_type="chart",
                expected_metric="ICAP",
                expected_banks=["BANORTE", "HSBC"],
                validate_multi_bank=True,
                validate_has_data=True,
                description="Should return ICAP for both Banorte and HSBC",
            ),
        ],
    ),
    TestScenario(
        id="COMP-003",
        bug_id="MULTI-BANK",
        name="Cartera Total Three Banks",
        description="Compare cartera total across three banks",
        turns=[
            TestTurn(
                message="cartera total de BBVA, Santander y Banorte",
                expected_type="chart",
                expected_metric="CARTERA_TOTAL",
                expected_banks=["BBVA", "SANTANDER", "BANORTE"],
                validate_multi_bank=True,
                validate_has_data=True,
                description="Should return cartera total for all three banks",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # COMP-002: Multi-Bank Data Availability
    # -------------------------------------------------------------------------
    TestScenario(
        id="COMP-004",
        bug_id="DATA-COVERAGE",
        name="BBVA ICAP Has Data",
        description="Verify BBVA has ICAP data after ETL fix",
        turns=[
            TestTurn(
                message="ICAP de BBVA",
                expected_type="chart",
                expected_metric="ICAP",
                expected_banks=["BBVA"],
                validate_has_data=True,
                description="BBVA should have ICAP data",
            ),
        ],
    ),
    TestScenario(
        id="COMP-005",
        bug_id="DATA-COVERAGE",
        name="Santander IMOR Has Data",
        description="Verify Santander has IMOR data",
        turns=[
            TestTurn(
                message="IMOR de Santander",
                expected_type="chart",
                expected_metric="IMOR",
                expected_banks=["SANTANDER"],
                validate_has_data=True,
                description="Santander should have IMOR data",
            ),
        ],
    ),
    TestScenario(
        id="COMP-006",
        bug_id="DATA-COVERAGE",
        name="Citibanamex Cartera Comercial",
        description="Verify Citibanamex has cartera comercial data",
        turns=[
            TestTurn(
                message="cartera comercial de Citibanamex",
                expected_type="chart",
                expected_metric="CARTERA_COMERCIAL",
                expected_banks=["CITIBANAMEX"],
                validate_has_data=True,
                description="Citibanamex should have cartera comercial data",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # COMP-003: Comparative Analysis Queries
    # -------------------------------------------------------------------------
    TestScenario(
        id="COMP-007",
        bug_id="COMPARISON",
        name="Ranking IMOR All Banks",
        description="Get IMOR ranking across multiple banks",
        turns=[
            TestTurn(
                message="ranking de IMOR por banco",
                expected_type="any",  # Could be chart or clarification
                expected_metric="IMOR",
                description="Should provide IMOR ranking or ask for clarification",
            ),
        ],
    ),
    TestScenario(
        id="COMP-008",
        bug_id="COMPARISON",
        name="Best ICAP Question",
        description="Question about best ICAP",
        turns=[
            TestTurn(
                message="cual banco tiene mejor ICAP?",
                expected_type="any",  # Could be chart or clarification
                description="Should answer about best ICAP bank",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # COMP-004: Multi-Turn Comparison Flow
    # -------------------------------------------------------------------------
    TestScenario(
        id="COMP-009",
        bug_id="MULTI-TURN",
        name="Compare Then Add Bank",
        description="Start with two banks, then add a third",
        turns=[
            TestTurn(
                message="ICAP de INVEX vs BBVA",
                expected_type="chart",
                expected_metric="ICAP",
                expected_banks=["INVEX", "BBVA"],
                validate_has_data=True,
                description="Compare ICAP of INVEX and BBVA",
            ),
            TestTurn(
                message="agrega Santander",
                expected_type="chart",
                expected_metric="ICAP",
                expected_banks=["INVEX", "BBVA", "SANTANDER"],
                validate_has_data=True,
                description="Should add Santander to the comparison",
            ),
        ],
    ),
    TestScenario(
        id="COMP-010",
        bug_id="MULTI-TURN",
        name="Compare Then Change Metric",
        description="Compare two banks, then change the metric",
        turns=[
            TestTurn(
                message="IMOR de BBVA y Banorte",
                expected_type="chart",
                expected_metric="IMOR",
                expected_banks=["BBVA", "BANORTE"],
                validate_has_data=True,
                description="Compare IMOR of BBVA and Banorte",
            ),
            TestTurn(
                message="ahora muestra el ICAP",
                expected_type="chart",
                expected_metric="ICAP",
                expected_banks=["BBVA", "BANORTE"],
                validate_has_data=True,
                description="Should show ICAP for same banks",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Regional Banks (from AnalisisGeneral 040_TO.csv)
    # -------------------------------------------------------------------------
    TestScenario(
        id="COMP-011",
        bug_id="REGIONAL",
        name="Regional Bank ICAP",
        description="Test regional bank (Bajio) has data",
        turns=[
            TestTurn(
                message="ICAP de Bajio",
                expected_type="chart",
                expected_metric="ICAP",
                expected_banks=["BAJIO"],
                validate_has_data=True,
                description="Bajio should have ICAP data from AnalisisGeneral",
            ),
        ],
    ),
    TestScenario(
        id="COMP-012",
        bug_id="REGIONAL",
        name="Regional Bank Comparison",
        description="Compare two regional banks",
        turns=[
            TestTurn(
                message="cartera total de Bajio vs Afirme",
                expected_type="chart",
                expected_metric="CARTERA_TOTAL",
                expected_banks=["BAJIO", "AFIRME"],
                validate_multi_bank=True,
                validate_has_data=True,
                description="Should compare cartera total for both regional banks",
            ),
        ],
    ),
]


def get_auth_token() -> Optional[str]:
    """Get authentication token using shared helper."""
    return helper_get_auth_token(backend_url=BACKEND_URL)


def parse_sse_response(response) -> Dict[str, Any]:
    """Parse SSE response."""
    result = {
        "events": [],
        "bank_chart": None,
        "clarification": None,
        "content": "",
        "meta": None,
        "error": None,
    }

    current_event = None

    for line in response.iter_lines():
        if not line:
            continue

        line = line.decode("utf-8")

        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            data = line[5:].strip()
            if data and current_event:
                result["events"].append(current_event)
                try:
                    parsed = json.loads(data)
                    if current_event == "bank_chart":
                        result["bank_chart"] = parsed
                    elif current_event == "clarification":
                        result["clarification"] = parsed
                    elif current_event == "content":
                        result["content"] += parsed.get("text", "")
                    elif current_event == "meta":
                        result["meta"] = parsed
                    elif current_event == "error":
                        result["error"] = parsed
                except json.JSONDecodeError:
                    pass

    return result


def send_message(token: str, message: str, conversation_id: str) -> Dict[str, Any]:
    """Send a message and get response."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",  # Required for SSE streaming
    }
    # FIX 2026-01-13: Use chat_id (not conversationId) to match ChatRequest schema
    # FIX 2026-01-13: Use valid Saptiva model (financial-analyst returns 404)
    payload = {
        "message": message,
        "chat_id": conversation_id,  # Backend expects 'chat_id', not 'conversationId'
        "model": "Saptiva Turbo",  # Must use valid Saptiva model name (case-sensitive)
        "stream": True,  # Required to activate streaming path
    }

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/chat",
            headers=headers,
            json=payload,
            stream=True,  # requests library streaming (for reading SSE)
            timeout=60
        )
        return parse_sse_response(response)
    except Exception as e:
        return {"error": str(e)}


def validate_turn(turn: TestTurn, result: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate a turn's result against expectations."""
    reasons = []

    # Check for error
    if result.get("error"):
        return False, f"Error: {result['error']}"

    # Determine response type
    if result.get("bank_chart"):
        response_type = "chart"
    elif result.get("clarification"):
        response_type = "clarification"
    elif result.get("content") and len(result["content"]) > 50:
        response_type = "rag"
    else:
        response_type = "unknown"

    # Validate type
    if turn.expected_type not in ["any", response_type]:
        reasons.append(f"Expected type {turn.expected_type}, got {response_type}")

    # Validate metric (case-insensitive)
    # FIX 2026-01-13: Use metric_name instead of metric
    if turn.expected_metric and result.get("bank_chart"):
        chart = result["bank_chart"]
        chart_metric = chart.get("metric_name", "").upper()
        expected = turn.expected_metric.upper()
        # Normalize common variations
        # FIX 2026-01-22: Normalize canonical IDs to their short aliases for comparison
        # The system returns canonical IDs (e.g., ICAP_TOTAL) but tests use aliases (e.g., ICAP)
        if chart_metric in ["ICAP_TOTAL"]:
            chart_metric = "ICAP"
        if expected in ["ICAP_TOTAL"]:
            expected = "ICAP"
        if chart_metric in ["CARTERA_VIVIENDA_TOTAL", "CARTERA_VIVIENDA"]:
            chart_metric = "CARTERA_VIVIENDA"
        if chart_metric in ["CARTERA_COMERCIAL_TOTAL", "CARTERA_COMERCIAL"]:
            chart_metric = "CARTERA_COMERCIAL"
        if expected in ["CARTERA_VIVIENDA_TOTAL", "CARTERA_VIVIENDA"]:
            expected = "CARTERA_VIVIENDA"
        if expected in ["CARTERA_COMERCIAL_TOTAL", "CARTERA_COMERCIAL"]:
            expected = "CARTERA_COMERCIAL"
        if chart_metric != expected:
            reasons.append(f"Expected metric {expected}, got {chart_metric}")

    # Validate banks
    # FIX 2026-01-13: Use bank_names instead of banks
    if turn.expected_banks and result.get("bank_chart"):
        chart = result["bank_chart"]
        chart_banks = [b.upper() for b in chart.get("bank_names", [])]
        for expected_bank in turn.expected_banks:
            if expected_bank.upper() not in chart_banks:
                reasons.append(f"Expected bank {expected_bank} not found in {chart_banks}")

    # Validate multi-bank (at least 2 banks with data)
    # FIX 2026-01-13: Use plotly_config.data instead of series
    if turn.validate_multi_bank and result.get("bank_chart"):
        chart = result["bank_chart"]
        plotly_config = chart.get("plotly_config", {})
        traces = plotly_config.get("data", [])
        # Count banks with actual data in traces
        banks_with_data = set()
        for trace in traces:
            # For bar charts, x contains bank names, y contains values
            x_values = trace.get("x", [])
            y_values = trace.get("y", [])
            for i, bank in enumerate(x_values):
                if i < len(y_values) and y_values[i] is not None and y_values[i] != 0:
                    banks_with_data.add(bank)
            # For line charts, name is the bank
            if trace.get("name") and trace.get("y"):
                if any(v is not None and v != 0 for v in trace.get("y", [])):
                    banks_with_data.add(trace.get("name"))
        if len(banks_with_data) < 2:
            reasons.append(f"Expected at least 2 banks with data, got {len(banks_with_data)}: {list(banks_with_data)}")

    # Validate has data
    # FIX 2026-01-13: Use plotly_config.data instead of series
    if turn.validate_has_data and result.get("bank_chart"):
        chart = result["bank_chart"]
        plotly_config = chart.get("plotly_config", {})
        traces = plotly_config.get("data", [])
        has_data = False
        for trace in traces:
            y_values = trace.get("y", [])
            if any(v is not None and v != 0 for v in y_values):
                has_data = True
                break
        if not has_data:
            reasons.append("Expected data in chart but found none")

    # Validate dates (no 2017-01-01)
    if turn.validate_dates and result.get("bank_chart"):
        chart = result["bank_chart"]
        dates = chart.get("dates", [])
        bad_dates = [d for d in dates if d and "2017-01-01" in str(d)]
        if bad_dates:
            reasons.append(f"Found invalid dates: {bad_dates[:3]}")

    if reasons:
        return False, "; ".join(reasons)
    return True, "OK"


def run_scenario(scenario: TestScenario, token: str) -> Tuple[bool, Dict]:
    """Run a test scenario."""
    # FIX 2026-01-13: Start with a placeholder conversation_id.
    # After the first turn, use the real chat_id from the 'meta' event
    # to ensure all turns in the same scenario share the same session.
    conversation_id = f"test-multibank-{scenario.id}-{int(time.time())}"
    results = {"turns": [], "passed": True}

    for i, turn in enumerate(scenario.turns):
        result = send_message(token, turn.message, conversation_id)

        # FIX 2026-01-13: Capture real chat_id from meta event for subsequent turns
        # The backend creates a new session if the provided conversation_id doesn't exist,
        # and returns the real chat_id in the 'meta' event.
        if result.get("meta") and result["meta"].get("chat_id"):
            real_chat_id = result["meta"]["chat_id"]
            if conversation_id != real_chat_id:
                print(f"  [DEBUG] Updating conversation_id: {conversation_id[:30]}... -> {real_chat_id[:30]}...")
                conversation_id = real_chat_id

        passed, reason = validate_turn(turn, result)

        turn_result = {
            "turn": i + 1,
            "message": turn.message,
            "passed": passed,
            "reason": reason,
            "response_type": "chart" if result.get("bank_chart") else ("clarification" if result.get("clarification") else "other"),
        }

        # Add chart details for debugging
        if result.get("bank_chart"):
            chart = result["bank_chart"]
            turn_result["metric"] = chart.get("metric")
            turn_result["banks"] = chart.get("banks", [])
            turn_result["data_points"] = len(chart.get("dates", []))

        results["turns"].append(turn_result)

        if not passed:
            results["passed"] = False

        time.sleep(1.0)  # FIX 2026-01-13: Increased delay to allow MongoDB write propagation

    return results["passed"], results


def main():
    """Main test runner."""
    print("=" * 70)
    print("MULTI-BANK COMPARISON E2E TESTS")
    print("=" * 70)
    print()

    # Get auth token
    token = get_auth_token()
    if not token:
        print("Failed to get auth token")
        return

    # Run scenarios
    passed_count = 0
    failed_count = 0
    results_by_bug = {}

    max_workers = int(os.environ.get("E2E_MAX_WORKERS", 1))
    if max_workers > 1:
        # Run scenarios in parallel using ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_scenario, s, token): s for s in SCENARIOS}

            for future in as_completed(futures):
                scenario = futures[future]
                passed, result = future.result()

                # Print result
                status = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
                print("-" * 60)
                print(f"Scenario: {scenario.id} [{scenario.bug_id}]")
                print(f"Name: {scenario.name}")
                print("-" * 60)
                print(f"Result: [{status}]")

                for turn in result["turns"]:
                    turn_status = "\033[92m✓\033[0m" if turn["passed"] else "\033[91m✗\033[0m"
                    print(f"  Turn {turn['turn']}: [{turn_status}] {turn['message'][:40]}...")
                    print(f"       Type: {turn['response_type']}")
                    if turn.get("metric"):
                        print(f"       Metric: {turn['metric']}")
                    if turn.get("banks"):
                        print(f"       Banks: {turn['banks']}")
                    if not turn["passed"]:
                        print(f"       Reason: {turn['reason']}")
                print()

                if passed:
                    passed_count += 1
                else:
                    failed_count += 1

                # Track by bug_id
                if scenario.bug_id not in results_by_bug:
                    results_by_bug[scenario.bug_id] = {"passed": 0, "total": 0}
                results_by_bug[scenario.bug_id]["total"] += 1
                if passed:
                    results_by_bug[scenario.bug_id]["passed"] += 1
    else:
        # Sequential execution
        for scenario in SCENARIOS:
            print("-" * 60)
            print(f"Scenario: {scenario.id} [{scenario.bug_id}]")
            print(f"Name: {scenario.name}")
            print(f"Description: {scenario.description}")
            print("-" * 60)

            passed, result = run_scenario(scenario, token)

            status = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
            print(f"Result: [{status}]")

            for turn in result["turns"]:
                turn_status = "\033[92m✓\033[0m" if turn["passed"] else "\033[91m✗\033[0m"
                print(f"  Turn {turn['turn']}: [{turn_status}] {turn['message'][:40]}...")
                print(f"       Type: {turn['response_type']}")
                if turn.get("metric"):
                    print(f"       Metric: {turn['metric']}")
                if turn.get("banks"):
                    print(f"       Banks: {turn['banks']}")
                if not turn["passed"]:
                    print(f"       Reason: {turn['reason']}")
            print()

            if passed:
                passed_count += 1
            else:
                failed_count += 1

            # Track by bug_id
            if scenario.bug_id not in results_by_bug:
                results_by_bug[scenario.bug_id] = {"passed": 0, "total": 0}
            results_by_bug[scenario.bug_id]["total"] += 1
            if passed:
                results_by_bug[scenario.bug_id]["passed"] += 1

    # Print summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total = passed_count + failed_count
    pass_rate = (passed_count / total * 100) if total > 0 else 0
    print(f"Scenarios Passed: {passed_count}/{total}")
    print(f"Pass Rate: {pass_rate:.1f}%")
    print()
    print("By Category:")
    for bug_id, stats in sorted(results_by_bug.items()):
        pct = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        status = "✓" if pct == 100 else "✗"
        print(f"  {bug_id}: {stats['passed']}/{stats['total']} ({pct:.0f}%) {status}")

    # Save results
    results_file = "multibank_test_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate": pass_rate,
            "by_category": results_by_bug,
        }, f, indent=2)
    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
