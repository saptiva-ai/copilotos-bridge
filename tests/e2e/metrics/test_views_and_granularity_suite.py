#!/usr/bin/env python3
"""
E2E Test Suite for Views and Granularity Validation

Tests for:
1. Different visualization types (evolution, ranking, YoY, comparison)
2. Different granularities (single bank, multi-bank, sistema, temporal)
3. Data unit validation (percentage vs absolute values)
4. Data correctness (values in expected ranges)
5. LLM response coherence (charts referenced only when present)

This suite validates the bank advisor returns correct data in correct units.

Reference: TASK-2026-01-27__metric-scaling-audit
"""

import os
import sys
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Add tests/ to path for shared helpers
sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")

# =============================================================================
# METRIC DEFINITIONS WITH EXPECTED RANGES
# =============================================================================

@dataclass
class MetricSpec:
    """Specification for a metric's expected behavior."""
    name: str
    column: str
    unit: str  # "%" or "MDP" or "x" (multiplier)
    min_value: float
    max_value: float
    typical_range: Tuple[float, float]
    is_ratio: bool = True  # True if percentage, False if absolute
    lower_is_better: bool = False
    publication_delay_months: int = 3


# Expected metrics with their correct units and ranges
METRIC_SPECS = {
    # Ratio metrics stored as decimal (need ×100 display)
    "imor": MetricSpec(
        name="IMOR",
        column="imor",
        unit="%",
        min_value=0,
        max_value=30,  # IMOR rarely exceeds 30%
        typical_range=(0, 10),
        lower_is_better=True,
        publication_delay_months=3,
    ),
    "pe_total": MetricSpec(
        name="Pérdida Esperada Total",
        column="pe_total",
        unit="%",
        min_value=0,
        max_value=50,
        typical_range=(0, 15),
        lower_is_better=True,
        publication_delay_months=5,
    ),
    "ct_etapa_1": MetricSpec(
        name="Cartera Etapa 1",
        column="ct_etapa_1",
        unit="%",
        min_value=0,
        max_value=100,
        typical_range=(70, 99),
        lower_is_better=False,  # Higher is better for performing
        publication_delay_months=5,
    ),
    "ct_etapa_3": MetricSpec(
        name="Cartera Etapa 3",
        column="ct_etapa_3",
        unit="%",
        min_value=0,
        max_value=30,
        typical_range=(0, 10),
        lower_is_better=True,  # Lower is better for non-performing
        publication_delay_months=5,
    ),
    # Ratio metrics stored as percentage (NO ×100 needed)
    "icap_total": MetricSpec(
        name="ICAP",
        column="icap_total",
        unit="%",
        min_value=8,  # Regulatory minimum is 10.5%, but some may be lower
        max_value=50,  # ICAP rarely exceeds 50%
        typical_range=(10, 30),
        lower_is_better=False,  # Higher is better
        publication_delay_months=3,
    ),
    "roe_12m": MetricSpec(
        name="ROE 12M",
        column="roe_12m",
        unit="%",
        min_value=-50,
        max_value=100,
        typical_range=(5, 40),
        lower_is_better=False,
        publication_delay_months=4,
    ),
    "roa_12m": MetricSpec(
        name="ROA 12M",
        column="roa_12m",
        unit="%",
        min_value=-20,
        max_value=20,
        typical_range=(0.5, 5),
        lower_is_better=False,
        publication_delay_months=4,
    ),
    "market_share_pct": MetricSpec(
        name="Market Share",
        column="market_share_pct",
        unit="%",
        min_value=0,
        max_value=100,
        typical_range=(0.1, 30),
        lower_is_better=False,
        publication_delay_months=3,
    ),
    # Coverage ratio (multiplier, not percentage)
    "icor": MetricSpec(
        name="ICOR",
        column="icor",
        unit="x",  # Multiplier (1.5x means 150% coverage)
        min_value=0,
        max_value=10,  # ICOR rarely exceeds 10x
        typical_range=(1, 3),
        is_ratio=False,
        lower_is_better=False,  # Higher coverage is better
        publication_delay_months=4,
    ),
    # Absolute values (MDP)
    "cartera_total": MetricSpec(
        name="Cartera Total",
        column="cartera_total",
        unit="MDP",
        min_value=0,
        max_value=10_000_000,  # Up to 10 trillion MDP
        typical_range=(1000, 1_000_000),
        is_ratio=False,
        lower_is_better=False,
        publication_delay_months=3,
    ),
    "cartera_vivienda_total": MetricSpec(
        name="Cartera Vivienda",
        column="cartera_vivienda_total",
        unit="MDP",
        min_value=0,
        max_value=2_000_000,
        typical_range=(100, 500_000),
        is_ratio=False,
        lower_is_better=False,
        publication_delay_months=3,
    ),
}


