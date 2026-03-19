#!/usr/bin/env python3
"""
E2E Test Suite for Materialized Views Coverage

Tests that queries correctly route to and retrieve data from
all available materialized views in the bank-advisor system.

Materialized Views Tested:
1. bank_mv_ranking_cartera_mensual - Ranking queries
2. bank_mv_evolucion_cartera_banco - Evolution/timeline queries
3. bank_mv_comparativa_bancos - Multi-bank comparison
4. bank_mv_cartera_por_estado - Geographic distribution
5. bank_mv_resumen_sistema - System totals
6. bank_mv_cartera_por_actividad - By economic activity
7. bank_mv_cartera_por_tamano - By company size (PyMEs)
8. bank_mv_cartera_por_destino - By credit purpose
9. bank_mv_vivienda_por_producto - By mortgage product
10. bank_mv_vivienda_por_perfil - By demographic profile

Created: 2026-01-27
Reference: Migrations 034, 047
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
# TEST CASE DEFINITIONS
# =============================================================================

@dataclass
class MVTestCase:
    """Test case for a materialized view query."""
    id: str
    mv_name: str  # Target materialized view
    query: str
    description: str
    expected_type: str = "chart"  # "chart", "clarification", "any"
    expected_keywords: List[str] = field(default_factory=list)  # Keywords in response
    min_data_points: int = 1
    validate_has_data: bool = True


# Test cases organized by materialized view
MV_TEST_CASES: List[MVTestCase] = [
    # =========================================================================
    # 1. bank_mv_ranking_cartera_mensual - Ranking Queries
    # =========================================================================
    MVTestCase(
        id="MV-RANK-001",
        mv_name="bank_mv_ranking_cartera_mensual",
        query="Dame el ranking de bancos por cartera total",
        description="Basic ranking query",
        expected_type="chart",
        expected_keywords=["ranking", "cartera"],
        min_data_points=5,
    ),
    MVTestCase(
        id="MV-RANK-002",
        mv_name="bank_mv_ranking_cartera_mensual",
        query="Top 10 bancos por IMOR",
        description="Top N ranking by IMOR",
        expected_type="chart",
        expected_keywords=["imor"],
        min_data_points=5,
    ),
    MVTestCase(
        id="MV-RANK-003",
        mv_name="bank_mv_ranking_cartera_mensual",
        query="¿Qué posición tiene INVEX en el ranking de cartera?",
        description="Position query for specific bank",
        expected_type="any",  # Could be chart or text response
        expected_keywords=["invex"],
    ),

    # =========================================================================
    # 2. bank_mv_evolucion_cartera_banco - Evolution/Timeline Queries
    # =========================================================================
    MVTestCase(
        id="MV-EVO-001",
        mv_name="bank_mv_evolucion_cartera_banco",
        query="Dame la evolución del IMOR de INVEX",
        description="Single bank IMOR evolution",
        expected_type="chart",
        expected_keywords=["imor", "invex"],
        min_data_points=10,
    ),
    MVTestCase(
        id="MV-EVO-002",
        mv_name="bank_mv_evolucion_cartera_banco",
        query="ICAP de INVEX últimos 12 meses",
        description="ICAP with temporal range",
        expected_type="chart",
        expected_keywords=["icap"],
        min_data_points=10,
    ),
    MVTestCase(
        id="MV-EVO-003",
        mv_name="bank_mv_evolucion_cartera_banco",
        query="Cartera total de BBVA desde 2023",
        description="Cartera with year filter",
        expected_type="chart",
        expected_keywords=["cartera", "bbva"],
        min_data_points=10,
    ),
    MVTestCase(
        id="MV-EVO-004",
        mv_name="bank_mv_evolucion_cartera_banco",
        query="Pérdida esperada de INVEX histórico",
        description="PE Total evolution",
        expected_type="chart",
        expected_keywords=["pérdida", "esperada"],
        min_data_points=10,
    ),

    # =========================================================================
    # 3. bank_mv_comparativa_bancos - Multi-Bank Comparison
    # =========================================================================
    MVTestCase(
        id="MV-COMP-001",
        mv_name="bank_mv_comparativa_bancos",
        query="Compara IMOR de INVEX vs BBVA",
        description="Two-bank IMOR comparison",
        expected_type="chart",
        expected_keywords=["imor"],
        min_data_points=2,
    ),
    MVTestCase(
        id="MV-COMP-002",
        mv_name="bank_mv_comparativa_bancos",
        query="ICAP de INVEX, BBVA y Banorte",
        description="Three-bank ICAP comparison",
        expected_type="chart",
        expected_keywords=["icap"],
        min_data_points=3,
    ),
    MVTestCase(
        id="MV-COMP-003",
        mv_name="bank_mv_comparativa_bancos",
        query="Compara la cartera comercial de los 5 principales bancos",
        description="Top 5 banks comparison",
        expected_type="chart",
        expected_keywords=["cartera", "comercial"],
        min_data_points=5,
    ),

    # =========================================================================
    # 4. bank_mv_cartera_por_estado - Geographic Distribution
    # =========================================================================
    MVTestCase(
        id="MV-GEO-001",
        mv_name="bank_mv_cartera_por_estado",
        query="Cartera de vivienda por estado",
        description="Vivienda by state",
        expected_type="any",  # May need clarification for bank
        expected_keywords=["estado", "vivienda"],
    ),
    MVTestCase(
        id="MV-GEO-002",
        mv_name="bank_mv_cartera_por_estado",
        query="¿En qué estados tiene más cartera INVEX?",
        description="Bank's geographic distribution",
        expected_type="any",
        expected_keywords=["estado"],
    ),
    MVTestCase(
        id="MV-GEO-003",
        mv_name="bank_mv_cartera_por_estado",
        query="Cartera hipotecaria de INVEX en Nuevo León",
        description="Bank + specific state",
        expected_type="any",
        expected_keywords=["nuevo león", "vivienda"],
        validate_has_data=False,
    ),
    # BUG-HALLUCINATION-001: Tests for regional queries that caused hallucination
    MVTestCase(
        id="MV-GEO-004",
        mv_name="bank_mv_cartera_por_estado",
        query="Saldo por entidad federativa de INVEX",
        description="Regional breakdown - hallucination prevention test",
        expected_type="chart",
        expected_keywords=["region", "estado", "invex"],
        min_data_points=3,  # Should have at least 3 regions
    ),
    MVTestCase(
        id="MV-GEO-005",
        mv_name="bank_mv_cartera_por_estado",
        query="Cartera por región de INVEX",
        description="Regional ranking query",
        expected_type="chart",
        expected_keywords=["region"],
        min_data_points=3,
    ),
    MVTestCase(
        id="MV-GEO-006",
        mv_name="bank_mv_cartera_por_estado",
        query="Comparativo regional 2024 vs 2025",
        description="Year-over-year regional comparison",
        expected_type="any",
        expected_keywords=["region", "comparativo"],
    ),

    # =========================================================================
    # 5. bank_mv_resumen_sistema - System Totals
    # =========================================================================
    MVTestCase(
        id="MV-SYS-001",
        mv_name="bank_mv_resumen_sistema",
        query="¿Cuál es la cartera total del sistema bancario?",
        description="System total cartera",
        expected_type="chart",
        expected_keywords=["sistema", "cartera"],
        min_data_points=1,
    ),
    MVTestCase(
        id="MV-SYS-002",
        mv_name="bank_mv_resumen_sistema",
        query="IMOR del sistema bancario últimos 24 meses",
        description="System IMOR evolution",
        expected_type="chart",
        expected_keywords=["imor", "sistema"],
        min_data_points=10,
    ),
    MVTestCase(
        id="MV-SYS-003",
        mv_name="bank_mv_resumen_sistema",
        query="¿Cuántas instituciones bancarias hay en México?",
        description="Institution count",
        expected_type="any",
        expected_keywords=["instituc"],
    ),
    MVTestCase(
        id="MV-SYS-004",
        mv_name="bank_mv_resumen_sistema",
        query="Concentración del Top 5 de bancos",
        description="Top 5 concentration",
        expected_type="any",
        expected_keywords=["concentración", "top"],
    ),

    # =========================================================================
    # 6. bank_mv_cartera_por_actividad - By Economic Activity
    # =========================================================================
    MVTestCase(
        id="MV-ACT-001",
        mv_name="bank_mv_cartera_por_actividad",
        query="Cartera comercial por actividad económica",
        description="Cartera by economic sector",
        expected_type="any",
        expected_keywords=["actividad", "económica"],
    ),
    MVTestCase(
        id="MV-ACT-002",
        mv_name="bank_mv_cartera_por_actividad",
        query="¿Cuál es la actividad económica con mayor morosidad?",
        description="Activity with highest IMOR",
        expected_type="any",
        expected_keywords=["actividad", "morosidad"],
    ),
    MVTestCase(
        id="MV-ACT-003",
        mv_name="bank_mv_cartera_por_actividad",
        query="Cartera de manufactura de INVEX",
        description="Specific activity for bank",
        expected_type="any",
        expected_keywords=["manufactura"],
        validate_has_data=False,
    ),

    # =========================================================================
    # 7. bank_mv_cartera_por_tamano - By Company Size
    # =========================================================================
    MVTestCase(
        id="MV-SIZE-001",
        mv_name="bank_mv_cartera_por_tamano",
        query="Cartera a PyMEs del sistema",
        description="PyME cartera total",
        expected_type="any",
        expected_keywords=["pyme", "mipyme"],
    ),
    MVTestCase(
        id="MV-SIZE-002",
        mv_name="bank_mv_cartera_por_tamano",
        query="IMOR por tamaño de empresa",
        description="IMOR by company size",
        expected_type="any",
        expected_keywords=["tamaño", "empresa"],
        validate_has_data=False,
    ),
    MVTestCase(
        id="MV-SIZE-003",
        mv_name="bank_mv_cartera_por_tamano",
        query="Cartera a grandes empresas de INVEX",
        description="Large enterprise cartera",
        expected_type="any",
        expected_keywords=["grande", "empresa"],
        validate_has_data=False,
    ),

    # =========================================================================
    # 8. bank_mv_cartera_por_destino - By Credit Purpose
    # =========================================================================
    MVTestCase(
        id="MV-DEST-001",
        mv_name="bank_mv_cartera_por_destino",
        query="Cartera por destino de crédito",
        description="Cartera by credit purpose",
        expected_type="any",
        expected_keywords=["destino", "crédito"],
        validate_has_data=False,
    ),
    MVTestCase(
        id="MV-DEST-002",
        mv_name="bank_mv_cartera_por_destino",
        query="Capital de trabajo vs activo fijo",
        description="Working capital vs fixed assets",
        expected_type="any",
        expected_keywords=["capital", "trabajo"],
    ),

    # =========================================================================
    # 9. bank_mv_vivienda_por_producto - By Mortgage Product
    # =========================================================================
    MVTestCase(
        id="MV-PROD-001",
        mv_name="bank_mv_vivienda_por_producto",
        query="Cartera hipotecaria por tipo de producto",
        description="Mortgage by product type",
        expected_type="any",
        expected_keywords=["hipotecario", "producto"],
    ),
    MVTestCase(
        id="MV-PROD-002",
        mv_name="bank_mv_vivienda_por_producto",
        query="Créditos FOVISSSTE vs tradicional de INVEX",
        description="FOVISSSTE vs traditional",
        expected_type="any",
        expected_keywords=["fovissste", "tradicional"],
    ),

    # =========================================================================
    # 10. bank_mv_vivienda_por_perfil - By Demographic Profile
    # =========================================================================
    MVTestCase(
        id="MV-PROF-001",
        mv_name="bank_mv_vivienda_por_perfil",
        query="Distribución de cartera vivienda por género",
        description="Vivienda by gender",
        expected_type="any",
        expected_keywords=["género"],
    ),
    MVTestCase(
        id="MV-PROF-002",
        mv_name="bank_mv_vivienda_por_perfil",
        query="Cartera hipotecaria por nivel de ingreso",
        description="Mortgage by income level",
        expected_type="any",
        expected_keywords=["ingreso"],
        validate_has_data=False,
    ),
]


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def extract_data_points(response: Dict) -> int:
    """Count data points in chart response."""
    chart = response.get("bank_chart")
    if not chart:
        return 0

    plotly_config = chart.get("plotly_config", {})
    traces = plotly_config.get("data", [])

    total_points = 0
    for trace in traces:
        y_values = trace.get("y", [])
        x_values = trace.get("x", [])
        # Count non-null values
        points = max(len([v for v in y_values if v is not None]),
                     len([v for v in x_values if v is not None]))
        total_points += points

    return total_points


def check_keywords(response: Dict, keywords: List[str]) -> Tuple[bool, List[str]]:
    """Check if response contains expected keywords."""
    found = []
    missing = []

    # Combine all text content
    content = response.get("content", "").lower()
    chart = response.get("bank_chart", {})
    metric_name = (chart.get("metric_name", "") if chart else "").lower()
    title = (chart.get("title", "") if chart else "").lower()
    banks = " ".join(chart.get("bank_names", []) if chart else []).lower()

    full_text = f"{content} {metric_name} {title} {banks}"

    for kw in keywords:
        if kw.lower() in full_text:
            found.append(kw)
        else:
            missing.append(kw)

    return len(missing) == 0, missing


# =============================================================================
# TEST RUNNER
# =============================================================================

def run_test(test: MVTestCase, token: str) -> Dict[str, Any]:
    """Run a single test case."""
    result = {
        "id": test.id,
        "mv_name": test.mv_name,
        "query": test.query,
        "description": test.description,
        "passed": True,
        "issues": [],
        "warnings": [],
        "details": {},
    }

    try:
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
        content = response.get("content", "")

        # Record response type
        if chart:
            result["details"]["response_type"] = "chart"
            result["details"]["metric_name"] = chart.get("metric_name")
            result["details"]["bank_names"] = chart.get("bank_names", [])
        elif clarification:
            result["details"]["response_type"] = "clarification"
            result["details"]["options"] = [o.get("label") for o in clarification.get("options", [])]
        else:
            result["details"]["response_type"] = "text"
            result["details"]["content_length"] = len(content)

        # 1. Check response type
        if test.expected_type == "chart" and not chart:
            if clarification:
                result["warnings"].append("Got clarification instead of chart")
            else:
                result["issues"].append("No chart received")
                result["passed"] = False

        # 2. Check data points
        if chart and test.validate_has_data:
            data_points = extract_data_points(response)
            result["details"]["data_points"] = data_points

            if data_points < test.min_data_points:
                result["issues"].append(
                    f"Insufficient data: {data_points} points, expected >= {test.min_data_points}"
                )

        # 3. Check keywords
        if test.expected_keywords:
            found_all, missing = check_keywords(response, test.expected_keywords)
            if not found_all:
                result["warnings"].append(f"Missing keywords: {missing}")

    except Exception as e:
        result["passed"] = False
        result["issues"].append(f"Exception: {str(e)}")

    # Determine pass/fail
    if result["issues"]:
        result["passed"] = False

    return result


def main():
    """Run all tests and report results."""
    print("=" * 70)
    print("MATERIALIZED VIEWS COVERAGE TEST SUITE")
    print("Testing all 10 materialized views in bank-advisor")
    print("=" * 70)

    token = get_auth_token()
    if not token:
        print("❌ FATAL: Authentication failed")
        sys.exit(2)

    print(f"\nTotal tests: {len(MV_TEST_CASES)}\n")

    results = []
    passed = 0
    failed = 0

    # Group tests by MV
    mv_groups = {}
    for test in MV_TEST_CASES:
        if test.mv_name not in mv_groups:
            mv_groups[test.mv_name] = []
        mv_groups[test.mv_name].append(test)

    mv_stats = {}

    for mv_name, tests in mv_groups.items():
        print(f"\n{'─' * 60}")
        print(f"MV: {mv_name}")
        print("─" * 60)

        mv_passed = 0
        mv_failed = 0

        for test in tests:
            print(f"\n[{test.id}] {test.description}")
            print(f"  Query: {test.query}")

            result = run_test(test, token)
            results.append(result)

            if result["passed"]:
                print(f"  ✅ PASS")
                passed += 1
                mv_passed += 1
            else:
                print(f"  ❌ FAIL")
                failed += 1
                mv_failed += 1
                for issue in result["issues"]:
                    print(f"     ⚠ {issue}")

            # Show details
            if result.get("details", {}).get("data_points"):
                print(f"  📊 Data points: {result['details']['data_points']}")
            if result.get("details", {}).get("response_type"):
                print(f"  📝 Response type: {result['details']['response_type']}")

            # Show warnings
            for warning in result.get("warnings", []):
                print(f"     ℹ {warning}")

            time.sleep(0.5)

        mv_stats[mv_name] = {"passed": mv_passed, "failed": mv_failed}

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total:  {len(MV_TEST_CASES)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Rate:   {passed/len(MV_TEST_CASES)*100:.1f}%")

    print("\nBy Materialized View:")
    for mv_name, stats in mv_stats.items():
        total = stats["passed"] + stats["failed"]
        rate = stats["passed"] / total * 100 if total > 0 else 0
        status = "✅" if stats["failed"] == 0 else "❌"
        # Shorten MV name for display
        short_name = mv_name.replace("bank_mv_", "")
        print(f"  {short_name}: {stats['passed']}/{total} ({rate:.0f}%) {status}")

    if failed > 0:
        print("\nFailed Tests:")
        for r in results:
            if not r["passed"]:
                print(f"  - [{r['id']}] {r['description']}")
                for issue in r["issues"]:
                    print(f"       {issue}")

    # Save results
    output_file = Path(__file__).parent / "materialized_views_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": len(MV_TEST_CASES),
            "passed": passed,
            "failed": failed,
            "mv_stats": mv_stats,
            "results": results,
        }, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
