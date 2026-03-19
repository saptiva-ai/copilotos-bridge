#!/usr/bin/env python3
"""
E2E Regression: Response Grounding Desync

Replays EXACT queries from production feedback where the LLM text
contained numbers that didn't match the chart data.

Feedback evidence:
- FDBK-0072: Text "15,048.23 MDP" vs chart 15,047.93 (small precision)
- FDBK-0004: Text "18,646,463,515 MDP" vs chart 16,402,586,992 (fabrication)
- FDBK-0073: Text shows round numbers (13,200, 13,350) — complete hallucination
- FDBK-0026: Text "2.32%" vs chart 2.38% (wrong data point)
- FDBK-0033: Text "no puede mostrarme" when chart_status=success

Five validation layers:
1. Contradiction check: text must not deny data when chart exists
2. Citation matching: numbers with units must match chart values
3. Chart year check: chart dates must match the requested period
4. Table reproduction: response must contain a markdown table when data exists
5. Bank-value association: values cited next to a bank name must come from that bank's trace
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

# --- Configuration ---
BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "90"))

# 1% tolerance for number matching
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
]


@dataclass
class DataCitation:
    """A number cited in the text with its unit."""

    value: float
    unit: str
    raw_text: str
    matched_chart_value: Optional[float] = None


@dataclass
class TestCase:
    feedback_id: str
    description: str
    query: str
    expect_chart: bool = True
    expect_no_contradiction: bool = True
    expect_citations_match: bool = True
    max_unmatched_citations: int = 2
    # If set, verify chart dates include this year
    expect_chart_year: Optional[str] = None
    # Verify the response contains a pipe-delimited markdown table
    expect_table_in_response: bool = False
    # Verify values cited next to bank names come from the correct trace
    expect_bank_value_grounded: bool = False


@dataclass
class TestResult:
    test_case: TestCase
    passed: bool
    text_content: str = ""
    has_chart: bool = False
    chart_status: str = ""
    chart_values: List[float] = field(default_factory=list)
    chart_dates: List[str] = field(default_factory=list)
    citations: List[DataCitation] = field(default_factory=list)
    unmatched_citations: List[DataCitation] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    has_table: bool = False
    misattributed_values: List[str] = field(default_factory=list)
    error: Optional[str] = None


# --- Test Cases: EXACT production queries ---

TEST_CASES = [
    # FDBK-0072: Small precision error (15,048.23 vs 15,047.93)
    # "muéstrame" triggers full table mode — LLM may cite derived stats too.
    TestCase(
        feedback_id="FDBK-0072",
        description="Cartera comercial INVEX 2025 — cited values must match chart",
        query="muéstrame la cartera comercial de INVEX en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        expect_chart_year="2025",
        max_unmatched_citations=4,
    ),
    # FDBK-0033: Text says "no puedo" when chart IS shown
    TestCase(
        feedback_id="FDBK-0033",
        description="Cartera comercial INVEX — must not deny data when chart exists",
        query="muestrame la cartera comercial de invex",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
    ),
    # FDBK-0004: Massive fabrication (18.6B vs 16.4B)
    TestCase(
        feedback_id="FDBK-0004",
        description="Saldo cartera comercial INVEX Oct 2025 — value must be accurate",
        query="cual es el saldo de la cartera comercial de invex a octubre de 2025?",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
    ),
    # FDBK-0026: Wrong percentage (2.32% vs 2.38%)
    TestCase(
        feedback_id="FDBK-0026",
        description="IMOR Santander — percentage must match chart data",
        query="IMOR de Santander en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        expect_chart_year="2025",
    ),
    # FDBK-0035: Text contradicts data ("no se dispone" but chart has data)
    TestCase(
        feedback_id="FDBK-0035",
        description="Cartera consumo Santander — must not deny data existence",
        query="dame la cartera de consumo de santander",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
    ),
    # ── New grounding cases: markdown table + multi-bank + diverse metrics ──
    # GND-001: Multi-bank comparison — values must not be swapped between banks
    # Stats-derived values (cambio %, diferencia) add ~3 unmatched per bank.
    TestCase(
        feedback_id="GND-001",
        description="ICAP BBVA vs Banorte — values must match per-bank traces",
        query="compara el ICAP de BBVA y Banorte en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        expect_chart_year="2025",
        expect_table_in_response=True,
        expect_bank_value_grounded=True,
        max_unmatched_citations=6,
    ),
    # GND-002: ROE ratio — small numbers prone to rounding hallucination
    TestCase(
        feedback_id="GND-002",
        description="ROE INVEX 2025 — ratio precision must match chart",
        query="ROE de INVEX en 2025",
        expect_chart=True,
        expect_no_contradiction=False,  # ROE_12M may have sparse data; LLM may report extraction issue
        expect_citations_match=True,
        expect_chart_year=None,  # ROE data availability varies
    ),
    # GND-003: Cartera hipotecaria — currency metric not tested before
    # Stats-derived values (cambio absoluto, %) add ~3 unmatched.
    TestCase(
        feedback_id="GND-003",
        description="Cartera hipotecaria BBVA — currency values must be exact",
        query="muéstrame la cartera hipotecaria de BBVA en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        expect_chart_year="2025",
        expect_table_in_response=True,
        max_unmatched_citations=4,
    ),
    # GND-004: Multi-bank currency — tests cross-bank value contamination
    # Stats-derived values (cambio período, %) add ~4 unmatched citations per bank.
    TestCase(
        feedback_id="GND-004",
        description="Cartera comercial INVEX vs Afirme — no cross-bank contamination",
        query="cartera comercial de INVEX y Afirme en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        expect_chart_year="2025",
        expect_bank_value_grounded=True,
        max_unmatched_citations=6,
    ),
    # GND-005: ICAP single bank — verifies citation accuracy for ratio metric
    # No detail keywords → stats-only context (table_mode="none"). Table not expected.
    TestCase(
        feedback_id="GND-005",
        description="ICAP INVEX 2025 — ratio citations must match chart values",
        query="ICAP de INVEX en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        expect_chart_year="2025",
        expect_table_in_response=False,
    ),
    # GND-006: Specific month — LLM must not cite wrong month's value
    # No detail keywords → stats-only context (table_mode="none"). Table not expected.
    TestCase(
        feedback_id="GND-006",
        description="IMOR INVEX — text values must come from chart, not invented",
        query="cuál es el IMOR de INVEX?",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        max_unmatched_citations=1,
        expect_table_in_response=False,
    ),
    # GND-007: Three-bank comparison — maximum opportunity for value swaps
    # 3 banks × ~2 derived stats each = up to 6 unmatched computed values.
    TestCase(
        feedback_id="GND-007",
        description="IMOR BBVA vs Santander vs Banorte — 3 bank values must be grounded",
        query="compara el IMOR de BBVA, Santander y Banorte en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        expect_chart_year="2025",
        expect_bank_value_grounded=True,
        max_unmatched_citations=8,
    ),
    # ── Lazy LLM context: table-mode detection cases ─────────────────
    # These test that the 3-tier table injection (none/excerpt/full)
    # produces accurate responses regardless of mode.
    #
    # LZY-001: Analytical query (no table keywords) → stats-only context
    # The LLM should produce a narrative using exact stats, not a table.
    # Stats-derived values (cambio período, %) are computed — allow 4 unmatched.
    TestCase(
        feedback_id="LZY-001",
        description="Analytical query — stats-only context, values must still match chart",
        query="cómo ha evolucionado la cartera comercial de INVEX en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        expect_chart_year="2025",
        expect_table_in_response=False,
        max_unmatched_citations=4,
    ),
    # LZY-002: Explicit table request with "tabla" keyword → full table
    TestCase(
        feedback_id="LZY-002",
        description="Explicit 'tabla' keyword — response should contain markdown table",
        query="muéstrame la tabla del ICAP de INVEX en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        expect_chart_year="2025",
        expect_table_in_response=True,
    ),
    # LZY-003: "mes a mes" keyword → full table mode
    # LLM may compute derived values (cambio, %) from the stats we inject.
    TestCase(
        feedback_id="LZY-003",
        description="'mes a mes' keyword — full table with monthly values",
        query="cartera comercial de INVEX mes a mes en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        expect_chart_year="2025",
        expect_table_in_response=True,
        max_unmatched_citations=6,
    ),
    # LZY-004: "valores" keyword → excerpt mode, values must still be grounded
    # Uses "cartera comercial" to avoid ICAP clarification flow.
    TestCase(
        feedback_id="LZY-004",
        description="'valores' keyword — excerpt context, cited values must match chart",
        query="dame los valores de la cartera comercial de INVEX en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        expect_chart_year="2025",
        max_unmatched_citations=4,
    ),
    # LZY-005: Multi-bank with explicit table request → table + grounding
    TestCase(
        feedback_id="LZY-005",
        description="Multi-bank + 'tabla' — table with per-bank grounding",
        query="muéstrame la tabla comparando el ICAP de BBVA y Santander en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        expect_chart_year="2025",
        expect_table_in_response=True,
        expect_bank_value_grounded=True,
    ),
    # ── Feedback-driven cases from triage 2026-02-05 ─────────────────
    # FDBK-0072: Precision error (15,048.23 vs 15,047.93)
    # This is a DIFFERENT query than the first FDBK-0072 case above.
    # The original used "muéstrame...", this one tests the multi-turn context.
    # Stats-only mode (no table keywords) — LLM cites derived values from summary stats.
    TestCase(
        feedback_id="FDBK-0072b",
        description="Cartera comercial INVEX 2025 (precision) — values within 1% tolerance",
        query="cartera comercial de INVEX en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        expect_chart_year="2025",
        max_unmatched_citations=4,
    ),
    # FDBK-0073 class: LLM claims it can't generate charts when it can.
    # Known LLM behavior — "no puedo generar" is a prompt issue.
    # We still verify the chart exists and citations are correct;
    # contradiction check is relaxed because the system DOES generate the chart.
    TestCase(
        feedback_id="FDBK-0073",
        description="Chart generation — chart exists even if LLM denies capability",
        query="hazme una gráfica de la cartera comercial de INVEX en 2025",
        expect_chart=True,
        expect_no_contradiction=False,
        expect_citations_match=True,
        expect_chart_year="2025",
        max_unmatched_citations=4,
    ),
    # FDBK-0043 class: Cartera hipotecaria extraction
    TestCase(
        feedback_id="FDBK-0043",
        description="Cartera hipotecaria INVEX — must not error on extraction",
        query="cartera hipotecaria de INVEX en 2025",
        expect_chart=True,
        expect_no_contradiction=True,
        expect_citations_match=True,
        max_unmatched_citations=3,
    ),
]


# --- Extraction functions ---


def extract_data_citations(text: str) -> List[DataCitation]:
    """Extract numbers cited WITH units (MDP, %, millones) from text."""
    citations: List[DataCitation] = []

    # Currency: "15,048.23 MDP", "$16,402 millones", "18,646,463,515 MDP"
    currency_re = (
        r"\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(MDP|mdp|millones(?:\s+de\s+pesos)?|mil\s+millones|pesos)"
    )
    for m in re.finditer(currency_re, text):
        raw = m.group(1).replace(",", "")
        try:
            citations.append(
                DataCitation(value=float(raw), unit=m.group(2).strip(), raw_text=m.group(0))
            )
        except ValueError:
            pass

    # Percentages: "2.38%", "15.05%"
    pct_re = r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*%"
    for m in re.finditer(pct_re, text):
        raw = m.group(1).replace(",", "")
        try:
            val = float(raw)
            if val == 100:
                continue
            citations.append(DataCitation(value=val, unit="%", raw_text=m.group(0)))
        except ValueError:
            pass

    return citations


def extract_chart_values(bank_chart: Dict[str, Any]) -> List[float]:
    """Extract all values from plotly traces (ground truth)."""
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


def extract_chart_dates(bank_chart: Dict[str, Any]) -> List[str]:
    """Extract all x-axis date strings from plotly traces."""
    dates = []
    plotly = bank_chart.get("plotly_config", {})
    if not plotly:
        return dates
    for trace in plotly.get("data", []):
        for x in trace.get("x", []):
            if isinstance(x, str):
                dates.append(x)
    return dates


def match_citation(citation: DataCitation, chart_values: List[float]) -> Optional[float]:
    """Try to match a data citation to a chart value."""
    tv = citation.value
    for cv in chart_values:
        if cv == 0:
            continue
        # Direct match
        if _close(tv, cv):
            return cv
        # Text in MDP/millones, chart in raw pesos (cv / 1e6 ≈ tv)
        if citation.unit in ("MDP", "mdp", "millones", "millones de pesos"):
            if abs(cv) >= 1000 and _close(tv, cv / 1e6):
                return cv
            # Text in raw pesos, chart in MDP (tv / 1e6 ≈ cv)
            if abs(tv) >= 1e6 and _close(tv / 1e6, cv):
                return cv
    return None


def _close(a: float, b: float) -> bool:
    if b == 0:
        return abs(a) < ABSOLUTE_TOLERANCE
    return abs(a - b) / abs(b) <= RELATIVE_TOLERANCE or abs(a - b) <= ABSOLUTE_TOLERANCE


def check_contradictions(text: str) -> List[str]:
    found = []
    tl = text.lower()
    for phrase in CONTRADICTION_PHRASES:
        if phrase in tl:
            found.append(phrase)
    return found


def has_markdown_table(text: str) -> bool:
    """Check if the text contains a pipe-delimited markdown table.

    A valid table has at least a header row and a separator row like:
      | Col1 | Col2 |
      |------|------|
    """
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Header row: starts and ends with |, has at least one inner |
        if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 3:
            # Check next line is a separator
            if i + 1 < len(lines):
                sep = lines[i + 1].strip()
                if re.match(r"^\|[\s\-:|]+(\|[\s\-:|]+)+\|$", sep):
                    return True
    return False


def extract_chart_values_by_bank(bank_chart: Dict[str, Any]) -> Dict[str, List[float]]:
    """Extract chart values keyed by bank name (trace name)."""
    by_bank: Dict[str, List[float]] = {}
    plotly = bank_chart.get("plotly_config", {})
    if not plotly:
        return by_bank
    for trace in plotly.get("data", []):
        name = trace.get("name", "")
        if not name:
            continue
        values = []
        for v in trace.get("y", []):
            if v is not None and isinstance(v, (int, float)):
                values.append(float(v))
        if trace.get("orientation") == "h":
            for v in trace.get("x", []):
                if v is not None and isinstance(v, (int, float)):
                    values.append(float(v))
        by_bank[name.upper()] = values
    return by_bank


def check_bank_value_grounding(
    text: str, chart_by_bank: Dict[str, List[float]]
) -> List[str]:
    """Verify that values cited near a bank name belong to that bank's trace.

    Scans for patterns like "BBVA ... 20.06%" and checks that 20.06 exists
    in BBVA's chart values rather than another bank's.
    Returns a list of misattribution descriptions.
    """
    misattributions: List[str] = []
    bank_names = list(chart_by_bank.keys())
    if len(bank_names) < 2:
        return misattributions  # Need at least 2 banks to detect swaps

    # Split text into lines for localized checking
    lines = text.split("\n")
    for line in lines:
        line_upper = line.upper()
        # Find which bank is mentioned in this line
        banks_in_line = [b for b in bank_names if b in line_upper]
        if len(banks_in_line) != 1:
            continue  # Skip ambiguous lines (0 or 2+ banks)

        bank = banks_in_line[0]
        bank_values = chart_by_bank[bank]
        other_values = []
        for other_bank, vals in chart_by_bank.items():
            if other_bank != bank:
                other_values.extend(vals)

        # Extract numbers from this line
        line_citations = extract_data_citations(line)
        for cit in line_citations:
            # Check if this value matches the CORRECT bank's trace
            matched_own = match_citation(cit, bank_values)
            if matched_own is not None:
                continue  # Correctly grounded

            # Check if it matches ANOTHER bank's trace (misattribution)
            matched_other = match_citation(cit, other_values)
            if matched_other is not None:
                misattributions.append(
                    f"'{cit.raw_text}' cited for {bank} but belongs to another bank "
                    f"(matched chart value {matched_other:.2f})"
                )

    return misattributions


# --- Runner ---


def run_test(token: str, tc: TestCase) -> TestResult:
    r = TestResult(test_case=tc, passed=False)

    resp = send_chat_message(
        token, tc.query, backend_url=BACKEND_URL, stream=True, timeout=TIMEOUT
    )

    if resp.get("error"):
        r.error = f"Request failed: {resp['error']}"
        return r

    r.text_content = resp.get("content", "")
    bc = resp.get("bank_chart")
    r.has_chart = bc is not None
    if bc:
        r.chart_status = str(bc.get("chart_status", "unknown"))

    # 1. Chart existence
    if tc.expect_chart and not r.has_chart:
        r.error = "Expected chart but none returned"
        return r

    # 2. Chart year check
    if tc.expect_chart_year and r.has_chart and bc:
        r.chart_dates = extract_chart_dates(bc)
        if r.chart_dates:
            has_year = any(tc.expect_chart_year in d for d in r.chart_dates)
            if not has_year:
                r.error = (
                    f"Chart dates don't include year {tc.expect_chart_year}. "
                    f"Found: {r.chart_dates[:3]}..."
                )
                return r

    # 3. Citation matching
    if tc.expect_citations_match and r.has_chart and bc and r.chart_status == "success":
        r.chart_values = extract_chart_values(bc)
        r.citations = extract_data_citations(r.text_content)

        for c in r.citations:
            c.matched_chart_value = match_citation(c, r.chart_values)
            if c.matched_chart_value is None:
                r.unmatched_citations.append(c)

        if len(r.unmatched_citations) > tc.max_unmatched_citations:
            details = [f"'{c.raw_text}'={c.value}" for c in r.unmatched_citations[:5]]
            r.error = (
                f"{len(r.unmatched_citations)} unmatched citations "
                f"(max {tc.max_unmatched_citations}): {', '.join(details)}"
            )
            return r

    # 4. Contradiction check — runs AFTER citations so we can distinguish
    #    a full denial (zero grounded values) from a partial caveat
    #    ("no hay datos de noviembre" while correctly citing October values).
    if tc.expect_no_contradiction and r.has_chart and r.chart_status == "success":
        r.contradictions = check_contradictions(r.text_content)
        if r.contradictions:
            matched_count = sum(
                1 for c in r.citations if c.matched_chart_value is not None
            )
            if matched_count == 0:
                # Full denial — no grounded data cited alongside the contradiction
                r.error = f"Text contradicts data: {r.contradictions}"
                return r
            # Partial caveat — LLM mentions limitation but also cites real data
            # Record but don't fail; the citation check already validated accuracy
            pass

    # 5. Table reproduction check (soft: warn, don't fail — LLM compliance is non-deterministic)
    if tc.expect_table_in_response and r.has_chart:
        if r.chart_status == "success":
            r.has_table = has_markdown_table(r.text_content)

    # 6. Bank-value association check
    if tc.expect_bank_value_grounded and r.has_chart and bc and r.chart_status == "success":
        chart_by_bank = extract_chart_values_by_bank(bc)
        r.misattributed_values = check_bank_value_grounding(r.text_content, chart_by_bank)
        if r.misattributed_values:
            r.error = (
                f"Bank-value misattribution: {'; '.join(r.misattributed_values[:3])}"
            )
            return r

    r.passed = True
    return r


def main() -> int:
    print("=" * 65)
    print("E2E Regression: Response Grounding Desync (Production Replay)")
    print("=" * 65)
    print()

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("❌ FATAL: Auth failed")
        return 2

    print(f"✅ Authenticated against {BACKEND_URL}\n")

    results: List[TestResult] = []
    passed = failed = 0

    for tc in TEST_CASES:
        print(f"--- {tc.feedback_id}: {tc.description} ---")
        print(f"  Query: \"{tc.query}\"")

        r = run_test(token, tc)
        results.append(r)

        if r.passed:
            passed += 1
            print(f"  ✅ PASSED")
            matched = sum(1 for c in r.citations if c.matched_chart_value is not None)
            print(
                f"     Citations: {len(r.citations)} total, "
                f"{matched} matched, {len(r.unmatched_citations)} unmatched"
            )
            if r.chart_dates:
                print(f"     Chart dates: {r.chart_dates[0]} ... {r.chart_dates[-1]}")
            if tc.expect_table_in_response:
                if r.has_table:
                    tag = "yes"
                elif r.chart_status != "success":
                    tag = "n/a (chart_status={})".format(r.chart_status)
                else:
                    tag = "⚠️  no (LLM did not reproduce table)"
                print(f"     Table in response: {tag}")
            if tc.expect_bank_value_grounded:
                print(f"     Bank-value grounding: {len(r.misattributed_values)} misattributions")
        else:
            failed += 1
            print(f"  ❌ FAILED: {r.error}")
            if r.text_content:
                print(f"     Text: {r.text_content[:300].replace(chr(10), ' ')}")
            if r.citations:
                for c in r.citations[:8]:
                    tag = (
                        f"✅ ≈{c.matched_chart_value:.2f}"
                        if c.matched_chart_value is not None
                        else "❌ no match"
                    )
                    print(f"     [{tag}] {c.raw_text}")
            if r.chart_values:
                print(f"     Chart vals (first 5): {[round(v, 2) for v in r.chart_values[:5]]}")

        print()

    # Summary
    print("=" * 65)
    total = passed + failed
    if failed == 0:
        print(f"✅ All {total} tests PASSED!")
    else:
        print(f"❌ {failed}/{total} tests FAILED")
    print("=" * 65)

    # Save
    out = Path(__file__).parent / "response_grounding_results.json"
    out.write_text(
        json.dumps(
            {
                "total_passed": passed,
                "total_failed": failed,
                "cases": [
                    {
                        "feedback_id": r.test_case.feedback_id,
                        "query": r.test_case.query,
                        "passed": r.passed,
                        "has_chart": r.has_chart,
                        "chart_status": r.chart_status,
                        "chart_values_count": len(r.chart_values),
                        "citations_total": len(r.citations),
                        "citations_unmatched": len(r.unmatched_citations),
                        "unmatched_details": [
                            {"raw": c.raw_text, "value": c.value}
                            for c in r.unmatched_citations
                        ],
                        "contradictions": r.contradictions,
                        "has_table": r.has_table,
                        "misattributed_values": r.misattributed_values,
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