# =============================================================================
# TEST CASE DEFINITIONS
# =============================================================================

@dataclass
class TestQuery:
    """A single test query with expected validations."""
    id: str
    query: str
    expected_metric: str  # Key in METRIC_SPECS
    expected_type: str = "chart"  # "chart", "ranking", "clarification", "any"
    expected_banks: List[str] = field(default_factory=list)
    expected_view: str = "evolution"  # "evolution", "ranking", "yoy", "comparison"
    validate_units: bool = True
    validate_range: bool = True
    validate_freshness: bool = True  # Check data_freshness field
    description: str = ""


# Test queries organized by view type and granularity
TEST_QUERIES: List[TestQuery] = [
    # =========================================================================
    # EVOLUTION VIEW (Line Charts) - Single Bank
    # =========================================================================
    TestQuery(
        id="EVO-001",
        query="Dame el IMOR de INVEX",
        expected_metric="imor",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        description="Single bank IMOR evolution - should be percentage 0-30%",
    ),
    TestQuery(
        id="EVO-002",
        query="ICAP de INVEX últimos 12 meses",
        expected_metric="icap_total",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        description="ICAP should be percentage 10-50%, NOT multiplied by 100",
    ),
    TestQuery(
        id="EVO-003",
        query="Pérdida esperada de INVEX",
        expected_metric="pe_total",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        description="PE Total should be percentage 0-50%",
    ),
    TestQuery(
        id="EVO-004",
        query="ICOR de INVEX",
        expected_metric="icor",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        description="ICOR should be multiplier 0-10x, NOT percentage",
    ),
    TestQuery(
        id="EVO-005",
        query="Cartera total de INVEX",
        expected_metric="cartera_total",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        validate_units=True,
        description="Cartera total should be in MDP (millions)",
    ),
    TestQuery(
        id="EVO-006",
        query="Market share de INVEX",
        expected_metric="market_share_pct",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        description="Market share should be percentage 0-100%, stored as %",
    ),

    # =========================================================================
    # EVOLUTION VIEW - Multi-Bank Comparison
    # =========================================================================
    TestQuery(
        id="EVO-010",
        query="IMOR de INVEX vs BBVA",
        expected_metric="imor",
        expected_type="chart",
        expected_banks=["INVEX", "BBVA"],
        expected_view="evolution",
        description="Multi-bank IMOR comparison",
    ),
    TestQuery(
        id="EVO-011",
        query="Compara el ICAP de INVEX y Santander",
        expected_metric="icap_total",
        expected_type="chart",
        expected_banks=["INVEX", "SANTANDER"],
        expected_view="evolution",
        description="Multi-bank ICAP - should be percentage not ×100",
    ),
    TestQuery(
        id="EVO-012",
        query="ICAP de INVEX, BBVA y Banorte últimos 6 meses",
        expected_metric="icap_total",
        expected_type="chart",
        expected_banks=["INVEX", "BBVA", "BANORTE"],
        expected_view="evolution",
        description="Multi-bank ICAP with temporal range",
    ),

    # =========================================================================
    # EVOLUTION VIEW - Sistema
    # =========================================================================
    TestQuery(
        id="EVO-020",
        query="IMOR del sistema bancario",
        expected_metric="imor",
        expected_type="chart",
        expected_banks=["SISTEMA"],
        expected_view="evolution",
        description="Sistema IMOR evolution",
    ),
    TestQuery(
        id="EVO-021",
        query="ICAP del sistema",
        expected_metric="icap_total",
        expected_type="chart",
        expected_banks=["SISTEMA"],
        expected_view="evolution",
        description="Sistema ICAP - should be ~15-20%",
    ),
    TestQuery(
        id="EVO-022",
        query="IMOR de INVEX vs Sistema",
        expected_metric="imor",
        expected_type="chart",
        expected_banks=["INVEX", "SISTEMA"],
        expected_view="evolution",
        description="Bank vs Sistema comparison",
    ),

    # =========================================================================
    # RANKING VIEW (Bar Charts)
    # =========================================================================
    TestQuery(
        id="RANK-001",
        query="Ranking de IMOR de todos los bancos",
        expected_metric="imor",
        expected_type="chart",
        expected_banks=[],  # All banks
        expected_view="ranking",
        description="IMOR ranking - all banks",
    ),
    TestQuery(
        id="RANK-002",
        query="¿Cuáles bancos tienen mejor ICAP?",
        expected_metric="icap_total",
        expected_type="chart",
        expected_banks=[],
        expected_view="ranking",
        description="ICAP ranking - should show % values 10-50%",
    ),
    TestQuery(
        id="RANK-003",
        query="Top 10 bancos por cartera total",
        expected_metric="cartera_total",
        expected_type="chart",
        expected_banks=[],
        expected_view="ranking",
        description="Cartera total ranking - MDP values",
    ),
    TestQuery(
        id="RANK-004",
        query="Ranking de market share bancario",
        expected_metric="market_share_pct",
        expected_type="chart",
        expected_banks=[],
        expected_view="ranking",
        description="Market share ranking - percentage values",
    ),
    TestQuery(
        id="RANK-005",
        query="¿Cuál banco tiene mejor ROE?",
        expected_metric="roe_12m",
        expected_type="chart",
        expected_banks=[],
        expected_view="ranking",
        description="ROE ranking - percentage values",
    ),

    # =========================================================================
    # TEMPORAL GRANULARITY
    # =========================================================================
    TestQuery(
        id="TEMP-001",
        query="IMOR de INVEX en 2024",
        expected_metric="imor",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        description="Year-specific query",
    ),
    TestQuery(
        id="TEMP-002",
        query="ICAP de INVEX últimos 3 meses",
        expected_metric="icap_total",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        description="Recent months query",
    ),
    TestQuery(
        id="TEMP-003",
        query="IMOR de INVEX de enero a junio 2024",
        expected_metric="imor",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        description="Date range query",
    ),

    # =========================================================================
    # IFRS9 METRICS (PE, CT) - Higher publication delay
    # =========================================================================
    TestQuery(
        id="IFRS-001",
        query="Pérdida esperada total de INVEX",
        expected_metric="pe_total",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        validate_freshness=True,
        description="PE Total - should show ~5 month delay in freshness",
    ),
    TestQuery(
        id="IFRS-002",
        query="Cartera etapa 1 de INVEX",
        expected_metric="ct_etapa_1",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        validate_freshness=True,
        description="CT Etapa 1 - should be high % (80-99%)",
    ),
    TestQuery(
        id="IFRS-003",
        query="Cartera etapa 3 de INVEX",
        expected_metric="ct_etapa_3",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        validate_freshness=True,
        description="CT Etapa 3 - should be low % (0-10%)",
    ),

    # =========================================================================
    # EDGE CASES
    # =========================================================================
    TestQuery(
        id="EDGE-001",
        query="ROA de INVEX",
        expected_metric="roa_12m",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        description="ROA - should be percentage 0-5% typically",
    ),
    TestQuery(
        id="EDGE-002",
        query="Cartera vivienda de INVEX",
        expected_metric="cartera_vivienda_total",
        expected_type="chart",
        expected_banks=["INVEX"],
        expected_view="evolution",
        description="Cartera vivienda - MDP values",
    ),
]


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def extract_chart_values(chart: Dict) -> List[float]:
    """Extract all numeric values from chart traces."""
    values = []
    plotly_config = chart.get("plotly_config", {})
    traces = plotly_config.get("data", [])

    for trace in traces:
        # Handle both horizontal and vertical charts
        orientation = trace.get("orientation", "v")
        vals = trace.get("x" if orientation == "h" else "y", [])

        for v in vals:
            if isinstance(v, (int, float)) and v is not None and v == v:  # Not NaN
                values.append(float(v))

    return values


