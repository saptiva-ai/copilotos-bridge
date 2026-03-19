#!/usr/bin/env python3
"""
Unified Metrics Test Suite
Combines:
1. Streaming Verification (Chart received, title correct)
2. Data Consistency (Value ranges, no nulls, temporal order)

Covers all 17 supported banking metrics.
"""

import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Ensure tests/ is on path for shared utils
sys.path.append(str(Path(__file__).resolve().parents[2]))

from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")


# --- DEFINITIONS ---

@dataclass
class MetricDefinition:
    """Definition of a metric for validation."""
    name: str
    expected_metric_keywords: List[str]
    min_value: float
    max_value: float
    can_be_negative: bool = False
    typical_range: Tuple[float, float] = (0, 100)


@dataclass
class TestCase:
    name: str
    query: str
    expected_type: str  # "chart" or "clarification"
    metric_def: Optional[MetricDefinition] = None


# --- CONFIGURATION: 17 Metrics ---

METRICS_DB = {
    # Valores de cartera en MXN (miles de millones = billones)
    "CARTERA_COMERCIAL": MetricDefinition(
        name="Cartera Comercial",
        expected_metric_keywords=["comercial", "cartera"],
        min_value=0, max_value=10_000_000_000_000,  # Hasta 10 trillones MXN
        typical_range=(1_000_000_000, 1_000_000_000_000)
    ),
    "PERDIDA_ESPERADA": MetricDefinition(
        name="Pérdida Esperada",
        expected_metric_keywords=["pérdida", "esperada", "pe_total"],
        min_value=0, max_value=100_000_000_000,  # Hasta 100 mil millones
    ),
    "RESERVAS": MetricDefinition(
        name="Reservas",
        expected_metric_keywords=["reserva"],
        min_value=-1_000_000_000_000, max_value=0,  # Reservas son negativas
        can_be_negative=True
    ),
    "VARIACION_RESERVAS": MetricDefinition(
        name="Variación Reservas",
        expected_metric_keywords=["reserva", "variación"],
        min_value=-100_000_000, max_value=100_000_000,  # Variación en millones
        can_be_negative=True
    ),
    "IMOR": MetricDefinition(
        name="IMOR",
        expected_metric_keywords=["imor", "morosidad"],
        min_value=0, max_value=100,  # Porcentaje
        typical_range=(0, 20)
    ),
    "CARTERA_VENCIDA": MetricDefinition(
        name="Cartera Vencida",
        expected_metric_keywords=["vencida", "cartera"],
        min_value=0, max_value=500_000_000_000,  # Hasta 500 mil millones
    ),
    "ICOR": MetricDefinition(
        name="ICOR",
        expected_metric_keywords=["icor", "cobertura"],
        min_value=0, max_value=10000,  # ICOR puede ser >100%
        typical_range=(50, 300)
    ),
    "ETAPA_1": MetricDefinition(
        name="Etapa 1",
        expected_metric_keywords=["etapa", "ct_etapa"],
        min_value=0, max_value=100,  # Porcentaje
        typical_range=(80, 100)
    ),
    "QUEBRANTOS": MetricDefinition(
        name="Quebrantos",
        expected_metric_keywords=["quebranto"],
        min_value=-10_000_000_000, max_value=10_000_000_000,
        can_be_negative=True
    ),
    "ICAP": MetricDefinition(
        name="ICAP",
        expected_metric_keywords=["icap", "capitalización"],
        min_value=0, max_value=10000,  # En puntos base (15% = 1500 bps)
        typical_range=(1000, 3000)
    ),
    "TDA": MetricDefinition(
        name="TDA",
        expected_metric_keywords=["deterioro", "ajustada"],
        min_value=0, max_value=100,  # Porcentaje
        typical_range=(0, 10)
    ),
    "TASA_EFECTIVA": MetricDefinition(
        name="Tasa Efectiva",
        expected_metric_keywords=["tasa"],
        min_value=0, max_value=10000,  # En puntos base (100% = 10000 bps)
        typical_range=(500, 6000)
    ),
}

TEST_CASES = [
    # Queries específicas con SISTEMA o INVEX para evitar clarificación
    TestCase("1. Cartera Comercial SISTEMA", "Cartera comercial del SISTEMA", "chart", METRICS_DB["CARTERA_COMERCIAL"]),
    TestCase("2. Cartera Comercial INVEX", "Cartera comercial de INVEX", "chart", METRICS_DB["CARTERA_COMERCIAL"]),
    TestCase("3. Pérdida Esperada", "Pérdida esperada de INVEX", "chart", METRICS_DB["PERDIDA_ESPERADA"]),
    TestCase("4. Reservas INVEX", "Reservas de INVEX", "chart", METRICS_DB["RESERVAS"]),
    TestCase("5. Variación Reservas", "Variación de reservas de INVEX", "chart", METRICS_DB["VARIACION_RESERVAS"]),
    TestCase("6. IMOR SISTEMA", "IMOR del SISTEMA", "chart", METRICS_DB["IMOR"]),
    TestCase("7. Cartera Vencida", "Cartera vencida del SISTEMA", "chart", METRICS_DB["CARTERA_VENCIDA"]),
    TestCase("8. ICOR SISTEMA", "ICOR del SISTEMA", "chart", METRICS_DB["ICOR"]),
    TestCase("9. Etapas Sistema (E1)", "ct_etapa_1 del SISTEMA", "chart", METRICS_DB["ETAPA_1"]),
    TestCase("10. Etapas INVEX (E1)", "ct_etapa_1 de INVEX", "chart", METRICS_DB["ETAPA_1"]),
    TestCase("11. Quebrantos INVEX", "Quebrantos de INVEX", "chart", METRICS_DB["QUEBRANTOS"]),
    TestCase("12. ICAP SISTEMA", "ICAP del SISTEMA", "chart", METRICS_DB["ICAP"]),
    TestCase("13. TDA SISTEMA", "Tasa de deterioro ajustada del SISTEMA", "chart", METRICS_DB["TDA"]),
    TestCase("14. Tasa Sistema", "Tasa efectiva del SISTEMA", "chart", METRICS_DB["TASA_EFECTIVA"]),
    TestCase("15. Tasa INVEX", "TASA_SISTEMA de INVEX", "chart", METRICS_DB["TASA_EFECTIVA"]),
    TestCase("16. IMOR INVEX", "IMOR de INVEX", "chart", METRICS_DB["IMOR"]),
    TestCase("17. ICAP INVEX", "ICAP de INVEX", "chart", METRICS_DB["ICAP"]),
]


