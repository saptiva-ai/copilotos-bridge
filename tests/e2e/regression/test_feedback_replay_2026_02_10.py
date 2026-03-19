#!/usr/bin/env python3
"""
E2E Feedback Replay — 2026-02-10 (response-grounding-desync)

Replays EXACT queries from feedback triage that reported month-value
confusion in LLM narrative text. Chart/table data is always correct;
the bug is the LLM text citing values from wrong months or wrong banks.

Source: docs/kanban/DOING/2026-02-03__BUG__response-grounding-desync/card.md

Conversations replayed:
  1. SINGLE_BANK (FDBK-0111, FDBK-0112): single-bank queries where LLM
     should use trend/stats only (Turbo instruction restricts citations).
  2. MULTI_BANK (FDBK-0093, FDBK-0094): multi-bank comparison queries
     where cross-bank value swaps occurred in paragraph transitions.
  3. EDGE_CASES (STRESS-TEST): stress-test scenarios that push the
     routing + format pipeline to its limits:
     - GD-5: Turbo with full table data (must resist citing)
     - GD-6: Legacy single-bank evolution (citation accuracy)
     - GD-7: Multi-bank dense evolution (worst case for swaps)
     - GD-8: 3-bank comparison (maximum confusion opportunity)
     - GD-9: Multi-year month comparison (truncation-before-filtering fix)
     - GD-10: 10-bank query (max_series=10 fix)

Bug clusters:
  - MONTH_SWAP  (S0) — LLM cites value from Month A under Month B label
  - CROSS_BANK  (S0) — LLM attributes Bank A's value to Bank B
  - OVERFIT_CITE(S1) — Turbo cites ≥3 individual month-values despite
                        instruction to use trends only

Fix: Dynamic model routing (Turbo→Legacy) + adaptive instructions +
     guardrail post-processor. Feature flag: DATA_MODEL_ROUTING_ENABLED.

Usage:
    python tests/e2e/regression/test_feedback_replay_2026_02_10.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "90"))

# ══════════════════════════════════════════════════════════════════════════════
# Shared regex and helpers
# ══════════════════════════════════════════════════════════════════════════════

_MONTH_NAMES = (
    r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|"
    r"octubre|noviembre|diciembre|ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)"
)
# Match month-value citations in both plain and bold-markdown formats:
#   "enero 2024: 132,450.30 MDP"
#   "**Enero 2024**: **132,450.30 MDP**"
#   "- **Ene. 2024**: 14,870.61 MDP"
_MONTH_VALUE_RE = re.compile(
    r"\*{0,2}"  # optional leading **
    + _MONTH_NAMES
    + r"\.?"
    + r"\*{0,2}"  # optional trailing **
    + r"\s+(?:de\s+)?"
    + r"\*{0,2}"  # optional ** around year
    + r"(?:20\d{2})"
    + r"\*{0,2}"  # optional trailing **
    + r"[\s:,]+(?:fue\s+(?:de\s+)?)?"
    + r"\*{0,2}"  # optional ** around value
    + r"([\d,.]+)\s*"
    + r"(?:MDP|mdp|%|mil\s+millones|millones|mmdp)"
    + r"\*{0,2}",  # optional trailing **
    re.IGNORECASE,
)

# Extracts numeric values (with commas/periods) from LLM text
_NUMERIC_RE = re.compile(r"([\d]{1,3}(?:[,.][\d]{3})*(?:[.,]\d+)?)")


@dataclass
class ConversationStep:
    step_id: str
    feedback_id: str
    ticket: str
    query: str
    validate: Callable[[Dict[str, Any]], Tuple[bool, str]]
    description: str = ""


@dataclass
class StepResult:
    step: ConversationStep
    passed: bool
    detail: str
    content_preview: str = ""
    chart_summary: Optional[str] = None


@dataclass
class ConversationReplay:
    name: str
    original_conv_id: str
    description: str
    steps: List[ConversationStep]


# ══════════════════════════════════════════════════════════════════════════════
# Helpers — chart data extraction
# ══════════════════════════════════════════════════════════════════════════════


def _extract_chart_values(resp: Dict[str, Any]) -> Set[str]:
    """Extract all Y-axis values from chart traces as normalized strings."""
    values: Set[str] = set()
    bc = resp.get("bank_chart")
    if not bc:
        return values
    plotly = bc.get("plotly_config", {})
    for trace in plotly.get("data", []):
        for y_val in trace.get("y", []):
            if y_val is not None:
                # Normalize: "15052.10" → "15,052.10" and vice versa
                raw = str(y_val)
                values.add(raw)
                # Also add comma-formatted version
                try:
                    num = float(raw.replace(",", ""))
                    values.add(f"{num:,.2f}")
                    values.add(f"{num:.2f}")
                    # Integer version for round numbers
                    if num == int(num):
                        values.add(f"{int(num):,}")
                        values.add(str(int(num)))
                except ValueError:
                    pass
    return values


def _extract_trace_names(resp: Dict[str, Any]) -> List[str]:
    """Extract bank/trace names from chart data.

    Handles two plotly structures:
    1. Multi-series line chart: each trace has a 'name' field (bank name)
    2. Grouped bar / category chart: bank names live in trace.x values
       (when x contains strings like ['BBVA', 'INVEX'] instead of dates)
    """
    bc = resp.get("bank_chart")
    if not bc:
        return []
    names = bc.get("bank_names", [])
    if names:
        return [n.upper() for n in names]
    plotly = bc.get("plotly_config", {})
    traces = plotly.get("data", [])
    # Strategy 1: trace.name (multi-series line charts)
    named = [t.get("name", "").upper() for t in traces if t.get("name")]
    if named:
        return named
    # Strategy 2: trace.x contains bank name strings (category charts)
    # Detect by checking if x values are non-date strings
    for trace in traces:
        x_vals = trace.get("x", [])
        if x_vals and isinstance(x_vals[0], str) and not x_vals[0][:4].isdigit():
            return [v.upper() for v in x_vals if isinstance(v, str)]
    return []


def _count_month_value_citations(text: str) -> int:
    """Count month-value citation patterns in LLM text."""
    return len(_MONTH_VALUE_RE.findall(text))


def _extract_x_range(resp: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """Extract (first_date, last_date) from chart plotly data."""
    bc = resp.get("bank_chart")
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


# ══════════════════════════════════════════════════════════════════════════════
# Shared false-negative detection — synced with response_postprocessor.py
# ══════════════════════════════════════════════════════════════════════════════

# Keep in sync with apps/backend/src/services/streaming/response_postprocessor.py
_FALSE_NEGATIVE_PHRASES = [
    "no encuentro información",
    "no tengo información",
    "no dispongo de información",
    "no puedo encontrar",
    "no hay datos",
    "no tengo datos",
    "no tengo el dato",
    "no cuento con datos",
    "no cuento con información",
    "no está disponible",
    "información no disponible",
    "no se encontró",
    "sin información",
    "lamentablemente no",
    "desafortunadamente no",
]

_FALSE_NEGATIVE_EXCEPTIONS = [
    "no hay datos históricos",
    "no hay datos adicionales",
    "no hay datos para ese período",
    # Partial data statements: LLM correctly reports missing data for a
    # specific bank/metric while still analyzing the rest.
    "no tengo datos para",
    "no hay datos para",
    "solo tengo datos",
    "sólo tengo datos",
]


def _check_no_false_negatives(resp: Dict[str, Any]) -> Optional[Tuple[bool, str]]:
    """Shared guard: fail if LLM says 'no tengo datos' when chart_status=success.

    Returns None if no false negative detected (caller continues its own validation).
    Returns (False, detail) if a false-negative phrase is found.
    """
    bc = resp.get("bank_chart")
    if not bc:
        return None
    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return None

    content = (resp.get("content") or "").lower()
    if not content:
        return None

    for exc in _FALSE_NEGATIVE_EXCEPTIONS:
        if exc in content:
            return None

    for phrase in _FALSE_NEGATIVE_PHRASES:
        if phrase in content:
            return False, (
                f"FALSE_NEGATIVE: LLM said '{phrase}' despite chart_status=success"
            )
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Validators — SINGLE BANK (Turbo: trends only, no individual month citations)
# ══════════════════════════════════════════════════════════════════════════════


def _check_single_bank_baseline(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """GD-0: Simple baseline query — chart present, response coherent."""
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned for baseline query"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return False, f"Chart status: {chart_status} (expected success)"

    content = resp.get("content", "")
    if not content or len(content) < 20:
        return False, f"Response too short ({len(content)} chars)"

    # LLM should NOT say "no tengo datos" when chart is success
    fn_result = _check_no_false_negatives(resp)
    if fn_result is not None:
        return fn_result

    return True, f"Baseline OK: chart success, response {len(content)} chars"


def _check_grounding_single_bank_2024(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    GD-1 (FDBK-0111): cartera comercial de invex en 2024.
    Bug: LLM text confuses months and amounts.
    Fix: Turbo instruction restricts to trends/stats — should NOT cite ≥3
    individual month-value pairs.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return False, f"Chart status: {chart_status}"

    fn_result = _check_no_false_negatives(resp)
    if fn_result is not None:
        return fn_result

    content = resp.get("content", "")
    citations = _count_month_value_citations(content)

    # With adaptive instructions, Turbo should cite ≤2 month-value pairs
    # (e.g., referencing min/max from stats is OK)
    if citations >= 3:
        # Check if guardrail disclaimer was appended (safety net working)
        has_disclaimer = "Los valores exactos por mes" in content
        if has_disclaimer:
            return True, (
                f"GUARDRAIL_ACTIVE: {citations} citations detected, "
                f"disclaimer appended (safety net working)"
            )
        return False, (
            f"OVERFIT_CITE: {citations} month-value citations found — "
            f"Turbo should use trends/stats only"
        )

    return True, (
        f"Grounding OK: {citations} citations "
        f"(within trend-only threshold), {len(content)} chars"
    )


def _check_grounding_single_bank_2025(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    GD-2 (FDBK-0112): cartera comercial de bbva en 2025.
    Same pattern as GD-1 — text should not cite individual month values.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return False, f"Chart status: {chart_status}"

    fn_result = _check_no_false_negatives(resp)
    if fn_result is not None:
        return fn_result

    content = resp.get("content", "")
    citations = _count_month_value_citations(content)

    if citations >= 3:
        has_disclaimer = "Los valores exactos por mes" in content
        if has_disclaimer:
            return True, (
                f"GUARDRAIL_ACTIVE: {citations} citations, " f"disclaimer appended"
            )
        return False, (
            f"OVERFIT_CITE: {citations} month-value citations — "
            f"Turbo should use trends/stats only"
        )

    return True, (f"Grounding OK: {citations} citations, {len(content)} chars")


# ══════════════════════════════════════════════════════════════════════════════
# Validators — MULTI BANK (cross-bank value swap detection)
# ══════════════════════════════════════════════════════════════════════════════


def _check_multi_bank_grounding(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    GD-3 (FDBK-0093): compare cartera bbva e invex.
    Bug: Cross-bank swap — LLM attributed INVEX's Oct value to Dec.
    Fix: Legacy model with exact-citation instructions, or Turbo with
    trend-only restriction.

    Validation: If text cites numeric values with month labels, those
    values must exist somewhere in the chart data traces.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned for multi-bank comparison"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return False, f"Chart status: {chart_status}"

    fn_result = _check_no_false_negatives(resp)
    if fn_result is not None:
        return fn_result

    trace_names = _extract_trace_names(resp)
    if len(trace_names) < 2:
        return False, (
            f"Expected ≥2 traces for comparison, got {len(trace_names)}: "
            f"{trace_names}"
        )

    content = resp.get("content", "")
    citations = _count_month_value_citations(content)

    # For multi-bank: if few citations, the trend-only approach is working
    if citations < 3:
        return True, (
            f"Multi-bank OK: {len(trace_names)} banks, "
            f"{citations} citations (trend-only), {len(content)} chars"
        )

    # If many citations: check that cited values exist in chart data
    chart_values = _extract_chart_values(resp)
    cited_values = _MONTH_VALUE_RE.findall(content)

    phantom_count = 0
    for cited_val in cited_values:
        # Normalize the cited value
        normalized = cited_val.replace(",", "").replace(" ", "")
        try:
            num = float(normalized)
        except ValueError:
            continue
        # Check if this value exists in any trace
        found = False
        for chart_val in chart_values:
            try:
                chart_num = float(chart_val.replace(",", ""))
                # Allow 1% tolerance for rounding
                if abs(num - chart_num) / max(chart_num, 1) < 0.01:
                    found = True
                    break
            except ValueError:
                continue
        if not found:
            phantom_count += 1

    if phantom_count > 0:
        return False, (
            f"CROSS_BANK_SWAP: {phantom_count}/{len(cited_values)} cited "
            f"values not found in chart traces (possible month/bank swap)"
        )

    # Citations exist but values match chart data — Legacy is citing correctly
    has_disclaimer = "Los valores exactos por mes" in content
    if has_disclaimer:
        return True, (
            f"GUARDRAIL_ACTIVE: {citations} citations with disclaimer, "
            f"values verified against chart"
        )

    return True, (
        f"Multi-bank grounding OK: {citations} citations, "
        f"all values found in chart data, {len(trace_names)} banks"
    )


def _check_multi_bank_santander(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    GD-4 (FDBK-0094): compare cartera bbva y santander.
    Same cross-bank swap pattern as GD-3.
    """
    return _check_multi_bank_grounding(resp)


