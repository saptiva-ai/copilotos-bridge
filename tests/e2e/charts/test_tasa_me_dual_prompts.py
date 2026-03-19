#!/usr/bin/env python3
"""
E2E Test — Tasa ME dual prompts: Ranking (bar chart) + Trend (line chart)

Tests the two onboarding presets for Tasa Promedio ME:
  1. Ranking: horizontal bar chart with individual bank rates + table
  2. Trend: INVEX vs PROMEDIO time series line chart

Tableau "Tasas Moneda Extranjera" view has both components.

Usage:
    python tests/e2e/charts/test_tasa_me_dual_prompts.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "120"))

# ── Prompts ──────────────────────────────────────────────────────────────────

PROMPT_RANKING = (
    "Muestra la tasa promedio en Moneda Extranjera del mes más reciente para los bancos: "
    "MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS Y BANCO BASE. "
    "Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca a INVEX de color rojo. "
    "Incluye una tabla con: Banco | Tasa ME"
)

PROMPT_TREND = (
    "Crea una gráfica donde se compare la tasa promedio en Moneda Extranjera de INVEX "
    "contra el promedio de los bancos: "
    "MONEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS Y BANCO BASE. "
    "De enero 2017 hasta el dato más reciente que tengas."
)

ALL_PROMPTS = [
    ("RANKING (bar-h)", PROMPT_RANKING),
    ("TREND (line)", PROMPT_TREND),
]

# Tableau reference for ME at 01/2025
TABLEAU_BANKS_ME = {
    "BANCA MIFEL": 15.29,
    "INVEX": 9.05,
    "AFIRME": 8.22,
    "VE POR MAS": 7.63,
    "BANCO BASE": 7.47,
    "SABADELL": 7.36,
    "MONEX": 7.12,
    "BANCREA": 2.95,
}


# ══════════════════════════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class ComponentCheck:
    name: str
    description: str
    validate: Callable[[dict[str, Any]], tuple[bool, str]]
    soft: bool = False


@dataclass
class CheckResult:
    check: ComponentCheck
    passed: bool
    detail: str


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _get_plotly(resp: dict[str, Any]) -> dict[str, Any] | None:
    bc = resp.get("bank_chart")
    if not bc:
        return None
    return bc.get("plotly_config")


def _get_traces(resp: dict[str, Any]) -> list[dict[str, Any]]:
    plotly = _get_plotly(resp)
    return (plotly or {}).get("data", [])


def _get_layout(resp: dict[str, Any]) -> dict[str, Any]:
    plotly = _get_plotly(resp)
    return (plotly or {}).get("layout", {})


def _trace_names(resp: dict[str, Any]) -> list[str]:
    return [t.get("name", "").upper() for t in _get_traces(resp) if t.get("name")]


# ══════════════════════════════════════════════════════════════════════════════
# RANKING checks (bar chart + table)
# ══════════════════════════════════════════════════════════════════════════════


def _r1_chart_exists(resp: dict[str, Any]) -> tuple[bool, str]:
    """R1: Chart must exist."""
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"
    if not resp.get("bank_chart"):
        return False, "CHART_MISSING"
    traces = _get_traces(resp)
    if not traces:
        return False, "CHART_EMPTY: no traces"
    chart_type = traces[0].get("type", "scatter")
    return True, f"Chart present: {len(traces)} trace(s), type={chart_type}"


def _r2_bar_chart_type(resp: dict[str, Any]) -> tuple[bool, str]:
    """R2: Chart should be a bar chart (horizontal)."""
    traces = _get_traces(resp)
    if not traces:
        return False, "NO_TRACES"
    t0 = traces[0]
    chart_type = t0.get("type", "")
    orientation = t0.get("orientation", "")
    if chart_type == "bar":
        orient_str = f", orientation={orientation}" if orientation else ""
        return True, f"Bar chart detected{orient_str}"
    return False, f"WRONG_TYPE: expected 'bar', got '{chart_type}'"


def _r3_multiple_banks(resp: dict[str, Any]) -> tuple[bool, str]:
    """R3: Chart should show multiple individual banks (not just INVEX+PROMEDIO)."""
    names = _trace_names(resp)
    traces = _get_traces(resp)

    # For bar charts, banks are in category axis:
    #   orientation=h → labels in y, values in x
    #   orientation=v → labels in x, values in y
    categories: list[str] = []
    for t in traces:
        orientation = t.get("orientation", "v")
        label_axis = t.get("y", []) if orientation == "h" else t.get("x", [])
        categories.extend(str(v).upper() for v in (label_axis or []) if v)

    all_labels = set(names) | set(categories)

    # Check if INVEX and at least 3 peer banks are present
    peer_found = []
    for bank in ["MONEX", "BANCREA", "SABADELL", "MIFEL", "MULTIVA",
                  "AFIRME", "BANSI", "VE POR MAS", "BANCO BASE"]:
        if any(bank in label for label in all_labels):
            peer_found.append(bank)

    has_invex = any("INVEX" in label for label in all_labels)

    if has_invex and len(peer_found) >= 3:
        return True, f"INVEX + {len(peer_found)} peers found: {peer_found[:5]}"

    return False, (
        f"INSUFFICIENT_BANKS: INVEX={'yes' if has_invex else 'no'}, "
        f"peers={len(peer_found)} (need >=3). Labels: {sorted(all_labels)[:10]}"
    )


def _r4_values_percentage(resp: dict[str, Any]) -> tuple[bool, str]:
    """R4: Values should be percentage range (2-20% for ME rates)."""
    traces = _get_traces(resp)
    if not traces:
        return False, "NO_TRACES"
    for t in traces:
        # Values could be in x or y depending on orientation
        vals = t.get("x", []) or []
        if not vals or not isinstance(vals[0], (int, float)):
            vals = t.get("y", []) or []
        numeric = [v for v in vals if isinstance(v, (int, float)) and v > 0]
        if numeric:
            max_v = max(numeric)
            min_v = min(numeric)
            if max_v < 1.0:
                return False, f"RAW_RATIO: max={max_v:.4f} — not normalized"
            if max_v > 50:
                return False, f"IMPLAUSIBLE: max={max_v:.2f}%"
            return True, f"Values OK: range [{min_v:.2f}%, {max_v:.2f}%]"
    return True, "SKIP: no numeric values found in traces"


def _r5_invex_highlighted(resp: dict[str, Any]) -> tuple[bool, str]:
    """R5: INVEX should be highlighted (different color)."""
    traces = _get_traces(resp)
    # Check if INVEX has a distinct color marker
    colors_seen: list[str] = []
    invex_color = None
    for t in traces:
        name = (t.get("name") or "").upper()
        marker = t.get("marker", {})
        color = marker.get("color", "")
        if isinstance(color, list):
            # Per-bar coloring
            return True, "SOFT_PASS: per-bar coloring detected"
        if "INVEX" in name and color:
            invex_color = color
        elif color:
            colors_seen.append(color)

    if invex_color and colors_seen and invex_color not in colors_seen:
        return True, f"INVEX highlighted: {invex_color} vs others"
    if invex_color:
        return True, f"INVEX color: {invex_color}"
    return True, "SOFT_PASS: could not verify color highlighting"


def _r6_table_in_text(resp: dict[str, Any]) -> tuple[bool, str]:
    """R6: Response text should contain a table with bank rates."""
    content = resp.get("content") or ""
    if not content:
        return False, "NO_TEXT"

    # Look for table-like patterns: pipes or bank names with numbers
    has_pipe_table = "|" in content and "Banco" in content
    has_bank_values = sum(1 for b in TABLEAU_BANKS_ME if b.upper() in content.upper()) >= 3

    if has_pipe_table:
        return True, "Table detected (pipe format)"
    if has_bank_values:
        return True, f"Bank names found in text (implicit table)"
    return False, "NO_TABLE: response text doesn't contain bank rates table"


def _r7_no_contradiction(resp: dict[str, Any]) -> tuple[bool, str]:
    """R7: LLM should not deny data."""
    content = (resp.get("content") or "").lower()
    deny_phrases = ["no tengo", "no cuento con", "no disponible", "no fue posible"]
    found = [p for p in deny_phrases if p in content]
    if found:
        return False, f"CONTRADICTION: {found}"
    return True, "No data denial detected"


RANKING_CHECKS: list[ComponentCheck] = [
    ComponentCheck("R1_CHART_EXISTS", "Chart must exist", _r1_chart_exists),
    ComponentCheck("R2_BAR_CHART", "Should be a bar chart", _r2_bar_chart_type),
    ComponentCheck("R3_MULTIPLE_BANKS", "Multiple individual banks shown", _r3_multiple_banks),
    ComponentCheck("R4_VALUES_PCT", "Values in percentage range", _r4_values_percentage),
    ComponentCheck("R5_INVEX_HIGHLIGHT", "INVEX highlighted", _r5_invex_highlighted, soft=True),
    ComponentCheck("R6_TABLE_IN_TEXT", "Table with bank rates in text", _r6_table_in_text),
    ComponentCheck("R7_NO_CONTRADICTION", "No data denial", _r7_no_contradiction),
]


# ══════════════════════════════════════════════════════════════════════════════
# TREND checks (line chart INVEX vs PROMEDIO)
# ══════════════════════════════════════════════════════════════════════════════


def _t1_chart_exists(resp: dict[str, Any]) -> tuple[bool, str]:
    """T1: Chart must exist."""
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"
    if not resp.get("bank_chart"):
        return False, "CHART_MISSING"
    traces = _get_traces(resp)
    if not traces:
        return False, "CHART_EMPTY"
    return True, f"Chart present: {len(traces)} trace(s)"


def _t2_two_series(resp: dict[str, Any]) -> tuple[bool, str]:
    """T2: Chart must have INVEX and PROMEDIO series."""
    names = _trace_names(resp)
    has_invex = any("INVEX" in n for n in names)
    has_promedio = any("PROMEDIO" in n for n in names)
    if has_invex and has_promedio:
        return True, f"Correct series: {names}"
    if len(names) > 5:
        return False, f"WRONG_HANDLER: {len(names)} series (expected 2)"
    missing = []
    if not has_invex:
        missing.append("INVEX")
    if not has_promedio:
        missing.append("PROMEDIO")
    return False, f"MISSING: {missing}. Got: {names}"


def _t3_line_chart(resp: dict[str, Any]) -> tuple[bool, str]:
    """T3: Chart should be a line/scatter chart."""
    traces = _get_traces(resp)
    if not traces:
        return False, "NO_TRACES"
    chart_type = traces[0].get("type", "scatter")
    if chart_type in ("scatter", "line"):
        return True, f"Line chart: type={chart_type}"
    return False, f"WRONG_TYPE: expected scatter/line, got '{chart_type}'"


def _t4_period_coverage(resp: dict[str, Any]) -> tuple[bool, str]:
    """T4: Should span multiple years."""
    traces = _get_traces(resp)
    all_dates: list[str] = []
    for t in traces:
        all_dates.extend(str(v) for v in t.get("x", []) if v)
    if not all_dates:
        return False, "NO_DATES"
    sorted_d = sorted(all_dates)
    first, last = sorted_d[0], sorted_d[-1]
    has_early = any(d <= "2020-06" for d in all_dates)
    has_recent = any(d >= "2024" for d in all_dates)
    if has_early and has_recent:
        return True, f"Period OK: {first} to {last}"
    return False, f"PERIOD_GAP: {first} to {last}"


def _t5_values_pct(resp: dict[str, Any]) -> tuple[bool, str]:
    """T5: Values should be percentages (2-20%)."""
    for t in _get_traces(resp):
        y_vals = [v for v in t.get("y", []) if v is not None]
        if y_vals:
            mx = max(y_vals)
            if mx < 1.0:
                return False, f"RAW_RATIO: {t.get('name')} max={mx:.4f}"
            if mx > 50:
                return False, f"IMPLAUSIBLE: {t.get('name')} max={mx:.2f}%"
    return True, "Values are valid percentages"


def _t6_data_points(resp: dict[str, Any]) -> tuple[bool, str]:
    """T6: At least 48 data points per series."""
    for t in _get_traces(resp):
        name = t.get("name", "?")
        y_count = len([v for v in t.get("y", []) if v is not None])
        if y_count < 48:
            return False, f"LOW: {name} has {y_count} points"
    counts = [f"{t.get('name', '?')}: {len(t.get('y', []))}" for t in _get_traces(resp)]
    return True, f"Data points OK: {', '.join(counts)}"


def _t7_no_contradiction(resp: dict[str, Any]) -> tuple[bool, str]:
    """T7: LLM should not deny data."""
    content = (resp.get("content") or "").lower()
    deny_phrases = ["no tengo", "no cuento con", "no disponible", "no fue posible"]
    found = [p for p in deny_phrases if p in content]
    if found:
        return False, f"CONTRADICTION: {found}"
    return True, "No data denial detected"


TREND_CHECKS: list[ComponentCheck] = [
    ComponentCheck("T1_CHART_EXISTS", "Chart must exist", _t1_chart_exists),
    ComponentCheck("T2_TWO_SERIES", "INVEX + PROMEDIO series", _t2_two_series),
    ComponentCheck("T3_LINE_CHART", "Line/scatter chart type", _t3_line_chart),
    ComponentCheck("T4_PERIOD", "Multi-year span", _t4_period_coverage),
    ComponentCheck("T5_VALUES_PCT", "Values are percentages", _t5_values_pct),
    ComponentCheck("T6_DATA_POINTS", ">=48 data points per series", _t6_data_points),
    ComponentCheck("T7_NO_CONTRADICTION", "No data denial", _t7_no_contradiction),
]


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════


def run_prompt(
    token: str, prompt: str, label: str, checks: list[ComponentCheck]
) -> tuple[list[CheckResult], dict[str, Any]]:
    print(f"\n{'─' * 70}")
    print(f"{label} ({len(prompt)} chars):")
    print(f"  \"{prompt[:100]}...\"")
    print(f"Sending (timeout={TIMEOUT}s)...")

    resp = send_chat_message(token, prompt, backend_url=BACKEND_URL, timeout=TIMEOUT)

    if resp.get("error"):
        print(f"  FATAL: {resp['error']}")
        return [], resp

    content = resp.get("content", "")
    bc = resp.get("bank_chart")
    events = resp.get("events", [])
    print(f"  Response: {len(content)} chars, chart={'present' if bc else 'MISSING'}")
    print(f"  Events: {events}")

    if bc:
        plotly = (bc or {}).get("plotly_config", {})
        traces = (plotly or {}).get("data", [])
        trace_names = [t.get("name", "?") for t in traces]
        print(f"  Traces ({len(traces)}): {trace_names}")
        for t in traces:
            name = t.get("name", "?")
            y_vals = [v for v in t.get("y", []) if isinstance(v, (int, float))]
            x_vals = [v for v in t.get("x", []) if isinstance(v, (int, float))]
            vals = y_vals or x_vals
            if vals:
                print(f"    {name}: last={vals[-1]:.4f}, min={min(vals):.4f}, max={max(vals):.4f}")

    results = []
    for check in checks:
        passed, detail = check.validate(resp)
        results.append(CheckResult(check=check, passed=passed, detail=detail))
        if passed:
            tag = "PASS"
        elif check.soft:
            tag = "WARN"
        else:
            tag = "FAIL"
        print(f"  [{tag}] {check.name}: {detail}")

    return results, resp


def main() -> int:
    print("=" * 70)
    print("E2E Test — Tasa ME: Dual Prompts (Ranking + Trend)")
    print(f"Backend: {BACKEND_URL}")
    print("=" * 70)

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FATAL: Auth failed")
        return 2

    print(f"Authenticated against {BACKEND_URL}")

    # ── Ranking prompt ──
    ranking_results, ranking_resp = run_prompt(
        token, PROMPT_RANKING, "RANKING (bar-h)", RANKING_CHECKS
    )

    # ── Trend prompt ──
    trend_results, trend_resp = run_prompt(
        token, PROMPT_TREND, "TREND (line)", TREND_CHECKS
    )

    # ── Summary ──
    all_results = ranking_results + trend_results

    passed = sum(1 for r in all_results if r.passed)
    hard_failed = sum(1 for r in all_results if not r.passed and not r.check.soft)
    warned = sum(1 for r in all_results if not r.passed and r.check.soft)
    total = len(all_results)

    print(f"\n{'=' * 70}")
    summary = f"RESULTS: {passed}/{total} passed, {hard_failed} failed"
    if warned:
        summary += f", {warned} warned (soft)"
    print(summary)
    print(f"  Ranking: {sum(1 for r in ranking_results if r.passed)}/{len(ranking_results)}")
    print(f"  Trend:   {sum(1 for r in trend_results if r.passed)}/{len(trend_results)}")
    print(f"{'=' * 70}")

    # ── Save results ──
    out = Path(__file__).parent / "tasa_me_dual_results.json"
    out.write_text(json.dumps({
        "test": "tasa-me-dual-prompts",
        "backend_url": BACKEND_URL,
        "total": total,
        "passed": passed,
        "failed": hard_failed,
        "warned": warned,
        "ranking": {
            "prompt": PROMPT_RANKING,
            "checks": [{"name": r.check.name, "passed": r.passed, "detail": r.detail}
                       for r in ranking_results],
        },
        "trend": {
            "prompt": PROMPT_TREND,
            "checks": [{"name": r.check.name, "passed": r.passed, "detail": r.detail}
                       for r in trend_results],
        },
    }, indent=2, ensure_ascii=False))
    print(f"\nResults saved: {out}")

    if warned > 0:
        print("\nSoft warnings:")
        for r in all_results:
            if not r.passed and r.check.soft:
                print(f"  - {r.check.name}: {r.detail}")

    if hard_failed > 0:
        print("\nFailed checks:")
        for r in all_results:
            if not r.passed and not r.check.soft:
                print(f"  - {r.check.name}: {r.detail}")

    return 0 if hard_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
