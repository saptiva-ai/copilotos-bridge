#!/usr/bin/env python3
"""
E2E Test for ALL Metrics in the Catalog

Tests the complete flow:
1. Query via HTTP API (simulates frontend)
2. NL2SQL pipeline processing
3. PostgreSQL data retrieval
4. Response validation

Usage:
    python scripts/test_metrics_catalog_e2e.py
"""
import asyncio
import httpx
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Configuration
BASE_URL = "http://localhost:8002"
TIMEOUT = 30.0

# Metrics catalog with test queries (all include time range for complete spec)
METRICS_CATALOG = [
    # 1. Cartera Comercial CC
    {
        "name": "Cartera Comercial CC",
        "queries": [
            "Cartera comercial de INVEX últimos 6 meses",
            "Evolución cartera comercial 2024"
        ],
        "expected_metric": "CARTERA_COMERCIAL",
        "required_fields": ["data", "plotly_config"]
    },
    # 2. Cartera Comercial Sin Gob
    {
        "name": "Cartera Comercial Sin Gob",
        "queries": [
            "Cartera comercial sin gobierno últimos 6 meses",
            "CC sin entidades gubernamentales 2024"
        ],
        "expected_metric": "CARTERA_COMERCIAL_SIN_GOB",
        "required_fields": ["data", "plotly_config"]
    },
    # 3. Pérdida Esperada Total
    {
        "name": "Pérdida Esperada Total",
        "queries": [
            "Pérdida esperada de INVEX últimos 6 meses",
            "PE total del sistema 2024"
        ],
        "expected_metric": "PERDIDA_ESPERADA",
        "required_fields": ["data", "plotly_config"]
    },
    # 4. Reservas Totales
    {
        "name": "Reservas Totales",
        "queries": [
            "Reservas totales de INVEX últimos 6 meses",
            "Reservas del sistema 2024"
        ],
        "expected_metric": "RESERVAS",
        "required_fields": ["data", "plotly_config"]
    },
    # 5. Reservas Totales (Variación)
    {
        "name": "Reservas Totales (Variación)",
        "queries": [
            "Variación de reservas INVEX últimos 6 meses",
            "Cambio en reservas 2024"
        ],
        "expected_metric": "RESERVAS_VAR",
        "required_fields": ["data", "plotly_config"]
    },
    # 6. IMOR
    {
        "name": "IMOR",
        "queries": [
            "IMOR de INVEX últimos 6 meses",
            "Índice de morosidad 2024"
        ],
        "expected_metric": "IMOR",
        "required_fields": ["data", "plotly_config"]
    },
    # 7. Cartera Vencida
    {
        "name": "Cartera Vencida",
        "queries": [
            "Cartera vencida de INVEX últimos 6 meses",
            "Evolución cartera vencida 2024"
        ],
        "expected_metric": "CARTERA_VENCIDA",
        "required_fields": ["data", "plotly_config"]
    },
    # 8. ICOR
    {
        "name": "ICOR",
        "queries": [
            "ICOR de INVEX últimos 6 meses",
            "Índice de cobertura 2024"
        ],
        "expected_metric": "ICOR",
        "required_fields": ["data", "plotly_config"]
    },
    # 9. Etapas de Deterioro (Sistema)
    {
        "name": "Etapas de Deterioro (Sistema)",
        "queries": [
            "Etapas de deterioro del sistema últimos 6 meses",
            "Distribución etapas IFRS9 sistema 2024"
        ],
        "expected_metric": "ETAPAS_DETERIORO",
        "required_fields": ["data", "plotly_config"]
    },
    # 10. Etapas de Deterioro (INVEX)
    {
        "name": "Etapas de Deterioro (INVEX)",
        "queries": [
            "Etapas de deterioro INVEX últimos 6 meses",
            "Etapas 1, 2, 3 de INVEX 2024"
        ],
        "expected_metric": "ETAPAS_DETERIORO",
        "required_fields": ["data", "plotly_config"]
    },
    # 11. Quebrantos Comerciales
    {
        "name": "Quebrantos Comerciales",
        "queries": [
            "Quebrantos comerciales INVEX últimos 6 meses",
            "Castigos cartera comercial 2024"
        ],
        "expected_metric": "QUEBRANTOS",
        "required_fields": ["data", "plotly_config"]
    },
    # 12. ICAP
    {
        "name": "ICAP",
        "queries": [
            "ICAP de INVEX últimos 6 meses",
            "Índice de capitalización 2024"
        ],
        "expected_metric": "ICAP",
        "required_fields": ["data", "plotly_config"]
    },
    # 13. Tasa de Deterioro Ajustada (TDA)
    {
        "name": "Tasa de Deterioro Ajustada",
        "queries": [
            "TDA de INVEX últimos 6 meses",
            "Tasa deterioro ajustada 2024"
        ],
        "expected_metric": "TDA",
        "required_fields": ["data", "plotly_config"]
    },
    # 14. Tasa Interés Efectiva (Sistema)
    {
        "name": "Tasa Interés Efectiva (Sistema)",
        "queries": [
            "Tasa efectiva del sistema últimos 12 meses",
            "TE sistema 2024"
        ],
        "expected_metric": "TASA_EFECTIVA",
        "required_fields": ["data", "plotly_config"]
    },
    # 15. Tasa Interés Efectiva (INVEX Consumo)
    {
        "name": "Tasa Interés Efectiva (INVEX Consumo)",
        "queries": [
            "Tasa INVEX consumo últimos 6 meses",
            "TE INVEX segmento consumo 2024"
        ],
        "expected_metric": "TASA_EFECTIVA_CONSUMO",
        "required_fields": ["data", "plotly_config"]
    },
    # 16. Tasa Crédito Corporativo (MN)
    {
        "name": "Tasa Crédito Corporativo (MN)",
        "queries": [
            "Tasa corporativa moneda nacional últimos 6 meses",
            "Tasa MN créditos corporativos 2024"
        ],
        "expected_metric": "TASA_MN",
        "required_fields": ["data", "plotly_config"]
    },
    # 17. Tasa Crédito Corporativo (ME)
    {
        "name": "Tasa Crédito Corporativo (ME)",
        "queries": [
            "Tasa corporativa moneda extranjera últimos 6 meses",
            "Tasa ME créditos corporativos 2024"
        ],
        "expected_metric": "TASA_ME",
        "required_fields": ["data", "plotly_config"]
    },
]


