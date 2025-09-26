#!/bin/bash

# ============================================================================
# COMPREHENSIVE HEALTH CHECK SCRIPT FOR COPILOTOS BRIDGE
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8001}"
WEB_BASE_URL="${WEB_BASE_URL:-http://localhost:3000}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
TIMEOUT="${TIMEOUT:-10}"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
}

# ============================================================================
# HEALTH CHECK FUNCTIONS
# ============================================================================

check_api_health() {
    print_status "Checking API health..."

    # Basic health endpoint
    if curl -f -s --max-time $TIMEOUT "$API_BASE_URL/api/health" > /dev/null; then
        print_success "API health endpoint responding"
    else
        print_error "API health endpoint not responding"
        return 1
    fi

    # Metrics endpoint
    if curl -f -s --max-time $TIMEOUT "$API_BASE_URL/api/health/metrics" > /dev/null; then
        print_success "API metrics health endpoint responding"
    else
        print_warning "API metrics health endpoint not responding"
    fi

    # Prometheus metrics
    if curl -f -s --max-time $TIMEOUT "$API_BASE_URL/api/metrics" | grep -q "copilotos_"; then
        print_success "Prometheus metrics are being exposed"
    else
        print_warning "Prometheus metrics not found or not responding"
    fi
}

check_web_health() {
    print_status "Checking Web application health..."

    if curl -f -s --max-time $TIMEOUT "$WEB_BASE_URL" > /dev/null; then
        print_success "Web application responding"
    else
        print_error "Web application not responding"
        return 1
    fi
}

check_deep_research_endpoints() {
    print_status "Checking Deep Research endpoints..."

    # Intent classification endpoint
    local intent_response=$(curl -s --max-time $TIMEOUT \
        -X POST "$API_BASE_URL/api/intent" \
        -H "Content-Type: application/json" \
        -d '{"text": "What is artificial intelligence?"}' \
        -w "%{http_code}")

    if [[ "$intent_response" =~ 200$ ]]; then
        print_success "Intent classification endpoint responding"
    else
        print_warning "Intent classification endpoint not responding properly"
    fi

    # Research metrics endpoint
    if curl -f -s --max-time $TIMEOUT "$API_BASE_URL/api/metrics/research" > /dev/null; then
        print_success "Research metrics endpoint responding"
    else
        print_warning "Research metrics endpoint not responding"
    fi
}

check_database_connectivity() {
    print_status "Checking database connectivity..."

    # This would check if the API can connect to MongoDB
    local db_status=$(curl -s --max-time $TIMEOUT "$API_BASE_URL/api/health" | grep -o '"database":[^,]*')

    if [[ "$db_status" =~ "healthy" ]]; then
        print_success "Database connectivity healthy"
    else
        print_warning "Database connectivity issues detected"
    fi
}

check_prometheus_targets() {
    print_status "Checking Prometheus targets..."

    if curl -f -s --max-time $TIMEOUT "$PROMETHEUS_URL/api/v1/targets" > /dev/null; then
        print_success "Prometheus targets endpoint responding"

        # Check if our API is being scraped
        local targets_response=$(curl -s --max-time $TIMEOUT "$PROMETHEUS_URL/api/v1/targets")
        if echo "$targets_response" | grep -q "copilotos-api"; then
            print_success "Copilotos API target found in Prometheus"
        else
            print_warning "Copilotos API target not found in Prometheus"
        fi
    else
        print_warning "Prometheus not accessible at $PROMETHEUS_URL"
    fi
}

check_metrics_data() {
    print_status "Checking metrics data availability..."

    # Check if we have request metrics
    local metrics_response=$(curl -s --max-time $TIMEOUT "$API_BASE_URL/api/metrics")

    if echo "$metrics_response" | grep -q "copilotos_requests_total"; then
        print_success "Request metrics are being collected"
    else
        print_warning "Request metrics not found"
    fi

    if echo "$metrics_response" | grep -q "copilotos_research"; then
        print_success "Research metrics are being collected"
    else
        print_warning "Research metrics not found (may be normal if no research operations have occurred)"
    fi

    if echo "$metrics_response" | grep -q "copilotos_intent_classification"; then
        print_success "Intent classification metrics are being collected"
    else
        print_warning "Intent classification metrics not found"
    fi
}

get_metrics_summary() {
    print_status "Getting metrics summary..."

    local summary=$(curl -s --max-time $TIMEOUT "$API_BASE_URL/api/metrics/summary" 2>/dev/null)

    if [[ -n "$summary" ]]; then
        echo "$summary" | python3 -m json.tool 2>/dev/null || echo "$summary"
    else
        print_warning "Could not retrieve metrics summary"
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    echo "🔍 Copilotos Bridge Health Check"
    echo "=================================="
    echo "API URL: $API_BASE_URL"
    echo "Web URL: $WEB_BASE_URL"
    echo "Prometheus URL: $PROMETHEUS_URL"
    echo "Timeout: ${TIMEOUT}s"
    echo ""

    local exit_code=0

    # Run all health checks
    check_api_health || exit_code=1
    echo ""

    check_web_health || exit_code=1
    echo ""

    check_deep_research_endpoints
    echo ""

    check_database_connectivity
    echo ""

    check_prometheus_targets
    echo ""

    check_metrics_data
    echo ""

    print_status "Metrics Summary:"
    get_metrics_summary
    echo ""

    # Final status
    if [[ $exit_code -eq 0 ]]; then
        print_success "🎉 All critical health checks passed!"
    else
        print_error "❌ Some critical health checks failed!"
    fi

    echo ""
    print_status "Health check completed at $(date)"

    return $exit_code
}

# Run the health check
main "$@"