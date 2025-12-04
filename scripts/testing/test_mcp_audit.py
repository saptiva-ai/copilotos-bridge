#!/usr/bin/env python3
"""
Test script for Capital414 Auditor MCP Plugin.

Usage:
    python scripts/test_mcp_audit.py /path/to/file.pdf
"""

import asyncio
import sys
import json

# Use httpx for SSE client
import httpx


async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """
    Call an MCP tool via HTTP.

    FastMCP exposes tools at POST /mcp with JSON-RPC 2.0 format.
    """
    url = "http://localhost:8002/mcp"

    # JSON-RPC 2.0 request
    payload = {
        "jsonrpc": "2.0",
        "id": "test-1",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        return response.json()


async def list_tools() -> dict:
    """List available MCP tools."""
    url = "http://localhost:8002/mcp"

    payload = {
        "jsonrpc": "2.0",
        "id": "list-tools",
        "method": "tools/list",
        "params": {}
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        return response.json()


async def main():
    print("=" * 60)
    print("Capital414 Auditor MCP Plugin Test")
    print("=" * 60)

    # 1. List available tools
    print("\n1. Listing available tools...")
    tools_response = await list_tools()

    if "error" in tools_response:
        print(f"   Error: {tools_response['error']}")
    else:
        tools = tools_response.get("result", {}).get("tools", [])
        print(f"   Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.get('name')}: {tool.get('description', '')[:50]}...")

    # 2. Call audit_document_full if a PDF path was provided
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        print(f"\n2. Auditing document: {pdf_path}")

        result = await call_mcp_tool(
            "audit_document_full",
            {
                "file_path": pdf_path,
                "policy_id": "auto",
                "enable_disclaimer": True,
                "enable_format": True,
                "enable_typography": True,
                "enable_grammar": True,
                "enable_logo": True,
                "enable_color_palette": True,
                "enable_entity_consistency": True,
                "enable_semantic_consistency": True,
            }
        )

        if "error" in result:
            print(f"   Error: {result['error']}")
        else:
            content = result.get("result", {})
            print(f"\n   Result:")
            print(json.dumps(content, indent=2, ensure_ascii=False)[:2000])
    else:
        print("\n2. No PDF provided. Usage: python test_mcp_audit.py /path/to/file.pdf")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
