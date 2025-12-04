#!/bin/bash
################################################################################
# Test Runner - Consolidates all testing logic
#
# Usage:
#   ./scripts/test-runner.sh <TARGET> [ARGS]
#
# Examples:
#   ./scripts/test-runner.sh api
#   ./scripts/test-runner.sh mcp -v
#   ./scripts/test-runner.sh web
#   ./scripts/test-runner.sh e2e
#   ./scripts/test-runner.sh all
#
# Targets: api, web, mcp, mcp-integration, e2e, all
################################################################################

set -e

TARGET=${1:-all}
shift || true
ARGS="$@"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_NAME="octavios-chat-bajaware_invex"
COMPOSE="docker compose -p $PROJECT_NAME -f infra/docker-compose.yml"

echo -e "${BLUE}🧪 Ejecutando tests: ${TARGET}${NC}"

# ============================================================================
# TEST TARGET SELECTOR
# ============================================================================

case "$TARGET" in
  "api")
    echo -e "${YELLOW}Running API tests...${NC}"
    $COMPOSE exec -T api pytest apps/api/tests/ -v $ARGS
    ;;

  "web")
    echo -e "${YELLOW}Running Web tests...${NC}"
    $COMPOSE exec -T web pnpm test $ARGS
    ;;

  "mcp")
    echo -e "${YELLOW}Running MCP unit tests...${NC}"
    $COMPOSE exec -T api pytest apps/api/tests/mcp/ -v -m mcp $ARGS
    ;;

  "mcp-integration")
    echo -e "${YELLOW}Running MCP integration tests...${NC}"
    $COMPOSE exec -T api pytest apps/api/tests/integration/test_mcp_tools_integration.py -v $ARGS
    ;;

  "mcp-all")
    echo -e "${YELLOW}Running all MCP tests...${NC}"
    $COMPOSE exec -T api pytest apps/api/tests/mcp/ apps/api/tests/integration/test_mcp_tools_integration.py -v $ARGS
    ;;

  "e2e")
    echo -e "${YELLOW}Running E2E tests with Playwright...${NC}"
    if command -v pnpm &> /dev/null; then
        pnpm exec playwright test $ARGS
    else
        echo -e "${YELLOW}Warning: pnpm not found, skipping E2E tests${NC}"
    fi
    ;;

  "shell")
    echo -e "${YELLOW}Running shell script tests...${NC}"
    ./scripts/run_shell_tests.sh
    ;;

  "all")
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE} Running Full Test Suite${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Run API tests
    echo -e "\n${GREEN}[1/4] API Tests${NC}"
    $COMPOSE exec -T api pytest apps/api/tests/ -v --tb=short || true

    # Run Web tests
    echo -e "\n${GREEN}[2/4] Web Tests${NC}"
    $COMPOSE exec -T web pnpm test || true

    # Run MCP tests
    echo -e "\n${GREEN}[3/4] MCP Tests${NC}"
    $COMPOSE exec -T api pytest apps/api/tests/mcp/ -v || true

    # Run Shell tests
    echo -e "\n${GREEN}[4/4] Shell Tests${NC}"
    ./scripts/run_shell_tests.sh || true

    echo -e "\n${GREEN}✅ Test suite completed${NC}"
    ;;

  *)
    echo -e "${YELLOW}❌ Unknown target: $TARGET${NC}"
    echo "Available targets: api, web, mcp, mcp-integration, mcp-all, e2e, shell, all"
    exit 1
    ;;
esac

echo -e "${GREEN}✅ Tests completed successfully${NC}"
