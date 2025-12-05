#!/usr/bin/env python3
"""
E2E Test for 17 Banking Metrics with Streaming
Tests full flow: Frontend -> Backend -> Bank-Advisor -> Response

Verifies:
1. Graph appears correctly
2. Title is correct
3. Data makes sense (not empty, reasonable values)
4. Clarification requested when appropriate
"""

import requests
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

BACKEND_URL = "http://localhost:8000"

@dataclass
class MetricTestCase:
    """Test case for a banking metric"""
    name: str
    query: str
    expected_type: str  # "chart" or "clarification"
    expected_metric_keywords: List[str]  # Keywords expected in metric name/title
    value_range: Optional[Tuple[float, float]] = None  # Expected value range (min, max)
    is_percentage: bool = False  # If values should be percentages

# Define all 17 test cases
TEST_CASES = [
    MetricTestCase(
        name="1. Cartera Comercial CC",
        query="Cartera comercial de todos los bancos",
        expected_type="chart",
        expected_metric_keywords=["comercial", "cartera"],
        value_range=(1000, 200000000),  # MDP (updated after scale fix)
    ),
    MetricTestCase(
        name="2. Cartera Comercial Sin Gob",
        query="Cartera comercial sin gobierno",
        expected_type="chart",
        expected_metric_keywords=["comercial", "gobierno"],
        value_range=(1000, 200000000),  # MDP (updated)
    ),
    MetricTestCase(
        name="3. Pérdida Esperada Total",
        query="Pérdida esperada total por banco",
        expected_type="chart",
        expected_metric_keywords=["pérdida", "esperada"],
        value_range=(0, 100000),
    ),
    MetricTestCase(
        name="4. Reservas Totales",
        query="Reservas totales por banco",
        expected_type="chart",
        expected_metric_keywords=["reserva"],
        value_range=(-35000000, -400),  # Negative is correct (liability convention)
    ),
    MetricTestCase(
        name="5. Reservas (Variación)",
        query="Variación mensual de reservas",
        expected_type="chart",
        expected_metric_keywords=["reserva", "variación"],
        value_range=(-50000, 50000),  # Can be negative
    ),
    MetricTestCase(
        name="6. IMOR",
        query="IMOR de todos los bancos",
        expected_type="chart",
        expected_metric_keywords=["imor", "morosidad"],
        value_range=(0, 20),
        is_percentage=True,
    ),
    MetricTestCase(
        name="7. Cartera Vencida",
        query="Cartera vencida por banco",
        expected_type="chart",
        expected_metric_keywords=["vencida", "cartera"],
        value_range=(0, 25000000),  # MDP (updated)
    ),
    MetricTestCase(
        name="8. ICOR",
        query="ICOR por banco",
        expected_type="chart",
        expected_metric_keywords=["icor", "cobertura"],
        value_range=(0, 500),  # Unbounded ratio, can exceed 100%
        is_percentage=True,
    ),
    MetricTestCase(
        name="9. Etapas Deterioro Sistema (Etapa 1)",
        query="ct_etapa_1 del sistema",
        expected_type="chart",
        expected_metric_keywords=["etapa", "ct_etapa"],
        value_range=(90, 100),  # Percentage (Etapa 1 ~95-96% for SISTEMA)
        is_percentage=True,
    ),
    MetricTestCase(
        name="10. Etapas Deterioro INVEX (Etapa 1)",
        query="ct_etapa_1 de INVEX",
        expected_type="chart",
        expected_metric_keywords=["etapa", "ct_etapa"],
        value_range=(80, 100),  # Percentage after scale fix (Etapa 1 ~95%)
        is_percentage=True,
    ),
    MetricTestCase(
        name="11. Quebrantos Comerciales",
        query="Quebrantos comerciales por banco",
        expected_type="chart",
        expected_metric_keywords=["quebranto"],
        value_range=(-10000, 500000),  # Can be negative
    ),
    MetricTestCase(
        name="12. ICAP",
        query="ICAP por banco",
        expected_type="chart",
        expected_metric_keywords=["icap", "capitalización"],
        value_range=(0, 60),  # Percentage (updated after scale fix)
        is_percentage=True,
    ),
    MetricTestCase(
        name="13. TDA",
        query="Tasa de deterioro ajustada",
        expected_type="chart",
        expected_metric_keywords=["deterioro", "ajustada", "tda"],
        value_range=(0, 10),  # Percentage (updated after scale fix)
        is_percentage=True,
    ),
    MetricTestCase(
        name="14. Tasa Sistema",
        query="Tasa efectiva del sistema",
        expected_type="chart",
        expected_metric_keywords=["tasa", "sistema"],
        value_range=(20, 50),
        is_percentage=True,
    ),
    MetricTestCase(
        name="15. Tasa INVEX Consumo",
        query="Tasa efectiva INVEX consumo",
        expected_type="chart",
        expected_metric_keywords=["tasa", "invex", "consumo"],
        value_range=(20, 50),
        is_percentage=True,
    ),
    MetricTestCase(
        name="16. Tasa MN",
        query="Tasa moneda nacional",
        expected_type="chart",
        expected_metric_keywords=["tasa", "moneda", "nacional"],
        value_range=(0, 30),  # Percentage (updated after scale fix)
        is_percentage=True,
    ),
    MetricTestCase(
        name="17. Tasa ME",
        query="Tasa moneda extranjera",
        expected_type="chart",
        expected_metric_keywords=["tasa", "moneda", "extranjera"],
        value_range=(0, 15),  # Percentage (updated after scale fix)
        is_percentage=True,
    ),
]