def validate_unit_range(
    chart: Dict,
    metric_spec: MetricSpec
) -> Tuple[bool, List[str]]:
    """
    Validate that chart values are in the expected unit range.

    Returns: (is_valid, list_of_issues)
    """
    issues = []
    values = extract_chart_values(chart)

    if not values:
        return False, ["No numeric values found in chart"]

    # Check value ranges
    min_val = min(values)
    max_val = max(values)
    avg_val = sum(values) / len(values)

    # Check if values are in expected range
    # Use absolute tolerance (-0.01) when min_value is 0 to handle floating-point artifacts
    lower_bound = metric_spec.min_value * 0.8 if metric_spec.min_value != 0 else -0.01
    if min_val < lower_bound:
        issues.append(
            f"Values too low: min={min_val:.2f}, expected >={metric_spec.min_value}"
        )

    if max_val > metric_spec.max_value * 1.5:  # Allow 50% tolerance
        issues.append(
            f"Values too high: max={max_val:.2f}, expected <={metric_spec.max_value}"
        )

    # Check if values are in typical range (warning only)
    typ_min, typ_max = metric_spec.typical_range
    if avg_val < typ_min * 0.5 or avg_val > typ_max * 2:
        issues.append(
            f"WARNING: Avg value {avg_val:.2f} outside typical range {typ_min}-{typ_max}"
        )

    # Detect wrong scaling (×100 error)
    # If metric should be 0-30% but we see 0-3000%, it's been scaled wrongly
    if metric_spec.unit == "%" and max_val > 100:
        issues.append(
            f"SCALING ERROR: Values suggest wrong ×100 scaling. "
            f"Max value {max_val:.2f}% exceeds 100%"
        )

    return len([i for i in issues if "SCALING ERROR" in i or "too" in i]) == 0, issues


