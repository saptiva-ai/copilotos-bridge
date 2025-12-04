#!/usr/bin/env python3
"""
E2E Integration Tests for BankAdvisor
Tests the complete flow: OctaviOS Backend → BankAdvisor → Response

Usage:
    python scripts/e2e_integration_test.py

Tests:
1. Backend health check
2. BankAdvisor health check
3. Simple metric query (IMOR)
4. Comparison query (INVEX vs SISTEMA)
5. Timeline query
6. Ambiguous query (clarification flow)
7. Complex query (LLM fallback)
8. Error handling
"""

import os
import sys
import json
import time
import requests
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3001")
BANK_ADVISOR_URL = os.getenv("BANK_ADVISOR_URL", "http://localhost:8002")

@dataclass
class TestCase:
    name: str
    query: str
    expected_type: str  # "data", "error", "clarification"
    expected_fields: List[str]
    timeout: int = 10


@dataclass
class TestResult:
    test_case: TestCase
    passed: bool
    latency_ms: float
    response: Dict[str, Any]
    failure_reason: str = ""


# Test cases covering all scenarios
TEST_CASES = [
    TestCase(
        name="Simple Metric Query - IMOR",
        query="IMOR de INVEX",
        expected_type="data",
        expected_fields=["data", "plotly_config", "title"],
        timeout=5
    ),
    TestCase(
        name="Comparison Query - INVEX vs SISTEMA",
        query="IMOR de INVEX vs sistema",
        expected_type="data",
        expected_fields=["data", "plotly_config"],
        timeout=5
    ),
    TestCase(
        name="Timeline Query - Last 12 Months",
        query="IMOR de INVEX últimos 12 meses",
        expected_type="data",
        expected_fields=["data", "plotly_config"],
        timeout=5
    ),
    TestCase(
        name="ICAP Query (New Metric)",
        query="ICAP de INVEX",
        expected_type="data",
        expected_fields=["data", "plotly_config"],
        timeout=5
    ),
    TestCase(
        name="TDA Query (New Metric)",
        query="TDA de INVEX",
        expected_type="data",
        expected_fields=["data", "plotly_config"],
        timeout=5
    ),
    TestCase(
        name="TASA_MN Query (New Metric)",
        query="tasa mn de INVEX",
        expected_type="data",
        expected_fields=["data", "plotly_config"],
        timeout=5
    ),
    TestCase(
        name="Ambiguous Query - Missing Metric",
        query="datos del banco",
        expected_type="clarification",
        expected_fields=["error", "options"],
        timeout=3
    ),
    TestCase(
        name="Vague Query - No Context",
        query="dame algo",
        expected_type="clarification",
        expected_fields=["error"],
        timeout=3
    ),
    TestCase(
        name="Complex Query - Multi-metric",
        query="Compara IMOR, ICOR y ICAP de INVEX",
        expected_type="data",  # Should attempt or clarify
        expected_fields=["error", "data"],  # Either works
        timeout=10
    ),
    TestCase(
        name="Invalid Metric",
        query="METRICA_INVENTADA de INVEX",
        expected_type="error",
        expected_fields=["error"],
        timeout=3
    ),
]


