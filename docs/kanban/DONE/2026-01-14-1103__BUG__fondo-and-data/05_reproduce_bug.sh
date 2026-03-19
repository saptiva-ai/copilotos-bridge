#!/bin/bash
# Script to reproduce the bug by calling bank-advisor directly
# Credentials referenced from envs/.env

set -e

echo "===== Testing bank-advisor MCP service directly ====="

BANK_ADVISOR_URL="http://${PROD_SERVER_IP}:8002"

echo ""
echo "Test 1: Query IMOR for Sistema 2024"
curl -s -X POST "${BANK_ADVISOR_URL}/rpc" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-imor-sistema",
    "method": "tools/call",
    "params": {
      "name": "bank_analytics",
      "arguments": {
        "metric_or_query": "IMOR del sistema al cierre de 2024",
        "mode": "dashboard"
      }
    }
  }' | jq '.result.data.response_text' | head -20

echo ""
echo "Test 2: Query ICAP for Banorte 2024"
curl -s -X POST "${BANK_ADVISOR_URL}/rpc" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-icap-banorte",
    "method": "tools/call",
    "params": {
      "name": "bank_analytics",
      "arguments": {
        "metric_or_query": "ICAP para Banorte en 2024",
        "mode": "dashboard"
      }
    }
  }' | jq '.result.data.response_text' | head -20

echo ""
echo "Test 3: Query IMOR histórico for multiple banks"
curl -s -X POST "${BANK_ADVISOR_URL}/rpc" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-imor-historico",
    "method": "tools/call",
    "params": {
      "name": "bank_analytics",
      "arguments": {
        "metric_or_query": "IMOR histórico de Santander, BBVA y Banorte",
        "mode": "dashboard"
      }
    }
  }' | jq '.result.data' > /tmp/imor_historico_response.json

echo "Full response saved to /tmp/imor_historico_response.json"
cat /tmp/imor_historico_response.json | jq '{
  type: .type,
  response_text: .response_text,
  data_as_of: .data_as_of,
  plotly_data_length: (.plotly_config.data | length),
  chart_status: .chart_status
}'