def validate_data_freshness(chart: Dict, metric_spec: MetricSpec) -> Tuple[bool, List[str]]:
    """
    Validate that data_freshness field is present and correct.

    Returns: (is_valid, list_of_issues)
    """
    issues = []

    freshness = chart.get("data_freshness")
    if not freshness:
        # Freshness is optional but expected for IFRS9 metrics
        if metric_spec.publication_delay_months >= 5:
            issues.append(
                f"Missing data_freshness for metric with {metric_spec.publication_delay_months} month delay"
            )
        return True, issues  # Not a failure, just a warning

    # Check expected delay matches
    actual_delay = freshness.get("publication_delay_months", 0)
    if actual_delay != metric_spec.publication_delay_months:
        issues.append(
            f"Freshness delay mismatch: got {actual_delay}, expected {metric_spec.publication_delay_months}"
        )

    # Check that Spanish note is present
    if not freshness.get("note_es"):
        issues.append("Missing Spanish freshness note (note_es)")

    return len(issues) == 0, issues


def validate_response_coherence(response: Dict) -> Tuple[bool, List[str]]:
    """
    Validate LLM response doesn't reference charts that don't exist.

    Returns: (is_valid, list_of_issues)
    """
    issues = []

    content = response.get("content", "")
    has_chart = response.get("bank_chart") is not None

    # Check for chart references in text
    chart_phrases = [
        "como puedes ver en la gráfica",
        "en la gráfica",
        "en el gráfico",
        "la gráfica muestra",
        "el gráfico muestra",
        "como se observa",
        "puedes observar",
    ]

    for phrase in chart_phrases:
        if phrase.lower() in content.lower() and not has_chart:
            issues.append(
                f"LLM references chart ('{phrase}') but no chart was generated"
            )

    return len(issues) == 0, issues


# =============================================================================
# TEST RUNNER
# =============================================================================

