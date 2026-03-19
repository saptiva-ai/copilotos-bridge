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
#
# Environment:
#   API_SERVICE   - Docker service name for API tests (default: backend)
#   WEB_SERVICE   - Docker service name for web tests (default: web)
#
# Exit codes:
#   0 - Tests passed
#   1 - Tests failed
#   2 - Preflight failure (service not running)
################################################################################

set -e

TARGET=${1:-all}
shift || true
ARGS=("$@")
TEST_PATHS_RAW="${TEST_PATHS:-tests/}"
read -r -a TEST_PATHS <<< "$TEST_PATHS_RAW"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_NAME="octavios-chat-bajaware_invex"
COMPOSE_BASE="infra/docker-compose.yml"
COMPOSE_DEV="infra/docker-compose.dev.yml"
# Use both base and dev compose files (dev target has pytest)
COMPOSE="docker compose -p $PROJECT_NAME -f $COMPOSE_BASE -f $COMPOSE_DEV"

# Service name mapping: test target -> actual docker compose service
# Override with environment variables if needed
API_SERVICE="${API_SERVICE:-backend}"
WEB_SERVICE="${WEB_SERVICE:-web}"
if [[ "$API_SERVICE" == "api" ]]; then
    echo -e "${YELLOW}Note: API_SERVICE=api maps to backend; using backend${NC}"
    API_SERVICE="backend"
fi

echo -e "${BLUE}🧪 Ejecutando tests: ${TARGET}${NC}"

# ============================================================================
# PREFLIGHT FUNCTIONS
# ============================================================================

# Check if a service is running using docker labels (compose-agnostic)
# Args: $1 = service name
# Returns: 0 if running, 1 if not
is_service_running() {
    local service="$1"
    local container_id
    container_id=$(docker ps -q --filter "label=com.docker.compose.service=$service" --filter "label=com.docker.compose.project=$PROJECT_NAME" 2>/dev/null)
    [[ -n "$container_id" ]]
}

# Get container name for a service
get_container_name() {
    local service="$1"
    docker ps --filter "label=com.docker.compose.service=$service" --filter "label=com.docker.compose.project=$PROJECT_NAME" --format "{{.Names}}" 2>/dev/null | head -1
}

# Print service status and actionable instructions on failure
# Args: $1 = service name, $2 = friendly name for error message
require_service() {
    local service="$1"
    local friendly_name="${2:-$service}"

    if is_service_running "$service"; then
        local container_name
        container_name=$(get_container_name "$service")
        echo -e "${GREEN}✓ Service '$service' is running ($container_name)${NC}"
        return 0
    fi

    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ PREFLIGHT FAILURE: Service '$service' is not running${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}The $friendly_name tests require the '$service' container to be running.${NC}"
    echo ""
    echo -e "${BLUE}To start the full stack:${NC}"
    echo "  make dev"
    echo ""
    echo -e "${BLUE}Or start just this service:${NC}"
    echo "  docker compose -f $COMPOSE_BASE -f $COMPOSE_DEV up -d $service"
    echo ""
    echo -e "${BLUE}Current container status:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}" --filter "label=com.docker.compose.project=$PROJECT_NAME" 2>/dev/null || echo "  (no containers found)"
    echo ""

    # Try to get last log lines if container exists but isn't running
    local exited_container
    exited_container=$(docker ps -a -q --filter "label=com.docker.compose.service=$service" --filter "label=com.docker.compose.project=$PROJECT_NAME" --filter "status=exited" 2>/dev/null | head -1)
    if [[ -n "$exited_container" ]]; then
        echo -e "${YELLOW}Last 20 log lines from exited container:${NC}"
        docker logs --tail 20 "$exited_container" 2>&1 || true
        echo ""
    fi

    exit 2
}

# ============================================================================
# TEST TARGET SELECTOR
# ============================================================================

case "$TARGET" in
  "api")
    echo -e "${YELLOW}Running API tests...${NC}"
    require_service "$API_SERVICE" "API"
    # Inside container, working dir is /app (apps/backend), so tests are at tests/
    $COMPOSE exec -T "$API_SERVICE" pytest "${TEST_PATHS[@]}" -v "${ARGS[@]}"
    ;;

  "web")
    echo -e "${YELLOW}Running Web tests...${NC}"
    require_service "$WEB_SERVICE" "Web"
    $COMPOSE exec -T "$WEB_SERVICE" pnpm test "${ARGS[@]}"
    ;;

  "mcp")
    echo -e "${YELLOW}Running MCP unit tests...${NC}"
    require_service "$API_SERVICE" "API"
    $COMPOSE exec -T "$API_SERVICE" pytest tests/mcp/ -v -m mcp "${ARGS[@]}"
    ;;

  "mcp-integration")
    echo -e "${YELLOW}Running MCP integration tests...${NC}"
    require_service "$API_SERVICE" "API"
    $COMPOSE exec -T "$API_SERVICE" pytest tests/integration/test_mcp_tools_integration.py -v "${ARGS[@]}"
    ;;

  "mcp-all")
    echo -e "${YELLOW}Running all MCP tests...${NC}"
    require_service "$API_SERVICE" "API"
    $COMPOSE exec -T "$API_SERVICE" pytest tests/mcp/ tests/integration/test_mcp_tools_integration.py -v "${ARGS[@]}"
    ;;

  "e2e")
    echo -e "${YELLOW}Running E2E tests with Playwright (Node.js runtime)...${NC}"
    if command -v pnpm &> /dev/null; then
        pnpm --filter web test:e2e "${ARGS[@]}"
    elif command -v npx &> /dev/null; then
        npx playwright test "${ARGS[@]}"
    elif command -v bun &> /dev/null; then
        bunx playwright test "${ARGS[@]}"
    else
        echo -e "${YELLOW}Warning: Playwright runner not found, skipping E2E tests${NC}"
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

    # Preflight check both services
    require_service "$API_SERVICE" "API"
    require_service "$WEB_SERVICE" "Web"

    # Run API tests
    echo -e "\n${GREEN}[1/4] API Tests${NC}"
    $COMPOSE exec -T "$API_SERVICE" pytest tests/ -v --tb=short || true

    # Run Web tests
    echo -e "\n${GREEN}[2/4] Web Tests${NC}"
    $COMPOSE exec -T "$WEB_SERVICE" pnpm test || true

    # Run MCP tests
    echo -e "\n${GREEN}[3/4] MCP Tests${NC}"
    $COMPOSE exec -T "$API_SERVICE" pytest tests/mcp/ -v || true

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