@dataclass
class TestResult:
    metric_name: str
    query: str
    success: bool
    response_time_ms: float
    error: Optional[str] = None
    data_points: int = 0
    pipeline: str = "unknown"
    has_visualization: bool = False


async def test_single_query(
    client: httpx.AsyncClient,
    metric_name: str,
    query: str,
    required_fields: List[str]
) -> TestResult:
    """Test a single query against the MCP API."""

    start_time = datetime.now()

    try:
        # Call the MCP RPC endpoint for bank_analytics tool
        response = await client.post(
            f"{BASE_URL}/rpc",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "bank_analytics",
                    "arguments": {
                        "metric_or_query": query,
                        "mode": "chart"
                    }
                },
                "id": 1
            },
            timeout=TIMEOUT
        )

        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        if response.status_code != 200:
            return TestResult(
                metric_name=metric_name,
                query=query,
                success=False,
                response_time_ms=response_time_ms,
                error=f"HTTP {response.status_code}: {response.text[:200]}"
            )

        rpc_response = response.json()

        # Check for RPC error
        if "error" in rpc_response:
            return TestResult(
                metric_name=metric_name,
                query=query,
                success=False,
                response_time_ms=response_time_ms,
                error=f"RPC Error: {rpc_response['error']}"
            )

        # Extract data from MCP response
        content = rpc_response.get("result", {}).get("content", [])
        if not content:
            return TestResult(
                metric_name=metric_name,
                query=query,
                success=False,
                response_time_ms=response_time_ms,
                error="Empty response content"
            )

        # Parse the text content (JSON string)
        text_content = content[0].get("text", "{}")
        try:
            data = json.loads(text_content)
        except json.JSONDecodeError:
            return TestResult(
                metric_name=metric_name,
                query=query,
                success=False,
                response_time_ms=response_time_ms,
                error=f"Invalid JSON response: {text_content[:100]}"
            )

        # Check for error in the data
        if not data.get("success", False):
            error_msg = data.get("data", {}).get("message", "Unknown error")
            error_code = data.get("data", {}).get("error", "unknown")
            return TestResult(
                metric_name=metric_name,
                query=query,
                success=False,
                response_time_ms=response_time_ms,
                error=f"{error_code}: {error_msg}"
            )

        # The data structure is nested in success responses
        inner_data = data.get("data", {})

        # Count data points
        data_points = 0
        if isinstance(inner_data, dict):
            if "months" in inner_data:
                data_points = len(inner_data["months"])
            elif "data" in inner_data and isinstance(inner_data["data"], dict):
                if "months" in inner_data["data"]:
                    data_points = len(inner_data["data"]["months"])

        # Check visualization
        has_viz = "plotly_config" in inner_data and inner_data.get("plotly_config") is not None

        # Get pipeline used
        pipeline = data.get("metadata", {}).get("pipeline", "unknown")

        return TestResult(
            metric_name=metric_name,
            query=query,
            success=True,
            response_time_ms=response_time_ms,
            data_points=data_points,
            pipeline=pipeline,
            has_visualization=has_viz
        )

    except httpx.TimeoutException:
        return TestResult(
            metric_name=metric_name,
            query=query,
            success=False,
            response_time_ms=TIMEOUT * 1000,
            error="Request timeout"
        )
    except Exception as e:
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        return TestResult(
            metric_name=metric_name,
            query=query,
            success=False,
            response_time_ms=response_time_ms,
            error=str(e)
        )


