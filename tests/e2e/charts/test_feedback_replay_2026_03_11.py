#!/usr/bin/env python3
"""
E2E Feedback Replay — 2026-03-11 (multi-bank-comparison-routing-failures)

Replays EXACT queries from 7 thumbs-down reported by Invex client (Fernando).
All from conversation `19f8707e`. Root cause: METRIC_MISROUTE — handler
returned CARTERA_TOTAL instead of the requested metric.

Source: docs/kanban/DOING/2026-03-06__BUG__multi-bank-comparison-routing-failures/card.md
Triage: docs/reports/feedback_triage/2026-03-11.md

Scenarios:
  S1 — Distribución porcentual etapas E1/E2/E3, Dic 2025, 10 bancos (FDBK-0203)
        Bug: "No encontré datos" → MultiMetricHandler should route to ct_etapa_*
  S2 — % Etapa 3 evolución, INVEX vs promedio (FDBK-0204)
        Bug: returned CARTERA_TOTAL MDP → should return ct_etapa_3 %
  S3 — TDA cartera total, Dic 2025, 10 bancos, barras (FDBK-0205)
        Bug: returned CARTERA_TOTAL MDP → should return tda_cartera_total %
  S4 — TDA evolución, INVEX vs promedio (FDBK-0206)
        Bug: returned CARTERA_TOTAL MDP → should return tda_cartera_total %
  S5 — Tasa interés efectiva, Dic 2025, 10 bancos, barras (FDBK-0207)
        Bug: returned CARTERA_TOTAL MDP → should return tasa_sistema %
  S6 — Tasa interés efectiva evolución, INVEX vs promedio (FDBK-0208)
        Bug: returned Tasa ME (wrong tasa) → should return tasa_sistema
  S7 — PE total (incluyendo gobierno), Dic 2025, 10 bancos (FDBK-0209)
        Bug: "No se dispone de datos" / returned CARTERA_GOBIERNO → pe_total

Usage:
    python tests/e2e/charts/test_feedback_replay_2026_03_11.py

    # Single scenario
    python tests/e2e/charts/test_feedback_replay_2026_03_11.py --scenario S3

    # Custom backend
    TEST_BACKEND_URL=http://localhost:18000 python tests/e2e/charts/test_feedback_replay_2026_03_11.py
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

# ══════════════════════════════════════════════════════════════════════════════
# Target banks — same 10 banks the client used in all queries
# ══════════════════════════════════════════════════════════════════════════════

TARGET_BANKS = [
    "MONEX", "INVEX", "BANCREA", "SABADELL", "MIFEL",
    "MULTIVA", "AFIRME", "BANSI", "VE POR MAS", "BANCO BASE",
]
BANK_ALIASES = {"BANCA MIFEL": "MIFEL"}

# ══════════════════════════════════════════════════════════════════════════════
# Exact prompts from user conversation 19f8707e (triage report section 4)
# ══════════════════════════════════════════════════════════════════════════════

PROMPT_S1_ETAPAS = (
    "Muestra la distribución porcentual de etapas de cartera total "
    "(Etapa 1, Etapa 2, Etapa 3) para diciembre 2025 para los bancos:\n"
    "MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, "
    "VE POR MAS Y BANCO BASE.\n"
    "Haz una gráfica de barras apiladas al 100% y marca a INVEX de color rojo.\n"
    "Incluye una tabla con: Banco | % Etapa 1 | % Etapa 2 | % Etapa 3"
)

PROMPT_S2_ETAPA3_EVOL = (
    "Crea una gráfica donde se compare el porcentaje de Etapa 3 de cartera "
    "total de INVEX contra el promedio de los bancos:\n"
    "MONEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, "
    "VE POR MAS Y BANCO BASE.\n"
    "De enero 2021 hasta el dato más reciente que tengas."
)

PROMPT_S3_TDA_BAR = (
    "Muestra la TDA de cartera total para diciembre 2025 para los bancos:\n"
    "MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, "
    "VE POR MAS Y BANCO BASE.\n"
    "Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca "
    "a INVEX de color rojo.\n"
    "Incluye una tabla con: Banco | TDA Cartera Total"
)

PROMPT_S4_TDA_EVOL = (
    "Crea una gráfica donde se compare la TDA de cartera total de INVEX "
    "contra el promedio de los bancos:\n"
    "MONEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, "
    "VE POR MAS Y BANCO BASE.\n"
    "De enero 2021 hasta el dato más reciente que tengas."
)

PROMPT_S5_TASA_EFECTIVA_BAR = (
    "Muestra la tasa de interés efectiva para diciembre 2025 para los bancos:\n"
    "MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, "
    "VE POR MAS Y BANCO BASE.\n"
    "Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca "
    "a INVEX de color rojo.\n"
    "Incluye una tabla con: Banco | Tasa Int. Efectiva"
)

PROMPT_S6_TASA_EFECTIVA_EVOL = (
    "Crea una gráfica donde se compare la tasa de interés efectiva de INVEX "
    "contra el promedio de los bancos:\n"
    "MONEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, "
    "VE POR MAS Y BANCO BASE.\n"
    "De enero 2021 hasta el dato más reciente que tengas."
)

PROMPT_S7_PE_TOTAL = (
    "Muestra la pérdida esperada total (incluyendo gobierno) para diciembre "
    "2025 para los bancos:\n"
    "MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, "
    "VE POR MAS Y BANCO BASE.\n"
    "Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca "
    "a INVEX de color rojo.\n"
    "Incluye una tabla con: Banco | PE Total"
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
    feedback_ids: list[str]
    prompt: str
    checks: list[CheckResult] = field(default_factory=list)
    response_summary: dict[str, Any] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _run(name: str, description: str,
         fn: Callable[..., str | None], *args: Any) -> CheckResult:
    try:
        error = fn(*args)
        if error is None:
            return CheckResult(name, description, True, "OK")
        if error.startswith("SOFT_PASS:"):
            return CheckResult(name, description, True, error)
        return CheckResult(name, description, False, error)
    except Exception as e:
        return CheckResult(name, description, False, f"Exception: {e}")


def _normalize_bank(name: str) -> str:
    n = name.strip().upper()
    return BANK_ALIASES.get(n, n)


def _get_bar_banks(resp: dict) -> list[str]:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return []
    # Horizontal bar: bank names in y-axis of first trace
    y_vals = traces[0].get("y", [])
    banks = [_normalize_bank(str(b)) for b in y_vals
             if not _is_numeric(str(b))]
    if banks:
        return banks
    # Scatter/line fallback: bank names as trace names
    return [_normalize_bank(t.get("name", "")) for t in traces
            if t.get("name")]


def _is_numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def _get_bar_values(resp: dict) -> list[float]:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return []
    # Horizontal bar: values in x-axis
    x_vals = [v for v in traces[0].get("x", [])
              if v is not None and isinstance(v, (int, float))]
    if x_vals:
        return x_vals
    # Scatter/line fallback: values in y-axis
    return [v for v in traces[0].get("y", [])
            if v is not None and isinstance(v, (int, float))]


def _get_line_traces(resp: dict) -> dict[str, list]:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    result = {}
    for t in traces:
        name = _normalize_bank(t.get("name", ""))
        y_vals = t.get("y", [])
        if name:
            result[name] = y_vals
    return result


def _get_chart_title(resp: dict) -> str:
    bc = resp.get("bank_chart", {})
    layout = bc.get("plotly_config", {}).get("layout", {})
    title = layout.get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")
    return str(title).lower()


_DATA_DENIAL_PHRASES = [
    "no se dispone de datos",
    "no dispone de datos",
    "no tengo datos",
    "no tengo los datos",
    "no hay datos disponibles",
    "no se encontraron datos",
    "no encontré datos",
    "no encontre datos",
    "datos no disponibles",
    "no puede generarse",
    "no pude completar",
]


def _has_data_denial(text: str) -> Optional[str]:
    lower = text.lower()
    for phrase in _DATA_DENIAL_PHRASES:
        if phrase in lower:
            return phrase
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Regression guard: detects CARTERA_TOTAL fallback (the core bug)
# ══════════════════════════════════════════════════════════════════════════════


def _check_not_cartera_total(resp: dict, expected_metric: str) -> str | None:
    """Verify the response is NOT about CARTERA_TOTAL when another metric was asked.

    This is the central regression check — before the fix, ALL these queries
    returned CARTERA_TOTAL data (amounts in MDP) instead of ratio/percentage data.
    """
    content = resp.get("content", "").lower()
    title = _get_chart_title(resp)

    # Check chart title for wrong metric
    wrong_markers = ["cartera total", "cartera_total"]
    for marker in wrong_markers:
        if marker in title and expected_metric not in title:
            return (
                f"REGRESSION: chart title contains '{marker}' — "
                f"expected '{expected_metric}'. Title: '{title}'"
            )

    # Check if values are in MDP range (currency) instead of % range (ratio)
    bar_vals = _get_bar_values(resp)
    if bar_vals:
        max_val = max(abs(v) for v in bar_vals)
        # CARTERA_TOTAL values are typically 10,000+ MDP
        # Ratio values (TDA, PE, tasa) are typically 0-100%
        if max_val > 1000:
            return (
                f"REGRESSION: values look like currency (max={max_val:,.0f}) "
                f"instead of ratio/percentage for '{expected_metric}'"
            )

    # Check line chart traces for MDP-scale values
    traces = _get_line_traces(resp)
    for name, y_vals in traces.items():
        valid = [v for v in y_vals if isinstance(v, (int, float))]
        if valid:
            max_v = max(abs(v) for v in valid)
            if max_v > 1000:
                return (
                    f"REGRESSION: trace '{name}' has MDP-scale values "
                    f"(max={max_v:,.0f}) instead of ratio for '{expected_metric}'"
                )

    return None


# ══════════════════════════════════════════════════════════════════════════════
# S1: Distribución porcentual de etapas E1/E2/E3 (stacked bar)
# ══════════════════════════════════════════════════════════════════════════════


def s1_chart_exists(resp: dict) -> str | None:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No chart traces found — was 'no data' before fix"
    return None


def s1_multiple_traces(resp: dict) -> str | None:
    """Stacked bar should have >=3 traces (E1, E2, E3)."""
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if len(traces) < 2:
        return f"Expected >=2 traces for stacked etapas, got {len(traces)}"
    return None


def s1_bank_coverage(resp: dict) -> str | None:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No traces"
    # In stacked bars, banks may be on y-axis (horizontal) or x-axis (vertical)
    y_vals = traces[0].get("y", [])
    x_vals = traces[0].get("x", [])
    axis_vals = y_vals if any(not _is_numeric(str(v)) for v in y_vals) else x_vals
    banks = [_normalize_bank(str(b)) for b in axis_vals if not _is_numeric(str(b))]
    found = [b for b in TARGET_BANKS if b in banks]
    if len(found) < 8:
        missing = [b for b in TARGET_BANKS if b not in banks]
        return f"Only {len(found)}/10 banks. Missing: {missing}"
    return None


def s1_no_data_denial(resp: dict) -> str | None:
    denial = _has_data_denial(resp.get("content", ""))
    if denial:
        return f"REGRESSION: LLM denied data: '{denial}'"
    return None


def s1_values_are_percentages(resp: dict) -> str | None:
    """Etapa values should sum to ~100% per bank."""
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No traces"
    # Check all x values are in [0, 100] range
    for t in traces:
        x_vals = [v for v in t.get("x", []) if v is not None and isinstance(v, (int, float))]
        for v in x_vals:
            if v < 0 or v > 110:
                return f"Value {v} out of percentage range [0, 110]"
    return None


def s1_not_cartera_total(resp: dict) -> str | None:
    return _check_not_cartera_total(resp, "etapa")


# ══════════════════════════════════════════════════════════════════════════════
# S2: % Etapa 3 evolución, INVEX vs promedio
# ══════════════════════════════════════════════════════════════════════════════


def s2_chart_exists(resp: dict) -> str | None:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No chart traces"
    return None


def s2_two_series(resp: dict) -> str | None:
    traces_dict = _get_line_traces(resp)
    names = list(traces_dict.keys())
    if len(names) < 2:
        return f"Expected 2 series (INVEX + PROMEDIO), got {len(names)}: {names}"
    has_invex = any("INVEX" in n for n in names)
    has_avg = any(n in names for n in ["PROMEDIO", "PROMEDIO PEERS", "AVERAGE"])
    if not has_invex:
        return f"INVEX series missing. Got: {names}"
    if not has_avg:
        return f"PROMEDIO series missing. Got: {names}"
    return None


def s2_not_cartera_total(resp: dict) -> str | None:
    return _check_not_cartera_total(resp, "etapa_3")


def s2_values_are_ratio(resp: dict) -> str | None:
    """% Etapa 3 values should be 0-100, not MDP."""
    traces = _get_line_traces(resp)
    for name, y_vals in traces.items():
        valid = [v for v in y_vals if v is not None]
        if valid and max(valid) > 100:
            return f"Trace '{name}' has values > 100 (max={max(valid):.0f}), expected percentage"
    return None


def s2_no_data_denial(resp: dict) -> str | None:
    denial = _has_data_denial(resp.get("content", ""))
    if denial:
        return f"REGRESSION: LLM denied data: '{denial}'"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# S3: TDA barras horizontales, 10 bancos, Dic 2025
# ══════════════════════════════════════════════════════════════════════════════


def s3_chart_exists(resp: dict) -> str | None:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No chart traces"
    t0 = traces[0]
    if t0.get("type") != "bar":
        return f"Expected bar chart, got type={t0.get('type')}"
    return None


def s3_bank_coverage(resp: dict) -> str | None:
    banks = _get_bar_banks(resp)
    found = [b for b in TARGET_BANKS if b in banks]
    if len(found) < 8:
        missing = [b for b in TARGET_BANKS if b not in banks]
        return f"Only {len(found)}/10 banks. Missing: {missing}. Got: {banks}"
    return None


def s3_not_cartera_total(resp: dict) -> str | None:
    return _check_not_cartera_total(resp, "tda")


def s3_values_plausible(resp: dict) -> str | None:
    """TDA values should be in [0, 30] range (percentage)."""
    vals = _get_bar_values(resp)
    if not vals:
        return "No numeric values in chart"
    out = [v for v in vals if v < 0 or v > 30]
    if out:
        return f"TDA values out of range [0, 30]: {out}"
    return None


def s3_no_data_denial(resp: dict) -> str | None:
    denial = _has_data_denial(resp.get("content", ""))
    if denial:
        return f"REGRESSION: LLM denied data: '{denial}'"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# S4: TDA evolución, INVEX vs promedio
# ══════════════════════════════════════════════════════════════════════════════


def s4_chart_exists(resp: dict) -> str | None:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No chart traces"
    return None


def s4_two_series(resp: dict) -> str | None:
    traces_dict = _get_line_traces(resp)
    names = list(traces_dict.keys())
    has_invex = any("INVEX" in n for n in names)
    has_avg = any(n in names for n in ["PROMEDIO", "PROMEDIO PEERS", "AVERAGE"])
    if not has_invex or not has_avg:
        return f"Expected INVEX + PROMEDIO, got: {names}"
    return None


def s4_not_cartera_total(resp: dict) -> str | None:
    return _check_not_cartera_total(resp, "tda")


def s4_title_mentions_tda(resp: dict) -> str | None:
    title = _get_chart_title(resp)
    tda_markers = ["tda", "deterioro", "alejamiento"]
    if any(m in title for m in tda_markers):
        return None
    if "cartera total" in title and "tda" not in title:
        return f"REGRESSION: title='{title}' mentions cartera total, not TDA"
    return f"SOFT_PASS: title='{title}' does not mention TDA"


def s4_no_data_denial(resp: dict) -> str | None:
    denial = _has_data_denial(resp.get("content", ""))
    if denial:
        return f"REGRESSION: LLM denied data: '{denial}'"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# S5: Tasa interés efectiva barras, 10 bancos, Dic 2025
# ══════════════════════════════════════════════════════════════════════════════


def s5_chart_exists(resp: dict) -> str | None:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No chart traces"
    return None


def s5_bank_coverage(resp: dict) -> str | None:
    banks = _get_bar_banks(resp)
    found = [b for b in TARGET_BANKS if b in banks]
    if len(found) < 8:
        missing = [b for b in TARGET_BANKS if b not in banks]
        return f"Only {len(found)}/10 banks. Missing: {missing}"
    return None


def s5_not_cartera_total(resp: dict) -> str | None:
    return _check_not_cartera_total(resp, "tasa")


def s5_values_plausible(resp: dict) -> str | None:
    """Tasa sistema values should be in [3, 30] range."""
    vals = _get_bar_values(resp)
    if not vals:
        return "No numeric values"
    out = [v for v in vals if v < 3 or v > 30]
    if out:
        return f"Tasa efectiva values out of range [3, 30]: {out}"
    return None


def s5_not_tasa_me(resp: dict) -> str | None:
    """Must NOT route to tasa_me (was the bug in FDBK-0208)."""
    title = _get_chart_title(resp)
    if "tasa_me" in title or "tasa promedio me" in title or "moneda extranjera" in title:
        return f"REGRESSION: routed to tasa_me instead of tasa_sistema. Title: '{title}'"
    return None


def s5_no_data_denial(resp: dict) -> str | None:
    denial = _has_data_denial(resp.get("content", ""))
    if denial:
        return f"REGRESSION: LLM denied data: '{denial}'"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# S6: Tasa interés efectiva evolución, INVEX vs promedio
# ══════════════════════════════════════════════════════════════════════════════


def s6_chart_exists(resp: dict) -> str | None:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No chart traces"
    return None


def s6_two_series(resp: dict) -> str | None:
    traces_dict = _get_line_traces(resp)
    names = list(traces_dict.keys())
    has_invex = any("INVEX" in n for n in names)
    has_avg = any(n in names for n in ["PROMEDIO", "PROMEDIO PEERS", "AVERAGE"])
    if not has_invex or not has_avg:
        return f"Expected INVEX + PROMEDIO, got: {names}"
    return None


def s6_not_tasa_me(resp: dict) -> str | None:
    """Must NOT route to tasa_me — should be tasa_sistema."""
    title = _get_chart_title(resp)
    if "tasa_me" in title or "tasa promedio me" in title or "moneda extranjera" in title:
        return f"REGRESSION: routed to tasa_me. Title: '{title}'"
    content = resp.get("content", "").lower()
    if "tasa promedio me" in content and "tasa" in content and "efectiva" not in content:
        return "REGRESSION: response mentions 'tasa promedio me' instead of tasa efectiva"
    return None


def s6_not_cartera_total(resp: dict) -> str | None:
    return _check_not_cartera_total(resp, "tasa")


def s6_no_data_denial(resp: dict) -> str | None:
    denial = _has_data_denial(resp.get("content", ""))
    if denial:
        return f"REGRESSION: LLM denied data: '{denial}'"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# S7: PE total (incluyendo gobierno), barras, 10 bancos
# ══════════════════════════════════════════════════════════════════════════════


def s7_chart_exists(resp: dict) -> str | None:
    bc = resp.get("bank_chart", {})
    traces = bc.get("plotly_config", {}).get("data", [])
    if not traces:
        return "No chart traces — was 'no data' before fix"
    return None


def s7_bank_coverage(resp: dict) -> str | None:
    banks = _get_bar_banks(resp)
    found = [b for b in TARGET_BANKS if b in banks]
    if len(found) < 8:
        missing = [b for b in TARGET_BANKS if b not in banks]
        return f"Only {len(found)}/10 banks. Missing: {missing}"
    return None


def s7_not_cartera_total(resp: dict) -> str | None:
    return _check_not_cartera_total(resp, "pe")


def s7_not_cartera_gobierno(resp: dict) -> str | None:
    """Must NOT route to cartera_gobierno (was partial bug)."""
    title = _get_chart_title(resp)
    if "cartera gobierno" in title or "cartera_gobierno" in title:
        return f"REGRESSION: routed to cartera_gobierno instead of pe_total. Title: '{title}'"
    return None


def s7_values_plausible(resp: dict) -> str | None:
    """PE total is a ratio, values should be in [0, 50] range."""
    vals = _get_bar_values(resp)
    if not vals:
        return "No numeric values"
    out = [v for v in vals if v < 0 or v > 50]
    if out:
        return f"PE total values out of range [0, 50]: {out}"
    return None


def s7_no_data_denial(resp: dict) -> str | None:
    denial = _has_data_denial(resp.get("content", ""))
    if denial:
        return f"REGRESSION: LLM denied data: '{denial}'"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Scenario definitions
# ══════════════════════════════════════════════════════════════════════════════

SCENARIOS: list[tuple[str, list[str], str, str, list[tuple[str, str, Callable]]]] = [
    (
        "S1_ETAPAS_DIC2025",
        ["FDBK-0203"],
        "Distribución etapas E1/E2/E3, Dic 2025 (bug: 'no data')",
        PROMPT_S1_ETAPAS,
        [
            ("V1_CHART_EXISTS", "Chart must exist (was empty)", s1_chart_exists),
            ("V2_MULTIPLE_TRACES", ">=2 traces for stacked etapas", s1_multiple_traces),
            ("V3_BANK_COVERAGE", ">=8/10 banks", s1_bank_coverage),
            ("V4_NO_DATA_DENIAL", "LLM must not deny data", s1_no_data_denial),
            ("V5_VALUES_PCT", "Values in [0, 110] range", s1_values_are_percentages),
            ("V6_NOT_CARTERA_TOTAL", "NOT cartera_total regression", s1_not_cartera_total),
        ],
    ),
    (
        "S2_ETAPA3_EVOL",
        ["FDBK-0204"],
        "% Etapa 3 evolución — INVEX vs PROMEDIO (bug: returned CARTERA_TOTAL)",
        PROMPT_S2_ETAPA3_EVOL,
        [
            ("V1_CHART_EXISTS", "Chart must exist", s2_chart_exists),
            ("V2_TWO_SERIES", "INVEX + PROMEDIO series", s2_two_series),
            ("V3_NOT_CARTERA_TOTAL", "NOT cartera_total regression", s2_not_cartera_total),
            ("V4_VALUES_RATIO", "Values < 100 (percentage)", s2_values_are_ratio),
            ("V5_NO_DATA_DENIAL", "LLM must not deny data", s2_no_data_denial),
        ],
    ),
    (
        "S3_TDA_BAR_DIC2025",
        ["FDBK-0205"],
        "TDA barras horizontales, 10 bancos (bug: returned CARTERA_TOTAL MDP)",
        PROMPT_S3_TDA_BAR,
        [
            ("V1_CHART_EXISTS", "Horizontal bar chart", s3_chart_exists),
            ("V2_BANK_COVERAGE", ">=8/10 banks", s3_bank_coverage),
            ("V3_NOT_CARTERA_TOTAL", "NOT cartera_total regression", s3_not_cartera_total),
            ("V4_VALUES_PLAUSIBLE", "TDA in [0, 30] range", s3_values_plausible),
            ("V5_NO_DATA_DENIAL", "LLM must not deny data", s3_no_data_denial),
        ],
    ),
    (
        "S4_TDA_EVOL",
        ["FDBK-0206"],
        "TDA evolución — INVEX vs PROMEDIO (bug: returned CARTERA_TOTAL)",
        PROMPT_S4_TDA_EVOL,
        [
            ("V1_CHART_EXISTS", "Chart must exist", s4_chart_exists),
            ("V2_TWO_SERIES", "INVEX + PROMEDIO", s4_two_series),
            ("V3_NOT_CARTERA_TOTAL", "NOT cartera_total regression", s4_not_cartera_total),
            ("V4_TITLE_TDA", "Title mentions TDA", s4_title_mentions_tda),
            ("V5_NO_DATA_DENIAL", "LLM must not deny data", s4_no_data_denial),
        ],
    ),
    (
        "S5_TASA_EFECTIVA_BAR",
        ["FDBK-0207"],
        "Tasa interés efectiva barras (bug: returned CARTERA_TOTAL)",
        PROMPT_S5_TASA_EFECTIVA_BAR,
        [
            ("V1_CHART_EXISTS", "Chart must exist", s5_chart_exists),
            ("V2_BANK_COVERAGE", ">=8/10 banks", s5_bank_coverage),
            ("V3_NOT_CARTERA_TOTAL", "NOT cartera_total regression", s5_not_cartera_total),
            ("V4_VALUES_PLAUSIBLE", "Tasa in [3, 30]", s5_values_plausible),
            ("V5_NOT_TASA_ME", "NOT tasa_me misroute", s5_not_tasa_me),
            ("V6_NO_DATA_DENIAL", "LLM must not deny data", s5_no_data_denial),
        ],
    ),
    (
        "S6_TASA_EFECTIVA_EVOL",
        ["FDBK-0208"],
        "Tasa interés efectiva evolución (bug: returned Tasa ME)",
        PROMPT_S6_TASA_EFECTIVA_EVOL,
        [
            ("V1_CHART_EXISTS", "Chart must exist", s6_chart_exists),
            ("V2_TWO_SERIES", "INVEX + PROMEDIO", s6_two_series),
            ("V3_NOT_TASA_ME", "NOT tasa_me misroute", s6_not_tasa_me),
            ("V4_NOT_CARTERA_TOTAL", "NOT cartera_total regression", s6_not_cartera_total),
            ("V5_NO_DATA_DENIAL", "LLM must not deny data", s6_no_data_denial),
        ],
    ),
    (
        "S7_PE_TOTAL_BAR",
        ["FDBK-0209"],
        "PE total (con gobierno), barras (bug: 'no data' / cartera_gobierno)",
        PROMPT_S7_PE_TOTAL,
        [
            ("V1_CHART_EXISTS", "Chart must exist (was empty)", s7_chart_exists),
            ("V2_BANK_COVERAGE", ">=8/10 banks", s7_bank_coverage),
            ("V3_NOT_CARTERA_TOTAL", "NOT cartera_total regression", s7_not_cartera_total),
            ("V4_NOT_CARTERA_GOBIERNO", "NOT cartera_gobierno misroute", s7_not_cartera_gobierno),
            ("V5_VALUES_PLAUSIBLE", "PE in [0, 50] range", s7_values_plausible),
            ("V6_NO_DATA_DENIAL", "LLM must not deny data", s7_no_data_denial),
        ],
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════


def run_scenario(
    token: str,
    scenario_id: str,
    feedback_ids: list[str],
    description: str,
    prompt: str,
    validators: list[tuple[str, str, Callable]],
) -> ScenarioResult:
    print(f"\n{'─' * 70}")
    print(f"  {scenario_id}: {description}")
    print(f"  FDBKs: {', '.join(feedback_ids)}")
    print(f"  Prompt: \"{prompt[:90]}...\"")
    print(f"  Sending (timeout={TIMEOUT}s)...")

    resp = send_chat_message(token, prompt, backend_url=BACKEND_URL, timeout=TIMEOUT)

    result = ScenarioResult(
        scenario_id=scenario_id,
        feedback_ids=feedback_ids,
        prompt=prompt,
    )

    if resp.get("error"):
        print(f"  ERROR: {resp['error']}")
        result.checks = [
            CheckResult("INFRA", "Request must succeed", False, str(resp["error"]))
        ]
        result.response_summary = {"error": str(resp["error"])}
        return result

    content = resp.get("content", "")
    bc = resp.get("bank_chart", {})

    banks_in_chart = _get_bar_banks(resp)
    if not banks_in_chart:
        trace_dict = _get_line_traces(resp)
        banks_in_chart = list(trace_dict.keys())

    print(f"  Response: {len(content)} chars, chart={'present' if bc else 'MISSING'}")
    print(f"  Banks in chart: {len(banks_in_chart)} → {banks_in_chart[:5]}{'...' if len(banks_in_chart) > 5 else ''}")

    checks = []
    for v_name, v_desc, v_fn in validators:
        check = _run(v_name, v_desc, v_fn, resp)
        status = "PASS" if check.passed else "FAIL"
        detail_str = f" — {check.detail}" if check.detail != "OK" else ""
        print(f"    [{status}] {v_name}: {v_desc}{detail_str}")
        checks.append(check)

    result.checks = checks
    result.response_summary = {
        "content_length": len(content),
        "has_chart": bool(bc),
        "banks_in_chart": banks_in_chart,
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
            print(f"No scenario matching '{filter_scenario}'. Available: "
                  f"{[s[0] for s in SCENARIOS]}")
            sys.exit(2)

    print(f"\n{'=' * 70}")
    print(f"  E2E Feedback Replay — 2026-03-11")
    print(f"  Ticket: multi-bank-comparison-routing-failures")
    print(f"  Backend: {BACKEND_URL}")
    print(f"  Scenarios: {len(scenarios)}")
    print(f"{'=' * 70}")

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("\nFATAL: Authentication failed")
        sys.exit(2)
    print(f"\nAuthenticated against {BACKEND_URL}")

    all_results: list[ScenarioResult] = []
    total_passed = 0
    total_failed = 0

    for sid, fids, desc, prompt, validators in scenarios:
        result = run_scenario(token, sid, fids, desc, prompt, validators)
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
        print(f"  [{status}] {r.scenario_id} ({p}/{p + f}) — {', '.join(r.feedback_ids)}")

    if total_failed > 0:
        print(f"\n  Failed checks:")
        for r in all_results:
            for c in r.checks:
                if not c.passed:
                    print(f"    {r.scenario_id}/{c.name}: {c.detail}")

    # Save results
    output = {
        "test": "feedback-replay-2026-03-11",
        "ticket": "multi-bank-comparison-routing-failures",
        "backend_url": BACKEND_URL,
        "total_checks": total,
        "passed": total_passed,
        "failed": total_failed,
        "scenarios": [
            {
                "scenario_id": r.scenario_id,
                "feedback_ids": r.feedback_ids,
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

    out_path = Path(__file__).with_name("feedback_replay_2026_03_11_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved: {out_path}")

    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
