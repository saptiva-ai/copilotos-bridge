---
name: dev-up
description: Show running containers; optionally start compose stack and wait for backend health.
argument-hint: "[--start]"
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
API_SERVICE=""
if [[ -f "$env_file" ]]; then
  COMPOSE_FILE=$(grep "^COMPOSE_FILE=" "$env_file" | cut -d= -f2 | tr -d '"')
  API_SERVICE=$(grep "^API_SERVICE=" "$env_file" | cut -d= -f2 | tr -d '"')
fi

start="${START:-0}"

for arg in "$@"; do
  if [[ "$arg" == "--start" ]]; then
    start=1
  fi
done

echo "== Running Containers =="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""

# Handle no compose file case
if [[ -z "$COMPOSE_FILE" ]] || [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "No compose file detected (repo-only mode)"
  echo ""
  echo "To use compose, ensure a docker-compose.yml exists in:"
  echo "  - ./docker-compose.yml"
  echo "  - ./infra/docker-compose.yml"
  echo "  - ./.docker/docker-compose.yml"
  exit 0
fi

if [[ "$start" == "1" ]]; then
  echo "+ docker compose -f $COMPOSE_FILE up -d"
  docker compose -f "$COMPOSE_FILE" up -d
  echo ""
  echo "Waiting for services to start..."
  sleep 3
fi

echo ""
echo "== Service Status =="
docker compose -f "$COMPOSE_FILE" ps --format "table {{.Service}}\t{{.State}}\t{{.Health}}" 2>/dev/null || echo "Unable to get compose status"

# Check API service health if defined
if [[ -n "$API_SERVICE" ]]; then
  echo ""
  echo "== $API_SERVICE Health =="
  backend_status=$(docker compose -f "$COMPOSE_FILE" ps --format json "$API_SERVICE" 2>/dev/null | head -1 || echo "")

  if [[ -n "$backend_status" ]]; then
    state=$(echo "$backend_status" | grep -o '"State":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
    health=$(echo "$backend_status" | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || echo "")

    if [[ "$state" == "running" ]]; then
      if [[ "$health" == "healthy" || -z "$health" ]]; then
        echo "$API_SERVICE: ${health:-running}"
      elif [[ "$health" == "starting" ]]; then
        echo "$API_SERVICE: starting (waiting...)"
        # Wait for health with timeout
        for i in {1..30}; do
          sleep 2
          backend_status=$(docker compose -f "$COMPOSE_FILE" ps --format json "$API_SERVICE" 2>/dev/null | head -1 || echo "")
          health=$(echo "$backend_status" | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || echo "")
          if [[ "$health" == "healthy" ]]; then
            echo "$API_SERVICE: healthy"
            break
          fi
          if [[ $i -eq 30 ]]; then
            echo "$API_SERVICE: timeout waiting for health"
          fi
        done
      else
        echo "$API_SERVICE: $health"
      fi
    else
      echo "$API_SERVICE: $state"
    fi
  else
    echo "$API_SERVICE: not running"
    if [[ "$start" != "1" ]]; then
      echo ""
      echo "Tip: Run '/dev-up --start' to start the stack"
    fi
  fi
fi

echo ""
echo "== Common Endpoints =="
echo "Check your compose file for actual port mappings."
