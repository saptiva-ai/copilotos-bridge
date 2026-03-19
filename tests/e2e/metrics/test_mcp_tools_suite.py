#!/usr/bin/env python3
"""
MCP Tools Test Suite - Bank Advisor
Validates the granular MCP tools architecture introduced in REFACTOR-2026-02-03.

Tests:
1. Tool Discovery: All 21 active tools are registered via /rpc tools/list
2. Tool Execution: Each tool returns valid data via /rpc tools/call
3. Backend Integration: LLM system prompt includes tool documentation
4. Deprecation: bank_analytics is marked deprecated

Reference: docs/kanban/DOING/2026-02-03__REFACTOR__handlers-to-mcp-tools/card.md
"""

import json
import os
import sys
import time
import requests
import pytest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure tests/ is on path for shared utils
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Configuration
BANK_ADVISOR_URL = os.environ.get("TEST_BANK_ADVISOR_URL", "http://localhost:8002")
BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")


# --- DEFINITIONS ---

@dataclass
class ToolDef:
    """Definition of an MCP tool for validation."""
    name: str
    category: str
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    test_args: Dict[str, Any] = field(default_factory=dict)
    expected_keys: List[str] = field(default_factory=list)


# Expected tools from the refactor (21 active + 1 deprecated)
EXPECTED_TOOLS: List[ToolDef] = [
    # Catalog Tools
    ToolDef("list_institutions", "catalog", test_args={}, expected_keys=["institutions", "total"]),
    ToolDef("lookup_bank_code", "catalog", required_params=["code"], test_args={"code": "040012"}, expected_keys=["bank"]),

    # Meta Tools
    ToolDef("get_available_metrics", "meta", test_args={}, expected_keys=["metrics"]),
    ToolDef("get_data_freshness", "meta", test_args={}, expected_keys=["data_freshness"]),

    # Regional Tools
    ToolDef("get_regional_portfolio", "regional", test_args={"banco": "BBVA"}, expected_keys=[]),
    ToolDef("get_region_breakdown", "regional", test_args={}, expected_keys=[]),

    # Ranking Tools
    ToolDef("get_metric_ranking", "ranking", required_params=["metric"], test_args={"metric": "imor", "top_n": 5}, expected_keys=[]),
    ToolDef("get_segment_ranking", "ranking", required_params=["segment"], test_args={"segment": "comercial", "top_n": 5}, expected_keys=[]),

    # Comparison Tools
    ToolDef("compare_banks", "comparison", required_params=["banks", "metrics"], test_args={"banks": ["BBVA", "BANORTE"], "metrics": ["imor", "icap"]}, expected_keys=[]),
    ToolDef("compare_bank_evolution", "comparison", required_params=["banks", "metric"], test_args={"banks": ["BBVA", "BANORTE"], "metric": "imor"}, expected_keys=[]),

    # Portfolio Tools
    ToolDef("get_commercial_portfolio_by_sector", "portfolio", test_args={"top_n": 5}, expected_keys=[]),
    ToolDef("get_commercial_portfolio_by_company_size", "portfolio", test_args={}, expected_keys=[]),
    ToolDef("get_housing_portfolio_demographics", "portfolio", test_args={}, expected_keys=[]),
    ToolDef("get_time_series", "portfolio", required_params=["banco", "metric"], test_args={"banco": "BBVA", "metric": "imor"}, expected_keys=[]),
    ToolDef("get_bank_detail", "portfolio", required_params=["banco"], test_args={"banco": "BBVA"}, expected_keys=["banco", "data"]),
    ToolDef("get_system_summary", "portfolio", test_args={}, expected_keys=["data"]),

    # Dimension Tools
    ToolDef("get_portfolio_by_activity", "dimension", test_args={"top_n": 5}, expected_keys=[]),
    ToolDef("get_portfolio_by_company_size_mv", "dimension", test_args={"top_n": 5}, expected_keys=[]),
    ToolDef("get_portfolio_by_destination", "dimension", test_args={"top_n": 5}, expected_keys=[]),
    ToolDef("detect_metric_trends", "dimension", test_args={"metric": "imor", "top_n": 5}, expected_keys=[]),
    ToolDef("get_metric_alerts", "dimension", test_args={}, expected_keys=[]),
]

DEPRECATED_TOOL = "bank_analytics"
EXPECTED_ACTIVE_COUNT = 21


# --- RPC HELPERS ---

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


# --- PYTEST TEST FUNCTIONS ---

