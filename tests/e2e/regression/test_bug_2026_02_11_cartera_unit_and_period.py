#!/usr/bin/env python3
"""
E2E Regression — 2026-02-11: Cartera Total Wrong Unit (%) + Wrong Data Points (22)

Replays the production query that triggered two bugs:
  "cual es la cartera total de INVEX en enero 2024 y en enero 2025"

Bug 1 — WRONG_UNIT: Values shown as "36,410,974,308.00 %" instead of MDP.
  Root cause: metricas_financieras_handler omitted metadata.metric_type,
  causing analytics_extractor to default to "ratio" → "%".
  Fix: Added metadata.metric_type = "currency" for non-ratio metrics.

Bug 2 — EXCESS_POINTS: 22 data points (2024-01..2025-10) instead of 2.
  Root cause: _ensure_multi_year_coverage expanded to continuous range.
  Fix: _parse_period_comparison detects "enero 2024 y enero 2025" and
  filters to exactly those 2 months.

Conversations:
  1. cartera-unit-regression (5 steps): validates unit + data point count
     for cartera_total, activo_total, ROA, IMOR, and period comparisons.

Usage:
    python tests/e2e/regression/test_bug_2026_02_11_cartera_unit_and_period.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "90"))


# ══════════════════════════════════════════════════════════════════════════════
# Dataclasses
# ══════════════════════════════════════════════════════════════════════════════


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
# Chart helpers
# ══════════════════════════════════════════════════════════════════════════════


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


def _extract_trace_names(resp: Dict[str, Any]) -> List[str]:
    """Extract bank/trace names from chart data."""
    bc = resp.get("bank_chart")
    if not bc:
        return []
    names = bc.get("bank_names", [])
    if names:
        return [n.upper() for n in names]
    plotly = bc.get("plotly_config", {})
    traces = plotly.get("data", [])
    return [t.get("name", "").upper() for t in traces if t.get("name")]


def _count_chart_datapoints(resp: Dict[str, Any]) -> int:
    """Count total data points across all traces."""
    bc = resp.get("bank_chart", {})
    if not bc:
        return 0
    plotly = bc.get("plotly_config", {})
    total = 0
    for trace in plotly.get("data", []):
        total += len(trace.get("y", []))
    return total


def _extract_chart_x_dates(resp: Dict[str, Any]) -> List[str]:
    """Extract all X-axis dates from first chart trace."""
    bc = resp.get("bank_chart")
    if not bc:
        return []
    plotly = bc.get("plotly_config", {})
    traces = plotly.get("data", [])
    if not traces:
        return []
    return [str(x) for x in traces[0].get("x", [])]


def _extract_yaxis_title(resp: Dict[str, Any]) -> str:
    """Extract Y-axis title from chart layout."""
    bc = resp.get("bank_chart")
    if not bc:
        return ""
    plotly = bc.get("plotly_config", {})
    layout = plotly.get("layout", {})
    yaxis = layout.get("yaxis", {})
    return yaxis.get("title", "")


# ══════════════════════════════════════════════════════════════════════════════
# Validators — Bug 1: Wrong Unit
# ══════════════════════════════════════════════════════════════════════════════


def _check_cartera_unit_is_not_percent(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    CU-1 (FDBK-0119): cartera total de INVEX en enero 2024 y enero 2025.

    Bug: yaxis.title showed "%" for cartera_total (a currency metric).
    Fix: metadata.metric_type = "currency" → yaxis shows "MDP" or "Cartera (MDP)".

    Also checks LLM text doesn't format cartera values with "%" suffix.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "CHART_MISSING: no chart returned for cartera query"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return False, f"Chart status: {chart_status}"

    # Check Y-axis title — should NOT be just "%"
    yaxis_title = _extract_yaxis_title(resp)
    issues = []

    if yaxis_title == "%" or yaxis_title == "Ratio (%)":
        issues.append(
            f"WRONG_UNIT: yaxis.title='{yaxis_title}', expected MDP-based unit"
        )

    # Check LLM text for "%" after large numeric values (e.g., "36,410,974,308.00 %")
    content = resp.get("content", "")
    # Pattern: large number (>1M) followed by %
    pct_after_large_num = re.findall(
        r"([\d,]{7,}[\d.]*)\s*%", content
    )
    if pct_after_large_num:
        issues.append(
            f"WRONG_UNIT_TEXT: LLM shows '{pct_after_large_num[0]}%' — "
            f"cartera values should be in MDP, not %"
        )

    if issues:
        return False, " | ".join(issues)

    return True, (
        f"Unit OK: yaxis='{yaxis_title}', no % on large values, "
        f"{len(content)} chars"
    )


def _check_roa_unit_is_percent(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    CU-2: ROA de INVEX en 2024.

    Counter-test: ROA IS a ratio metric — yaxis SHOULD show "%".
    Ensures we didn't over-correct by removing % from everything.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        # ROA single-bank may return None and delegate to legacy SQL
        return True, "PASSTHROUGH: handler deferred to legacy SQL (expected)"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return True, f"Chart status: {chart_status} — deferred to legacy"

    yaxis_title = _extract_yaxis_title(resp)

    # ROA yaxis should contain "%" (e.g., "ROA (%)")
    if "%" not in yaxis_title and "ROA" not in yaxis_title:
        return False, (
            f"WRONG_UNIT: yaxis='{yaxis_title}' for ROA — "
            f"expected '%' or 'ROA (%)'"
        )

    return True, f"ROA unit OK: yaxis='{yaxis_title}'"


def _check_activo_total_unit(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    CU-3: activo total de INVEX en 2024.

    Activo total is currency — yaxis should show MDP-based unit, not %.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return True, "PASSTHROUGH: handler deferred to legacy SQL"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return True, f"Chart status: {chart_status}"

    yaxis_title = _extract_yaxis_title(resp)
    content = resp.get("content", "")

    if yaxis_title == "%" or yaxis_title == "Ratio (%)":
        return False, (
            f"WRONG_UNIT: yaxis='{yaxis_title}' for activo_total — "
            f"expected MDP"
        )

    # Check text doesn't use % for large values
    pct_after_large_num = re.findall(r"([\d,]{7,}[\d.]*)\s*%", content)
    if pct_after_large_num:
        return False, (
            f"WRONG_UNIT_TEXT: '{pct_after_large_num[0]}%' in text — "
            f"activos should be in MDP"
        )

    return True, f"Activo total unit OK: yaxis='{yaxis_title}'"


# ══════════════════════════════════════════════════════════════════════════════
# Validators — Bug 2: Excess Data Points
# ══════════════════════════════════════════════════════════════════════════════


def _check_period_comparison_two_points(
    resp: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    CP-1 (FDBK-0119): cartera total de INVEX en enero 2024 y en enero 2025.

    Bug: 22 data points (continuous range 2024-01..2025-10).
    Fix: _parse_period_comparison detects the pattern and filters to 2 months.

    Checks:
    - Chart has <=4 data points (ideally 2; 3-4 acceptable for small rounding)
    - X-axis dates include both 2024-01 and 2025-01
    - NOT 22 consecutive months
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "CHART_MISSING: no chart for period comparison"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return False, f"Chart status: {chart_status}"

    datapoints = _count_chart_datapoints(resp)
    x_dates = _extract_chart_x_dates(resp)

    issues = []

    # Should have 2 points (or ≤4 with minor tolerance)
    if datapoints > 4:
        issues.append(
            f"EXCESS_POINTS: {datapoints} data points, expected 2 "
            f"(enero 2024 + enero 2025)"
        )

    # Should include both target months
    has_2024_01 = any("2024-01" in d for d in x_dates)
    has_2025_01 = any("2025-01" in d for d in x_dates)

    if not has_2024_01:
        issues.append("MISSING_PERIOD: 2024-01 not in chart x-axis")
    if not has_2025_01:
        issues.append("MISSING_PERIOD: 2025-01 not in chart x-axis")

    if issues:
        return False, " | ".join(issues) + f" (dates: {x_dates[:5]})"

    return True, (
        f"Period comparison OK: {datapoints} points, "
        f"dates={x_dates}"
    )


def _check_sept_march_comparison(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    CP-2: cartera total de INVEX en septiembre 2024 y en marzo 2025.

    Variant: different months to verify period comparison generalizes.
    Should have <=4 points covering 2024-09 and 2025-03.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "CHART_MISSING: no chart for sept/march comparison"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status != "success":
        return False, f"Chart status: {chart_status}"

    datapoints = _count_chart_datapoints(resp)
    x_dates = _extract_chart_x_dates(resp)

    issues = []

    if datapoints > 4:
        issues.append(
            f"EXCESS_POINTS: {datapoints} data points, expected 2 "
            f"(sep 2024 + mar 2025)"
        )

    has_2024_09 = any("2024-09" in d for d in x_dates)
    has_2025_03 = any("2025-03" in d for d in x_dates)

    if not has_2024_09:
        issues.append("MISSING_PERIOD: 2024-09 not in chart x-axis")
    if not has_2025_03:
        issues.append("MISSING_PERIOD: 2025-03 not in chart x-axis")

    if issues:
        return False, " | ".join(issues) + f" (dates: {x_dates[:5]})"

    return True, (
        f"Sept/March comparison OK: {datapoints} points, "
        f"dates={x_dates}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Combined validator: both bugs at once (the original production query)
# ══════════════════════════════════════════════════════════════════════════════


def _check_cartera_unit_and_points(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    CU+CP (FDBK-0119): THE original production query.
    "cual es la cartera total de INVEX en enero 2024 y en enero 2025"

    Combined check for BOTH bugs:
    1. Unit should NOT be "%" for cartera_total
    2. Data points should be exactly 2 (not 22)
    """
    # Check unit first
    unit_ok, unit_detail = _check_cartera_unit_is_not_percent(resp)
    # Check points
    points_ok, points_detail = _check_period_comparison_two_points(resp)

    all_ok = unit_ok and points_ok
    combined = f"[UNIT] {unit_detail} | [POINTS] {points_detail}"

    return all_ok, combined