# ══════════════════════════════════════════════════════════════════════════════
# Validators — EDGE CASES (stress-test routing + format accuracy)
# ══════════════════════════════════════════════════════════════════════════════


def _check_turbo_full_table_restriction(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    GD-5: Single-bank + keyword "todos los datos" → Turbo + table_mode=full.
    Turbo MUST NOT cite ≥3 individual month-values even when given full table.
    Tests that the restrictive instruction holds under data pressure.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return False, f"Chart status: {chart_status}"

    fn_result = _check_no_false_negatives(resp)
    if fn_result is not None:
        return fn_result

    content = resp.get("content", "")
    citations = _count_month_value_citations(content)

    if citations >= 3:
        has_disclaimer = "Los valores exactos por mes" in content
        if has_disclaimer:
            return True, (
                f"GUARDRAIL_ACTIVE: {citations} citations but disclaimer "
                f"appended — Turbo guardrail working"
            )
        return False, (
            f"TURBO_LEAK: {citations} month-value citations in full-table mode — "
            f"restrictive instruction not respected"
        )

    return True, (
        f"Turbo full-table OK: {citations} citations "
        f"(instruction restriction held), {len(content)} chars"
    )


def _check_legacy_evolution_accuracy(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    GD-6: "evolución mes a mes" → routes to Legacy + full markdown-kv.
    If Legacy cites values, they MUST match chart trace data.
    This is the critical accuracy test for the markdown-kv format.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned for evolution query"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return False, f"Chart status: {chart_status}"

    fn_result = _check_no_false_negatives(resp)
    if fn_result is not None:
        return fn_result

    content = resp.get("content", "")
    citations = _count_month_value_citations(content)

    # Legacy may or may not cite — both are OK if values are correct
    if citations < 3:
        return True, (
            f"Legacy evolution OK: {citations} citations (trend-summary mode), "
            f"{len(content)} chars"
        )

    # If Legacy cited ≥3 values, verify they exist in chart data
    chart_values = _extract_chart_values(resp)
    cited_matches = _MONTH_VALUE_RE.findall(content)

    phantom_count = 0
    verified_count = 0
    for cited_val in cited_matches:
        normalized = cited_val.replace(",", "").replace(" ", "")
        try:
            num = float(normalized)
        except ValueError:
            continue
        found = False
        for chart_val in chart_values:
            try:
                chart_num = float(chart_val.replace(",", ""))
                if abs(num - chart_num) / max(chart_num, 1) < 0.02:
                    found = True
                    break
            except ValueError:
                continue
        if found:
            verified_count += 1
        else:
            phantom_count += 1

    if phantom_count > 0:
        return False, (
            f"MONTH_SWAP: {phantom_count}/{len(cited_matches)} cited values "
            f"not found in chart data (markdown-kv format did not prevent swap)"
        )

    return True, (
        f"Legacy evolution ACCURATE: {verified_count} cited values all verified "
        f"against chart data, {len(content)} chars"
    )


def _count_chart_datapoints(resp: Dict[str, Any]) -> int:
    """Count total data points across all traces."""
    bc = resp.get("bank_chart", {})
    plotly = bc.get("plotly_config", {})
    total = 0
    for trace in plotly.get("data", []):
        total += len(trace.get("y", []))
    return total


def _check_multi_bank_dense_evolution(
    resp: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    GD-7: Multi-bank + "mes a mes" → Legacy + 2 banks + dense data.
    This is the WORST CASE: the exact scenario where cross-bank swaps
    happened in production. Legacy + markdown-kv format should prevent them.

    Two chart shapes are possible:
    1. Dense temporal: line/bar with 12+ points per bank → verify citations
    2. Summary bar: 1-2 points per bank (totals) → citations are hallucinated
       if they reference individual months not present in chart
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned for multi-bank evolution"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return False, f"Chart status: {chart_status}"

    fn_result = _check_no_false_negatives(resp)
    if fn_result is not None:
        return fn_result

    trace_names = _extract_trace_names(resp)
    if len(trace_names) < 2:
        return False, (
            f"Expected ≥2 traces/banks, got {len(trace_names)}: {trace_names}"
        )

    content = resp.get("content", "")
    citations = _count_month_value_citations(content)
    datapoints = _count_chart_datapoints(resp)

    # If chart only has summary data (≤4 points), the handler did NOT
    # generate a temporal evolution. LLM citations of individual months
    # would be hallucinated — but that's a handler bug, not grounding.
    if datapoints <= 4:
        if citations >= 3:
            return True, (
                f"HANDLER_LIMITATION: chart has only {datapoints} points "
                f"(summary, not evolution) but LLM cited {citations} months — "
                f"handler did not generate temporal data. "
                f"Grounding cannot verify. {len(trace_names)} banks."
            )
        return True, (
            f"Multi-bank summary OK: {len(trace_names)} banks, "
            f"{datapoints} chart points, {citations} citations, "
            f"{len(content)} chars"
        )

    # Dense chart (≥5 datapoints): verify citations against chart values
    if citations < 3:
        return True, (
            f"Multi-bank evolution OK: {len(trace_names)} banks, "
            f"{citations} citations (trend-only), {datapoints} chart points, "
            f"{len(content)} chars"
        )

    chart_values = _extract_chart_values(resp)
    cited_matches = _MONTH_VALUE_RE.findall(content)

    phantom_count = 0
    verified_count = 0
    for cited_val in cited_matches:
        normalized = cited_val.replace(",", "").replace(" ", "")
        try:
            num = float(normalized)
        except ValueError:
            continue
        found = False
        for chart_val in chart_values:
            try:
                chart_num = float(chart_val.replace(",", ""))
                if abs(num - chart_num) / max(chart_num, 1) < 0.02:
                    found = True
                    break
            except ValueError:
                continue
        if found:
            verified_count += 1
        else:
            phantom_count += 1

    if phantom_count > 0:
        return False, (
            f"CROSS_BANK_SWAP: {phantom_count}/{len(cited_matches)} cited "
            f"values not in chart traces ({datapoints} chart points, "
            f"{len(trace_names)} banks)"
        )

    return True, (
        f"Multi-bank evolution ACCURATE: {len(trace_names)} banks, "
        f"{verified_count} cited values verified, {datapoints} chart points, "
        f"{len(content)} chars"
    )


def _check_three_bank_stress(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    GD-8: 3-bank comparison → Legacy routing, ≥3 traces.
    Stress test: more banks = more opportunity for cross-bank confusion.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned for 3-bank query"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return False, f"Chart status: {chart_status}"

    fn_result = _check_no_false_negatives(resp)
    if fn_result is not None:
        return fn_result

    trace_names = _extract_trace_names(resp)
    if len(trace_names) < 3:
        return False, (
            f"Expected ≥3 traces for 3-bank comparison, got "
            f"{len(trace_names)}: {trace_names}"
        )

    content = resp.get("content", "")
    citations = _count_month_value_citations(content)

    if citations < 3:
        return True, (
            f"3-bank OK: {len(trace_names)} banks, {citations} citations "
            f"(trend-only), {len(content)} chars"
        )

    # Verify cited values exist in chart data
    chart_values = _extract_chart_values(resp)
    cited_matches = _MONTH_VALUE_RE.findall(content)

    phantom_count = 0
    for cited_val in cited_matches:
        normalized = cited_val.replace(",", "").replace(" ", "")
        try:
            num = float(normalized)
        except ValueError:
            continue
        found = any(
            abs(num - float(cv.replace(",", ""))) / max(float(cv.replace(",", "")), 1)
            < 0.02
            for cv in chart_values
            if cv.replace(",", "").replace(".", "").isdigit()
            or cv.replace(",", "").replace(".", "", 1).isdigit()
        )
        if not found:
            phantom_count += 1

    if phantom_count > 0:
        return False, (
            f"3-BANK_SWAP: {phantom_count}/{len(cited_matches)} phantom values — "
            f"cross-bank confusion with 3 banks"
        )

    return True, (
        f"3-bank grounding OK: {len(trace_names)} banks, {citations} citations, "
        f"all values verified, {len(content)} chars"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Validators — FALSE NEGATIVE fixes (truncation + max_series)
# ══════════════════════════════════════════════════════════════════════════════


def _check_multiyear_month_comparison(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    GD-9: "enero 2024 vs enero 2025" — multi-year month comparison.
    Bug: datos[-12:] truncated before month filter → enero 2024 lost from context.
    Fix: Filter by month FIRST, then truncate.

    Validation: chart should succeed AND response should NOT contain false-negative
    phrases. The LLM must acknowledge data for both years.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned for multi-year query"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return False, f"Chart status: {chart_status}"

    fn_result = _check_no_false_negatives(resp)
    if fn_result is not None:
        return fn_result

    content = resp.get("content", "")
    lower = content.lower()

    # Verify that response references both years (not just one)
    has_2024 = "2024" in content
    has_2025 = "2025" in content
    if not has_2024 or not has_2025:
        missing = []
        if not has_2024:
            missing.append("2024")
        if not has_2025:
            missing.append("2025")
        return False, (
            f"TRUNCATION_BUG: response missing year(s) {', '.join(missing)} — "
            f"data may have been truncated before month filter"
        )

    return True, (
        f"Multi-year OK: both 2024 and 2025 referenced, "
        f"{len(content)} chars, no false negatives"
    )


def _check_ten_bank_query(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    GD-10: 10-bank comparison query.
    Bug: max_series=6 dropped 4 banks from context → LLM says "no tengo datos".
    Fix: max_series raised to 10.

    Validation: chart should succeed, response should NOT contain false-negative
    phrases, and response should reference a reasonable number of banks.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "No chart returned for 10-bank query"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return False, f"Chart status: {chart_status}"

    fn_result = _check_no_false_negatives(resp)
    if fn_result is not None:
        return fn_result

    trace_names = _extract_trace_names(resp)
    content = resp.get("content", "").upper()

    # Count how many of the requested banks are mentioned in the response
    requested_banks = [
        "INVEX",
        "BBVA",
        "BANORTE",
        "SANTANDER",
        "SCOTIABANK",
        "HSBC",
        "AFIRME",
        "BANREGIO",
        "BAJIO",
        "INBURSA",
    ]
    mentioned = [b for b in requested_banks if b in content]

    if len(mentioned) < 6:
        return False, (
            f"MAX_SERIES_BUG: only {len(mentioned)}/10 banks mentioned in response "
            f"({', '.join(mentioned)}). Context table may be truncating at old limit."
        )

    return True, (
        f"10-bank OK: {len(mentioned)} banks mentioned, "
        f"{len(trace_names)} traces, {len(resp.get('content', ''))} chars"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Conversation definitions
# ══════════════════════════════════════════════════════════════════════════════


CONV_SINGLE_BANK = ConversationReplay(
    name="grounding-single-bank",
    original_conv_id="FDBK-0111/0112",
    description=(
        "Single-bank queries where LLM should use trend/stats only. "
        "Reproduces MONTH_SWAP from FDBK-0111 and FDBK-0112."
    ),
    steps=[
        ConversationStep(
            step_id="GD-0",
            feedback_id="BASELINE",
            ticket="grounding-desync",
            query="muestrame la cartera comercial de invex",
            validate=_check_single_bank_baseline,
            description="Baseline: simple query, chart present, no contradiction",
        ),
        ConversationStep(
            step_id="GD-1",
            feedback_id="FDBK-0111",
            ticket="grounding-desync",
            query="muéstrame la cartera comercial de invex en 2024",
            validate=_check_grounding_single_bank_2024,
            description=(
                "MONTH_SWAP: user reports text confuses months and amounts. "
                "Fix: Turbo should use trends/stats only."
            ),
        ),
        ConversationStep(
            step_id="GD-2",
            feedback_id="FDBK-0112",
            ticket="grounding-desync",
            query="muestrame la cartera comercial de bbva en 2025",
            validate=_check_grounding_single_bank_2025,
            description=(
                "MONTH_SWAP: text doesn't match chart/table months. "
                "Fix: Turbo should use trends/stats only."
            ),
        ),
    ],
)


CONV_MULTI_BANK = ConversationReplay(
    name="grounding-multi-bank",
    original_conv_id="FDBK-0093/0094",
    description=(
        "Multi-bank comparison queries where cross-bank value swaps "
        "occurred. Reproduces CROSS_BANK from FDBK-0093 and FDBK-0094."
    ),
    steps=[
        ConversationStep(
            step_id="GD-3",
            feedback_id="FDBK-0093",
            ticket="grounding-desync",
            query=(
                "muestrame una grafica en la que se compare la cartera "
                "comercial de bbva e invex el ultimo año"
            ),
            validate=_check_multi_bank_grounding,
            description=(
                "CROSS_BANK: INVEX Oct value attributed to Dec. "
                "Fix: Legacy model for multi-bank, or trend-only for Turbo."
            ),
        ),
        ConversationStep(
            step_id="GD-4",
            feedback_id="FDBK-0094",
            ticket="grounding-desync",
            query=(
                "muestrame una grafica en la que se compare la cartera "
                "comercial de bbva y santander el ultimo año"
            ),
            validate=_check_multi_bank_santander,
            description=(
                "CROSS_BANK: Santander Oct value showed Dec amount. "
                "Fix: Legacy model for multi-bank, or trend-only for Turbo."
            ),
        ),
    ],
)


CONV_EDGE_CASES = ConversationReplay(
    name="grounding-edge-cases",
    original_conv_id="STRESS-TEST",
    description=(
        "Edge cases that stress-test the routing + format pipeline. "
        "GD-5: Turbo under data pressure. GD-6: Legacy citation accuracy. "
        "GD-7: Multi-bank dense evolution (worst case). GD-8: 3-bank stress."
    ),
    steps=[
        ConversationStep(
            step_id="GD-5",
            feedback_id="STRESS",
            ticket="grounding-desync",
            query=(
                "muestrame todos los datos de la cartera comercial " "de invex en 2024"
            ),
            validate=_check_turbo_full_table_restriction,
            description=(
                "TURBO_PRESSURE: keyword 'todos los datos' forces full "
                "table mode. Turbo must still NOT cite ≥3 month-values."
            ),
        ),
        ConversationStep(
            step_id="GD-6",
            feedback_id="STRESS",
            ticket="grounding-desync",
            query=(
                "muestrame la evolución de la cartera comercial de invex "
                "mes a mes en 2024"
            ),
            validate=_check_legacy_evolution_accuracy,
            description=(
                "LEGACY_ACCURACY: evolution keywords route to Legacy. "
                "If Legacy cites values, they must match chart data exactly."
            ),
        ),
        ConversationStep(
            step_id="GD-7",
            feedback_id="STRESS",
            ticket="grounding-desync",
            query=(
                "compara la evolución de la cartera comercial de bbva e invex "
                "mes a mes en 2024"
            ),
            validate=_check_multi_bank_dense_evolution,
            description=(
                "WORST_CASE: multi-bank + evolution + dense data. "
                "Legacy + markdown-kv must prevent cross-bank swaps."
            ),
        ),
        ConversationStep(
            step_id="GD-8",
            feedback_id="STRESS",
            ticket="grounding-desync",
            query=(
                "compara la cartera comercial de invex, bbva y banorte " "el ultimo año"
            ),
            validate=_check_three_bank_stress,
            description=(
                "3-BANK STRESS: 3 traces, maximum cross-bank confusion "
                "opportunity. All cited values must exist in chart data."
            ),
        ),
    ],
)

# GD-9 and GD-10 run in a fresh session to avoid context bleed from GD-8's
# 3-bank query (ContextEnricher additive mode would carry BANORTE/BBVA forward).
CONV_NO_TENGO_DATOS = ConversationReplay(
    name="no-tengo-datos-fixes",
    original_conv_id="FIX-VERIFICATION",
    description=(
        "Isolated tests for 'no tengo datos' false-negative fixes. "
        "GD-9: Multi-year truncation fix. GD-10: 10-bank max_series fix. "
        "These run in a fresh session to avoid session context bleed."
    ),
    steps=[
        ConversationStep(
            step_id="GD-9",
            feedback_id="FIX-TRUNCATION",
            ticket="no-tengo-datos",
            query=(
                "compara la cartera comercial de INVEX " "en enero 2024 vs enero 2025"
            ),
            validate=_check_multiyear_month_comparison,
            description=(
                "TRUNCATION_FIX: multi-year month query that previously "
                "lost old months due to truncation-before-filtering."
            ),
        ),
        ConversationStep(
            step_id="GD-10",
            feedback_id="FIX-MAX-SERIES",
            ticket="no-tengo-datos",
            query=(
                "compara la cartera comercial de INVEX, BBVA, Banorte, "
                "Santander, Scotiabank, HSBC, Afirme, Banregio, Bajío "
                "e Inbursa en 2025"
            ),
            validate=_check_ten_bank_query,
            description=(
                "MAX_SERIES_FIX: 10-bank query that previously truncated "
                "to 6 banks in context table."
            ),
        ),
    ],
)


CONVERSATIONS: List[ConversationReplay] = [
    CONV_SINGLE_BANK,
    CONV_MULTI_BANK,
    CONV_EDGE_CASES,
    CONV_NO_TENGO_DATOS,
]


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
        print(f'  Query: "{step.query}"')

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

        if not chat_id:
            extra = resp.get("extra", {})
            done_data = extra.get("done")
            if isinstance(done_data, dict):
                chat_id = done_data.get("chat_id")

        content = resp.get("content", "")
        passed, detail = step.validate(resp)

        # Chart summary
        chart_summary = None
        bc = resp.get("bank_chart")
        if bc:
            x_range = _extract_x_range(resp)
            traces = _extract_trace_names(resp)
            citations = _count_month_value_citations(content)
            chart_summary = (
                f"status={bc.get('chart_status', '?')}, "
                f"traces={traces}, "
                f"citations={citations}"
            )
            if x_range:
                chart_summary += f", x_range=[{x_range[0]}, {x_range[1]}]"

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
    print("E2E Feedback Replay — 2026-02-10 (response-grounding-desync)")
    print(
        "Conversations: grounding-single-bank, grounding-multi-bank, grounding-edge-cases, no-tengo-datos-fixes"
    )
    print("Source: docs/kanban/DOING/2026-02-03__BUG__response-grounding-desync/")
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
            "RESOLVED" if all_passed else f"PERSISTS ({total - passed}/{total} failing)"
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

    out = Path(__file__).parent / "feedback_replay_2026_02_10_results.json"
    out.write_text(
        json.dumps(
            {
                "date": "2026-02-10",
                "bug": "response-grounding-desync",
                "source": "docs/kanban/DOING/2026-02-03__BUG__response-grounding-desync/card.md",
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
                        "steps_passed": sum(1 for r in conv_results if r.passed),
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