def get_auth_token() -> Optional[str]:
    """Get JWT token for demo user"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/auth/login",
            json={"identifier": "demo", "password": "Demo1234"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception as e:
        print(f"Auth error: {e}")
    return None


def parse_sse_response(response) -> Dict[str, Any]:
    """Parse SSE response and extract relevant events"""
    result = {
        "events": [],
        "bank_chart": None,
        "bank_clarification": None,
        "chunks": [],
        "meta": None,
        "error": None
    }

    current_event = None

    try:
        for line in response.iter_lines():
            if not line:
                continue
            decoded = line.decode('utf-8')

            if decoded.startswith('event:'):
                current_event = decoded.replace('event:', '').strip()
                result["events"].append(current_event)
            elif decoded.startswith('data:') and current_event:
                data = decoded.replace('data:', '').strip()
                try:
                    parsed = json.loads(data)
                    if current_event == 'bank_chart':
                        result["bank_chart"] = parsed
                    elif current_event == 'bank_clarification':
                        result["bank_clarification"] = parsed
                    elif current_event == 'meta':
                        result["meta"] = parsed
                    elif current_event == 'chunk':
                        result["chunks"].append(parsed)
                    elif current_event == 'error':
                        result["error"] = parsed
                except json.JSONDecodeError:
                    if current_event == 'chunk':
                        result["chunks"].append(data)
    except Exception as e:
        result["error"] = str(e)

    return result


def test_metric_streaming(test_case: MetricTestCase, token: str) -> Dict[str, Any]:
    """Test a single metric with streaming"""
    result = {
        "name": test_case.name,
        "query": test_case.query,
        "passed": False,
        "issues": [],
        "details": {}
    }

    payload = {
        "chat_id": None,
        "message": test_case.query,
        "context": {},
        "stream": True,
        "model": "Saptiva Turbo"
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream"
    }

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/chat",
            json=payload,
            headers=headers,
            timeout=120,
            stream=True
        )

        if response.status_code != 200:
            result["issues"].append(f"HTTP {response.status_code}")
            return result

        sse_data = parse_sse_response(response)
        result["details"]["events"] = list(set(sse_data["events"]))

        # Check for errors
        if sse_data["error"]:
            result["issues"].append(f"Error: {sse_data['error']}")
            return result

        # Check expected type
        if test_case.expected_type == "clarification":
            if sse_data["bank_clarification"]:
                result["passed"] = True
                result["details"]["clarification_message"] = sse_data["bank_clarification"].get("message")
                result["details"]["options"] = [o.get("label") for o in sse_data["bank_clarification"].get("options", [])]
            else:
                result["issues"].append("Expected clarification but got chart or nothing")

        elif test_case.expected_type == "chart":
            if sse_data["bank_clarification"]:
                # Got clarification instead of chart - might be intentional
                result["details"]["got_clarification"] = True
                result["details"]["clarification_message"] = sse_data["bank_clarification"].get("message")
                result["details"]["options"] = [o.get("label") for o in sse_data["bank_clarification"].get("options", [])]
                result["issues"].append("Got clarification instead of chart")
            elif sse_data["bank_chart"]:
                chart = sse_data["bank_chart"]
                result["details"]["chart_received"] = True

                # 1. Check title (check both top-level and metadata)
                metric_name = (chart.get("metric_name") or "").lower()
                title = (chart.get("title") or "").lower()
                # Also check metadata.title if top-level title is empty
                if not title:
                    metadata = chart.get("metadata", {})
                    title = (metadata.get("title") or "").lower()
                title_text = f"{metric_name} {title}"

                keyword_found = any(kw.lower() in title_text for kw in test_case.expected_metric_keywords)
                if not keyword_found:
                    result["issues"].append(f"Title mismatch: got '{metric_name}', expected keywords: {test_case.expected_metric_keywords}")
                result["details"]["metric_name"] = chart.get("metric_name")
                result["details"]["title"] = chart.get("title") or chart.get("metadata", {}).get("title")

                # 2. Check plotly data
                plotly_config = chart.get("plotly_config", {})
                plotly_data = plotly_config.get("data", [])

                if not plotly_data:
                    result["issues"].append("No plotly data")
                else:
                    # Get all Y values from all traces - filter only numeric values
                    all_y_values = []
                    for trace in plotly_data:
                        y_vals = trace.get("y", [])
                        # Filter: only int/float, not None, not NaN, not strings
                        for v in y_vals:
                            if isinstance(v, (int, float)) and v is not None:
                                # Check for NaN (NaN != NaN)
                                if v == v:  # False for NaN
                                    all_y_values.append(v)

                    result["details"]["data_points"] = len(all_y_values)
                    result["details"]["traces_count"] = len(plotly_data)

                    if not all_y_values:
                        result["issues"].append("No valid Y values in data")
                    else:
                        try:
                            min_val = min(all_y_values)
                            max_val = max(all_y_values)
                            avg_val = sum(all_y_values) / len(all_y_values)

                            result["details"]["value_range"] = f"{min_val:.2f} - {max_val:.2f}"
                            result["details"]["average"] = f"{avg_val:.2f}"

                            # 3. Check value range
                            if test_case.value_range:
                                expected_min, expected_max = test_case.value_range
                                if min_val < expected_min * 0.1 or max_val > expected_max * 10:
                                    result["issues"].append(
                                        f"Values out of expected range: got {min_val:.2f}-{max_val:.2f}, "
                                        f"expected ~{expected_min}-{expected_max}"
                                    )
                        except (TypeError, ValueError) as e:
                            result["issues"].append(f"Error calculating statistics: {e}")

                # 4. Check SQL if available
                metadata = chart.get("metadata", {})
                sql_generated = metadata.get("sql_generated")
                if sql_generated:
                    result["details"]["has_sql"] = True
                    result["details"]["sql_preview"] = sql_generated[:100] + "..."
                else:
                    result["details"]["has_sql"] = False

                # 5. Check bank names
                bank_names = chart.get("bank_names", [])
                result["details"]["banks"] = bank_names

                # If no critical issues, mark as passed
                if not result["issues"]:
                    result["passed"] = True
            else:
                result["issues"].append("No chart or clarification received")

    except Exception as e:
        result["issues"].append(f"Exception: {str(e)}")

    return result


def run_all_tests():
    """Run all 17 metric tests"""
    print("=" * 70)
    print("E2E STREAMING TEST - 17 BANKING METRICS")
    print("=" * 70)

    # Get auth token
    token = get_auth_token()
    if not token:
        print("FATAL: Could not get auth token")
        return

    print("Auth token obtained\n")

    results = []
    passed = 0
    failed = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/17] Testing: {test_case.name}")
        print(f"    Query: \"{test_case.query}\"")

        result = test_metric_streaming(test_case, token)
        results.append(result)

        if result["passed"]:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"

        print(f"    Status: {status}")

        if result["details"].get("metric_name"):
            print(f"    Metric: {result['details']['metric_name']}")
        if result["details"].get("data_points"):
            print(f"    Data points: {result['details']['data_points']}")
        if result["details"].get("value_range"):
            print(f"    Value range: {result['details']['value_range']}")
        if result["details"].get("got_clarification"):
            print(f"    Got clarification: {result['details']['clarification_message']}")
            print(f"    Options: {result['details'].get('options', [])}")
        if result["issues"]:
            for issue in result["issues"]:
                print(f"    Issue: {issue}")

        # Small delay between requests
        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total: {len(TEST_CASES)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {passed/len(TEST_CASES)*100:.1f}%")

    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['name']}: {', '.join(r['issues'])}")

    # Detailed JSON output
    print("\n" + "=" * 70)
    print("DETAILED RESULTS (JSON)")
    print("=" * 70)
    for r in results:
        print(f"\n{r['name']}:")
        print(json.dumps(r, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    run_all_tests()