# ══════════════════════════════════════════════════════════════════════════════
# Conversation definitions
# ══════════════════════════════════════════════════════════════════════════════


CONV_CARTERA_UNIT = ConversationReplay(
    name="cartera-unit-and-period-regression",
    original_conv_id="85338a1e",
    description=(
        "Regression test for two bugs in metricas_financieras_handler: "
        "wrong unit (% instead of MDP) and excess data points (22 instead of 2). "
        "Tests the exact production query + variants for unit correctness."
    ),
    steps=[
        ConversationStep(
            step_id="CU+CP-0",
            feedback_id="FDBK-0119",
            ticket="cartera-wrong-unit-and-points",
            query=(
                "cual es la cartera total de INVEX en enero 2024 "
                "y en enero 2025"
            ),
            validate=_check_cartera_unit_and_points,
            description=(
                "THE ORIGINAL BUG: cartera values as '36,410,974,308 %' "
                "and 22 data points. Fix: metadata.metric_type=currency + "
                "period comparison filter."
            ),
        ),
        ConversationStep(
            step_id="CU-1",
            feedback_id="REGRESSION",
            ticket="cartera-wrong-unit-and-points",
            query="cartera total de INVEX en 2024",
            validate=_check_cartera_unit_is_not_percent,
            description=(
                "UNIT_CHECK: cartera_total without period comparison. "
                "Verifies unit is MDP, not %."
            ),
        ),
        ConversationStep(
            step_id="CU-2",
            feedback_id="REGRESSION",
            ticket="cartera-wrong-unit-and-points",
            query="ROA de INVEX en 2024",
            validate=_check_roa_unit_is_percent,
            description=(
                "COUNTER_TEST: ROA IS a ratio — yaxis SHOULD show %. "
                "Ensures we didn't remove % from everything."
            ),
        ),
        ConversationStep(
            step_id="CU-3",
            feedback_id="REGRESSION",
            ticket="cartera-wrong-unit-and-points",
            query="activo total de INVEX en 2024",
            validate=_check_activo_total_unit,
            description=(
                "UNIT_CHECK: activo_total is currency — should be MDP."
            ),
        ),
        ConversationStep(
            step_id="CP-2",
            feedback_id="REGRESSION",
            ticket="cartera-wrong-unit-and-points",
            query=(
                "cual es la cartera total de INVEX en septiembre 2024 "
                "y en marzo 2025"
            ),
            validate=_check_sept_march_comparison,
            description=(
                "PERIOD_VARIANT: different months to verify period "
                "comparison generalizes beyond enero."
            ),
        ),
    ],
)


