#!/usr/bin/env python3
"""
Test Suite - Bank Code Hallucination Bug (BUG-2026-02-04)
Validates that lookup_institution_code returns correct CNBV codes.

Bug: System hallucinated CNBV codes (e.g., BBVA returned AFIRME's code)
Root cause: Missing lookup_institution_code tool, queries fell through to LLM

Ticket ID: 2026-02-04__BUG__bank-code-hallucination
Status: DONE (2026-02-05)

Run: python tests/e2e/regression/test_bug_2026_02_04_bank_code_hallucination.py
"""

import os
import sys
import json
import requests
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

# Configuration
BANK_ADVISOR_URL = os.environ.get("BANK_ADVISOR_URL", "http://localhost:8002")

# Expected bank codes (from bank_dim_institucion)
EXPECTED_CODES = {
    "BBVA": "0000040012",
    "SANTANDER": "0000040014",
    "SCOTIABANK": "0000040044",
    "HSBC": "0000040021",
    "BANORTE": "0000040072",
    "BANAMEX": "0000040002",
    "AFIRME": "0000040062",
}


@dataclass
class BankCodeTestCase:
    test_id: str
    description: str
    bank_name: str
    expected_code: str
    user_report: str = ""


# Test cases from user feedback (11 reports from 2026-02-04)
TEST_CASES = [
    BankCodeTestCase(
        test_id="HALLUC-001",
        description="Case 1: BBVA should return 0000040012, not AFIRME",
        bank_name="BBVA",
        expected_code="0000040012",
        user_report="esperaba la clave de BBVA y me dio la de AFIRME",
    ),
    BankCodeTestCase(
        test_id="HALLUC-002",
        description="Case 6/8: Santander should return 0000040014",
        bank_name="Santander",
        expected_code="0000040014",
        user_report="la clave de santander no es la indicada",
    ),
    BankCodeTestCase(
        test_id="HALLUC-003",
        description="Case 4: Scotiabank should return single code, not list",
        bank_name="Scotiabank",
        expected_code="0000040044",
        user_report="esperaba la clave de scotiabank y me dio lista de 50 bancos",
    ),
    BankCodeTestCase(
        test_id="HALLUC-004",
        description="HSBC should return 0000040021",
        bank_name="HSBC",
        expected_code="0000040021",
        user_report="",
    ),
    BankCodeTestCase(
        test_id="HALLUC-005",
        description="Banorte should return 0000040072",
        bank_name="Banorte",
        expected_code="0000040072",
        user_report="",
    ),
]


def call_lookup_institution_code(bank_name: str) -> Dict[str, Any]:
    """Call the lookup_institution_code MCP tool."""
    try:
        response = requests.post(
            f"{BANK_ADVISOR_URL}/rpc",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "lookup_institution_code",
                    "arguments": {"bank_name": bank_name}
                },
                "id": 1
            },
            timeout=30
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


def run_test(test_case: BankCodeTestCase) -> Tuple[bool, str]:
    """Run a single test case."""
    result = call_lookup_institution_code(test_case.bank_name)

    if "error" in result and result.get("success") is not True:
        return False, f"API error: {result.get('error', 'Unknown error')}"

    if not result.get("success"):
        return False, f"Tool returned success=False: {result.get('error', 'Unknown')}"

    bank = result.get("bank", {})
    actual_code = bank.get("clave_cnbv", "")

    if actual_code != test_case.expected_code:
        return False, f"Wrong code: expected {test_case.expected_code}, got {actual_code}"

    return True, f"Correct: {bank.get('nombre_corto')} = {actual_code}"


def main():
    print("=" * 70)
    print("Bank Code Hallucination Bug Test Suite (BUG-2026-02-04)")
    print("Ticket: 2026-02-04__BUG__bank-code-hallucination")
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
        print("\u2705 All bank code tests PASSED!")
        sys.exit(0)
    else:
        print(f"\u274c {failed} tests FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
