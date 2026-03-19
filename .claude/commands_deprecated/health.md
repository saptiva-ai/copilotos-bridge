---
name: health
description: Quick health check of all services.
argument-hint: ""
allowed-tools: [Bash]
disable-model-invocation: true
---

!bash
set -euo pipefail

# Ensure we're in project root
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Load env
env_file=".claude/.env.claude"
COMPOSE_FILE=""
COMPOSE_PROJECT_NAME=""
if [[ -f "$env_file" ]]; then
  COMPOSE_FILE=$(grep "^COMPOSE_FILE=" "$env_file" | cut -d= -f2 | tr -d '"')
  COMPOSE_PROJECT_NAME=$(grep "^COMPOSE_PROJECT_NAME=" "$env_file" | cut -d= -f2 | tr -d '"')
fi

echo "== Service Health =="
echo ""

# Handle no compose file case
if [[ -z "$COMPOSE_FILE" ]] || [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "No compose file detected (repo-only mode)"
  echo ""
  echo "Running containers:"
  docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "No containers running"
  exit 0
fi

# Get all services from compose
services=$(docker compose -f "$COMPOSE_FILE" config --services 2>/dev/null || echo "")

if [[ -z "$services" ]]; then
  echo "Unable to read compose services"
  exit 2
fi

check_service() {
  local svc=$1
  local status
  status=$(docker compose -f "$COMPOSE_FILE" ps --format json "$svc" 2>/dev/null | head -1)

  if [[ -z "$status" ]]; then
    echo "  $svc: not running"
    return 1
  fi

  local state health
  state=$(echo "$status" | grep -o '"State":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
  health=$(echo "$status" | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || echo "")

  if [[ "$state" == "running" ]]; then
    if [[ "$health" == "healthy" || -z "$health" ]]; then
      echo "  $svc: ${health:-running}"
      return 0
    else
      echo "  $svc: $health"
      return 1
    fi
  else
    echo "  $svc: $state"
    return 1
  fi
}

all_healthy=true

echo "Services:"
for svc in $services; do
  check_service "$svc" || all_healthy=false
done

echo ""
if [[ "$all_healthy" == "true" ]]; then
  echo "All services healthy"
  exit 0
else
  echo "Some services need attention. Run /infra-doctor for details."
  exit 1
fi
