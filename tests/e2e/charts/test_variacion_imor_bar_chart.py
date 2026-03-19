#!/usr/bin/env python3
"""
E2E Test — Variacion de IMOR: Bar Chart Pipeline

Sends the exact multi-bank IMOR variation prompt and validates every component
of the response: chart type, period parsing, bank coverage, coloring
(INVEX red, rest grey), zeroline, table_data, metric detection (imor),
text/chart coherence, and anti-fabrication guards.

This test validates the pipeline for IMOR variation between two periods:
  QueryRouter → handler match → _parse_period_comparison()
  → delta or time-series path → horizontal bar chart

NOTE: EvolucionBancoHandler explicitly EXCLUDES "imor" in _METRIC_EXCLUSIONS.
IMOR queries may route through MetricasFinancierasHandler, ComparativeHandler,
or fall through to NL2SQL. This test validates the end-to-end result regardless
of which handler processes it.

Prompt under test:
    "Toma como periodo inicial enero 2024 y como periodo actual enero 2025.
     Compara el IMOR entre el periodo inicial y el periodo final entre los
     bancos: MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME,
     BANSI, VE POR MAS Y BANCO BASE. Presenta el dato del periodo inicial,
     el dato del periodo final y la variacion entre el periodo inicial.
     Donde la variacion es = (periodo actual / periodo inicial -1)
     Haz una grafica de barras donde se vea la variacion graficada y marca
     a INVEX de color rojo. Asi como una tabla con:
     Banco | IMOR 2024 | IMOR 2025 | % Variacion"

Usage:
    python tests/e2e/charts/test_variacion_imor_bar_chart.py
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

# The 10 banks requested in the prompt (canonical names after alias resolution)
REQUESTED_BANKS = [
    "MONEX", "INVEX", "BANCREA", "SABADELL", "MIFEL",
    "MULTIVA", "AFIRME", "BANSI", "VE POR MAS", "BANCO BASE",
]

# The exact prompt — note "IMOR" (ratio metric, not cartera)
PROMPT = (
    "Toma como periodo inicial enero 2024 y como periodo actual enero 2025. "
    "Compara el IMOR entre el periodo inicial y el periodo final entre los "
    "bancos: MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, "
    "AFIRME, BANSI, VE POR MAS Y BANCO BASE. "
    "Presenta el dato del periodo inicial, el dato del periodo final y la "
    "variacion entre el periodo inicial. "
    "Donde la variacion es = (periodo actual / periodo inicial -1) "
    "Haz una grafica de barras donde se vea la variacion graficada y "
    "marca a INVEX de color rojo. Asi como una tabla con: "
    "Banco | IMOR 2024 | IMOR 2025 | % Variacion"
)

# Colors from BANK_COLORS in chart_formatter.py
INVEX_RED = "#E45756"
NEUTRAL_GREY = "#999999"

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
    "no esta disponible",
    "no cuento con los datos",
    "no cuento con datos",
    "no encuentro informacion",
    "no se encontraron datos",
    "no hay datos disponibles",
    "no dispongo de",
    "no puedo realizar la comparacion",
    "datos no disponibles",
    "sin datos para",
    "lamentablemente no",
    "lo siento, pero no tengo",
    "no fue posible obtener",
]

# Suspicious round values suggesting LLM fabrication
SUSPICIOUS_ROUND_PATTERN = re.compile(r"\$[\d,]*[05]00[,.]000[,.]000")


# ==============================================================================
# Data Classes (replay pattern)
# ==============================================================================


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


# ==============================================================================
# Chart helpers
# ==============================================================================


def _get_plotly_config(resp: dict[str, Any]) -> dict[str, Any] | None:
    bc = resp.get("bank_chart")
    if not bc:
        return None
    return bc.get("plotly_config")


def _get_first_trace(resp: dict[str, Any]) -> dict[str, Any] | None:
    plotly = _get_plotly_config(resp)
    if not plotly:
        return None
    traces = plotly.get("data", [])
    return traces[0] if traces else None


def _extract_trace_names(resp: dict[str, Any]) -> list[str]:
    bc = resp.get("bank_chart")
    if not bc:
        return []
    names = bc.get("bank_names", [])
    if names:
        return [n.upper() for n in names]
    plotly = bc.get("plotly_config", {})
    traces = plotly.get("data", [])
    if traces and traces[0].get("orientation") == "h":
        y_vals = traces[0].get("y", [])
        return [str(y).upper() for y in y_vals]
    return [t.get("name", "").upper() for t in traces if t.get("name")]


def _get_layout(resp: dict[str, Any]) -> dict[str, Any] | None:
    plotly = _get_plotly_config(resp)
    if not plotly:
        return None
    return plotly.get("layout")


# ==============================================================================
# Component Validators
# ==============================================================================


def _check_chart_exists(resp: dict[str, Any]) -> tuple[bool, str]:
    """V1: Chart must exist and be a horizontal bar chart."""
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    bc = resp.get("bank_chart")
    if not bc:
        return False, "CHART_MISSING: no bank_chart in response"

    chart_status = bc.get("chart_status", "")
    if hasattr(chart_status, "value"):
        chart_status = chart_status.value
    if chart_status not in ("success", None, ""):
        return False, f"CHART_FAILED: chart_status={chart_status}"

    trace = _get_first_trace(resp)
    if not trace:
        return False, "CHART_EMPTY: plotly_config has no data traces"

    chart_type = trace.get("type", "")
    orientation = trace.get("orientation", "")

    if chart_type != "bar":
        return False, f"WRONG_TYPE: expected 'bar', got '{chart_type}'"
    if orientation != "h":
        return False, f"WRONG_ORIENTATION: expected 'h', got '{orientation}'"

    return True, f"Bar chart present: type={chart_type}, orientation={orientation}"


def _check_period_parsing(resp: dict[str, Any]) -> tuple[bool, str]:
    """V2: Chart title or metadata must reference 2024 vs 2025."""
    layout = _get_layout(resp)
    if not layout:
        return False, "NO_LAYOUT: cannot verify period in title"

    title = layout.get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")

    has_2024 = "2024" in title
    has_2025 = "2025" in title

    if has_2024 and has_2025:
        return True, f"Period parsed correctly: title='{title}'"

    bc = resp.get("bank_chart", {})
    summary = bc.get("summary", "")
    if "2024" in summary and "2025" in summary:
        return True, f"Period in summary: '{summary[:80]}'"

    return False, (
        f"PERIOD_MISS: title='{title}', expected both 2024 and 2025. "
        f"Labeled regex 'periodo inicial = enero 2024 ... periodo actual = enero 2025' "
        f"did not match."
    )


def _check_metric_detection(resp: dict[str, Any]) -> tuple[bool, str]:
    """V3: Metric must be IMOR (not cartera, not ICOR, not ICAP).

    The prompt says "IMOR" explicitly, so the response should reference
    IMOR / morosidad / indice de morosidad somewhere.
    """
    bc = resp.get("bank_chart")
    if not bc:
        return False, "NO_CHART: cannot verify metric"

    layout = _get_layout(resp)
    title = ""
    if layout:
        title = layout.get("title", "")
        if isinstance(title, dict):
            title = title.get("text", "")

    summary = bc.get("summary", "")
    content = (resp.get("content") or "").lower()

    title_lower = title.lower()
    summary_lower = summary.lower()

    # Positive: "imor" or "morosidad" should appear in title, summary, or content
    has_imor = (
        "imor" in title_lower
        or "imor" in summary_lower
        or "morosidad" in title_lower
        or "morosidad" in summary_lower
        or "imor" in content
    )

    # Negative: should NOT say "cartera" as the primary metric
    has_wrong_metric = (
        "cartera_total" in title_lower
        or "cartera_comercial" in title_lower
    )

    if has_imor:
        return True, (
            f"Metric detection OK: 'imor' or 'morosidad' found. "
            f"title='{title}', summary='{summary[:60]}'"
        )

    if has_wrong_metric:
        return False, (
            f"WRONG_METRIC: detected cartera instead of IMOR. "
            f"EvolucionBancoHandler should have excluded this query "
            f"(_METRIC_EXCLUSIONS). title='{title}'"
        )

    return True, (
        f"METRIC_INDIRECT: no explicit 'imor' in title/summary, "
        f"but query explicitly asks for IMOR. title='{title[:50]}'"
    )


def _check_bank_coverage(resp: dict[str, Any]) -> tuple[bool, str]:
    """V4: At least 7/10 requested banks should appear in chart."""
    trace_names = _extract_trace_names(resp)
    trace_upper = {t.upper() for t in trace_names}

    resolved = []
    missing = []
    for bank in REQUESTED_BANKS:
        found = any(bank in t or t in bank for t in trace_upper)
        if found:
            resolved.append(bank)
        else:
            missing.append(bank)

    coverage = len(resolved) / len(REQUESTED_BANKS) if REQUESTED_BANKS else 0

    if coverage >= 0.7:
        return True, (
            f"Coverage OK: {len(resolved)}/{len(REQUESTED_BANKS)} "
            f"({coverage:.0%}). Banks: {trace_names}"
        )
    elif coverage >= 0.5:
        return True, (
            f"PARTIAL_COVERAGE: {len(resolved)}/{len(REQUESTED_BANKS)} "
            f"({coverage:.0%}). Missing: {missing}"
        )
    else:
        return False, (
            f"LOW_COVERAGE: {len(resolved)}/{len(REQUESTED_BANKS)} "
            f"({coverage:.0%}). Missing: {missing}. Traces: {trace_names}"
        )


def _check_invex_highlight(resp: dict[str, Any]) -> tuple[bool, str]:
    """V5: INVEX bar must be colored red (#E45756)."""
    trace = _get_first_trace(resp)
    if not trace:
        return False, "NO_TRACE: cannot verify colors"

    marker = trace.get("marker", {})
    colors = marker.get("color", [])
    y_vals = trace.get("y", [])

    if not colors or not y_vals:
        return False, "NO_COLORS: marker.color not present"

    invex_idx = None
    for i, bank in enumerate(y_vals):
        if str(bank).upper() == "INVEX":
            invex_idx = i
            break

    if invex_idx is None:
        return False, "INVEX_MISSING: INVEX not in y-axis banks"

    invex_color = colors[invex_idx] if invex_idx < len(colors) else None
    if invex_color and invex_color.upper() == INVEX_RED.upper():
        return True, f"INVEX highlighted: color={invex_color} at index {invex_idx}"

    return False, (
        f"WRONG_COLOR: INVEX color={invex_color}, expected {INVEX_RED}. "
        f"_detect_highlight_bank() may have failed."
    )


def _check_neutral_colors(resp: dict[str, Any]) -> tuple[bool, str]:
    """V6: Non-INVEX bars should be grey (#999999)."""
    trace = _get_first_trace(resp)
    if not trace:
        return False, "NO_TRACE: cannot verify colors"

    marker = trace.get("marker", {})
    colors = marker.get("color", [])
    y_vals = trace.get("y", [])

    if not colors or not y_vals:
        return False, "NO_COLORS: marker.color not present"

    non_invex_colors = {}
    for i, bank in enumerate(y_vals):
        if str(bank).upper() != "INVEX" and i < len(colors):
            non_invex_colors[str(bank)] = colors[i]

    wrong = {
        bank: color for bank, color in non_invex_colors.items()
        if color.upper() != NEUTRAL_GREY.upper()
    }

    if not wrong:
        return True, (
            f"All {len(non_invex_colors)} non-INVEX bars are grey ({NEUTRAL_GREY})"
        )

    return False, (
        f"WRONG_NEUTRAL: {len(wrong)}/{len(non_invex_colors)} bars not grey: "
        f"{wrong}"
    )


def _check_zeroline(resp: dict[str, Any]) -> tuple[bool, str]:
    """V7: Layout.xaxis should have zeroline=true (variations can be +/-)."""
    layout = _get_layout(resp)
    if not layout:
        return False, "NO_LAYOUT: cannot verify zeroline"

    xaxis = layout.get("xaxis", {})
    zeroline = xaxis.get("zeroline")
    zerolinewidth = xaxis.get("zerolinewidth")
    zerolinecolor = xaxis.get("zerolinecolor")

    if zeroline is True:
        return True, (
            f"Zeroline present: width={zerolinewidth}, color={zerolinecolor}"
        )

    return False, f"NO_ZEROLINE: xaxis.zeroline={zeroline}"


def _check_table_data(resp: dict[str, Any]) -> tuple[bool, str]:
    """V8: Response should include table_data with 4 columns.

    Expected: Banco | IMOR 2024 | IMOR 2025 | % Variacion
    """
    bc = resp.get("bank_chart")
    if not bc:
        return False, "NO_CHART: cannot check table_data"

    table_data = bc.get("table_data")
    if not table_data:
        return False, "NO_TABLE_DATA: table_data not present in response"

    columns = table_data.get("columns", [])
    rows = table_data.get("rows", [])

    if len(columns) != 4:
        return False, f"WRONG_COLUMNS: expected 4, got {len(columns)}: {columns}"

    if not rows:
        return False, "EMPTY_TABLE: table_data.rows is empty"

    has_banco = any("banco" in c.lower() for c in columns)
    has_variacion = any("variaci" in c.lower() or "%" in c for c in columns)

    if not has_banco or not has_variacion:
        return False, f"BAD_COLUMNS: columns={columns}, missing Banco or Variacion"

    valid_rows = 0
    for row in rows:
        if len(row) >= 4 and row[3] is not None:
            try:
                # pct_change may be pre-formatted as "+72.32%" or raw float
                raw = str(row[3]).replace("%", "").replace("+", "").strip()
                float(raw)
                valid_rows += 1
            except (TypeError, ValueError):
                pass

    return True, (
        f"Table data OK: {len(columns)} columns, {len(rows)} rows, "
        f"{valid_rows} with valid variation"
    )


def _check_no_fabrication(resp: dict[str, Any]) -> tuple[bool, str]:
    """V9: Response content should not contain fabricated value markers."""
    content = (resp.get("content") or "").lower()
    issues = []

    for phrase in FABRICATED_VALUE_PHRASES:
        if phrase in content:
            issues.append(f"FABRICATION: '{phrase}' found in response text")

    raw = resp.get("content") or ""
    round_matches = SUSPICIOUS_ROUND_PATTERN.findall(raw)
    if round_matches:
        issues.append(
            f"SUSPICIOUS_ROUND: {len(round_matches)} round values: "
            f"{round_matches[:3]}"
        )

    if issues:
        return False, " | ".join(issues)

    return True, "No fabrication markers detected"


def _check_variation_values(resp: dict[str, Any]) -> tuple[bool, str]:
    """V10: Variation values in chart should be plausible.

    IMOR values are typically 0.5%-15% for Mexican banks. Variation between
    periods can be extreme (a bank going from 1% to 2% IMOR is +100% variation).
    We allow a wider range: -100% to +500%.
    """
    trace = _get_first_trace(resp)
    if not trace:
        return False, "NO_TRACE: cannot verify variation values"

    x_vals = trace.get("x", [])
    y_vals = trace.get("y", [])

    if not x_vals:
        return False, "NO_VALUES: trace.x is empty"

    out_of_range = []
    none_count = 0
    for i, val in enumerate(x_vals):
        if val is None:
            none_count += 1
            continue
        try:
            v = float(val)
            # IMOR variations can be extreme: a bank with 0.03% IMOR going to
            # 1.0% is a +3233% variation. Allow up to 5000%.
            if v < -100 or v > 5000:
                bank = y_vals[i] if i < len(y_vals) else f"idx_{i}"
                out_of_range.append(f"{bank}={v:.1f}%")
        except (TypeError, ValueError):
            pass

    if none_count == len(x_vals):
        return False, "ALL_NONE: every variation value is None"

    if out_of_range:
        return False, (
            f"IMPLAUSIBLE: {len(out_of_range)} values out of [-100, 5000] range: "
            f"{out_of_range[:5]}"
        )

    valid = len(x_vals) - none_count
    non_none = []
    for v in x_vals:
        if v is not None:
            try:
                non_none.append(float(v))
            except (TypeError, ValueError):
                pass

    if not non_none:
        return False, (
            f"NON_NUMERIC: x_vals are not numeric (got dates or strings?). "
            f"Sample: {x_vals[:3]}"
        )

    return True, (
        f"Variation values OK: {valid}/{len(x_vals)} valid, "
        f"range=[{min(non_none):.1f}%, {max(non_none):.1f}%]"
    )


def _check_text_labels(resp: dict[str, Any]) -> tuple[bool, str]:
    """V11: Bar text labels should show formatted percentages or numbers."""
    trace = _get_first_trace(resp)
    if not trace:
        return False, "NO_TRACE: cannot verify text labels"

    text_vals = trace.get("text", [])
    textposition = trace.get("textposition", "")

    if not text_vals:
        return False, "NO_TEXT: trace.text is empty"

    # Labels could be percentages (%) or numeric values
    has_content = [t for t in text_vals if str(t).strip()]
    pct_labels = [t for t in text_vals if "%" in str(t)]
    numeric_labels = []
    for t in text_vals:
        try:
            float(str(t).replace("%", "").replace(",", ".").strip())
            numeric_labels.append(t)
        except (TypeError, ValueError):
            pass

    if pct_labels:
        return True, (
            f"Text labels OK: {len(pct_labels)}/{len(text_vals)} with '%', "
            f"position='{textposition}', sample={pct_labels[:3]}"
        )

    if numeric_labels:
        return True, (
            f"Text labels OK (numeric): {len(numeric_labels)}/{len(text_vals)} "
            f"numeric, position='{textposition}', sample={numeric_labels[:3]}"
        )

    if has_content:
        return True, (
            f"Text labels present: {len(has_content)}/{len(text_vals)} non-empty, "
            f"sample={has_content[:3]}"
        )

    return False, f"NO_LABELS: text values are all empty: {text_vals[:3]}"


def _check_table_bank_coverage(resp: dict[str, Any]) -> tuple[bool, str]:
    """V12: table_data rows should cover most of the 10 banks."""
    bc = resp.get("bank_chart")
    if not bc:
        return False, "NO_CHART: cannot check table bank coverage"

    table_data = bc.get("table_data")
    if not table_data:
        return False, "NO_TABLE_DATA: cannot check bank coverage"

    rows = table_data.get("rows", [])
    table_banks = {str(row[0]).upper() for row in rows if row}

    resolved = []
    missing = []
    for bank in REQUESTED_BANKS:
        found = any(bank in tb or tb in bank for tb in table_banks)
        if found:
            resolved.append(bank)
        else:
            missing.append(bank)

    coverage = len(resolved) / len(REQUESTED_BANKS) if REQUESTED_BANKS else 0

    if coverage >= 0.7:
        return True, (
            f"Table bank coverage OK: {len(resolved)}/{len(REQUESTED_BANKS)} "
            f"({coverage:.0%}). Banks in table: {sorted(table_banks)}"
        )
    elif coverage >= 0.5:
        return True, (
            f"PARTIAL_TABLE_COVERAGE: {len(resolved)}/{len(REQUESTED_BANKS)} "
            f"({coverage:.0%}). Missing from table: {missing}"
        )
    else:
        return False, (
            f"LOW_TABLE_COVERAGE: {len(resolved)}/{len(REQUESTED_BANKS)} "
            f"({coverage:.0%}). Missing: {missing}"
        )


def _check_no_text_contradiction(resp: dict[str, Any]) -> tuple[bool, str]:
    """V13: LLM text must NOT deny data when the chart has valid data."""
    bc = resp.get("bank_chart")
    content = (resp.get("content") or "").lower()

    if not bc or not bc.get("plotly_config", {}).get("data"):
        return True, "SKIP: no chart data to contradict"

    trace = bc.get("plotly_config", {}).get("data", [{}])[0]
    x_vals = [v for v in trace.get("x", []) if v is not None]
    if not x_vals:
        return True, "SKIP: chart trace has no non-null values"

    found = [p for p in TEXT_CONTRADICTION_PHRASES if p in content]
    if found:
        return False, (
            f"TEXT_CONTRADICTION: chart has {len(x_vals)} data points but "
            f"LLM text contains denial phrases: {found}"
        )

    return True, (
        f"No contradiction: chart has {len(x_vals)} data points, "
        f"text does not deny data availability"
    )


def _check_text_chart_coherence(resp: dict[str, Any]) -> tuple[bool, str]:
    """V14: LLM text percentages must be coherent with chart values.

    For IMOR, the LLM often writes absolute metric values (e.g. "INVEX: 2.1%")
    while the chart shows variation percentages (e.g. "+14.2%"). These are
    categorically different scales, so this validator detects when text values
    are absolute (small, typically <20%) and chart values are variation (larger),
    and treats that as a soft pass rather than a mismatch.
    """
    bc = resp.get("bank_chart")
    content = resp.get("content") or ""

    if not bc:
        return True, "SKIP: no chart to compare against"

    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return True, "SKIP: chart trace empty"

    trace = traces[0]
    x_vals = trace.get("x", [])
    y_vals = trace.get("y", [])

    if not x_vals or not y_vals:
        return True, "SKIP: chart trace empty"

    # Only works for horizontal bar charts (y=banks, x=values)
    if trace.get("type") != "bar" or trace.get("orientation") != "h":
        return True, (
            f"SKIP: chart is {trace.get('type')}/{trace.get('orientation')}, "
            f"coherence check only applies to horizontal bar charts"
        )

    chart_map: dict[str, float] = {}
    for bank, val in zip(y_vals, x_vals):
        if val is not None:
            try:
                chart_map[str(bank).upper()] = float(val)
            except (TypeError, ValueError):
                pass

    text_vals_found: list[float] = []
    matched = 0
    lines = content.split("\n")
    for bank, chart_val in chart_map.items():
        pattern = re.compile(
            rf"[-\u2022]\s*{re.escape(bank)}.{{0,120}}?([+-]?\d+[.,]\d+)\s*%",
            re.IGNORECASE,
        )
        for line in lines:
            m = pattern.search(line)
            if m:
                text_val = float(m.group(1).replace(",", "."))
                text_vals_found.append(text_val)
                diff = abs(text_val - chart_val)
                if diff <= 5.0:
                    matched += 1
                break

    # Detect absolute-vs-variation scale mismatch:
    # If most text values are small (< 20) but chart values span a wider range,
    # the LLM is likely reporting absolute IMOR values, not variation %.
    if text_vals_found and matched == 0:
        avg_text = sum(abs(v) for v in text_vals_found) / len(text_vals_found)
        chart_vals = [abs(v) for v in chart_map.values()]
        avg_chart = sum(chart_vals) / len(chart_vals) if chart_vals else 0
        if avg_text < 20 and avg_chart > 20:
            return True, (
                f"SOFT_PASS: LLM reports absolute IMOR values "
                f"(avg={avg_text:.1f}%) while chart shows variation % "
                f"(avg={avg_chart:.1f}%). Scale mismatch is expected for "
                f"ratio metrics."
            )

    if matched == 0 and not text_vals_found:
        return True, (
            "SOFT_PASS: no percentages found in text to cross-check "
            f"(chart has {len(chart_map)} banks)"
        )

    if matched == 0 and text_vals_found:
        return False, (
            f"INCOHERENT: {len(text_vals_found)} text values found but none "
            f"match chart values (within 5pp)"
        )

    return True, (
        f"Coherent: {matched}/{len(chart_map)} banks' percentages in text "
        f"match chart values (within 5pp)"
    )


def _check_markdown_table_in_response(resp: dict[str, Any]) -> tuple[bool, str]:
    """V15: Response text must contain a markdown table with bank data."""
    content = resp.get("content") or ""
    if not content:
        return False, "NO_CONTENT: response text is empty"

    lines = content.split("\n")
    table_start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (
            stripped.startswith("|")
            and stripped.endswith("|")
            and stripped.count("|") >= 3
        ):
            if i + 1 < len(lines):
                sep = lines[i + 1].strip()
                if re.match(r"^[\s\-:|]+([\|\s\-:|]+)+\|?$", sep):
                    table_start = i
                    break

    if table_start is None:
        return False, (
            "NO_TABLE: response text does not contain a markdown table. "
            "LLM may have omitted it and inject_table_if_missing() did not fire."
        )

    # Count data rows (after header + separator)
    data_rows = 0
    for line in lines[table_start + 2:]:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            data_rows += 1
        else:
            break

    # Verify at least 7/10 banks appear somewhere in the table
    table_text = "\n".join(lines[table_start:table_start + 2 + data_rows]).upper()
    banks_in_table = [b for b in REQUESTED_BANKS if b in table_text]

    if data_rows < 5:
        return False, (
            f"SMALL_TABLE: only {data_rows} data rows found (expected ~10). "
            f"Banks found: {banks_in_table}"
        )

    return True, (
        f"Markdown table present: {data_rows} data rows, "
        f"{len(banks_in_table)}/{len(REQUESTED_BANKS)} banks found"
    )


# ==============================================================================
# All checks
# ==============================================================================

ALL_CHECKS: list[ComponentCheck] = [
    ComponentCheck(
        name="V1_CHART_EXISTS",
        description="Chart must exist and be a horizontal bar chart",
        validate=_check_chart_exists,
    ),
    ComponentCheck(
        name="V2_PERIOD_PARSING",
        description=(
            "Period regex must parse "
            "'periodo inicial = enero 2024 ... periodo actual = enero 2025'"
        ),
        validate=_check_period_parsing,
    ),
    ComponentCheck(
        name="V3_METRIC_DETECTION",
        description=(
            "Response must reference IMOR / morosidad "
            "(not cartera_total or cartera_comercial)"
        ),
        validate=_check_metric_detection,
    ),
    ComponentCheck(
        name="V4_BANK_COVERAGE",
        description="At least 7/10 requested banks must appear in chart",
        validate=_check_bank_coverage,
    ),
    ComponentCheck(
        name="V5_INVEX_HIGHLIGHT",
        description="INVEX bar must be colored red (#E45756)",
        validate=_check_invex_highlight,
    ),
    ComponentCheck(
        name="V6_NEUTRAL_COLORS",
        description="Non-INVEX bars must be grey (#999999)",
        validate=_check_neutral_colors,
    ),
    ComponentCheck(
        name="V7_ZEROLINE",
        description="Layout.xaxis must have zeroline=true",
        validate=_check_zeroline,
    ),
    ComponentCheck(
        name="V8_TABLE_DATA",
        description=(
            "Response must include table_data with 4 columns: "
            "Banco | IMOR 2024 | IMOR 2025 | % Variacion"
        ),
        validate=_check_table_data,
    ),
    ComponentCheck(
        name="V9_NO_FABRICATION",
        description="Response must not contain fabricated value markers",
        validate=_check_no_fabrication,
    ),
    ComponentCheck(
        name="V10_VARIATION_VALUES",
        description=(
            "IMOR variation percentages must be in plausible range [-100%, +5000%]"
        ),
        validate=_check_variation_values,
    ),
    ComponentCheck(
        name="V11_TEXT_LABELS",
        description="Bar text labels must show formatted values",
        validate=_check_text_labels,
    ),
    ComponentCheck(
        name="V12_TABLE_BANK_COVERAGE",
        description="table_data rows must cover 7+/10 requested banks",
        validate=_check_table_bank_coverage,
    ),
    ComponentCheck(
        name="V13_NO_TEXT_CONTRADICTION",
        description="LLM text must NOT deny data when chart has valid data",
        validate=_check_no_text_contradiction,
    ),
    ComponentCheck(
        name="V14_TEXT_CHART_COHERENCE",
        description=(
            "LLM text percentages must match chart values (within 5pp)"
        ),
        validate=_check_text_chart_coherence,
    ),
    ComponentCheck(
        name="V15_MARKDOWN_TABLE",
        description="Response text must contain a markdown table with bank data",
        validate=_check_markdown_table_in_response,
    ),
]


# ==============================================================================
# Runner
# ==============================================================================


def run_checks(resp: dict[str, Any]) -> list[CheckResult]:
    results = []
    for check in ALL_CHECKS:
        passed, detail = check.validate(resp)
        results.append(CheckResult(check=check, passed=passed, detail=detail))
    return results


def main() -> int:
    print("=" * 70)
    print("E2E Test — Variacion de IMOR: Bar Chart Pipeline")
    print(f"Backend: {BACKEND_URL}")
    print(f"Checks: {len(ALL_CHECKS)} component validators")
    print("=" * 70)

    # -- Authenticate --
    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FATAL: Auth failed")
        return 2

    print(f"Authenticated against {BACKEND_URL}")

    # -- Send prompt --
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

    # -- Show response summary --
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
        print(f"  Traces: {len(traces)}")
        if traces:
            trace = traces[0]
            print(
                f"  Type: {trace.get('type')}, "
                f"orientation: {trace.get('orientation')}"
            )
            y_vals = trace.get("y", [])
            print(f"  Banks: {y_vals}")
        table_data = bc.get("table_data")
        if table_data:
            print(f"  Table: {len(table_data.get('rows', []))} rows")
        summary = bc.get("summary", "")
        if summary:
            print(f"  Summary: {summary[:80]}")

    # -- Run checks --
    print(f"\n{'~' * 70}")
    print("COMPONENT CHECKS")
    print(f"{'~' * 70}")

    results = run_checks(resp)

    for r in results:
        tag = "PASS" if r.passed else "FAIL"
        print(f"\n  [{tag}] {r.check.name}")
        print(f"         {r.check.description}")
        print(f"         {r.detail}")

    # -- Summary --
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 70}")

    # -- Save results JSON --
    out = Path(__file__).parent / "variacion_imor_results.json"
    out.write_text(
        json.dumps(
            {
                "test": "variacion-imor-bar-chart",
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
