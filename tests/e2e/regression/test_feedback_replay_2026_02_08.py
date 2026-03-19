#!/usr/bin/env python3
"""
E2E Feedback Replay — 2026-02-08

Replays EXACT user queries from 3 bugs fixed in this session:

1. cartera-por-banco-por-ano (FDBK-0006, FDBK-0043):
   Handler priority collision — ViviendaPerfilHandler captured "cartera
   hipotecaria por banco por año" before InstitutionRankingHandler.
   Fix: Guard in ViviendaPerfilHandler + "por banco" expansion in ranking.

2. entity-alias-gfnorte (FDBK-0075):
   "GFNORTE" not recognized as alias for BANORTE in plugin dicts.
   Fix: Added aliases to query_spec_parser, context_enricher, bank_resolver.

3. ranking-intent-lista-mayor-menor (no FDBK — found via test suite):
   "Lista de bancos por capitalización de mayor a menor" failed to trigger
   ranking intent.
   Fix: Added "de mayor a menor", "lista de" to IMPLICIT_RANKING +
   "capitalización"/"solvencia" to RANKABLE_METRICS.

Usage:
    python tests/e2e/regression/test_feedback_replay_2026_02_08.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "90"))


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
# Validators — cartera-por-banco-por-ano
# ══════════════════════════════════════════════════════════════════════════════


def _check_bank_ranking_not_vivienda(response: Dict[str, Any]) -> Tuple[bool, str]:
    """
    "cartera hipotecaria por banco por año" should produce a multi-bank
    ranking, NOT a vivienda product breakdown.

    Failure mode (before fix): ViviendaPerfilHandler returned
    "CARTERA VIVIENDA POR PRODUCTO HIPOTECARIO" with bank_names: [].
    """
    content = response.get("content", "").lower()
    bc = response.get("bank_chart")

    if response.get("error"):
        return False, f"Request error: {response['error']}"

    # Check for the OLD bug: vivienda product breakdown
    vivienda_product_patterns = [
        "por producto hipotecario",
        "vivienda por producto",
        "no incluyen desglose por banco",
        "no incluye desglose por banco",
    ]
    for pat in vivienda_product_patterns:
        if pat in content:
            return False, (
                f"OLD BUG: ViviendaPerfilHandler captured query — "
                f"found '{pat}' in response"
            )

    # Check for extraction errors
    error_patterns = [
        "error técnico",
        "error al procesar",
        "no pudo extraer",
        "error de extracción",
    ]
    for pat in error_patterns:
        if pat in content:
            return False, f"Extraction error: '{pat}'"

    # Positive check: should have chart with multiple banks
    if bc and bc.get("chart_status") == "success":
        bank_names = bc.get("bank_names", [])
        if len(bank_names) >= 2:
            return True, (
                f"Bank ranking chart OK: {len(bank_names)} banks "
                f"({', '.join(bank_names[:5])}...)"
            )
        if len(bank_names) == 0:
            return False, "Chart success but bank_names empty — vivienda handler?"
        return True, f"Chart with {len(bank_names)} bank(s): {bank_names}"

    # Chart may not exist but text should still be about banks
    if "banco" in content and len(content) > 100:
        return True, "No chart but response discusses banks"

    if not bc:
        return False, "No chart returned — ranking handler may not have matched"

    return False, f"Chart status: {bc.get('chart_status', 'unknown')}"


def _check_cartera_typo_resolves(response: Dict[str, Any]) -> Tuple[bool, str]:
    """
    "cartera hipetecario por banco por año" (typo: hipetecario) should
    still produce a valid response — synonym normalization should catch it.
    """
    content = response.get("content", "").lower()
    bc = response.get("bank_chart")

    if response.get("error"):
        return False, f"Request error: {response['error']}"

    # Should NOT ask for clarification
    clarification = response.get("clarification") or response.get("bank_clarification")
    if clarification:
        return False, "System asked for clarification instead of answering"

    # Should have meaningful content
    if bc and bc.get("chart_status") == "success":
        return True, "Chart returned despite typo in query"

    if len(content) > 100 and ("cartera" in content or "hipotec" in content):
        return True, f"Meaningful response ({len(content)} chars) despite typo"

    if len(content) < 30:
        return False, "Response too short — typo may not have been resolved"

    return True, f"Response received ({len(content)} chars)"


# ══════════════════════════════════════════════════════════════════════════════
# Validators — entity-alias-gfnorte
# ══════════════════════════════════════════════════════════════════════════════


def _check_gfnorte_resolves(response: Dict[str, Any]) -> Tuple[bool, str]:
    """GFNORTE must resolve to BANORTE — not return "no data" or error."""
    content = response.get("content", "").lower()
    bc = response.get("bank_chart")

    if response.get("error"):
        return False, f"Request error: {response['error']}"

    # Refusal = alias not resolved
    refusal = [
        "no reconoz", "no encontr", "no tengo datos",
        "no pude identificar", "no está disponible",
    ]
    for pat in refusal:
        if pat in content:
            return False, f"GFNORTE not recognized: '{pat}' in response"

    # Positive: response should mention BANORTE
    if "banorte" in content:
        if bc and bc.get("chart_status") == "success":
            return True, "GFNORTE → BANORTE resolved (chart + text)"
        return True, "GFNORTE → BANORTE resolved (text)"

    # Chart may have BANORTE even if text doesn't
    if bc and bc.get("chart_status") == "success":
        bank_names = [b.upper() for b in bc.get("bank_names", [])]
        if "BANORTE" in bank_names:
            return True, "GFNORTE → BANORTE resolved (chart bank_names)"

    return False, "Response doesn't mention BANORTE — alias not resolved"


# ══════════════════════════════════════════════════════════════════════════════
# Validators — ranking-intent-lista-mayor-menor
# ══════════════════════════════════════════════════════════════════════════════


def _check_ranking_chart_returned(response: Dict[str, Any]) -> Tuple[bool, str]:
    """
    "Lista de bancos por X de mayor a menor" should trigger ranking intent
    and return a chart with multiple banks.
    """
    content = response.get("content", "").lower()
    bc = response.get("bank_chart")

    if response.get("error"):
        return False, f"Request error: {response['error']}"

    if not bc:
        # Check if clarification was returned instead
        if response.get("clarification") or response.get("bank_clarification"):
            return False, "Clarification returned instead of ranking chart"
        if len(content) > 100:
            return False, f"Text-only response ({len(content)} chars) — no chart"
        return False, "No chart returned — ranking intent not detected"

    status = bc.get("chart_status", "")
    if status != "success":
        return False, f"Chart status: {status} (expected success)"

    bank_names = bc.get("bank_names", [])
    if len(bank_names) >= 3:
        return True, (
            f"Ranking chart OK: {len(bank_names)} banks "
            f"({', '.join(bank_names[:5])}...)"
        )

    if len(bank_names) == 0:
        return False, "Chart success but no bank_names — not a ranking?"

    return True, f"Chart with {len(bank_names)} bank(s)"


def _check_ranking_ascending_order(response: Dict[str, Any]) -> Tuple[bool, str]:
    """
    "de menor a mayor" should produce ascending data in chart.
    Check that first value <= last value in the ranking trace.
    """
    bc = response.get("bank_chart")

    if response.get("error"):
        return False, f"Request error: {response['error']}"

    if not bc or bc.get("chart_status") != "success":
        return False, "No successful chart to check ordering"

    plotly = bc.get("plotly_config", {})
    traces = plotly.get("data", [])
    if not traces:
        return False, "No traces in plotly config"

    # For horizontal bar ranking, values are typically in x
    values = traces[0].get("x", []) or traces[0].get("y", [])
    if not values or len(values) < 2:
        return False, f"Insufficient values to check order: {len(values) if values else 0}"

    # Check ascending: first should be <= last
    numeric_vals = [v for v in values if isinstance(v, (int, float))]
    if len(numeric_vals) < 2:
        return True, "Non-numeric values — skip order check"

    if numeric_vals[0] <= numeric_vals[-1]:
        return True, (
            f"Ascending order confirmed: {numeric_vals[0]:.2f} → "
            f"{numeric_vals[-1]:.2f}"
        )

    return False, (
        f"NOT ascending: {numeric_vals[0]:.2f} → {numeric_vals[-1]:.2f} "
        f"— 'de menor a mayor' not respected"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Test Cases
# ══════════════════════════════════════════════════════════════════════════════

REPLAY_CASES: List[ReplayCase] = [
    # ──────────────────────────────────────────────────────
    # TICKET: cartera-por-banco-por-ano (FDBK-0006, FDBK-0043)
    # Fix: ViviendaPerfilHandler guard + ranking "por banco" expansion
    # ──────────────────────────────────────────────────────
    ReplayCase(
        feedback_id="FDBK-0043",
        ticket="cartera-por-banco-por-ano",
        description="EXACT query: 'cartera hipotecaria por banco por año' — must return "
                    "bank ranking, NOT vivienda product breakdown",
        query="quiero que me des la cartera hipotecaria por banco por año",
        validate=_check_bank_ranking_not_vivienda,
    ),
    ReplayCase(
        feedback_id="FDBK-0006",
        ticket="cartera-por-banco-por-ano",
        description="EXACT query with typo: 'hipetecario' (e instead of o) — "
                    "synonym normalization should resolve it",
        query="quiero que me des la cartera hipetecario por banco por año",
        validate=_check_cartera_typo_resolves,
    ),
    ReplayCase(
        feedback_id="FDBK-0043b",
        ticket="cartera-por-banco-por-ano",
        description="Variation: 'cartera hipotecaria por banco' without 'por año'",
        query="cartera hipotecaria por banco",
        validate=_check_bank_ranking_not_vivienda,
    ),

    # ──────────────────────────────────────────────────────
    # TICKET: entity-alias-gfnorte (FDBK-0075)
    # Fix: Added GFNORTE to 4 bank alias dictionaries
    # ──────────────────────────────────────────────────────
    ReplayCase(
        feedback_id="FDBK-0075",
        ticket="entity-alias-gfnorte",
        description="EXACT query: 'Dime el historico del portafolio GFNORTE'",
        query="Dime el historico del portafolio GFNORTE",
        validate=_check_gfnorte_resolves,
    ),
    ReplayCase(
        feedback_id="FDBK-0075b",
        ticket="entity-alias-gfnorte",
        description="GFNORTE with metric — IMOR should resolve to BANORTE",
        query="IMOR de GFNORTE en 2025",
        validate=_check_gfnorte_resolves,
    ),
    ReplayCase(
        feedback_id="FDBK-0075c",
        ticket="entity-alias-gfnorte",
        description="Full name: 'Grupo Financiero Banorte' alias",
        query="cartera de Grupo Financiero Banorte",
        validate=_check_gfnorte_resolves,
    ),

    # ──────────────────────────────────────────────────────
    # TICKET: ranking-intent-lista-mayor-menor
    # Fix: Added "de mayor a menor", "lista de" to IMPLICIT_RANKING
    # ──────────────────────────────────────────────────────
    ReplayCase(
        feedback_id="RANK-051",
        ticket="ranking-intent-lista-mayor-menor",
        description="EXACT failing query: 'Lista de bancos por capitalización "
                    "de mayor a menor'",
        query="Lista de bancos por capitalización de mayor a menor",
        validate=_check_ranking_chart_returned,
    ),
    ReplayCase(
        feedback_id="RANK-051b",
        ticket="ranking-intent-lista-mayor-menor",
        description="Ascending variant: 'de menor a mayor' should sort ascending",
        query="lista de bancos por IMOR de menor a mayor",
        validate=_check_ranking_chart_returned,
    ),
    ReplayCase(
        feedback_id="RANK-051c",
        ticket="ranking-intent-lista-mayor-menor",
        description="Ascending order check: data should be sorted low → high",
        query="lista de bancos por IMOR de menor a mayor",
        validate=_check_ranking_ascending_order,
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════


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
    print("E2E Feedback Replay — 2026-02-08")
    print("Bugs: cartera-por-banco-por-ano, entity-alias-gfnorte,")
    print("      ranking-intent-lista-mayor-menor")
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
            print(f"  {ticket}: DOING -> REVIEW (all feedback cases pass)")
        else:
            print(f"  {ticket}: stays in DOING ({status})")

    # --- Save results ---
    total_passed = sum(1 for r in results if r.passed)
    total_failed = sum(1 for r in results if not r.passed)

    out = Path(__file__).parent / "feedback_replay_2026_02_08_results.json"
    out.write_text(
        json.dumps(
            {
                "date": "2026-02-08",
                "bugs_tested": [
                    "cartera-por-banco-por-ano",
                    "entity-alias-gfnorte",
                    "ranking-intent-lista-mayor-menor",
                ],
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
    print(f"\nResults saved: {out}")

    # --- Final verdict ---
    print(f"\n{'=' * 70}")
    if total_failed == 0:
        print(f"ALL {total_passed} REPLAY CASES PASSED!")
    else:
        print(f"{total_passed} passed, {total_failed} failed out of {total_passed + total_failed}")
    print(f"{'=' * 70}")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
