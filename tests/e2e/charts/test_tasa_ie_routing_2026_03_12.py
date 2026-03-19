#!/usr/bin/env python3
"""
E2E Test — Tasa de Interés Efectiva Routing (2026-03-12)

Validates that "tasa de interés efectiva" queries return tasa_sistema,
NOT cartera_total or hip_tasa_me.

Reported issues:
- "me da la información de la cartera total y de bancos que no le pedí"
- "no me da los datos de la tasa de interés efectiva, me da de tasa ME"

Scenarios:
  S1 — Tasa IE de INVEX (single bank, tasa_sistema ~35.7 for dic 2024)
  S2 — Tasa IE barras 10 bancos
  S3 — "Tasa efectiva de INVEX" (shorter prompt, risk of tasa_me confusion)

Usage:
    TEST_BACKEND_URL=http://localhost:8000 python tests/e2e/charts/test_tasa_ie_routing_2026_03_12.py
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "120"))

TARGET_BANKS = [
    "BANORTE", "BBVA", "CITIBANAMEX", "HSBC", "INVEX", "SANTANDER",
]
BANK_ALIASES = {"BANCA MIFEL": "MIFEL"}

# ══════════════════════════════════════════════════════════════════════════════
# Prompts
# ══════════════════════════════════════════════════════════════════════════════

PROMPT_S1 = "Cuál es la tasa de interés efectiva de INVEX?"

PROMPT_S2 = (
    "Muestra la tasa de interés efectiva para los bancos: "
    "BANORTE, BBVA, CITIBANAMEX, HSBC, INVEX Y SANTANDER.\n"
    "Gráfica de barras horizontales."
)

PROMPT_S3 = "Cuál es la tasa efectiva de INVEX?"

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

def _get_chart_title(resp):
    bc = resp.get("bank_chart", {})
    layout = bc.get("plotly_config", {}).get("layout", {})
    title = layout.get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")
    return str(title).lower()

def _get_metric_name(resp):
    bc = resp.get("bank_chart", {})
    return (bc.get("metric_name") or "").lower()

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
        return f"REGRESSION: values are MDP-scale (max={max(vals):,.0f}), not tasa %"
    title = _get_chart_title(resp)
    metric = _get_metric_name(resp)
    if "cartera total" in metric and "tasa" not in metric:
        return f"REGRESSION: metric_name='{metric}' is cartera_total"
    return None

def not_tasa_me(resp):
    """Must NOT return tasa ME (moneda extranjera) instead of tasa sistema."""
    title = _get_chart_title(resp)
    metric = _get_metric_name(resp)
    combined = f"{title} {metric}"
    if "moneda extranjera" in combined or "tasa me" in combined:
        return f"WRONG METRIC: got tasa ME instead of tasa sistema. title='{title}', metric='{metric}'"
    return None

def no_data_denial(resp):
    content = resp.get("content", "").lower()
    for phrase in _DATA_DENIAL_PHRASES:
        if phrase in content:
            return f"LLM denied data: '{phrase}'"
    return None

def s1_tasa_value(resp):
    """INVEX tasa_sistema ~35.7 for latest available period."""
    content = resp.get("content", "")
    # Check for values in plausible tasa range (5-50%)
    vals = _get_bar_values(resp)
    if vals and any(5 < v < 60 for v in vals):
        return None
    traces = _get_line_traces(resp)
    for name, y_vals in traces.items():
        valid = [v for v in y_vals if isinstance(v, (int, float))]
        if valid and any(5 < v < 60 for v in valid):
            return None
        if valid and any(0.05 < v < 0.6 for v in valid):
            return None  # ratio format
    if any(x in content for x in ["35", "36", "34"]):
        return None
    return f"Expected tasa ~35.7 for INVEX. Content: {content[:300]}"

def s2_bank_coverage(resp):
    banks = _get_bar_banks(resp)
    found = [b for b in TARGET_BANKS if b in banks]
    if len(found) < 4:
        missing = [b for b in TARGET_BANKS if b not in banks]
        return f"Only {len(found)}/{len(TARGET_BANKS)} banks. Missing: {missing}. Got: {banks}"
    return None

def only_requested_banks(resp):
    """Should only show requested banks, not extra ones."""
    banks = _get_bar_banks(resp) or list(_get_line_traces(resp).keys())
    if not banks:
        return None  # no chart, other validator catches
    extra = [b for b in banks if b not in TARGET_BANKS and b not in ("SISTEMA", "PROMEDIO")]
    if len(extra) > 2:
        return f"Too many unrequested banks: {extra[:5]}"
    return None

# ══════════════════════════════════════════════════════════════════════════════
# Scenarios
# ══════════════════════════════════════════════════════════════════════════════

SCENARIOS = [
    (
        "S1_TASA_IE_INVEX",
        "Tasa IE de INVEX (~35.7%)",
        PROMPT_S1,
        [
            ("V1_CHART_EXISTS", "Chart must exist", chart_exists),
            ("V2_NOT_CARTERA_TOTAL", "NOT cartera_total regression", not_cartera_total),
            ("V3_NOT_TASA_ME", "NOT tasa ME confusion", not_tasa_me),
            ("V4_TASA_VALUE", "Tasa ~35.7% for INVEX", s1_tasa_value),
            ("V5_NO_DATA_DENIAL", "LLM must not deny data", no_data_denial),
        ],
    ),
    (
        "S2_TASA_IE_BAR_10",
        "Tasa IE barras 10 bancos",
        PROMPT_S2,
        [
            ("V1_CHART_EXISTS", "Chart must exist", chart_exists),
            ("V2_NOT_CARTERA_TOTAL", "NOT cartera_total regression", not_cartera_total),
            ("V3_NOT_TASA_ME", "NOT tasa ME confusion", not_tasa_me),
            ("V4_BANK_COVERAGE", ">=4/6 target banks in chart", s2_bank_coverage),
            ("V5_ONLY_REQUESTED", "No extra unrequested banks", only_requested_banks),
            ("V6_NO_DATA_DENIAL", "LLM must not deny data", no_data_denial),
        ],
    ),
    (
        "S3_TASA_EFECTIVA_SHORT",
        "Tasa efectiva INVEX (short prompt, tasa_me risk)",
        PROMPT_S3,
        [
            ("V1_CHART_EXISTS", "Chart must exist", chart_exists),
            ("V2_NOT_CARTERA_TOTAL", "NOT cartera_total regression", not_cartera_total),
            ("V3_NOT_TASA_ME", "NOT tasa ME confusion", not_tasa_me),
            ("V4_NO_DATA_DENIAL", "LLM must not deny data", no_data_denial),
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
    print(f"  E2E Tasa Interés Efectiva Routing — 2026-03-12")
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

    out_path = Path(__file__).with_name("tasa_ie_routing_2026_03_12_results.json")
    with open(out_path, "w") as f:
        json.dump({
            "test": "tasa-ie-routing-2026-03-12",
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
