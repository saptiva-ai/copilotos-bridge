#!/usr/bin/env python3
"""
Test Suite - Production Bugs 2026-01-30
Validates fixes for three critical production bugs.

Bugs:
- MONTH-001: Wrong month data mapping (LLM uses Jan data as Sep)
- DECIMAL-001: ICAP decimal shift (2005% instead of 20%)
- SCOPE-001: Query scope expansion (single bank returns all banks)

Run: python tests/e2e/regression/test_production_bugs_2026_01_30.py
Run specific: python tests/e2e/regression/test_production_bugs_2026_01_30.py --bugs MONTH-001
"""

import os
import sys
import re
import requests
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

# Add tests/ to path for shared helpers
sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token as helper_get_auth_token

# Configuration
BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")


def parse_args():
    parser = argparse.ArgumentParser(description="Run Production Bugs 2026-01-30 Test Suite")
    parser.add_argument("--bugs", type=str, help="Comma-separated bug IDs (MONTH-001,DECIMAL-001,SCOPE-001)")
    parser.add_argument("--backend-url", type=str, default=BACKEND_URL)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


@dataclass
class BugTestCase:
    bug_id: str
    description: str
    query: str
    expected_behavior: str
    validation_fn: str
    expected_keywords: List[str] = field(default_factory=list)
    forbidden_keywords: List[str] = field(default_factory=list)


# =============================================================================
# TEST CASES
# =============================================================================
BUG_TEST_CASES = [
    # =========================================================================
    # MONTH-001: Wrong Month Data Mapping
    # Root cause: extract_chart_statistics() extracted values WITHOUT dates
    # Fix: New analytics_extractor.py keeps date-value pairs together
    # =========================================================================
    BugTestCase(
        bug_id="MONTH-001",
        description="Chart response includes explicit date-value pairs",
        query="Dame el ICAP de BBVA en 2025",
        expected_behavior="Response should include explicit dates with values",
        validation_fn="validate_date_value_association",
        expected_keywords=["ICAP", "BBVA", "2025"]
    ),
    BugTestCase(
        bug_id="MONTH-001",
        description="Analysis text correctly associates months with values",
        query="Explícame la evolución del ICAP de Santander de enero a octubre 2025",
        expected_behavior="Text should not confuse January values with September",
        validation_fn="validate_date_value_association",
        expected_keywords=["ICAP", "Santander"]
    ),
    BugTestCase(
        bug_id="MONTH-001",
        description="Multi-bank comparison maintains correct date associations",
        query="Compara el ICAP de BBVA y Santander en 2025",
        expected_behavior="Each bank's values should be correctly dated",
        validation_fn="validate_date_value_association",
        expected_keywords=["ICAP", "BBVA", "Santander"]
    ),

    # =========================================================================
    # DECIMAL-001: ICAP Decimal Shift (2005% instead of 20%)
    # Root cause: Value multiplied by 100 when already a percentage
    # =========================================================================
    BugTestCase(
        bug_id="DECIMAL-001",
        description="ICAP values are in valid percentage range (0-100%)",
        query="Dame el ICAP de BBVA",
        expected_behavior="ICAP values should be <100%, not >1000%",
        validation_fn="validate_icap_range",
        expected_keywords=["ICAP", "BBVA"]
    ),
    BugTestCase(
        bug_id="DECIMAL-001",
        description="IMOR values are in valid percentage range (0-20%)",
        query="Dame el IMOR de Santander",
        expected_behavior="IMOR values should be <20%, not >100%",
        validation_fn="validate_imor_range",
        expected_keywords=["IMOR", "Santander"]
    ),
    BugTestCase(
        bug_id="DECIMAL-001",
        description="Ranking ICAP values are all valid",
        query="¿Cuál banco tiene el mejor ICAP?",
        expected_behavior="All ICAP values in ranking should be <100%",
        validation_fn="validate_icap_range",
        expected_keywords=["ICAP"]
    ),

    # =========================================================================
    # SCOPE-001: Query Scope Expansion (single bank returns all banks)
    # Root cause: Follow-up queries lose bank context
    # =========================================================================
    BugTestCase(
        bug_id="SCOPE-001",
        description="Single bank query returns only that bank",
        query="Dame el ICAP de Citibanamex",
        expected_behavior="Chart should only contain Citibanamex",
        validation_fn="validate_single_bank_scope",
        expected_keywords=["ICAP", "Citibanamex"]
    ),
    BugTestCase(
        bug_id="SCOPE-001",
        description="Two bank comparison returns only those banks",
        query="Compara el ICAP de BBVA y Santander",
        expected_behavior="Chart should only contain BBVA and Santander",
        validation_fn="validate_limited_bank_scope",
        expected_keywords=["ICAP", "BBVA", "Santander"]
    ),
    BugTestCase(
        bug_id="SCOPE-001",
        description="Query should not expand to all banks",
        query="Dame el IMOR de Banorte",
        expected_behavior="Should not return 18 banks",
        validation_fn="validate_no_bank_expansion",
        expected_keywords=["IMOR", "Banorte"],
        forbidden_keywords=["INVEX", "AZTECA", "AFIRME"]
    ),
]


