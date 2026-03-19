#!/usr/bin/env python3
"""
E2E Regression — Multi-Bank Hallucination Guard

Validates the 4-layer defense against multi-bank hallucinations:
  Layer 1: metricas_financieras handler rejects multi-bank queries
  Layer 2: Entity extraction detects all bank names (expanded aliases)
  Layer 3: Bank coverage manifest prevents LLM from fabricating data
  Layer 4: Truth gating appends correction if hallucination slips through

Scenarios:
  A. 10-bank query (original prod bug) — should return multi-bank chart
  B. 2-bank comparison — should return overlay chart, no fabrication
  C. Alias-heavy query (Banamex, Scotia, Bancomer) — aliases should resolve
  D. Single bank baseline — should work normally with PROHIBIDO rule
  E. Bank not in CNBV — should refuse gracefully, not hallucinate

Usage:
    python tests/e2e/regression/test_multibank_hallucination_guard.py

Requires:
    - Backend running at TEST_BACKEND_URL (default: http://localhost:8000)
    - Valid test credentials (TEST_AUTH_USER / TEST_AUTH_PASS)
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "90"))

# Indicators of LLM fabrication
FABRICATION_PHRASES = [
    "estimado basado en tendencia",
    "estimado",
    "proyectado",
    "aproximado basado en",
    "no cuento con datos exactos",
    "basándome en datos públicos",
]

# Round numbers that suggest hallucination (exact multiples of 100M)
SUSPICIOUS_ROUND_PATTERN = re.compile(r"\$[\d,]*[05]00[,.]000[,.]000")

# Truth gating correction indicator
CORRECTION_MARKER = "Corrección de consistencia de datos"


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _extract_trace_names(resp: Dict[str, Any]) -> List[str]:
    """Extract bank/trace names from chart data."""
    bc = resp.get("bank_chart")
    if not bc:
        return []
    names = bc.get("bank_names", [])
    if names:
        return [n.upper() for n in names]
    plotly = bc.get("plotly_config", {})
    traces = plotly.get("data", [])
    return [t.get("name", "").upper() for t in traces if t.get("name")]


def _has_chart(resp: Dict[str, Any]) -> bool:
    """Check if response includes a chart."""
    bc = resp.get("bank_chart")
    return bc is not None and bc.get("chart_status") == "success"


def _count_fabrication_phrases(content: str) -> List[str]:
    """Return list of fabrication phrases found in content."""
    content_lower = content.lower()
    return [p for p in FABRICATION_PHRASES if p in content_lower]


def _count_round_values(content: str) -> List[str]:
    """Return suspiciously round monetary values found in content."""
    return SUSPICIOUS_ROUND_PATTERN.findall(content)


@dataclass
class TestCase:
    """A single E2E test case."""

    id: str
    query: str
    validate: Callable[[Dict[str, Any]], Tuple[bool, str]]
    description: str = ""


@dataclass
class TestResult:
    """Result of a single test case."""

    case: TestCase
    passed: bool
    detail: str
    chart_traces: List[str] = field(default_factory=list)
    has_correction: bool = False


# ══════════════════════════════════════════════════════════════════════════════
# Scenario A: 10-bank query (original prod bug)
# ══════════════════════════════════════════════════════════════════════════════


def _validate_10bank_query(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    10 banks requested. Chart should have multiple traces.
    LLM should NOT fabricate data for banks not in the chart.

    This is the EXACT scenario from the 2026-02-11 prod incident where
    metricas_financieras_handler only processed INVEX (first bank) and
    the LLM hallucinated data for the other 9.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    content = resp.get("content") or ""
    issues = []

    # Check for fabrication indicators
    fabrications = _count_fabrication_phrases(content)
    if fabrications:
        issues.append(f"FABRICATION: found phrases {fabrications}")

    # Check for suspicious round values (3+ suggests systematic fabrication)
    round_vals = _count_round_values(content)
    if len(round_vals) >= 3:
        issues.append(
            f"FABRICATION: {len(round_vals)} suspiciously round values: "
            f"{round_vals[:3]}"
        )

    # Chart should exist
    if not _has_chart(resp):
        issues.append("CHART_MISSING: no chart for 10-bank query")
    else:
        traces = _extract_trace_names(resp)
        if len(traces) < 2:
            issues.append(
                f"SINGLE_BANK_ONLY: chart has {len(traces)} traces {traces} "
                f"but 10 banks were requested — handler guard may have failed"
            )

    # Check for truth gating correction (layer 4 safety net)
    has_correction = CORRECTION_MARKER in content
    if has_correction:
        # Correction is acceptable but notable — means layer 3 didn't fully prevent
        issues.append(
            "PARTIAL_FIX: truth gating correction appended (bank manifest "
            "didn't fully prevent hallucination)"
        )

    if issues:
        # Distinguish hard failures from soft warnings
        hard_failures = [i for i in issues if not i.startswith("PARTIAL_FIX")]
        if hard_failures:
            return False, " | ".join(issues)
        return True, f"PASSED with warnings: {' | '.join(issues)}"

    traces = _extract_trace_names(resp)
    return True, f"10-bank query OK: {len(traces)} traces — {traces[:5]}..."


# ══════════════════════════════════════════════════════════════════════════════
# Scenario B: 2-bank comparison
# ══════════════════════════════════════════════════════════════════════════════


def _validate_2bank_comparison(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Simple 2-bank comparison. Both banks should appear in chart.
    No fabrication expected since handler supports this case.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    content = resp.get("content") or ""
    issues = []

    fabrications = _count_fabrication_phrases(content)
    if fabrications:
        issues.append(f"FABRICATION: {fabrications}")

    if not _has_chart(resp):
        issues.append("CHART_MISSING: no chart for 2-bank comparison")
    else:
        traces = _extract_trace_names(resp)
        has_invex = any("INVEX" in t for t in traces)
        has_bbva = any("BBVA" in t for t in traces)
        if not has_invex or not has_bbva:
            issues.append(f"INCOMPLETE_CHART: expected INVEX + BBVA, got {traces}")

    if issues:
        return False, " | ".join(issues)

    traces = _extract_trace_names(resp)
    return True, f"2-bank comparison OK: {traces}"


# ══════════════════════════════════════════════════════════════════════════════
# Scenario C: Alias-heavy query
# ══════════════════════════════════════════════════════════════════════════════


def _validate_alias_resolution(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Query uses aliases: Banamex (→CITIBANAMEX), Scotia (→SCOTIABANK),
    Bancomer (→BBVA). All should resolve to canonical names in the chart.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    content = resp.get("content") or ""
    issues = []

    fabrications = _count_fabrication_phrases(content)
    if fabrications:
        issues.append(f"FABRICATION: {fabrications}")

    if not _has_chart(resp):
        issues.append("CHART_MISSING: no chart for alias query")
    else:
        traces = _extract_trace_names(resp)
        # Check canonical names resolved
        expected_canonical = {"CITIBANAMEX", "SCOTIABANK", "BBVA"}
        found_canonical = {t for t in traces if t in expected_canonical}
        missing = expected_canonical - found_canonical
        if missing:
            issues.append(f"ALIAS_MISS: expected {missing} in traces but got {traces}")

    # Should NOT contain rejection of aliases
    content_lower = content.lower()
    if "no tenemos datos" in content_lower and "banamex" in content_lower:
        issues.append(
            "ALIAS_REJECTED: Banamex rejected instead of resolving to CITIBANAMEX"
        )

    if issues:
        return False, " | ".join(issues)

    traces = _extract_trace_names(resp)
    return True, f"Alias resolution OK: {traces}"


# ══════════════════════════════════════════════════════════════════════════════
# Scenario D: Single bank baseline
# ══════════════════════════════════════════════════════════════════════════════


def _validate_single_bank(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Standard single-bank query. Should work normally with full PROHIBIDO rule.
    This verifies we didn't break the happy path while fixing multi-bank.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    if not _has_chart(resp):
        return False, "CHART_MISSING: no chart for single bank IMOR query"

    traces = _extract_trace_names(resp)
    if not any("INVEX" in t for t in traces):
        return False, f"WRONG_BANK: expected INVEX in traces, got {traces}"

    content = resp.get("content") or ""
    # Single bank should NOT trigger bank coverage manifest
    if "Cobertura de Bancos" in content:
        return (
            False,
            "FALSE_MANIFEST: bank coverage manifest triggered for single-bank query",
        )

    return True, f"Single bank baseline OK: {traces}"


# ══════════════════════════════════════════════════════════════════════════════
# Scenario E: Non-existent bank — graceful refusal
# ══════════════════════════════════════════════════════════════════════════════


def _validate_nonexistent_bank(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Query asks for 'Banco Imaginario' which doesn't exist.
    System should refuse gracefully, NOT hallucinate data.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    content = (resp.get("content") or "").lower()
    issues = []

    # Should NOT produce chart data for a non-existent bank
    if _has_chart(resp):
        traces = _extract_trace_names(resp)
        if any("IMAGINARIO" in t for t in traces):
            issues.append("HALLUCINATION: chart has traces for non-existent bank")

    # Should NOT fabricate numeric values
    fabrications = _count_fabrication_phrases(content)
    if fabrications:
        issues.append(f"FABRICATION: {fabrications}")

    # Should indicate the bank isn't in the database
    # (either via universe validation or LLM response)
    refusal_indicators = [
        "no tenemos datos",
        "no existe",
        "no encontr",
        "no está disponible",
        "no se encuentra",
        "quisiste decir",
    ]
    has_refusal = any(ind in content for ind in refusal_indicators)
    if not has_refusal:
        # If no explicit refusal AND there's numeric data, likely hallucinated
        has_numbers = bool(re.search(r"\d{3,}", content))
        if has_numbers:
            issues.append(
                "NO_REFUSAL: non-existent bank query got numeric data "
                "without refusal — possible hallucination"
            )

    if issues:
        return False, " | ".join(issues)

    return True, "Non-existent bank gracefully refused"


# ══════════════════════════════════════════════════════════════════════════════
# Scenario F: Multi-bank with partial data — manifest check
# ══════════════════════════════════════════════════════════════════════════════


def _validate_partial_coverage_honest(resp: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Query asks for 5 banks. If chart only covers some, the response
    should honestly state which banks have data and which don't.
    It should NOT fabricate data for uncovered banks.
    """
    if resp.get("error"):
        return False, f"Request error: {resp['error']}"

    content = resp.get("content") or ""
    content_lower = content.lower()
    issues = []

    # Check for fabrication
    fabrications = _count_fabrication_phrases(content)
    if fabrications:
        issues.append(f"FABRICATION: {fabrications}")

    round_vals = _count_round_values(content)
    if len(round_vals) >= 3:
        issues.append(f"ROUND_VALUES: {len(round_vals)} suspicious values")

    # If there's a chart, check trace count
    if _has_chart(resp):
        traces = _extract_trace_names(resp)
        # We asked for 5 banks — if chart has fewer, the response should mention it
        if len(traces) < 5:
            # Response should indicate partial coverage
            honesty_markers = [
                "solo",
                "únicamente",
                "no se encontraron",
                "no tenemos datos",
                "parcial",
                "no disponible",
                "faltantes",
            ]
            is_honest = any(m in content_lower for m in honesty_markers)
            if not is_honest:
                issues.append(
                    f"SILENT_GAP: chart has {len(traces)} of 5 requested banks "
                    f"but response doesn't mention missing banks"
                )

    if issues:
        return False, " | ".join(issues)

    traces = _extract_trace_names(resp)
    return True, f"Partial coverage handled honestly: {len(traces)} traces"