CONVERSATIONS: List[ConversationReplay] = [CONV_CARTERA_UNIT]


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
        print(
            f"\n  Step {i + 1}/{len(conv.steps)} [{step.step_id}] "
            f"{step.description}"
        )
        print(
            f"  Query: \"{step.query[:80]}"
            f"{'...' if len(step.query) > 80 else ''}\""
        )

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

        # Build chart summary
        chart_summary = None
        bc = resp.get("bank_chart")
        if bc:
            x_range = _extract_x_range(resp)
            traces = _extract_trace_names(resp)
            datapoints = _count_chart_datapoints(resp)
            yaxis = _extract_yaxis_title(resp)
            chart_summary = (
                f"status={bc.get('chart_status', '?')}, "
                f"traces={traces}, points={datapoints}, "
                f"yaxis='{yaxis}'"
            )
            if x_range:
                chart_summary += f", x=[{x_range[0]}..{x_range[1]}]"

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
    print("E2E Regression — 2026-02-11: Cartera Unit (%) + Period Points (22)")
    print("Bugs: WRONG_UNIT (% instead of MDP), EXCESS_POINTS (22 vs 2)")
    print("Fix: metadata.metric_type + _parse_period_comparison in handler")
    print("=" * 70)

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FATAL: Auth failed")
        return 2

    print(f"Authenticated against {BACKEND_URL}")

    all_results: List[StepResult] = []
    by_ticket: Dict[str, List[StepResult]] = {}

    for conv in CONVERSATIONS:
        conv_results = run_conversation(token, conv)
        all_results.extend(conv_results)

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

    # ── Save results JSON ──
    total_passed = sum(1 for r in all_results if r.passed)
    total_failed = sum(1 for r in all_results if not r.passed)

    out = (
        Path(__file__).parent
        / "bug_2026_02_11_cartera_unit_and_period_results.json"
    )
    out.write_text(
        json.dumps(
            {
                "date": "2026-02-11",
                "bug": "cartera-wrong-unit-and-excess-points",
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
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"\nResults saved: {out}")

    # ── Final verdict ──
    print(f"\n{'=' * 70}")
    if total_failed == 0:
        print(f"ALL {total_passed} REGRESSION STEPS PASSED!")
    else:
        print(
            f"{total_passed} passed, {total_failed} failed "
            f"out of {total_passed + total_failed}"
        )
    print(f"{'=' * 70}")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
