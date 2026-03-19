#!/usr/bin/env python3
"""
Feedback Replay Test — 2026-02-05

Replays the EXACT queries reported in negative user feedback to verify fixes.
Source: docs/feedback-triage-2026-02-05.md

Tickets tested:
  - bank-code-confusion (FDBK-0059 to FDBK-0065)
  - multi-bank-code-filter (FDBK-0066 to FDBK-0070)

Run:
    python tests/e2e/regression/test_feedback_replay_2026_02_05.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")


# Reference codes
CORRECT_CODES: Dict[str, str] = {
    "BBVA": "0000040012",
    "BANORTE": "0000040072",
    "SCOTIABANK": "0000040044",
    "SANTANDER": "0000040014",
    "HSBC": "0000040021",
    "CIBANCO": "0000040143",
    "INVEX": "0000040059",
    "AFIRME": "0000040062",
    "BANAMEX": "0000040002",
    "BANK OF AMERICA": "0000040106",
}


@dataclass
class FeedbackCase:
    fdbk_id: str
    query: str
    ticket: str
    expected_codes: Dict[str, str]  # bank -> code
    forbidden_codes: List[str] = field(default_factory=list)
    max_institutions: int = 0  # 0 = no limit check
    must_not_contain: List[str] = field(default_factory=list)
    is_followup: bool = False
    setup_query: str = ""  # Query to send first for follow-ups


@dataclass
class ReplayResult:
    fdbk_id: str
    query: str
    passed: bool
    checks: List[str]
    failures: List[str]
    response_preview: str


# ─────────────────────────────────────────────────────────────
# BANK-CODE-CONFUSION test cases (exact user queries)
# ─────────────────────────────────────────────────────────────
BANK_CODE_CONFUSION_CASES = [
    FeedbackCase(
        fdbk_id="FDBK-0063",
        query="cual es la clave de CIBANCO?",
        ticket="bank-code-confusion",
        expected_codes={"CIBANCO": "040143"},
        forbidden_codes=["040014", "0000040014"],  # NOT Santander
    ),
    FeedbackCase(
        fdbk_id="FDBK-0064",
        query="cual es la clave de CIBanco?",
        ticket="bank-code-confusion",
        expected_codes={"CIBANCO": "040143"},
        forbidden_codes=["040014", "0000040014"],
    ),
    FeedbackCase(
        fdbk_id="FDBK-0060",
        query="de que banco es la clave 040044?",
        ticket="bank-code-confusion",
        expected_codes={"SCOTIABANK": "040044"},
        must_not_contain=["banorte", "mercantil del norte"],
    ),
    FeedbackCase(
        fdbk_id="FDBK-0059",
        query="y la de scotiabank?",
        ticket="bank-code-confusion",
        expected_codes={"SCOTIABANK": "040044"},
        forbidden_codes=["0000040015", "040015"],
        is_followup=True,
        setup_query="cual es la clave de BBVA?",
    ),
    FeedbackCase(
        fdbk_id="FDBK-0065",
        query="podrías darme las claves de los siguientes bancos: Scotiabank, Banorte, BBVA e INVEX",
        ticket="bank-code-confusion",
        expected_codes={
            "SCOTIABANK": "040044",
            "BANORTE": "040072",
            "BBVA": "040012",
            "INVEX": "040059",
        },
        forbidden_codes=["0000040015", "040015", "0000040020", "040020"],
    ),
]

# ─────────────────────────────────────────────────────────────
# MULTI-BANK-CODE-FILTER test cases (exact user queries)
# ─────────────────────────────────────────────────────────────
MULTI_BANK_CODE_FILTER_CASES = [
    FeedbackCase(
        fdbk_id="FDBK-0066",
        query="cual es la clave de santander, bbva, bank of america, invex y afirme?",
        ticket="multi-bank-code-filter",
        expected_codes={
            "SANTANDER": "040014",
            "BBVA": "040012",
            "INVEX": "040059",
            "AFIRME": "040062",
        },
        max_institutions=20,  # should NOT return 121
        must_not_contain=["no encontré"],
    ),
    FeedbackCase(
        fdbk_id="FDBK-0067",
        query="cuales son las claves de santander, bbva, bank of america, invex y afirme?",
        ticket="multi-bank-code-filter",
        expected_codes={
            "SANTANDER": "040014",
            "BBVA": "040012",
            "INVEX": "040059",
            "AFIRME": "040062",
        },
        max_institutions=20,
        must_not_contain=["no encontré"],
    ),
    FeedbackCase(
        fdbk_id="FDBK-0068",
        query="cuales son las claves institucionales de santander, bbva, bank of america, invex y afirme?",
        ticket="multi-bank-code-filter",
        expected_codes={
            "SANTANDER": "040014",
            "BBVA": "040012",
            "INVEX": "040059",
            "AFIRME": "040062",
        },
        max_institutions=20,
        must_not_contain=["no encontré"],
    ),
    FeedbackCase(
        fdbk_id="FDBK-0069",
        query="dame las claves de los siguientes bancos: santander, bbva, BoA, invex, afirme",
        ticket="multi-bank-code-filter",
        expected_codes={
            "SANTANDER": "040014",
            "BBVA": "040012",
            "INVEX": "040059",
            "AFIRME": "040062",
        },
        max_institutions=20,
    ),
    FeedbackCase(
        fdbk_id="FDBK-0070",
        query="dame las claves de los siguientes bancos: bank of america, invex y afirme",
        ticket="multi-bank-code-filter",
        expected_codes={
            "INVEX": "040059",
            "AFIRME": "040062",
        },
        max_institutions=20,
    ),
]


def code_in_response(response: str, code: str) -> bool:
    """Check if a code appears in the response (with or without leading zeros)."""
    short = code.lstrip("0") or "0"
    return short in response or code in response


def count_table_rows(response: str) -> int:
    """Count rows in a markdown table response."""
    count = 0
    for line in response.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|") and "---" not in stripped and stripped.count("|") >= 3:
            count += 1
    return max(count - 1, 0)  # Subtract header


def create_conversation(token: str) -> Optional[str]:
    import httpx

    try:
        resp = httpx.post(
            f"{BACKEND_URL}/api/conversations",
            json={},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        return resp.json().get("id")
    except Exception as e:
        print(f"  ⚠ Failed to create conversation: {e}")
        return None


def run_feedback_case(
    case: FeedbackCase, token: str, chat_id: Optional[str] = None
) -> ReplayResult:
    """Run a single feedback case and validate response."""
    checks: List[str] = []
    failures: List[str] = []

    # Create conversation if needed
    cid = chat_id
    if not cid:
        cid = create_conversation(token)
        if not cid:
            return ReplayResult(case.fdbk_id, case.query, False, [], ["no conversation"], "")

    # Send setup query for follow-ups
    if case.is_followup and case.setup_query:
        send_chat_message(token, case.setup_query, backend_url=BACKEND_URL, chat_id=cid, timeout=60)

    # Send the actual query
    resp = send_chat_message(token, case.query, backend_url=BACKEND_URL, chat_id=cid, timeout=60)
    content = resp.get("content", "")
    content_lower = content.lower()

    # Check 1: Expected codes present
    for bank, code in case.expected_codes.items():
        if code_in_response(content, code):
            checks.append(f"{bank}={code}")
        else:
            failures.append(f"MISSING {bank}={code}")

    # Check 2: Forbidden codes absent
    for forbidden in case.forbidden_codes:
        if code_in_response(content, forbidden):
            failures.append(f"FORBIDDEN code {forbidden} found")
        else:
            checks.append(f"no {forbidden}")

    # Check 3: Must-not-contain phrases
    for phrase in case.must_not_contain:
        if phrase.lower() in content_lower:
            failures.append(f"UNWANTED phrase '{phrase}' found")
        else:
            checks.append(f"no '{phrase}'")

    # Check 4: Institution count limit
    if case.max_institutions > 0:
        row_count = count_table_rows(content)
        if row_count > case.max_institutions:
            failures.append(f"TOO MANY rows: {row_count} (max {case.max_institutions})")
        else:
            checks.append(f"rows={row_count} (max {case.max_institutions})")

    passed = len(failures) == 0 and len(checks) > 0
    return ReplayResult(
        fdbk_id=case.fdbk_id,
        query=case.query,
        passed=passed,
        checks=checks,
        failures=failures,
        response_preview=content[:300],
    )


def run_suite(
    cases: List[FeedbackCase], suite_name: str, token: str
) -> Dict:
    print(f"\n{'='*65}")
    print(f"  {suite_name}")
    print(f"{'='*65}")

    passed = 0
    failed = 0
    results = []

    for case in cases:
        result = run_feedback_case(case, token)
        results.append(result)

        icon = "✅" if result.passed else "❌"
        print(f"\n{icon} {result.fdbk_id} [{case.ticket}]")
        print(f"   Query: \"{case.query}\"")

        if result.passed:
            print(f"   Checks: {', '.join(result.checks)}")
            passed += 1
        else:
            print(f"   Checks OK: {', '.join(result.checks)}")
            print(f"   FAILURES: {', '.join(result.failures)}")
            print(f"   Response: {result.response_preview[:200]}...")
            failed += 1

    return {"suite": suite_name, "passed": passed, "failed": failed, "total": len(cases)}


def main() -> int:
    print("=" * 65)
    print("  Feedback Replay — 2026-02-05")
    print("  Source: docs/feedback-triage-2026-02-05.md")
    print("=" * 65)

    print("\n🔐 Authenticating...")
    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("❌ Authentication failed. Is the backend running?")
        return 1
    print("✅ Authenticated\n")

    all_results = []

    # Suite 1: bank-code-confusion
    r1 = run_suite(
        BANK_CODE_CONFUSION_CASES,
        "bank-code-confusion (FDBK-0059..0065)",
        token,
    )
    all_results.append(r1)

    # Suite 2: multi-bank-code-filter
    r2 = run_suite(
        MULTI_BANK_CODE_FILTER_CASES,
        "multi-bank-code-filter (FDBK-0066..0070)",
        token,
    )
    all_results.append(r2)

    # Summary
    print(f"\n{'='*65}")
    print("  SUMMARY")
    print(f"{'='*65}")

    total_p = sum(r["passed"] for r in all_results)
    total_f = sum(r["failed"] for r in all_results)

    for r in all_results:
        icon = "✅" if r["failed"] == 0 else "❌"
        print(f"  {icon} {r['suite']}: {r['passed']}/{r['total']}")

    print(f"\n  Total: {total_p}/{total_p + total_f} passed")

    # Save results
    out_path = Path(__file__).parent / "feedback_replay_2026_02_05_results.json"
    with open(out_path, "w") as f:
        json.dump({"total_passed": total_p, "total_failed": total_f, "suites": all_results}, f, indent=2)
    print(f"  Results: {out_path}\n")

    return 0 if total_f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