# ══════════════════════════════════════════════════════════════════════════════
# Test Case Definitions
# ══════════════════════════════════════════════════════════════════════════════


TESTS: List[TestCase] = [
    TestCase(
        id="MBH-A",
        query=(
            "Dame la cartera total de INVEX, BBVA, BANORTE, SANTANDER, HSBC, "
            "SCOTIABANK, CITIBANAMEX, INBURSA, BANCO AZTECA y BANREGIO "
            "en los últimos 12 meses"
        ),
        validate=_validate_10bank_query,
        description=(
            "10-bank query — exact scenario from prod bug 2026-02-11. "
            "metricas_financieras used to only process first bank."
        ),
    ),
    TestCase(
        id="MBH-B",
        query="Compara la cartera comercial de INVEX vs BBVA últimos 12 meses",
        validate=_validate_2bank_comparison,
        description="2-bank comparison — should produce overlay chart.",
    ),
    TestCase(
        id="MBH-C",
        query=("Compara el IMOR de Banamex, Scotia y Bancomer en los últimos 6 meses"),
        validate=_validate_alias_resolution,
        description=(
            "Alias-heavy query: Banamex→CITIBANAMEX, Scotia→SCOTIABANK, "
            "Bancomer→BBVA. All should resolve."
        ),
    ),
    TestCase(
        id="MBH-D",
        query="Muéstrame el IMOR de INVEX en los últimos 12 meses",
        validate=_validate_single_bank,
        description="Single-bank baseline — verifies happy path not broken.",
    ),
    TestCase(
        id="MBH-E",
        query="¿Cuál es la cartera total de Banco Imaginario?",
        validate=_validate_nonexistent_bank,
        description="Non-existent bank — should refuse, not hallucinate.",
    ),
    TestCase(
        id="MBH-F",
        query=(
            "Dame la cartera total de INVEX, MULTIVA, BANCREA, "
            "SABADELL y BANSÍ en los últimos 6 meses"
        ),
        validate=_validate_partial_coverage_honest,
        description=(
            "5 medium banks — if chart covers partial set, "
            "response must be honest about missing banks."
        ),
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════


def run_tests(token: str) -> List[TestResult]:
    """Run all test cases as independent queries (no session continuity)."""
    results: List[TestResult] = []

    for i, case in enumerate(TESTS):
        print(f"\n  [{case.id}] ({i + 1}/{len(TESTS)}) {case.description}")
        print(f'  Query: "{case.query[:80]}{"..." if len(case.query) > 80 else ""}"')

        resp = send_chat_message(
            token,
            case.query,
            backend_url=BACKEND_URL,
            timeout=TIMEOUT,
        )

        content = resp.get("content", "")
        passed, detail = case.validate(resp)
        traces = _extract_trace_names(resp)
        has_correction = CORRECTION_MARKER in content

        result = TestResult(
            case=case,
            passed=passed,
            detail=detail,
            chart_traces=traces,
            has_correction=has_correction,
        )
        results.append(result)

        tag = "PASSED" if passed else "FAILED"
        print(f"  {tag}: {detail}")
        if traces:
            print(f"  Chart: {len(traces)} traces — {traces[:5]}")
        if has_correction:
            print(f"  Note: truth gating correction was appended")
        if not passed and content:
            print(f"  Content: {content[:200].replace(chr(10), ' ')}")

    return results


def main() -> int:
    print("=" * 70)
    print("E2E Regression — Multi-Bank Hallucination Guard")
    print("Defense layers: handler guard + aliases + manifest + truth gating")
    print("=" * 70)

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FATAL: Auth failed")
        return 2

    print(f"Authenticated against {BACKEND_URL}")

    results = run_tests(token)

    # Summary
    print(f"\n\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}\n")

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    corrections = sum(1 for r in results if r.has_correction)

    for r in results:
        tag = "OK  " if r.passed else "FAIL"
        print(f"  [{tag}] {r.case.id}: {r.detail[:70]}")

    print(f"\n  Passed: {passed}/{passed + failed}")
    if corrections:
        print(f"  Truth gating corrections triggered: {corrections}")

    # Save results
    out = Path(__file__).parent / "multibank_hallucination_guard_results.json"
    out.write_text(
        json.dumps(
            {
                "test": "multibank_hallucination_guard",
                "total_passed": passed,
                "total_failed": failed,
                "truth_corrections": corrections,
                "cases": [
                    {
                        "id": r.case.id,
                        "query": r.case.query,
                        "passed": r.passed,
                        "detail": r.detail,
                        "chart_traces": r.chart_traces,
                        "has_correction": r.has_correction,
                    }
                    for r in results
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"\n  Results saved: {out}")

    print(f"\n{'=' * 70}")
    if failed == 0:
        print(f"ALL {passed} TESTS PASSED!")
    else:
        print(f"{passed} passed, {failed} failed out of {passed + failed}")
    print(f"{'=' * 70}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
