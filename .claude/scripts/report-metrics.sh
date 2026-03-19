#!/usr/bin/env bash
#
# report-metrics.sh - Generate observability reports from Claude Code metrics
#
# Usage:
#   report-metrics.sh [--format=<text|json|markdown>] [--period=<today|week|month|all>]
#
# Options:
#   --format    Output format: text (default), json, markdown
#   --period    Time period: today, week, month, all (default)
#   --agents    Show agent-specific stats
#   --phases    Show workflow phase stats
#   --errors    Show error summary
#   --summary   Show quick summary only
#
# Examples:
#   report-metrics.sh                      # Full report, all time
#   report-metrics.sh --period=today       # Today's metrics
#   report-metrics.sh --format=markdown    # Markdown output for docs
#   report-metrics.sh --summary            # Quick summary
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="${SCRIPT_DIR}/../logs"
METRICS_FILE="${LOGS_DIR}/metrics.jsonl"

# Defaults
FORMAT="text"
PERIOD="all"
SHOW_AGENTS=false
SHOW_PHASES=false
SHOW_ERRORS=false
SUMMARY_ONLY=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --format=*)
            FORMAT="${arg#*=}"
            ;;
        --period=*)
            PERIOD="${arg#*=}"
            ;;
        --agents)
            SHOW_AGENTS=true
            ;;
        --phases)
            SHOW_PHASES=true
            ;;
        --errors)
            SHOW_ERRORS=true
            ;;
        --summary)
            SUMMARY_ONLY=true
            ;;
        --help|-h)
            head -30 "$0" | tail -25
            exit 0
            ;;
    esac
done

# Check if metrics file exists
if [[ ! -f "${METRICS_FILE}" ]]; then
    echo "No metrics found. File does not exist: ${METRICS_FILE}"
    echo "Run some Claude Code sessions to generate metrics."
    exit 0
fi

# Calculate date filter based on period
get_date_filter() {
    case $PERIOD in
        today)
            date -u +"%Y-%m-%d"
            ;;
        week)
            date -u -d "7 days ago" +"%Y-%m-%d" 2>/dev/null || date -u -v-7d +"%Y-%m-%d"
            ;;
        month)
            date -u -d "30 days ago" +"%Y-%m-%d" 2>/dev/null || date -u -v-30d +"%Y-%m-%d"
            ;;
        all)
            echo "1970-01-01"
            ;;
    esac
}

DATE_FILTER=$(get_date_filter)

# Filter metrics by date
filter_metrics() {
    if command -v jq &>/dev/null; then
        jq -c "select(.timestamp >= \"${DATE_FILTER}\")" "${METRICS_FILE}" 2>/dev/null || cat "${METRICS_FILE}"
    else
        grep -E "\"timestamp\":\"${DATE_FILTER:0:10}" "${METRICS_FILE}" 2>/dev/null || cat "${METRICS_FILE}"
    fi
}

# Count events by type
count_events() {
    local event_type="$1"
    local count
    count=$(filter_metrics | grep -c "\"event\":\"${event_type}\"" 2>/dev/null) || count=0
    # Ensure single number
    printf "%d" "${count:-0}"
}

# Get unique values for a field
get_unique_values() {
    local field="$1"
    if command -v jq &>/dev/null; then
        filter_metrics | jq -r ".${field} // empty" 2>/dev/null | sort | uniq -c | sort -rn
    else
        filter_metrics | grep -oP "\"${field}\":\"[^\"]+\"" | cut -d'"' -f4 | sort | uniq -c | sort -rn
    fi
}

# Calculate average duration
calc_avg_duration() {
    local event_type="$1"
    if command -v jq &>/dev/null; then
        filter_metrics | jq -r "select(.event == \"${event_type}\" and .duration_ms != null) | .duration_ms" 2>/dev/null | \
            awk '{sum+=$1; count++} END {if(count>0) printf "%.0f", sum/count; else print "N/A"}'
    else
        echo "N/A"
    fi
}

