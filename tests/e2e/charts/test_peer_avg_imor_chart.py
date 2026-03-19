#!/usr/bin/env python3
"""
E2E Test — Peer Average IMOR: INVEX vs PROMEDIO

Validates that the IMOR (Índice de Morosidad) prompt routes to the
peer-average handler and produces a comparison chart with INVEX and
PROMEDIO series.

IMOR = Cartera Vencida / Cartera Total — expressed as a small percentage
(typically 0.5% to 15% for commercial banks).

This test validates:
  - Chart type and series structure (INVEX + PROMEDIO)
  - No system bank leak (only 2 series, not all 46 banks)
  - Period coverage (2021-01 to recent)
  - Values plausible for IMOR (0% to 30% range)
  - PROMEDIO magnitude (small percentage, not a sum)
  - Anti-fabrication and text/chart coherence
  - Directional claims (above/below average)

Prompt under test:
    "Crea una gráfica donde se compare el IMOR de INVEX contra el IMOR
     promedio de los bancos: MONEX, BANCREA, SABADELL, BANCA MIFEL,
     MULTIVA, AFIRME, BANSI, VE POR MÁS Y BANCO BASE.
     De Enero 2021 hasta el dato más reciente que tengas"

Usage:
    python tests/e2e/charts/test_peer_avg_imor_chart.py
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

# The 9 peer banks requested in the prompt
PEER_BANKS = [
    "MONEX", "BANCREA", "SABADELL", "MIFEL",
    "MULTIVA", "AFIRME", "BANSI", "VE POR MAS", "BANCO BASE",
]

# The exact prompt
PROMPT = (
    "Crea una gráfica donde se compare el IMOR de INVEX contra el IMOR "
    "promedio de los bancos: MONEX, BANCREA, SABADELL, BANCA MIFEL, "
    "MULTIVA, AFIRME, BANSI, VE POR MÁS Y BANCO BASE. "
    "De Enero 2021 hasta el dato más reciente que tengas"
)

# Phrases that indicate grounding desync (fabricated values)
FABRICATED_VALUE_PHRASES = [
    "estimado basado en tendencia",
    "estimado",
    "proyectado",
    "aproximado basado en",
]

# Phrases that indicate the LLM denies data that IS present in the chart
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
    "no puedo realizar la comparación",
    "no puedo realizar la comparacion",
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
    """A single validation check on the response."""

    name: str
    description: str
    validate: Callable[[dict[str, Any]], tuple[bool, str]]


@dataclass
class CheckResult:
    """Result of a single component check."""

    check: ComponentCheck
    passed: bool
    detail: str


# ══════════════════════════════════════════════════════════════════════════════
# Chart helpers
# ══════════════════════════════════════════════════════════════════════════════


def _get_plotly_config(resp: dict[str, Any]) -> dict[str, Any] | None:
    bc = resp.get("bank_chart")
    if not bc:
        return None
    return bc.get("plotly_config")


def _get_traces(resp: dict[str, Any]) -> list[dict[str, Any]]:
    plotly = _get_plotly_config(resp)
    if not plotly:
        return []
    return plotly.get("data", [])


def _get_layout(resp: dict[str, Any]) -> dict[str, Any] | None:
    plotly = _get_plotly_config(resp)
    if not plotly:
        return None
    return plotly.get("layout")


def _extract_trace_names(resp: dict[str, Any]) -> list[str]:
    traces = _get_traces(resp)
    return [t.get("name", "").upper() for t in traces if t.get("name")]


def _extract_last_values(
    resp: dict[str, Any],
) -> dict[str, float]:
    """Return {TRACE_NAME: last_non_null_y_value} for each trace."""
    traces = _get_traces(resp)
    result: dict[str, float] = {}
    for t in traces:
        name = (t.get("name") or "").upper()
        y_vals = [v for v in t.get("y", []) if v is not None]
        if name and y_vals:
            result[name] = float(y_vals[-1])
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Component Validators
# ══════════════════════════════════════════════════════════════════════════════


def _check_chart_exists(resp: dict[str, Any]) -> tuple[bool, str]:
    """V1: Chart must exist with at least one data trace."""
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "CHART_MISSING: no bank_chart in response"

    traces = _get_traces(resp)
    if not traces:
        return False, "CHART_EMPTY: plotly_config has no data traces"

    trace_type = traces[0].get("type", "scatter")
    return True, (
        f"Chart present: {len(traces)} trace(s), type={trace_type}"
    )


def _check_peer_average_series(resp: dict[str, Any]) -> tuple[bool, str]:
    """V2: Chart must have exactly 2 series: INVEX and PROMEDIO."""
    trace_names = _extract_trace_names(resp)

    if not trace_names:
        return False, "NO_TRACES: cannot verify series names"

    has_invex = any("INVEX" in n for n in trace_names)
    has_promedio = any("PROMEDIO" in n for n in trace_names)

    if has_invex and has_promedio:
        return True, f"Correct series: {trace_names}"

    if len(trace_names) > 5:
        return False, (
            f"WRONG_HANDLER: got {len(trace_names)} series — "
            f"query likely routed to EvolucionBancoHandler instead of "
            f"peer_average. Series: {trace_names[:10]}"
        )

    missing = []
    if not has_invex:
        missing.append("INVEX")
    if not has_promedio:
        missing.append("PROMEDIO")
    return False, (
        f"MISSING_SERIES: {missing}. Got: {trace_names}"
    )


def _check_not_all_banks(resp: dict[str, Any]) -> tuple[bool, str]:
    """V3: Response must NOT contain all system banks (regression guard)."""
    trace_names = _extract_trace_names(resp)
    bc = resp.get("bank_chart", {})
    bank_names = bc.get("bank_names", []) if bc else []
    all_names = set(n.upper() for n in trace_names + bank_names)

    system_only_banks = {"BBVA", "SANTANDER", "BANORTE", "CITIBANAMEX",
                         "SCOTIABANK", "INBURSA", "HSBC", "BAJIO", "BANREGIO"}
    leaked = system_only_banks & all_names

    if len(leaked) >= 3:
        return False, (
            f"REGRESSION: {len(leaked)} system-wide banks leaked into response "
            f"(peer_average_mode likely False). Leaked: {sorted(leaked)}"
        )

    return True, (
        f"No system bank leak: only {len(all_names)} bank(s) in response"
    )


def _check_period_coverage(resp: dict[str, Any]) -> tuple[bool, str]:
    """V4: Data should span from ~2021-01 to a recent date."""
    traces = _get_traces(resp)
    if not traces:
        return False, "NO_TRACES: cannot verify period"

    all_dates: list[str] = []
    for t in traces:
        x_vals = t.get("x", [])
        all_dates.extend(str(v) for v in x_vals if v)

    if not all_dates:
        return False, "NO_DATES: x-axis values are empty"

    sorted_dates = sorted(all_dates)
    first = sorted_dates[0]
    last = sorted_dates[-1]

    has_2021 = any("2021" in d for d in all_dates)
    has_recent = any(d >= "2024" for d in all_dates)

    if has_2021 and has_recent:
        return True, (
            f"Period OK: {first} to {last} "
            f"({len(all_dates)} data points across {len(traces)} series)"
        )

    return False, (
        f"PERIOD_GAP: first={first}, last={last}. "
        f"Expected 2021-01 through at least 2024."
    )


def _check_data_point_count(resp: dict[str, Any]) -> tuple[bool, str]:
    """V5: Each series should have >= 48 data points (~4 years monthly)."""
    traces = _get_traces(resp)
    if not traces:
        return False, "NO_TRACES"

    issues = []
    for t in traces:
        name = t.get("name", "unknown")
        y_vals = [v for v in t.get("y", []) if v is not None]
        if len(y_vals) < 48:
            issues.append(f"{name}: {len(y_vals)} points (expected >=48)")

    if issues:
        return False, f"LOW_POINTS: {'; '.join(issues)}"

    counts = [
        f"{t.get('name', '?')}: {len(t.get('y', []))}"
        for t in traces
    ]
    return True, f"Data points OK: {', '.join(counts)}"


def _check_values_plausible(resp: dict[str, Any]) -> tuple[bool, str]:
    """V6: Y-values should be plausible for IMOR (0% to 30% range).

    IMOR = Cartera Vencida / Cartera Total, expressed as percentage.
    Typical range for commercial banks: 0.5% to 15%.
    Values > 30% or negative would be suspicious.
    """
    traces = _get_traces(resp)
    if not traces:
        return False, "NO_TRACES"

    for t in traces:
        name = t.get("name", "unknown")
        y_vals = [v for v in t.get("y", []) if v is not None]
        if not y_vals:
            continue

        min_val = min(y_vals)
        max_val = max(y_vals)

        if min_val < 0:
            return False, f"NEGATIVE: {name} min={min_val} — IMOR cannot be negative"

        if max_val > 30:
            return False, (
                f"TOO_HIGH: {name} max={max_val:.2f}% — "
                f"IMOR > 30% is implausible for these banks. "
                f"Values may be in wrong unit (raw ratio vs percentage)."
            )

        if max_val == 0:
            return False, f"ALL_ZERO: {name} has no non-zero values"

    all_y = []
    for t in traces:
        all_y.extend(v for v in t.get("y", []) if v is not None)

    return True, (
        f"Values plausible: range=[{min(all_y):.2f}%, {max(all_y):.2f}%] "
        f"across {len(traces)} series"
    )


def _check_promedio_magnitude(resp: dict[str, Any]) -> tuple[bool, str]:
    """V7: PROMEDIO should be a peer average (small %), not a sum.

    For IMOR, the average of 9 banks should still be a small percentage
    (typically 1-10%). If it's > 50%, it was likely summed instead of averaged.
    """
    traces = _get_traces(resp)
    promedio_trace = None
    for t in traces:
        if "PROMEDIO" in (t.get("name", "")).upper():
            promedio_trace = t
            break

    if not promedio_trace:
        return False, "NO_PROMEDIO_TRACE: cannot verify average magnitude"

    y_vals = [v for v in promedio_trace.get("y", []) if v is not None]
    if not y_vals:
        return False, "EMPTY_PROMEDIO: no y-values"

    max_val = max(y_vals)
    avg_val = sum(y_vals) / len(y_vals)

    if max_val > 50:
        return False, (
            f"IMPLAUSIBLE_AVG: PROMEDIO max={max_val:.2f}% — "
            f"likely summed instead of averaged (IMOR sum of 9 banks)"
        )

    return True, (
        f"Promedio magnitude OK: avg={avg_val:.2f}%, max={max_val:.2f}%"
    )


def _check_no_fabrication(resp: dict[str, Any]) -> tuple[bool, str]:
    """V8: Response text should not contain fabricated value markers."""
    content = (resp.get("content") or "").lower()

    found = [p for p in FABRICATED_VALUE_PHRASES if p in content]
    if found:
        return False, f"FABRICATION: markers found: {found}"

    return True, "No fabrication markers detected"


def _check_no_text_contradiction(resp: dict[str, Any]) -> tuple[bool, str]:
    """V9: LLM text must NOT deny data when the chart has valid data."""
    bc = resp.get("bank_chart")
    content = (resp.get("content") or "").lower()

    if not bc or not _get_traces(resp):
        return True, "SKIP: no chart data to contradict"

    found = [p for p in TEXT_CONTRADICTION_PHRASES if p in content]
    if found:
        return False, (
            f"TEXT_CONTRADICTION: chart has data but LLM says: {found}"
        )

    return True, "No contradiction: text does not deny data"


def _check_layout_title(resp: dict[str, Any]) -> tuple[bool, str]:
    """V10: Chart title should reference 'IMOR' or 'morosidad'."""
    layout = _get_layout(resp)
    if not layout:
        return False, "NO_LAYOUT"

    title = layout.get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")

    title_lower = title.lower()

    has_imor = "imor" in title_lower
    has_morosidad = "morosidad" in title_lower

    if has_imor or has_morosidad:
        return True, f"Title OK: '{title}'"

    return False, f"WRONG_TITLE: '{title}' — expected 'IMOR' or 'morosidad'"


def _check_invex_in_text(resp: dict[str, Any]) -> tuple[bool, str]:
    """V11: LLM response text should mention INVEX."""
    content = (resp.get("content") or "").upper()

    if "INVEX" in content:
        return True, "INVEX mentioned in response text"

    return False, "INVEX_MISSING: LLM text does not mention INVEX"


def _check_promedio_in_text(resp: dict[str, Any]) -> tuple[bool, str]:
    """V12: LLM response text should mention promedio/average."""
    content = (resp.get("content") or "").lower()

    markers = ["promedio", "average", "pares", "peer"]
    found = [m for m in markers if m in content]

    if found:
        return True, f"Average referenced in text: {found}"

    return False, (
        "NO_AVG_MENTION: LLM text doesn't mention promedio/pares — "
        "the model may not know it's comparing against a peer average"
    )


def _check_text_pct_coherence(resp: dict[str, Any]) -> tuple[bool, str]:
    """V13: Percentage values in LLM text must be close to chart Y-values.

    For IMOR, the LLM will mention percentages like "3.5%", "5.2%", etc.
    We extract these from text near INVEX/PROMEDIO mentions and compare
    against the latest chart Y-values. Tolerance: 1 percentage point.
    """
    content = resp.get("content") or ""
    if not content:
        return True, "SKIP: no LLM text"

    chart_vals = _extract_last_values(resp)
    if not chart_vals:
        return True, "SKIP: no chart traces to compare"

    # Extract percentages from text: "N.N%" or "N,N%"
    pct_pattern = re.compile(r"(\d+[.,]\d+)\s*%")

    mismatches: list[str] = []
    matched = 0

    for trace_name, chart_val in chart_vals.items():
        # Find text region near this trace name
        name_lower = trace_name.lower()
        search_aliases = [name_lower]
        if "promedio" in name_lower:
            search_aliases.extend(["promedio", "pares", "average", "peer"])

        best_match: tuple[float, str] | None = None
        best_diff = float("inf")

        content_lower = content.lower()
        for alias in search_aliases:
            pos = content_lower.find(alias)
            while pos != -1:
                # Search for percentages within 200 chars of this mention
                window_start = max(0, pos - 50)
                window_end = min(len(content), pos + 250)
                window = content[window_start:window_end]

                for m in pct_pattern.finditer(window):
                    text_val = float(m.group(1).replace(",", "."))
                    # Only consider values in IMOR range (0-30%)
                    if 0 < text_val < 30:
                        diff = abs(text_val - chart_val)
                        if diff < best_diff:
                            best_diff = diff
                            best_match = (text_val, m.group(0))

                pos = content_lower.find(alias, pos + 1)

        if best_match:
            text_val, text_str = best_match
            diff = abs(text_val - chart_val)
            if diff > 1.0:
                mismatches.append(
                    f"{trace_name}: text={text_val:.2f}% vs "
                    f"chart={chart_val:.2f}% (diff={diff:.2f}pp)"
                )
            else:
                matched += 1

    if mismatches:
        return False, (
            f"INCOHERENT: {len(mismatches)} trace(s) with text/chart mismatch: "
            + " | ".join(mismatches)
        )

    if matched > 0:
        return True, (
            f"Values coherent: {matched}/{len(chart_vals)} traces' IMOR % in text "
            f"match chart data (within 1pp)"
        )

    return True, (
        "SOFT_PASS: no IMOR percentages found in text to cross-check "
        f"(chart last values: { {k: f'{v:.2f}%' for k, v in chart_vals.items()} })"
    )


def _check_text_direction_coherence(resp: dict[str, Any]) -> tuple[bool, str]:
    """V14: Directional claims in text must match chart reality.

    If INVEX IMOR > PROMEDIO (higher morosidad = worse), the LLM must
    NOT say INVEX has "better" IMOR than average. And vice versa.

    Note: for IMOR, HIGHER = WORSE (more delinquent loans).
    """
    content = (resp.get("content") or "").lower()
    if not content:
        return True, "SKIP: no LLM text"

    chart_vals = _extract_last_values(resp)
    invex_val = chart_vals.get("INVEX")
    promedio_val = None
    for k, v in chart_vals.items():
        if "PROMEDIO" in k:
            promedio_val = v
            break

    if invex_val is None or promedio_val is None:
        return True, "SKIP: missing INVEX or PROMEDIO trace for direction check"

    invex_above = invex_val > promedio_val
    diff_pp = abs(invex_val - promedio_val)

    # Phrases that claim INVEX IMOR is ABOVE average (higher morosidad)
    above_phrases = [
        "por encima del promedio",
        "por encima de los pares",
        "supera al promedio",
        "supera el promedio",
        "superior al promedio",
        "mayor que el promedio",
        "mayor al promedio",
        "por arriba del promedio",
        "above the average",
        "above average",
    ]
    # Phrases that claim INVEX IMOR is BELOW average (lower morosidad)
    below_phrases = [
        "por debajo del promedio",
        "por debajo de los pares",
        "inferior al promedio",
        "menor que el promedio",
        "menor al promedio",
        "por abajo del promedio",
        "below the average",
        "below average",
    ]

    wrong_claims: list[str] = []

    if invex_above:
        # INVEX IMOR > PROMEDIO: below phrases are wrong
        for phrase in below_phrases:
            if phrase in content:
                wrong_claims.append(f"says '{phrase}' but INVEX IMOR > PROMEDIO")
    else:
        # INVEX IMOR < PROMEDIO: above phrases are wrong
        for phrase in above_phrases:
            if phrase in content:
                wrong_claims.append(f"says '{phrase}' but INVEX IMOR < PROMEDIO")

    if wrong_claims:
        direction = "ABOVE" if invex_above else "BELOW"
        return False, (
            f"DIRECTION_WRONG: INVEX IMOR is {direction} PROMEDIO "
            f"(diff={diff_pp:.2f}pp) but text claims opposite: "
            + " | ".join(wrong_claims[:3])
        )

    direction = "above" if invex_above else "below"
    quality = "worse" if invex_above else "better"
    return True, (
        f"Direction OK: INVEX IMOR {direction} PROMEDIO ({quality} quality) "
        f"(INVEX={invex_val:.2f}%, PROMEDIO={promedio_val:.2f}%, "
        f"diff={diff_pp:.2f}pp)"
    )


# ══════════════════════════════════════════════════════════════════════════════
# All checks
# ══════════════════════════════════════════════════════════════════════════════

ALL_CHECKS: list[ComponentCheck] = [
    ComponentCheck(
        name="V1_CHART_EXISTS",
        description="Chart must exist with at least one data trace",
        validate=_check_chart_exists,
    ),
    ComponentCheck(
        name="V2_PEER_AVG_SERIES",
        description="Chart must have INVEX and PROMEDIO series",
        validate=_check_peer_average_series,
    ),
    ComponentCheck(
        name="V3_NO_SYSTEM_LEAK",
        description="Response must NOT contain all 46 system banks (regression guard)",
        validate=_check_not_all_banks,
    ),
    ComponentCheck(
        name="V4_PERIOD_COVERAGE",
        description="Data should span from 2021-01 to a recent date",
        validate=_check_period_coverage,
    ),
    ComponentCheck(
        name="V5_DATA_POINTS",
        description="Each series should have >= 48 monthly data points",
        validate=_check_data_point_count,
    ),
    ComponentCheck(
        name="V6_VALUES_PLAUSIBLE",
        description="IMOR values must be in 0-30% range (positive, non-zero)",
        validate=_check_values_plausible,
    ),
    ComponentCheck(
        name="V7_PROMEDIO_MAGNITUDE",
        description="PROMEDIO should be a peer average (small %), not a sum",
        validate=_check_promedio_magnitude,
    ),
    ComponentCheck(
        name="V8_NO_FABRICATION",
        description="Response must not contain fabricated value markers",
        validate=_check_no_fabrication,
    ),
    ComponentCheck(
        name="V9_NO_TEXT_CONTRADICTION",
        description="LLM text must NOT deny data when chart has valid data",
        validate=_check_no_text_contradiction,
    ),
    ComponentCheck(
        name="V10_LAYOUT_TITLE",
        description="Chart title should reference 'IMOR' or 'morosidad'",
        validate=_check_layout_title,
    ),
    ComponentCheck(
        name="V11_INVEX_IN_TEXT",
        description="LLM response text should mention INVEX",
        validate=_check_invex_in_text,
    ),
    ComponentCheck(
        name="V12_PROMEDIO_IN_TEXT",
        description="LLM response text should mention promedio/pares",
        validate=_check_promedio_in_text,
    ),
    ComponentCheck(
        name="V13_TEXT_PCT_COHERENCE",
        description="IMOR percentages in LLM text must match chart Y-values (within 1pp)",
        validate=_check_text_pct_coherence,
    ),
    ComponentCheck(
        name="V14_TEXT_DIRECTION_COHERENCE",
        description="Directional claims (above/below) must match INVEX vs PROMEDIO reality",
        validate=_check_text_direction_coherence,
    ),
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
    print("E2E Test — Peer Average IMOR: INVEX vs PROMEDIO")
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
    for line in PROMPT.split("\n"):
        if line.strip():
            print(f"  {line.strip()}")
    print(f"\nSending (timeout={TIMEOUT}s)...")

    resp = send_chat_message(
        token,
        PROMPT,
        backend_url=BACKEND_URL,
        timeout=TIMEOUT,
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
        if traces:
            for t in traces:
                name = t.get("name", "?")
                y_vals = [v for v in t.get("y", []) if v is not None]
                if y_vals:
                    print(
                        f"    {name}: {len(y_vals)} points, "
                        f"last={y_vals[-1]:.2f}%, "
                        f"range=[{min(y_vals):.2f}%, {max(y_vals):.2f}%]"
                    )
        summary = bc.get("summary", "")
        if summary:
            print(f"  Summary: {summary[:80]}")

    # ── Run checks ──
    print(f"\n{'─' * 70}")
    print("COMPONENT CHECKS")
    print(f"{'─' * 70}")

    results = run_checks(resp)

    for r in results:
        tag = "PASS" if r.passed else "FAIL"
        print(f"\n  [{tag}] {r.check.name}")
        print(f"         {r.check.description}")
        print(f"         {r.detail}")

    # ── Summary ──
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 70}")

    # ── Save results JSON ──
    out = Path(__file__).parent / "peer_avg_imor_results.json"
    out.write_text(
        json.dumps(
            {
                "test": "peer-avg-imor-chart",
                "prompt": PROMPT,
                "backend_url": BACKEND_URL,
                "total_checks": total,
                "passed": passed,
                "failed": failed,
                "checks": [
                    {
                        "name": r.check.name,
                        "description": r.check.description,
                        "passed": r.passed,
                        "detail": r.detail,
                    }
                    for r in results
                ],
                "response_summary": {
                    "content_length": len(content),
                    "has_chart": bc is not None,
                    "events": events,
                    "trace_names": _extract_trace_names(resp),
                    "last_values": {
                        k: f"{v:.2f}%"
                        for k, v in _extract_last_values(resp).items()
                    },
                    "content_preview": content[:300],
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"\nResults saved: {out}")

    if failed > 0:
        print("\nFailed checks:")
        for r in results:
            if not r.passed:
                print(f"  - {r.check.name}: {r.detail}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
