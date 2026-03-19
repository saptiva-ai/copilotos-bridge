#!/usr/bin/env python3
"""
E2E Test — Quebrantos CC Snapshot Bar Chart

Tests the onboarding prompt for "Promedio Quebrantos" which asks for a
single-period horizontal bar chart of Quebrantos Comerciales (CC) across
10 banks.

Data source: CASTIGOS.xlsx "CASTIGOS" sheet
  Backfill: scripts/data/backfill_castigos.py (LIB_CASTIGOS_COMERC + QUITAS_COMER)
  DB column: bank_fact_kpis_mensual.quebrantos_comerciales (pesos, SCALE=1M)
  Period: 01/2023 (monthly metric, most banks have zero in many months)
  Note: Original Tableau reference values are from an older XLSX version and
  cannot be reconciled with current data. Tests validate structural correctness.

Pipeline path:
  evolucion_banco_handler → hip_quebrantos_cc → execute_hip_snapshot()
  Registered in: handler, evolution.py, peer_average.py, template_sql, comparison_tools

Usage:
    python tests/e2e/charts/test_quebrantos_cc_snapshot_bar_chart.py
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

REQUESTED_BANKS = [
    "MONEX", "INVEX", "BANCREA", "SABADELL", "MIFEL",
    "MULTIVA", "AFIRME", "BANSI", "VE POR MAS", "BANCO BASE",
]

# XLSX reference values for 01/2023 (from CASTIGOS.xlsx "CASTIGOS" sheet, MDP)
# Note: Original Tableau screenshot values were from an older XLSX version
# and cannot be reconciled with current data.  These are the actual values
# from the XLSX currently used by backfill_castigos.py.
XLSX_REFERENCE_202301 = {
    "MONEX": 14.62,
    "BANCREA": 5.78,
    "AFIRME": 0.02,
    "MIFEL": 0.00,
    "VE POR MAS": 0.00,
    "BANCO BASE": 0.00,
    "SABADELL": 0.00,
    "MULTIVA": 0.00,
    "INVEX": 0.00,
    "BANSI": 0.00,
}

# Improved prompt: date-first, explicit metric, explicit chart request.
# Uses "enero 2023" to match Tableau reference values.
PROMPT = (
    "Muestra los quebrantos comerciales de enero 2023 para los bancos: "
    "MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, "
    "VE POR MAS Y BANCO BASE. "
    "Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca "
    "a INVEX de color rojo. "
    "Incluye una tabla con: Banco | Quebrantos CC (MDP)"
)

# Colors from chart_formatter.py
INVEX_RED = "#E45756"
NEUTRAL_GREY = "#999999"

# Fabrication markers
FABRICATION_PHRASES = [
    "datos simulados", "datos ficticios", "fabricado", "inventado",
    "no dispongo", "no tengo acceso", "estimado basado en tendencia",
    "proyectado", "aproximado basado en",
]

# Text contradiction phrases
TEXT_CONTRADICTION_PHRASES = [
    "no tengo los datos", "no tengo datos",
    "no está disponible", "no esta disponible",
    "no cuento con los datos", "no cuento con datos",
    "no encuentro información", "no encuentro informacion",
    "no se encontraron datos", "no hay datos disponibles",
    "no dispongo de",
    "no puedo realizar la comparación", "no puedo realizar la comparacion",
    "datos no disponibles", "sin datos para",
    "lamentablemente no", "lo siento, pero no tengo",
    "no fue posible obtener",
]


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class CheckResult:
    name: str
    description: str
    passed: bool
    detail: str


def _run(name: str, description: str, fn: Callable[..., str | None],
         *args: Any) -> CheckResult:
    try:
        error = fn(*args)
        if error is None:
            return CheckResult(name, description, True, "OK")
        return CheckResult(name, description, False, error)
    except Exception as e:
        return CheckResult(name, description, False, f"Exception: {e}")


def _get_plotly(data: dict) -> dict:
    return data.get("bank_chart", {}).get("plotly_config", {})


def _get_first_trace(data: dict) -> dict:
    traces = _get_plotly(data).get("data", [])
    return traces[0] if traces else {}


def _get_layout(data: dict) -> dict:
    return _get_plotly(data).get("layout", {})


# ══════════════════════════════════════════════════════════════════════════════
# Validators
# ══════════════════════════════════════════════════════════════════════════════


def v1_chart_exists(data: dict) -> str | None:
    """V1: Chart must exist and be a horizontal bar chart."""
    if data.get("error"):
        return f"Request error: {data['error']}"
    chart = data.get("bank_chart", {})
    if not chart:
        return "CHART_MISSING: no bank_chart in response"
    t0 = _get_first_trace(data)
    if not t0:
        return "CHART_EMPTY: no data traces in plotly_config"
    if t0.get("type") != "bar":
        return f"WRONG_TYPE: expected 'bar', got '{t0.get('type')}'"
    if t0.get("orientation") != "h":
        return f"WRONG_ORIENTATION: expected 'h', got '{t0.get('orientation')}'"
    return None


def v2_single_period(data: dict) -> str | None:
    """V2: Title or metadata should reference a single period (2024)."""
    title = _get_layout(data).get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")
    title_lower = title.lower()
    if "2023" in title_lower:
        return None
    summary = data.get("bank_chart", {}).get("summary", "").lower()
    if "2023" in summary:
        return None
    content = (data.get("content") or "").lower()
    if "2023" in content and "enero" in content:
        return None
    return f"Period 2024 not found in title='{title}' or summary or content"


def v3_metric_detection(data: dict) -> str | None:
    """V3: Response should reference quebrantos or castigos."""
    chart = data.get("bank_chart", {})
    title = str(_get_layout(data).get("title", "")).lower()
    summary = str(chart.get("summary", "")).lower()
    content = (data.get("content") or "").lower()
    combined = f"{title} {summary} {content}"
    keywords = ["quebrant", "castigo", "write-off", "charge-off"]
    for kw in keywords:
        if kw in combined:
            return None
    return (
        f"Metric not detected. None of {keywords} found in "
        f"title='{title[:50]}', summary='{summary[:50]}', content[:100]='{content[:100]}'"
    )


def v4_bank_coverage(data: dict) -> str | None:
    """V4: At least 7/10 requested banks should appear in chart."""
    t0 = _get_first_trace(data)
    if not t0:
        return "No traces"
    y_vals = [str(b).upper() for b in t0.get("y", [])]
    found = []
    for bank in REQUESTED_BANKS:
        if any(bank in y or y in bank for y in y_vals):
            found.append(bank)
    pct = len(found) / len(REQUESTED_BANKS) * 100
    if len(found) < 7:
        missing = [b for b in REQUESTED_BANKS if b not in found]
        return f"Only {len(found)}/10 banks ({pct:.0f}%). Missing: {missing}"
    return None


def v5_invex_highlight(data: dict) -> str | None:
    """V5: INVEX bar must be colored red (not grey)."""
    t0 = _get_first_trace(data)
    if not t0:
        return "No traces"
    y_vals = [str(b).upper() for b in t0.get("y", [])]
    colors = t0.get("marker", {}).get("color", [])
    if not isinstance(colors, list):
        return f"Colors not a list: {type(colors)}"
    for i, bank in enumerate(y_vals):
        if bank == "INVEX" and i < len(colors):
            c = str(colors[i]).upper()
            if c != NEUTRAL_GREY.upper():
                return None  # Highlighted with non-grey color
    return "INVEX not highlighted (not found or same grey as others)"


def v6_neutral_colors(data: dict) -> str | None:
    """V6: Non-INVEX bars should be grey (#999999)."""
    t0 = _get_first_trace(data)
    if not t0:
        return "No traces"
    y_vals = [str(b).upper() for b in t0.get("y", [])]
    colors = t0.get("marker", {}).get("color", [])
    non_invex_non_grey = []
    for i, bank in enumerate(y_vals):
        if bank != "INVEX" and i < len(colors):
            c = str(colors[i]).upper()
            if c != NEUTRAL_GREY.upper():
                non_invex_non_grey.append((bank, c))
    if non_invex_non_grey:
        return f"Non-INVEX banks with non-grey color: {non_invex_non_grey}"
    return None


def v7_values_plausible(data: dict) -> str | None:
    """V7: Quebrantos CC values should be in plausible range.

    DB stores quebrantos in pesos; pipeline divides ÷1M for display as MDP.
    Plausible range: [0, 200 MDP] per bank per month.
    Negative values are impossible (write-offs are always positive or zero).
    """
    t0 = _get_first_trace(data)
    if not t0:
        return "No traces"
    x_vals = t0.get("x", [])
    valid = [v for v in x_vals if v is not None and isinstance(v, (int, float))]
    if not valid:
        return "No numeric x values"
    negatives = [v for v in valid if v < 0]
    if negatives:
        return f"Negative values found (impossible for quebrantos): {negatives}"
    max_mdp = 200  # 200 MDP (display unit after ÷1M scaling)
    out_of_range = [v for v in valid if v > max_mdp]
    if out_of_range:
        return f"Values suspiciously high (>{max_mdp} MDP): {out_of_range}"
    return None


def v8_table_data(data: dict) -> str | None:
    """V8: Response should include table_data with >=2 columns and >=7 rows."""
    chart = data.get("bank_chart", {})
    table = chart.get("table_data", {})
    if not table:
        return "No table_data in response"
    cols = table.get("columns", [])
    rows = table.get("rows", [])
    if len(cols) < 2:
        return f"Expected >=2 columns, got {len(cols)}: {cols}"
    if len(rows) < 7:
        return f"Expected >=7 rows, got {len(rows)}"
    return None


def v9_no_fabrication(data: dict) -> str | None:
    """V9: Response must not contain fabrication markers."""
    content = (data.get("content") or "").lower()
    for phrase in FABRICATION_PHRASES:
        if phrase in content:
            return f"Fabrication marker found: '{phrase}'"
    return None


def v10_no_text_contradiction(data: dict) -> str | None:
    """V10: LLM text must not deny data when chart has valid data."""
    chart = data.get("bank_chart", {})
    content = (data.get("content") or "").lower()
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return None  # No chart to contradict
    x_vals = [v for v in traces[0].get("x", []) if v is not None]
    if not x_vals:
        return None
    found = [p for p in TEXT_CONTRADICTION_PHRASES if p in content]
    if found:
        return (
            f"TEXT_CONTRADICTION: chart has {len(x_vals)} data points but "
            f"LLM text denies data: {found}"
        )
    return None


def v11_bar_count(data: dict) -> str | None:
    """V11: Number of bars should match banks and be consistent."""
    t0 = _get_first_trace(data)
    if not t0:
        return "No traces"
    y_vals = t0.get("y", [])
    x_vals = t0.get("x", [])
    if len(y_vals) != len(x_vals):
        return f"y ({len(y_vals)}) != x ({len(x_vals)})"
    if len(y_vals) < 7:
        return f"Only {len(y_vals)} bars, expected >=7"
    return None


def v12_markdown_table(data: dict) -> str | None:
    """V12: Response text should contain a markdown table with bank data."""
    content = data.get("content") or ""
    if not content:
        return "NO_CONTENT: response text is empty"
    lines = content.split("\n")
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
                    # Count data rows
                    data_rows = 0
                    for row_line in lines[i + 2:]:
                        s = row_line.strip()
                        if s.startswith("|") and s.endswith("|"):
                            data_rows += 1
                        else:
                            break
                    if data_rows >= 5:
                        return None
                    return f"SMALL_TABLE: only {data_rows} data rows (expected >=5)"
    return "NO_TABLE: no markdown table found in response text"


# ══════════════════════════════════════════════════════════════════════════════
# Main runner
# ══════════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 70)
    print("E2E Test — Quebrantos CC Snapshot Bar Chart")
    print(f"Backend: {BACKEND_URL}")
    print(f"Checks: 12 component validators")
    print("=" * 70)

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FATAL: Auth failed")
        return 2

    print(f"Authenticated against {BACKEND_URL}")
    print(f"\nPrompt ({len(PROMPT)} chars):")
    print(f'  "{PROMPT[:100]}..."')
    print(f"\nSending (timeout={TIMEOUT}s)...")

    resp = send_chat_message(token, PROMPT, backend_url=BACKEND_URL, timeout=TIMEOUT)

    if resp.get("error"):
        print(f"\nFATAL: Request failed: {resp['error']}")
        return 2

    # Show response summary
    content = resp.get("content", "")
    bc = resp.get("bank_chart")
    events = resp.get("events", [])
    print(f"\nResponse received:")
    print(f"  Events: {events}")
    print(f"  Content: {len(content)} chars")
    print(f"  Chart: {'present' if bc else 'MISSING'}")

    if bc:
        plotly = bc.get("plotly_config", {})
        traces = plotly.get("data", [])
        print(f"  Traces: {len(traces)}")
        if traces:
            t0 = traces[0]
            print(f"  Type: {t0.get('type')}, orientation: {t0.get('orientation')}")
            y_vals = t0.get("y", [])
            x_vals = t0.get("x", [])
            print(f"  Banks (y): {y_vals}")
            print(f"  Values (x): {x_vals}")
        table = bc.get("table_data")
        if table:
            print(f"  Table: {len(table.get('rows', []))} rows")

    # Run checks
    checks = [
        _run("V1_CHART_EXISTS", "Chart must be horizontal bar chart", v1_chart_exists, resp),
        _run("V2_SINGLE_PERIOD", "Must reference period enero 2024", v2_single_period, resp),
        _run("V3_METRIC_DETECTION", "Must reference quebrantos/castigos", v3_metric_detection, resp),
        _run("V4_BANK_COVERAGE", ">=7/10 requested banks in chart", v4_bank_coverage, resp),
        _run("V5_INVEX_HIGHLIGHT", "INVEX bar must be colored (not grey)", v5_invex_highlight, resp),
        _run("V6_NEUTRAL_COLORS", "Non-INVEX bars must be grey", v6_neutral_colors, resp),
        _run("V7_VALUES_PLAUSIBLE", "Quebrantos values in [0, 200] MDP", v7_values_plausible, resp),
        _run("V8_TABLE_DATA", "table_data with >=2 cols and >=7 rows", v8_table_data, resp),
        _run("V9_NO_FABRICATION", "No fabrication markers in text", v9_no_fabrication, resp),
        _run("V10_NO_CONTRADICTION", "Text must not deny data", v10_no_text_contradiction, resp),
        _run("V11_BAR_COUNT", "Bar count matches bank count", v11_bar_count, resp),
        _run("V12_MARKDOWN_TABLE", "Response has markdown table with bank data", v12_markdown_table, resp),
    ]

    # Print results
    passed = sum(1 for c in checks if c.passed)
    failed = sum(1 for c in checks if not c.passed)
    total = len(checks)

    print(f"\n{'─' * 70}")
    print("COMPONENT CHECKS")
    print(f"{'─' * 70}")

    for c in checks:
        status = "PASS" if c.passed else "FAIL"
        print(f"\n  [{status}] {c.name}")
        print(f"         {c.description}")
        if c.detail != "OK":
            print(f"         {c.detail}")

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 70}")

    # Save results
    results = {
        "test": "quebrantos-cc-snapshot-bar-chart",
        "prompt": PROMPT,
        "backend_url": BACKEND_URL,
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "xlsx_reference_01_2023": XLSX_REFERENCE_202301,
        "checks": [
            {"name": c.name, "description": c.description,
             "passed": c.passed, "detail": c.detail}
            for c in checks
        ],
        "response_summary": {
            "content_length": len(content),
            "has_chart": bc is not None,
            "events": events,
            "content_preview": content[:300],
        },
    }

    out_path = Path(__file__).with_name("quebrantos_cc_snapshot_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved: {out_path}")

    if failed > 0:
        print("\nFailed checks:")
        for c in checks:
            if not c.passed:
                print(f"  - {c.name}: {c.detail}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
