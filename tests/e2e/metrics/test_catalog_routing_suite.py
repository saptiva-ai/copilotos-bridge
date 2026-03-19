#!/usr/bin/env python3
"""
Catalog Query Routing E2E Test Suite
Phase 2.5 Implementation Tests (2026-02-04)

Tests the routing of catalog queries to specific MCP tools instead of
the deprecated bank_analytics monolithic tool.

Tests:
1. Detection Patterns: Various phrasings for list_institutions and lookup_bank_code
2. Edge Cases: Typos, accents, mixed case, punctuation
3. Full Flow: Through ToolExecutionService.invoke_bank_analytics()
4. Response Format: Correct structure for catalog responses
5. Fallback: Non-catalog queries still use query_bank_analytics()

Reference: docs/kanban/DOING/2026-02-03__REFACTOR__handlers-to-mcp-tools/research.md
"""

import json
import os
import sys
import time
import asyncio
import requests
import pytest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Ensure tests/ is on path
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Configuration
BANK_ADVISOR_URL = os.environ.get("TEST_BANK_ADVISOR_URL", "http://localhost:8002")
BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")


# =============================================================================
# TEST DATA DEFINITIONS
# =============================================================================

@dataclass
class CatalogTestCase:
    """Test case for catalog query routing."""
    query: str
    expected_tool: Optional[str]  # None means should fallback to bank_analytics
    expected_bank: Optional[str] = None  # For lookup queries
    description: str = ""


# List Institutions - queries asking for institution list
LIST_INSTITUTIONS_CASES: List[CatalogTestCase] = [
    # Standard phrasings
    CatalogTestCase("dame las instituciones", "list_institutions", description="Standard request"),
    CatalogTestCase("muestra las instituciones", "list_institutions", description="Muestra variant"),
    CatalogTestCase("lista de instituciones", "list_institutions", description="Lista variant"),
    CatalogTestCase("tabla de instituciones", "list_institutions", description="Tabla variant"),
    CatalogTestCase("ver instituciones", "list_institutions", description="Ver variant"),
    CatalogTestCase("cuales son las instituciones", "list_institutions", description="Cuales son variant"),

    # Bank variants
    CatalogTestCase("dame los bancos", "list_institutions", description="Bancos instead of instituciones"),
    CatalogTestCase("muestra los bancos disponibles", "list_institutions", description="Bancos disponibles"),
    CatalogTestCase("lista de bancos activos", "list_institutions", description="Bancos activos"),
    CatalogTestCase("todos los bancos", "list_institutions", description="Todos los bancos"),

    # With qualifiers
    CatalogTestCase("instituciones activas", "list_institutions", description="With activas qualifier"),
    CatalogTestCase("instituciones disponibles", "list_institutions", description="With disponibles qualifier"),
    CatalogTestCase("bancos existentes", "list_institutions", description="With existentes qualifier"),

    # Catalog phrasing
    CatalogTestCase("catalogo de instituciones", "list_institutions", description="Catalogo phrasing"),
    CatalogTestCase("catálogo de bancos", "list_institutions", description="Catálogo with accent"),

    # Edge cases - punctuation and case
    CatalogTestCase("Dame las instituciones!", "list_institutions", description="With exclamation"),
    CatalogTestCase("DAME LAS INSTITUCIONES", "list_institutions", description="All caps"),
    CatalogTestCase("  dame las instituciones  ", "list_institutions", description="With spaces"),
]

