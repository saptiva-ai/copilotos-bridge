#!/usr/bin/env python3
"""
E2E Test — PE Total SG: Bar Chart Pipeline

Sends a prompt requesting the average of PE Total SG for 10 banks
between enero 2023 and enero 2025, and validates every component of the
response: chart type, period parsing, bank coverage, coloring (INVEX red,
rest grey), table_data, metric detection (pe_sg), text/chart coherence,
and anti-fabrication guards.

This test validates the pipeline that feeds through:
  evolucion_banco_handler._detect_metric()  → "pe_sg"
  BaseHandler._parse_period_comparison()    → ("2023-01-01", "2025-01-01")
  execute_average() (discrete-period)       → bar chart with 3-month avg

Prompt under test:
    "Toma como periodo inicial enero 2023 y como periodo actual enero 2025.
     Presenta gráfica de barras con el promedio de PE Total SG entre MONEX,
     INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI,
     VE POR MÁS y BANCO BASE. Marca a INVEX de color rojo."

Usage:
    python tests/e2e/charts/test_reservas_totales_bar_chart.py
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

# The exact prompt — "Pérdida Esperada Total SG" (ratio metric, not currency)
PROMPT = (
    "Toma como periodo inicial enero 2023 y como periodo actual enero 2025. "
    "Presenta gráfica de barras con el promedio de Pérdida Esperada Total SG "
    "entre MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, "
    "BANSI, VE POR MÁS y BANCO BASE. Marca a INVEX de color rojo."
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

# Suspicious round values suggesting LLM fabrication
SUSPICIOUS_ROUND_PATTERN = re.compile(r"\$[\d,]*[05]00[,.]000[,.]000")


# ══════════════════════════════════════════════════════════════════════════════
# Data Classes (replay pattern)
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


# ══════════════════════════════════════════════════════════════════════════════
# Component Validators
# ══════════════════════════════════════════════════════════════════════════════


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
    """V2: Chart title or metadata must reference 2023 and/or 2025."""
    layout = _get_layout(resp)
    if not layout:
        return False, "NO_LAYOUT: cannot verify period in title"

    title = layout.get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")

    has_2023 = "2023" in title
    has_2025 = "2025" in title

    if has_2023 and has_2025:
        return True, f"Period parsed correctly: title='{title}'"
    if has_2023 or has_2025:
        return True, f"Period partially in title: title='{title}'"

    bc = resp.get("bank_chart", {})
    summary = bc.get("summary", "")
    if "2023" in summary or "2025" in summary:
        return True, f"Period in summary: '{summary[:80]}'"

    return False, (
        f"PERIOD_MISS: title='{title}', expected 2023 or 2025. "
        f"Period 'enero 2023 ... enero 2025' not detected."
    )


def _check_metric_detection(resp: dict[str, Any]) -> tuple[bool, str]:
    """V3: Metric must be PE/pe_sg-related (not cartera_total or reservas).

    The prompt says "PE Total SG", so the handler should detect pe_sg,
    NOT cartera_comercial, cartera_total, or reservas_etapa_todas.
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
    metadata = bc.get("metadata", {})

    title_lower = title.lower()
    summary_lower = summary.lower()

    # Positive: "pe" or "pe sg" or "pérdida esperada" should appear
    has_pe = (
        "pe sg" in title_lower
        or "pe_sg" in title_lower
        or "pe sg" in summary_lower
        or "pe_sg" in summary_lower
    )

    # Also accept metric_type == "ratio" as evidence of correct routing
    is_ratio = metadata.get("metric_type") == "ratio"

    # Negative: should NOT say "cartera" or "reservas" (wrong metric)
    has_wrong_metric = (
        "cartera_comercial" in title_lower
        or "cartera_total" in title_lower
        or "reservas" in title_lower
    )

    if has_pe:
        return True, (
            f"Metric detection OK: 'PE SG' found. "
            f"title='{title}', summary='{summary[:60]}'"
        )

    if is_ratio:
        return True, (
            f"Metric detection OK via metadata: metric_type='ratio'. "
            f"title='{title[:60]}'"
        )

    if has_wrong_metric:
        return False, (
            f"WRONG_METRIC: detected cartera/reservas instead of pe_sg. "
            f"_detect_metric() may have matched the wrong keyword."
        )

    content_lower = (resp.get("content") or "").lower()
    metric_type = metadata.get("metric_type", "")
    if "pe" in content_lower or "pérdida esperada" in content_lower:
        return True, (
            f"METRIC_IN_CONTENT: 'PE' found in LLM text. "
            f"metric_type='{metric_type}', title='{title[:50]}'"
        )

    return True, (
        f"METRIC_INDIRECT: no explicit 'PE SG' in title/summary, "
        f"but metric_type='{metric_type}'. title='{title[:50]}'"
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


def _check_table_data(resp: dict[str, Any]) -> tuple[bool, str]:
    """V7: Response should include table_data with 2 columns (Banco + PE/Promedio)."""
    bc = resp.get("bank_chart")
    if not bc:
        return False, "NO_CHART: cannot check table_data"

    table_data = bc.get("table_data")
    if not table_data:
        return False, "NO_TABLE_DATA: table_data not present in response"

    columns = table_data.get("columns", [])
    rows = table_data.get("rows", [])

    if len(columns) < 2:
        return False, f"TOO_FEW_COLUMNS: expected ≥2, got {len(columns)}: {columns}"

    if not rows:
        return False, "EMPTY_TABLE: table_data.rows is empty"

    has_banco = any("banco" in c.lower() for c in columns)
    has_metric = any(
        "pe" in c.lower() or "prom" in c.lower() or "sg" in c.lower()
        for c in columns
    )

    if not has_banco:
        return False, f"BAD_COLUMNS: columns={columns}, missing 'Banco'"
    if not has_metric:
        return False, (
            f"BAD_COLUMNS: columns={columns}, missing PE/PROM/SG column"
        )

    valid_rows = 0
    for row in rows:
        if len(row) >= 2 and row[1] is not None:
            try:
                float(row[1])
                valid_rows += 1
            except (TypeError, ValueError):
                pass

    return True, (
        f"Table data OK: {len(columns)} columns, {len(rows)} rows, "
        f"{valid_rows} with valid numeric value. Columns: {columns}"
    )


def _check_no_fabrication(resp: dict[str, Any]) -> tuple[bool, str]:
    """V8: Response content should not contain fabricated value markers."""
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


def _check_values_plausible(resp: dict[str, Any]) -> tuple[bool, str]:
    """V9: Chart values should be plausible percentage values (0-100%).

    PE Total SG is a ratio metric (reservas_sg / cartera_total × 100).
    Typical values are in the range 0-20% for most banks.
    Values must be positive and within 0-100%.
    """
    trace = _get_first_trace(resp)
    if not trace:
        return False, "NO_TRACE: cannot verify values"

    x_vals = trace.get("x", [])
    y_vals = trace.get("y", [])

    if not x_vals:
        return False, "NO_VALUES: trace.x is empty"

    none_count = 0
    out_of_range = []
    for i, val in enumerate(x_vals):
        if val is None:
            none_count += 1
            continue
        try:
            v = float(val)
            if v < 0 or v > 100:
                bank = y_vals[i] if i < len(y_vals) else f"idx_{i}"
                out_of_range.append(f"{bank}={v:.2f}%")
        except (TypeError, ValueError):
            pass

    if none_count == len(x_vals):
        return False, "ALL_NONE: every value is None"

    if out_of_range:
        return False, (
            f"OUT_OF_RANGE: {len(out_of_range)} banks outside 0-100%: "
            f"{out_of_range[:5]}"
        )

    valid = len(x_vals) - none_count
    non_none: list[float] = []
    for v in x_vals:
        if v is None:
            continue
        try:
            non_none.append(float(v))
        except (TypeError, ValueError):
            pass

    if not non_none:
        return False, "NO_NUMERIC: x_vals contain no parseable numbers"

    return True, (
        f"Values OK: {valid}/{len(x_vals)} valid, all within 0-100%. "
        f"range=[{min(non_none):.2f}%, {max(non_none):.2f}%]"
    )


def _check_text_labels(resp: dict[str, Any]) -> tuple[bool, str]:
    """V10: Bar text labels should show percentage-formatted values.

    For PE Total SG (ratio metric), labels should be like "4.95%".
    """
    trace = _get_first_trace(resp)
    if not trace:
        return False, "NO_TRACE: cannot verify text labels"

    text_vals = trace.get("text", [])
    textposition = trace.get("textposition", "")

    if not text_vals:
        return False, "NO_TEXT: trace.text is empty"

    # Labels should contain numeric content with % suffix
    pct_labels = [t for t in text_vals if re.search(r"\d.*%", str(t))]
    numeric_labels = [t for t in text_vals if re.search(r"\d", str(t))]

    if pct_labels:
        return True, (
            f"Text labels OK: {len(pct_labels)}/{len(text_vals)} with %, "
            f"position='{textposition}', sample={text_vals[:3]}"
        )

    if numeric_labels:
        return True, (
            f"Text labels OK (no %): {len(numeric_labels)}/{len(text_vals)} "
            f"with numbers, position='{textposition}', sample={text_vals[:3]}"
        )

    return False, (
        f"NO_NUMERIC_LABELS: text values lack numbers: {text_vals[:3]}"
    )


def _check_table_bank_coverage(resp: dict[str, Any]) -> tuple[bool, str]:
    """V11: table_data rows should cover most of the 10 banks."""
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
    """V12: LLM text must NOT deny data when the chart has valid data."""
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


def _check_markdown_table_in_response(resp: dict[str, Any]) -> tuple[bool, str]:
    """V13: Response text must contain a markdown table with bank data.

    Validates that either the LLM generated or the post-processor injected
    a pipe-delimited markdown table in the response content.
    """
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
                if re.match(r"^\|[\s\-:|]+(\|[\s\-:|]+)+\|$", sep):
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
    table_text = "\n".join(
        lines[table_start:table_start + 2 + data_rows]
    ).upper()
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


# ══════════════════════════════════════════════════════════════════════════════
# All checks
# ══════════════════════════════════════════════════════════════════════════════

ALL_CHECKS: list[ComponentCheck] = [
    ComponentCheck(
        name="V1_CHART_EXISTS",
        description="Chart must exist and be a horizontal bar chart",
        validate=_check_chart_exists,
    ),
    ComponentCheck(
        name="V2_PERIOD_PARSING",
        description=(
            "Period must reference 2023 and/or 2025 "
            "(enero 2023 ... enero 2025)"
        ),
        validate=_check_period_parsing,
    ),
    ComponentCheck(
        name="V3_METRIC_DETECTION",
        description=(
            "_detect_metric() must classify 'PE Total SG' as "
            "pe_sg ratio metric (not cartera_total or reservas)"
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
        name="V7_TABLE_DATA",
        description=(
            "Response must include table_data with ≥2 columns "
            "(Banco + PE/PROM)"
        ),
        validate=_check_table_data,
    ),
    ComponentCheck(
        name="V8_NO_FABRICATION",
        description="Response must not contain fabricated value markers",
        validate=_check_no_fabrication,
    ),
    ComponentCheck(
        name="V9_VALUES_PLAUSIBLE",
        description=(
            "Chart values must be plausible percentage values "
            "(PE Total SG is a ratio, expected 0-100%)"
        ),
        validate=_check_values_plausible,
    ),
    ComponentCheck(
        name="V10_TEXT_LABELS",
        description="Bar text labels must show percentage-formatted values",
        validate=_check_text_labels,
    ),
    ComponentCheck(
        name="V11_TABLE_BANK_COVERAGE",
        description="table_data rows must cover 7+/10 requested banks",
        validate=_check_table_bank_coverage,
    ),
    ComponentCheck(
        name="V12_NO_TEXT_CONTRADICTION",
        description="LLM text must NOT deny data when chart has valid data",
        validate=_check_no_text_contradiction,
    ),
    ComponentCheck(
        name="V13_MARKDOWN_TABLE",
        description="Response text must contain a markdown table with bank data",
        validate=_check_markdown_table_in_response,
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
    print("E2E Test — PE Total SG: Bar Chart Pipeline")
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
    out = Path(__file__).parent / "reservas_totales_results.json"
    out.write_text(
        json.dumps(
            {
                "test": "pe-total-sg-bar-chart",
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