class TestMCPToolsDiscovery:
    """Test tool registration and discovery via /rpc tools/list."""

    def test_all_expected_tools_registered(self):
        """All 21 expected tools should be registered."""
        result = rpc_call("tools/list")
        assert "error" not in result, f"RPC Error: {result.get('error')}"

        tools = result.get("result", {}).get("tools", [])
        tool_names = {t["name"] for t in tools}

        expected_names = {t.name for t in EXPECTED_TOOLS}
        missing = expected_names - tool_names
        assert not missing, f"Missing tools: {missing}"

    def test_deprecated_tool_marked(self):
        """bank_analytics should be marked as deprecated."""
        result = rpc_call("tools/list")
        tools = result.get("result", {}).get("tools", [])

        deprecated_tools = [t for t in tools if t.get("deprecated")]
        deprecated_names = {t["name"] for t in deprecated_tools}

        assert DEPRECATED_TOOL in deprecated_names, f"{DEPRECATED_TOOL} not marked as deprecated"

    def test_active_tools_count(self):
        """Should have at least 21 active (non-deprecated) tools."""
        result = rpc_call("tools/list")
        tools = result.get("result", {}).get("tools", [])

        active_count = len([t for t in tools if not t.get("deprecated")])
        assert active_count >= EXPECTED_ACTIVE_COUNT, f"Expected {EXPECTED_ACTIVE_COUNT}+ active tools, got {active_count}"


class TestMCPToolsCritical:
    """Test critical tools that must work for the system to function."""

    def test_get_bank_detail(self):
        """get_bank_detail should return bank data with expected keys."""
        result = call_tool("get_bank_detail", {"banco": "BBVA"})
        assert result.get("success"), f"Tool failed: {result.get('error')}"
        assert "banco" in result or "data" in result, "Missing 'banco' or 'data' key"

    def test_get_system_summary(self):
        """get_system_summary should return system-wide aggregates."""
        result = call_tool("get_system_summary", {})
        assert result.get("success"), f"Tool failed: {result.get('error')}"
        assert "data" in result, "Missing 'data' key"

    def test_list_institutions(self):
        """list_institutions should return institution list."""
        result = call_tool("list_institutions", {})
        assert result.get("success"), f"Tool failed: {result.get('error')}"
        assert "institutions" in result, "Missing 'institutions' key"
        assert len(result["institutions"]) > 0, "No institutions returned"


class TestMCPToolsExecution:
    """Test execution of all MCP tools."""

    @pytest.mark.parametrize("tool_def", EXPECTED_TOOLS, ids=[t.name for t in EXPECTED_TOOLS])
    def test_tool_executes_successfully(self, tool_def: ToolDef):
        """Each tool should execute without error."""
        result = call_tool(tool_def.name, tool_def.test_args)

        # Regional tools may legitimately have no data
        if tool_def.category == "regional" and not result.get("success"):
            pytest.skip(f"Regional tool {tool_def.name} has no data (expected)")

        assert result.get("success"), f"{tool_def.name} failed: {result.get('error', result.get('message', 'Unknown'))}"

        # Check expected keys if defined
        if tool_def.expected_keys:
            data = result.get("data", {})
            for key in tool_def.expected_keys:
                assert key in result or key in data, f"Missing expected key '{key}' in {tool_def.name} response"


class TestMCPToolsBackendIntegration:
    """Test backend integration with bank-advisor."""

    def test_bank_advisor_reachable(self):
        """Backend should be able to reach bank-advisor /rpc."""
        result = rpc_call("tools/list")
        assert "error" not in result, f"Bank-advisor unreachable: {result.get('error')}"

    def test_tools_list_has_minimum_count(self):
        """tools/list should return at least 21 tools."""
        result = rpc_call("tools/list")
        tools = result.get("result", {}).get("tools", [])
        assert len(tools) >= EXPECTED_ACTIVE_COUNT, f"Expected {EXPECTED_ACTIVE_COUNT}+ tools, got {len(tools)}"


# --- STANDALONE RUNNER ---

def main():
    """Standalone runner for quick verification."""
    print("=" * 70)
    print("MCP TOOLS TEST SUITE (REFACTOR-2026-02-03)")
    print("=" * 70)
    print(f"Bank-Advisor URL: {BANK_ADVISOR_URL}")
    print()

    # Quick verification
    result = rpc_call("tools/list")
    if "error" in result:
        print(f"FAIL: Cannot reach bank-advisor: {result['error']}")
        sys.exit(1)

    tools = result.get("result", {}).get("tools", [])
    active = [t for t in tools if not t.get("deprecated")]
    deprecated = [t for t in tools if t.get("deprecated")]

    print(f"Total tools: {len(tools)}")
    print(f"Active: {len(active)}")
    print(f"Deprecated: {len(deprecated)}")
    print()

    # Test critical tools
    critical_passed = 0
    critical_tools = [
        ("get_bank_detail", {"banco": "BBVA"}),
        ("get_system_summary", {}),
        ("list_institutions", {}),
    ]

    for name, args in critical_tools:
        result = call_tool(name, args)
        status = "PASS" if result.get("success") else "FAIL"
        print(f"  {status}: {name}")
        if result.get("success"):
            critical_passed += 1

    print()
    print(f"Critical tools: {critical_passed}/{len(critical_tools)} passed")

    # Save results
    output_file = Path(__file__).parent / "mcp_tools_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tools": len(tools),
            "active_tools": len(active),
            "deprecated_tools": len(deprecated),
            "critical_passed": critical_passed,
        }, f, indent=2)
    print(f"\nResults saved to {output_file}")

    if critical_passed < len(critical_tools):
        sys.exit(1)


if __name__ == "__main__":
    main()