def run_test(test: TestQuery, token: str) -> Dict[str, Any]:
    """Run a single test query and validate results."""
    result = {
        "id": test.id,
        "query": test.query,
        "description": test.description,
        "passed": True,
        "issues": [],
        "warnings": [],
        "details": {},
    }

    try:
        # Send request
        response = send_chat_message(
            token,
            test.query,
            backend_url=BACKEND_URL,
            model="Saptiva Turbo",
            timeout=90,
        )

        if response.get("error"):
            result["passed"] = False
            result["issues"].append(f"API Error: {response['error']}")
            return result

        chart = response.get("bank_chart")
        clarification = response.get("clarification") or response.get("bank_clarification")

        # 1. Check response type
        if test.expected_type == "chart" and not chart:
            if clarification:
                result["issues"].append("Got clarification instead of chart")
            else:
                result["issues"].append("No chart received")
            result["passed"] = False
            return result

        if not chart:
            # If we expected clarification or any, this is OK
            return result

        # Save chart details
        result["details"]["metric_name"] = chart.get("metric_name")
        result["details"]["bank_names"] = chart.get("bank_names", [])
        result["details"]["data_as_of"] = chart.get("data_as_of")
        result["details"]["has_freshness"] = chart.get("data_freshness") is not None

        # 2. Validate metric mapping
        metric_name = (chart.get("metric_name") or "").lower().replace(" ", "_")
        expected_spec = METRIC_SPECS.get(test.expected_metric)

        if expected_spec:
            # Check metric name contains expected keywords
            expected_keywords = [test.expected_metric, expected_spec.name.lower()]
            found = any(kw.lower() in metric_name for kw in expected_keywords)
            if not found:
                result["issues"].append(
                    f"Metric mismatch: expected '{test.expected_metric}', got '{metric_name}'"
                )

        # 3. Validate banks
        actual_banks = [b.upper() for b in chart.get("bank_names", [])]
        for expected_bank in test.expected_banks:
            if expected_bank.upper() not in actual_banks:
                result["issues"].append(f"Missing bank: {expected_bank}")

        # 4. Validate unit ranges
        if test.validate_units and expected_spec:
            valid, unit_issues = validate_unit_range(chart, expected_spec)
            for issue in unit_issues:
                if "WARNING" in issue:
                    result["warnings"].append(issue)
                else:
                    result["issues"].append(issue)

        # 5. Validate data freshness
        if test.validate_freshness and expected_spec:
            valid, freshness_issues = validate_data_freshness(chart, expected_spec)
            for issue in freshness_issues:
                result["warnings"].append(issue)

        # 6. Validate LLM coherence
        valid, coherence_issues = validate_response_coherence(response)
        result["issues"].extend(coherence_issues)

        # Extract sample values for reporting
        values = extract_chart_values(chart)
        if values:
            result["details"]["value_range"] = {
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "avg": round(sum(values) / len(values), 2),
                "count": len(values),
            }

        # Determine pass/fail
        result["passed"] = len(result["issues"]) == 0

    except Exception as e:
        result["passed"] = False
        result["issues"].append(f"Exception: {str(e)}")

    return result


def main():
    """Run all tests and report results."""
    print("=" * 70)
    print("VIEWS AND GRANULARITY TEST SUITE")
    print("Validating chart data units, ranges, and response coherence")
    print("=" * 70)

    token = get_auth_token()
    if not token:
        print("❌ FATAL: Authentication failed")
        sys.exit(2)

    print(f"\nTotal tests: {len(TEST_QUERIES)}\n")

    results = []
    passed = 0
    failed = 0

    # Group tests by category
    categories = {}
    for test in TEST_QUERIES:
        prefix = test.id.split("-")[0]
        if prefix not in categories:
            categories[prefix] = []
        categories[prefix].append(test)

    for category, tests in categories.items():
        print(f"\n{'─' * 60}")
        print(f"Category: {category}")
        print("─" * 60)

        for test in tests:
            print(f"\n[{test.id}] {test.description}")
            print(f"  Query: {test.query}")

            result = run_test(test, token)
            results.append(result)

            if result["passed"]:
                print(f"  ✅ PASS")
                passed += 1
            else:
                print(f"  ❌ FAIL")
                failed += 1
                for issue in result["issues"]:
                    print(f"     ⚠ {issue}")

            # Show details
            if result.get("details", {}).get("value_range"):
                vr = result["details"]["value_range"]
                print(f"  📊 Values: min={vr['min']}, max={vr['max']}, avg={vr['avg']} ({vr['count']} points)")

            # Show warnings
            for warning in result.get("warnings", []):
                print(f"     ℹ {warning}")

            time.sleep(0.5)  # Rate limiting

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total:  {len(TEST_QUERIES)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Rate:   {passed/len(TEST_QUERIES)*100:.1f}%")

    if failed > 0:
        print("\nFailed Tests:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['id']}: {r['description']}")
                for issue in r["issues"]:
                    print(f"       {issue}")

    # Save results
    output_file = Path(__file__).parent / "views_granularity_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": len(TEST_QUERIES),
            "passed": passed,
            "failed": failed,
            "results": results,
        }, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