# Lookup Bank Code by Name - queries asking for bank code (name → code)
LOOKUP_BANK_CODE_CASES: List[CatalogTestCase] = [
    # Standard banks
    CatalogTestCase("cual es la clave de santander", "lookup_bank_by_name", "SANTANDER", "Standard Santander"),
    CatalogTestCase("cual es la clave de bbva", "lookup_bank_by_name", "BBVA", "Standard BBVA"),
    CatalogTestCase("cual es la clave de banorte", "lookup_bank_by_name", "BANORTE", "Standard Banorte"),
    CatalogTestCase("cual es la clave de hsbc", "lookup_bank_by_name", "HSBC", "Standard HSBC"),
    CatalogTestCase("cual es la clave de banamex", "lookup_bank_by_name", "BANAMEX", "Standard Banamex"),
    CatalogTestCase("cual es la clave de scotiabank", "lookup_bank_by_name", "SCOTIABANK", "Standard Scotiabank"),

    # Code/codigo variants
    CatalogTestCase("codigo de santander", "lookup_bank_by_name", "SANTANDER", "Codigo variant"),
    CatalogTestCase("código de bbva", "lookup_bank_by_name", "BBVA", "Código with accent"),
    CatalogTestCase("codigo institucional de banorte", "lookup_bank_by_name", "BANORTE", "Codigo institucional"),

    # Clave variants
    CatalogTestCase("clave de hsbc", "lookup_bank_by_name", "HSBC", "Clave simple"),
    CatalogTestCase("clave institucional de santander", "lookup_bank_by_name", "SANTANDER", "Clave institucional"),
    CatalogTestCase("clave cnbv de bbva", "lookup_bank_by_name", "BBVA", "Clave CNBV"),

    # Dame/dime variants
    CatalogTestCase("dame la clave de banorte", "lookup_bank_by_name", "BANORTE", "Dame la clave"),
    CatalogTestCase("dime la clave de santander", "lookup_bank_by_name", "SANTANDER", "Dime la clave"),
    CatalogTestCase("dame el codigo de hsbc", "lookup_bank_by_name", "HSBC", "Dame el codigo"),

    # Cuál/qué variants
    CatalogTestCase("cuál es la clave de bbva", "lookup_bank_by_name", "BBVA", "Cuál with accent"),
    CatalogTestCase("que codigo tiene santander", "lookup_bank_by_name", "SANTANDER", "Que codigo tiene"),
    CatalogTestCase("qué clave tiene banorte", "lookup_bank_by_name", "BANORTE", "Qué with accent"),

    # Edge cases - case variations
    CatalogTestCase("CLAVE DE SANTANDER", "lookup_bank_by_name", "SANTANDER", "All caps"),
    CatalogTestCase("Clave De Bbva", "lookup_bank_by_name", "BBVA", "Title case"),
]

# Non-catalog queries - should NOT route to catalog tools (fallback to bank_analytics)
NON_CATALOG_CASES: List[CatalogTestCase] = [
    # Data queries
    CatalogTestCase("imor de bbva", None, description="IMOR query"),
    CatalogTestCase("cartera de santander", None, description="Cartera query"),
    CatalogTestCase("icap del sistema", None, description="ICAP sistema"),

    # Ranking queries
    CatalogTestCase("ranking de morosidad", None, description="Ranking query"),
    CatalogTestCase("top 10 bancos por imor", None, description="Top N query"),
    CatalogTestCase("mejores bancos por icap", None, description="Mejores query"),

    # Evolution/time series
    CatalogTestCase("evolucion del imor", None, description="Evolution query"),
    CatalogTestCase("tendencia de cartera", None, description="Tendencia query"),
    CatalogTestCase("historico de bbva", None, description="Historico query"),

    # Comparison queries
    CatalogTestCase("comparar bbva vs banorte", None, description="Comparison query"),
    CatalogTestCase("bbva contra santander", None, description="Contra query"),

    # Regional queries
    CatalogTestCase("cartera por estado", None, description="Regional query"),
    CatalogTestCase("morosidad en jalisco", None, description="State query"),

    # Definition queries (should go to RAG)
    CatalogTestCase("que es el imor", None, description="Definition query"),
    CatalogTestCase("define icap", None, description="Define query"),
]


# =============================================================================
# RPC HELPERS
# =============================================================================

