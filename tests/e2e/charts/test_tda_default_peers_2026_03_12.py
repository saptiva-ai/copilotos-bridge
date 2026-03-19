#!/usr/bin/env python3
"""
E2E Test — TDA Default Peer Group (2026-03-12)

Validates that "INVEX vs promedio TDA" queries WITHOUT listing banks
correctly fall back to PEER_GROUP_DEFAULT (13 bancos banca mediana).

Root cause: PeerAverageUseCase rejected requests with empty peer_banks.
When the LLM/parser only detected the target bank (INVEX), the handler
passed an empty peer list, causing an error instead of using the default
13-bank peer group.

Scenarios:
  S1 — "TDA de INVEX vs promedio" (no banks listed, should use default peers)
  S2 — "Compara TDA de INVEX contra el promedio" (variant phrasing)
  S3 — "TDA INVEX vs promedio" with explicit banks (control, must still work)

Usage:
    python tests/e2e/charts/test_tda_default_peers_2026_03_12.py
    TEST_BACKEND_URL=http://localhost:18000 python tests/e2e/charts/test_tda_default_peers_2026_03_12.py
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

# The 13 banks in PEER_GROUP_DEFAULT (from BankClassification)
DEFAULT_PEER_GROUP = [
    "MONEX", "INVEX", "BANCREA", "SABADELL", "MIFEL", "MULTIVA",
    "AFIRME", "BANSI", "VE POR MAS", "BANCO BASE",
    "CIBANCO", "BANREGIO", "BAJIO",
]

# ══════════════════════════════════════════════════════════════════════════════
# Prompts
# ══════════════════════════════════════════════════════════════════════════════

# S1: NO banks listed — must trigger default peer group
PROMPT_S1_NO_BANKS = (
    "Crea una gráfica de línea donde se compare la TDA de cartera total "
    "de INVEX contra el promedio de los bancos del grupo par, "
    "de enero 2021 hasta el dato más reciente."
)

# S2: Variant phrasing, still no explicit bank list
PROMPT_S2_VS_PROMEDIO = (
    "Muestra la evolución de la TDA de INVEX vs promedio del grupo "
    "desde enero 2021."
)

# S3: Control — explicit bank list (should always work)
PROMPT_S3_EXPLICIT = (
    "Crea una gráfica donde se compare la TDA de cartera total de INVEX "
    "contra el promedio de los bancos:\n"
    "MONEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, "
    "VE POR MAS Y BANCO BASE.\n"
    "De enero 2021 hasta el dato más reciente que tengas."
)

# S4: Full 12-bank peer list — must NOT truncate to 10
PROMPT_S4_ALL_12_PEERS = (
    "Crea una gráfica donde se compare la TDA de cartera total de INVEX "
    "contra el promedio de los bancos: MONEX, BANCREA, SABADELL, MIFEL, "
    "MULTIVA, AFIRME, BANSI, VE POR MAS, BANCO BASE, CIBANCO, BANREGIO "
    "Y BAJIO. De enero 2021 hasta el dato más reciente que tengas."
)

_DATA_DENIAL_PHRASES = [
    "no se dispone de datos", "no tengo datos", "no hay datos disponibles",
    "no se encontraron datos", "no encontré datos", "datos no disponibles",
    "debes especificar al menos un banco par",
]


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

BANK_ALIASES = {"BANCA MIFEL": "MIFEL"}


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


def _get_line_traces(resp: dict) -> dict[str, list]:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    return {
        _normalize_bank(t.get("name", "")): t.get("y", [])
        for t in traces if t.get("name")
    }


def _get_chart_title(resp: dict) -> str:
    bc = resp.get("bank_chart", {})
    layout = bc.get("plotly_config", {}).get("layout", {})
    title = layout.get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")
    return str(title).lower()


def _get_peer_banks(resp: dict) -> list[str]:
    """Extract peer_banks from response metadata."""
    bc = resp.get("bank_chart", {})
    return bc.get("peer_banks", [])


def _get_x_dates(resp: dict) -> list[str]:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return []
    return [str(x) for x in traces[0].get("x", []) if x]


# ══════════════════════════════════════════════════════════════════════════════
# Shared validators for "vs promedio" line charts
# ══════════════════════════════════════════════════════════════════════════════

def check_chart_exists(resp: dict) -> Optional[str]:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No chart traces — chart missing or error response"
    return None


def check_two_series(resp: dict) -> Optional[str]:
    """Must have INVEX + PROMEDIO series (peer average mode)."""
    traces = _get_line_traces(resp)
    names = list(traces.keys())
    has_invex = any("INVEX" in n for n in names)
    has_avg = any(n in ("PROMEDIO", "PROMEDIO PEERS", "AVERAGE") for n in names)
    if not has_invex:
        return f"INVEX series missing. Got: {names}"
    if not has_avg:
        return f"PROMEDIO series missing. Got: {names}"
    if len(names) > 5:
        return (
            f"TOO_MANY_SERIES: got {len(names)} — likely routed to "
            f"multi-bank evolution instead of peer_average. Series: {names[:10]}"
        )
    return None


def check_not_cartera_total(resp: dict) -> Optional[str]:
    """Values must be TDA percentage [0, 30], not cartera_total MDP."""
    traces = _get_line_traces(resp)
    for name, y_vals in traces.items():
        valid = [v for v in y_vals if isinstance(v, (int, float))]
        if valid and max(abs(v) for v in valid) > 100:
            return (
                f"REGRESSION: trace '{name}' max={max(valid):,.0f} — "
                f"values are MDP-scale, not TDA percentage"
            )
    return None


def check_data_points(resp: dict) -> Optional[str]:
    """Each series should have >= 40 monthly data points (~3+ years)."""
    traces = _get_line_traces(resp)
    for name, y_vals in traces.items():
        valid = [v for v in y_vals if v is not None]
        if len(valid) < 40:
            return f"{name}: only {len(valid)} data points (expected >=40)"
    return None


def check_period_coverage(resp: dict) -> Optional[str]:
    dates = _get_x_dates(resp)
    if not dates:
        return "No dates in x-axis"
    has_2021 = any("2021" in d for d in dates)
    has_2025 = any("2025" in d for d in dates)
    if not has_2021:
        return f"Missing 2021 data. First date: {dates[0]}"
    if not has_2025:
        return f"Missing 2025 data. Last date: {dates[-1]}"
    return None


def check_no_data_denial(resp: dict) -> Optional[str]:
    content = resp.get("content", "").lower()
    for phrase in _DATA_DENIAL_PHRASES:
        if phrase in content:
            return f"DATA_DENIAL: LLM says '{phrase}'"
    return None


def check_no_error_response(resp: dict) -> Optional[str]:
    """Response must not be an error type."""
    bc = resp.get("bank_chart", {})
    if bc.get("type") == "error":
        msg = bc.get("message", "unknown")
        return f"ERROR_RESPONSE: bank_chart.type=error — {msg}"
    return None


def check_all_12_peers(resp: dict) -> Optional[str]:
    """All 12 explicitly listed peers must appear in peer_banks metadata."""
    expected = {
        "MONEX", "BANCREA", "SABADELL", "MIFEL", "MULTIVA",
        "AFIRME", "BANSI", "VE POR MAS", "BANCO BASE",
        "CIBANCO", "BANREGIO", "BAJIO",
    }
    bc = resp.get("bank_chart", {})
    peer_banks = {b.upper() for b in bc.get("peer_banks", [])}
    # Also check chart title for peer count
    title = _get_chart_title(resp)
    missing = expected - peer_banks
    if missing:
        return (
            f"TRUNCATED: missing {len(missing)} peers: {sorted(missing)}. "
            f"Got {len(peer_banks)} peers: {sorted(peer_banks)}. "
            f"Title: {title}"
        )
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Scenario definitions
# ══════════════════════════════════════════════════════════════════════════════

SCENARIOS = [
    (
        "S1_DEFAULT_PEERS_NO_BANKS",
        "TDA INVEX vs promedio — NO banks listed (default peer group)",
        PROMPT_S1_NO_BANKS,
        [
            ("V1_NO_ERROR", "Response must not be error", check_no_error_response),
            ("V2_CHART_EXISTS", "Chart must exist", check_chart_exists),
            ("V3_TWO_SERIES", "INVEX + PROMEDIO series", check_two_series),
            ("V4_NOT_CARTERA_TOTAL", "TDA %, not MDP values", check_not_cartera_total),
            ("V5_DATA_POINTS", ">=40 monthly points", check_data_points),
            ("V6_PERIOD_COVERAGE", "2021 through 2025", check_period_coverage),
            ("V7_NO_DATA_DENIAL", "LLM must not deny data", check_no_data_denial),
        ],
    ),
    (
        "S2_DEFAULT_PEERS_VARIANT",
        "TDA INVEX vs promedio — variant phrasing (default peer group)",
        PROMPT_S2_VS_PROMEDIO,
        [
            ("V1_NO_ERROR", "Response must not be error", check_no_error_response),
            ("V2_CHART_EXISTS", "Chart must exist", check_chart_exists),
            ("V3_TWO_SERIES", "INVEX + PROMEDIO series", check_two_series),
            ("V4_NOT_CARTERA_TOTAL", "TDA %, not MDP values", check_not_cartera_total),
            ("V5_NO_DATA_DENIAL", "LLM must not deny data", check_no_data_denial),
        ],
    ),
    (
        "S3_EXPLICIT_BANKS_CONTROL",
        "TDA INVEX vs promedio — explicit banks (control group)",
        PROMPT_S3_EXPLICIT,
        [
            ("V1_NO_ERROR", "Response must not be error", check_no_error_response),
            ("V2_CHART_EXISTS", "Chart must exist", check_chart_exists),
            ("V3_TWO_SERIES", "INVEX + PROMEDIO series", check_two_series),
            ("V4_NOT_CARTERA_TOTAL", "TDA %, not MDP values", check_not_cartera_total),
            ("V5_DATA_POINTS", ">=40 monthly points", check_data_points),
            ("V6_PERIOD_COVERAGE", "2021 through 2025", check_period_coverage),
            ("V7_NO_DATA_DENIAL", "LLM must not deny data", check_no_data_denial),
        ],
    ),
    (
        "S4_ALL_12_PEERS_NO_TRUNCATION",
        "TDA INVEX vs promedio — all 12 peers must NOT truncate to 10",
        PROMPT_S4_ALL_12_PEERS,
        [
            ("V1_NO_ERROR", "Response must not be error", check_no_error_response),
            ("V2_CHART_EXISTS", "Chart must exist", check_chart_exists),
            ("V3_TWO_SERIES", "INVEX + PROMEDIO series", check_two_series),
            ("V4_NOT_CARTERA_TOTAL", "TDA %, not MDP values", check_not_cartera_total),
            ("V5_ALL_12_PEERS", "All 12 peers in calculation", check_all_12_peers),
            ("V6_DATA_POINTS", ">=40 monthly points", check_data_points),
            ("V7_PERIOD_COVERAGE", "2021 through 2025", check_period_coverage),
            ("V8_NO_DATA_DENIAL", "LLM must not deny data", check_no_data_denial),
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
    traces = _get_line_traces(resp)

    print(f"  Response: {len(content)} chars, chart={'present' if bc else 'MISSING'}")
    print(f"  Traces: {list(traces.keys())}")
    if bc.get("peer_banks"):
        print(f"  Peer banks: {bc['peer_banks']}")

    for v_name, v_desc, v_fn in validators:
        check = _run(v_name, v_desc, v_fn, resp)
        status = "PASS" if check.passed else "FAIL"
        detail_str = f" — {check.detail}" if check.detail != "OK" else ""
        print(f"    [{status}] {v_name}: {v_desc}{detail_str}")
        result.checks.append(check)

    result.response_summary = {
        "content_length": len(content),
        "has_chart": bool(bc),
        "traces": list(traces.keys()),
        "peer_banks": bc.get("peer_banks", []),
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
    print(f"  E2E TDA Default Peer Group — 2026-03-12")
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
        "test": "tda-default-peers-2026-03-12",
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

    out_path = Path(__file__).with_name("tda_default_peers_2026_03_12_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved: {out_path}")

    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
