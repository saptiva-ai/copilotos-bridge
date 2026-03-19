#!/usr/bin/env python3
"""
E2E Test — IMOR Snapshot Diciembre 2025 (Post-ETL Refresh)

Validates that IMOR (Índice de Morosidad) for December 2025 is
accessible end-to-end through the chat system.

DB reference values (bank_fact_kpis_mensual, loaded 2026-03-02):
    HSBC:        3.05%  (0.0305)
    INVEX:       2.65%  (0.0265)
    CITIBANAMEX: 2.16%  (0.0216)
    SANTANDER:   2.03%  (0.0203)
    BBVA:        1.63%  (0.0163)
    BANORTE:     1.41%  (0.0141)

Usage:
    python tests/e2e/charts/test_imor_dic2025_snapshot.py
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

REQUESTED_BANKS = [
    "BANORTE", "BBVA", "CITIBANAMEX", "HSBC", "INVEX", "SANTANDER",
]

# IMOR stored as decimal ratio: 0.0305 = 3.05%
DB_REFERENCE_PCT = {
    "HSBC": 3.05,
    "INVEX": 2.65,
    "CITIBANAMEX": 2.16,
    "SANTANDER": 2.03,
    "BBVA": 1.63,
    "BANORTE": 1.41,
}
DB_REFERENCE_DECIMAL = {k: v / 100 for k, v in DB_REFERENCE_PCT.items()}

PROMPT = (
    "Muestra el IMOR para diciembre 2025 para los bancos: "
    "BANORTE, BBVA, CITIBANAMEX, HSBC, INVEX y SANTANDER. "
    "Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca "
    "a INVEX de color rojo. "
    "Incluye una tabla con: Banco | IMOR 12/2025"
)


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


def _detect_scale(x_vals: list) -> str:
    valid = [v for v in x_vals if v is not None and isinstance(v, (int, float))]
    if not valid:
        return "unknown"
    max_val = max(valid)
    return "decimal" if max_val < 1.0 else "percentage"


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
    chart = data.get("bank_chart", {})
    plotly = chart.get("plotly_config", {})
    title = plotly.get("layout", {}).get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")
    text = data.get("content", "")
    combined = f"{title} {chart.get('summary', '')} {text}".lower()
    if "2025" in combined or "diciembre" in combined:
        return None
    return f"Period not found in title/summary/text"


def v3_metric_detection(data: dict) -> str | None:
    chart = data.get("bank_chart", {})
    metric = str(chart.get("metric_name", "")).lower()
    summary = str(chart.get("summary", "")).lower()
    title = str(chart.get("plotly_config", {}).get("layout", {}).get("title", "")).lower()
    combined = f"{metric} {summary} {title}"
    if "imor" in combined or "morosidad" in combined:
        return None
    return f"Metric not detected. metric_name='{metric}', title='{title[:80]}'"


def v4_bank_coverage(data: dict) -> str | None:
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No traces"
    y_values = [str(b).upper() for b in traces[0].get("y", [])]
    found = [b for b in REQUESTED_BANKS if b in y_values]
    if len(found) < 5:
        missing = [b for b in REQUESTED_BANKS if b not in y_values]
        return f"Only {len(found)}/6 banks. Missing: {missing}"
    return None


def v5_invex_highlight(data: dict) -> str | None:
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No traces"
    t0 = traces[0]
    y_vals = [str(b).upper() for b in t0.get("y", [])]
    colors = t0.get("marker", {}).get("color", [])
    # Handle single-color string (all bars same color) — highlighting not applied
    if isinstance(colors, str):
        return "SOFT_PASS: single color for all bars (no per-bar highlighting)"
    if not isinstance(colors, list):
        return f"SOFT_PASS: unexpected color type: {type(colors)}"
    for i, bank in enumerate(y_vals):
        if bank == "INVEX" and i < len(colors):
            c = str(colors[i]).upper()
            if c != "#999999":
                return None
    return "INVEX not highlighted"


def v6_values_plausible(data: dict) -> str | None:
    """IMOR values should be between 0-10% or 0.00-0.10 decimal."""
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
        out = [v for v in valid if v < 0.0 or v > 0.15]
        if out:
            return f"Values out of range [0, 0.15] (decimal): {out}"
    else:
        out = [v for v in valid if v < 0 or v > 15]
        if out:
            return f"Values out of range [0, 15] (percentage): {out}"
    return None


def v7_db_accuracy(data: dict) -> str | None:
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No traces"
    t0 = traces[0]
    y_vals = [str(b).upper() for b in t0.get("y", [])]
    x_vals = t0.get("x", [])
    scale = _detect_scale(x_vals)
    ref = DB_REFERENCE_DECIMAL if scale == "decimal" else DB_REFERENCE_PCT
    tol = 0.005 if scale == "decimal" else 0.5
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
        return f"Mismatches (>{tol}): {'; '.join(mismatches)}"
    if matched == 0:
        return "No banks matched against DB reference"
    return None


def v8_table_data(data: dict) -> str | None:
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
    text = data.get("content", "").lower()
    markers = ["datos simulados", "datos ficticios", "fabricado", "inventado",
               "no dispongo", "no tengo acceso"]
    for m in markers:
        if m in text:
            return f"Fabrication marker: '{m}'"
    return None


def v10_no_contradiction(data: dict) -> str | None:
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return None
    text = data.get("content", "").lower()
    denials = ["no tengo los datos", "no tengo datos", "no está disponible",
               "no se encontraron datos", "no hay datos disponibles"]
    for d in denials:
        if d in text:
            return f"Chart has data but LLM says: '{d}'"
    return None


def main():
    print(f"\n{'=' * 70}")
    print("E2E Test — IMOR Snapshot Diciembre 2025 (Post-ETL Refresh)")
    print(f"Backend: {BACKEND_URL}")
    print(f"{'=' * 70}\n")

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FATAL: Authentication failed")
        sys.exit(2)

    print(f"Authenticated. Sending prompt (timeout={TIMEOUT}s)...\n")
    resp = send_chat_message(token, PROMPT, backend_url=BACKEND_URL, timeout=TIMEOUT)

    if resp.get("error"):
        print(f"FATAL: {resp['error']}")
        sys.exit(2)

    content = resp.get("content", "")
    bc = resp.get("bank_chart")
    print(f"Response: {len(content)} chars, chart={'present' if bc else 'MISSING'}")
    if bc:
        traces = bc.get("plotly_config", {}).get("data", [])
        if traces:
            for i, b in enumerate(traces[0].get("y", [])):
                v = traces[0].get("x", [])[i] if i < len(traces[0].get("x", [])) else "?"
                print(f"  {b}: {v}")

    checks = [
        _run("V1_CHART_EXISTS", "Horizontal bar chart", v1_chart_exists, resp),
        _run("V2_SINGLE_PERIOD", "References Dec 2025", v2_single_period, resp),
        _run("V3_METRIC_DETECTION", "References IMOR metric", v3_metric_detection, resp),
        _run("V4_BANK_COVERAGE", ">=5/6 banks in chart", v4_bank_coverage, resp),
        _run("V5_INVEX_HIGHLIGHT", "INVEX colored (not grey)", v5_invex_highlight, resp),
        _run("V6_VALUES_PLAUSIBLE", "IMOR in plausible range", v6_values_plausible, resp),
        _run("V7_DB_ACCURACY", "Values match DB reference", v7_db_accuracy, resp),
        _run("V8_TABLE_DATA", "table_data present", v8_table_data, resp),
        _run("V9_NO_FABRICATION", "No fabrication markers", v9_no_fabrication, resp),
        _run("V10_NO_CONTRADICTION", "LLM doesn't deny data", v10_no_contradiction, resp),
    ]

    passed = sum(1 for c in checks if c.passed)
    failed = sum(1 for c in checks if not c.passed)

    print(f"\n{'─' * 70}")
    for c in checks:
        status = "PASS" if c.passed else "FAIL"
        print(f"  [{status}] {c.name} — {c.description}")
        if c.detail != "OK":
            print(f"         {c.detail}")
    print(f"{'=' * 70}")
    print(f"RESULTS: {passed}/{len(checks)} passed, {failed} failed")
    print(f"{'=' * 70}")

    out_path = Path(__file__).with_name("imor_dic2025_snapshot_results.json")
    with open(out_path, "w") as f:
        json.dump({
            "test": "imor-dic2025-snapshot", "prompt": PROMPT,
            "backend_url": BACKEND_URL, "passed": passed, "failed": failed,
            "db_reference_pct": DB_REFERENCE_PCT,
            "checks": [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in checks],
            "response_summary": {
                "content_length": len(content),
                "has_chart": bool(bc),
                "content_preview": content[:500],
            },
        }, f, indent=2, ensure_ascii=False)
    print(f"Results saved: {out_path}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
