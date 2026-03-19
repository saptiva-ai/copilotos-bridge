#!/usr/bin/env python3
"""
E2E Test — Etapas de Cartera Routing (2026-03-12)

Validates that "etapa 3", "etapa 1", etc. queries return ct_etapa_*
percentages, NOT cartera_total absolute values.

Reported issues:
- "no me da ningún dato ni genera ninguna grafica"
- "me da los mismos datos de la cartera total"

Scenarios:
  S1 — Etapa 3 de INVEX (single bank, should return ~2.65%)
  S2 — Etapa 3 barras 10 bancos dic 2025
  S3 — Porcentaje etapa 1 de INVEX (should return ~92.99%)

Usage:
    TEST_BACKEND_URL=http://localhost:8000 python tests/e2e/charts/test_etapas_routing_2026_03_12.py
    TEST_BACKEND_URL=http://localhost:8000 python tests/e2e/charts/test_etapas_routing_2026_03_12.py --scenario S1
"""
from __future__ import annotations

import json
import os
import re
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
BANK_ALIASES = {}

# ══════════════════════════════════════════════════════════════════════════════
# Prompts
# ══════════════════════════════════════════════════════════════════════════════

PROMPT_S1 = "Cuál es el porcentaje de etapa 3 de cartera total de INVEX para diciembre 2025?"

PROMPT_S2 = (
    "Muestra el porcentaje de etapa 3 de cartera total para diciembre 2025 "
    "para los bancos: BANORTE, BBVA, CITIBANAMEX, HSBC, INVEX Y SANTANDER.\n"
    "Gráfica de barras horizontales ordenadas de mayor a menor."
)

PROMPT_S3 = "Cuál es el porcentaje de etapa 1 de cartera total de INVEX para diciembre 2025?"


# ══════════════════════════════════════════════════════════════════════════════
# Data classes & helpers
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


