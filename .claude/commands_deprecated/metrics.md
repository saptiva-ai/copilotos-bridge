# /metrics - Observability Dashboard

Generate observability reports for Claude Code agentic workflows.

## Usage

```
/metrics [period] [format]
```

## Parameters

- **period**: `today`, `week`, `month`, `all` (default: all)
- **format**: `text`, `markdown`, `json` (default: text)

## Examples

```
/metrics                    # Full report, all time
/metrics today              # Today's metrics
/metrics week markdown      # This week in markdown format
/metrics month json         # This month in JSON format
```

## Output

The report includes:

- **Summary**: Sessions, agents invoked, commands executed, errors
- **Agent Usage**: Which agents are used most frequently
- **Workflow Phases**: explore, plan, code, test, review, docs
- **Performance**: Average durations
- **Errors**: Recent error summary

## Execution

$ARGUMENTS

```bash
# Parse arguments
PERIOD="${1:-all}"
FORMAT="${2:-text}"

# Make script executable if needed
chmod +x .claude/scripts/report-metrics.sh 2>/dev/null || true

# Run report
.claude/scripts/report-metrics.sh --period="$PERIOD" --format="$FORMAT"
```

## Manual Logging

To log custom events:

```bash
# Log agent start
.claude/scripts/log-metrics.sh agent_start agent=repo-scout task="Map structure"

# Log agent end with duration
.claude/scripts/log-metrics.sh agent_end agent=repo-scout status=success duration_ms=5000

# Log workflow phase
.claude/scripts/log-metrics.sh phase_start phase=explore epic=HU5
.claude/scripts/log-metrics.sh phase_end phase=explore status=completed duration_ms=30000

# Log error
.claude/scripts/log-metrics.sh error message="Rate limit reached" context=Task
```

## Files

| File | Purpose |
|------|---------|
| `.claude/logs/metrics.jsonl` | Raw metrics data (JSON lines) |
| `.claude/scripts/log-metrics.sh` | Logging script |
| `.claude/scripts/report-metrics.sh` | Report generator |

## Maintenance

- Logs are stored in `.claude/logs/metrics.jsonl`
- Old logs can be archived or deleted manually
- Recommended: Archive logs monthly

```bash
# Archive old logs
mv .claude/logs/metrics.jsonl .claude/logs/metrics-$(date +%Y%m).jsonl
```
