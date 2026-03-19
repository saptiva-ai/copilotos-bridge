#!/usr/bin/env bash
#
# log-metrics.sh - Observability logging for Claude Code agentic workflows
#
# Usage:
#   log-metrics.sh <event_type> [key=value ...]
#
# Event Types:
#   session_start    - New Claude Code session started
#   session_end      - Session ended (manual call)
#   agent_start      - Agent/Task started
#   agent_end        - Agent/Task completed
#   command_start    - Slash command started
#   command_end      - Slash command completed
#   phase_start      - Workflow phase started (explore, plan, code, test, review, docs)
#   phase_end        - Workflow phase completed
#   error            - Error occurred
#   hook_exec        - Hook executed
#
# Examples:
#   log-metrics.sh session_start
#   log-metrics.sh agent_start agent=repo-scout task="Map frontend structure"
#   log-metrics.sh agent_end agent=repo-scout status=success duration_ms=1234
#   log-metrics.sh phase_start phase=explore epic=HU5
#   log-metrics.sh error message="Rate limit reached" context=Task
#
# Output:
#   Appends JSON lines to .claude/logs/metrics.jsonl
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_ROOT="${SCRIPT_DIR}/../.."
LOGS_DIR="${SCRIPT_DIR}/../logs"
METRICS_FILE="${LOGS_DIR}/metrics.jsonl"

# Ensure logs directory exists
mkdir -p "${LOGS_DIR}"

# Get event type
EVENT_TYPE="${1:-unknown}"
shift || true

# Build JSON object
build_json() {
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Start JSON
    local json="{"
    json+="\"timestamp\":\"${timestamp}\","
    json+="\"event\":\"${EVENT_TYPE}\","
    json+="\"session_id\":\"${CLAUDE_SESSION_ID:-$(cat /proc/sys/kernel/random/uuid 2>/dev/null || echo "unknown")}\""

    # Add key=value pairs
    for arg in "$@"; do
        if [[ "$arg" == *"="* ]]; then
            local key="${arg%%=*}"
            local value="${arg#*=}"
            # Escape quotes in value
            value="${value//\"/\\\"}"
            # Check if value is numeric
            if [[ "$value" =~ ^-?[0-9]+\.?[0-9]*$ ]]; then
                json+=",\"${key}\":${value}"
            else
                json+=",\"${key}\":\"${value}\""
            fi
        fi
    done

    # Add environment context
    json+=",\"cwd\":\"${PWD}\""
    json+=",\"user\":\"${USER:-unknown}\""

    json+="}"
    echo "$json"
}

# Log the event
log_event() {
    local json
    json=$(build_json "$@")
    echo "$json" >> "${METRICS_FILE}"

    # Also output to stderr for immediate feedback (optional, can be disabled)
    if [[ "${METRICS_VERBOSE:-0}" == "1" ]]; then
        echo "[metrics] $json" >&2
    fi
}

# Main
log_event "$@"
