#!/usr/bin/env bash
################################################################################
# Quick Checks - Pre-commit validation script
#
# Runs minimal test suite to validate codebase before changes.
# Reads configuration from .claude/.env.claude (no hardcoded values).
#
# Usage:
#   ./quick_checks.sh           # Check services, run tests if running
#   START=1 ./quick_checks.sh   # Start services before tests if not running
#   RUN_E2E=1 ./quick_checks.sh # Include E2E tests
#
# Exit codes:
#   0 - All checks passed
#   1 - Tests failed
#   2 - Preflight failure (services not running, START=0)
################################################################################

set -euo pipefail

root_dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root_dir"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# LOAD CONFIGURATION FROM ENV FILE
# ============================================================================

env_file=".claude/.env.claude"
COMPOSE_FILE=""
COMPOSE_DEV_FILE=""
COMPOSE_PROJECT_NAME=""
API_SERVICE=""
WEB_SERVICE=""

if [[ -f "$env_file" ]]; then
  while IFS='=' read -r key value; do
    case "$key" in
      COMPOSE_FILE|COMPOSE_DEV_FILE|COMPOSE_PROJECT_NAME|API_SERVICE|WEB_SERVICE)
        value="${value%\"}"
        value="${value#\"}"
        export "$key=$value"
        ;;
    esac
  done < <(grep -E "^[A-Z_]+=" "$env_file" 2>/dev/null || true)
fi

# Allow env overrides
COMPOSE_FILE="${COMPOSE_FILE:-}"
COMPOSE_DEV_FILE="${COMPOSE_DEV_FILE:-}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-}"
API_SERVICE="${API_SERVICE:-backend}"
WEB_SERVICE="${WEB_SERVICE:-web}"

QUICK_CHECKS_TIMEOUT="${QUICK_CHECKS_TIMEOUT:-180}"

# Build compose command dynamically
COMPOSE=""
if [[ -n "$COMPOSE_FILE" ]] && [[ -f "$COMPOSE_FILE" ]]; then
  COMPOSE="docker compose -f $COMPOSE_FILE"
  if [[ -n "$COMPOSE_DEV_FILE" ]] && [[ -f "$COMPOSE_DEV_FILE" ]]; then
    COMPOSE="$COMPOSE -f $COMPOSE_DEV_FILE"
  fi
  if [[ -n "$COMPOSE_PROJECT_NAME" ]]; then
    COMPOSE="docker compose -p $COMPOSE_PROJECT_NAME -f $COMPOSE_FILE"
    if [[ -n "$COMPOSE_DEV_FILE" ]] && [[ -f "$COMPOSE_DEV_FILE" ]]; then
      COMPOSE="$COMPOSE -f $COMPOSE_DEV_FILE"
    fi
  fi
fi

TIMEOUT_BIN="$(command -v timeout || true)"
if [[ -z "$TIMEOUT_BIN" ]]; then
    echo -e "${RED}PREFLIGHT FAILURE: 'timeout' not found${NC}"
    echo -e "${YELLOW}Install coreutils (Linux: apt/yum; macOS: brew install coreutils)${NC}"
    exit 2
fi

echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo -e "${BLUE} Quick Checks${NC}"
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Compose:${NC} ${COMPOSE_FILE:-"(none)"}"
echo -e "${BLUE}Project:${NC} ${COMPOSE_PROJECT_NAME:-"(auto)"}"
echo -e "${BLUE}Timeout:${NC} ${QUICK_CHECKS_TIMEOUT}s"
echo ""

# ============================================================================
# PREFLIGHT FUNCTIONS
# ============================================================================

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

run_stage() {
    local name="$1"
    shift
    local start_ts
    start_ts="$(date +%s)"
    echo -e "${BLUE}Stage: ${name} (start $(timestamp))${NC}"

    "$TIMEOUT_BIN" "$QUICK_CHECKS_TIMEOUT" "$@"
    local rc=$?
    if [[ $rc -ne 0 ]]; then
        local end_ts
        end_ts="$(date +%s)"
        local elapsed=$((end_ts - start_ts))

        if [[ $rc -eq 124 || $rc -eq 137 ]]; then
            echo -e "${RED}Stage '${name}' timed out after ${elapsed}s (limit ${QUICK_CHECKS_TIMEOUT}s)${NC}"
            echo -e "${YELLOW}Hint:${NC} reduce scope or increase QUICK_CHECKS_TIMEOUT."
            exit 2
        fi

        echo -e "${RED}Stage '${name}' failed after ${elapsed}s (exit ${rc})${NC}"
        return $rc
    fi

    local end_ts
    end_ts="$(date +%s)"
    local elapsed=$((end_ts - start_ts))
    echo -e "${GREEN}Stage '${name}' completed in ${elapsed}s${NC}"
    echo ""
}

