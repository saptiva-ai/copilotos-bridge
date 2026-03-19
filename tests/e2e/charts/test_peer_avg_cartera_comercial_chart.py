#!/usr/bin/env python3
"""
E2E Test — Peer Average Cartera Comercial: INVEX vs PROMEDIO

Validates that prompt variants (colon, parentheses, period position)
all route to the peer-average handler and produce a comparison chart
with INVEX and PROMEDIO series for CARTERA COMERCIAL.

This test complements test_peer_average_chart.py (2 prompts, generic)
by adding a third variant where the time period appears at the END of
the prompt and validating that the chart title specifically references
"cartera comercial".

Prompts under test:
    A) "...cartera comercial de INVEX contra ... bancos: MONEX, ... De enero 2021..."
    B) "...cartera comercial de INVEX contra ... bancos (MONEX, ...) de enero 2021..."
    C) "...de enero 2021... cartera comercial de INVEX contra ... bancos: MONEX, ..."

Usage:
    python tests/e2e/charts/test_peer_avg_cartera_comercial_chart.py
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

# The 9 peer banks requested in all prompts
PEER_BANKS = [
    "MONEX", "BANCREA", "SABADELL", "MIFEL",
    "MULTIVA", "AFIRME", "BANSI", "VE POR MAS", "BANCO BASE",
]

# ── Prompt variants ──────────────────────────────────────────────────────────
# Variant A: user's natural prompt — colon after "bancos", period at end.
PROMPT_A_COLON_END = (
    "Crea una gráfica donde se compare la cartera comercial de INVEX "
    "contra la cartera promedio de los bancos: MONEX, BANCREA, SABADELL, "
    "BANCA MIFEL, MULTIVA, AFIRME, BANSI, VE POR MÁS Y BANCO BASE. "
    "De enero 2021 hasta el dato más reciente que tengas"
)
# Variant B: parenthesized bank list, period at end.
PROMPT_B_PARENS_END = (
    "Crea una gráfica donde se compare la cartera comercial de INVEX "
    "contra la cartera promedio de los bancos (MONEX, BANCREA, SABADELL, "
    "BANCA MIFEL, MULTIVA, AFIRME, BANSI, VE POR MÁS Y BANCO BASE) "
    "de enero 2021 hasta el dato más reciente que tengas"
)
# Variant C: colon after "bancos", period at beginning (original bug case).
PROMPT_C_COLON_START = (
    "Crea una gráfica de enero 2021 hasta el dato más reciente que tengas "
    "donde se compare la cartera comercial de INVEX contra la cartera "
    "promedio de los bancos: MONEX, BANCREA, SABADELL, BANCA MIFEL, "
    "MULTIVA, AFIRME, BANSI, VE POR MÁS Y BANCO BASE"
)

ALL_PROMPTS = [
    ("A (colon, period end)", PROMPT_A_COLON_END),
    ("B (parens, period end)", PROMPT_B_PARENS_END),
    ("C (colon, period start)", PROMPT_C_COLON_START),
]

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
    """V6: Y-values should be in a plausible range for cartera comercial."""
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
            return False, f"NEGATIVE: {name} min={min_val}"
        if max_val == 0:
            return False, f"ALL_ZERO: {name} has no non-zero values"

    return True, "Values plausible across all series"


def _check_promedio_smaller_than_system(resp: dict[str, Any]) -> tuple[bool, str]:
    """V7: PROMEDIO should be a peer average, not a system sum."""
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

    if max_val > 1e13:
        return False, (
            f"IMPLAUSIBLE_AVG: PROMEDIO max={max_val:.2e} — "
            f"likely summed instead of averaged"
        )

    return True, f"Promedio magnitude OK: max={max_val:.2e}"


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
    """V10: Chart title should reference 'cartera comercial'."""
    layout = _get_layout(resp)
    if not layout:
        return False, "NO_LAYOUT"

    title = layout.get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")

    title_lower = title.lower()
    has_comercial = "comercial" in title_lower

    if has_comercial:
        return True, f"Title OK: '{title}'"

    has_cartera = "cartera" in title_lower
    if has_cartera:
        return False, (
            f"PARTIAL_TITLE: '{title}' — has 'cartera' but missing 'comercial'"
        )

    return False, f"WRONG_TITLE: '{title}' — expected 'cartera comercial'"


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


def _parse_monetary_values(text: str) -> list[tuple[float, str]]:
    """Extract monetary values from LLM text, normalized to raw pesos.

    Handles patterns like:
      - "$14,230 millones" → 14_230_000_000
      - "15,665 MDP" → 15_665_000_000
      - "$52,865.9 millones de pesos" → 52_865_900_000_000 (wrong scale)
      - "16,402,586,992" → 16_402_586_992 (raw)

    Returns list of (value_in_pesos, original_match_text).
    """
    results: list[tuple[float, str]] = []

    # Pattern 1: "$NN,NNN millones" or "NN,NNN MDP" or "NN,NNN millones de pesos"
    mdp_pat = re.compile(
        r"\$?([\d,]+(?:\.\d+)?)\s*(?:millones|mdp|millones\s+de\s+pesos)",
        re.IGNORECASE,
    )
    for m in mdp_pat.finditer(text):
        raw = m.group(1).replace(",", "")
        try:
            val = float(raw) * 1e6  # millones → pesos
            results.append((val, m.group(0).strip()))
        except ValueError:
            pass

    # Pattern 2: raw large numbers like "16,402,586,992" (>= 1 billion)
    raw_pat = re.compile(r"\b([\d]{1,3}(?:,\d{3}){3,})\b")
    for m in raw_pat.finditer(text):
        raw = m.group(1).replace(",", "")
        try:
            val = float(raw)
            if val >= 1e9:
                results.append((val, m.group(0)))
        except ValueError:
            pass

    return results


def _check_text_values_coherence(resp: dict[str, Any]) -> tuple[bool, str]:
    """V13: Monetary values in LLM text must be close to chart Y-values.

    Extracts the most recent Y-values from each trace (INVEX, PROMEDIO)
    and compares against any monetary values the LLM mentions in the text.
    Tolerance: 20% relative difference.
    """
    content = resp.get("content") or ""
    if not content:
        return True, "SKIP: no LLM text"

    chart_vals = _extract_last_values(resp)
    if not chart_vals:
        return True, "SKIP: no chart traces to compare"

    text_moneys = _parse_monetary_values(content)
    if not text_moneys:
        return True, (
            "SOFT_PASS: no monetary values found in text to cross-check "
            f"(chart last values: { {k: f'{v:.0f}' for k, v in chart_vals.items()} })"
        )

    # For each chart trace, find the closest text value and check tolerance
    mismatches: list[str] = []
    matched = 0

    for trace_name, chart_val in chart_vals.items():
        # Find text values mentioned near this trace name (within 200 chars)
        name_lower = trace_name.lower()
        search_aliases = [name_lower]
        if "promedio" in name_lower:
            search_aliases.extend(["promedio", "pares", "average", "peer"])

        best_match: tuple[float, str] | None = None
        best_distance = float("inf")

        for text_val, text_str in text_moneys:
            # Check if this value is contextually near the trace name
            for alias in search_aliases:
                # Find positions of alias in text
                pos = content.lower().find(alias)
                while pos != -1:
                    text_pos = content.lower().find(text_str.lower(), max(0, pos - 200))
                    if text_pos != -1 and abs(text_pos - pos) < 300:
                        rel_diff = abs(text_val - chart_val) / chart_val if chart_val else 1
                        if rel_diff < best_distance:
                            best_distance = rel_diff
                            best_match = (text_val, text_str)
                    pos = content.lower().find(alias, pos + 1)

        if best_match:
            text_val, text_str = best_match
            rel_diff = abs(text_val - chart_val) / chart_val if chart_val else 1
            if rel_diff > 0.20:
                mismatches.append(
                    f"{trace_name}: text='{text_str}' ({text_val:,.0f}) vs "
                    f"chart={chart_val:,.0f} (diff={rel_diff:.0%})"
                )
            else:
                matched += 1

    if mismatches:
        return False, (
            f"INCOHERENT_VALUES: {len(mismatches)} trace(s) with text/chart mismatch: "
            + " | ".join(mismatches)
        )

    if matched > 0:
        return True, (
            f"Values coherent: {matched}/{len(chart_vals)} traces' values in text "
            f"match chart data (within 20%)"
        )

    return True, (
        "SOFT_PASS: could not associate text values with specific traces "
        f"(chart: { {k: f'{v:,.0f}' for k, v in chart_vals.items()} })"
    )


def _check_text_direction_coherence(resp: dict[str, Any]) -> tuple[bool, str]:
    """V14: Directional claims in text must match chart reality.

    If INVEX < PROMEDIO in the chart, the LLM must NOT say INVEX
    is "above" or "greater than" the average. And vice versa.
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
    ratio = invex_val / promedio_val if promedio_val else 0

    # Phrases that claim INVEX is ABOVE average
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
        "ventaja relativa",
    ]
    # NOTE: "brecha creciente" excluded — directionally neutral
    # (gap can grow regardless of which series is higher)
    # Phrases that claim INVEX is BELOW average
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
        # INVEX > PROMEDIO: below phrases are wrong
        for phrase in below_phrases:
            if phrase in content:
                wrong_claims.append(f"says '{phrase}' but INVEX > PROMEDIO")
    else:
        # INVEX < PROMEDIO: above phrases are wrong
        for phrase in above_phrases:
            if phrase in content:
                wrong_claims.append(f"says '{phrase}' but INVEX < PROMEDIO")

    if wrong_claims:
        direction = "ABOVE" if invex_above else "BELOW"
        return False, (
            f"DIRECTION_WRONG: INVEX is {direction} PROMEDIO "
            f"(ratio={ratio:.2f}x) but text claims opposite: "
            + " | ".join(wrong_claims[:3])
        )

    direction = "above" if invex_above else "below"
    return True, (
        f"Direction OK: INVEX {direction} PROMEDIO "
        f"(ratio={ratio:.2f}x, INVEX={invex_val:,.0f}, "
        f"PROMEDIO={promedio_val:,.0f})"
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
        description="Y-values must be positive and non-zero",
        validate=_check_values_plausible,
    ),
    ComponentCheck(
        name="V7_PROMEDIO_MAGNITUDE",
        description="PROMEDIO should be a peer average, not a system sum",
        validate=_check_promedio_smaller_than_system,
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
        description="Chart title should reference 'cartera comercial'",
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
        name="V13_TEXT_VALUES_COHERENCE",
        description="Monetary values in LLM text must match chart Y-values (within 20%)",
        validate=_check_text_values_coherence,
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


def run_single_prompt(
    token: str, prompt: str, label: str
) -> tuple[list[CheckResult], dict[str, Any]]:
    """Send a prompt and run all checks; return (results, raw_response)."""
    print(f"\n{'─' * 70}")
    print(f"PROMPT {label} ({len(prompt)} chars):")
    print(f"  \"{prompt[:100]}...\"")
    print(f"Sending (timeout={TIMEOUT}s)...")

    resp = send_chat_message(
        token,
        prompt,
        backend_url=BACKEND_URL,
        timeout=TIMEOUT,
    )

    if resp.get("error"):
        print(f"  FATAL: Request failed: {resp['error']}")
        return [], resp

    content = resp.get("content", "")
    bc = resp.get("bank_chart")
    events = resp.get("events", [])
    print(f"  Response: {len(content)} chars, chart={'present' if bc else 'MISSING'}")
    print(f"  Events: {events}")

    if bc:
        traces = bc.get("plotly_config", {}).get("data", [])
        trace_names = [t.get("name", "?") for t in traces]
        print(f"  Traces ({len(traces)}): {trace_names}")

    results = run_checks(resp)

    for r in results:
        tag = "PASS" if r.passed else "FAIL"
        print(f"  [{tag}] {r.check.name}: {r.detail}")

    return results, resp


def main() -> int:
    n_prompts = len(ALL_PROMPTS)
    print("=" * 70)
    print("E2E Test — Peer Average Cartera Comercial: INVEX vs PROMEDIO")
    print(f"Backend: {BACKEND_URL}")
    print(f"Checks: {len(ALL_CHECKS)} component validators x {n_prompts} prompts")
    print("=" * 70)

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FATAL: Auth failed")
        return 2

    print(f"Authenticated against {BACKEND_URL}")

    # ── Run all prompts ──
    prompt_results: list[tuple[str, list[CheckResult], dict[str, Any]]] = []
    for label, prompt in ALL_PROMPTS:
        results, resp = run_single_prompt(token, prompt, label)
        prompt_results.append((label, results, resp))

    # ── Cross-prompt consistency check ──
    print(f"\n{'─' * 70}")
    print("CROSS-PROMPT CONSISTENCY")
    print(f"{'─' * 70}")

    all_trace_sets: list[tuple[str, set[str]]] = []
    for label, _, resp in prompt_results:
        names = set(_extract_trace_names({"bank_chart": resp.get("bank_chart")}))
        all_trace_sets.append((label, names))

    consistency_ok = True
    reference_label, reference_names = all_trace_sets[0]
    for label, names in all_trace_sets[1:]:
        if not reference_names or not names:
            print(f"  [SKIP] Cannot compare {reference_label} vs {label} — missing traces")
            continue
        if reference_names == names:
            print(f"  [PASS] {reference_label} == {label}: {sorted(reference_names)}")
        else:
            diff = reference_names.symmetric_difference(names)
            print(f"  [FAIL] {reference_label} != {label}: diff={sorted(diff)}")
            consistency_ok = False

    # ── Summary ──
    all_results: list[CheckResult] = []
    for _, results, _ in prompt_results:
        all_results.extend(results)

    passed = sum(1 for r in all_results if r.passed)
    failed = sum(1 for r in all_results if not r.passed)
    total = len(all_results)

    if not consistency_ok:
        failed += 1
        total += 1

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    for label, results, _ in prompt_results:
        p = sum(1 for r in results if r.passed)
        print(f"  Prompt {label}: {p}/{len(results)}")
    print(f"  Consistency: {'PASS' if consistency_ok else 'FAIL'}")
    print(f"{'=' * 70}")

    # ── Save results JSON ──
    out = Path(__file__).parent / "peer_avg_cartera_comercial_results.json"
    prompt_data = {}
    for i, (label, results, resp) in enumerate(prompt_results):
        key = f"prompt_{chr(ord('a') + i)}"
        names = set(_extract_trace_names({"bank_chart": resp.get("bank_chart")}))
        prompt_data[key] = {
            "label": label,
            "prompt": ALL_PROMPTS[i][1],
            "checks": [
                {
                    "name": r.check.name,
                    "passed": r.passed,
                    "detail": r.detail,
                }
                for r in results
            ],
            "response_summary": {
                "content_length": len(resp.get("content", "")),
                "has_chart": resp.get("bank_chart") is not None,
                "trace_names": list(names),
            },
        }

    out.write_text(
        json.dumps(
            {
                "test": "peer-avg-cartera-comercial-chart",
                "backend_url": BACKEND_URL,
                "total_checks": total,
                "passed": passed,
                "failed": failed,
                "consistency": consistency_ok,
                **prompt_data,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"\nResults saved: {out}")

    if failed > 0:
        print("\nFailed checks:")
        for r in all_results:
            if not r.passed:
                print(f"  - {r.check.name}: {r.detail}")
        if not consistency_ok:
            print("  - CROSS_PROMPT_CONSISTENCY: series mismatch between prompts")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
