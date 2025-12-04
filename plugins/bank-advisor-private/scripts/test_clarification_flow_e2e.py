#!/usr/bin/env python3
"""
E2E Test Script: Clarification Flow & All Metrics Validation

Tests:
1. All 17 metrics with complete queries (should return data)
2. All 17 metrics with incomplete queries (should return clarification)
3. Combined query simulation (original + clarification response)
4. Edge cases and robustness

Usage:
    python scripts/test_clarification_flow_e2e.py
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field

# Configuration
BASE_URL = "http://localhost:8002"
TIMEOUT = 30.0

# All 17 metrics from the catalog
METRICS_CATALOG = [
    {
        "name": "Cartera Comercial CC",
        "complete_query": "Cartera comercial de INVEX últimos 6 meses",
        "incomplete_query": "Cartera comercial",
        "clarification_response": "de INVEX últimos 6 meses"
    },
    {
        "name": "Cartera Comercial Sin Gob",
        "complete_query": "Cartera comercial sin gobierno de INVEX últimos 6 meses",
        "incomplete_query": "Cartera comercial sin gobierno",
        "clarification_response": "de INVEX 2024"
    },
    {
        "name": "Pérdida Esperada Total",
        "complete_query": "Pérdida esperada de INVEX últimos 6 meses",
        "incomplete_query": "Pérdida esperada total",
        "clarification_response": "INVEX últimos 12 meses"
    },
    {
        "name": "Reservas Totales",
        "complete_query": "Reservas totales de INVEX últimos 6 meses",
        "incomplete_query": "Reservas totales",
        "clarification_response": "de INVEX 2024"
    },
    {
        "name": "Reservas Totales (Variación)",
        "complete_query": "Variación de reservas INVEX últimos 6 meses",
        "incomplete_query": "Reservas Totales (Variación)",
        "clarification_response": "INVEX últimos 6 meses"
    },
    {
        "name": "IMOR",
        "complete_query": "IMOR de INVEX últimos 6 meses",
        "incomplete_query": "IMOR",
        "clarification_response": "de INVEX últimos 6 meses"
    },
    {
        "name": "Cartera Vencida",
        "complete_query": "Cartera vencida de INVEX últimos 6 meses",
        "incomplete_query": "Cartera vencida",
        "clarification_response": "INVEX 2024"
    },
    {
        "name": "ICOR",
        "complete_query": "ICOR de INVEX últimos 6 meses",
        "incomplete_query": "ICOR",
        "clarification_response": "de INVEX últimos 12 meses"
    },
    {
        "name": "Etapas de Deterioro (Sistema)",
        "complete_query": "Etapas de deterioro del sistema últimos 6 meses",
        "incomplete_query": "Etapas de deterioro sistema",
        "clarification_response": "últimos 6 meses"
    },
    {
        "name": "Etapas de Deterioro (INVEX)",
        "complete_query": "Etapas de deterioro INVEX últimos 6 meses",
        "incomplete_query": "Etapas de deterioro INVEX",
        "clarification_response": "últimos 6 meses"
    },
    {
        "name": "Quebrantos Comerciales",
        "complete_query": "Quebrantos comerciales INVEX últimos 6 meses",
        "incomplete_query": "Quebrantos comerciales",
        "clarification_response": "de INVEX 2024"
    },
    {
        "name": "ICAP",
        "complete_query": "ICAP de INVEX últimos 6 meses",
        "incomplete_query": "ICAP",
        "clarification_response": "INVEX últimos 6 meses"
    },
    {
        "name": "Tasa de Deterioro Ajustada",
        "complete_query": "TDA de INVEX últimos 6 meses",
        "incomplete_query": "Tasa de deterioro ajustada",
        "clarification_response": "de INVEX últimos 6 meses"
    },
    {
        "name": "Tasa Interés Efectiva (Sistema)",
        "complete_query": "Tasa efectiva del sistema últimos 12 meses",
        "incomplete_query": "Tasa efectiva sistema",
        "clarification_response": "últimos 12 meses"
    },
    {
        "name": "Tasa Interés Efectiva (INVEX Consumo)",
        "complete_query": "Tasa INVEX consumo últimos 6 meses",
        "incomplete_query": "Tasa INVEX consumo",
        "clarification_response": "últimos 6 meses"
    },
    {
        "name": "Tasa Crédito Corporativo (MN)",
        "complete_query": "Tasa corporativa moneda nacional INVEX últimos 6 meses",
        "incomplete_query": "Tasa corporativa MN",
        "clarification_response": "de INVEX últimos 6 meses"
    },
    {
        "name": "Tasa Crédito Corporativo (ME)",
        "complete_query": "Tasa corporativa moneda extranjera INVEX últimos 6 meses",
        "incomplete_query": "Tasa corporativa ME",
        "clarification_response": "INVEX 2024"
    },
]

# Edge cases for robustness testing
EDGE_CASES = [
    {"name": "Empty query", "query": ""},
    {"name": "Only spaces", "query": "   "},
    {"name": "Special characters", "query": "IMOR @#$% INVEX"},
    {"name": "Very long query", "query": "Muéstrame el IMOR de INVEX " * 20},
    {"name": "SQL injection attempt", "query": "IMOR; DROP TABLE monthly_kpis;--"},
    {"name": "Mixed case", "query": "ImOr De InVeX úLtImOs 6 MeSeS"},
    {"name": "Numbers in query", "query": "IMOR 2024 INVEX 6 meses"},
    {"name": "Unicode characters", "query": "IMOR de INVEX últimos 6 meses 日本語"},
    {"name": "Multiple banks", "query": "Comparar IMOR INVEX vs Banorte 2024"},
    {"name": "Ambiguous metric", "query": "cartera"},
    {"name": "Only time range", "query": "últimos 6 meses"},
    {"name": "Only bank name", "query": "INVEX"},
]


@dataclass
class TestResult:
    """Test result container"""
    test_name: str
    query: str
    success: bool
    response_type: str  # "data", "clarification", "error"
    response_time_ms: float
    error: str = None
    details: Dict = field(default_factory=dict)


class ClarificationFlowTester:
    """E2E tester for clarification flow"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.results: List[TestResult] = []

    async def _call_bank_analytics(
        self,
        query: str,
        mode: str = "chart"
    ) -> Tuple[Dict, float]:
        """Call bank_analytics RPC endpoint"""
        start = datetime.now()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/rpc",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "bank_analytics",
                        "arguments": {
                            "metric_or_query": query,
                            "mode": mode
                        }
                    },
                    "id": 1
                },
                timeout=TIMEOUT
            )

        elapsed_ms = (datetime.now() - start).total_seconds() * 1000

        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}"}, elapsed_ms

        rpc_response = response.json()

        if "error" in rpc_response:
            return {"error": rpc_response["error"]}, elapsed_ms

        # Parse the nested JSON from MCP response
        try:
            content = rpc_response["result"]["content"][0]["text"]
            result = json.loads(content)
            return result, elapsed_ms
        except (KeyError, json.JSONDecodeError) as e:
            return {"error": f"Parse error: {str(e)}"}, elapsed_ms

    def _classify_response(self, result: Dict) -> str:
        """Classify response type"""
        if "error" in result and not result.get("success"):
            return "error"

        data = result.get("data", {})
        if isinstance(data, dict):
            if data.get("type") == "clarification":
                return "clarification"
            if data.get("plotly_config") or data.get("months"):
                return "data"
            if data.get("error"):
                return "error"

        if result.get("success") and result.get("data"):
            return "data"

        return "unknown"

    async def test_complete_queries(self) -> List[TestResult]:
        """Test all metrics with complete queries - should return data"""
        print("\n" + "="*60)
        print("TEST 1: Complete Queries (expecting data)")
        print("="*60)

        results = []
        for metric in METRICS_CATALOG:
            query = metric["complete_query"]
            result, elapsed_ms = await self._call_bank_analytics(query)
            response_type = self._classify_response(result)

            success = response_type == "data"
            test_result = TestResult(
                test_name=f"Complete: {metric['name']}",
                query=query,
                success=success,
                response_type=response_type,
                response_time_ms=elapsed_ms,
                error=result.get("error") if not success else None,
                details={"data_points": len(result.get("data", {}).get("months", [])) if success else 0}
            )
            results.append(test_result)

            status = "✅" if success else "❌"
            print(f"  {status} {metric['name']}: {response_type} ({elapsed_ms:.1f}ms)")

        return results

    async def test_incomplete_queries(self) -> List[TestResult]:
        """Test all metrics with incomplete queries - should return clarification"""
        print("\n" + "="*60)
        print("TEST 2: Incomplete Queries (expecting clarification)")
        print("="*60)

        results = []
        for metric in METRICS_CATALOG:
            query = metric["incomplete_query"]
            result, elapsed_ms = await self._call_bank_analytics(query)
            response_type = self._classify_response(result)

            # Incomplete queries should either return clarification OR data (if parser is smart)
            success = response_type in ["clarification", "data"]

            test_result = TestResult(
                test_name=f"Incomplete: {metric['name']}",
                query=query,
                success=success,
                response_type=response_type,
                response_time_ms=elapsed_ms,
                error=result.get("error") if response_type == "error" else None,
                details={
                    "has_options": len(result.get("data", {}).get("options", [])) > 0 if response_type == "clarification" else False,
                    "original_query_preserved": result.get("data", {}).get("context", {}).get("original_query") == query
                }
            )
            results.append(test_result)

            status = "✅" if success else "❌"
            indicator = "📋" if response_type == "clarification" else "📊" if response_type == "data" else "⚠️"
            print(f"  {status} {indicator} {metric['name']}: {response_type} ({elapsed_ms:.1f}ms)")

        return results

    async def test_combined_queries(self) -> List[TestResult]:
        """Test combined queries (simulating clarification + response)"""
        print("\n" + "="*60)
        print("TEST 3: Combined Queries (original + clarification)")
        print("="*60)

        results = []
        for metric in METRICS_CATALOG:
            # Combine incomplete query with clarification response
            combined = f"{metric['incomplete_query']} {metric['clarification_response']}"
            result, elapsed_ms = await self._call_bank_analytics(combined)
            response_type = self._classify_response(result)

            success = response_type == "data"

            test_result = TestResult(
                test_name=f"Combined: {metric['name']}",
                query=combined,
                success=success,
                response_type=response_type,
                response_time_ms=elapsed_ms,
                error=result.get("error") if not success else None
            )
            results.append(test_result)

            status = "✅" if success else "❌"
            print(f"  {status} {metric['name']}: {response_type} ({elapsed_ms:.1f}ms)")

        return results

    async def test_edge_cases(self) -> List[TestResult]:
        """Test edge cases for robustness"""
        print("\n" + "="*60)
        print("TEST 4: Edge Cases (robustness)")
        print("="*60)

        results = []
        for case in EDGE_CASES:
            query = case["query"]
            try:
                result, elapsed_ms = await self._call_bank_analytics(query)
                response_type = self._classify_response(result)

                # Edge cases should NOT crash - any response is acceptable
                success = response_type in ["data", "clarification", "error"]
                error = None
            except Exception as e:
                success = False
                response_type = "exception"
                elapsed_ms = 0
                error = str(e)

            test_result = TestResult(
                test_name=f"Edge: {case['name']}",
                query=query[:50] + "..." if len(query) > 50 else query,
                success=success,
                response_type=response_type,
                response_time_ms=elapsed_ms,
                error=error
            )
            results.append(test_result)

            status = "✅" if success else "❌"
            print(f"  {status} {case['name']}: {response_type} ({elapsed_ms:.1f}ms)")

        return results

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all test suites"""
        print("\n" + "="*60)
        print("BANK ADVISOR CLARIFICATION FLOW E2E TESTS")
        print(f"Started: {datetime.now().isoformat()}")
        print("="*60)

        # Check service health first
        try:
            async with httpx.AsyncClient() as client:
                health = await client.get(f"{self.base_url}/health", timeout=5.0)
                if health.status_code != 200:
                    print(f"❌ Service unhealthy: {health.status_code}")
                    return {"error": "Service unhealthy"}
                print(f"✅ Service healthy")
        except Exception as e:
            print(f"❌ Service unavailable: {e}")
            return {"error": f"Service unavailable: {e}"}

        # Run test suites
        all_results = []

        complete_results = await self.test_complete_queries()
        all_results.extend(complete_results)

        incomplete_results = await self.test_incomplete_queries()
        all_results.extend(incomplete_results)

        combined_results = await self.test_combined_queries()
        all_results.extend(combined_results)

        edge_results = await self.test_edge_cases()
        all_results.extend(edge_results)

        # Generate summary
        total = len(all_results)
        passed = sum(1 for r in all_results if r.success)
        failed = total - passed

        avg_time = sum(r.response_time_ms for r in all_results) / total if total > 0 else 0

        # Count by response type
        by_type = {}
        for r in all_results:
            by_type[r.response_type] = by_type.get(r.response_type, 0) + 1

        # Categorize results
        complete_passed = sum(1 for r in complete_results if r.success)
        incomplete_passed = sum(1 for r in incomplete_results if r.success)
        combined_passed = sum(1 for r in combined_results if r.success)
        edge_passed = sum(1 for r in edge_results if r.success)

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed/total)*100:.1f}%" if total > 0 else "N/A",
            "avg_response_time_ms": round(avg_time, 2),
            "by_category": {
                "complete_queries": f"{complete_passed}/{len(complete_results)}",
                "incomplete_queries": f"{incomplete_passed}/{len(incomplete_results)}",
                "combined_queries": f"{combined_passed}/{len(combined_results)}",
                "edge_cases": f"{edge_passed}/{len(edge_results)}"
            },
            "by_response_type": by_type,
            "failed_tests": [
                {"name": r.test_name, "query": r.query, "error": r.error, "type": r.response_type}
                for r in all_results if not r.success
            ]
        }

        # Print summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total:    {total}")
        print(f"Passed:   {passed} ({summary['pass_rate']})")
        print(f"Failed:   {failed}")
        print(f"Avg Time: {avg_time:.1f}ms")
        print()
        print("By Category:")
        for cat, score in summary["by_category"].items():
            print(f"  {cat}: {score}")
        print()
        print("By Response Type:")
        for rtype, count in by_type.items():
            print(f"  {rtype}: {count}")

        if summary["failed_tests"]:
            print()
            print("Failed Tests:")
            for ft in summary["failed_tests"][:10]:  # Show first 10
                print(f"  ❌ {ft['name']}: {ft['type']} - {ft['error'] or 'unexpected response'}")

        # Save results
        output_file = f"clarification_flow_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n📄 Results saved to: {output_file}")

        return summary


async def main():
    tester = ClarificationFlowTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
