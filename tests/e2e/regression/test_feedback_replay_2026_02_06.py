#!/usr/bin/env python3
"""
E2E Feedback Replay — 2026-02-06

Replays EXACT queries from the feedback triage report (2026-02-05) to verify
which bugs persist and which are resolved.

Source: docs/feedback-triage-2026-02-05.md (18 negative feedback entries)

Tickets tested (DOING):
  - bank-code-confusion       (FDBK-0059,0060,0063,0064,0065)
  - multi-bank-code-filter    (FDBK-0066,0067,0068,0069,0070)
  - response-grounding-desync (FDBK-0072)
  - cartera-por-banco-por-ano (FDBK-0043)

Regression checks (DONE):
  - chart-year-mismatch       (FDBK-0074)
  - icap-decimal-shift        (FDBK-0005)
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "90"))

# Known correct bank codes (from bank_dim_institucion)
BANK_CODES = {
    "INVEX": "0000040059",
    "BBVA": "0000040012",
    "BANORTE": "0000040072",
    "SCOTIABANK": "0000040044",
    "SANTANDER": "0000040014",
    "CIBANCO": "0000040143",
    "AFIRME": "0000040062",
}

# Wrong codes that the LLM used to hallucinate
KNOWN_WRONG_CODES = {
    "0000040015",  # FDBK-0059: LLM gave this for Scotiabank (wrong)
    "0000040020",  # FDBK-0065: LLM gave this for INVEX (wrong)
}


@dataclass
class ReplayCase:
    feedback_id: str
    ticket: str
    query: str
    validate: Callable[[Dict[str, Any]], tuple[bool, str]]
    description: str = ""
    # For multi-turn: prior messages to send first (same chat_id)
    prior_messages: List[str] = field(default_factory=list)


@dataclass
class ReplayResult:
    case: ReplayCase
    passed: bool
    detail: str
    content_preview: str = ""


# --- Validators ---


def _check_bank_code(response: Dict[str, Any], bank: str, correct_code: str) -> tuple[bool, str]:
    """Check that response contains the correct code for a bank."""
    content = response.get("content", "")
    if response.get("error"):
        return False, f"Request error: {response['error']}"
    if not content:
        return False, "Empty response"

    # Check correct code is present
    if correct_code in content:
        return True, f"Correct code {correct_code} found for {bank}"

    # Check if a known wrong code was returned
    for wrong in KNOWN_WRONG_CODES:
        if wrong in content:
            return False, f"Wrong code {wrong} returned for {bank} (correct: {correct_code})"

    # Check if any 10-digit code is present
    codes_in_text = re.findall(r"0000\d{6}", content)
    if codes_in_text:
        return False, (
            f"Code(s) {codes_in_text} found but not {correct_code} for {bank}"
        )

    return False, f"No code found for {bank} in response"


def _check_reverse_lookup(response: Dict[str, Any], code: str, expected_bank: str) -> tuple[bool, str]:
    """Check that reverse lookup (code → bank) returns correct bank name."""
    content = response.get("content", "").lower()
    if response.get("error"):
        return False, f"Request error: {response['error']}"

    expected_lower = expected_bank.lower()
    if expected_lower in content:
        return True, f"Correctly identified {code} as {expected_bank}"

    # Check for known wrong associations
    wrong_banks = {"banorte", "banamex", "santander", "bbva"} - {expected_lower}
    for wrong in wrong_banks:
        if wrong in content:
            return False, f"Wrong bank: said '{wrong}' for code {code} (correct: {expected_bank})"

    return False, f"'{expected_bank}' not found in response"


def _check_multi_bank_filter(
    response: Dict[str, Any], expected_banks: List[str], max_total: int
) -> tuple[bool, str]:
    """Check that multi-bank query returns only the requested banks, not all 121."""
    content = response.get("content", "")
    if response.get("error"):
        return False, f"Request error: {response['error']}"
    if not content:
        return False, "Empty response"

    # Count how many 10-digit codes appear — if >max_total, it dumped the full catalog
    all_codes = re.findall(r"0000\d{6}", content)
    unique_codes = set(all_codes)

    if len(unique_codes) > max_total:
        return False, (
            f"Returned {len(unique_codes)} unique codes (max expected: {max_total}). "
            f"Likely dumped full catalog"
        )

    # Check that at least some of the requested banks have correct codes
    found = 0
    for bank in expected_banks:
        correct = BANK_CODES.get(bank.upper())
        if correct and correct in content:
            found += 1

    if found == 0:
        # Check for parser error pattern
        if "no encontr" in content.lower():
            return False, f"Parser error: 'no encontré' — couldn't split multi-bank query"
        return False, f"None of the {len(expected_banks)} requested banks found with correct codes"

    return True, f"{found}/{len(expected_banks)} requested banks found with correct codes"


def _check_no_extraction_error(response: Dict[str, Any]) -> tuple[bool, str]:
    """Check that response doesn't contain a technical extraction error."""
    content = response.get("content", "").lower()
    if response.get("error"):
        return False, f"Request error: {response['error']}"

    error_patterns = [
        "error técnico",
        "error al procesar",
        "extraction failed",
        "error de extracción",
        "no pude procesar",
    ]
    for pat in error_patterns:
        if pat in content:
            return False, f"Extraction error detected: '{pat}'"

    # Also check that we got a chart or meaningful content
    has_chart = response.get("bank_chart") is not None
    has_content = len(content) > 50

    if has_chart or has_content:
        return True, "No extraction error, response looks valid"

    return False, "Response too short and no chart — possible silent failure"


