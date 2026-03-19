---
name: infra-doctor
description: Diagnose compose services, health, and basic host resources.
argument-hint: ""
allowed-tools: [Bash, Read]
disable-model-invocation: true
---

!bash
set -euo pipefail

# Ensure we're in project root
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Load env for compose file
env_file=".claude/.env.claude"
COMPOSE_FILE=""
if [[ -f "$env_file" ]]; then
  COMPOSE_FILE=$(grep "^COMPOSE_FILE=" "$env_file" | cut -d= -f2 | tr -d '"')
fi

out_file=".claude/docs/infra_doctor.md"

mkdir -p .claude/docs

echo "Running infrastructure diagnostics..."
echo ""

{
  echo "# Infrastructure Diagnostics Report"
  echo ""
  echo "Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo ""

  if [[ -z "$COMPOSE_FILE" ]] || [[ ! -f "$COMPOSE_FILE" ]]; then
    echo "**Mode:** No compose file detected (repo-only mode)"
    echo ""
    echo "## Running Containers"
    echo "\`\`\`"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "docker unavailable"
    echo "\`\`\`"
  else
    echo "**Compose:** $COMPOSE_FILE"
    echo ""

    # Get available services dynamically
    services=$(docker compose -f "$COMPOSE_FILE" config --services 2>/dev/null || echo "")

    echo "## Compose Services"
    echo "\`\`\`"
    echo "$services"
    echo "\`\`\`"
    echo ""

    echo "## Running Containers"
    echo "\`\`\`"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "docker unavailable"
    echo "\`\`\`"
    echo ""

    echo "## Compose Status"
    echo "\`\`\`"
    docker compose -f "$COMPOSE_FILE" ps 2>/dev/null || echo "docker compose unavailable"
    echo "\`\`\`"
    echo ""

    echo "## Service Health"
    echo ""
    echo "| Service | Status | Health |"
    echo "|---------|--------|--------|"
    for svc in $services; do
      status=$(docker compose -f "$COMPOSE_FILE" ps --format json "$svc" 2>/dev/null | head -1 || echo "")
      if [[ -n "$status" ]]; then
        state=$(echo "$status" | grep -o '"State":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
        health=$(echo "$status" | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || echo "-")
        echo "| $svc | $state | ${health:--} |"
      else
        echo "| $svc | not running | - |"
      fi
    done
    echo ""

    echo "## Recent Logs (errors only)"
    echo ""
    for svc in $services; do
      error_lines=$(docker compose -f "$COMPOSE_FILE" logs --tail=50 "$svc" 2>/dev/null | grep -i -E "(error|exception|fail|critical)" | tail -10 || echo "")
      if [[ -n "$error_lines" ]]; then
        echo "### $svc"
        echo "\`\`\`"
        echo "$error_lines"
        echo "\`\`\`"
        echo ""
      fi
    done
  fi

  echo "## Disk Usage"
  echo "\`\`\`"
  df -h / 2>/dev/null || echo "df not available"
  echo "\`\`\`"
  echo ""

  echo "## Memory"
  echo "\`\`\`"
  free -m 2>/dev/null || echo "free not available"
  echo "\`\`\`"
  echo ""

  echo "## Docker Resources"
  echo "\`\`\`"
  docker system df 2>/dev/null || echo "docker system df not available"
  echo "\`\`\`"

} > "$out_file"

echo "Report saved to: $out_file"
echo ""

# Quick summary to stdout
echo "== Quick Summary =="
if [[ -n "$COMPOSE_FILE" ]] && [[ -f "$COMPOSE_FILE" ]]; then
  docker compose -f "$COMPOSE_FILE" ps --format "table {{.Service}}\t{{.State}}\t{{.Health}}" 2>/dev/null || echo "Unable to get status"
else
  docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "No containers running"
fi
echo ""
echo "Review full report: $out_file"
