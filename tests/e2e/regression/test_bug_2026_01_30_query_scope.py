#!/usr/bin/env python3
"""
Test Suite - Query Scope All Banks Bug (BUG-2026-01-30)
Validates that follow-up queries respect bank context from previous messages.

Bug: User asks about specific bank in follow-up query but system returns all banks.
Root cause: Context banks from session not propagated to QuerySpec.

Run: python tests/e2e/regression/test_bug_2026_01_30_query_scope.py
"""

import os
import sys
import requests
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# Add tests/ to path for shared helpers
sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token as helper_get_auth_token

# Configuration
BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")


@dataclass
class ScopeTestCase:
    test_id: str
    description: str
    query: str
    session_context: Optional[Dict[str, Any]]
    expected_banks: List[str]
    should_not_include: List[str]


TEST_CASES = [
    # Case 1: Follow-up query should use bank from memory_context
    ScopeTestCase(
        test_id="SCOPE-001",
        description="Follow-up query should maintain bank context",
        query="explícame como obtuviste que santander creció un 12%",
        session_context={
            "memory_context": {
                "bank": "santander",
                "metric": "icap_total",
                "period": "2025",
            },
            "recent_messages": [],
        },
        expected_banks=["SANTANDER"],
        should_not_include=["BBVA", "BANORTE", "CITIBANAMEX", "HSBC"],
    ),
    # Case 2: Query with explicit bank should work without context
    ScopeTestCase(
        test_id="SCOPE-002",
        description="Explicit bank in query should be respected",
        query="Dame el ICAP de BBVA",
        session_context=None,
        expected_banks=["BBVA"],
        should_not_include=["SANTANDER", "BANORTE"],
    ),
    # Case 3: Multi-bank context should be preserved
    ScopeTestCase(
        test_id="SCOPE-003",
        description="Multi-bank context should be preserved in follow-up",
        query="cuál tuvo mejor rendimiento",
        session_context={
            "memory_context": {
                "last_banks": "BBVA,SANTANDER,BANORTE",
                "last_metric": "ICAP",
                "period": "2025",
            },
            "recent_messages": [],
        },
        expected_banks=["BBVA", "SANTANDER", "BANORTE"],
        should_not_include=["CITIBANAMEX", "HSBC", "INBURSA"],
    ),
]


def parse_sse_response(response) -> Dict[str, Any]:
    """Parse SSE response into structured data."""
    result = {
        "events": [],
        "bank_chart": None,
        "content": "",
        "error": None,
        "sql_generated": None,
        "bank_names": [],
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
                    # Extract bank_names from chart metadata
                    if isinstance(parsed, dict):
                        result["bank_names"] = parsed.get("bank_names", [])
                        metadata = parsed.get("metadata", {})
                        if not result["bank_names"] and "bank_names" in metadata:
                            result["bank_names"] = metadata["bank_names"]
                        # Also check sql_generated
                        result["sql_generated"] = metadata.get("sql_generated", "")
                elif current_event == 'chunk':
                    if "content" in parsed:
                        result["content"] += parsed["content"]
                elif current_event == 'error':
                    result["error"] = parsed
            except json.JSONDecodeError:
                if current_event == 'chunk':
                    result["content"] += data

    return result


def validate_bank_scope(
    sse_data: Dict,
    test_case: ScopeTestCase
) -> Tuple[bool, List[str]]:
    """Validate that response contains only expected banks."""
    issues = []

    bank_names = sse_data.get("bank_names", [])
    sql_generated = sse_data.get("sql_generated", "")

    # If no bank_names in response, check SQL for bank filter
    if not bank_names and sql_generated:
        # Check if SQL has bank filter
        has_bank_filter = "banco_norm" in sql_generated.lower() and any(
            bank.lower() in sql_generated.lower()
            for bank in test_case.expected_banks
        )
        if not has_bank_filter and test_case.expected_banks:
            issues.append(
                f"SQL missing bank filter. Expected {test_case.expected_banks} "
                f"but got: {sql_generated[:100]}..."
            )

    # Check expected banks are present
    if bank_names:
        for expected_bank in test_case.expected_banks:
            if expected_bank.upper() not in [b.upper() for b in bank_names]:
                issues.append(f"Missing expected bank: {expected_bank}")

        # Check unwanted banks are NOT present
        for unwanted_bank in test_case.should_not_include:
            if unwanted_bank.upper() in [b.upper() for b in bank_names]:
                issues.append(
                    f"Unwanted bank present: {unwanted_bank}. "
                    f"This indicates bank context was not respected."
                )

    return len(issues) == 0, issues


def run_test(
    test_case: ScopeTestCase,
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
        "model": "Saptiva Turbo",
    }

    # Add session_context if provided
    if test_case.session_context:
        payload["session_context"] = test_case.session_context

    result = {
        "test_id": test_case.test_id,
        "description": test_case.description,
        "query": test_case.query,
        "passed": False,
        "issues": [],
        "bank_names": [],
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
        result["bank_names"] = sse_data.get("bank_names", [])

        passed, issues = validate_bank_scope(sse_data, test_case)
        result["passed"] = passed
        result["issues"] = issues

        if verbose:
            print(f"   Bank names found: {result['bank_names']}")
            sql_preview = sse_data.get("sql_generated", "")[:100]
            if sql_preview:
                print(f"   SQL preview: {sql_preview}...")

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
    print("Query Scope All Banks Bug Test Suite (BUG-2026-01-30)")
    print("=" * 60)
    print("Validation: Follow-up queries should respect bank context")
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
            if result["bank_names"]:
                print(f"   Banks: {result['bank_names']}")
        else:
            failed_count += 1
            for issue in result["issues"]:
                print(f"   {issue}")

        time.sleep(0.5)

    print("=" * 60)
    print(f"Results: {passed_count}/{passed_count + failed_count} passed")

    if failed_count == 0:
        print("\u2705 All scope tests PASSED - bank context is respected!")
        sys.exit(0)
    else:
        print("\u274c Some tests FAILED - bank context may not be respected")
        sys.exit(1)


if __name__ == "__main__":
    main()
