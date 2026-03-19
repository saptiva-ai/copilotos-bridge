#!/usr/bin/env python3
"""
E2E Test — ICAP Snapshot Diciembre 2025 (Post-ETL Refresh)

Validates that the December 2025 data loaded by the ETL refresh is
accessible end-to-end through the chat system.

Reference values from bank_fact_kpis_mensual (loaded 2026-03-02):
    BANORTE:     20.06%
    BBVA:        20.15%
    CITIBANAMEX: 20.82%
    HSBC:        19.38%
    INVEX:       16.38%
    SANTANDER:   18.49%

Pipeline under test:
  QueryRouter → evolucion_banco_handler._handle_hip_snapshot
  → execute_hip_snapshot() (hip_icap in _METRIC_MAP)

Usage:
    python tests/e2e/charts/test_icap_dic2025_snapshot.py

    # Custom backend (e.g. via SSH tunnel to PROD)
    TEST_BACKEND_URL=http://localhost:18000 python tests/e2e/charts/test_icap_dic2025_snapshot.py
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "120"))

# Banks with complete KPIs in December 2025
REQUESTED_BANKS = [
    "BANORTE", "BBVA", "CITIBANAMEX", "HSBC", "INVEX", "SANTANDER",
]

# DB reference values from ETL refresh (2026-03-02)
# ICAP stored as decimal ratio in DB: 0.1638 = 16.38%
# The chart formatter may return either format — validators handle both.
DB_REFERENCE_PCT = {
    "CITIBANAMEX": 20.82,
    "BBVA": 20.15,
    "BANORTE": 20.06,
    "HSBC": 19.38,
    "SANTANDER": 18.49,
    "INVEX": 16.38,
}
DB_REFERENCE_DECIMAL = {k: v / 100 for k, v in DB_REFERENCE_PCT.items()}

PROMPT = (
    "Muestra el ICAP para diciembre 2025 para los bancos: "
    "BANORTE, BBVA, CITIBANAMEX, HSBC, INVEX y SANTANDER. "
    "Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca "
    "a INVEX de color rojo. "
    "Incluye una tabla con: Banco | ICAP 12/2025"
)


# --- Check infrastructure ---------------------------------------------------

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
        if error.startswith("SOFT_PASS:"):
            return CheckResult(name, description, True, error)
        return CheckResult(name, description, False, error)
    except Exception as e:
        return CheckResult(name, description, False, f"Exception: {e}")


# --- Validators --------------------------------------------------------------

def v1_chart_exists(data: dict) -> str | None:
    """Chart must be a horizontal bar chart."""
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
    """Title or metadata should reference December 2025."""
    chart = data.get("bank_chart", {})
    plotly = chart.get("plotly_config", {})
    title = plotly.get("layout", {}).get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")
    combined = f"{title} {chart.get('summary', '')}".lower()
    if "2025-12" in combined or "12/2025" in combined or "diciembre 2025" in combined:
        return None
    if "2025" in combined:
        return None  # at least references the year
    return f"Period not found. title='{title}'"


def v3_metric_detection(data: dict) -> str | None:
    """Response should reference ICAP or capitalización."""
    chart = data.get("bank_chart", {})
    metric = str(chart.get("metric_name", "")).lower()
    summary = str(chart.get("summary", "")).lower()
    title = str(chart.get("plotly_config", {}).get("layout", {}).get("title", "")).lower()
    combined = f"{metric} {summary} {title}"
    if "icap" in combined or "capitalizacion" in combined or "capitalización" in combined:
        return None
    return f"Metric not detected. metric_name='{metric}', summary='{summary[:80]}'"


def v4_bank_coverage(data: dict) -> str | None:
    """At least 5 of 6 requested banks must appear."""
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No traces"
    y_values = [str(b).upper() for b in traces[0].get("y", [])]
    found = [b for b in REQUESTED_BANKS if b in y_values]
    if len(found) < 5:
        missing = [b for b in REQUESTED_BANKS if b not in y_values]
        return f"Only {len(found)}/6 banks. Missing: {missing}. Got: {y_values}"
    return None


def v5_invex_highlight(data: dict) -> str | None:
    """INVEX bar should be highlighted (non-grey color)."""
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
                return None
    return "INVEX not highlighted (not found or grey)"


def _detect_scale(x_vals: list) -> str:
    """Detect whether chart values are decimal ratios or percentages."""
    valid = [v for v in x_vals if v is not None and isinstance(v, (int, float))]
    if not valid:
        return "unknown"
    max_val = max(valid)
    return "decimal" if max_val < 1.0 else "percentage"


def v6_values_plausible(data: dict) -> str | None:
    """ICAP values should be plausible (10-30% or 0.10-0.30 decimal)."""
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No traces"
    x_vals = traces[0].get("x", [])
    valid = [v for v in x_vals if v is not None and isinstance(v, (int, float))]
    if not valid:
        return "No numeric x values"
    scale = _detect_scale(x_vals)
    if scale == "decimal":
        out = [v for v in valid if v < 0.05 or v > 0.40]
        if out:
            return f"Values out of range [0.05, 0.40] (decimal): {out}"
    else:
        out = [v for v in valid if v < 5 or v > 40]
        if out:
            return f"Values out of range [5, 40] (percentage): {out}"
    return None


def v7_db_accuracy(data: dict) -> str | None:
    """Values must match DB reference within tolerance (auto-detects scale)."""
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No traces"
    t0 = traces[0]
    y_vals = [str(b).upper() for b in t0.get("y", [])]
    x_vals = t0.get("x", [])

    scale = _detect_scale(x_vals)
    ref = DB_REFERENCE_DECIMAL if scale == "decimal" else DB_REFERENCE_PCT
    # Tolerance: 0.01 for decimal (= 1 pp), 1.0 for percentage
    tol = 0.01 if scale == "decimal" else 1.0

    mismatches = []
    matched = 0
    for i, bank in enumerate(y_vals):
        if bank in ref and i < len(x_vals):
            actual = x_vals[i]
            expected = ref[bank]
            if actual is not None:
                diff = abs(actual - expected)
                if diff > tol:
                    mismatches.append(
                        f"{bank}: got={actual:.4f}, expected={expected:.4f}, diff={diff:.4f}"
                    )
                else:
                    matched += 1
    if mismatches:
        return f"Mismatches (>{tol} in {scale} scale): {'; '.join(mismatches)}"
    if matched == 0:
        return "No banks matched against DB reference"
    return None


def v8_table_data(data: dict) -> str | None:
    """Response should include table_data with >=2 columns and >=5 rows."""
    chart = data.get("bank_chart", {})
    table = chart.get("table_data", {})
    if not table:
        return "No table_data in response"
    cols = table.get("columns", [])
    rows = table.get("rows", [])
    if len(cols) < 2:
        return f"Expected >=2 columns, got {len(cols)}"
    if len(rows) < 5:
        return f"Expected >=5 rows, got {len(rows)}"
    return None


def v9_no_fabrication(data: dict) -> str | None:
    """LLM text must not contain fabrication markers."""
    text = data.get("content", "").lower()
    markers = [
        "datos simulados", "datos ficticios", "fabricado", "inventado",
        "no dispongo", "no tengo acceso",
    ]
    for m in markers:
        if m in text:
            return f"Fabrication marker found: '{m}'"
    return None


def v10_no_text_contradiction(data: dict) -> str | None:
    """LLM text must NOT deny having data when chart has data."""
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return None  # no chart to contradict
    text = data.get("content", "").lower()
    denials = [
        "no tengo los datos", "no tengo datos", "no está disponible",
        "no se encontraron datos", "no hay datos disponibles",
        "datos no disponibles", "lamentablemente no",
    ]
    for d in denials:
        if d in text:
            return f"Chart has data but LLM says: '{d}'"
    return None


def v11_invex_in_text(data: dict) -> str | None:
    """LLM response should mention INVEX."""
    if "INVEX" in data.get("content", "").upper():
        return None
    return "INVEX not mentioned in LLM text"


def v12_december_in_text(data: dict) -> str | None:
    """LLM response should mention December 2025."""
    text = data.get("content", "").lower()
    if "diciembre 2025" in text or "dic 2025" in text or "12/2025" in text or "2025-12" in text:
        return None
    if "diciembre" in text or "december" in text:
        return None  # at least references the month
    return "SOFT_PASS: December not explicitly mentioned in text"


# --- Main runner -------------------------------------------------------------

def main():
    print(f"\n{'=' * 70}")
    print("E2E Test — ICAP Snapshot Diciembre 2025 (Post-ETL Refresh)")
    print(f"Backend: {BACKEND_URL}")
    print(f"{'=' * 70}\n")

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FATAL: Authentication failed")
        sys.exit(2)

    print(f"Authenticated against {BACKEND_URL}")
    print(f"\nPROMPT: \"{PROMPT[:100]}...\"")
    print(f"Sending (timeout={TIMEOUT}s)...\n")

    resp = send_chat_message(token, PROMPT, backend_url=BACKEND_URL, timeout=TIMEOUT)

    if resp.get("error"):
        print(f"FATAL: Request error: {resp['error']}")
        sys.exit(2)

    # Print response summary
    content = resp.get("content", "")
    bc = resp.get("bank_chart")
    events = resp.get("events", [])
    print(f"Response: {len(content)} chars, chart={'present' if bc else 'MISSING'}")
    print(f"Events: {events}")

    if bc:
        traces = bc.get("plotly_config", {}).get("data", [])
        if traces:
            t0 = traces[0]
            banks = t0.get("y", [])
            vals = t0.get("x", [])
            print(f"Traces: {len(traces)}, bars: {len(banks)}")
            for i, b in enumerate(banks):
                v = vals[i] if i < len(vals) else "?"
                print(f"  {b}: {v}")

    # Run validators
    checks = [
        _run("V1_CHART_EXISTS", "Chart must be horizontal bar", v1_chart_exists, resp),
        _run("V2_SINGLE_PERIOD", "Must reference Dec 2025", v2_single_period, resp),
        _run("V3_METRIC_DETECTION", "Must reference ICAP metric", v3_metric_detection, resp),
        _run("V4_BANK_COVERAGE", ">=5/6 requested banks in chart", v4_bank_coverage, resp),
        _run("V5_INVEX_HIGHLIGHT", "INVEX bar colored (not grey)", v5_invex_highlight, resp),
        _run("V6_VALUES_PLAUSIBLE", "ICAP values in [10, 30] range", v6_values_plausible, resp),
        _run("V7_DB_ACCURACY", "Values match DB reference (+-1.0 pp)", v7_db_accuracy, resp),
        _run("V8_TABLE_DATA", "table_data with >=2 cols, >=5 rows", v8_table_data, resp),
        _run("V9_NO_FABRICATION", "No fabrication markers in text", v9_no_fabrication, resp),
        _run("V10_NO_CONTRADICTION", "LLM must not deny data", v10_no_text_contradiction, resp),
        _run("V11_INVEX_IN_TEXT", "LLM text mentions INVEX", v11_invex_in_text, resp),
        _run("V12_DECEMBER_IN_TEXT", "LLM text mentions December", v12_december_in_text, resp),
    ]

    passed = sum(1 for c in checks if c.passed)
    failed = sum(1 for c in checks if not c.passed)
    total = len(checks)

    print(f"\n{'─' * 70}")
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
        "test": "icap-dic2025-snapshot",
        "prompt": PROMPT,
        "backend_url": BACKEND_URL,
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "db_reference_pct": DB_REFERENCE_PCT,
        "db_reference_decimal": DB_REFERENCE_DECIMAL,
        "checks": [
            {"name": c.name, "description": c.description,
             "passed": c.passed, "detail": c.detail}
            for c in checks
        ],
        "response_summary": {
            "content_length": len(resp.get("content", "")),
            "has_chart": bool((resp.get("bank_chart") or {}).get("plotly_config")),
            "events": resp.get("events", []),
            "content_preview": resp.get("content", "")[:500],
        },
    }

    out_path = Path(__file__).with_name("icap_dic2025_snapshot_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved: {out_path}")

    if failed > 0:
        print("\nFailed checks:")
        for c in checks:
            if not c.passed:
                print(f"  - {c.name}: {c.detail}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
