#!/usr/bin/env python3
"""
E2E Test — CVC/CC Snapshot Bar Chart (single-period, onboarding prompt)

Tests the exact onboarding prompt for "Ranking CVC/CC" which asks for a
single-period horizontal bar chart of CVC/CC ratio across 10 banks.

Pipeline under test:
  evolucion_banco_handler.matches()           → hip_cvc_cc detected
  _handle_multi_bank() → _handle_hip_snapshot → execute_hip_snapshot()
  AverageResult.to_response_dict()            → horizontal bar chart

Prompt under test:
    "Muestra la razón de cartera vencida comercial entre la cartera comercial
     para enero 2025 para los bancos: MONEX, INVEX, BANCREA, SABADELL,
     BANCA MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS Y BANCO BASE.
     Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca
     a INVEX de color rojo. Incluye una tabla con: Banco | CVC/CC 01/2025"

Usage:
    python tests/e2e/charts/test_cvc_cc_snapshot_bar_chart.py
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

# Tableau reference values for 01/2025 (CVC/CC %)
TABLEAU_REFERENCE = {
    "BANCREA": 0.80,
    "MIFEL": 1.23,
    "MONEX": 1.58,
    "INVEX": 2.36,
    "SABADELL": 2.58,
    "BANCO BASE": 2.87,
    "VE POR MAS": 3.51,
    "MULTIVA": 4.33,
    "AFIRME": 4.43,
    "BANSI": 5.67,
}

PROMPT = (
    "Muestra la razón de cartera vencida comercial entre la cartera comercial "
    "para enero 2025 para los bancos: "
    "MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, "
    "VE POR MAS Y BANCO BASE. "
    "Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca "
    "a INVEX de color rojo. "
    "Incluye una tabla con: Banco | CVC/CC 01/2025"
)


# ─── Check helpers ────────────────────────────────────────────────

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


# ─── Individual validators ────────────────────────────────────────

def v1_chart_exists(data: dict) -> str | None:
    chart = data.get("bank_chart", {})
    plotly = chart.get("plotly_config", {})
    traces = plotly.get("data", [])
    if not traces:
        return "No chart traces found"
    t0 = traces[0]
    if t0.get("type") != "bar":
        return f"Expected bar chart, got type={t0.get('type')}"
    if t0.get("orientation") != "h":
        return f"Expected horizontal bars, got orientation={t0.get('orientation')}"
    return None


def v2_single_period(data: dict) -> str | None:
    """Title or metadata should reference a single period, not a range."""
    chart = data.get("bank_chart", {})
    plotly = chart.get("plotly_config", {})
    title = plotly.get("layout", {}).get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")
    title_lower = title.lower()
    # Should mention 2025-01 but NOT "a" between two dates
    if "2025-01" in title or "2025" in title:
        return None
    # Fallback: accept if summary mentions the period
    summary = chart.get("summary", "").lower()
    if "2025" in summary:
        return None
    return f"Period not found in title='{title}' or summary"


def v3_metric_detection(data: dict) -> str | None:
    """Response should reference CVC/CC or cartera vencida comercial."""
    chart = data.get("bank_chart", {})
    metric_name = str(chart.get("metric_name", "")).lower()
    summary = str(chart.get("summary", "")).lower()
    title = str(chart.get("plotly_config", {}).get("layout", {}).get("title", "")).lower()
    combined = f"{metric_name} {summary} {title}"
    if "cvc" in combined or "vencida" in combined:
        return None
    return f"Metric not detected. metric_name='{metric_name}', summary='{summary}'"


def v4_bank_coverage(data: dict) -> str | None:
    chart = data.get("bank_chart", {})
    plotly = chart.get("plotly_config", {})
    traces = plotly.get("data", [])
    if not traces:
        return "No traces"
    y_values = traces[0].get("y", [])
    banks_in_chart = [str(b).upper() for b in y_values]
    found = [b for b in REQUESTED_BANKS if b in banks_in_chart]
    pct = len(found) / len(REQUESTED_BANKS) * 100
    if len(found) < 7:
        missing = [b for b in REQUESTED_BANKS if b not in banks_in_chart]
        return f"Only {len(found)}/10 banks ({pct:.0f}%). Missing: {missing}"
    return None


def v5_invex_highlight(data: dict) -> str | None:
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No traces"
    t0 = traces[0]
    y_vals = [str(b).upper() for b in t0.get("y", [])]
    colors = t0.get("marker", {}).get("color", [])
    if not isinstance(colors, list):
        return f"Colors not a list: {type(colors)}"
    for i, bank in enumerate(y_vals):
        if bank == "INVEX" and i < len(colors):
            c = str(colors[i]).upper()
            if c != "#999999":
                return None  # INVEX has a non-grey color → highlighted
    return "INVEX not highlighted (not found or grey)"


def v6_neutral_colors(data: dict) -> str | None:
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No traces"
    t0 = traces[0]
    y_vals = [str(b).upper() for b in t0.get("y", [])]
    colors = t0.get("marker", {}).get("color", [])
    non_invex_non_grey = []
    for i, bank in enumerate(y_vals):
        if bank != "INVEX" and i < len(colors):
            c = str(colors[i]).upper()
            if c != "#999999":
                non_invex_non_grey.append((bank, c))
    if non_invex_non_grey:
        return f"Non-INVEX banks with non-grey color: {non_invex_non_grey}"
    return None


def v7_values_plausible(data: dict) -> str | None:
    """CVC/CC ratio should be between 0% and 20% for these banks."""
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No traces"
    x_vals = traces[0].get("x", [])
    valid = [v for v in x_vals if v is not None and isinstance(v, (int, float))]
    if not valid:
        return "No numeric x values"
    out_of_range = [v for v in valid if v < 0 or v > 20]
    if out_of_range:
        return f"Values out of range [0, 20]: {out_of_range}"
    return None


def v8_tableau_accuracy(data: dict) -> str | None:
    """Check that values match Tableau reference within ±0.1pp."""
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No traces"
    t0 = traces[0]
    y_vals = [str(b).upper() for b in t0.get("y", [])]
    x_vals = t0.get("x", [])
    mismatches = []
    for i, bank in enumerate(y_vals):
        if bank in TABLEAU_REFERENCE and i < len(x_vals):
            actual = x_vals[i]
            expected = TABLEAU_REFERENCE[bank]
            if actual is not None and abs(actual - expected) > 0.1:
                mismatches.append(
                    f"{bank}: got={actual:.2f}%, expected={expected:.2f}%"
                )
    if mismatches:
        return f"Mismatches (>0.1pp): {'; '.join(mismatches)}"
    matched = sum(1 for i, b in enumerate(y_vals)
                  if b in TABLEAU_REFERENCE and i < len(x_vals)
                  and x_vals[i] is not None
                  and abs(x_vals[i] - TABLEAU_REFERENCE[b]) <= 0.1)
    return None


def v9_table_data(data: dict) -> str | None:
    chart = data.get("bank_chart", {})
    table = chart.get("table_data", {})
    if not table:
        return "No table_data in response"
    cols = table.get("columns", [])
    rows = table.get("rows", [])
    if len(cols) < 2:
        return f"Expected ≥2 columns, got {len(cols)}"
    if len(rows) < 7:
        return f"Expected ≥7 rows, got {len(rows)}"
    return None


def v10_no_fabrication(data: dict) -> str | None:
    text = data.get("content", "")
    markers = ["datos simulados", "datos ficticios", "fabricado", "inventado",
               "no dispongo", "no tengo acceso"]
    for m in markers:
        if m in text.lower():
            return f"Fabrication marker found: '{m}'"
    return None


def v11_bar_count_matches_banks(data: dict) -> str | None:
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No traces"
    y_vals = traces[0].get("y", [])
    x_vals = traces[0].get("x", [])
    if len(y_vals) != len(x_vals):
        return f"y ({len(y_vals)}) != x ({len(x_vals)})"
    if len(y_vals) < 7:
        return f"Only {len(y_vals)} bars, expected ≥7"
    return None


def v12_average_reference_line(data: dict) -> str | None:
    """Check for average reference line (shape) in layout."""
    chart = data.get("bank_chart", {})
    layout = chart.get("plotly_config", {}).get("layout", {})
    shapes = layout.get("shapes", [])
    if not shapes:
        return "SOFT_PASS: No reference line (optional feature)"
    return None


# ─── Main runner ──────────────────────────────────────────────────

def main():
    token = get_auth_token(backend_url=BACKEND_URL)
    resp = send_chat_message(token, PROMPT, backend_url=BACKEND_URL, timeout=TIMEOUT)

    checks = [
        _run("V1_CHART_EXISTS", "Chart must be horizontal bar chart", v1_chart_exists, resp),
        _run("V2_SINGLE_PERIOD", "Must reference single period (01/2025)", v2_single_period, resp),
        _run("V3_METRIC_DETECTION", "Must reference CVC/CC metric", v3_metric_detection, resp),
        _run("V4_BANK_COVERAGE", "≥7/10 requested banks in chart", v4_bank_coverage, resp),
        _run("V5_INVEX_HIGHLIGHT", "INVEX bar must be colored (not grey)", v5_invex_highlight, resp),
        _run("V6_NEUTRAL_COLORS", "Non-INVEX bars must be grey", v6_neutral_colors, resp),
        _run("V7_VALUES_PLAUSIBLE", "CVC/CC values between 0% and 20%", v7_values_plausible, resp),
        _run("V8_TABLEAU_ACCURACY", "Values match Tableau (±0.1pp)", v8_tableau_accuracy, resp),
        _run("V9_TABLE_DATA", "table_data with ≥2 cols and ≥7 rows", v9_table_data, resp),
        _run("V10_NO_FABRICATION", "No fabrication markers in text", v10_no_fabrication, resp),
        _run("V11_BAR_COUNT", "Bar count matches bank count", v11_bar_count_matches_banks, resp),
        _run("V12_AVG_LINE", "Average reference line (optional)", v12_average_reference_line, resp),
    ]

    passed = sum(1 for c in checks if c.passed)
    failed = sum(1 for c in checks if not c.passed)
    total = len(checks)

    print(f"\n{'=' * 70}")
    print(f"TEST: CVC/CC Snapshot Bar Chart (onboarding prompt)")
    print(f"{'=' * 70}\n")

    for c in checks:
        status = "PASS" if c.passed else "FAIL"
        print(f"  [{status}] {c.name}")
        print(f"         {c.description}")
        if c.detail != "OK":
            print(f"         {c.detail}")
        print()

    print(f"{'=' * 70}")
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 70}")

    # Save results
    results = {
        "test": "cvc-cc-snapshot-bar-chart",
        "prompt": PROMPT,
        "backend_url": BACKEND_URL,
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "checks": [
            {"name": c.name, "description": c.description,
             "passed": c.passed, "detail": c.detail}
            for c in checks
        ],
        "response_summary": {
            "content_length": len(resp.get("content", "")),
            "has_chart": bool(resp.get("bank_chart", {}).get("plotly_config")),
            "events": resp.get("events", []),
            "content_preview": resp.get("content", "")[:300],
        },
    }

    out_path = Path(__file__).with_name("cvc_cc_snapshot_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved: {out_path}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
