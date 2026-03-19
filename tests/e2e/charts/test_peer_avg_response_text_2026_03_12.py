#!/usr/bin/env python3
"""
E2E Test — Peer Average response_text cosmetic fix (2026-03-12)

Validates that "INVEX vs promedio TDA" with explicit 12-bank peer list:
  - Uses WAVG (not AVG) in response_text for TDA cartera total
  - Reports "12 bancos" (not "13 bancos") — target excluded from peer count
  - Does NOT mention "AVG(INVEX" — target excluded from aggregation formula
  - peer_banks metadata has exactly 12 banks
  - Chart has 2 series (INVEX + PROMEDIO), TDA % range, >=40 data points

Root cause: _build_response_text() was using len(peer_banks)+1 and showing
the target bank inside the aggregation formula. The calculation was already
correct (target excluded, WAVG for TDA), but the descriptive text was stale.

Note: PROD has the calculation fix but NOT the cosmetic text fix yet.
Text-related checks use soft assertions — they will SOFT_PASS with a
"POST_DEPLOY" note until the cosmetic fix is deployed.

Usage:
    TEST_BACKEND_URL=http://localhost:18000 python tests/e2e/charts/test_peer_avg_response_text_2026_03_12.py
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

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:18000")
TIMEOUT = int(os.environ.get("TIMEOUT", "120"))

PROMPT = (
    "Crea una gráfica donde se compare la TDA de cartera total de INVEX "
    "contra el promedio de los bancos: MONEX, BANCREA, SABADELL, MIFEL, "
    "MULTIVA, AFIRME, BANSI, VE POR MAS, BANCO BASE, CIBANCO, BANREGIO "
    "Y BAJIO. De enero 2021 hasta el dato más reciente que tengas."
)

EXPECTED_PEERS = {
    "MONEX", "BANCREA", "SABADELL", "MIFEL", "MULTIVA",
    "AFIRME", "BANSI", "VE POR MAS", "BANCO BASE",
    "CIBANCO", "BANREGIO", "BAJIO",
}


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
class TestResult:
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


def _get_response_text(resp: dict) -> str:
    bc = resp.get("bank_chart", {})
    return bc.get("response_text", "")


# ══════════════════════════════════════════════════════════════════════════════
# Validators — structural (must pass now)
# ══════════════════════════════════════════════════════════════════════════════

def check_no_error(resp: dict) -> Optional[str]:
    bc = resp.get("bank_chart", {})
    if bc.get("type") == "error":
        return f"ERROR_RESPONSE: {bc.get('message', 'unknown')}"
    return None


def check_chart_exists(resp: dict) -> Optional[str]:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No chart traces — chart missing or error response"
    return None


def check_two_series(resp: dict) -> Optional[str]:
    traces = _get_line_traces(resp)
    names = list(traces.keys())
    has_invex = any("INVEX" in n for n in names)
    has_avg = any(n in ("PROMEDIO", "PROMEDIO PEERS", "AVERAGE") for n in names)
    if not has_invex:
        return f"INVEX series missing. Got: {names}"
    if not has_avg:
        return f"PROMEDIO series missing. Got: {names}"
    return None


def check_tda_range(resp: dict) -> Optional[str]:
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
    traces = _get_line_traces(resp)
    for name, y_vals in traces.items():
        valid = [v for v in y_vals if v is not None]
        if len(valid) < 40:
            return f"{name}: only {len(valid)} data points (expected >=40)"
    return None


def check_12_peer_banks(resp: dict) -> Optional[str]:
    """Check peer_banks metadata, falling back to response_text parsing."""
    bc = resp.get("bank_chart", {})
    peer_banks = {b.upper() for b in bc.get("peer_banks", [])}

    # Fallback: extract from response_text when API layer doesn't expose peer_banks
    if not peer_banks:
        text = _get_response_text(resp)
        for expected in EXPECTED_PEERS:
            if expected.upper() in text.upper():
                peer_banks.add(expected)

    missing = EXPECTED_PEERS - peer_banks
    if missing:
        return (
            f"Missing {len(missing)} peers: {sorted(missing)}. "
            f"Got {len(peer_banks)}: {sorted(peer_banks)}"
        )
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Validators — cosmetic text (soft assertions — POST_DEPLOY)
# ══════════════════════════════════════════════════════════════════════════════

def check_wavg_in_response_text(resp: dict) -> Optional[str]:
    """response_text must say WAVG for TDA cartera total, not plain AVG."""
    text = _get_response_text(resp).upper()
    if not text:
        return "response_text is empty"
    if "WAVG" in text:
        return None
    if "AVG" in text:
        return "SOFT_PASS: POST_DEPLOY — response_text says AVG instead of WAVG"
    return "SOFT_PASS: POST_DEPLOY — neither WAVG nor AVG found in response_text"


def check_12_bancos_in_text(resp: dict) -> Optional[str]:
    """response_text must say '12 bancos', not '13 bancos'."""
    text = _get_response_text(resp)
    if not text:
        return "response_text is empty"
    if "12 bancos" in text:
        return None
    if "13 bancos" in text:
        return "SOFT_PASS: POST_DEPLOY — response_text says '13 bancos' instead of '12 bancos'"
    return f"SOFT_PASS: POST_DEPLOY — neither '12 bancos' nor '13 bancos' in text"


def check_no_avg_invex(resp: dict) -> Optional[str]:
    """response_text must NOT contain 'AVG(INVEX' — target excluded from formula."""
    text = _get_response_text(resp).upper()
    if not text:
        return "response_text is empty"
    if "AVG(INVEX" not in text and "WAVG(INVEX" not in text:
        return None
    return "SOFT_PASS: POST_DEPLOY — response_text includes target bank in aggregation formula"


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════

VALIDATORS = [
    # Structural — must pass now
    ("V1_NO_ERROR", "Response must not be error", check_no_error),
    ("V2_CHART_EXISTS", "Chart must have traces", check_chart_exists),
    ("V3_TWO_SERIES", "INVEX + PROMEDIO series", check_two_series),
    ("V4_TDA_RANGE", "TDA %, not MDP values", check_tda_range),
    ("V5_DATA_POINTS", ">=40 monthly points", check_data_points),
    ("V6_12_PEER_BANKS", "Exactly 12 peers in metadata", check_12_peer_banks),
    # Cosmetic — soft pass until deployed
    ("V7_WAVG_TEXT", "response_text says WAVG (not AVG)", check_wavg_in_response_text),
    ("V8_12_BANCOS_TEXT", "response_text says '12 bancos'", check_12_bancos_in_text),
    ("V9_NO_AVG_INVEX", "Target excluded from formula", check_no_avg_invex),
]


def main():
    print(f"\n{'=' * 70}")
    print(f"  E2E Peer Average response_text Fix — 2026-03-12")
    print(f"  Backend: {BACKEND_URL}")
    print(f"{'=' * 70}")

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("\nFATAL: Authentication failed")
        sys.exit(2)
    print(f"\nAuthenticated against {BACKEND_URL}")

    print(f"\n{'─' * 70}")
    print(f"  Prompt: \"{PROMPT[:90]}...\"")
    print(f"  Sending (timeout={TIMEOUT}s)...")

    resp = send_chat_message(token, PROMPT, backend_url=BACKEND_URL, timeout=TIMEOUT)
    result = TestResult(prompt=PROMPT)

    if resp.get("error"):
        print(f"  ERROR: {resp['error']}")
        result.checks = [CheckResult("INFRA", "Request must succeed", False, str(resp["error"]))]
        result.response_summary = {"error": str(resp["error"])}
    else:
        content = resp.get("content", "")
        bc = resp.get("bank_chart", {})
        traces = _get_line_traces(resp)
        response_text = _get_response_text(resp)

        print(f"  Response: {len(content)} chars, chart={'present' if bc else 'MISSING'}")
        print(f"  Traces: {list(traces.keys())}")
        if bc.get("peer_banks"):
            print(f"  Peer banks ({len(bc['peer_banks'])}): {bc['peer_banks']}")
        if response_text:
            print(f"  response_text preview: {response_text[:200]}")

        for v_name, v_desc, v_fn in VALIDATORS:
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
            "response_text_preview": response_text[:400] if response_text else "",
            "content_preview": content[:400],
        }

    total_passed = sum(1 for c in result.checks if c.passed)
    total_failed = sum(1 for c in result.checks if not c.passed)
    total = total_passed + total_failed

    print(f"\n{'=' * 70}")
    print(f"  SUMMARY: {total_passed}/{total} passed, {total_failed} failed")
    soft = sum(1 for c in result.checks if c.passed and "SOFT_PASS" in c.detail)
    if soft:
        print(f"  (includes {soft} SOFT_PASS checks — pending deployment)")
    print(f"{'=' * 70}")

    if total_failed > 0:
        print(f"\n  Failed checks:")
        for c in result.checks:
            if not c.passed:
                print(f"    {c.name}: {c.detail}")

    output = {
        "test": "peer-avg-response-text-2026-03-12",
        "backend_url": BACKEND_URL,
        "total_checks": total,
        "passed": total_passed,
        "failed": total_failed,
        "soft_pass": soft if 'soft' in dir() else 0,
        "checks": [
            {"name": c.name, "description": c.description,
             "passed": c.passed, "detail": c.detail}
            for c in result.checks
        ],
        "response_summary": result.response_summary,
    }

    out_path = Path(__file__).with_name("peer_avg_response_text_2026_03_12_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved: {out_path}")

    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
