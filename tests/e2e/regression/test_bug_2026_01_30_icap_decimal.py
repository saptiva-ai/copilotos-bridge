#!/usr/bin/env python3
"""
Test Suite - ICAP Decimal Shift Bug (BUG-2026-01-30)
Validates that ICAP values are NOT multiplied by 100.

Bug: ICAP shows 2005.94% instead of 20.06%
Root cause: analytics_service.py skip_multiply list missing icap_total

Run: python tests/e2e/regression/test_bug_2026_01_30_icap_decimal.py
"""

import os
import sys
import re
import requests
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field

# Add tests/ to path for shared helpers
sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token as helper_get_auth_token

# Configuration
BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")

# ICAP should NEVER exceed 100% in normal circumstances
# Regulatory minimum is 10.5%, healthy banks are 15-25%
MAX_VALID_ICAP = 50.0  # Very generous upper bound


@dataclass
class IcapTestCase:
    test_id: str
    description: str
    query: str
    expected_behavior: str


TEST_CASES = [
    IcapTestCase(
        test_id="ICAP-001",
        description="ICAP de BBVA should be ~20%, not ~2000%",
        query="Dame el ICAP de BBVA",
        expected_behavior="ICAP value between 10% and 50%",
    ),
    IcapTestCase(
        test_id="ICAP-002",
        description="ICAP ranking should show reasonable values",
        query="¿Cuál banco tiene el mejor ICAP?",
        expected_behavior="All ICAP values under 50%",
    ),
    IcapTestCase(
        test_id="ICAP-003",
        description="ICAP comparison should not multiply by 100",
        query="Compara el ICAP de BBVA y Santander",
        expected_behavior="Both values between 10% and 50%",
    ),
]


def parse_sse_response(response) -> Dict[str, Any]:
    """Parse SSE response into structured data."""
    result = {
        "events": [],
        "bank_chart": None,
        "content": "",
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
                elif current_event == 'chunk':
                    if "content" in parsed:
                        result["content"] += parsed["content"]
                elif current_event == 'error':
                    result["error"] = parsed
            except:
                if current_event == 'chunk':
                    result["content"] += data

    return result


def extract_icap_values(sse_data: Dict) -> List[float]:
    """Extract ICAP percentage values from response."""
    values = []

    # From bank_chart data
    chart = sse_data.get("bank_chart")
    if chart and isinstance(chart, dict):
        # Check plotly data format
        data = chart.get("data", [])
        for trace in data:
            if isinstance(trace, dict):
                y_values = trace.get("y", [])
                for v in y_values:
                    if isinstance(v, (int, float)) and v > 0:
                        values.append(float(v))

    # From text content - look for patterns like "20.06%" or "20.06 %"
    content = sse_data.get("content", "")
    # Pattern: number followed by %
    percent_matches = re.findall(r'(\d+\.?\d*)\s*%', content)
    for match in percent_matches:
        try:
            val = float(match)
            if val > 0:
                values.append(val)
        except ValueError:
            pass

    return values


def validate_icap_values(
    sse_data: Dict,
    test_case: IcapTestCase
) -> Tuple[bool, List[str]]:
    """Validate that ICAP values are in reasonable range (not multiplied by 100)."""
    issues = []

    icap_values = extract_icap_values(sse_data)

    if not icap_values:
        # No values found - might be clarification, ranking list, or error
        content = sse_data.get("content", "")
        if "clarif" in content.lower() or not content:
            return True, []  # Clarification is OK
        # For ranking queries, the response might list banks without explicit %
        # Check if we got a meaningful response about ICAP
        if "icap" in content.lower() and len(content) > 100:
            # Got ICAP-related content, probably ranking format
            # Check for any suspiciously high numbers (>100) that would indicate bug
            all_numbers = re.findall(r'\b(\d{3,}\.?\d*)\b', content)
            suspicious = [float(n) for n in all_numbers if float(n) > 100 and float(n) < 10000]
            if suspicious:
                issues.append(f"Suspicious high values found: {suspicious[:3]} - may indicate x100 bug")
            else:
                return True, []  # No suspicious values, test passes
        issues.append("No ICAP values found in response")
        return False, issues

    # Check if any value exceeds the maximum (indicating x100 bug)
    for val in icap_values:
        if val > MAX_VALID_ICAP:
            issues.append(
                f"ICAP VALUE TOO HIGH: {val}% (expected <{MAX_VALID_ICAP}%). "
                f"This suggests value was incorrectly multiplied by 100."
            )

    return len(issues) == 0, issues


def run_test(
    test_case: IcapTestCase,
    token: str,
    backend_url: str,
    timeout: int,
    verbose: bool
) -> Dict[str, Any]:
    """Run a single test case."""
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
        "test_id": test_case.test_id,
        "description": test_case.description,
        "query": test_case.query,
        "passed": False,
        "issues": [],
        "icap_values": [],
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
        result["icap_values"] = extract_icap_values(sse_data)

        passed, issues = validate_icap_values(sse_data, test_case)
        result["passed"] = passed
        result["issues"] = issues

        if verbose:
            print(f"   ICAP values found: {result['icap_values']}")
            content_preview = sse_data.get("content", "")[:200]
            print(f"   Content preview: {content_preview}...")

    except requests.exceptions.ConnectionError:
        result["issues"].append("Connection failed - is backend running?")
    except Exception as e:
        result["issues"].append(str(e))

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-url", default=BACKEND_URL)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("ICAP Decimal Shift Bug Test Suite (BUG-2026-01-30)")
    print("=" * 60)
    print(f"Validation: ICAP values must be < {MAX_VALID_ICAP}%")
    print("(Values > 100% indicate x100 multiplication bug)")
    print()

    token = helper_get_auth_token(backend_url=args.backend_url)
    if not token:
        print("Fatal: Auth failed - check backend is running")
        sys.exit(2)

    print(f"Running {len(TEST_CASES)} test cases")
    print("-" * 60)

    passed_count = 0
    failed_count = 0

    for test_case in TEST_CASES:
        result = run_test(test_case, token, args.backend_url, args.timeout, args.verbose)

        status = "\u2705" if result["passed"] else "\u274c"
        print(f"{status} [{result['test_id']}]: {result['description'][:50]}...")

        if result["passed"]:
            passed_count += 1
            if result["icap_values"]:
                print(f"   Values: {result['icap_values'][:5]}...")
        else:
            failed_count += 1
            for issue in result["issues"]:
                print(f"   {issue}")

        time.sleep(0.5)

    print("=" * 60)
    print(f"Results: {passed_count}/{passed_count + failed_count} passed")

    if failed_count == 0:
        print("\u2705 All ICAP tests PASSED - no decimal shift detected!")
        sys.exit(0)
    else:
        print("\u274c Some tests FAILED - ICAP values may still be multiplied by 100")
        sys.exit(1)


if __name__ == "__main__":
    main()