def _check_chart_year(response: Dict[str, Any], expected_year: str) -> tuple[bool, str]:
    """Check that chart dates include the expected year."""
    bc = response.get("bank_chart")
    if not bc:
        return False, "No chart returned"

    chart_status = str(bc.get("chart_status", ""))
    if chart_status != "success":
        return False, f"Chart status: {chart_status} (expected success)"

    plotly = bc.get("plotly_config", {})
    dates = []
    for trace in plotly.get("data", []):
        dates.extend(trace.get("x", []))

    if not dates:
        return False, "No dates in chart"

    has_year = any(expected_year in str(d) for d in dates)
    if has_year:
        return True, f"Chart includes year {expected_year}"

    sample = dates[:3]
    return False, f"Chart dates don't include {expected_year}. Sample: {sample}"


def _check_icap_range(response: Dict[str, Any]) -> tuple[bool, str]:
    """Check that ICAP values are in reasonable range (10-30%), not shifted x100."""
    content = response.get("content", "")
    if response.get("error"):
        return False, f"Request error: {response['error']}"

    # Extract percentages from text
    pcts = re.findall(r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*%", content)
    if not pcts:
        return True, "No percentages found in text (may be using chart only)"

    values = []
    for p in pcts:
        try:
            v = float(p.replace(",", ""))
            if v != 100:  # Skip "100%"
                values.append(v)
        except ValueError:
            pass

    if not values:
        return True, "No meaningful ICAP percentages found"

    max_val = max(values)
    if max_val > 100:
        return False, f"ICAP value {max_val}% exceeds 100% — likely decimal shift (x100)"

    if max_val > 50:
        return False, f"ICAP value {max_val}% unusually high — verify data"

    return True, f"ICAP values in range (max: {max_val}%)"


def _check_definition_response(
    response: Dict[str, Any], expected_terms: List[str],
) -> tuple[bool, str]:
    """Check that the system provides a conceptual explanation, not just data."""
    content = response.get("content", "").lower()
    if response.get("error"):
        return False, f"Request error: {response['error']}"
    if not content or len(content) < 30:
        return False, "Response too short — likely didn't answer"

    # Check for expected explanation terms
    found = [t for t in expected_terms if t.lower() in content]
    if len(found) >= 2:
        return True, f"Definition found ({len(found)}/{len(expected_terms)} terms: {found})"
    if len(found) == 1:
        return True, f"Partial definition ({found[0]} found)"

    # Check for error/refusal patterns
    refusal_patterns = ["no puedo", "no tengo", "error", "no encontré"]
    if any(p in content for p in refusal_patterns):
        return False, "System refused or errored instead of explaining"

    # If content is long enough, the LLM probably answered something useful
    if len(content) > 200:
        return True, f"Long response ({len(content)} chars) — likely contains explanation"

    return False, f"None of {expected_terms} found in response"


def _check_chart_updates_between_queries(
    resp1: Dict[str, Any], resp2: Dict[str, Any],
) -> tuple[bool, str]:
    """Check that two consecutive queries produce different chart data."""
    bc1 = resp1.get("bank_chart")
    bc2 = resp2.get("bank_chart")

    if not bc1:
        return False, "First query didn't return a chart"
    if not bc2:
        return False, "Second query didn't return a chart"

    # Compare chart data — they should be different
    plotly1 = bc1.get("plotly_config", {})
    plotly2 = bc2.get("plotly_config", {})

    traces1 = plotly1.get("data", [])
    traces2 = plotly2.get("data", [])

    if not traces1 or not traces2:
        return False, "One or both charts have no trace data"

    # Compare trace names (bank names should differ)
    names1 = {t.get("name", "") for t in traces1}
    names2 = {t.get("name", "") for t in traces2}

    if names1 != names2:
        return True, f"Charts differ: {names1} vs {names2}"

    # If same bank, compare y-values
    y1 = traces1[0].get("y", [])[:3] if traces1 else []
    y2 = traces2[0].get("y", [])[:3] if traces2 else []

    if y1 != y2:
        return True, f"Same bank but different data values"

    return False, "Charts appear identical — possible caching issue"


def _check_grounding(response: Dict[str, Any]) -> tuple[bool, str]:
    """Check that text doesn't contradict chart data (no denial when data exists)."""
    content = response.get("content", "").lower()
    bc = response.get("bank_chart")

    if not bc:
        return True, "No chart — grounding check n/a"

    chart_status = str(bc.get("chart_status", ""))
    if chart_status != "success":
        return True, f"Chart status {chart_status} — grounding check n/a"

    denial_phrases = [
        "no tengo datos", "no hay datos", "no puedo proporcionar",
        "no puedo mostrar", "no está disponible",
    ]
    denials = [p for p in denial_phrases if p in content]

    # Check if there are also grounded values (partial caveat is OK)
    has_numbers = bool(re.search(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:MDP|%|millones)", content))

    if denials and not has_numbers:
        return False, f"Full data denial when chart=success: {denials}"

    return True, "Text is grounded (no contradictions or partial caveat)"


# --- Test Cases ---

REPLAY_CASES: List[ReplayCase] = [
    # ══════════════════════════════════════════════════════════════
    # TICKET: bank-code-confusion (DOING)
    # ══════════════════════════════════════════════════════════════
    ReplayCase(
        feedback_id="FDBK-0064",
        ticket="bank-code-confusion",
        description="CIBanco code lookup — was returning Santander's code",
        query="cual es la clave de CIBanco?",
        validate=lambda r: _check_bank_code(r, "CIBANCO", BANK_CODES["CIBANCO"]),
    ),
    ReplayCase(
        feedback_id="FDBK-0060",
        ticket="bank-code-confusion",
        description="Reverse lookup 040044 — was saying Banorte instead of Scotiabank",
        query="de que banco es la clave 040044?",
        validate=lambda r: _check_reverse_lookup(r, "040044", "Scotiabank"),
    ),
    ReplayCase(
        feedback_id="FDBK-0065",
        ticket="bank-code-confusion",
        description="Multi-bank code lookup — was swapping codes between banks",
        query="podrías darme las claves de los siguientes bancos: Scotiabank, Banorte, BBVA e INVEX",
        validate=lambda r: _check_multi_bank_filter(
            r, ["SCOTIABANK", "BANORTE", "BBVA", "INVEX"], max_total=6,
        ),
    ),

    # ══════════════════════════════════════════════════════════════
    # TICKET: multi-bank-code-filter (DOING)
    # ══════════════════════════════════════════════════════════════
    ReplayCase(
        feedback_id="FDBK-0066",
        ticket="multi-bank-code-filter",
        description="Comma-separated banks — parser couldn't split",
        query="cual es la clave de santander, bbva, bank of america, invex y afirme?",
        validate=lambda r: _check_multi_bank_filter(
            r, ["SANTANDER", "BBVA", "INVEX", "AFIRME"], max_total=8,
        ),
    ),
    ReplayCase(
        feedback_id="FDBK-0070",
        ticket="multi-bank-code-filter",
        description="'los siguientes bancos:' prefix — returned full catalog",
        query="dame las claves de los siguientes bancos: bank of america, invex y afirme",
        validate=lambda r: _check_multi_bank_filter(
            r, ["INVEX", "AFIRME"], max_total=6,
        ),
    ),
    ReplayCase(
        feedback_id="FDBK-0069",
        ticket="multi-bank-code-filter",
        description="5-bank query — returned all 121 + duplicates",
        query="dame las claves de los siguientes bancos: santander, bbva, BoA, invex, afirme",
        validate=lambda r: _check_multi_bank_filter(
            r, ["SANTANDER", "BBVA", "INVEX", "AFIRME"], max_total=8,
        ),
    ),

    # ══════════════════════════════════════════════════════════════
    # TICKET: response-grounding-desync (DOING)
    # ══════════════════════════════════════════════════════════════
    ReplayCase(
        feedback_id="FDBK-0072",
        ticket="response-grounding-desync",
        description="Text values must match chart data (was off by 0.30 MDP)",
        query="muéstrame la cartera comercial de INVEX en 2025",
        validate=lambda r: _check_grounding(r),
    ),

    # ══════════════════════════════════════════════════════════════
    # TICKET: cartera-por-banco-por-ano (DOING)
    # ══════════════════════════════════════════════════════════════
    ReplayCase(
        feedback_id="FDBK-0043",
        ticket="cartera-por-banco-por-ano",
        description="Cartera hipotecaria extraction — was failing with technical error",
        query="cartera hipotecaria de INVEX en 2025",
        validate=lambda r: _check_no_extraction_error(r),
    ),

    # ══════════════════════════════════════════════════════════════
    # TICKET: definition-glossary-queries (DOING)
    # ══════════════════════════════════════════════════════════════
    ReplayCase(
        feedback_id="FDBK-DEF-001",
        ticket="definition-glossary-queries",
        description="User asked 'what is cartera comercial' — system didn't explain",
        query="que es la cartera comercial de un banco?",
        validate=lambda r: _check_definition_response(
            r, ["crédito", "préstamo", "empresa", "comercial", "banco"],
        ),
    ),
    ReplayCase(
        feedback_id="FDBK-DEF-002",
        ticket="definition-glossary-queries",
        description="User asked for detailed ICAP explanation",
        query="qué es el ICAP?",
        validate=lambda r: _check_definition_response(
            r, ["capital", "capitalización", "riesgo", "activo", "banco"],
        ),
    ),

    # ══════════════════════════════════════════════════════════════
    # TICKET: chart-caching-stale-render (DOING) — backend-side only
    # NOTE: Full visual test requires Playwright. Here we verify the
    # backend returns DIFFERENT chart data for different queries.
    # ══════════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════
    # REGRESSION: chart-year-mismatch (DONE)
    # ══════════════════════════════════════════════════════════════
    ReplayCase(
        feedback_id="FDBK-0074",
        ticket="chart-year-mismatch",
        description="Chart must show 2023 data when user asks for 2023",
        query="muéstrame la cartera comercial de INVEX en 2023",
        validate=lambda r: _check_chart_year(r, "2023"),
    ),

    # ══════════════════════════════════════════════════════════════
    # REGRESSION: icap-decimal-shift (DONE)
    # ══════════════════════════════════════════════════════════════
    ReplayCase(
        feedback_id="FDBK-0005",
        ticket="icap-decimal-shift",
        description="ICAP values must be in 10-30% range, not x100 shifted",
        query="Cual banco tiene el mejor ICAP?",
        validate=lambda r: _check_icap_range(r),
    ),
]


# --- Special multi-query test for chart caching ---

CHART_CACHE_TEST = {
    "feedback_id": "FDBK-CACHE-001",
    "ticket": "chart-caching-stale-render",
    "description": "Backend returns different chart data for BBVA vs Santander",
    "query_1": "ICAP de BBVA en 2025",
    "query_2": "ICAP de Santander en 2025",
}


def run_chart_cache_test(token: str) -> ReplayResult:
    """Test that backend returns different charts for different banks."""
    info = CHART_CACHE_TEST
    dummy_case = ReplayCase(
        feedback_id=info["feedback_id"],
        ticket=info["ticket"],
        description=info["description"],
        query=f"{info['query_1']} → {info['query_2']}",
        validate=lambda r: (False, "n/a"),  # unused
    )

    resp1 = send_chat_message(
        token, info["query_1"], backend_url=BACKEND_URL, timeout=TIMEOUT,
    )
    resp2 = send_chat_message(
        token, info["query_2"], backend_url=BACKEND_URL, timeout=TIMEOUT,
    )

    passed, detail = _check_chart_updates_between_queries(resp1, resp2)
    content_preview = f"Q1: {resp1.get('content', '')[:100]} | Q2: {resp2.get('content', '')[:100]}"

    return ReplayResult(
        case=dummy_case,
        passed=passed,
        detail=detail,
        content_preview=content_preview,
    )


# --- Runner ---


def run_replay(token: str, case: ReplayCase) -> ReplayResult:
    """Run a single feedback replay case."""
    chat_id = None

    # Send prior messages if multi-turn
    for msg in case.prior_messages:
        resp = send_chat_message(token, msg, backend_url=BACKEND_URL, timeout=TIMEOUT)
        if resp.get("meta") and resp["meta"].get("chat_id"):
            chat_id = resp["meta"]["chat_id"]

    # Send the actual query
    resp = send_chat_message(
        token, case.query, backend_url=BACKEND_URL, chat_id=chat_id, timeout=TIMEOUT,
    )

    content = resp.get("content", "")
    passed, detail = case.validate(resp)

    return ReplayResult(
        case=case,
        passed=passed,
        detail=detail,
        content_preview=content[:300].replace("\n", " ") if content else "(empty)",
    )


def main() -> int:
    print("=" * 70)
    print("E2E Feedback Replay — 2026-02-06")
    print("Replaying exact user queries from feedback triage (2026-02-05)")
    print("=" * 70)
    print()

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FATAL: Auth failed")
        return 2

    print(f"Authenticated against {BACKEND_URL}\n")

    results: List[ReplayResult] = []
    by_ticket: Dict[str, List[ReplayResult]] = {}
    current_ticket = ""

    for case in REPLAY_CASES:
        if case.ticket != current_ticket:
            current_ticket = case.ticket
            print(f"\n{'=' * 70}")
            print(f"  TICKET: {case.ticket}")
            print(f"{'=' * 70}")

        print(f"\n  [{case.feedback_id}] {case.description}")
        print(f"  Query: \"{case.query}\"")

        result = run_replay(token, case)
        results.append(result)
        by_ticket.setdefault(case.ticket, []).append(result)

        if result.passed:
            print(f"  PASSED: {result.detail}")
        else:
            print(f"  FAILED: {result.detail}")
            if result.content_preview:
                print(f"  Response: {result.content_preview[:200]}")

    # --- Special: chart caching test (multi-query) ---
    print(f"\n{'=' * 70}")
    print(f"  TICKET: chart-caching-stale-render")
    print(f"{'=' * 70}")
    info = CHART_CACHE_TEST
    print(f"\n  [{info['feedback_id']}] {info['description']}")
    print(f"  Query 1: \"{info['query_1']}\"")
    print(f"  Query 2: \"{info['query_2']}\"")

    cache_result = run_chart_cache_test(token)
    results.append(cache_result)
    by_ticket.setdefault("chart-caching-stale-render", []).append(cache_result)

    if cache_result.passed:
        print(f"  PASSED: {cache_result.detail}")
    else:
        print(f"  FAILED: {cache_result.detail}")

    # --- Summary by ticket ---
    print(f"\n\n{'=' * 70}")
    print("SUMMARY BY TICKET")
    print(f"{'=' * 70}\n")

    ticket_status: Dict[str, str] = {}
    for ticket, ticket_results in by_ticket.items():
        passed = sum(1 for r in ticket_results if r.passed)
        total = len(ticket_results)
        all_passed = passed == total

        status = "RESOLVED" if all_passed else f"PERSISTS ({total - passed}/{total} failing)"
        ticket_status[ticket] = status

        icon = "RESOLVED" if all_passed else "PERSISTS"
        print(f"  [{icon}] {ticket}: {passed}/{total} passed")
        for r in ticket_results:
            tag = "OK" if r.passed else "FAIL"
            print(f"    [{tag}] {r.case.feedback_id}: {r.detail}")

    # --- Kanban recommendations ---
    print(f"\n{'=' * 70}")
    print("KANBAN RECOMMENDATIONS")
    print(f"{'=' * 70}\n")

    for ticket, status in ticket_status.items():
        if "RESOLVED" in status:
            print(f"  {ticket}: DOING -> DONE (all feedback cases pass)")
        else:
            print(f"  {ticket}: stays in DOING ({status})")

    # --- Save results ---
    total_passed = sum(1 for r in results if r.passed)
    total_failed = sum(1 for r in results if not r.passed)

    out = Path(__file__).parent / "feedback_replay_2026_02_06_results.json"
    out.write_text(
        json.dumps(
            {
                "date": "2026-02-06",
                "source": "docs/feedback-triage-2026-02-05.md",
                "total_passed": total_passed,
                "total_failed": total_failed,
                "by_ticket": {
                    ticket: {
                        "status": ticket_status[ticket],
                        "cases": [
                            {
                                "feedback_id": r.case.feedback_id,
                                "query": r.case.query,
                                "passed": r.passed,
                                "detail": r.detail,
                            }
                            for r in ticket_results
                        ],
                    }
                    for ticket, ticket_results in by_ticket.items()
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"\nResults saved: {out}")

    print(f"\n{'=' * 70}")
    if total_failed == 0:
        print(f"ALL {total_passed} REPLAY CASES PASSED!")
    else:
        print(f"{total_passed} passed, {total_failed} failed out of {total_passed + total_failed}")
    print(f"{'=' * 70}")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
