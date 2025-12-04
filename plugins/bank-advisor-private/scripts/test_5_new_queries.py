#!/usr/bin/env python3
"""
Quick test script for 5 new query types.
Tests the transformation fix for ranking queries.

Uses HTTP to call the running bank-advisor server.
"""

import asyncio
import httpx
import json
import sys

BASE_URL = "http://localhost:8002"
TIMEOUT = 30.0

async def test_queries():
    """Test all 5 query types."""
    queries = [
        # With complete time range to avoid clarification
        ("cual es el IMOR de invex vs el mercado últimos 6 meses?", "IMOR comparison"),
        ("cómo está mi PDM medido por cartera total últimos 6 meses?", "Market share"),
        ("Cómo ha evolucionado la cartera de crédito de consumo de INVEX en los últimos 6 meses?", "Cartera consumo evolution"),
        ("Cómo está mi IMOR en la cartera automotriz frente al mercado últimos 6 meses?", "IMOR automotriz"),
        ("cual es el tamaño de los bancos por tamaño de activos?", "Bank ranking by assets"),
    ]

    results = []

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for query, description in queries:
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print(f"Description: {description}")
            print('='*60)

            try:
                # Call the bank_analytics endpoint via MCP JSON-RPC
                response = await client.post(
                    f"{BASE_URL}/rpc",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "bank_analytics",
                            "arguments": {
                                "metric_or_query": query,
                                "mode": "chart"
                            }
                        }
                    }
                )

                if response.status_code != 200:
                    print(f"❌ HTTP Error: {response.status_code}")
                    print(f"   Response: {response.text[:200]}")
                    results.append((description, False, False))
                    continue

                rpc_response = response.json()

                # Check for JSON-RPC error
                if "error" in rpc_response:
                    print(f"❌ RPC Error: {rpc_response['error']}")
                    results.append((description, False, False))
                    continue

                # Extract result from JSON-RPC response
                # The content is in result.content[0].text as JSON string
                rpc_result = rpc_response.get("result", {})
                content = rpc_result.get("content", [])
                if content and content[0].get("type") == "text":
                    result = json.loads(content[0].get("text", "{}"))
                else:
                    print(f"❌ Unexpected response format: {rpc_response}")
                    results.append((description, False, False))
                    continue

                success = result.get("success", False)
                # Handle nested data structure: data.data.months or data.months
                data_obj = result.get("data", {})
                months = []

                # Check for different response formats
                if isinstance(data_obj.get("data"), dict):
                    # NL2SQL format: {data: {data: {months: [...]}}}
                    months = data_obj.get("data", {}).get("months", [])
                elif isinstance(data_obj.get("months"), list):
                    # Simple format: {data: {months: [...]}}
                    months = data_obj.get("months", [])
                elif data_obj.get("type") == "data" and "visualization" in data_obj:
                    # HU3_NLP segment format - has data but in different structure
                    # Consider it has_data if it has bank_names or time_series
                    if data_obj.get("bank_names") or data_obj.get("time_series"):
                        months = [{"month_label": "segment_data", "data": [{"category": "OK", "value": 1}]}]

                template = result.get("metadata", {}).get("template_used", "unknown")
                # Also check data.metadata for template
                if template == "unknown" and isinstance(data_obj, dict):
                    nested_meta = data_obj.get("metadata", {})
                    if nested_meta:
                        template = nested_meta.get("template_used", "unknown")
                    # Check visualization type from HU3
                    if data_obj.get("visualization"):
                        template = data_obj.get("visualization")

                sql = result.get("metadata", {}).get("sql_generated", "")

                print(f"✅ Success: {success}")
                print(f"📊 Template: {template}")
                print(f"📈 Data entries: {len(months)}")

                if sql:
                    print(f"   SQL: {sql[:150]}...")

                if months:
                    first = months[0]
                    print(f"   First entry label: {first.get('month_label')}")
                    print(f"   Data items: {len(first.get('data', []))}")
                    if first.get("data"):
                        for item in first['data'][:5]:
                            cat = item.get('category', 'N/A')
                            val = item.get('value', 'N/A')
                            pct = item.get('pct_total')
                            if pct:
                                print(f"      {cat}: {val:,.0f} ({pct:.1f}%)")
                            else:
                                print(f"      {cat}: {val}")

                # Check plotly config
                plotly = result.get("plotly_config", {})
                if plotly:
                    chart_type = plotly.get("data", [{}])[0].get("type", "unknown")
                    orientation = plotly.get("data", [{}])[0].get("orientation", "v")
                    print(f"📉 Chart type: {chart_type} ({orientation})")

                results.append((description, success, len(months) > 0))

            except Exception as e:
                print(f"❌ Error: {e}")
                results.append((description, False, False))

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed = 0
    for desc, success, has_data in results:
        status = "✅" if success and has_data else "❌"
        print(f"{status} {desc}: success={success}, has_data={has_data}")
        if success and has_data:
            passed += 1

    print(f"\nTotal: {passed}/{len(results)} passed")
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(test_queries())
    sys.exit(0 if success else 1)
