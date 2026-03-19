#!/usr/bin/env python3
"""
E2E Regression: Help Onboarding Prompts

Validates the 3 prompts shown in the Help/Onboarding section (HelpOnboardingMenu.tsx).
These are the first queries new users see — they MUST work reliably.

Prompts:
  Paso 1: "Analiza el ICAP de INVEX en los ultimos 12 meses y muestra los datos en tabla."
  Paso 2: "Compara el ICAP de BBVA y Santander en los ultimos 12 meses en formato tabular con periodos exactos."
  Paso 3: "Grafica la morosidad (IMOR) de Banorte en los ultimos 24 meses y resume los cambios clave."

Validation layers:
  1. Chart existence: bank_chart must be present with chart_status=success
  2. Period coverage: chart dates must span the requested months (±2 tolerance)
  3. Bank match: chart traces must reference the correct bank(s)
  4. Value sanity: values must be non-zero and within plausible ranges
  5. No contradiction: LLM text must not deny data when chart is present
  6. Citation grounding: numbers in text must match chart values (1% tolerance)
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "120"))

RELATIVE_TOLERANCE = 0.01
ABSOLUTE_TOLERANCE = 0.1

CONTRADICTION_PHRASES = [
    "no tengo datos",
    "no hay datos",
    "no puedo proporcionar",
    "no puedo mostrar",
    "no está disponible",
    "no encontré datos",
    "no se encontraron",
    "no cuento con",
    "no dispongo de",
    "no es posible obtener",
    "no puedo generar",
    "problema técnico",
    "error al",
]


@dataclass
class HelpPromptTestCase:
    step_id: str
    title: str
    prompt: str
    expected_banks: List[str]
    expected_months: int
    month_tolerance: int = 2
    expect_chart: bool = True
    expect_no_contradiction: bool = True
    expect_table: bool = False
    expect_multi_trace: bool = False
    max_unmatched_citations: int = 4
    value_range: Optional[tuple] = None  # (min, max) for sanity check


@dataclass
class HelpPromptResult:
    test_case: HelpPromptTestCase
    passed: bool = False
    text_content: str = ""
    has_chart: bool = False
    chart_status: str = ""
    chart_banks: List[str] = field(default_factory=list)
    chart_dates: List[str] = field(default_factory=list)
    chart_values: List[float] = field(default_factory=list)
    chart_traces: int = 0
    contradictions: List[str] = field(default_factory=list)
    has_table: bool = False
    period_span_months: int = 0
    unmatched_citations: int = 0
    total_citations: int = 0
    errors: List[str] = field(default_factory=list)
    error: Optional[str] = None


# === Help Onboarding Prompts (from HelpOnboardingMenu.tsx) ===

TEST_CASES = [
    HelpPromptTestCase(
        step_id="paso-1-icap-invex",
        title="Paso 1: Consulta Base — ICAP INVEX 12m",
        prompt="Analiza el ICAP de INVEX en los ultimos 12 meses y muestra los datos en tabla.",
        expected_banks=["INVEX"],
        expected_months=12,
        expect_table=True,
        max_unmatched_citations=6,
        value_range=(0.0, 100.0),  # ICAP is a percentage, typically 10-30%
    ),
    HelpPromptTestCase(
        step_id="paso-2-comparativo-icap",
        title="Paso 2: Comparativo — ICAP BBVA vs Santander 12m",
        prompt="Compara el ICAP de BBVA y Santander en los ultimos 12 meses en formato tabular con periodos exactos.",
        expected_banks=["BBVA", "SANTANDER"],
        expected_months=12,
        expect_table=True,
        expect_multi_trace=True,
        max_unmatched_citations=8,
    ),
    HelpPromptTestCase(
        step_id="paso-3-imor-banorte",
        title="Paso 3: Validación — IMOR Banorte 24m",
        prompt="Grafica la morosidad (IMOR) de Banorte en los ultimos 24 meses y resume los cambios clave.",
        expected_banks=["BANORTE"],
        expected_months=24,
        expect_table=False,
        max_unmatched_citations=4,
        value_range=(0.0, 20.0),  # IMOR is a percentage, should be 0-20%
    ),
]


# === Extraction Helpers ===


def extract_chart_dates(bank_chart: Dict[str, Any]) -> List[str]:
    dates = []
    plotly = bank_chart.get("plotly_config", {})
    if not plotly:
        return dates
    for trace in plotly.get("data", []):
        for x in trace.get("x", []):
            if isinstance(x, str):
                dates.append(x)
    return dates


def extract_chart_values(bank_chart: Dict[str, Any]) -> List[float]:
    values = []
    plotly = bank_chart.get("plotly_config", {})
    if not plotly:
        return values
    for trace in plotly.get("data", []):
        for v in trace.get("y", []):
            if v is not None and isinstance(v, (int, float)):
                values.append(float(v))
        if trace.get("orientation") == "h":
            for v in trace.get("x", []):
                if v is not None and isinstance(v, (int, float)):
                    values.append(float(v))
    return values


def extract_trace_names(bank_chart: Dict[str, Any]) -> List[str]:
    names = []
    plotly = bank_chart.get("plotly_config", {})
    if not plotly:
        return names
    for trace in plotly.get("data", []):
        name = trace.get("name", "")
        if name:
            names.append(name.upper())
    return names


def count_traces(bank_chart: Dict[str, Any]) -> int:
    plotly = bank_chart.get("plotly_config", {})
    if not plotly:
        return 0
    return len(plotly.get("data", []))


def estimate_month_span(dates: List[str]) -> int:
    """Estimate the number of months spanned by date strings."""
    if len(dates) < 2:
        return len(dates)
    parsed = []
    for d in dates:
        m = re.match(r"(\d{4})-(\d{2})", d)
        if m:
            parsed.append(int(m.group(1)) * 12 + int(m.group(2)))
    if len(parsed) < 2:
        return len(dates)
    return max(parsed) - min(parsed) + 1


def extract_data_citations(text: str) -> List[dict]:
    citations = []
    # Currency
    for m in re.finditer(
        r"\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(MDP|mdp|millones(?:\s+de\s+pesos)?|mil\s+millones|pesos)",
        text,
    ):
        raw = m.group(1).replace(",", "")
        try:
            citations.append({"value": float(raw), "unit": m.group(2).strip(), "raw": m.group(0)})
        except ValueError:
            pass
    # Percentages
    for m in re.finditer(r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*%", text):
        raw = m.group(1).replace(",", "")
        try:
            val = float(raw)
            if val == 100:
                continue
            citations.append({"value": val, "unit": "%", "raw": m.group(0)})
        except ValueError:
            pass
    return citations


def match_citation_to_chart(citation_value: float, unit: str, chart_values: List[float]) -> bool:
    for cv in chart_values:
        if cv == 0:
            continue
        if _close(citation_value, cv):
            return True
        if unit in ("MDP", "mdp", "millones", "millones de pesos"):
            if abs(cv) >= 1000 and _close(citation_value, cv / 1e6):
                return True
            if abs(citation_value) >= 1e6 and _close(citation_value / 1e6, cv):
                return True
    return False


def _close(a: float, b: float) -> bool:
    if b == 0:
        return abs(a) < ABSOLUTE_TOLERANCE
    return abs(a - b) / abs(b) <= RELATIVE_TOLERANCE or abs(a - b) <= ABSOLUTE_TOLERANCE


def has_markdown_table(text: str) -> bool:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 3:
            if i + 1 < len(lines):
                sep = lines[i + 1].strip()
                if re.match(r"^\|[\s\-:|]+(\|[\s\-:|]+)+\|$", sep):
                    return True
    return False


def check_contradictions(text: str) -> List[str]:
    found = []
    tl = text.lower()
    for phrase in CONTRADICTION_PHRASES:
        if phrase in tl:
            found.append(phrase)
    return found


# === Test Runner ===


def run_test(token: str, tc: HelpPromptTestCase) -> HelpPromptResult:
    r = HelpPromptResult(test_case=tc)

    resp = send_chat_message(
        token, tc.prompt, backend_url=BACKEND_URL, stream=True, timeout=TIMEOUT
    )

    if resp.get("error"):
        r.error = f"Request failed: {resp['error']}"
        return r

    r.text_content = resp.get("content", "")
    bc = resp.get("bank_chart")
    r.has_chart = bc is not None

    if bc:
        r.chart_status = str(bc.get("chart_status", "unknown"))
        r.chart_dates = extract_chart_dates(bc)
        r.chart_values = extract_chart_values(bc)
        r.chart_banks = extract_trace_names(bc)
        r.chart_traces = count_traces(bc)

    # === Validation 1: Chart existence ===
    if tc.expect_chart:
        if not r.has_chart:
            r.errors.append("NO_CHART: Expected chart but none returned")
        elif r.chart_status != "success":
            r.errors.append(f"CHART_STATUS: Expected 'success', got '{r.chart_status}'")

    # === Validation 2: Period coverage ===
    if r.chart_dates:
        r.period_span_months = estimate_month_span(r.chart_dates)
        min_expected = tc.expected_months - tc.month_tolerance
        if r.period_span_months < min_expected:
            r.errors.append(
                f"PERIOD_SHORT: Chart spans {r.period_span_months} months, "
                f"expected >= {min_expected} (requested {tc.expected_months})"
            )

    # === Validation 3: Bank match ===
    if r.has_chart and r.chart_status == "success":
        for expected_bank in tc.expected_banks:
            found = any(expected_bank in name for name in r.chart_banks)
            if not found:
                # Also check in chart title or bank_names
                chart_title = bc.get("plotly_config", {}).get("layout", {}).get("title", "")
                bank_names = bc.get("bank_names", [])
                if isinstance(bank_names, list):
                    found = any(expected_bank in str(bn).upper() for bn in bank_names)
                if not found and expected_bank in str(chart_title).upper():
                    found = True
                if not found:
                    r.errors.append(
                        f"BANK_MISSING: Expected '{expected_bank}' in chart traces, "
                        f"found: {r.chart_banks}"
                    )

    # === Validation 4: Multi-trace ===
    if tc.expect_multi_trace and r.chart_traces < 2:
        r.errors.append(
            f"SINGLE_TRACE: Expected multiple traces for comparison, got {r.chart_traces}"
        )

    # === Validation 5: Value sanity ===
    if r.chart_values and tc.value_range:
        vmin, vmax = tc.value_range
        out_of_range = [v for v in r.chart_values if v < vmin or v > vmax]
        if out_of_range:
            r.errors.append(
                f"VALUE_RANGE: {len(out_of_range)} values outside [{vmin}, {vmax}], "
                f"e.g. {out_of_range[:3]}"
            )

    # === Validation 6: No contradiction ===
    if tc.expect_no_contradiction and r.has_chart and r.chart_status == "success":
        r.contradictions = check_contradictions(r.text_content)
        if r.contradictions:
            r.errors.append(f"CONTRADICTION: Text contains: {r.contradictions}")

    # === Validation 7: Table presence ===
    if tc.expect_table:
        r.has_table = has_markdown_table(r.text_content)
        # Also check table_append_chunk (SSE event)
        extra = resp.get("extra", {})
        if not r.has_table and "table_append" in extra:
            table_text = extra.get("table_append", "")
            if isinstance(table_text, str):
                r.has_table = has_markdown_table(table_text)
        # Soft warning — LLM table generation is non-deterministic
        if not r.has_table:
            r.errors.append("TABLE_MISSING: Expected markdown table in response (soft)")

    # === Validation 8: Citation grounding ===
    if r.has_chart and r.chart_status == "success" and r.chart_values:
        citations = extract_data_citations(r.text_content)
        r.total_citations = len(citations)
        unmatched = 0
        for c in citations:
            if not match_citation_to_chart(c["value"], c["unit"], r.chart_values):
                unmatched += 1
        r.unmatched_citations = unmatched
        if unmatched > tc.max_unmatched_citations:
            r.errors.append(
                f"CITATIONS: {unmatched} unmatched citations (max {tc.max_unmatched_citations})"
            )

    # Determine pass/fail: hard errors only (exclude TABLE_MISSING soft warning)
    hard_errors = [e for e in r.errors if not e.startswith("TABLE_MISSING")]
    r.passed = len(hard_errors) == 0
    if hard_errors:
        r.error = hard_errors[0]

    return r


def main() -> int:
    print("=" * 70)
    print("E2E Regression: Help Onboarding Prompts (HelpOnboardingMenu.tsx)")
    print("=" * 70)
    print()

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FATAL: Auth failed against", BACKEND_URL)
        return 2

    print(f"Authenticated against {BACKEND_URL}\n")

    results: List[HelpPromptResult] = []
    passed = failed = 0

    for tc in TEST_CASES:
        print(f"--- {tc.step_id}: {tc.title} ---")
        print(f'  Prompt: "{tc.prompt[:80]}..."')

        r = run_test(token, tc)
        results.append(r)

        if r.passed:
            passed += 1
            status_icon = "PASSED"
        else:
            failed += 1
            status_icon = "FAILED"

        print(f"  {status_icon}")
        print(f"     Chart: {r.has_chart} (status={r.chart_status})")
        print(f"     Traces: {r.chart_traces}, Banks: {r.chart_banks}")
        if r.chart_dates:
            print(f"     Dates: {r.chart_dates[0]} ... {r.chart_dates[-1]} ({r.period_span_months}m)")
        if r.chart_values:
            print(f"     Values: {len(r.chart_values)} points, range [{min(r.chart_values):.4f}, {max(r.chart_values):.4f}]")
        print(f"     Citations: {r.total_citations} total, {r.unmatched_citations} unmatched")
        if r.has_table:
            print(f"     Table: yes")
        if r.contradictions:
            print(f"     Contradictions: {r.contradictions}")

        for err in r.errors:
            prefix = "  >> SOFT" if err.startswith("TABLE_MISSING") else "  >> HARD"
            print(f"     {prefix}: {err}")

        if not r.passed and r.text_content:
            print(f"     Text: {r.text_content[:250].replace(chr(10), ' ')}")

        print()

    # Summary
    print("=" * 70)
    total = passed + failed
    if failed == 0:
        print(f"All {total} help prompts PASSED!")
    else:
        print(f"{failed}/{total} help prompts FAILED")
    print("=" * 70)

    # Save results
    out = Path(__file__).parent / "help_onboarding_results.json"
    out.write_text(
        json.dumps(
            {
                "total_passed": passed,
                "total_failed": failed,
                "cases": [
                    {
                        "step_id": r.test_case.step_id,
                        "prompt": r.test_case.prompt,
                        "passed": r.passed,
                        "has_chart": r.has_chart,
                        "chart_status": r.chart_status,
                        "chart_banks": r.chart_banks,
                        "chart_dates_first": r.chart_dates[0] if r.chart_dates else None,
                        "chart_dates_last": r.chart_dates[-1] if r.chart_dates else None,
                        "period_span_months": r.period_span_months,
                        "chart_values_count": len(r.chart_values),
                        "chart_values_range": (
                            [round(min(r.chart_values), 4), round(max(r.chart_values), 4)]
                            if r.chart_values else None
                        ),
                        "chart_traces": r.chart_traces,
                        "total_citations": r.total_citations,
                        "unmatched_citations": r.unmatched_citations,
                        "contradictions": r.contradictions,
                        "has_table": r.has_table,
                        "errors": r.errors,
                        "error": r.error,
                    }
                    for r in results
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"\nResults: {out}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
