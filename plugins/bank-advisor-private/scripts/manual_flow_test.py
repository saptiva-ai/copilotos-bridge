#!/usr/bin/env python3
"""
Manual Flow Testing - BankAdvisor Complete Verification
Tests the actual flow with real queries and inspects responses.

Usage:
    python scripts/manual_flow_test.py
"""

import json
import requests
from datetime import datetime
from typing import Dict, Any

BANK_ADVISOR_URL = "http://localhost:8002"


def call_bank_advisor(query: str) -> Dict[str, Any]:
    """Call BankAdvisor and return parsed response."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "bank_analytics",
            "arguments": {"metric_or_query": query}
        }
    }

    response = requests.post(
        f"{BANK_ADVISOR_URL}/rpc",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        if "result" in data and "content" in data["result"]:
            content = data["result"]["content"]
            if content and len(content) > 0:
                text = content[0].get("text", "{}")
                return json.loads(text)

    return {"error": "Failed to get response"}


def print_response_summary(query: str, response: Dict[str, Any]):
    """Print a summary of the response."""
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}")

    if "error" in response:
        print(f"❌ ERROR: {response.get('error')}")
        return

    # Check response structure
    print(f"✅ Success: {response.get('success', False)}")

    data = response.get("data", {})
    metadata = response.get("metadata", {})

    print(f"\n📊 Data Structure:")
    print(f"   Type: {data.get('type')}")
    print(f"   Visualization: {data.get('visualization')}")
    print(f"   Metric: {data.get('metric_name')}")
    print(f"   Banks: {', '.join(data.get('bank_names', []))}")
    print(f"   Time Range: {data.get('time_range', {}).get('start')} → {data.get('time_range', {}).get('end')}")

    # Check plotly data
    plotly_config = data.get("plotly_config", {})
    plotly_data = plotly_config.get("data", [])

    if plotly_data:
        print(f"\n📈 Plotly Data:")
        for series in plotly_data:
            name = series.get("name", "Unknown")
            x_points = len(series.get("x", []))
            y_points = len(series.get("y", []))
            y_values = series.get("y", [])

            print(f"   Series: {name}")
            print(f"   Points: {x_points} dates, {y_points} values")

            if y_values:
                print(f"   Range: {min(y_values):.2f} - {max(y_values):.2f}")
                print(f"   Latest: {y_values[-1]:.2f}")

    # Pipeline and performance
    print(f"\n⚙️  Metadata:")
    print(f"   Pipeline: {metadata.get('pipeline')}")
    print(f"   Execution: {metadata.get('execution_time_ms')}ms")
    print(f"   Requires Clarification: {metadata.get('requires_clarification', False)}")

    # Query info
    query_info = data.get("query_info", {})
    if query_info:
        print(f"\n🔍 Query Analysis:")
        print(f"   Detected Intent: {query_info.get('detected_intent')}")
        print(f"   Detected Metric: {query_info.get('detected_metric')}")
        print(f"   Detected Banks: {', '.join(query_info.get('detected_banks', []))}")
        print(f"   Confidence: {query_info.get('confidence', 0)*100:.0f}%")

    # SQL generated
    sql = metadata.get('sql_generated')
    if sql:
        print(f"\n💾 Generated SQL:")
        for line in sql.split('\n'):
            print(f"   {line}")


def test_scenarios():
    """Test various scenarios."""

    print("\n" + "="*80)
    print("BANKADVISOR FLOW TESTING")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"URL: {BANK_ADVISOR_URL}")
    print("="*80)

    # Test cases
    test_cases = [
        # Basic queries
        ("IMOR de INVEX", "Basic metric query"),
        ("ICAP de INVEX", "New metric - ICAP"),
        ("TDA de INVEX", "New metric - TDA"),
        ("tasa mn de INVEX", "New metric - TASA_MN"),

        # Comparisons
        ("IMOR de INVEX vs SISTEMA", "Comparison query"),
        ("ICAP de INVEX vs BBVA", "Comparison with new metric"),

        # Timelines
        ("IMOR de INVEX últimos 12 meses", "Timeline - last 12 months"),
        ("ICAP de INVEX en 2024", "Timeline - specific year"),

        # Ambiguous (should trigger clarification)
        ("datos del banco", "Ambiguous - missing metric"),
        ("INVEX", "Ambiguous - bank only"),

        # Invalid
        ("METRICA_INVENTADA de INVEX", "Invalid metric"),
    ]

    for query, description in test_cases:
        print(f"\n\n{'#'*80}")
        print(f"# Test: {description}")
        print(f"{'#'*80}")

        try:
            response = call_bank_advisor(query)
            print_response_summary(query, response)
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    print("\n\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)


if __name__ == "__main__":
    test_scenarios()