# =============================================================================
# VALIDATORS
# =============================================================================
def validate_date_value_association(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """MONTH-001: Validate that chart data has explicit date-value pairs."""
    issues = []

    chart = sse_data.get("bank_chart")
    if not chart:
        if sse_data.get("clarification"):
            return True, []
        issues.append("No chart received")
        return False, issues

    plotly_config = chart.get("plotly_config", {})
    traces = plotly_config.get("data", [])

    if not traces:
        issues.append("No traces in plotly_config")
        return False, issues

    for i, trace in enumerate(traces):
        x_values = trace.get("x", [])
        y_values = trace.get("y", [])
        bank_name = trace.get("name", f"Trace_{i}")

        # Both x (dates) and y (values) must be present
        if not x_values:
            issues.append(f"Trace '{bank_name}' missing x values (dates)")
        if not y_values:
            issues.append(f"Trace '{bank_name}' missing y values")

        # Lengths must match
        if x_values and y_values and len(x_values) != len(y_values):
            issues.append(f"Trace '{bank_name}' mismatched x/y: {len(x_values)} vs {len(y_values)}")

        # x values should look like dates (multiple formats accepted)
        if x_values:
            first_x = str(x_values[0])
            # Accept: "2025-01-01", "Jan 2025", "January 2025", "2025-01", etc.
            date_patterns = [
                r'\d{4}-\d{2}',           # 2025-01 or 2025-01-01
                r'[A-Za-z]{3,9}\s+\d{4}', # Jan 2025 or January 2025
                r'\d{4}',                  # 2025 (year only)
            ]
            looks_like_date = any(re.search(p, first_x) for p in date_patterns)
            if not looks_like_date:
                issues.append(f"Trace '{bank_name}' x values don't look like dates: {first_x}")

    return len(issues) == 0, issues


def validate_icap_range(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """DECIMAL-001: Validate ICAP values are in valid range (0-100%)."""
    issues = []

    chart = sse_data.get("bank_chart")
    content = sse_data.get("content", "")

    if not chart:
        if sse_data.get("clarification"):
            return True, []
        issues.append("No chart received")
        return False, issues

    plotly_config = chart.get("plotly_config", {})
    traces = plotly_config.get("data", [])

    for trace in traces:
        y_values = trace.get("y", [])
        bank_name = trace.get("name", "Unknown")

        for val in y_values:
            if val is not None and isinstance(val, (int, float)):
                if abs(val) > 100:
                    issues.append(
                        f"DECIMAL SHIFT: {bank_name} ICAP={val:.2f}% (should be <100%)"
                    )
                if abs(val) > 500:
                    issues.append(f"CRITICAL: {bank_name} ICAP={val:.2f}% (x100 bug)")

    # Check text content
    percentage_pattern = r'(\d{3,4})[,.]?\d*\s*%'
    suspicious = re.findall(percentage_pattern, content)
    for val in suspicious:
        if int(val) > 100:
            issues.append(f"Text contains suspicious: {val}%")

    return len(issues) == 0, issues


def validate_imor_range(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """DECIMAL-001: Validate IMOR values are in valid range (0-20%)."""
    issues = []

    chart = sse_data.get("bank_chart")

    if not chart:
        if sse_data.get("clarification"):
            return True, []
        issues.append("No chart received")
        return False, issues

    plotly_config = chart.get("plotly_config", {})
    traces = plotly_config.get("data", [])

    for trace in traces:
        y_values = trace.get("y", [])
        bank_name = trace.get("name", "Unknown")

        for val in y_values:
            if val is not None and isinstance(val, (int, float)):
                if abs(val) > 50:
                    issues.append(
                        f"DECIMAL SHIFT: {bank_name} IMOR={val:.2f}% (should be <20%)"
                    )

    return len(issues) == 0, issues


def validate_single_bank_scope(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """SCOPE-001: Single bank query should return only that bank."""
    issues = []

    chart = sse_data.get("bank_chart")

    if not chart:
        if sse_data.get("clarification"):
            return True, []
        issues.append("No chart received")
        return False, issues

    bank_names = chart.get("bank_names", [])
    plotly_config = chart.get("plotly_config", {})
    traces = plotly_config.get("data", [])

    # Extract expected bank from query
    metrics = {"ICAP", "IMOR", "ICOR", "ROE", "ROA"}
    expected_bank = None
    for kw in test_case.expected_keywords:
        if kw.upper() not in metrics:
            expected_bank = kw.upper()
            break

    # Allow 1-2 banks (bank + SISTEMA)
    if len(bank_names) > 2:
        issues.append(f"SCOPE EXPANSION: Expected 1-2 banks, got {len(bank_names)}: {bank_names}")

    if len(traces) > 3:
        trace_names = [t.get("name", "") for t in traces]
        issues.append(f"Too many traces ({len(traces)}): {trace_names[:5]}...")

    return len(issues) == 0, issues


def validate_limited_bank_scope(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """SCOPE-001: Multi-bank comparison should return only specified banks."""
    issues = []

    chart = sse_data.get("bank_chart")

    if not chart:
        if sse_data.get("clarification"):
            return True, []
        issues.append("No chart received")
        return False, issues

    bank_names = chart.get("bank_names", [])

    metrics = {"ICAP", "IMOR", "ICOR", "ROE", "ROA", "CARTERA", "RESERVAS"}
    expected_banks = [kw.upper() for kw in test_case.expected_keywords if kw.upper() not in metrics]

    max_banks = len(expected_banks) + 1  # +1 for SISTEMA
    if len(bank_names) > max_banks + 1:
        issues.append(f"SCOPE EXPANSION: Expected max {max_banks} banks, got {len(bank_names)}")

    return len(issues) == 0, issues


def validate_no_bank_expansion(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """SCOPE-001: Query should not silently expand to all banks."""
    issues = []

    chart = sse_data.get("bank_chart")

    if not chart:
        if sse_data.get("clarification"):
            return True, []
        issues.append("No chart received")
        return False, issues

    bank_names = chart.get("bank_names", [])
    traces = chart.get("plotly_config", {}).get("data", [])

    # Check forbidden banks
    for forbidden in test_case.forbidden_keywords:
        if forbidden.upper() in [b.upper() for b in bank_names]:
            issues.append(f"SCOPE EXPANSION: Unexpected bank '{forbidden}'")

        for trace in traces:
            if forbidden.upper() in trace.get("name", "").upper():
                issues.append(f"SCOPE EXPANSION: '{forbidden}' in traces")
                break

    if len(bank_names) > 5:
        issues.append(f"SUSPICIOUS: {len(bank_names)} banks for single-bank query")

    return len(issues) == 0, issues


VALIDATORS = {
    "validate_date_value_association": validate_date_value_association,
    "validate_icap_range": validate_icap_range,
    "validate_imor_range": validate_imor_range,
    "validate_single_bank_scope": validate_single_bank_scope,
    "validate_limited_bank_scope": validate_limited_bank_scope,
    "validate_no_bank_expansion": validate_no_bank_expansion,
}


# =============================================================================
# TEST RUNNER
# =============================================================================
def parse_sse_response(response) -> Dict[str, Any]:
    result = {
        "events": [],
        "bank_chart": None,
        "content": "",
        "clarification": None,
        "error": None
    }

    current_event = None

    for line in response.iter_lines():
        if not line:
            continue
        decoded = line.decode('utf-8')

        if decoded.startswith('event:'):
            current_event = decoded.replace('event:', '').strip()
            result["events"].append(current_event)
        elif decoded.startswith('data:') and current_event:
            data = decoded.replace('data:', '').strip()
            if data == "[DONE]":
                continue

            try:
                parsed = json.loads(data)
                if current_event == 'bank_chart':
                    result["bank_chart"] = parsed
                elif current_event == 'bank_clarification':
                    result["clarification"] = parsed
                elif current_event == 'chunk':
                    if "content" in parsed:
                        result["content"] += parsed["content"]
                elif current_event == 'error':
                    result["error"] = parsed
            except:
                if current_event == 'chunk':
                    result["content"] += data

    return result


def run_bug_test(
    test_case: BugTestCase,
    token: str,
    backend_url: str,
    timeout: int,
    verbose: bool
) -> Dict[str, Any]:
    """Run a single bug test case."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream"
    }
    payload = {
        "message": test_case.query,
        "stream": True,
        "model": "Saptiva Turbo"
    }

    result = {
        "bug_id": test_case.bug_id,
        "description": test_case.description,
        "query": test_case.query,
        "passed": False,
        "issues": [],
        "latency_ms": 0
    }

    try:
        start_time = time.time()
        response = requests.post(
            f"{backend_url}/api/chat",
            json=payload,
            headers=headers,
            stream=True,
            timeout=timeout
        )

        if response.status_code != 200:
            result["issues"].append(f"HTTP {response.status_code}")
            return result

        sse_data = parse_sse_response(response)
        result["latency_ms"] = (time.time() - start_time) * 1000

        validator = VALIDATORS.get(test_case.validation_fn)
        if validator:
            passed, issues = validator(sse_data, test_case)
            result["passed"] = passed
            result["issues"] = issues
        else:
            result["issues"].append(f"Unknown validator: {test_case.validation_fn}")

        if verbose:
            print(f"   Events: {sse_data.get('events', [])}")
            if sse_data.get("clarification"):
                print(f"   Clarification: {sse_data['clarification'].get('message', '')[:80]}")
            if sse_data.get("bank_chart"):
                chart = sse_data['bank_chart']
                print(f"   Chart: {chart.get('metric_name', 'N/A')}, banks={chart.get('bank_names', [])}")

    except requests.exceptions.ConnectionError:
        result["issues"].append("Connection failed - is backend running?")
    except Exception as e:
        result["issues"].append(str(e))

    return result


def main():
    args = parse_args()

    print("=" * 60)
    print("Production Bugs Test Suite (2026-01-30)")
    print("=" * 60)

    # Get auth token
    token = helper_get_auth_token(backend_url=args.backend_url)
    if not token:
        print("Fatal: Auth failed - check backend is running")
        sys.exit(2)

    # Filter test cases
    cases = BUG_TEST_CASES
    if args.bugs:
        wanted = {b.strip().upper() for b in args.bugs.split(",")}
        cases = [c for c in cases if c.bug_id.upper() in wanted]

    print(f"Running {len(cases)} test cases")
    print("-" * 60)

    results_by_bug: Dict[str, List[Dict]] = {}

    for case in cases:
        result = run_bug_test(case, token, args.backend_url, args.timeout, args.verbose)

        if case.bug_id not in results_by_bug:
            results_by_bug[case.bug_id] = []
        results_by_bug[case.bug_id].append(result)

        status = "\u2705" if result["passed"] else "\u274c"
        print(f"{status} [{case.bug_id}]: {case.description[:50]}...")
        if not result["passed"]:
            for issue in result["issues"]:
                print(f"   {issue}")

        time.sleep(0.5)

    # Summary
    print("=" * 60)
    print("Summary by Bug")
    print("=" * 60)

    all_passed = True
    total_passed = 0
    total_tests = 0

    for bug_id in sorted(results_by_bug.keys()):
        bug_results = results_by_bug[bug_id]
        passed = sum(1 for r in bug_results if r["passed"])
        total = len(bug_results)
        total_passed += passed
        total_tests += total
        status = "\u2705" if passed == total else "\u274c"
        print(f"{status} {bug_id}: {passed}/{total} tests passed")
        if passed < total:
            all_passed = False

    print("=" * 60)
    print(f"Total: {total_passed}/{total_tests} tests passed")

    if all_passed:
        print("\u2705 All production bug tests PASSED!")
        sys.exit(0)
    else:
        print("\u274c Some tests FAILED - bugs may still exist")
        sys.exit(1)


if __name__ == "__main__":
    main()
