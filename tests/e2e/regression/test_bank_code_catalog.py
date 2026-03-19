#!/usr/bin/env python3
"""
Bank Code Catalog Query Tests - BUG-2026-02-05

Regression tests for bank code lookup issues:
1. Single bank lookup returns wrong code (CIBANCO → Santander's code)
2. Reverse lookup returns wrong bank (040044 → Banorte instead of Scotiabank)
3. Multi-bank queries return ALL institutions instead of filtering
4. Incoherence: code→bank and bank→code give different results in same conversation

Reference codes (from bank_dim_institucion):
- BBVA: 0000040012
- BANORTE: 0000040072
- SCOTIABANK: 0000040044
- SANTANDER: 0000040014
- HSBC: 0000040021
- CIBANCO: 0000040143
- INVEX: 0000040059  # Fixed 2026-02-05: was incorrectly 040020
- BANAMEX: 0000040002

Run with:
    python tests/e2e/regression/test_bank_code_catalog.py

Or via pytest (requires backend running):
    RUN_E2E=1 pytest tests/e2e/regression/test_bank_code_catalog.py -v
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add tests/ to path for shared utils
sys.path.append(str(Path(__file__).resolve().parents[2]))

try:
    from utils.helpers import get_auth_token, send_chat_message
except ImportError:
    # Fallback for direct execution
    import httpx

    def get_auth_token(backend_url: str = "http://localhost:8000") -> Optional[str]:
        try:
            resp = httpx.post(
                f"{backend_url}/api/auth/login",
                json={"identifier": "demo", "password": "Demo1234"},
                timeout=10,
            )
            return resp.json().get("access_token") if resp.status_code == 200 else None
        except Exception:
            return None

    def send_chat_message(
        backend_url: str,
        token: str,
        chat_id: str,
        message: str,
        timeout: float = 60,
    ) -> dict:
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.post(
            f"{backend_url}/api/chat",
            json={"message": message, "chat_id": chat_id, "model": "Saptiva Turbo", "stream": False},
            headers=headers,
            timeout=timeout,
        )
        return resp.json()


BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")

# =============================================================================
# REFERENCE DATA - Correct bank codes
# =============================================================================
CORRECT_CODES = {
    "BBVA": "0000040012",
    "BANORTE": "0000040072",
    "SCOTIABANK": "0000040044",
    "SANTANDER": "0000040014",
    "HSBC": "0000040021",
    "CIBANCO": "0000040143",
    "INVEX": "0000040059",  # Fixed 2026-02-05: was incorrectly 040020
    "BANAMEX": "0000040002",
    "AFIRME": "0000040062",
}

# Reverse lookup
CODE_TO_BANK = {code: bank for bank, code in CORRECT_CODES.items()}
# Also add short codes (without leading zeros)
CODE_TO_BANK["040044"] = "SCOTIABANK"
CODE_TO_BANK["040072"] = "BANORTE"
CODE_TO_BANK["040014"] = "SANTANDER"
CODE_TO_BANK["040012"] = "BBVA"
CODE_TO_BANK["040143"] = "CIBANCO"


@dataclass
class TestCase:
    """A single test case for bank code queries."""
    id: str
    query: str
    expected_banks: List[str]  # Banks that MUST appear in response
    expected_codes: List[str]  # Codes that MUST appear in response
    forbidden_codes: List[str] = field(default_factory=list)  # Codes that must NOT appear
    description: str = ""
    query_type: str = "single"  # "single", "multi", "reverse", "list"


@dataclass
class TestResult:
    """Result of a test case execution."""
    test_id: str
    passed: bool
    query: str
    response: str
    expected_codes: List[str]
    found_codes: List[str]
    forbidden_found: List[str]
    error: Optional[str] = None


# =============================================================================
# TEST CASES
# =============================================================================

SINGLE_BANK_TESTS = [
    TestCase(
        id="SINGLE-001",
        query="cual es la clave de CIBANCO?",
        expected_banks=["CIBANCO"],
        expected_codes=["0000040143", "040143"],
        forbidden_codes=["0000040014", "040014"],  # NOT Santander!
        description="CIBANCO should return 040143, NOT 040014 (Santander)",
        query_type="single",
    ),
    TestCase(
        id="SINGLE-002",
        query="clave institucional de Banorte",
        expected_banks=["BANORTE"],
        expected_codes=["0000040072", "040072"],
        forbidden_codes=["0000040044", "040044"],  # NOT Scotiabank!
        description="Banorte should return 040072, NOT 040044 (Scotiabank)",
        query_type="single",
    ),
    TestCase(
        id="SINGLE-003",
        query="dame la clave de Scotiabank",
        expected_banks=["SCOTIABANK"],
        expected_codes=["0000040044", "040044"],
        forbidden_codes=["0000040072", "040072"],  # NOT Banorte!
        description="Scotiabank should return 040044",
        query_type="single",
    ),
    TestCase(
        id="SINGLE-004",
        query="código de Santander",
        expected_banks=["SANTANDER"],
        expected_codes=["0000040014", "040014"],
        description="Santander should return 040014",
        query_type="single",
    ),
    TestCase(
        id="SINGLE-005",
        query="cual es la clave de BBVA?",
        expected_banks=["BBVA"],
        expected_codes=["0000040012", "040012"],
        description="BBVA should return 040012",
        query_type="single",
    ),
]

REVERSE_LOOKUP_TESTS = [
    TestCase(
        id="REVERSE-001",
        query="de que banco es la clave 040044?",
        expected_banks=["SCOTIABANK"],
        expected_codes=["040044"],
        forbidden_codes=[],
        description="040044 should return Scotiabank, NOT Banorte",
        query_type="reverse",
    ),
    TestCase(
        id="REVERSE-002",
        query="a que banco corresponde la clave 040072?",
        expected_banks=["BANORTE"],
        expected_codes=["040072"],
        description="040072 should return Banorte",
        query_type="reverse",
    ),
    TestCase(
        id="REVERSE-003",
        query="que banco tiene el código 040143?",
        expected_banks=["CIBANCO"],
        expected_codes=["040143"],
        description="040143 should return CIBANCO",
        query_type="reverse",
    ),
]

MULTI_BANK_TESTS = [
    TestCase(
        id="MULTI-001",
        query="dame las claves de BBVA, Banorte y Santander",
        expected_banks=["BBVA", "BANORTE", "SANTANDER"],
        expected_codes=["040012", "040072", "040014"],
        description="Multi-bank query should return exactly 3 codes, not all 500",
        query_type="multi",
    ),
    TestCase(
        id="MULTI-002",
        query="códigos de Scotiabank y HSBC",
        expected_banks=["SCOTIABANK", "HSBC"],
        expected_codes=["040044", "040021"],
        description="Multi-bank query should return exactly 2 codes",
        query_type="multi",
    ),
    TestCase(
        id="MULTI-003",
        query="dame las claves de los bancos INVEX, CIBANCO y AFIRME",
        expected_banks=["INVEX", "CIBANCO", "AFIRME"],
        expected_codes=["040059", "040143", "040062"],  # Fixed: INVEX=040059, not 040020
        description="Multi-bank query should return exactly 3 codes",
        query_type="multi",
    ),
]

COHERENCE_TESTS = [
    # Two-turn test: ask for code, then ask reverse lookup with same code
    # Response should be coherent
    TestCase(
        id="COHERENCE-001",
        query="cual es la clave de Scotiabank?",
        expected_banks=["SCOTIABANK"],
        expected_codes=["040044"],
        description="First ask: Scotiabank code",
        query_type="single",
    ),
    # Second turn will use the code from first response
]


def extract_codes_from_response(response: str) -> List[str]:
    """Extract all bank codes (6-10 digits) from response text."""
    # Match patterns like 040044, 0000040044, etc.
    pattern = r'\b0*4\d{4,9}\b'
    codes = re.findall(pattern, response)
    return list(set(codes))


def check_response_has_bank(response: str, bank_name: str) -> bool:
    """Check if response mentions a specific bank."""
    return bank_name.lower() in response.lower()


def check_response_has_code(response: str, code: str) -> bool:
    """Check if response contains a specific code (with or without leading zeros)."""
    # Normalize code - remove leading zeros for comparison
    short_code = code.lstrip('0') or '0'
    return short_code in response or code in response


def count_institutions_in_response(response: str) -> int:
    """Count how many institutions appear in a table-like response."""
    # Count rows in markdown table or bullet points
    lines = response.split('\n')
    count = 0
    for line in lines:
        if line.strip().startswith('|') and '---' not in line:
            count += 1
        elif line.strip().startswith('-') and any(c.isdigit() for c in line):
            count += 1
    return max(count - 1, 0)  # Subtract header row


def run_test_case(
    test: TestCase,
    token: str,
    chat_id: str,
) -> TestResult:
    """Execute a single test case and return result."""
    try:
        response_data = send_chat_message(
            token,
            test.query,
            backend_url=BACKEND_URL,
            chat_id=chat_id,
            timeout=60,
        )

        response_text = response_data.get("content", "")

        # Extract codes from response
        found_codes = extract_codes_from_response(response_text)

        # Check expected codes
        codes_found = []
        codes_missing = []
        for expected_code in test.expected_codes:
            if check_response_has_code(response_text, expected_code):
                codes_found.append(expected_code)
            else:
                codes_missing.append(expected_code)

        # Check forbidden codes
        forbidden_found = []
        for forbidden in test.forbidden_codes:
            if check_response_has_code(response_text, forbidden):
                forbidden_found.append(forbidden)

        # Check expected banks
        banks_found = []
        for bank in test.expected_banks:
            if check_response_has_bank(response_text, bank):
                banks_found.append(bank)

        # For multi-bank tests, check we didn't get ALL institutions
        if test.query_type == "multi":
            institution_count = count_institutions_in_response(response_text)
            if institution_count > 20:  # Way more than requested
                return TestResult(
                    test_id=test.id,
                    passed=False,
                    query=test.query,
                    response=response_text[:500],
                    expected_codes=test.expected_codes,
                    found_codes=found_codes,
                    forbidden_found=forbidden_found,
                    error=f"Got {institution_count} institutions instead of {len(test.expected_banks)}",
                )

        # Determine pass/fail
        passed = (
            len(codes_missing) == 0 and
            len(forbidden_found) == 0 and
            len(banks_found) == len(test.expected_banks)
        )

        error = None
        if codes_missing:
            error = f"Missing codes: {codes_missing}"
        if forbidden_found:
            error = f"Found forbidden codes: {forbidden_found}"
        if len(banks_found) != len(test.expected_banks):
            error = f"Missing banks: {set(test.expected_banks) - set(banks_found)}"

        return TestResult(
            test_id=test.id,
            passed=passed,
            query=test.query,
            response=response_text[:500],
            expected_codes=test.expected_codes,
            found_codes=found_codes,
            forbidden_found=forbidden_found,
            error=error,
        )

    except Exception as e:
        return TestResult(
            test_id=test.id,
            passed=False,
            query=test.query,
            response="",
            expected_codes=test.expected_codes,
            found_codes=[],
            forbidden_found=[],
            error=str(e),
        )


def create_conversation(token: str) -> Optional[str]:
    """Create a new conversation and return its ID."""
    import httpx
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = httpx.post(
            f"{BACKEND_URL}/api/conversations",
            json={},
            headers=headers,
            timeout=10,
        )
        return resp.json().get("id")
    except Exception as e:
        print(f"Failed to create conversation: {e}")
        return None


def run_test_suite(test_cases: List[TestCase], suite_name: str, token: str) -> Dict:
    """Run a suite of tests and return summary."""
    print(f"\n{'='*60}")
    print(f"Running: {suite_name}")
    print(f"{'='*60}")

    results = []
    passed = 0
    failed = 0

    # Create one conversation per suite
    chat_id = create_conversation(token)
    if not chat_id:
        print("❌ Failed to create conversation")
        return {"passed": 0, "failed": len(test_cases), "results": []}

    for test in test_cases:
        result = run_test_case(test, token, chat_id)
        results.append(result)

        status = "✅" if result.passed else "❌"
        print(f"\n{status} {result.test_id}: {test.description}")
        print(f"   Query: {test.query}")
        if not result.passed:
            print(f"   Error: {result.error}")
            print(f"   Found codes: {result.found_codes}")
            print(f"   Response preview: {result.response[:200]}...")
            failed += 1
        else:
            passed += 1

    return {
        "suite": suite_name,
        "passed": passed,
        "failed": failed,
        "total": len(test_cases),
        "results": results,
    }


def run_coherence_test(token: str) -> Dict:
    """
    Test coherence: ask for bank→code, then code→bank in same conversation.
    The responses should be consistent.
    """
    print(f"\n{'='*60}")
    print("Running: Coherence Test (bank→code then code→bank)")
    print(f"{'='*60}")

    chat_id = create_conversation(token)
    if not chat_id:
        return {"passed": 0, "failed": 1, "error": "Failed to create conversation"}

    # Turn 1: Ask for Scotiabank's code
    print("\n📤 Turn 1: 'cual es la clave de Scotiabank?'")
    response1 = send_chat_message(
        token,
        "cual es la clave de Scotiabank?",
        backend_url=BACKEND_URL,
        chat_id=chat_id,
        timeout=60,
    )
    content1 = response1.get("content", "")
    print(f"📥 Response: {content1[:200]}...")

    # Extract code from response
    codes1 = extract_codes_from_response(content1)
    print(f"   Extracted codes: {codes1}")

    if not codes1:
        print("❌ FAIL: No code found in response")
        return {"passed": 0, "failed": 1, "error": "No code in first response"}

    # Turn 2: Ask reverse lookup with the code we got
    code_to_check = codes1[0]
    query2 = f"de que banco es la clave {code_to_check}?"
    print(f"\n📤 Turn 2: '{query2}'")
    response2 = send_chat_message(
        token,
        query2,
        backend_url=BACKEND_URL,
        chat_id=chat_id,
        timeout=60,
    )
    content2 = response2.get("content", "")
    print(f"📥 Response: {content2[:200]}...")

    # Check coherence: should mention Scotiabank
    if "scotiabank" in content2.lower():
        print("✅ PASS: Coherent - reverse lookup returned Scotiabank")
        return {"passed": 1, "failed": 0}
    else:
        print(f"❌ FAIL: Incoherent - asked about code {code_to_check} but didn't get Scotiabank")
        return {"passed": 0, "failed": 1, "error": f"Expected Scotiabank for code {code_to_check}"}


def main():
    """Run all test suites."""
    print("="*60)
    print("Bank Code Catalog Query Tests - BUG-2026-02-05")
    print("="*60)

    # Authenticate
    print("\n🔐 Authenticating...")
    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("❌ Authentication failed. Is the backend running?")
        return 1
    print("✅ Authenticated")

    # Run test suites
    all_results = []

    # Single bank lookups
    result1 = run_test_suite(SINGLE_BANK_TESTS, "Single Bank Lookups", token)
    all_results.append(result1)

    # Reverse lookups
    result2 = run_test_suite(REVERSE_LOOKUP_TESTS, "Reverse Lookups (code→bank)", token)
    all_results.append(result2)

    # Multi-bank queries
    result3 = run_test_suite(MULTI_BANK_TESTS, "Multi-Bank Queries", token)
    all_results.append(result3)

    # Coherence test
    result4 = run_coherence_test(token)
    all_results.append(result4)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    total_passed = sum(r.get("passed", 0) for r in all_results)
    total_failed = sum(r.get("failed", 0) for r in all_results)

    for r in all_results:
        suite = r.get("suite", "Test")
        p = r.get("passed", 0)
        f = r.get("failed", 0)
        status = "✅" if f == 0 else "❌"
        print(f"{status} {suite}: {p}/{p+f} passed")

    print(f"\n{'─'*60}")
    print(f"Total: {total_passed}/{total_passed + total_failed} passed")

    # Save results
    results_path = Path(__file__).parent / "bank_code_catalog_results.json"
    with open(results_path, "w") as f:
        json.dump({
            "timestamp": str(Path(__file__).stat().st_mtime),
            "total_passed": total_passed,
            "total_failed": total_failed,
            "suites": all_results,
        }, f, indent=2, default=str)
    print(f"\nResults saved to: {results_path}")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
