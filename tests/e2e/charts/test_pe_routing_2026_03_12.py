#!/usr/bin/env python3
"""
E2E Test — Pérdida Esperada Routing (2026-03-12)

Validates that PE queries return pe_sg/pe_total, NOT cartera_total
or cartera_comercial_sin_gob.

Reported issues:
- "no me da los bancos que le solicite"
- "me dice que es la cartera gobierno no la perdida esperada"
- "me da la misma información de perdida esperada sin gobierno"

DB reference (INVEX):
  pe_sg:    0.79%  (periodo 202511)
  pe_total: 6.27%  (periodo 202512)

Scenarios:
  S1 — PE sin gobierno de INVEX (should return ~0.79%)
  S2 — PE total (con gobierno) de INVEX (should return ~6.27%, distinct from pe_sg)
  S3 — PE barras 10 bancos (bank coverage)
  S4 — "Pérdida esperada total sin gobierno" explicit (regression guard)

Usage:
    TEST_BACKEND_URL=http://localhost:8000 python tests/e2e/charts/test_pe_routing_2026_03_12.py
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "120"))

TARGET_BANKS = [
    "MONEX", "INVEX", "BANCREA", "SABADELL", "MIFEL",
    "MULTIVA", "AFIRME", "BANSI", "VE POR MAS", "BANCO BASE",
]
BANK_ALIASES = {"BANCA MIFEL": "MIFEL"}

# ══════════════════════════════════════════════════════════════════════════════
# Prompts
# ══════════════════════════════════════════════════════════════════════════════

PROMPT_S1 = "Cuál es la pérdida esperada sin gobierno de INVEX?"

PROMPT_S2 = "Cuál es la pérdida esperada total incluyendo gobierno de INVEX?"

PROMPT_S3 = (
    "Muestra la pérdida esperada sin gobierno para los bancos: "
    "MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, "
    "AFIRME, BANSI, VE POR MAS Y BANCO BASE.\n"
    "Gráfica de barras horizontales."
)

PROMPT_S4 = "Pérdida esperada total sin gobierno de INVEX para diciembre 2025"

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CheckResult:
    name: str
    description: str
    passed: bool
    detail: str

@dataclass
class ScenarioResult:
    scenario_id: str
    prompt: str
    checks: list[CheckResult] = field(default_factory=list)
    response_summary: dict[str, Any] = field(default_factory=dict)

def _run(name, desc, fn, *args):
    try:
        error = fn(*args)
        if error is None:
            return CheckResult(name, desc, True, "OK")
        if error.startswith("SOFT_PASS:"):
            return CheckResult(name, desc, True, error)
        return CheckResult(name, desc, False, error)
    except Exception as e:
        return CheckResult(name, desc, False, f"Exception: {e}")

def _normalize_bank(name):
    n = name.strip().upper()
    return BANK_ALIASES.get(n, n)

def _is_numeric(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def _get_bar_banks(resp):
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return []
    for axis in ("y", "x"):
        vals = traces[0].get(axis, [])
        banks = [_normalize_bank(str(b)) for b in vals if not _is_numeric(str(b))]
        if banks:
            return banks
    return []

def _get_bar_values(resp):
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return []
    for axis in ("x", "y"):
        vals = [v for v in traces[0].get(axis, []) if isinstance(v, (int, float))]
        if vals:
            return vals
    return []

def _get_line_traces(resp):
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    return {_normalize_bank(t.get("name", "")): t.get("y", []) for t in traces if t.get("name")}

def _get_metric_name(resp):
    bc = resp.get("bank_chart", {})
    return (bc.get("metric_name") or "").lower()

def _get_chart_title(resp):
    bc = resp.get("bank_chart", {})
    layout = bc.get("plotly_config", {}).get("layout", {})
    title = layout.get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")
    return str(title).lower()

_DATA_DENIAL_PHRASES = [
    "no se dispone de datos", "no tengo datos", "no hay datos disponibles",
    "no se encontraron datos", "no encontré datos", "datos no disponibles",
]

# ══════════════════════════════════════════════════════════════════════════════
# Validators
# ══════════════════════════════════════════════════════════════════════════════

def chart_exists(resp):
    bc = resp.get("bank_chart", {})
    if not bc.get("plotly_config", {}).get("data"):
        return "No chart traces found"
    return None

def not_cartera_total(resp):
    vals = _get_bar_values(resp)
    if not vals:
        for name, y_vals in _get_line_traces(resp).items():
            valid = [v for v in y_vals if isinstance(v, (int, float))]
            if valid and max(abs(v) for v in valid) > 1_000_000:
                return f"REGRESSION: trace '{name}' has MDP-scale values"
        return None
    if vals and max(abs(v) for v in vals) > 1_000_000:
        return f"REGRESSION: values are MDP-scale (max={max(vals):,.0f}), not PE %"
    metric = _get_metric_name(resp)
    if "cartera total" in metric and "p" not in metric:
        return f"REGRESSION: metric_name='{metric}' is cartera_total"
    return None

def not_cartera_gobierno(resp):
    """Must NOT confuse PE with cartera_comercial_sin_gob."""
    metric = _get_metric_name(resp)
    title = _get_chart_title(resp)
    content = resp.get("content", "").lower()
    combined = f"{metric} {title}"
    if "cartera comercial" in combined and "pérdida" not in combined and "pe " not in combined:
        return f"WRONG METRIC: got cartera_comercial, not PE. metric='{metric}'"
    # Content check: if it says "cartera comercial sin gobierno" without PE context
    if "cartera comercial sin gobierno" in content and "pérdida esperada" not in content:
        return "Content describes cartera_comercial_sin_gob, not PE"
    return None

def no_data_denial(resp):
    content = resp.get("content", "").lower()
    for phrase in _DATA_DENIAL_PHRASES:
        if phrase in content:
            return f"LLM denied data: '{phrase}'"
    return None

def s1_pe_sg_value(resp):
    """PE SG for INVEX should be ~0.79% (small percentage, not billions)."""
    content = resp.get("content", "")
    vals = _get_bar_values(resp)
    # PE sg is ~0.79% or 0.0079 ratio
    if vals and any(0 < v < 5 for v in vals):
        return None
    if vals and any(0 < v < 0.05 for v in vals):
        return None  # ratio
    traces = _get_line_traces(resp)
    for name, y_vals in traces.items():
        valid = [v for v in y_vals if isinstance(v, (int, float))]
        if valid and any(0 < v < 5 for v in valid):
            return None
        if valid and any(0 < v < 0.05 for v in valid):
            return None
    if any(x in content for x in ["0.7", "0.8", "0,7", "0,8", "0.79"]):
        return None
    return f"Expected PE SG ~0.79% for INVEX. Content: {content[:300]}"

def s2_pe_total_value(resp):
    """PE total (con gobierno) for INVEX should be ~6.27% (distinct from pe_sg ~0.79%)."""
    content = resp.get("content", "")
    vals = _get_bar_values(resp)
    # PE total is ~6.27%
    if vals and any(3 < v < 15 for v in vals):
        return None
    if vals and any(0.03 < v < 0.15 for v in vals):
        return None  # ratio
    traces = _get_line_traces(resp)
    for name, y_vals in traces.items():
        valid = [v for v in y_vals if isinstance(v, (int, float))]
        if valid and any(3 < v < 15 for v in valid):
            return None
        if valid and any(0.03 < v < 0.15 for v in valid):
            return None
    if any(x in content for x in ["6.2", "6.3", "6,2", "6,3"]):
        return None
    return f"Expected PE total ~6.27% for INVEX (distinct from pe_sg ~0.79%). Content: {content[:300]}"

def s3_bank_coverage(resp):
    banks = _get_bar_banks(resp)
    found = [b for b in TARGET_BANKS if b in banks]
    if len(found) < 8:
        missing = [b for b in TARGET_BANKS if b not in banks]
        return f"Only {len(found)}/10 banks. Missing: {missing}. Got: {banks}"
    return None

def s3_only_requested_banks(resp):
    banks = _get_bar_banks(resp) or list(_get_line_traces(resp).keys())
    if not banks:
        return None
    extra = [b for b in banks if b not in TARGET_BANKS and b not in ("SISTEMA", "PROMEDIO")]
    if len(extra) > 2:
        return f"Too many unrequested banks: {extra[:5]}"
    return None

# ══════════════════════════════════════════════════════════════════════════════
# Scenarios
# ══════════════════════════════════════════════════════════════════════════════

SCENARIOS = [
    (
        "S1_PE_SG_INVEX",
        "PE sin gobierno INVEX (~0.79%)",
        PROMPT_S1,
        [
            ("V1_CHART_EXISTS", "Chart must exist", chart_exists),
            ("V2_NOT_CARTERA_TOTAL", "NOT cartera_total regression", not_cartera_total),
            ("V3_NOT_CARTERA_GOB", "NOT cartera_comercial confusion", not_cartera_gobierno),
            ("V4_PE_SG_VALUE", "PE SG ~0.79% for INVEX", s1_pe_sg_value),
            ("V5_NO_DATA_DENIAL", "LLM must not deny data", no_data_denial),
        ],
    ),
    (
        "S2_PE_TOTAL_INVEX",
        "PE total con gobierno INVEX (~6.27%, distinct from SG)",
        PROMPT_S2,
        [
            ("V1_CHART_EXISTS", "Chart must exist", chart_exists),
            ("V2_NOT_CARTERA_TOTAL", "NOT cartera_total regression", not_cartera_total),
            ("V3_NOT_CARTERA_GOB", "NOT cartera_comercial confusion", not_cartera_gobierno),
            ("V4_PE_TOTAL_VALUE", "PE total ~6.27% (not same as SG)", s2_pe_total_value),
            ("V5_NO_DATA_DENIAL", "LLM must not deny data", no_data_denial),
        ],
    ),
    (
        "S3_PE_BAR_10",
        "PE sin gob barras 10 bancos (bank coverage)",
        PROMPT_S3,
        [
            ("V1_CHART_EXISTS", "Chart must exist", chart_exists),
            ("V2_NOT_CARTERA_TOTAL", "NOT cartera_total regression", not_cartera_total),
            ("V3_BANK_COVERAGE", ">=8/10 target banks in chart", s3_bank_coverage),
            ("V4_ONLY_REQUESTED", "No extra unrequested banks", s3_only_requested_banks),
            ("V5_NO_DATA_DENIAL", "LLM must not deny data", no_data_denial),
        ],
    ),
    (
        "S4_PE_SG_EXPLICIT",
        "PE total sin gobierno explicit (regression guard)",
        PROMPT_S4,
        [
            ("V1_CHART_EXISTS", "Chart must exist", chart_exists),
            ("V2_NOT_CARTERA_TOTAL", "NOT cartera_total regression", not_cartera_total),
            ("V3_NOT_CARTERA_GOB", "NOT cartera_comercial confusion", not_cartera_gobierno),
            ("V4_PE_SG_VALUE", "PE SG ~0.79% for INVEX", s1_pe_sg_value),
            ("V5_NO_DATA_DENIAL", "LLM must not deny data", no_data_denial),
        ],
    ),
]

# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════

def run_scenario(token, scenario_id, description, prompt, validators):
    print(f"\n{'─' * 70}")
    print(f"  {scenario_id}: {description}")
    print(f"  Prompt: \"{prompt[:90]}...\"")
    print(f"  Sending (timeout={TIMEOUT}s)...")

    resp = send_chat_message(token, prompt, backend_url=BACKEND_URL, timeout=TIMEOUT)
    result = ScenarioResult(scenario_id=scenario_id, prompt=prompt)

    if resp.get("error"):
        print(f"  ERROR: {resp['error']}")
        result.checks = [CheckResult("INFRA", "Request must succeed", False, str(resp["error"]))]
        result.response_summary = {"error": str(resp["error"])}
        return result

    content = resp.get("content", "")
    bc = resp.get("bank_chart", {})
    banks = _get_bar_banks(resp) or list(_get_line_traces(resp).keys())
    metric = _get_metric_name(resp)

    print(f"  Response: {len(content)} chars, chart={'present' if bc else 'MISSING'}, metric='{metric}'")
    print(f"  Banks: {len(banks)} → {banks[:5]}{'...' if len(banks) > 5 else ''}")

    for v_name, v_desc, v_fn in validators:
        check = _run(v_name, v_desc, v_fn, resp)
        status = "PASS" if check.passed else "FAIL"
        detail_str = f" — {check.detail}" if check.detail != "OK" else ""
        print(f"    [{status}] {v_name}: {v_desc}{detail_str}")
        result.checks.append(check)

    result.response_summary = {
        "content_length": len(content), "has_chart": bool(bc),
        "banks_in_chart": banks, "metric_name": metric,
        "content_preview": content[:400],
    }
    return result


def main():
    filter_scenario = None
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--scenario" and i < len(sys.argv) - 1:
            filter_scenario = sys.argv[i + 1].upper()

    scenarios = SCENARIOS
    if filter_scenario:
        scenarios = [s for s in SCENARIOS if s[0].startswith(filter_scenario)]
        if not scenarios:
            print(f"No scenario matching '{filter_scenario}'. Available: {[s[0] for s in SCENARIOS]}")
            sys.exit(2)

    print(f"\n{'=' * 70}")
    print(f"  E2E Pérdida Esperada Routing — 2026-03-12")
    print(f"  Backend: {BACKEND_URL}")
    print(f"  Scenarios: {len(scenarios)}")
    print(f"{'=' * 70}")

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("\nFATAL: Authentication failed")
        sys.exit(2)
    print(f"\nAuthenticated against {BACKEND_URL}")

    all_results = []
    total_passed = total_failed = 0

    for sid, desc, prompt, validators in scenarios:
        result = run_scenario(token, sid, desc, prompt, validators)
        all_results.append(result)
        for c in result.checks:
            if c.passed:
                total_passed += 1
            else:
                total_failed += 1

    total = total_passed + total_failed
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY: {total_passed}/{total} passed, {total_failed} failed")
    print(f"{'=' * 70}")
    for r in all_results:
        p = sum(1 for c in r.checks if c.passed)
        f = sum(1 for c in r.checks if not c.passed)
        print(f"  [{'PASS' if f == 0 else 'FAIL'}] {r.scenario_id} ({p}/{p + f})")
    if total_failed > 0:
        print(f"\n  Failed checks:")
        for r in all_results:
            for c in r.checks:
                if not c.passed:
                    print(f"    {r.scenario_id}/{c.name}: {c.detail}")

    out_path = Path(__file__).with_name("pe_routing_2026_03_12_results.json")
    with open(out_path, "w") as f:
        json.dump({
            "test": "pe-routing-2026-03-12",
            "backend_url": BACKEND_URL,
            "total_checks": total, "passed": total_passed, "failed": total_failed,
            "scenarios": [{
                "scenario_id": r.scenario_id, "prompt": r.prompt,
                "checks": [{"name": c.name, "description": c.description,
                             "passed": c.passed, "detail": c.detail} for c in r.checks],
                "response_summary": r.response_summary,
            } for r in all_results],
        }, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved: {out_path}")
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
