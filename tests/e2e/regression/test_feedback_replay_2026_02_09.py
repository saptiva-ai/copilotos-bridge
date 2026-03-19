#!/usr/bin/env python3
"""
E2E Feedback Replay — 2026-02-09

Replays EXACT multi-turn conversations from the feedback triage report to
verify bug fixes and document known open issues.

Source: docs/reports/feedback_triage/2026-02-09.md

Conversations replayed:
  1. STALE_CHART (conv 84ba1397): 5-turn session testing year-filtered
     charts and bank state isolation between turns.
  2. CATALOG_MISS + CATALOG_FALLBACK (conv 2aacb224): 7-turn session
     testing catalog fast-path lookups, IXE/Monex misses, and content
     persistence after our fix.

Bug clusters:
  - STALE_CHART      (S0)  — SQL missing date filter for year queries
  - STATE_LEAK       (S1)  — bank names from prior turn leak into current
  - CATALOG_FALLBACK (S1)  — message.content gets generic template (FIXED)
  - CATALOG_MISS     (S2)  — IXE not in lookup, Monex bypasses catalog
  - MONEX_HALLUC     (S1)  — LLM hallucinates wrong code for Monex

Usage:
    python tests/e2e/regression/test_feedback_replay_2026_02_09.py
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

# Known correct bank codes (from bank_dim_institucion + CNBV catalog)
BANK_CODES = {
    "INVEX": "0000040059",
    "BBVA": "0000040012",
    "BANORTE": "0000040072",
    "SCOTIABANK": "0000040044",
    "SANTANDER": "0000040014",
    "CIBANCO": "0000040143",
    "AFIRME": "0000040062",
    "BANAMEX": "0000040002",
    "IXE": "0000040032",
    "MONEX": "0000040112",
    "MIZUHO": "0000040158",
}

# Generic template phrases that indicate CATALOG_FALLBACK bug
GENERIC_TEMPLATE_PHRASES = [
    "a continuación se presentan los datos",
    "revisa la gráfica y la tabla adjunta",
    "la métrica solicitada",
]


@dataclass
class ConversationStep:
    """A single step in a multi-turn conversation replay."""

    step_id: str
    feedback_id: str
    ticket: str
    query: str
    validate: Callable[[Dict[str, Any]], Tuple[bool, str]]
    description: str = ""


@dataclass
class StepResult:
    """Result of executing one conversation step."""

    step: ConversationStep
    passed: bool
    detail: str
    content_preview: str = ""
    chart_summary: Optional[str] = None


@dataclass
class ConversationReplay:
    """A full multi-turn conversation to replay."""

    name: str
    original_conv_id: str
    description: str
    steps: List[ConversationStep]


# ══════════════════════════════════════════════════════════════════════════════
# Validators — STALE_CHART (year filter in chart data)
# ══════════════════════════════════════════════════════════════════════════════


def _extract_x_range(response: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """Extract (first_date, last_date) from chart plotly data."""
    bc = response.get("bank_chart")
    if not bc:
        return None
    plotly = bc.get("plotly_config", {})
    traces = plotly.get("data", [])
    if not traces:
        return None
    x_vals = traces[0].get("x", [])
    if not x_vals:
        return None
    return (x_vals[0], x_vals[-1])


def _extract_trace_names(response: Dict[str, Any]) -> List[str]:
    """Extract bank/trace names from chart data."""
    bc = response.get("bank_chart")
    if not bc:
        return []
    # Direct bank_names field
    names = bc.get("bank_names", [])
    if names:
        return [n.upper() for n in names]
    # Fallback: extract from plotly traces
    plotly = bc.get("plotly_config", {})
    traces = plotly.get("data", [])
    return [t.get("name", "").upper() for t in traces if t.get("name")]


def _check_chart_2024_baseline(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """Step 1: cartera comercial de INVEX en 2024 — baseline, should work."""
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned for baseline 2024 query"

    x_range = _extract_x_range(resp)
    if not x_range:
        return False, "No x values in chart"

    first, last = x_range
    if "2024" in first:
        return True, f"Baseline OK: x_range=[{first}, {last}]"

    return False, f"Unexpected x_range=[{first}, {last}] — expected 2024 data"


def _check_chart_has_2025(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """Chart x_range must include 2025 dates (not stale 2024 data)."""
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned — expected chart with 2025 data"

    x_range = _extract_x_range(resp)
    if not x_range:
        return False, "No x values in chart"

    first, last = x_range
    has_2025 = "2025" in first or "2025" in last

    if has_2025:
        return True, f"Chart includes 2025: x_range=[{first}, {last}]"

    return False, (
        f"STALE_CHART: x_range=[{first}, {last}] — "
        f"no 2025 data despite user requesting 2025"
    )


def _check_chart_has_2024_and_2025(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """Chart should span both 2024 and 2025 for comparison query."""
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned for 2024+2025 comparison"

    x_range = _extract_x_range(resp)
    if not x_range:
        return False, "No x values in chart"

    first, last = x_range
    has_2024 = "2024" in first
    has_2025 = "2025" in last

    if has_2024 and has_2025:
        return True, f"Both years present: x_range=[{first}, {last}]"

    return False, (
        f"STALE_CHART: x_range=[{first}, {last}] — "
        f"expected 2024→2025 span"
    )


def _check_chart_2025_two_banks_no_leak(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Chart should have exactly 2 requested banks in 2025, no state leak.
    For SC-5: INVEX + BANREGIO only, no INBURSA from prior turn.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned"

    trace_names = _extract_trace_names(resp)
    x_range = _extract_x_range(resp)

    issues = []

    # Check for state leak: INBURSA should NOT be present
    if "INBURSA" in trace_names:
        issues.append(
            f"STATE_LEAK: INBURSA present in traces {trace_names} — "
            f"leaked from prior turn"
        )

    # Check correct banks present
    expected = {"INVEX", "BANREGIO"}
    actual = set(trace_names)
    missing = expected - actual
    if missing:
        issues.append(f"Missing banks: {missing}")

    # Check year
    if x_range:
        first, last = x_range
        if "2025" not in first and "2025" not in last:
            issues.append(f"STALE_CHART: x_range=[{first}, {last}], no 2025")

    if issues:
        return False, " | ".join(issues)

    return True, (
        f"Correct: {trace_names}, x_range=[{x_range[0]}, {x_range[1]}]"
        if x_range
        else f"Correct banks: {trace_names}"
    )


def _check_chart_2025_inbursa_invex(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """SC-4: Inbursa vs INVEX in 2025 — check 2 traces with 2025 data."""
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned"

    trace_names = _extract_trace_names(resp)
    x_range = _extract_x_range(resp)

    expected = {"INVEX", "INBURSA"}
    actual = set(trace_names)
    missing = expected - actual

    issues = []
    if missing:
        issues.append(f"Missing banks: {missing} (got {actual})")

    if x_range:
        first, last = x_range
        if "2025" not in first and "2025" not in last:
            issues.append(f"STALE_CHART: x_range=[{first}, {last}], no 2025")

    if issues:
        return False, " | ".join(issues)

    range_str = f", x=[{x_range[0]}..{x_range[1]}]" if x_range else ""
    return True, f"Correct: {trace_names}{range_str}"


# ══════════════════════════════════════════════════════════════════════════════
# Validators — CATALOG fast path (content persistence, lookups)
# ══════════════════════════════════════════════════════════════════════════════


def _has_generic_template(content: str) -> bool:
    """Check if content contains the generic template from CATALOG_FALLBACK bug."""
    lower = content.lower()
    return any(phrase in lower for phrase in GENERIC_TEMPLATE_PHRASES)


def _check_catalog_banamex(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """Step 1: 'dame la clave institucional de banamex' → 0000040002."""
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    content = resp.get("content", "")

    if _has_generic_template(content):
        return False, "CATALOG_FALLBACK: generic template in content"

    if "0000040002" in content or "040002" in content:
        return True, "Correct: BANAMEX code 0000040002 found"

    if "banamex" in content.lower() and ("clave" in content.lower() or "código" in content.lower()):
        return True, f"Response discusses BANAMEX code ({len(content)} chars)"

    return False, f"Code 0000040002 not found in response ({len(content)} chars)"


def _check_catalog_ixe_e_invex(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Step 2: 'cual es la clave de ixe e invex?' — multi-bank with 'e' separator.
    IXE was absorbed by BANORTE in 2014 → alias resolves to BANORTE (040072).
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    content = resp.get("content", "")

    if _has_generic_template(content):
        return False, "CATALOG_FALLBACK: generic template in content"

    has_invex = "0000040059" in content or "040059" in content
    # IXE → BANORTE alias: accept either the historical code or the alias target
    has_ixe_or_banorte = (
        "0000040032" in content or "040032" in content
        or "0000040072" in content or "040072" in content
    )

    if has_invex and has_ixe_or_banorte:
        return True, "Both banks resolved: IXE→BANORTE(040072) + INVEX(040059)"

    if has_invex:
        return False, (
            "PARTIAL: INVEX found but IXE/BANORTE missing — "
            "'e' separator or alias lookup issue"
        )

    # Known: treated as single lookup "ixe e invex"
    if "no encontr" in content.lower() or "no se encontr" in content.lower():
        return False, (
            "CATALOG_MISS: 'ixe e invex' treated as single name — "
            "'e' separator not parsed"
        )

    return False, f"Neither code found ({len(content)} chars)"


def _check_catalog_ixe_solo(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Step 3: 'cual es la clave de Ixe?'
    IXE was absorbed by BANORTE in 2014 → alias resolves to BANORTE (040072).
    Accept either historical code 040032 or alias target code 040072.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    content = resp.get("content", "")

    if _has_generic_template(content):
        return False, "CATALOG_FALLBACK: generic template in content"

    # Accept either historical IXE code or BANORTE alias code
    if "0000040032" in content or "040032" in content:
        return True, "Correct: IXE historical code 0000040032 found"

    if "0000040072" in content or "040072" in content:
        return True, "Correct: IXE→BANORTE alias resolved (code 0000040072)"

    if "no encontr" in content.lower() or "no se encontr" in content.lower():
        return False, "CATALOG_MISS: IXE not in lookup table and alias not applied"

    return False, f"Neither IXE(040032) nor BANORTE(040072) code found ({len(content)} chars)"


def _check_catalog_invex(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """Step 4: 'cual es la clave de Invex?' → 0000040059."""
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    content = resp.get("content", "")

    if _has_generic_template(content):
        return False, "CATALOG_FALLBACK: generic template in content"

    if "0000040059" in content or "040059" in content:
        return True, "Correct: INVEX code 0000040059 found"

    return False, f"Code 0000040059 not found ({len(content)} chars)"


def _check_catalog_reverse_040032(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Step 5: 'a que banco pertenece la clave 040032' → IXE.
    Known issues: IXE not in lookup + CATALOG_FALLBACK was replacing content.
    After fix: content should NOT be generic template.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    content = resp.get("content", "")

    # PRIMARY CHECK: CATALOG_FALLBACK bug — content must NOT be generic template
    if _has_generic_template(content):
        return False, (
            "CATALOG_FALLBACK: content is generic template — "
            "post-processor replaced catalog response (BUG NOT FIXED)"
        )

    # If we get here, the CATALOG_FALLBACK fix is working
    if "ixe" in content.lower() or "040032" in content:
        return True, "Correct: IXE identified for code 040032"

    # Catalog returns "no se encontró" — this is the correct catalog response
    # being preserved (fix working), even though IXE is missing from lookup
    if "no se encontr" in content.lower() or "no encontr" in content.lower():
        return True, (
            "CATALOG_FALLBACK fix confirmed: catalog 'not found' response "
            "preserved in content (IXE still missing from lookup)"
        )

    return False, f"Unexpected content ({len(content)} chars)"


def _check_catalog_monex(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Step 6: 'cual es la de monex?' → 0000040112 (Banco Monex).
    Known issue: query bypasses catalog, LLM hallucinates 0000040158 (MIZUHO).
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    content = resp.get("content", "")

    if _has_generic_template(content):
        return False, "CATALOG_FALLBACK: generic template in content"

    # Correct code
    if "0000040112" in content or "040112" in content:
        return True, "Correct: MONEX code 0000040112 found"

    # Wrong code — hallucinated MIZUHO's code
    if "0000040158" in content or "040158" in content:
        return False, (
            "MONEX_HALLUC: LLM returned 0000040158 (MIZUHO) instead of "
            "0000040112 (MONEX) — query bypassed catalog fast path"
        )

    # Other response
    if "monex" in content.lower():
        return False, f"Mentions Monex but code 040112 not found ({len(content)} chars)"

    return False, f"No Monex info in response ({len(content)} chars)"


def _check_catalog_reverse_040158(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Step 7: 'a que banco pertenece la clave 040158?' → MIZUHO BANK.
    This verifies 040158 = MIZUHO (not Monex).
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    content = resp.get("content", "")

    if _has_generic_template(content):
        return False, "CATALOG_FALLBACK: generic template in content"

    if "mizuho" in content.lower():
        return True, "Correct: 040158 → MIZUHO BANK confirmed"

    if "monex" in content.lower():
        return False, "WRONG: 040158 mapped to MONEX (should be MIZUHO)"

    return False, f"Neither MIZUHO nor MONEX found ({len(content)} chars)"


# ══════════════════════════════════════════════════════════════════════════════
# Conversation definitions
# ══════════════════════════════════════════════════════════════════════════════


CONV_STALE_CHART = ConversationReplay(
    name="stale-chart-state-leak",
    original_conv_id="84ba1397",
    description=(
        "5-turn conversation testing year-filtered charts. "
        "Reproduces STALE_CHART (SC-1 to SC-4) and STATE_LEAK."
    ),
    steps=[
        ConversationStep(
            step_id="SC-0",
            feedback_id="BASELINE",
            ticket="stale-chart",
            query="muestrame la cartera comercial de INVEX en 2024",
            validate=_check_chart_2024_baseline,
            description="Baseline: 2024 data should be correct",
        ),
        ConversationStep(
            step_id="SC-1",
            feedback_id="FDBK-0095",
            ticket="stale-chart",
            query="muestrame la cartera comercial de INVEX en 2025",
            validate=_check_chart_has_2025,
            description=(
                "STALE_CHART: user asks for 2025 but system returned 2024 data. "
                "SQL had no date filter."
            ),
        ),
        ConversationStep(
            step_id="SC-2",
            feedback_id="FDBK-0096",
            ticket="stale-chart",
            query="muéstrame una grafica comparando cartera comercial de INVEX de 2024 y 2025",
            validate=_check_chart_has_2024_and_2025,
            description="STALE_CHART: comparison query should span both years",
        ),
        ConversationStep(
            step_id="SC-3",
            feedback_id="FDBK-0097",
            ticket="stale-chart",
            query=(
                "muéstrame una gráfica comparando cartera comercial de "
                "Inbursa vs invex durante 2025"
            ),
            validate=_check_chart_2025_inbursa_invex,
            description="STALE_CHART: Inbursa vs INVEX in 2025 only",
        ),
        ConversationStep(
            step_id="SC-4",
            feedback_id="FDBK-0098",
            ticket="state-leak",
            query=(
                "quiero ver la cartera comercial de invex vs banregio "
                "únicamente en 2025"
            ),
            validate=_check_chart_2025_two_banks_no_leak,
            description=(
                "STATE_LEAK: only INVEX + BANREGIO requested, but INBURSA "
                "from prior turn leaked into SQL and chart"
            ),
        ),
    ],
)


CONV_CATALOG = ConversationReplay(
    name="catalog-miss-fallback",
    original_conv_id="2aacb224",
    description=(
        "7-turn conversation testing catalog fast-path lookups. "
        "Reproduces CATALOG_MISS (IXE, Monex) and CATALOG_FALLBACK."
    ),
    steps=[
        ConversationStep(
            step_id="CF-0",
            feedback_id="BASELINE",
            ticket="catalog-baseline",
            query="dame la clave institucional de banamex",
            validate=_check_catalog_banamex,
            description="Baseline: BANAMEX lookup should return 0000040002",
        ),
        ConversationStep(
            step_id="CF-1",
            feedback_id="FDBK-0100",
            ticket="catalog-miss-multi",
            query="cual es la clave de ixe e invex?",
            validate=_check_catalog_ixe_e_invex,
            description=(
                "CATALOG_MISS: 'e' not parsed as separator; "
                "IXE not in lookup table"
            ),
        ),
        ConversationStep(
            step_id="CF-2",
            feedback_id="FDBK-0102",
            ticket="catalog-miss-ixe",
            query="cual es la clave de Ixe?",
            validate=_check_catalog_ixe_solo,
            description="CATALOG_MISS: IXE (0000040032) not in lookup table",
        ),
        ConversationStep(
            step_id="CF-3",
            feedback_id="FDBK-INVEX",
            ticket="catalog-baseline",
            query="cual es la clave de Invex?",
            validate=_check_catalog_invex,
            description="Baseline: INVEX lookup should return 0000040059",
        ),
        ConversationStep(
            step_id="CF-4",
            feedback_id="FDBK-0103",
            ticket="catalog-fallback",
            query="a que banco pertenece la clave 040032",
            validate=_check_catalog_reverse_040032,
            description=(
                "CATALOG_FALLBACK: content was replaced with generic template. "
                "After fix: catalog response must be preserved in content."
            ),
        ),
        ConversationStep(
            step_id="CF-5",
            feedback_id="FDBK-0105",
            ticket="monex-hallucination",
            query="cual es la de monex?",
            validate=_check_catalog_monex,
            description=(
                "MONEX_HALLUC: 'cual es la de monex?' bypasses catalog, "
                "LLM hallucinated 0000040158 (MIZUHO) instead of 0000040112"
            ),
        ),
        ConversationStep(
            step_id="CF-6",
            feedback_id="FDBK-0106",
            ticket="catalog-baseline",
            query="a que banco pertenece la clave 040158?",
            validate=_check_catalog_reverse_040158,
            description="Verification: 040158 = MIZUHO BANK (proves Monex was wrong)",
        ),
    ],
)


CONVERSATIONS: List[ConversationReplay] = [CONV_STALE_CHART, CONV_CATALOG]


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════


def run_conversation(token: str, conv: ConversationReplay) -> List[StepResult]:
    """Run a full multi-turn conversation replay, preserving session."""
    results: List[StepResult] = []
    chat_id: Optional[str] = None

    print(f"\n{'─' * 70}")
    print(f"  CONVERSATION: {conv.name}")
    print(f"  Original: {conv.original_conv_id}")
    print(f"  {conv.description}")
    print(f"{'─' * 70}")

    for i, step in enumerate(conv.steps):
        print(f"\n  Step {i + 1}/{len(conv.steps)} [{step.step_id}] {step.description}")
        print(f"  Query: \"{step.query}\"")

        resp = send_chat_message(
            token,
            step.query,
            backend_url=BACKEND_URL,
            chat_id=chat_id,
            timeout=TIMEOUT,
        )

        # Extract chat_id for session continuity
        if not chat_id:
            meta = resp.get("meta")
            if meta and meta.get("chat_id"):
                chat_id = meta["chat_id"]
                print(f"  Session: {chat_id}")

        # Also try to get chat_id from 'extra' (done event)
        if not chat_id:
            extra = resp.get("extra", {})
            done_data = extra.get("done")
            if isinstance(done_data, dict):
                chat_id = done_data.get("chat_id")

        content = resp.get("content", "")
        passed, detail = step.validate(resp)

        # Build chart summary
        chart_summary = None
        bc = resp.get("bank_chart")
        if bc:
            x_range = _extract_x_range(resp)
            traces = _extract_trace_names(resp)
            chart_summary = (
                f"status={bc.get('chart_status', '?')}, "
                f"traces={traces}, "
                f"x_range=[{x_range[0]}, {x_range[1]}]"
                if x_range
                else f"status={bc.get('chart_status', '?')}, traces={traces}"
            )

        result = StepResult(
            step=step,
            passed=passed,
            detail=detail,
            content_preview=(
                content[:300].replace("\n", " ") if content else "(empty)"
            ),
            chart_summary=chart_summary,
        )
        results.append(result)

        tag = "PASSED" if passed else "FAILED"
        print(f"  {tag}: {detail}")
        if chart_summary:
            print(f"  Chart: {chart_summary}")
        if not passed and content:
            print(f"  Content: {content[:200].replace(chr(10), ' ')}")

    return results


def main() -> int:
    print("=" * 70)
    print("E2E Feedback Replay — 2026-02-09")
    print("Conversations: stale-chart-state-leak, catalog-miss-fallback")
    print("Source: docs/reports/feedback_triage/2026-02-09.md")
    print("=" * 70)

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FATAL: Auth failed")
        return 2

    print(f"Authenticated against {BACKEND_URL}")

    all_results: List[StepResult] = []
    by_ticket: Dict[str, List[StepResult]] = {}
    by_conversation: Dict[str, List[StepResult]] = {}

    for conv in CONVERSATIONS:
        conv_results = run_conversation(token, conv)
        all_results.extend(conv_results)
        by_conversation[conv.name] = conv_results

        for r in conv_results:
            by_ticket.setdefault(r.step.ticket, []).append(r)

    # ── Summary by ticket ──
    print(f"\n\n{'=' * 70}")
    print("SUMMARY BY TICKET")
    print(f"{'=' * 70}\n")

    ticket_status: Dict[str, str] = {}
    for ticket, ticket_results in by_ticket.items():
        passed = sum(1 for r in ticket_results if r.passed)
        total = len(ticket_results)
        all_passed = passed == total

        status = (
            "RESOLVED" if all_passed
            else f"PERSISTS ({total - passed}/{total} failing)"
        )
        ticket_status[ticket] = status

        icon = "RESOLVED" if all_passed else "PERSISTS"
        print(f"  [{icon}] {ticket}: {passed}/{total} passed")
        for r in ticket_results:
            tag = "OK" if r.passed else "FAIL"
            print(f"    [{tag}] {r.step.step_id}: {r.detail[:80]}")

    # ── Summary by conversation ──
    print(f"\n{'=' * 70}")
    print("SUMMARY BY CONVERSATION")
    print(f"{'=' * 70}\n")

    for conv_name, conv_results in by_conversation.items():
        passed = sum(1 for r in conv_results if r.passed)
        total = len(conv_results)
        print(f"  {conv_name}: {passed}/{total} steps passed")

    # ── Save results JSON ──
    total_passed = sum(1 for r in all_results if r.passed)
    total_failed = sum(1 for r in all_results if not r.passed)

    out = Path(__file__).parent / "feedback_replay_2026_02_09_results.json"
    out.write_text(
        json.dumps(
            {
                "date": "2026-02-09",
                "source": "docs/reports/feedback_triage/2026-02-09.md",
                "total_passed": total_passed,
                "total_failed": total_failed,
                "by_ticket": {
                    ticket: {
                        "status": ticket_status[ticket],
                        "cases": [
                            {
                                "step_id": r.step.step_id,
                                "feedback_id": r.step.feedback_id,
                                "query": r.step.query,
                                "passed": r.passed,
                                "detail": r.detail,
                                "chart_summary": r.chart_summary,
                                "content_preview": r.content_preview[:200],
                            }
                            for r in trs
                        ],
                    }
                    for ticket, trs in by_ticket.items()
                },
                "by_conversation": {
                    conv_name: {
                        "steps_passed": sum(
                            1 for r in conv_results if r.passed
                        ),
                        "steps_total": len(conv_results),
                        "steps": [
                            {
                                "step_id": r.step.step_id,
                                "query": r.step.query,
                                "passed": r.passed,
                                "detail": r.detail,
                            }
                            for r in conv_results
                        ],
                    }
                    for conv_name, conv_results in by_conversation.items()
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"\nResults saved: {out}")

    # ── Final verdict ──
    print(f"\n{'=' * 70}")
    if total_failed == 0:
        print(f"ALL {total_passed} REPLAY STEPS PASSED!")
    else:
        print(
            f"{total_passed} passed, {total_failed} failed "
            f"out of {total_passed + total_failed}"
        )
    print(f"{'=' * 70}")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
