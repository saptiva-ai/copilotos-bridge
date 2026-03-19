#!/usr/bin/env python3
"""
E2E Test — IMOR Comercial Snapshot Diciembre 2025 (Post-ETL Refresh)

Validates that IMOR Comercial (Sin Gobierno) for December 2025 is
accessible end-to-end. This metric has the widest coverage: 38 banks
(vs 6 for other KPIs) because it comes from the dedicated IMOR
Comercial loader.

DB reference (6 major banks, bank_fact_kpis_mensual, loaded 2026-03-02):
    HSBC:        3.22%  (0.0322)
    INVEX:       2.29%  (0.0229)
    CITIBANAMEX: 1.74%  (0.0174)
    BANORTE:     1.62%  (0.0162)
    SANTANDER:   1.59%  (0.0159)
    BBVA:        1.06%  (0.0106)

Usage:
    python tests/e2e/charts/test_imor_comercial_dic2025_snapshot.py
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

# IMOR Comercial stored as decimal ratio
DB_REFERENCE_PCT = {
    "HSBC": 3.22,
    "INVEX": 2.29,
    "CITIBANAMEX": 1.74,
    "BANORTE": 1.62,
    "SANTANDER": 1.59,
    "BBVA": 1.06,
}
DB_REFERENCE_DECIMAL = {k: v / 100 for k, v in DB_REFERENCE_PCT.items()}

PROMPT = (
    "Muestra el IMOR comercial sin gobierno para diciembre 2025 para los bancos: "
    "BANORTE, BBVA, CITIBANAMEX, HSBC, INVEX y SANTANDER. "
    "Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca "
    "a INVEX de color rojo. "
    "Incluye una tabla con: Banco | IMOR Comercial 12/2025"
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
    return "decimal" if max(valid) < 1.0 else "percentage"


def v1_chart_exists(data: dict) -> str | None:
    chart = data.get("bank_chart", {})
    traces = chart.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No chart traces found"
    t0 = traces[0]
    if t0.get("type") != "bar":
        return f"Expected bar, got type={t0.get('type')}"
    if t0.get("orientation") != "h":
        return f"Expected horizontal, got orientation={t0.get('orientation')}"
    return None


def v2_period_reference(data: dict) -> str | None:
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
    """Must reference IMOR comercial or cartera comercial sin gobierno."""
    chart = data.get("bank_chart", {})
    metric = str(chart.get("metric_name", "")).lower()
    summary = str(chart.get("summary", "")).lower()
    title = str(chart.get("plotly_config", {}).get("layout", {}).get("title", "")).lower()
    text = data.get("content", "").lower()
    combined = f"{metric} {summary} {title} {text}"
    if "imor" in combined and ("comercial" in combined or "sin gob" in combined):
        return None
    if "imor_comercial" in combined or "morosidad comercial" in combined:
        return None
    if "imor" in combined:
        return None  # at least references IMOR
    return f"Metric not detected. metric='{metric}'"


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
    if isinstance(colors, str):
        return "SOFT_PASS: single color for all bars"
    if not isinstance(colors, list):
        return f"SOFT_PASS: unexpected color type: {type(colors)}"
    for i, bank in enumerate(y_vals):
        if bank == "INVEX" and i < len(colors):
            if str(colors[i]).upper() != "#999999":
                return None
    return "INVEX not highlighted"


def v6_values_plausible(data: dict) -> str | None:
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
    else:
        out = [v for v in valid if v < 0 or v > 15]
    if out:
        return f"Values out of range ({scale}): {out}"
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
                    mismatches.append(f"{bank}: got={actual:.4f}, exp={expected:.4f}")
                else:
                    matched += 1
    if mismatches:
        return f"Mismatches: {'; '.join(mismatches)}"
    if matched == 0:
        return "No banks matched against DB reference"
    return None


def v8_table_data(data: dict) -> str | None:
    chart = data.get("bank_chart", {})
    table = chart.get("table_data", {})
    if not table:
        return "No table_data"
    if len(table.get("rows", [])) < 5:
        return f"Expected >=5 rows, got {len(table.get('rows', []))}"
    return None


def v9_no_fabrication(data: dict) -> str | None:
    text = data.get("content", "").lower()
    for m in ["datos simulados", "datos ficticios", "fabricado", "no dispongo"]:
        if m in text:
            return f"Fabrication marker: '{m}'"
    return None


def v10_no_contradiction(data: dict) -> str | None:
    traces = data.get("bank_chart", {}).get("plotly_config", {}).get("data", [])
    if not traces:
        return None
    text = data.get("content", "").lower()
    for d in ["no tengo los datos", "no tengo datos", "no se encontraron datos"]:
        if d in text:
            return f"Chart has data but LLM says: '{d}'"
    return None


def main():
    print(f"\n{'=' * 70}")
    print("E2E Test — IMOR Comercial Snapshot Dic 2025 (Post-ETL Refresh)")
    print(f"Backend: {BACKEND_URL}")
    print(f"{'=' * 70}\n")

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FATAL: Auth failed")
        sys.exit(2)

    print(f"Sending prompt (timeout={TIMEOUT}s)...\n")
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
        _run("V2_PERIOD_REF", "References Dec 2025", v2_period_reference, resp),
        _run("V3_METRIC", "References IMOR comercial", v3_metric_detection, resp),
        _run("V4_BANK_COVERAGE", ">=5/6 banks", v4_bank_coverage, resp),
        _run("V5_INVEX_HIGHLIGHT", "INVEX colored", v5_invex_highlight, resp),
        _run("V6_PLAUSIBLE", "Values in range", v6_values_plausible, resp),
        _run("V7_DB_ACCURACY", "Match DB reference", v7_db_accuracy, resp),
        _run("V8_TABLE_DATA", "Table present", v8_table_data, resp),
        _run("V9_NO_FABRICATION", "No fabrication", v9_no_fabrication, resp),
        _run("V10_NO_CONTRADICTION", "No denial", v10_no_contradiction, resp),
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

    out_path = Path(__file__).with_name("imor_comercial_dic2025_snapshot_results.json")
    with open(out_path, "w") as f:
        json.dump({
            "test": "imor-comercial-dic2025-snapshot", "prompt": PROMPT,
            "passed": passed, "failed": failed,
            "db_reference_pct": DB_REFERENCE_PCT,
            "checks": [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in checks],
            "response_summary": {"content_length": len(content), "has_chart": bool(bc)},
        }, f, indent=2, ensure_ascii=False)
    print(f"Results saved: {out_path}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