is_service_running() {
    local service="$1"
    if [[ -z "$COMPOSE_PROJECT_NAME" ]]; then
        return 1
    fi
    local container_id
    container_id=$(docker ps -q --filter "label=com.docker.compose.service=$service" --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME" 2>/dev/null)
    [[ -n "$container_id" ]]
}

check_required_services() {
    if [[ -z "$COMPOSE_FILE" ]]; then
        echo -e "${YELLOW}No compose file - skipping service checks${NC}"
        return 0
    fi

    local missing=()

    echo -e "${YELLOW}Preflight: checking required services...${NC}"

    if [[ -n "$API_SERVICE" ]]; then
        if is_service_running "$API_SERVICE"; then
            echo -e "  ${GREEN}✓ $API_SERVICE (API)${NC}"
        else
            echo -e "  ${RED}✗ $API_SERVICE (API)${NC}"
            missing+=("$API_SERVICE")
        fi
    fi

    if [[ -n "$WEB_SERVICE" ]]; then
        if is_service_running "$WEB_SERVICE"; then
            echo -e "  ${GREEN}✓ $WEB_SERVICE (Web)${NC}"
        else
            echo -e "  ${RED}✗ $WEB_SERVICE (Web)${NC}"
            missing+=("$WEB_SERVICE")
        fi
    fi

    echo ""

    if [[ ${#missing[@]} -gt 0 ]]; then
        return 1
    fi
    return 0
}

check_python_dependencies() {
    if [[ -z "$COMPOSE" ]] || [[ -z "$API_SERVICE" ]]; then
        return 0
    fi

    local missing=()
    local deps=("mongomock_motor")

    echo -e "${YELLOW}Preflight: checking Python deps in $API_SERVICE...${NC}"

    for module in "${deps[@]}"; do
        if ! $COMPOSE exec -T "$API_SERVICE" python - <<PY >/dev/null 2>&1
import importlib
importlib.import_module("$module")
PY
        then
            missing+=("$module")
        else
            echo -e "  ${GREEN}✓ $module${NC}"
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo ""
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}PREFLIGHT FAILURE: Missing Python deps in $API_SERVICE${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${YELLOW}Missing:${NC} ${missing[*]}"
        echo ""
        echo -e "${BLUE}Fix:${NC} Rebuild backend with dev deps"
        echo ""
        exit 2
    fi

    echo ""
}

check_weaviate_ready() {
    if [[ "${RUN_E2E:-0}" != "1" ]]; then
        return 0
    fi

    if ! command -v curl >/dev/null 2>&1; then
        echo -e "${RED}PREFLIGHT FAILURE: 'curl' not found${NC}"
        exit 2
    fi

    echo -e "${YELLOW}Preflight: checking Weaviate health...${NC}"
    if ! curl -fsS --max-time 2 "http://localhost:8080/v1/.well-known/ready" >/dev/null 2>&1; then
        echo ""
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}PREFLIGHT FAILURE: Weaviate not healthy${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        exit 2
    fi

    echo -e "  ${GREEN}✓ weaviate healthy${NC}"
    echo ""
}

start_services() {
    echo -e "${YELLOW}Starting services with 'make dev'...${NC}"
    echo ""

    if ! make dev; then
        echo -e "${RED}Failed to start services${NC}"
        exit 2
    fi

    echo -e "${YELLOW}Waiting for services to be ready...${NC}"
    local max_wait=60
    local waited=0

    while [[ $waited -lt $max_wait ]]; do
        if is_service_running "$API_SERVICE" && is_service_running "$WEB_SERVICE"; then
            echo -e "${GREEN}Services are ready!${NC}"
            echo ""
            return 0
        fi
        sleep 2
        waited=$((waited + 2))
        echo -n "."
    done

    echo ""
    echo -e "${RED}Timeout waiting for services to start${NC}"
    exit 2
}

# ============================================================================
# MAIN
# ============================================================================

preflight_start="$(date +%s)"
echo -e "${BLUE}Stage: preflight (start $(timestamp))${NC}"

# Skip service checks if no compose file
if [[ -n "$COMPOSE_FILE" ]]; then
    if ! check_required_services; then
        if [[ "${START:-0}" == "1" ]]; then
            start_services
        else
            echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${RED}PREFLIGHT FAILURE: Required services not running${NC}"
            echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo ""
            echo -e "${YELLOW}Options:${NC}"
            echo "  1. Start services manually:  make dev"
            echo "  2. Auto-start with tests:    START=1 ./quick_checks.sh"
            echo ""
            if [[ -n "$COMPOSE_PROJECT_NAME" ]]; then
                echo -e "${BLUE}Current container status:${NC}"
                docker ps --format "table {{.Names}}\t{{.Status}}" --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME" 2>/dev/null || echo "  (no containers found)"
            fi
            echo ""
            exit 2
        fi
    fi

    check_python_dependencies
    check_weaviate_ready
fi

preflight_end="$(date +%s)"
echo -e "${GREEN}Stage 'preflight' completed in $((preflight_end - preflight_start))s${NC}"
echo ""

# Pytest selection (quick checks should be fast + deterministic)
PYTEST_ARGS=""
API_TEST_PATHS=""
if [[ "${RUN_E2E:-0}" != "1" ]]; then
    PYTEST_ARGS="-m \"unit and not integration and not e2e\""
    PYTEST_ARGS+=" --ignore=tests/integration --ignore=tests/e2e"
    PYTEST_ARGS+=" --ignore=tests/performance --ignore=tests/manual"
    API_TEST_PATHS="tests/unit"
fi

# Run tests
echo -e "${BLUE}────────────────────────────────────────${NC}"
echo -e "${BLUE}Running tests...${NC}"
echo -e "${BLUE}────────────────────────────────────────${NC}"
echo ""

echo "+ make test T=api (API_SERVICE=$API_SERVICE)"
if run_stage "api tests" env API_SERVICE="$API_SERVICE" TEST_PATHS="$API_TEST_PATHS" make test T=api TEST_ARGS="$PYTEST_ARGS"; then
    :
else
    rc=$?
    if [[ $rc -eq 2 ]]; then
        echo -e "${YELLOW}Note:${NC} make returned 2; treating as test failure (exit 1)."
        rc=1
    fi
    echo -e "${RED}API tests failed${NC}"
    exit "${rc}"
fi

echo ""
echo "+ make test T=web (WEB_SERVICE=$WEB_SERVICE)"
if run_stage "web tests" env WEB_SERVICE="$WEB_SERVICE" make test T=web; then
    :
else
    rc=$?
    if [[ $rc -eq 2 ]]; then
        echo -e "${YELLOW}Note:${NC} make returned 2; treating as test failure (exit 1)."
        rc=1
    fi
    echo -e "${RED}Web tests failed${NC}"
    exit "${rc}"
fi

if [[ "${RUN_E2E:-0}" == "1" ]]; then
    echo ""
    echo "+ make test T=e2e"
    if run_stage "e2e tests" make test T=e2e; then
        :
    else
        rc=$?
        if [[ $rc -eq 2 ]]; then
            echo -e "${YELLOW}Note:${NC} make returned 2; treating as test failure (exit 1)."
            rc=1
        fi
        echo -e "${RED}E2E tests failed${NC}"
        exit "${rc}"
    fi
else
    echo ""
    echo "(skip) make test T=e2e (set RUN_E2E=1 to enable)"
fi

# Write result to docs/agent
mkdir -p .claude/docs
{
  echo "# Quick Checks Result"
  echo ""
  echo "**Time:** $(timestamp)"
  echo "**Status:** PASS"
  echo ""
  echo "## Configuration"
  echo ""
  echo "- Compose: ${COMPOSE_FILE:-"(none)"}"
  echo "- API: ${API_SERVICE:-"(none)"}"
  echo "- Web: ${WEB_SERVICE:-"(none)"}"
  echo ""
  echo "## Tests Run"
  echo ""
  echo "- API tests: PASS"
  echo "- Web tests: PASS"
  if [[ "${RUN_E2E:-0}" == "1" ]]; then
    echo "- E2E tests: PASS"
  else
    echo "- E2E tests: SKIPPED"
  fi
} > .claude/docs/quick_checks.md

echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN} All quick checks passed!${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo ""
echo "Report: .claude/docs/quick_checks.md"