async def test_health_endpoint(client: httpx.AsyncClient) -> bool:
    """Check if the service is healthy."""
    try:
        response = await client.get(f"{BASE_URL}/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            return data.get("status") == "healthy"
        return False
    except Exception:
        return False


async def run_all_tests() -> List[TestResult]:
    """Run all metric tests."""

    print("\n" + "="*70)
    print("BankAdvisor - Metrics Catalog E2E Validation")
    print("="*70)
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    print(f"Target: {BASE_URL}")
    print(f"Metrics to test: {len(METRICS_CATALOG)}")
    print(f"Total queries: {sum(len(m['queries']) for m in METRICS_CATALOG)}")

    results: List[TestResult] = []

    async with httpx.AsyncClient() as client:
        # Check service health first
        print("\n" + "-"*70)
        print("Step 1: Checking service health...")

        is_healthy = await test_health_endpoint(client)
        if not is_healthy:
            print("❌ Service is not healthy or not reachable")
            print(f"   Make sure the service is running: docker-compose up bank-advisor")
            return []

        print("✅ Service is healthy")

        # Test each metric
        print("\n" + "-"*70)
        print("Step 2: Testing metrics catalog...")
        print("-"*70)

        for i, metric in enumerate(METRICS_CATALOG, 1):
            metric_name = metric["name"]
            queries = metric["queries"]
            required_fields = metric["required_fields"]

            print(f"\n[{i}/{len(METRICS_CATALOG)}] {metric_name}")

            for query in queries:
                result = await test_single_query(
                    client, metric_name, query, required_fields
                )
                results.append(result)

                status = "✅" if result.success else "❌"
                time_str = f"{result.response_time_ms:.0f}ms"

                if result.success:
                    print(f"   {status} \"{query}\" [{time_str}] "
                          f"({result.data_points} points, {result.pipeline})")
                else:
                    print(f"   {status} \"{query}\" [{time_str}]")
                    print(f"      Error: {result.error}")

    return results


def print_summary(results: List[TestResult]):
    """Print test summary."""

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed

    # Group by metric
    metrics_status: Dict[str, Dict[str, Any]] = {}
    for result in results:
        if result.metric_name not in metrics_status:
            metrics_status[result.metric_name] = {
                "total": 0,
                "passed": 0,
                "avg_time": 0,
                "times": []
            }

        metrics_status[result.metric_name]["total"] += 1
        metrics_status[result.metric_name]["times"].append(result.response_time_ms)

        if result.success:
            metrics_status[result.metric_name]["passed"] += 1

    # Calculate averages
    for name, status in metrics_status.items():
        status["avg_time"] = sum(status["times"]) / len(status["times"])

    # Print metrics table
    print("\n| Metric | Queries | Passed | Avg Time |")
    print("|--------|---------|--------|----------|")

    for name, status in metrics_status.items():
        total_q = status["total"]
        passed_q = status["passed"]
        avg_time = status["avg_time"]
        status_icon = "✅" if passed_q == total_q else "⚠️" if passed_q > 0 else "❌"

        print(f"| {status_icon} {name[:30]:<30} | {total_q} | {passed_q}/{total_q} | {avg_time:.0f}ms |")

    # Print overall stats
    print("\n" + "-"*70)
    print(f"Total Queries: {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")

    if results:
        avg_time = sum(r.response_time_ms for r in results) / len(results)
        max_time = max(r.response_time_ms for r in results)
        successful_times = [r.response_time_ms for r in results if r.success]
        min_time = min(successful_times) if successful_times else 0

        print(f"\nResponse Times:")
        print(f"  Average: {avg_time:.0f}ms")
        print(f"  Min: {min_time:.0f}ms")
        print(f"  Max: {max_time:.0f}ms")

    # Print failed queries
    failed_results = [r for r in results if not r.success]
    if failed_results:
        print("\n" + "-"*70)
        print("FAILED QUERIES:")
        print("-"*70)

        for result in failed_results:
            print(f"\n❌ {result.metric_name}")
            print(f"   Query: \"{result.query}\"")
            print(f"   Error: {result.error}")

    print("\n" + "="*70)

    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {failed} TESTS FAILED - Review errors above")

    print("="*70 + "\n")

    return failed == 0


def save_results(results: List[TestResult], filename: str):
    """Save results to JSON file."""

    data = {
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "passed": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "results": [
            {
                "metric_name": r.metric_name,
                "query": r.query,
                "success": r.success,
                "response_time_ms": r.response_time_ms,
                "error": r.error,
                "data_points": r.data_points,
                "pipeline": r.pipeline,
                "has_visualization": r.has_visualization
            }
            for r in results
        ]
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Results saved to: {filename}")


async def main():
    """Main entry point."""

    results = await run_all_tests()

    if not results:
        print("\n❌ No tests were run. Check service availability.")
        sys.exit(1)

    # Print summary
    all_passed = print_summary(results)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_results(results, f"metrics_catalog_results_{timestamp}.json")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