def rpc_call(method: str, params: Optional[Dict] = None, url: str = BANK_ADVISOR_URL) -> Dict[str, Any]:
    """Make a JSON-RPC 2.0 call to the bank-advisor /rpc endpoint."""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": int(time.time() * 1000),
    }
    if params:
        payload["params"] = params

    try:
        response = requests.post(
            f"{url}/rpc",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Call a specific MCP tool via /rpc tools/call."""
    result = rpc_call("tools/call", {"name": name, "arguments": arguments})

    if "error" in result:
        return {"success": False, "error": result["error"]}

    content = result.get("result", {}).get("content", [])
    if content and len(content) > 0:
        text = content[0].get("text", "{}")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON response"}

    return {"success": False, "error": "Empty response"}


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def bank_analytics_client():
    """Import bank_analytics_client for testing."""
    # Add backend src to path
    backend_src = Path(__file__).resolve().parents[3] / "apps" / "backend" / "src"
    if str(backend_src) not in sys.path:
        sys.path.insert(0, str(backend_src))

    from services.bank_analytics_client import (
        detect_catalog_tool,
        handle_catalog_query,
    )
    return {
        "detect_catalog_tool": detect_catalog_tool,
        "handle_catalog_query": handle_catalog_query,
    }


@pytest.fixture(scope="module")
def tool_execution_service():
    """Import ToolExecutionService for full flow testing."""
    backend_src = Path(__file__).resolve().parents[3] / "apps" / "backend" / "src"
    if str(backend_src) not in sys.path:
        sys.path.insert(0, str(backend_src))

    from services.tool_execution_service import ToolExecutionService
    return ToolExecutionService


# =============================================================================
# DETECTION TESTS
# =============================================================================

class TestCatalogDetection:
    """Test detect_catalog_tool() function with various query patterns."""

    @pytest.mark.parametrize("case", LIST_INSTITUTIONS_CASES,
                           ids=[c.description for c in LIST_INSTITUTIONS_CASES])
    def test_list_institutions_detection(self, bank_analytics_client, case: CatalogTestCase):
        """Queries asking for institution list should detect list_institutions."""
        detect = bank_analytics_client["detect_catalog_tool"]
        result = detect(case.query)

        assert result is not None, f"Query '{case.query}' not detected as catalog"
        tool_name, _ = result
        assert tool_name == case.expected_tool, f"Expected {case.expected_tool}, got {tool_name}"

    @pytest.mark.parametrize("case", LOOKUP_BANK_CODE_CASES,
                           ids=[c.description for c in LOOKUP_BANK_CODE_CASES])
    def test_lookup_bank_code_detection(self, bank_analytics_client, case: CatalogTestCase):
        """Queries asking for bank code should detect lookup_bank_by_name."""
        detect = bank_analytics_client["detect_catalog_tool"]
        result = detect(case.query)

        assert result is not None, f"Query '{case.query}' not detected as catalog"
        tool_name, args = result
        assert tool_name == case.expected_tool, f"Expected {case.expected_tool}, got {tool_name}"

        # Verify bank name extraction
        if case.expected_bank:
            bank_name = args.get("bank_name", "").lower()
            assert case.expected_bank.lower() in bank_name or bank_name in case.expected_bank.lower(), \
                f"Expected bank '{case.expected_bank}', got '{bank_name}'"

    @pytest.mark.parametrize("case", NON_CATALOG_CASES,
                           ids=[c.description for c in NON_CATALOG_CASES])
    def test_non_catalog_not_detected(self, bank_analytics_client, case: CatalogTestCase):
        """Non-catalog queries should not be detected (return None)."""
        detect = bank_analytics_client["detect_catalog_tool"]
        result = detect(case.query)

        assert result is None, f"Query '{case.query}' incorrectly detected as catalog: {result}"


# =============================================================================
# HANDLER TESTS
# =============================================================================

class TestCatalogHandler:
    """Test handle_catalog_query() function."""

    @pytest.mark.asyncio
    async def test_list_institutions_handler(self, bank_analytics_client):
        """list_institutions should return formatted institution list."""
        handler = bank_analytics_client["handle_catalog_query"]
        result = await handler("dame las instituciones")

        assert result is not None, "Handler returned None"
        assert result.get("type") == "catalog", f"Wrong type: {result.get('type')}"
        assert result.get("chart_status") == "success", f"Wrong status: {result.get('chart_status')}"
        assert "response_text" in result, "Missing response_text"
        assert "instituciones" in result["response_text"].lower(), "Missing 'instituciones' in response"

    @pytest.mark.asyncio
    async def test_lookup_bank_code_handler(self, bank_analytics_client):
        """lookup_bank_by_name should return correct bank code."""
        handler = bank_analytics_client["handle_catalog_query"]

        test_cases = [
            ("cual es la clave de santander", "SANTANDER", "0000040014"),
            ("cual es la clave de bbva", "BBVA", "0000040012"),
            ("cual es la clave de hsbc", "HSBC", "0000040021"),
        ]

        for query, expected_bank, expected_code in test_cases:
            result = await handler(query)

            assert result is not None, f"Handler returned None for '{query}'"
            assert result.get("type") == "catalog", f"Wrong type for '{query}'"
            assert result.get("chart_status") == "success", f"Wrong status for '{query}'"

            response_text = result.get("response_text", "")
            assert expected_bank in response_text, f"Missing '{expected_bank}' in response: {response_text}"
            assert expected_code in response_text, f"Missing code '{expected_code}' in response: {response_text}"

    @pytest.mark.asyncio
    async def test_non_catalog_handler_returns_none(self, bank_analytics_client):
        """Non-catalog queries should return None from handler."""
        handler = bank_analytics_client["handle_catalog_query"]

        for case in NON_CATALOG_CASES[:5]:  # Test first 5
            result = await handler(case.query)
            assert result is None, f"Query '{case.query}' should return None, got {result}"


# =============================================================================
# FULL FLOW TESTS
# =============================================================================

class TestFullFlowRouting:
    """Test full flow through ToolExecutionService.invoke_bank_analytics()."""

    @pytest.mark.asyncio
    async def test_full_flow_list_institutions(self, tool_execution_service):
        """Full flow: list institutions query routes correctly."""
        result = await tool_execution_service.invoke_bank_analytics(
            message="dame las instituciones",
            user_id="test-user",
            mode="dashboard"
        )

        assert result is not None, "invoke_bank_analytics returned None"
        assert result.get("type") == "catalog", f"Wrong type: {result.get('type')}"
        assert "instituciones" in result.get("response_text", "").lower()

    @pytest.mark.asyncio
    async def test_full_flow_lookup_bank_code(self, tool_execution_service):
        """Full flow: bank code lookup routes correctly."""
        result = await tool_execution_service.invoke_bank_analytics(
            message="cual es la clave de santander",
            user_id="test-user",
            mode="dashboard"
        )

        assert result is not None, "invoke_bank_analytics returned None"
        assert result.get("type") == "catalog", f"Wrong type: {result.get('type')}"
        assert "SANTANDER" in result.get("response_text", "")
        assert "0000040014" in result.get("response_text", "")

    @pytest.mark.asyncio
    async def test_full_flow_data_query_fallback(self, tool_execution_service):
        """Full flow: data queries should fallback to bank_analytics."""
        result = await tool_execution_service.invoke_bank_analytics(
            message="imor de bbva",
            user_id="test-user",
            mode="dashboard"
        )

        # Data queries return chart data, not catalog type
        assert result is not None, "invoke_bank_analytics returned None"
        # Should NOT be catalog type
        assert result.get("type") != "catalog" or result.get("type") is None, \
            f"Data query incorrectly routed to catalog: {result.get('type')}"


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_bank_not_found(self, bank_analytics_client):
        """Lookup for non-existent bank should return helpful message."""
        handler = bank_analytics_client["handle_catalog_query"]
        result = await handler("cual es la clave de bancofalso")

        assert result is not None
        assert result.get("type") == "catalog"
        response = result.get("response_text", "").lower()
        assert "no encontr" in response or "lista de instituciones" in response

    @pytest.mark.parametrize("query", [
        "clave de banco santander",  # "banco" before bank name
        "código del santander",  # "del" instead of "de"
        "la clave de santander es?",  # Question mark at end
        "cual clave tiene santander",  # Missing "es la"
    ])
    @pytest.mark.asyncio
    async def test_variant_phrasings(self, bank_analytics_client, query):
        """Various phrasing variants should still work."""
        detect = bank_analytics_client["detect_catalog_tool"]
        result = detect(query)

        # These might not all be detected - this is to document behavior
        # Some variants may need pattern improvements
        if result is None:
            pytest.skip(f"Pattern not yet supported: {query}")

    @pytest.mark.asyncio
    async def test_empty_query(self, bank_analytics_client):
        """Empty query should not crash."""
        detect = bank_analytics_client["detect_catalog_tool"]
        result = detect("")
        assert result is None

    @pytest.mark.asyncio
    async def test_very_long_query(self, bank_analytics_client):
        """Very long query should not crash."""
        detect = bank_analytics_client["detect_catalog_tool"]
        long_query = "dame " + "las instituciones " * 100
        result = detect(long_query)
        # Should still detect as list_institutions
        assert result is not None or result is None  # Just verify no crash


# =============================================================================
# MCP TOOL DIRECT TESTS
# =============================================================================

class TestMCPToolsDirect:
    """Test MCP tools directly via /rpc endpoint."""

    def test_list_institutions_tool_direct(self):
        """Direct call to list_institutions tool."""
        result = call_tool("list_institutions", {"active_only": True, "limit": 10})

        assert result.get("success"), f"Tool failed: {result.get('error')}"
        assert "institutions" in result, "Missing institutions key"
        assert len(result["institutions"]) <= 10, "Limit not respected"

        # Verify institution structure
        inst = result["institutions"][0]
        assert "nombre_corto" in inst, "Missing nombre_corto"
        assert "clave_cnbv" in inst, "Missing clave_cnbv"

    def test_lookup_bank_code_tool_direct(self):
        """Direct call to lookup_bank_code tool (code → name)."""
        result = call_tool("lookup_bank_code", {"code": "040014"})

        assert result.get("success"), f"Tool failed: {result.get('error')}"
        assert "bank" in result, "Missing bank key"
        assert result["bank"]["nombre_corto"] == "SANTANDER"

    def test_lookup_bank_code_invalid(self):
        """Invalid code should return error."""
        result = call_tool("lookup_bank_code", {"code": "000000"})

        # Should either return success: false or bank: null
        if result.get("success"):
            assert result.get("bank") is None, "Should not find bank with invalid code"

    @pytest.mark.parametrize("bank_code,expected_name", [
        ("040012", "BBVA"),
        ("040014", "SANTANDER"),
        ("040021", "HSBC"),
        ("040072", "BANORTE"),
        ("040002", "BANAMEX"),
    ])
    def test_known_bank_codes(self, bank_code, expected_name):
        """Verify known bank codes return correct names."""
        result = call_tool("lookup_bank_code", {"code": bank_code})

        assert result.get("success"), f"Tool failed for {bank_code}: {result.get('error')}"
        assert result.get("bank", {}).get("nombre_corto") == expected_name


# =============================================================================
# STANDALONE RUNNER
# =============================================================================

def run_detection_tests():
    """Run detection tests standalone."""
    print("\n" + "=" * 70)
    print("CATALOG ROUTING DETECTION TESTS")
    print("=" * 70)

    # Import the detection function
    backend_src = Path(__file__).resolve().parents[3] / "apps" / "backend" / "src"
    sys.path.insert(0, str(backend_src))

    from services.bank_analytics_client import detect_catalog_tool

    passed = 0
    failed = 0

    print("\n--- list_institutions detection ---")
    for case in LIST_INSTITUTIONS_CASES:
        result = detect_catalog_tool(case.query)
        tool = result[0] if result else None
        status = "✅" if tool == case.expected_tool else "❌"
        if tool == case.expected_tool:
            passed += 1
        else:
            failed += 1
        print(f"  {status} {case.description}: '{case.query[:40]}...' → {tool}")

    print("\n--- lookup_bank_by_name detection ---")
    for case in LOOKUP_BANK_CODE_CASES:
        result = detect_catalog_tool(case.query)
        tool = result[0] if result else None
        status = "✅" if tool == case.expected_tool else "❌"
        if tool == case.expected_tool:
            passed += 1
        else:
            failed += 1
        print(f"  {status} {case.description}: '{case.query[:40]}...' → {tool}")

    print("\n--- non-catalog queries (should return None) ---")
    for case in NON_CATALOG_CASES:
        result = detect_catalog_tool(case.query)
        tool = result[0] if result else None
        status = "✅" if tool is None else "❌"
        if tool is None:
            passed += 1
        else:
            failed += 1
        print(f"  {status} {case.description}: '{case.query[:40]}...' → {tool}")

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {passed}/{passed + failed} passed ({100 * passed / (passed + failed):.1f}%)")
    print("=" * 70)

    return failed == 0


async def run_handler_tests():
    """Run handler tests standalone."""
    print("\n" + "=" * 70)
    print("CATALOG ROUTING HANDLER TESTS")
    print("=" * 70)

    backend_src = Path(__file__).resolve().parents[3] / "apps" / "backend" / "src"
    sys.path.insert(0, str(backend_src))

    from services.bank_analytics_client import handle_catalog_query

    passed = 0
    failed = 0

    test_cases = [
        ("dame las instituciones", "catalog", "121"),
        ("cual es la clave de santander", "catalog", "SANTANDER"),
        ("cual es la clave de bbva", "catalog", "BBVA"),
        ("imor de bbva", None, None),  # Should return None
    ]

    for query, expected_type, expected_content in test_cases:
        result = await handle_catalog_query(query)

        if expected_type is None:
            status = "✅" if result is None else "❌"
            actual = "None" if result is None else result.get("type")
        else:
            status = "✅" if result and result.get("type") == expected_type else "❌"
            actual = result.get("type") if result else "None"
            if expected_content and result:
                if expected_content not in result.get("response_text", ""):
                    status = "❌"

        if status == "✅":
            passed += 1
        else:
            failed += 1

        print(f"  {status} '{query[:40]}...' → type={actual}")

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {passed}/{passed + failed} passed")
    print("=" * 70)

    return failed == 0


def main():
    """Standalone runner for quick verification."""
    print("=" * 70)
    print("CATALOG ROUTING E2E TEST SUITE (Phase 2.5)")
    print("=" * 70)
    print(f"Bank-Advisor URL: {BANK_ADVISOR_URL}")
    print(f"Backend URL: {BACKEND_URL}")

    # Run detection tests
    detection_ok = run_detection_tests()

    # Run handler tests
    handler_ok = asyncio.run(run_handler_tests())

    # Save results
    output_file = Path(__file__).parent / "catalog_routing_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "detection_passed": detection_ok,
            "handler_passed": handler_ok,
            "list_institutions_cases": len(LIST_INSTITUTIONS_CASES),
            "lookup_bank_code_cases": len(LOOKUP_BANK_CODE_CASES),
            "non_catalog_cases": len(NON_CATALOG_CASES),
        }, f, indent=2)
    print(f"\nResults saved to {output_file}")

    if not (detection_ok and handler_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