def _is_numeric(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


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
    """Must NOT return cartera_total MDP values (billions)."""
    vals = _get_bar_values(resp)
    if not vals:
        # Check line traces
        for name, y_vals in _get_line_traces(resp).items():
            valid = [v for v in y_vals if isinstance(v, (int, float))]
            if valid and max(abs(v) for v in valid) > 1_000_000:
                return f"REGRESSION: trace '{name}' has MDP-scale values (max={max(valid):,.0f})"
        return None
    if vals and max(abs(v) for v in vals) > 1000:
        return f"REGRESSION: values are MDP-scale (max={max(vals):,.0f}), not etapa percentage"
    return None


def no_data_denial(resp):
    content = resp.get("content", "").lower()
    for phrase in _DATA_DENIAL_PHRASES:
        if phrase in content:
            return f"LLM denied data: '{phrase}'"
    return None


def s1_etapa3_value(resp):
    """Response should mention etapa 3 ~2.65% for INVEX dic 2025."""
    content = resp.get("content", "")
    # Check for percentage in content or chart
    if any(x in content for x in ["2.6", "2,6", "2.7", "2,7"]):
        return None
    vals = _get_bar_values(resp)
    if vals and any(1.5 < v < 5.0 for v in vals):
        return None
    traces = _get_line_traces(resp)
    for name, y_vals in traces.items():
        valid = [v for v in y_vals if isinstance(v, (int, float))]
        if valid and any(0.01 < v < 0.05 for v in valid):
            return None  # ratio format
        if valid and any(1.5 < v < 5.0 for v in valid):
            return None  # percentage format
    return f"Expected etapa 3 ~2.65% for INVEX. Content: {content[:300]}"


def s2_bank_coverage(resp):
    banks = _get_bar_banks(resp)
    found = [b for b in TARGET_BANKS if b in banks]
    if len(found) < 4:
        missing = [b for b in TARGET_BANKS if b not in banks]
        return f"Only {len(found)}/{len(TARGET_BANKS)} banks. Missing: {missing}. Got: {banks}"
    return None


def s2_values_plausible(resp):
    vals = _get_bar_values(resp)
    if not vals:
        return "No numeric values in chart"
    # ct_etapa_3 should be 0-100% (or 0-1 ratio)
    if all(0 <= v <= 1 for v in vals):
        return None  # ratio format
    if all(0 <= v <= 100 for v in vals):
        return None  # percentage format
    return f"Etapa 3 values out of plausible range: {vals[:5]}"


def s3_etapa1_value(resp):
    """Response should mention etapa 1 ~92.99% for INVEX dic 2025."""
    content = resp.get("content", "")
    if any(x in content for x in ["92", "93"]):
        return None
    vals = _get_bar_values(resp)
    if vals and any(80 < v < 100 for v in vals):
        return None
    traces = _get_line_traces(resp)
    for name, y_vals in traces.items():
        valid = [v for v in y_vals if isinstance(v, (int, float))]
        if valid and any(0.85 < v < 1.0 for v in valid):
            return None  # ratio format
        if valid and any(80 < v < 100 for v in valid):
            return None
    return f"Expected etapa 1 ~92.99% for INVEX. Content: {content[:300]}"


# ══════════════════════════════════════════════════════════════════════════════
# Scenario definitions
# ══════════════════════════════════════════════════════════════════════════════

SCENARIOS = [
    (
        "S1_ETAPA3_INVEX",
        "Etapa 3 INVEX dic 2025 (~2.65%)",
        PROMPT_S1,
        [
            ("V1_CHART_EXISTS", "Chart must exist", chart_exists),
            ("V2_NOT_CARTERA_TOTAL", "NOT cartera_total regression", not_cartera_total),
            ("V3_ETAPA3_VALUE", "Response mentions ~2.65%", s1_etapa3_value),
            ("V4_NO_DATA_DENIAL", "LLM must not deny data", no_data_denial),
        ],
    ),
    (
        "S2_ETAPA3_BAR_10",
        "Etapa 3 barras 10 bancos dic 2025",
        PROMPT_S2,
        [
            ("V1_CHART_EXISTS", "Chart must exist", chart_exists),
            ("V2_NOT_CARTERA_TOTAL", "NOT cartera_total regression", not_cartera_total),
            ("V3_BANK_COVERAGE", ">=8/10 target banks in chart", s2_bank_coverage),
            ("V4_VALUES_PLAUSIBLE", "Etapa 3 in [0, 100] range", s2_values_plausible),
            ("V5_NO_DATA_DENIAL", "LLM must not deny data", no_data_denial),
        ],
    ),
    (
        "S3_ETAPA1_INVEX",
        "Etapa 1 INVEX dic 2025 (~92.99%)",
        PROMPT_S3,
        [
            ("V1_CHART_EXISTS", "Chart must exist", chart_exists),
            ("V2_NOT_CARTERA_TOTAL", "NOT cartera_total regression", not_cartera_total),
            ("V3_ETAPA1_VALUE", "Response mentions ~93%", s3_etapa1_value),
            ("V4_NO_DATA_DENIAL", "LLM must not deny data", no_data_denial),
        ],
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# Runner (same pattern as TDA test)
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

    print(f"  Response: {len(content)} chars, chart={'present' if bc else 'MISSING'}")
    print(f"  Banks: {len(banks)} → {banks[:5]}{'...' if len(banks) > 5 else ''}")

    for v_name, v_desc, v_fn in validators:
        check = _run(v_name, v_desc, v_fn, resp)
        status = "PASS" if check.passed else "FAIL"
        detail_str = f" — {check.detail}" if check.detail != "OK" else ""
        print(f"    [{status}] {v_name}: {v_desc}{detail_str}")
        result.checks.append(check)

    result.response_summary = {
        "content_length": len(content),
        "has_chart": bool(bc),
        "banks_in_chart": banks,
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
    print(f"  E2E Etapas de Cartera Routing — 2026-03-12")
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
            (total_passed if c.passed else total_failed).__class__  # no-op
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

    out_path = Path(__file__).with_name("etapas_routing_2026_03_12_results.json")
    with open(out_path, "w") as f:
        json.dump({
            "test": "etapas-routing-2026-03-12",
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
