#!/bin/bash
# =============================================================================
# Run All Embedding Delegation Tests
# =============================================================================
# OPTIMIZATION 2026-01: Comprehensive test suite for the new embedding
# delegation architecture.
#
# Usage:
#   ./scripts/testing/run_embedding_tests.sh [OPTIONS]
#
# Options:
#   --smoke     Run only smoke tests (fast)
#   --unit      Run only unit tests
#   --integration Run only integration tests
#   --regression  Run only regression tests
#   --all       Run all tests (default)
#   --verbose   Enable verbose output
#
# Exit Codes:
#   0 - All tests passed
#   1 - Some tests failed
#   2 - Infrastructure failure (services not running)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${TEST_BACKEND_URL:-http://localhost:8000}"
EMBEDDING_URL="${TEST_EMBEDDING_SERVICE_URL:-http://localhost:8003}"
VERBOSE="${VERBOSE:-false}"

# Parse arguments
RUN_SMOKE=false
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_REGRESSION=false
RUN_ALL=true

for arg in "$@"; do
    case $arg in
        --smoke)
            RUN_SMOKE=true
            RUN_ALL=false
            ;;
        --unit)
            RUN_UNIT=true
            RUN_ALL=false
            ;;
        --integration)
            RUN_INTEGRATION=true
            RUN_ALL=false
            ;;
        --regression)
            RUN_REGRESSION=true
            RUN_ALL=false
            ;;
        --all)
            RUN_ALL=true
            ;;
        --verbose)
            VERBOSE=true
            ;;
        *)
            echo "Unknown option: $arg"
            exit 1
            ;;
    esac
done

# If --all, enable all suites
if [ "$RUN_ALL" = true ]; then
    RUN_SMOKE=true
    RUN_UNIT=true
    RUN_INTEGRATION=true
    RUN_REGRESSION=true
fi

echo "============================================================"
echo -e "${BLUE}EMBEDDING DELEGATION TEST SUITE${NC}"
echo "============================================================"
echo "Backend URL: $BACKEND_URL"
echo "Embedding Service URL: $EMBEDDING_URL"
echo "Verbose: $VERBOSE"
echo "============================================================"

# Track results
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0

run_suite() {
    local name=$1
    local command=$2

    echo ""
    echo "============================================================"
    echo -e "${YELLOW}Running: $name${NC}"
    echo "============================================================"

    if eval "$command"; then
        echo -e "${GREEN}✅ $name: PASSED${NC}"
        ((TOTAL_PASSED++))
    else
        echo -e "${RED}❌ $name: FAILED${NC}"
        ((TOTAL_FAILED++))
    fi
}

# Pre-flight check: Services running?
echo ""
echo -e "${BLUE}Pre-flight checks...${NC}"

if ! curl -s --connect-timeout 5 "$EMBEDDING_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ Embedding service not available at $EMBEDDING_URL${NC}"
    echo "   Start with: docker compose up embedding-service"
    exit 2
fi
echo -e "${GREEN}✅ Embedding service: OK${NC}"

if ! curl -s --connect-timeout 5 "$BACKEND_URL/api/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ Backend not available at $BACKEND_URL${NC}"
    echo "   Start with: docker compose up backend"
    exit 2
fi
echo -e "${GREEN}✅ Backend: OK${NC}"

# Run smoke tests
if [ "$RUN_SMOKE" = true ]; then
    run_suite "Smoke Tests" "python ${PROJECT_ROOT}/tests/smoke/test_embedding_delegation_smoke.py"
fi

# Run unit tests
if [ "$RUN_UNIT" = true ]; then
    PYTEST_ARGS="-v"
    if [ "$VERBOSE" = true ]; then
        PYTEST_ARGS="-v -s"
    fi
    run_suite "Unit Tests" "cd ${PROJECT_ROOT}/apps/backend && python -m pytest tests/unit/services/test_embedding_service.py $PYTEST_ARGS"
fi

# Run integration tests
if [ "$RUN_INTEGRATION" = true ]; then
    run_suite "Integration Tests" "python ${PROJECT_ROOT}/tests/integration/test_backend_to_embedding_service.py"
fi

# Run regression tests
if [ "$RUN_REGRESSION" = true ]; then
    VERBOSE_ARG=""
    if [ "$VERBOSE" = true ]; then
        VERBOSE_ARG="VERBOSE=1"
    fi
    run_suite "Regression Tests" "$VERBOSE_ARG python ${PROJECT_ROOT}/tests/e2e/regression/test_embedding_delegation_regression.py"
fi

# Summary
echo ""
echo "============================================================"
echo -e "${BLUE}SUMMARY${NC}"
echo "============================================================"
echo -e "Passed:  ${GREEN}$TOTAL_PASSED${NC}"
echo -e "Failed:  ${RED}$TOTAL_FAILED${NC}"
echo -e "Skipped: ${YELLOW}$TOTAL_SKIPPED${NC}"
echo ""

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL EMBEDDING TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    exit 1
fi