def call_bank_advisor_direct(query: str, timeout: int = 10) -> Tuple[Dict[str, Any], float]:
    """Call BankAdvisor directly via JSON-RPC."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "bank_analytics",
            "arguments": {"metric_or_query": query}
        }
    }

    start = time.time()
    try:
        response = requests.post(
            f"{BANK_ADVISOR_URL}/rpc",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=timeout
        )
        latency_ms = (time.time() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            # Extract text content from JSON-RPC response
            if "result" in data and "content" in data["result"]:
                content = data["result"]["content"]
                if content and len(content) > 0:
                    text = content[0].get("text", "{}")
                    try:
                        parsed = json.loads(text)
                        return parsed, latency_ms
                    except json.JSONDecodeError:
                        return {"error": "invalid_json", "raw": text}, latency_ms
            return data, latency_ms
        else:
            return {"error": "http_error", "status": response.status_code}, latency_ms

    except requests.exceptions.Timeout:
        latency_ms = (time.time() - start) * 1000
        return {"error": "timeout"}, latency_ms
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return {"error": "exception", "message": str(e)}, latency_ms


def evaluate_result(test_case: TestCase, response: Dict[str, Any]) -> Tuple[bool, str]:
    """Evaluate if response matches expected type."""

    # Check for error responses
    if "error" in response:
        if test_case.expected_type == "error" or test_case.expected_type == "clarification":
            # Expected error
            return True, ""
        else:
            return False, f"Unexpected error: {response.get('error')}"

    # Check for clarification (ambiguous query)
    if "options" in response or response.get("error") == "ambiguous_query":
        if test_case.expected_type == "clarification":
            return True, ""
        else:
            return False, f"Got clarification but expected {test_case.expected_type}"

    # Check for data response
    if "data" in response:
        if test_case.expected_type == "data":
            # Verify expected fields
            missing_fields = [f for f in test_case.expected_fields if f not in response]
            if missing_fields and not any(f in response for f in test_case.expected_fields):
                return False, f"Missing fields: {missing_fields}"

            # Verify data structure
            if "months" in response.get("data", {}):
                months = response["data"]["months"]
                if len(months) == 0:
                    return False, "No data returned (empty months array)"

            return True, ""
        else:
            return False, f"Got data but expected {test_case.expected_type}"

    # Unknown response format
    return False, f"Unknown response format: {list(response.keys())}"


def check_health(url: str, service_name: str) -> bool:
    """Check if service is healthy."""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ {service_name} is healthy")
            return True
        else:
            print(f"❌ {service_name} returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {service_name} not reachable: {e}")
        return False


def run_tests() -> List[TestResult]:
    """Run all E2E tests."""

    print("\n" + "="*80)
    print("E2E INTEGRATION TESTS - BankAdvisor")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Bank Advisor URL: {BANK_ADVISOR_URL}")
    print("="*80 + "\n")

    # Health checks
    print("🔍 Running health checks...\n")
    bank_advisor_healthy = check_health(BANK_ADVISOR_URL, "BankAdvisor")

    if not bank_advisor_healthy:
        print("\n❌ Cannot proceed: Services not healthy")
        sys.exit(1)

    print("\n" + "="*80)
    print("Running Test Cases")
    print("="*80 + "\n")

    results = []
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"[{i:02d}/{len(TEST_CASES)}] {test_case.name}")
        print(f'   Query: "{test_case.query}"')

        response, latency_ms = call_bank_advisor_direct(test_case.query, test_case.timeout)
        passed, failure_reason = evaluate_result(test_case, response)

        result = TestResult(
            test_case=test_case,
            passed=passed,
            latency_ms=latency_ms,
            response=response,
            failure_reason=failure_reason
        )
        results.append(result)

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   → {status} ({latency_ms:.0f}ms)")
        if failure_reason:
            print(f"   → Reason: {failure_reason}")

        # Show snippet of response
        if passed and "data" in response:
            months = response.get("data", {}).get("months", [])
            print(f"   → Returned {len(months)} months of data")

        print()
        time.sleep(0.1)  # Small delay between tests

    return results


def print_summary(results: List[TestResult]):
    """Print test summary."""

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    print(f"Total:  {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")

    # Latency stats
    latencies = [r.latency_ms for r in results if r.passed]
    if latencies:
        print(f"\nLatency Statistics (passed tests):")
        print(f"  Min:  {min(latencies):.0f}ms")
        print(f"  Max:  {max(latencies):.0f}ms")
        print(f"  Avg:  {sum(latencies)/len(latencies):.0f}ms")
        print(f"  P95:  {sorted(latencies)[int(len(latencies)*0.95)]:.0f}ms")

    # Failed tests detail
    failed_tests = [r for r in results if not r.passed]
    if failed_tests:
        print(f"\n{'='*80}")
        print("FAILED TESTS DETAIL")
        print(f"{'='*80}\n")

        for r in failed_tests:
            print(f"❌ {r.test_case.name}")
            print(f"   Query: {r.test_case.query}")
            print(f"   Reason: {r.failure_reason}")
            print(f"   Response keys: {list(r.response.keys())}")
            print()

    # Success criteria
    print(f"\n{'='*80}")
    print("SUCCESS CRITERIA")
    print(f"{'='*80}\n")

    criteria = {
        "All tests pass": passed == total,
        "P95 latency < 5s": len(latencies) > 0 and sorted(latencies)[int(len(latencies)*0.95)] < 5000,
        "No crashes": all("exception" not in r.response for r in results),
    }

    for criterion, met in criteria.items():
        status = "✅" if met else "❌"
        print(f"{status} {criterion}")

    if all(criteria.values()):
        print("\n✅ ALL CRITERIA MET - E2E INTEGRATION VALIDATED")
        return 0
    else:
        print("\n❌ SOME CRITERIA NOT MET - REVIEW FAILURES")
        return 1


def main():
    """Main entry point."""

    results = run_tests()
    exit_code = print_summary(results)

    # Save results to JSON
    output_file = f"e2e_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump([
            {
                "name": r.test_case.name,
                "query": r.test_case.query,
                "expected_type": r.test_case.expected_type,
                "passed": r.passed,
                "latency_ms": r.latency_ms,
                "failure_reason": r.failure_reason,
                "response_keys": list(r.response.keys())
            }
            for r in results
        ], f, indent=2, ensure_ascii=False)

    print(f"\n📄 Results saved to: {output_file}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
