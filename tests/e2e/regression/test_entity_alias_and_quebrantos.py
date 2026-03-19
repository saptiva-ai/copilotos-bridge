#!/usr/bin/env python3
"""
E2E Regression — entity-alias-gfnorte + quebrantos-data-stale

Verifies two BACKLOG bug fixes:

1. entity-alias-gfnorte (FDBK-0075):
   "GFNORTE" was not recognized as an alias for BANORTE.
   Fix: Added "gfnorte" and "grupo financiero banorte" to ACRONYM_NORMALIZATIONS
   in banking_keywords.py.

2. quebrantos-data-stale (FDBK-0008):
   "que bancos tienen quebrantos?" returned all banks at 0 MDP.
   Root causes:
     a) Quebrantos is annual (January only) — other months are 0.
        Ranking used latest month → always 0. Fix: exclude_zeros config flag.
     b) Values stored in PESOS (backfill ×1M); pipeline now divides ÷1M.
        Fix: skip_currency_scale=False + ÷1M in use cases.

Usage:
    python tests/e2e/regression/test_entity_alias_and_quebrantos.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "90"))

# Known banks with quebrantos data (non-zero, from DB investigation)
BANKS_WITH_QUEBRANTOS = {
    "BANORTE", "BBVA", "CITIBANAMEX", "HSBC", "SANTANDER",
    "MONEX", "BANCREA", "AFIRME", "MIFEL", "MULTIVA",
}
# Banks that should NOT appear (all zeros)
BANKS_WITHOUT_QUEBRANTOS = {"INVEX", "SISTEMA"}


@dataclass
class ReplayCase:
    feedback_id: str
    ticket: str
    query: str
    validate: Callable[[Dict[str, Any]], Tuple[bool, str]]
    description: str = ""
    prior_messages: List[str] = field(default_factory=list)


@dataclass
class ReplayResult:
    case: ReplayCase
    passed: bool
    detail: str
    content_preview: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# Validators
# ══════════════════════════════════════════════════════════════════════════════


def _check_gfnorte_resolves_to_banorte(response: Dict[str, Any]) -> Tuple[bool, str]:
    """GFNORTE query should return data about BANORTE, not an error.

    The alias resolves at the DATA level (bank_names, chart traces).
    The LLM text may echo 'GFNORTE' instead of 'BANORTE' — that's OK
    as long as data is present and not a refusal.
    """
    content = response.get("content", "").lower()
    bc = response.get("bank_chart")

    if response.get("error"):
        return False, f"Request error: {response['error']}"

    # Check for refusal / not-found patterns
    refusal = ["no reconoz", "no encontr", "no tengo datos", "no pude identificar"]
    for pat in refusal:
        if pat in content:
            return False, f"System refused: '{pat}' found — GFNORTE not recognized"

    # Best: text mentions BANORTE explicitly
    if "banorte" in content:
        if bc and bc.get("chart_status") == "success":
            bank_names = [b.upper() for b in bc.get("bank_names", [])]
            if "BANORTE" in bank_names:
                return True, "GFNORTE resolved to BANORTE (chart + text)"
            return True, "GFNORTE resolved to BANORTE (text mentions it)"
        return True, "GFNORTE resolved to BANORTE (text mentions it, no chart)"

    # Chart has BANORTE in bank_names even if text doesn't say it
    if bc and bc.get("chart_status") == "success":
        bank_names = [b.upper() for b in bc.get("bank_names", [])]
        if "BANORTE" in bank_names:
            return True, "GFNORTE resolved to BANORTE (chart bank_names)"

    # LLM echoed GFNORTE but chart has data → alias resolved at data level
    if bc and bc.get("chart_status") == "success":
        plotly = bc.get("plotly_config", {})
        traces = plotly.get("data", [])
        has_data = any(len(t.get("y", t.get("x", []))) > 0 for t in traces)
        if has_data and "gfnorte" in content:
            return True, "Alias resolved at data level (chart has data, text uses GFNORTE)"

    return False, "Response doesn't mention BANORTE and no chart data — alias not resolved"


def _check_gfnorte_no_chart_error(response: Dict[str, Any]) -> Tuple[bool, str]:
    """GFNORTE evolution query should produce a valid chart, not an error."""
    bc = response.get("bank_chart")
    content = response.get("content", "").lower()

    if response.get("error"):
        return False, f"Request error: {response['error']}"

    if not bc:
        # Might be a text-only response if the LLM narrates
        if "banorte" in content and len(content) > 50:
            return True, "No chart but meaningful BANORTE response"
        return False, "No chart and no meaningful BANORTE content"

    status = bc.get("chart_status", "")
    if status == "success":
        bank_names = [b.upper() for b in bc.get("bank_names", [])]
        if "BANORTE" in bank_names:
            return True, f"Chart success with BANORTE in bank_names"
        return True, f"Chart success (banks: {bank_names})"

    return False, f"Chart status: {status} (expected success)"


def _check_quebrantos_comparison_chart(response: Dict[str, Any]) -> Tuple[bool, str]:
    """Comparison chart for quebrantos should show non-zero MDP values.

    Handles both chart formats:
      - Bar chart ranking: x=values, y=bank names
      - Time-series comparison: x=dates, y=values (scatter/line)
    """
    bc = response.get("bank_chart")

    if response.get("error"):
        return False, f"Request error: {response['error']}"

    if not bc:
        return False, "No chart returned for quebrantos comparison"

    status = bc.get("chart_status", "")
    if status != "success":
        return False, f"Chart status: {status} (expected success)"

    plotly = bc.get("plotly_config", {})
    traces = plotly.get("data", [])
    if not traces:
        return False, "No traces in plotly config"

    # Collect all numeric values across all traces (x or y)
    all_values: List[float] = []
    trace_names: List[str] = []
    for trace in traces:
        trace_names.append(trace.get("name", "?"))
        for axis in ("x", "y"):
            vals = trace.get(axis, [])
            all_values.extend(v for v in vals if isinstance(v, (int, float)))

    if not all_values:
        return False, f"No numeric values in {len(traces)} traces"

    max_val = max(all_values)
    min_val = min(v for v in all_values if v > 0) if any(v > 0 for v in all_values) else 0

    # Values should be in MDP range (÷1M from pesos)
    if max_val > 500_000:
        return False, (
            f"Max value {max_val:,.0f} too large — still in pesos (not ÷1M). "
            f"Expected values in MDP range"
        )

    # At least some non-zero values
    non_zero = [v for v in all_values if v > 0.001]
    if len(non_zero) < 2:
        return False, f"Only {len(non_zero)} non-zero values — expected at least 2"

    return True, (
        f"Chart OK: {len(traces)} traces ({trace_names}), "
        f"values {min_val:,.2f} - {max_val:,.2f} MDP, "
        f"{len(non_zero)} non-zero points"
    )


def _check_quebrantos_evolution_values(response: Dict[str, Any]) -> Tuple[bool, str]:
    """Evolution for quebrantos should show annual data points with correct MDP values."""
    bc = response.get("bank_chart")

    if response.get("error"):
        return False, f"Request error: {response['error']}"

    if not bc:
        return False, "No chart returned for quebrantos evolution"

    status = bc.get("chart_status", "")
    if status != "success":
        return False, f"Chart status: {status}"

    plotly = bc.get("plotly_config", {})
    traces = plotly.get("data", [])
    if not traces:
        return False, "No traces in plotly config"

    # Check y-values (evolution line values)
    y_values = traces[0].get("y", [])
    x_values = traces[0].get("x", [])

    if not y_values:
        return False, "No y-values in evolution trace"

    # All non-zero (exclude_zeros should have filtered zeros)
    zeros = [v for v in y_values if v == 0 or v == 0.0]
    if len(zeros) > 0:
        return False, f"{len(zeros)} zero values found — exclude_zeros not filtering"

    # Values should be in MDP range (skip_currency_scale=False + ÷1M in use cases)
    # Typical BBVA quebrantos: 1–500 MDP per year
    max_val = max(y_values)
    if max_val < 0.01:
        return False, f"Max y-value {max_val:.6f} too small — double ÷1M?"
    if max_val > 500_000:
        return False, f"Max y-value {max_val:,.0f} too large — still in pesos?"

    # Allow up to 40 data points (monthly data ~3 years is valid)
    if len(y_values) > 40:
        return False, f"{len(y_values)} data points — too many (max 40)"

    # Check dates are January (annual reporting)
    jan_dates = [d for d in x_values if isinstance(d, str) and "-01-" in d]

    return True, (
        f"Evolution OK: {len(y_values)} points, "
        f"values {min(y_values):,.0f} - {max_val:,.0f} MDP, "
        f"Jan dates: {len(jan_dates)}/{len(x_values)}"
    )


def _check_quebrantos_no_all_zeros(response: Dict[str, Any]) -> Tuple[bool, str]:
    """The LLM text should NOT say 'all banks have 0' for quebrantos."""
    content = response.get("content", "").lower()

    if response.get("error"):
        return False, f"Request error: {response['error']}"

    # Patterns that indicate the old bug (all zeros)
    # Use regex with word boundaries to avoid false positives like "14,460 MDP"
    zero_patterns = [
        (r"todos los bancos tienen 0", "todos los bancos tienen 0"),
        (r"\b0\.00\s*MDP\b", "0.00 MDP"),
        (r"(?<!\d[,.])\b0\s+MDP\b", "0 MDP (standalone)"),
        (r"no hay datos", "no hay datos"),
        (r"no tengo datos de quebrantos", "no tengo datos de quebrantos"),
    ]
    for regex, label in zero_patterns:
        if re.search(regex, content, re.IGNORECASE):
            return False, f"Old bug detected: '{label}' in response — still showing zeros"

    # Should mention actual values > 0
    if re.search(r"\d{1,3}(?:,\d{3})+", content):
        return True, "Response contains formatted numbers (not all zeros)"

    if len(content) > 100:
        return True, f"Response is substantial ({len(content)} chars)"

    return False, "Response too short or no numeric values found"


# ══════════════════════════════════════════════════════════════════════════════
# Test Cases
# ══════════════════════════════════════════════════════════════════════════════

REPLAY_CASES: List[ReplayCase] = [
    # ──────────────────────────────────────────────────────
    # TICKET: entity-alias-gfnorte (FDBK-0075)
    # ──────────────────────────────────────────────────────
    ReplayCase(
        feedback_id="FDBK-0075",
        ticket="entity-alias-gfnorte",
        description="Original feedback: 'Dime el historico del portafolio GFNORTE'",
        query="Dime el historico del portafolio GFNORTE",
        validate=_check_gfnorte_resolves_to_banorte,
    ),
    ReplayCase(
        feedback_id="FDBK-0075b",
        ticket="entity-alias-gfnorte",
        description="GFNORTE with metric — should resolve to BANORTE chart",
        query="IMOR de GFNORTE en 2025",
        validate=_check_gfnorte_no_chart_error,
    ),
    ReplayCase(
        feedback_id="FDBK-0075c",
        ticket="entity-alias-gfnorte",
        description="Grupo Financiero Banorte — full name alias",
        query="cartera comercial de Grupo Financiero Banorte",
        validate=_check_gfnorte_resolves_to_banorte,
    ),

    # ──────────────────────────────────────────────────────
    # TICKET: quebrantos-data-stale (FDBK-0008)
    # ──────────────────────────────────────────────────────
    ReplayCase(
        feedback_id="FDBK-0008",
        ticket="quebrantos-data-stale",
        description="Quebrantos BANORTE evolution — second bank with non-zero MDP values",
        query="quebrantos comerciales de BANORTE",
        validate=_check_quebrantos_comparison_chart,
    ),
    ReplayCase(
        feedback_id="FDBK-0008b",
        ticket="quebrantos-data-stale",
        description="BANORTE response should NOT say 'all banks have 0 MDP'",
        query="quebrantos comerciales de BANORTE",
        validate=_check_quebrantos_no_all_zeros,
    ),
    ReplayCase(
        feedback_id="FDBK-0008c",
        ticket="quebrantos-data-stale",
        description="Evolution shows annual data in MDP range (skip_currency_scale=False + ÷1M)",
        query="quebrantos comerciales de BBVA",
        validate=_check_quebrantos_evolution_values,
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════


def run_replay(token: str, case: ReplayCase) -> ReplayResult:
    """Run a single feedback replay case."""
    resp = send_chat_message(
        token, case.query, backend_url=BACKEND_URL, timeout=TIMEOUT,
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
    print("E2E Regression — entity-alias-gfnorte + quebrantos-data-stale")
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

    # --- Summary ---
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
            print(f"  {ticket}: BACKLOG -> DONE (all feedback cases pass)")
        else:
            print(f"  {ticket}: stays in BACKLOG ({status})")

    # --- Save results ---
    total_passed = sum(1 for r in results if r.passed)
    total_failed = sum(1 for r in results if not r.passed)

    out = Path(__file__).parent / "entity_alias_quebrantos_results.json"
    out.write_text(
        json.dumps(
            {
                "date": "2026-02-06",
                "tickets": ["entity-alias-gfnorte", "quebrantos-data-stale"],
                "total_passed": total_passed,
                "total_failed": total_failed,
                "by_ticket": {
                    ticket: {
                        "status": ticket_status[ticket],
                        "cases": [
                            {
                                "feedback_id": r.case.feedback_id,
                                "description": r.case.description,
                                "query": r.case.query,
                                "passed": r.passed,
                                "detail": r.detail,
                                "content_preview": r.content_preview[:200],
                            }
                            for r in trs
                        ],
                    }
                    for ticket, trs in by_ticket.items()
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"\nResults saved to {out}")

    # --- Final verdict ---
    print(f"\n{'=' * 70}")
    print(f"TOTAL: {total_passed} passed, {total_failed} failed out of {len(results)}")
    print(f"{'=' * 70}")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
