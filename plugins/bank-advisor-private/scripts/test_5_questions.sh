#!/usr/bin/env bash
################################################################################
# Test 5 Business Questions Integration
################################################################################
# Tests the newly implemented question-specific handlers in bank-advisor

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Testing 5 Business Questions Integration${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Test Question 1: IMOR INVEX vs Sistema
echo -e "${YELLOW}[1/5] Testing: IMOR de INVEX vs Sistema${NC}"
curl -s -X POST http://localhost:8002/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test1",
    "method": "tools/call",
    "params": {
      "name": "bank_analytics",
      "arguments": {
        "metric_or_query": "IMOR de INVEX vs Sistema",
        "mode": "dashboard"
      }
    }
  }' | jq -r '.result | if .error then "❌ ERROR: " + .error else "✅ SUCCESS: " + (.visualization // "data") end'
echo ""

# Test Question 2: Market Share INVEX
echo -e "${YELLOW}[2/5] Testing: Market share de INVEX${NC}"
curl -s -X POST http://localhost:8002/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test2",
    "method": "tools/call",
    "params": {
      "name": "bank_analytics",
      "arguments": {
        "metric_or_query": "market share de INVEX últimos 3 años",
        "mode": "dashboard"
      }
    }
  }' | jq -r '.result | if .error then "❌ ERROR: " + .error else "✅ SUCCESS: " + (.visualization // "data") end'
echo ""

# Test Question 3: IMOR Automotriz Evolución
echo -e "${YELLOW}[3/5] Testing: IMOR automotriz últimos 3 años${NC}"
curl -s -X POST http://localhost:8002/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test3",
    "method": "tools/call",
    "params": {
      "name": "bank_analytics",
      "arguments": {
        "metric_or_query": "IMOR automotriz últimos 3 años",
        "mode": "dashboard"
      }
    }
  }' | jq -r '.result | if .error then "❌ ERROR: " + .error else "✅ SUCCESS: " + (.visualization // "data") end'
echo ""

# Test Question 4: IMOR Automotriz por Banco (Top 5)
echo -e "${YELLOW}[4/5] Testing: IMOR automotriz por banco Top 5${NC}"
curl -s -X POST http://localhost:8002/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test4",
    "method": "tools/call",
    "params": {
      "name": "bank_analytics",
      "arguments": {
        "metric_or_query": "IMOR automotriz por banco top 5",
        "mode": "dashboard"
      }
    }
  }' | jq -r '.result | if .error then "❌ ERROR: " + .error else "✅ SUCCESS: " + (.visualization // "data") end'
echo ""

# Test Question 5: Ranking Bancos por Activo Total
echo -e "${YELLOW}[5/5] Testing: Ranking de bancos por activo total${NC}"
curl -s -X POST http://localhost:8002/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test5",
    "method": "tools/call",
    "params": {
      "name": "bank_analytics",
      "arguments": {
        "metric_or_query": "ranking de bancos por activo total",
        "mode": "dashboard"
      }
    }
  }' | jq -r '.result | if .error then "❌ ERROR: " + .error else "✅ SUCCESS: " + (.visualization // "data") end'
echo ""

echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Test suite completed!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
