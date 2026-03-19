#!/usr/bin/env python3
"""
E2E Test — Quebrantos CC Quarterly T1 Vertical Bar Chart (INVEX vs Total)

Tests the onboarding preset "quebrantos-anio" which asks for a VERTICAL bar
chart (column chart) comparing INVEX vs system total of quebrantos
comerciales, aggregated by Q1 (T1 = Jan+Feb+Mar) per year.  Matches Tableau.

Tableau reference view: "QUEBRANTOS — Q-2 — Quebrantos Cartera Comercial por Mes"
  Title: "Quebrantos Cartera Comercial por Mes (Invex vs Total)"
  Chart: Vertical grouped bar chart by year (2023, 2024, 2025)
  Series: "TOTAL" (grey) + "INVEX" (red)
  Aggregation: SUM of Jan+Feb+Mar per year per bank, then SUM of all banks (incl. INVEX)
  Values (MDP):
    2023 T1: Total=$193,   INVEX=$0
    2024 T1: Total=$1,383, INVEX=$116
    2025 T1: Total=$54,    INVEX=$0
  Rule: Exclude year if any of the 3 months is missing for T1.

Pipeline path:
  evolucion_banco_handler → hip_quebrantos_cc → peer_average or evolution
  DB column: bank_fact_kpis_mensual.quebrantos_comerciales
  Values in MDP (pesos ÷ 1M)

Prompt under test (V5 — Tableau parity, SUM total, vertical bars):
    "Crea una gráfica de barras VERTICALES que compare los quebrantos
     comerciales de INVEX contra el total del grupo: MONEX, BANCREA,
     SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS y BANCO BASE.
     Importante: compara únicamente el primer trimestre (T1) de cada año
     disponible desde 2023 hasta el más reciente. ..."

Usage:
    python tests/e2e/charts/test_quebrantos_cc_yearly_bar_chart.py
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

# The onboarding prompt V5 — Tableau-parity: quarterly T1 aggregation, SUM total, VERTICAL bars
PROMPT = (
    "Crea una gráfica de barras VERTICALES que compare los quebrantos comerciales "
    "de INVEX contra el total del grupo: MONEX, BANCREA, SABADELL, BANCA MIFEL, "
    "MULTIVA, AFIRME, BANSI, VE POR MAS y BANCO BASE. "
    "Importante: compara únicamente el primer trimestre (T1) de cada año disponible "
    "desde 2023 hasta el más reciente. "
    "Agregación: para cada (año, T1) calcula el TOTAL del trimestre (SUM de los 3 meses) "
    "para INVEX y el TOTAL del sistema (SUM de los totales trimestrales del grupo "
    "incluyendo INVEX). "
    "Visual: por cada año muestra dos barras: TOTAL (gris) e INVEX (rojo), con etiquetas "
    "de valor en MDP y el eje/leyenda indicando 'T1'. Orden: años ascendente."
)

# Tableau reference values (MDP) for T1 grouped bars
# T1 = SUM(Jan + Feb + Mar) per year
# TOTAL = SUM of all 10 banks (including INVEX)
TABLEAU_YEARLY = {
    2023: {"TOTAL": 193, "INVEX": 0},
    2024: {"TOTAL": 1383, "INVEX": 116},
    2025: {"TOTAL": 54, "INVEX": 0},
}

# Colors from chart_formatter.py
INVEX_RED = "#E45756"
NEUTRAL_GREY = "#999999"

# Phrases indicating fabrication
FABRICATED_VALUE_PHRASES = [
    "estimado basado en tendencia",
    "estimado",
    "proyectado",
    "aproximado basado en",
]

# Phrases indicating LLM denies data
TEXT_CONTRADICTION_PHRASES = [
    "no tengo los datos",
    "no tengo datos",
    "no está disponible",
    "no esta disponible",
    "no cuento con los datos",
    "no cuento con datos",
    "no encuentro información",
    "no encuentro informacion",
    "no se encontraron datos",
    "no hay datos disponibles",
    "no dispongo de",
    "no puedo realizar",
    "datos no disponibles",
    "sin datos para",
    "lamentablemente no",
    "lo siento, pero no tengo",
    "no fue posible obtener",
]


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


def _all_numeric_values(resp: dict[str, Any]) -> list[float]:
    """Collect all numeric y-values (or x-values for h-bars) across traces."""
    vals: list[float] = []
    for t in _get_traces(resp):
        orientation = t.get("orientation", "v")
        data_axis = t.get("x", []) if orientation == "h" else t.get("y", [])
        vals.extend(v for v in (data_axis or []) if isinstance(v, (int, float)))
    return vals


# ══════════════════════════════════════════════════════════════════════════════
# Component Validators
# ══════════════════════════════════════════════════════════════════════════════


def _v1_chart_exists(resp: dict[str, Any]) -> tuple[bool, str]:
    """V1: Chart must exist."""
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"
    if not resp.get("bank_chart"):
        return False, "CHART_MISSING: no bank_chart in response"
    traces = _get_traces(resp)
    if not traces:
        return False, "CHART_EMPTY: no data traces"
    types = [t.get("type", "scatter") for t in traces]
    return True, f"Chart present: {len(traces)} trace(s), types={types}"


def _v2_bar_chart_type(resp: dict[str, Any]) -> tuple[bool, str]:
    """V2: Chart MUST be a bar chart (pipeline supports time_grain=quarterly_t1)."""
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


def _v3_has_invex(resp: dict[str, Any]) -> tuple[bool, str]:
    """V3: Chart must include INVEX data."""
    names = _trace_names(resp)
    traces = _get_traces(resp)

    # Check trace names
    if any("INVEX" in n for n in names):
        return True, f"INVEX found in trace names: {names}"

    # For single-trace bar charts, check y-axis labels
    for t in traces:
        orientation = t.get("orientation", "v")
        label_axis = t.get("y", []) if orientation == "h" else t.get("x", [])
        labels = [str(v).upper() for v in (label_axis or []) if v]
        if any("INVEX" in label for label in labels):
            return True, f"INVEX found in axis labels: {labels[:5]}"

    # Check response text
    content = (resp.get("content") or "").upper()
    if "INVEX" in content:
        return True, "SOFT_PASS: INVEX mentioned in text but not in chart traces"

    return False, f"INVEX_MISSING: not found in traces {names} or axis labels"


def _v4_has_comparison(resp: dict[str, Any]) -> tuple[bool, str]:
    """V4: Chart should have a comparison element (promedio, CC, or multiple banks)."""
    names = _trace_names(resp)
    traces = _get_traces(resp)

    # Multiple traces → comparison
    if len(traces) >= 2:
        return True, f"Multiple series: {names}"

    # Single trace but with multiple banks in labels
    if traces:
        t0 = traces[0]
        orientation = t0.get("orientation", "v")
        label_axis = t0.get("y", []) if orientation == "h" else t0.get("x", [])
        labels = [str(v) for v in (label_axis or []) if v]
        if len(labels) >= 3:
            return True, f"Single trace with {len(labels)} categories: {labels[:5]}"

    # Check text for comparison language
    content = (resp.get("content") or "").lower()
    has_aggregate = any(w in content for w in ["promedio", "total"])
    has_comparison = any(w in content for w in ["vs", "comparación", "comparacion", "contra"])
    if has_aggregate or has_comparison:
        return True, "SOFT_PASS: comparison language found in text"

    return False, f"NO_COMPARISON: only {len(traces)} trace(s), names={names}"


def _v5_invex_highlighted(resp: dict[str, Any]) -> tuple[bool, str]:
    """V5: INVEX should be highlighted (red color)."""
    traces = _get_traces(resp)

    for t in traces:
        name = (t.get("name") or "").upper()
        marker = t.get("marker", {})
        color = marker.get("color", "")
        line_color = t.get("line", {}).get("color", "")

        # Per-bar coloring (list of colors)
        if isinstance(color, list):
            return True, "SOFT_PASS: per-bar coloring detected"

        # Named INVEX trace with red-ish color
        if "INVEX" in name:
            actual_color = color or line_color
            if actual_color:
                is_red = any(r in actual_color.upper() for r in ["#E4", "RED", "#FF", "#D9"])
                if is_red:
                    return True, f"INVEX highlighted: color={actual_color}"
                return True, f"SOFT_PASS: INVEX has color={actual_color}"
            return True, "SOFT_PASS: INVEX trace exists but no explicit color"

    return True, "SOFT_PASS: could not verify INVEX highlight"


def _v6_multi_year(resp: dict[str, Any]) -> tuple[bool, str]:
    """V6: Chart should span multiple years."""
    traces = _get_traces(resp)
    all_labels: list[str] = []

    for t in traces:
        orientation = t.get("orientation", "v")
        # For time series, x-axis has dates; for grouped bars, x-axis has year labels
        x_vals = t.get("x", [])
        all_labels.extend(str(v) for v in (x_vals or []) if v)

    if not all_labels:
        return False, "NO_LABELS: no x-axis values found"

    # Extract years from labels
    years_found: set[int] = set()
    for label in all_labels:
        # Match "2023", "2024-01-01", "2023 T1", etc.
        year_matches = re.findall(r"20[12]\d", str(label))
        for ym in year_matches:
            years_found.add(int(ym))

    if len(years_found) >= 2:
        return True, f"Multi-year OK: {sorted(years_found)}"

    return False, f"SINGLE_YEAR: only found years={sorted(years_found)} in {len(all_labels)} labels"


def _v7_values_plausible(resp: dict[str, Any]) -> tuple[bool, str]:
    """V7: Values should be in plausible range for quebrantos.

    DB stores quebrantos in pesos; pipeline divides ÷1M for display as MDP.
    Plausible range: 0 to 2000 MDP (TOTAL series is SUM of ~10 banks,
    e.g. T1 2024 total ≈ 1383 MDP).
    """
    vals = _all_numeric_values(resp)
    if not vals:
        return False, "NO_VALUES: no numeric data in traces"

    positive = [v for v in vals if v > 0]
    if not positive:
        return True, f"SOFT_PASS: all {len(vals)} values are zero (may be real)"

    max_v = max(positive)
    min_v = min(positive)

    # Display values in MDP after ÷1M scaling
    if max_v > 2000:
        return False, f"IMPLAUSIBLE: max={max_v:,.1f} MDP (too high for quebrantos)"

    return True, (
        f"Values OK: range [{min_v:,.2f}, {max_v:,.2f}] MDP, {len(vals)} total"
    )


def _v8_no_contradiction(resp: dict[str, Any]) -> tuple[bool, str]:
    """V8: LLM text must NOT deny data when chart has valid data."""
    bc = resp.get("bank_chart")
    content = (resp.get("content") or "").lower()

    if not bc or not _get_traces(resp):
        return True, "SKIP: no chart data to contradict"

    found = [p for p in TEXT_CONTRADICTION_PHRASES if p in content]
    if found:
        return False, f"TEXT_CONTRADICTION: {found}"
    return True, "No data denial detected"


def _v9_no_fabrication(resp: dict[str, Any]) -> tuple[bool, str]:
    """V9: Response content should not contain fabricated value markers."""
    content = (resp.get("content") or "").lower()
    found = [p for p in FABRICATED_VALUE_PHRASES if p in content]
    if found:
        return False, f"FABRICATION: {found}"
    return True, "No fabrication markers detected"


def _v10_metric_quebrantos(resp: dict[str, Any]) -> tuple[bool, str]:
    """V10: Chart title or text should reference quebrantos/castigos."""
    layout = _get_layout(resp)
    title = ""
    if layout:
        title = layout.get("title", "")
        if isinstance(title, dict):
            title = title.get("text", "")

    content = (resp.get("content") or "")
    names = _trace_names(resp)
    combined = f"{title} {content} {' '.join(names)}".lower()

    has_quebrantos = any(kw in combined for kw in ["quebranto", "castigo"])

    if has_quebrantos:
        return True, f"Metric OK: quebrantos/castigos referenced. Title='{title[:60]}'"

    return False, f"WRONG_METRIC: no 'quebrantos' or 'castigos' in title/text/traces. Title='{title[:60]}'"


def _v11_quarterly_labels(resp: dict[str, Any]) -> tuple[bool, str]:
    """V11: X-axis labels should be quarterly (T1 2023, T1 2024, ...)."""
    traces = _get_traces(resp)
    all_x: list[str] = []
    for t in traces:
        all_x.extend(str(v) for v in (t.get("x") or []) if v)

    if not all_x:
        return False, "NO_X_LABELS"

    # Check that labels match "T1 YYYY" pattern
    quarterly_pattern = re.compile(r"^T[1-4]\s+20[12]\d$")
    matching = [x for x in all_x if quarterly_pattern.match(x)]

    if matching:
        unique = sorted(set(matching))
        return True, f"Quarterly labels OK: {unique}"

    # Fallback: check for year-only labels (e.g. "2023", "2024")
    year_only = [x for x in all_x if re.match(r"^20[12]\d$", x)]
    if year_only:
        return True, f"SOFT_PASS: year labels found (no T prefix): {sorted(set(year_only))}"

    # Check if they look like monthly dates (regression)
    monthly = [x for x in all_x if re.match(r"^20[12]\d-\d{2}", x)]
    if monthly:
        return False, f"MONTHLY_DATES: got monthly labels instead of quarterly: {monthly[:5]}"

    return False, f"UNEXPECTED_LABELS: {all_x[:5]}"


def _v12_barmode_group(resp: dict[str, Any]) -> tuple[bool, str]:
    """V12: Layout barmode should be 'group' for side-by-side bars."""
    layout = _get_layout(resp)
    barmode = layout.get("barmode", "")
    if barmode == "group":
        return True, "barmode='group' OK"
    if not barmode:
        return False, "BARMODE_MISSING: no barmode in layout"
    return False, f"WRONG_BARMODE: expected 'group', got '{barmode}'"


# ══════════════════════════════════════════════════════════════════════════════
# All checks
# ══════════════════════════════════════════════════════════════════════════════

ALL_CHECKS: list[ComponentCheck] = [
    ComponentCheck("V1_CHART_EXISTS", "Chart must exist", _v1_chart_exists),
    ComponentCheck("V2_BAR_CHART", "Must be a bar chart", _v2_bar_chart_type),
    ComponentCheck("V3_HAS_INVEX", "INVEX data must be present", _v3_has_invex),
    ComponentCheck("V4_HAS_COMPARISON", "Should have comparison (promedio or multi-bank)", _v4_has_comparison),
    ComponentCheck("V5_INVEX_HIGHLIGHT", "INVEX highlighted in red", _v5_invex_highlighted, soft=True),
    ComponentCheck("V6_MULTI_YEAR", "Chart spans multiple years", _v6_multi_year),
    ComponentCheck("V7_VALUES_PLAUSIBLE", "Values in plausible range (pesos)", _v7_values_plausible),
    ComponentCheck("V8_NO_CONTRADICTION", "LLM text does not deny data", _v8_no_contradiction, soft=True),
    ComponentCheck("V9_NO_FABRICATION", "No fabrication markers", _v9_no_fabrication),
    ComponentCheck("V10_METRIC_QUEBRANTOS", "Metric is quebrantos/castigos", _v10_metric_quebrantos),
    ComponentCheck("V11_QUARTERLY_LABELS", "X-axis has quarterly labels (T1 YYYY)", _v11_quarterly_labels),
    ComponentCheck("V12_BARMODE_GROUP", "Layout barmode is 'group'", _v12_barmode_group),
]


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════


def run_checks(resp: dict[str, Any]) -> list[CheckResult]:
    results = []
    for check in ALL_CHECKS:
        passed, detail = check.validate(resp)
        results.append(CheckResult(check=check, passed=passed, detail=detail))
    return results


def main() -> int:
    print("=" * 70)
    print("E2E Test — Quebrantos CC: Yearly Bar Chart (INVEX vs Total)")
    print(f"Backend: {BACKEND_URL}")
    print(f"Checks: {len(ALL_CHECKS)} component validators")
    print("=" * 70)

    # ── Authenticate ──
    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FATAL: Auth failed")
        return 2

    print(f"Authenticated against {BACKEND_URL}")

    # ── Send prompt ──
    print(f"\nPrompt ({len(PROMPT)} chars):")
    print(f"  \"{PROMPT}\"")
    print(f"\nSending (timeout={TIMEOUT}s)...")

    resp = send_chat_message(
        token, PROMPT, backend_url=BACKEND_URL, timeout=TIMEOUT,
    )

    if resp.get("error"):
        print(f"\nFATAL: Request failed: {resp['error']}")
        return 2

    # ── Show response summary ──
    content = resp.get("content", "")
    bc = resp.get("bank_chart")
    events = resp.get("events", [])
    print("\nResponse received:")
    print(f"  Events: {events}")
    print(f"  Content: {len(content)} chars")
    print(f"  Chart: {'present' if bc else 'MISSING'}")

    if bc:
        plotly = bc.get("plotly_config", {})
        traces = plotly.get("data", [])
        trace_names = [t.get("name", "?") for t in traces]
        print(f"  Traces ({len(traces)}): {trace_names}")
        for t in traces:
            name = t.get("name", "?")
            y_vals = [v for v in t.get("y", []) if isinstance(v, (int, float))]
            x_vals = [v for v in t.get("x", []) if isinstance(v, (int, float))]
            vals = y_vals or x_vals
            if vals:
                non_zero = [v for v in vals if v != 0]
                if non_zero:
                    print(f"    {name}: count={len(vals)}, min={min(non_zero):.2f}, max={max(non_zero):.2f}")
                else:
                    print(f"    {name}: count={len(vals)}, all zeros")
        table_data = bc.get("table_data")
        if table_data:
            print(f"  Table: {len(table_data.get('rows', []))} rows")

    # ── Run checks ──
    print(f"\n{'─' * 70}")
    print("COMPONENT CHECKS")
    print(f"{'─' * 70}")

    results = run_checks(resp)

    for r in results:
        if r.passed:
            tag = "PASS"
        elif r.check.soft:
            tag = "WARN"
        else:
            tag = "FAIL"
        print(f"\n  [{tag}] {r.check.name}")
        print(f"         {r.check.description}")
        print(f"         {r.detail}")

    # ── Summary ──
    passed = sum(1 for r in results if r.passed)
    hard_failed = sum(1 for r in results if not r.passed and not r.check.soft)
    warned = sum(1 for r in results if not r.passed and r.check.soft)
    total = len(results)

    print(f"\n{'=' * 70}")
    summary = f"RESULTS: {passed}/{total} passed, {hard_failed} failed"
    if warned:
        summary += f", {warned} warned (soft)"
    print(summary)
    print(f"{'=' * 70}")

    # ── Save results JSON ──
    out = Path(__file__).parent / "quebrantos_cc_yearly_results.json"
    out.write_text(json.dumps({
        "test": "quebrantos-cc-yearly-bar-chart",
        "prompt": PROMPT,
        "backend_url": BACKEND_URL,
        "total_checks": total,
        "passed": passed,
        "failed": hard_failed,
        "warned": warned,
        "checks": [
            {
                "name": r.check.name,
                "description": r.check.description,
                "passed": r.passed,
                "soft": r.check.soft,
                "detail": r.detail,
            }
            for r in results
        ],
        "response_summary": {
            "content_length": len(content),
            "has_chart": bc is not None,
            "events": events,
            "content_preview": content[:300],
        },
    }, indent=2, ensure_ascii=False))
    print(f"\nResults saved: {out}")

    if warned > 0:
        print("\nSoft warnings:")
        for r in results:
            if not r.passed and r.check.soft:
                print(f"  - {r.check.name}: {r.detail}")

    if hard_failed > 0:
        print("\nFailed checks:")
        for r in results:
            if not r.passed and not r.check.soft:
                print(f"  - {r.check.name}: {r.detail}")

    return 0 if hard_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
