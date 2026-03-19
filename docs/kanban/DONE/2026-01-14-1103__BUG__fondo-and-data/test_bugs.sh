#!/bin/bash
# Reproducible test suite for ISSUE-007 bugs
# Tests each bug in both LOCAL and PRODUCTION environments
# Credentials referenced from envs/.env

set -e

LOCAL_URL="http://localhost:8002"
PROD_URL="http://${PROD_SERVER_IP}:8002"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "ISSUE-007 Bug Test Suite"
echo "=========================================="
echo ""

# Helper function to test a query
test_query() {
    local env=$1
    local url=$2
    local query=$3
    local test_name=$4

    echo "Testing: $test_name"
    echo "Environment: $env"
    echo "Query: $query"

    response=$(curl -s -X POST "${url}/rpc" \
        -H "Content-Type: application/json" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": \"test-${env}\",
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"bank_analytics\",
                \"arguments\": {
                    \"metric_or_query\": \"${query}\",
                    \"mode\": \"dashboard\"
                }
            }
        }")

    # Extract key fields
    data_type=$(echo "$response" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.type // "error"' 2>/dev/null || echo "parse_error")
    chart_status=$(echo "$response" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.chart_status // "null"' 2>/dev/null || echo "parse_error")
    has_plotly=$(echo "$response" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.plotly_config.data | length > 0' 2>/dev/null || echo "false")
    response_text=$(echo "$response" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.response_text // ""' 2>/dev/null | head -c 200)

    echo "  data.type: $data_type"
    echo "  chart_status: $chart_status"
    echo "  has_plotly_data: $has_plotly"

    # Check for "2024%" bug
    if echo "$response" | grep -q "2024%"; then
        echo -e "  ${RED}⚠️  BUG DETECTED: Contains '2024%'${NC}"
        echo "$response" | grep "2024%" | head -3
        return 1
    fi

    # Check for empty chart
    if [ "$chart_status" == "empty" ]; then
        echo -e "  ${RED}⚠️  BUG DETECTED: chart_status is 'empty'${NC}"
        return 1
    fi

    # Check for no data
    if [ "$data_type" == "empty" ] || [ "$has_plotly" == "false" ]; then
        echo -e "  ${YELLOW}⚠️  WARNING: No data returned${NC}"
        return 1
    fi

    echo -e "  ${GREEN}✅ PASS${NC}"
    return 0
}

# Test results tracking
declare -A local_results
declare -A prod_results

# ==========================================
# BUG 1-2: IMOR/ICAP "2024%" bug
# ==========================================
echo ""
echo "=========================================="
echo "BUG 1-2: IMOR/ICAP showing '2024%'"
echo "=========================================="

echo ""
echo "--- Test 1a: IMOR del sistema 2024 ---"
test_query "LOCAL" "$LOCAL_URL" "IMOR del sistema al cierre de 2024" "BUG1-IMOR" && local_results[BUG1]="PASS" || local_results[BUG1]="FAIL"
echo ""
test_query "PROD" "$PROD_URL" "IMOR del sistema al cierre de 2024" "BUG1-IMOR" && prod_results[BUG1]="PASS" || prod_results[BUG1]="FAIL"

echo ""
echo "--- Test 1b: ICAP de Banorte 2024 ---"
test_query "LOCAL" "$LOCAL_URL" "ICAP para Banorte en 2024" "BUG2-ICAP" && local_results[BUG2]="PASS" || local_results[BUG2]="FAIL"
echo ""
test_query "PROD" "$PROD_URL" "ICAP para Banorte en 2024" "BUG2-ICAP" && prod_results[BUG2]="PASS" || prod_results[BUG2]="FAIL"

# ==========================================
# BUG 3: Historical query with multiple banks
# ==========================================
echo ""
echo "=========================================="
echo "BUG 3: Histórico IMOR múltiples bancos"
echo "=========================================="

echo ""
echo "--- Test 3: IMOR histórico Santander, BBVA, Banorte ---"
test_query "LOCAL" "$LOCAL_URL" "Histórico del IMOR para Santander, BBVA y Banorte" "BUG3-HISTORICO" && local_results[BUG3]="PASS" || local_results[BUG3]="FAIL"
echo ""
test_query "PROD" "$PROD_URL" "Histórico del IMOR para Santander, BBVA y Banorte" "BUG3-HISTORICO" && prod_results[BUG3]="PASS" || prod_results[BUG3]="FAIL"

# ==========================================
# BUG 4: Data recency (PostgreSQL check)
# ==========================================
echo ""
echo "=========================================="
echo "BUG 4: Data Recency Check"
echo "=========================================="
echo ""
echo "Checking PostgreSQL for latest data..."

export PGPASSWORD="${POSTGRES_PASSWORD}"
max_date=$(psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -t -c "SELECT MAX(fecha) FROM monthly_kpis" | tr -d ' ')

echo "PostgreSQL max date: $max_date"

if [[ "$max_date" > "2025-06-01" ]]; then
    echo -e "${GREEN}✅ PASS: Data exists until $max_date (expected: 2025-10)${NC}"
    local_results[BUG4]="PASS"
    prod_results[BUG4]="PASS"  # Data layer is correct
else
    echo -e "${RED}⚠️  FAIL: Data only until $max_date${NC}"
    local_results[BUG4]="FAIL"
    prod_results[BUG4]="FAIL"
fi

# ==========================================
# BUG 5: CARTERA_VIVIENDA_TOTAL
# ==========================================
echo ""
echo "=========================================="
echo "BUG 5: CARTERA_VIVIENDA_TOTAL = 0"
echo "=========================================="
echo ""
echo "Checking PostgreSQL for CARTERA_VIVIENDA_TOTAL..."

cartera_check=$(psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -t -c "
SELECT COUNT(*)
FROM monthly_kpis
WHERE banco_norm = 'SISTEMA'
  AND fecha >= '2024-01-01'
  AND cartera_vivienda_total > 0
" | tr -d ' ')

echo "Rows with CARTERA_VIVIENDA_TOTAL > 0: $cartera_check"

if [ "$cartera_check" -gt "0" ]; then
    echo -e "${GREEN}✅ PASS: CARTERA_VIVIENDA_TOTAL has non-zero values${NC}"
    local_results[BUG5]="PASS"
    prod_results[BUG5]="PASS"
else
    echo -e "${RED}⚠️  FAIL: All CARTERA_VIVIENDA_TOTAL values are zero${NC}"
    local_results[BUG5]="FAIL"
    prod_results[BUG5]="FAIL"
fi

# Test the metric query
echo ""
echo "--- Test 5: Query CARTERA_VIVIENDA_TOTAL ---"
test_query "LOCAL" "$LOCAL_URL" "CARTERA_VIVIENDA_TOTAL del sistema" "BUG5-CARTERA" || local_results[BUG5_QUERY]="FAIL"
echo ""
test_query "PROD" "$PROD_URL" "CARTERA_VIVIENDA_TOTAL del sistema" "BUG5-CARTERA" || prod_results[BUG5_QUERY]="FAIL"

# ==========================================
# SUMMARY
# ==========================================
echo ""
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo ""
printf "%-20s | %-10s | %-10s | %s\n" "Bug" "Local" "Production" "Status"
echo "--------------------------------------------------------------"

for bug in BUG1 BUG2 BUG3 BUG4 BUG5; do
    local_result=${local_results[$bug]:-"NOT_RUN"}
    prod_result=${prod_results[$bug]:-"NOT_RUN"}

    if [ "$local_result" == "PASS" ] && [ "$prod_result" == "FAIL" ]; then
        status="${YELLOW}FIXED IN LATEST${NC}"
    elif [ "$local_result" == "PASS" ] && [ "$prod_result" == "PASS" ]; then
        status="${GREEN}RESOLVED${NC}"
    elif [ "$local_result" == "FAIL" ] && [ "$prod_result" == "FAIL" ]; then
        status="${RED}STILL BROKEN${NC}"
    else
        status="INCONSISTENT"
    fi

    printf "%-20s | %-10s | %-10s | %b\n" "$bug" "$local_result" "$prod_result" "$status"
done

echo ""
echo "Legend:"
echo "  FIXED IN LATEST  - Bug exists in prod (v1.4.4) but fixed in local (latest)"
echo "  RESOLVED         - Bug fixed in both environments"
echo "  STILL BROKEN     - Bug exists in both environments"
echo ""
