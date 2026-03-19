#!/usr/bin/env python3
"""
E2E Test — TDA Routing + Data Patch Validation (2026-03-12)

Validates two fixes:
1. DATA: TDA.xlsx patch loaded 26 rows → bank_fact_kpis_mensual (10/10 target banks)
2. ROUTING: semantic scorer exemplars added to evolucion_banco for TDA queries

Scenarios:
  S1 — TDA barras horizontales, 10 bancos, Dic 2025 (exact FDBK-0205 prompt)
  S2 — TDA evolución INVEX vs promedio (exact FDBK-0206 prompt)
  S3 — TDA snapshot single bank (INVEX, should return ~2.43%)

Usage:
    TEST_BACKEND_URL=http://localhost:18000 python tests/e2e/charts/test_tda_routing_2026_03_12.py
    TEST_BACKEND_URL=http://localhost:18000 python tests/e2e/charts/test_tda_routing_2026_03_12.py --scenario S1
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
    "MONEX", "INVEX", "BANCREA", "SABADELL", "MIFEL",
    "MULTIVA", "AFIRME", "BANSI", "VE POR MAS", "BANCO BASE",
]
BANK_ALIASES = {"BANCA MIFEL": "MIFEL"}

# ══════════════════════════════════════════════════════════════════════════════
# Prompts
# ══════════════════════════════════════════════════════════════════════════════

PROMPT_S1_TDA_BAR = (
    "Muestra la TDA de cartera total para diciembre 2025 para los bancos:\n"
    "MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, "
    "VE POR MAS Y BANCO BASE.\n"
    "Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca "
    "a INVEX de color rojo.\n"
    "Incluye una tabla con: Banco | TDA Cartera Total"
)

PROMPT_S2_TDA_EVOL = (
    "Crea una gráfica donde se compare la TDA de cartera total de INVEX "
    "contra el promedio de los bancos:\n"
    "MONEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, "
    "VE POR MAS Y BANCO BASE.\n"
    "De enero 2021 hasta el dato más reciente que tengas."
)

PROMPT_S3_TDA_INVEX = (
    "Cuál es la TDA de cartera total de INVEX para diciembre 2025?"
)


# ══════════════════════════════════════════════════════════════════════════════
# Data classes
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


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _run(name: str, desc: str, fn: Callable, *args) -> CheckResult:
    try:
        error = fn(*args)
        if error is None:
            return CheckResult(name, desc, True, "OK")
        if error.startswith("SOFT_PASS:"):
            return CheckResult(name, desc, True, error)
        return CheckResult(name, desc, False, error)
    except Exception as e:
        return CheckResult(name, desc, False, f"Exception: {e}")


def _normalize_bank(name: str) -> str:
    n = name.strip().upper()
    return BANK_ALIASES.get(n, n)


def _is_numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def _get_bar_banks(resp: dict) -> list[str]:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return []
    y_vals = traces[0].get("y", [])
    banks = [_normalize_bank(str(b)) for b in y_vals if not _is_numeric(str(b))]
    if banks:
        return banks
    x_vals = traces[0].get("x", [])
    banks = [_normalize_bank(str(b)) for b in x_vals if not _is_numeric(str(b))]
    return banks


def _get_bar_values(resp: dict) -> list[float]:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return []
    x_vals = [v for v in traces[0].get("x", []) if isinstance(v, (int, float))]
    if x_vals:
        return x_vals
    return [v for v in traces[0].get("y", []) if isinstance(v, (int, float))]


def _get_line_traces(resp: dict) -> dict[str, list]:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    return {_normalize_bank(t.get("name", "")): t.get("y", []) for t in traces if t.get("name")}


def _get_chart_title(resp: dict) -> str:
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
# S1: TDA barras horizontales, 10 bancos, Dic 2025
# ══════════════════════════════════════════════════════════════════════════════

def s1_chart_exists(resp: dict) -> Optional[str]:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No chart traces"
    return None


def s1_not_cartera_total(resp: dict) -> Optional[str]:
    """Core regression: must NOT return cartera_total MDP values."""
    vals = _get_bar_values(resp)
    if vals and max(abs(v) for v in vals) > 1000:
        return (
            f"REGRESSION: values are MDP-scale (max={max(vals):,.0f}), "
            "not TDA percentage — routed to cartera_total instead of tda"
        )
    title = _get_chart_title(resp)
    if "cartera total" in title and "tda" not in title:
        return f"REGRESSION: title='{title}' is cartera_total, not TDA"
    return None


def s1_bank_coverage(resp: dict) -> Optional[str]:
    banks = _get_bar_banks(resp)
    found = [b for b in TARGET_BANKS if b in banks]
    if len(found) < 8:
        missing = [b for b in TARGET_BANKS if b not in banks]
        return f"Only {len(found)}/10 banks. Missing: {missing}"
    return None


def s1_values_plausible(resp: dict) -> Optional[str]:
    vals = _get_bar_values(resp)
    if not vals:
        return "No numeric values in chart"
    out = [v for v in vals if v < 0 or v > 30]
    if out:
        return f"TDA values out of [0, 30] range: {out[:5]}"
    return None


def s1_no_data_denial(resp: dict) -> Optional[str]:
    content = resp.get("content", "").lower()
    for phrase in _DATA_DENIAL_PHRASES:
        if phrase in content:
            return f"LLM denied data: '{phrase}'"
    return None


def s1_title_mentions_tda(resp: dict) -> Optional[str]:
    title = _get_chart_title(resp)
    if any(m in title for m in ["tda", "deterioro", "alejamiento"]):
        return None
    return f"SOFT_PASS: title='{title}' does not mention TDA explicitly"


# ══════════════════════════════════════════════════════════════════════════════
# S2: TDA evolución, INVEX vs promedio
# ══════════════════════════════════════════════════════════════════════════════

def s2_chart_exists(resp: dict) -> Optional[str]:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No chart traces"
    return None


def s2_two_series(resp: dict) -> Optional[str]:
    traces = _get_line_traces(resp)
    names = list(traces.keys())
    has_invex = any("INVEX" in n for n in names)
    has_avg = any(n in names for n in ["PROMEDIO", "PROMEDIO PEERS", "AVERAGE"])
    if not has_invex:
        return f"INVEX series missing. Got: {names}"
    if not has_avg:
        return f"PROMEDIO series missing. Got: {names}"
    return None


def s2_not_cartera_total(resp: dict) -> Optional[str]:
    traces = _get_line_traces(resp)
    for name, y_vals in traces.items():
        valid = [v for v in y_vals if isinstance(v, (int, float))]
        if valid and max(abs(v) for v in valid) > 1000:
            return f"REGRESSION: trace '{name}' has MDP-scale values (max={max(valid):,.0f})"
    return None


def s2_no_data_denial(resp: dict) -> Optional[str]:
    content = resp.get("content", "").lower()
    for phrase in _DATA_DENIAL_PHRASES:
        if phrase in content:
            return f"LLM denied data: '{phrase}'"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# S3: TDA single bank INVEX (sanity check)
# ══════════════════════════════════════════════════════════════════════════════

def s3_mentions_tda_value(resp: dict) -> Optional[str]:
    """Response should mention TDA ~2.43% for INVEX dic 2025."""
    content = resp.get("content", "")
    if "2.4" in content or "2,4" in content:
        return None
    return f"Expected TDA ~2.43% for INVEX in response. Content: {content[:300]}"


def s3_not_cartera_total(resp: dict) -> Optional[str]:
    content = resp.get("content", "").lower()
    # Check for MDP amounts (billions)
    import re
    mdp_pattern = re.findall(r'[\d,]+\s*(?:mdp|millones|mil millones)', content)
    if mdp_pattern:
        return f"REGRESSION: response contains MDP amounts: {mdp_pattern[:3]}"
    return None


def s3_no_data_denial(resp: dict) -> Optional[str]:
    content = resp.get("content", "").lower()
    for phrase in _DATA_DENIAL_PHRASES:
        if phrase in content:
            return f"LLM denied data: '{phrase}'"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Scenario definitions
# ══════════════════════════════════════════════════════════════════════════════

SCENARIOS = [
    (
        "S1_TDA_BAR_DIC2025",
        "TDA barras 10 bancos dic 2025 (data patch + routing fix)",
        PROMPT_S1_TDA_BAR,
        [
            ("V1_CHART_EXISTS", "Chart must exist", s1_chart_exists),
            ("V2_NOT_CARTERA_TOTAL", "NOT cartera_total regression", s1_not_cartera_total),
            ("V3_BANK_COVERAGE", ">=8/10 target banks in chart", s1_bank_coverage),
            ("V4_VALUES_PLAUSIBLE", "TDA in [0, 30] range", s1_values_plausible),
            ("V5_NO_DATA_DENIAL", "LLM must not deny data", s1_no_data_denial),
            ("V6_TITLE_TDA", "Title mentions TDA", s1_title_mentions_tda),
        ],
    ),
    (
        "S2_TDA_EVOL",
        "TDA evolución INVEX vs promedio (routing fix)",
        PROMPT_S2_TDA_EVOL,
        [
            ("V1_CHART_EXISTS", "Chart must exist", s2_chart_exists),
            ("V2_TWO_SERIES", "INVEX + PROMEDIO series", s2_two_series),
            ("V3_NOT_CARTERA_TOTAL", "NOT cartera_total regression", s2_not_cartera_total),
            ("V4_NO_DATA_DENIAL", "LLM must not deny data", s2_no_data_denial),
        ],
    ),
    (
        "S3_TDA_SINGLE_INVEX",
        "TDA INVEX dic 2025 sanity check (~2.43%)",
        PROMPT_S3_TDA_INVEX,
        [
            ("V1_TDA_VALUE", "Response mentions ~2.43%", s3_mentions_tda_value),
            ("V2_NOT_CARTERA_TOTAL", "NOT cartera_total regression", s3_not_cartera_total),
            ("V3_NO_DATA_DENIAL", "LLM must not deny data", s3_no_data_denial),
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
    print(f"  E2E TDA Routing + Data Patch — 2026-03-12")
    print(f"  Backend: {BACKEND_URL}")
    print(f"  Scenarios: {len(scenarios)}")
    print(f"{'=' * 70}")

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("\nFATAL: Authentication failed")
        sys.exit(2)
    print(f"\nAuthenticated against {BACKEND_URL}")

    all_results = []
    total_passed = 0
    total_failed = 0

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
        status = "PASS" if f == 0 else "FAIL"
        print(f"  [{status}] {r.scenario_id} ({p}/{p + f})")

    if total_failed > 0:
        print(f"\n  Failed checks:")
        for r in all_results:
            for c in r.checks:
                if not c.passed:
                    print(f"    {r.scenario_id}/{c.name}: {c.detail}")

    output = {
        "test": "tda-routing-2026-03-12",
        "backend_url": BACKEND_URL,
        "total_checks": total,
        "passed": total_passed,
        "failed": total_failed,
        "scenarios": [
            {
                "scenario_id": r.scenario_id,
                "prompt": r.prompt,
                "checks": [
                    {"name": c.name, "description": c.description,
                     "passed": c.passed, "detail": c.detail}
                    for c in r.checks
                ],
                "response_summary": r.response_summary,
            }
            for r in all_results
        ],
    }

    out_path = Path(__file__).with_name("tda_routing_2026_03_12_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved: {out_path}")

    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