# --- VALIDATION LOGIC ---

def validate_value_range(traces: List[Dict], metric_def: MetricDefinition) -> List[str]:
    issues = []
    all_values = []

    for trace in traces:
        # Horizontal bar charts have values in 'x', vertical have them in 'y'
        orientation = trace.get("orientation", "v")
        if orientation == "h":
            vals = trace.get("x", [])
        else:
            vals = trace.get("y", [])

        for v in vals:
            if isinstance(v, (int, float)) and v is not None and v == v:  # Not NaN
                all_values.append(v)

                # Check absolute bounds
                if v < metric_def.min_value:
                    issues.append(f"Value {v:.2f} below min {metric_def.min_value}")
                if v > metric_def.max_value:
                    issues.append(f"Value {v:.2f} above max {metric_def.max_value}")

    if not all_values:
        issues.append("No numeric values found in traces")

    return issues

def validate_temporal_order(traces: List[Dict]) -> List[str]:
    issues = []
    for trace in traces:
        x_values = trace.get("x", [])
        dates = []
        for x in x_values:
            if isinstance(x, str):
                for fmt in ["%Y-%m", "%Y-%m-%d", "%Y/%m", "%Y"]:
                    try:
                        dates.append(datetime.strptime(x, fmt))
                        break
                    except ValueError:
                        continue
        
        # Check ordering
        for i in range(1, len(dates)):
            if dates[i] < dates[i - 1]:
                issues.append(f"Dates out of order: {dates[i - 1]} > {dates[i]}")
    return issues

def validate_no_all_nulls(traces: List[Dict]) -> List[str]:
    issues = []
    for trace in traces:
        y_values = trace.get("y", [])
        non_null = [v for v in y_values if v is not None and v == v]
        if len(y_values) > 0 and len(non_null) == 0:
            issues.append(f"Trace '{trace.get('name')}' has all null/NaN values")
    return issues


# --- TEST RUNNER ---

def run_test_case(test_case: TestCase, token: str) -> Dict[str, Any]:
    result = {
        "name": test_case.name,
        "query": test_case.query,
        "passed": False,
        "issues": [],
        "details": {}
    }

    try:
        sse_data = send_chat_message(
            token,
            test_case.query,
            backend_url=BACKEND_URL,
            model="Saptiva Turbo",
            timeout=90,
        )

        if sse_data.get("error"):
            result["issues"].append(f"API Error: {sse_data['error']}")
            return result

        chart = sse_data.get("bank_chart")
        clarification = sse_data.get("clarification") or sse_data.get("bank_clarification")

        # 1. Type Check
        if test_case.expected_type == "chart" and not chart:
            if clarification:
                 result["issues"].append("Got clarification instead of chart")
            else:
                 result["issues"].append("No chart received")
            return result
            
        if chart:
            result["details"]["metric_name"] = chart.get("metric_name")
            
            # 2. Title Keyword Validation
            title = (chart.get("title") or "").lower()
            metric_name = (chart.get("metric_name") or "").lower()
            full_title = f"{title} {metric_name}"
            
            if test_case.metric_def:
                found = any(kw.lower() in full_title for kw in test_case.metric_def.expected_metric_keywords)
                if not found:
                    result["issues"].append(f"Title mismatch. Keywords: {test_case.metric_def.expected_metric_keywords}")
            
            # 3. Data Consistency Validation
            plotly_data = chart.get("plotly_config", {}).get("data", [])
            if not plotly_data:
                result["issues"].append("No plotly traces found")
            elif test_case.metric_def:
                # Range Check
                range_issues = validate_value_range(plotly_data, test_case.metric_def)
                result["issues"].extend(range_issues)
                
                # Temporal Check
                date_issues = validate_temporal_order(plotly_data)
                result["issues"].extend(date_issues)
                
                # Null Check
                null_issues = validate_no_all_nulls(plotly_data)
                result["issues"].extend(null_issues)

        if not result["issues"]:
            result["passed"] = True

    except Exception as e:
        result["issues"].append(f"Exception: {str(e)}")

    return result

def main():
    print("=" * 70)
    print("UNIFIED METRICS TEST SUITE (Streaming + Consistency)")
    print("=" * 70)

    token = get_auth_token()
    if not token:
        print("❌ Fatal: Auth failed")
        return

    passed = 0
    failed = 0
    results = []

    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] {test.name}")
        res = run_test_case(test, token)
        results.append(res)
        
        if res["passed"]:
            print(f"    ✅ PASS")
            passed += 1
        else:
            print(f"    ❌ FAIL")
            for issue in res["issues"]:
                print(f"       - {issue}")
            failed += 1
            
        time.sleep(0.3)

    print("\n" + "=" * 70)
    print(f"SUMMARY: {passed} Passed, {failed} Failed")
    
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