# Generate text report
generate_text_report() {
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Claude Code Observability Report"
    echo "  Period: ${PERIOD} (since ${DATE_FILTER})"
    echo "  Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    # Summary counts
    local sessions=$(count_events "session_start")
    local agents_started=$(count_events "agent_start")
    local agents_completed=$(count_events "agent_end")
    local commands=$(count_events "command_start")
    local phases=$(count_events "phase_start")
    local errors=$(count_events "error")

    echo "📊 Summary"
    echo "───────────────────────────────────────────────────────────────"
    printf "  Sessions Started:    %s\n" "$sessions"
    printf "  Agents Invoked:      %s\n" "$agents_started"
    printf "  Agents Completed:    %s\n" "$agents_completed"
    printf "  Commands Executed:   %s\n" "$commands"
    printf "  Workflow Phases:     %s\n" "$phases"
    printf "  Errors Logged:       %s\n" "$errors"
    echo ""

    if [[ "$SUMMARY_ONLY" == "true" ]]; then
        return
    fi

    # Agent breakdown
    if [[ "$SHOW_AGENTS" == "true" ]] || [[ "$SUMMARY_ONLY" == "false" ]]; then
        echo "🤖 Agent Usage"
        echo "───────────────────────────────────────────────────────────────"
        local agent_counts=$(get_unique_values "agent")
        if [[ -n "$agent_counts" ]]; then
            echo "$agent_counts" | while read count name; do
                [[ -n "$name" ]] && printf "  %-25s %s invocations\n" "$name" "$count"
            done
        else
            echo "  No agent data available"
        fi
        echo ""
    fi

    # Phase breakdown
    if [[ "$SHOW_PHASES" == "true" ]] || [[ "$SUMMARY_ONLY" == "false" ]]; then
        echo "🔄 Workflow Phases"
        echo "───────────────────────────────────────────────────────────────"
        local phase_counts=$(get_unique_values "phase")
        if [[ -n "$phase_counts" ]]; then
            echo "$phase_counts" | while read count name; do
                [[ -n "$name" ]] && printf "  %-25s %s executions\n" "$name" "$count"
            done
        else
            echo "  No phase data available"
        fi
        echo ""
    fi

    # Error breakdown
    if [[ "$SHOW_ERRORS" == "true" ]] || [[ "$errors" -gt 0 ]]; then
        echo "❌ Errors"
        echo "───────────────────────────────────────────────────────────────"
        if [[ "$errors" -gt 0 ]]; then
            filter_metrics | grep "\"event\":\"error\"" | tail -5 | while read line; do
                if command -v jq &>/dev/null; then
                    local msg=$(echo "$line" | jq -r '.message // "Unknown error"')
                    local ts=$(echo "$line" | jq -r '.timestamp // ""')
                    printf "  [%s] %s\n" "${ts:0:19}" "$msg"
                else
                    echo "  $line"
                fi
            done
        else
            echo "  No errors logged"
        fi
        echo ""
    fi

    # Performance stats
    echo "⏱️  Performance"
    echo "───────────────────────────────────────────────────────────────"
    local avg_agent=$(calc_avg_duration "agent_end")
    local avg_phase=$(calc_avg_duration "phase_end")
    printf "  Avg Agent Duration:  %s ms\n" "$avg_agent"
    printf "  Avg Phase Duration:  %s ms\n" "$avg_phase"
    echo ""

    echo "═══════════════════════════════════════════════════════════════"
    echo "  Metrics file: ${METRICS_FILE}"
    echo "  Total entries: $(wc -l < "${METRICS_FILE}" 2>/dev/null || echo "0")"
    echo "═══════════════════════════════════════════════════════════════"
}

# Generate markdown report
generate_markdown_report() {
    local sessions=$(count_events "session_start")
    local agents_started=$(count_events "agent_start")
    local agents_completed=$(count_events "agent_end")
    local commands=$(count_events "command_start")
    local phases=$(count_events "phase_start")
    local errors=$(count_events "error")

    cat << EOF
# Claude Code Observability Report

**Period:** ${PERIOD} (since ${DATE_FILTER})
**Generated:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")

## Summary

| Metric | Count |
|--------|-------|
| Sessions Started | ${sessions} |
| Agents Invoked | ${agents_started} |
| Agents Completed | ${agents_completed} |
| Commands Executed | ${commands} |
| Workflow Phases | ${phases} |
| Errors Logged | ${errors} |

## Agent Usage

\`\`\`
$(get_unique_values "agent" | head -10)
\`\`\`

## Workflow Phases

\`\`\`
$(get_unique_values "phase" | head -10)
\`\`\`

## Performance

| Metric | Value |
|--------|-------|
| Avg Agent Duration | $(calc_avg_duration "agent_end") ms |
| Avg Phase Duration | $(calc_avg_duration "phase_end") ms |

---
*Metrics file: ${METRICS_FILE}*
EOF
}

# Generate JSON report
generate_json_report() {
    local sessions=$(count_events "session_start")
    local agents_started=$(count_events "agent_start")
    local agents_completed=$(count_events "agent_end")
    local commands=$(count_events "command_start")
    local phases=$(count_events "phase_start")
    local errors=$(count_events "error")

    cat << EOF
{
  "period": "${PERIOD}",
  "date_filter": "${DATE_FILTER}",
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "summary": {
    "sessions_started": ${sessions},
    "agents_invoked": ${agents_started},
    "agents_completed": ${agents_completed},
    "commands_executed": ${commands},
    "workflow_phases": ${phases},
    "errors_logged": ${errors}
  },
  "performance": {
    "avg_agent_duration_ms": "$(calc_avg_duration "agent_end")",
    "avg_phase_duration_ms": "$(calc_avg_duration "phase_end")"
  },
  "metrics_file": "${METRICS_FILE}",
  "total_entries": $(wc -l < "${METRICS_FILE}" 2>/dev/null || echo "0")
}
EOF
}

# Main
case $FORMAT in
    text)
        generate_text_report
        ;;
    markdown|md)
        generate_markdown_report
        ;;
    json)
        generate_json_report
        ;;
    *)
        echo "Unknown format: $FORMAT"
        exit 1
        ;;
esac
