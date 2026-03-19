---
name: triage
description: Generate and analyze daily feedback triage report. Runs data-gathering script, then Claude fills in LLM analysis sections. Usage /triage 2026-02-10
argument-hint: "<YYYY-MM-DD> [--dry-run] [--skip-analysis]"
allowed-tools: [Bash, Read, Write, Edit, Grep, Glob]
---

# /triage — Daily Feedback Triage Report

Generate a feedback triage report for a given date. The pipeline has 2 phases:
1. **Deterministic** (script): API calls, data aggregation, Jinja2 rendering → `docs/reports/feedback_triage/{date}.md`
2. **Analysis** (Claude): Read the rendered report and fill in sections marked `<!-- LLM_REQUIRED -->`

## Steps

### Phase 1: Data Gathering (script)

Run the triage report generator. The script calls the internal API endpoints and renders 6/7 sections deterministically.

First, load environment variables from `envs/.env` (only the keys the script needs):

```bash
cd "$(git rev-parse --show-toplevel)"

# Load env vars from envs/.env if not already set
if [[ -f envs/.env ]]; then
  # Extract only the vars the triage script needs (no secrets printed)
  _val() { grep "^$1=" envs/.env | head -1 | cut -d= -f2- | sed 's/^"//;s/"$//' ; }
  [[ -z "${INTERNAL_API_KEY:-}" ]] && export INTERNAL_API_KEY="$(_val INTERNAL_API_KEY)"
  [[ -z "${BACKEND_INTERNAL_KEY:-}" ]] && export BACKEND_INTERNAL_KEY="${INTERNAL_API_KEY}"
fi

python scripts/triage/generate_report.py \
  --date "$DATE" \
  --backend-url "${BACKEND_URL:-http://localhost:18000}" \
  --api-key "${BACKEND_INTERNAL_KEY:-${INTERNAL_API_KEY:-}}" \
  --output "docs/reports/feedback_triage/$DATE.md"
```

If the script fails with connection errors:
- Check SSH tunnel: `ssh -L 18000:localhost:8000 ${PROD_USER}@${PROD_HOST} -N -f`
- Check backend health: `curl -s http://localhost:18000/health`
- Check API key: ensure `INTERNAL_API_KEY` is set in `envs/.env` or exported in shell

If `--dry-run` is passed, print to stdout and stop (no Phase 2).

### Phase 2: LLM Analysis

Read the generated report file:

```
docs/reports/feedback_triage/{date}.md
```

Find all `<!-- LLM_REQUIRED -->` markers and replace them with analysis:

#### Section 1 — Resumen ejecutivo (3-5 lines)
Based on sections 0, 2, 3, and 4 data, write a concise executive summary:
- How many thumbs-down and what categories (STALE_CHART, COMPARISON_FORMAT, CATALOG_MISS, etc.)
- Whether any new bug patterns appeared or existing ones persisted
- Key metrics vs previous days (trend direction)
- Overall system health assessment

#### Section 5 — Hipotesis raiz
For each thumbs-down case in section 3, propose a root cause hypothesis:
- Reference the exact evidence from sections 2 (stale charts) and 4 (message threads)
- Classify by severity: S0 (data wrong), S1 (UX broken), S2 (cosmetic)
- Suggest which component is responsible (SQL generator, LLM, post-processor, chart renderer)
- If the bug matches a known pattern from previous triage reports, reference it

After filling sections 1 and 5, save the file.

### Phase 2.5: Deep Investigation (persistent bugs only)

This phase runs **only when** the triage report references feedback IDs that match existing DOING tickets in `docs/kanban/DOING/`. If no persistent bugs are detected, skip to Phase 3.

**Detection**: After Phase 2, scan the feedback IDs in the report. For each one, check if `docs/kanban/DOING/*/card.md` already references the same bug pattern (same handler, same query type, same failure mode). If yes, this is a **persistent bug** — it survived a previous fix iteration.

**For each persistent bug, perform this investigation:**

1. **Read the ticket's card.md** — understand what the previous fix attempted, which files were modified, what acceptance criteria were checked.

2. **Trace the code path** — starting from the user's query, follow the execution:
   - Query parsing: `query_spec_parser.py` → `QuerySpec` with `time_range`
   - Handler selection: `query_router.py` → which handler handles this query type
   - Handler execution: the specific handler's `handle()` method
   - Data pipeline: SQL generation → database query → Plotly trace building
   - LLM context: `analytics_extractor.py` → `llm_context_builder.py` → system prompt
   - Post-processing: `system_prompt_builder.py` → streaming to user

3. **Identify the gap** — answer these specific questions:
   - What did the previous fix change? (diff summary)
   - Why didn't it cover this case? (e.g., handler not called, condition not triggered, different code path)
   - Where exactly does the data diverge from expected? (line number + variable state)
   - Is there a missing integration point? (e.g., resolver not called from handler)

4. **Write findings to card.md** — add a `### Deep Investigation (YYYY-MM-DD)` section with:
   ```markdown
   ### Deep Investigation (YYYY-MM-DD)

   **Previous fix**: [summary of what was changed and when]
   **Gap identified**: [why the fix didn't cover this case]

   **Code trace**:
   | Step | File:Line | What happens | Problem |
   |------|-----------|-------------|---------|
   | 1 | file.py:N | description | gap/issue |

   **Fix strategy**: [specific change needed to close the gap]
   ```

5. **Update card.md status** — ensure the "Workflow Status" table reflects the re-analysis state.

### Phase 3: Summary

Print a brief summary of findings to the user:
- Number of thumbs-down analyzed
- Bug categories detected
- Any new patterns not seen before
- Recommended next steps (create tickets, fix priority, etc.)

## Arguments

- `$ARGUMENTS` contains the date and optional flags
- Parse the first positional argument as `DATE` (YYYY-MM-DD format)
- If `--dry-run`: only run Phase 1, print output, stop
- If `--skip-analysis`: run Phase 1, save file, skip Phase 2

## Environment

Variables are auto-loaded from `envs/.env` if not already exported:

- `INTERNAL_API_KEY`: API key for internal endpoints (read from `envs/.env`)
- `BACKEND_INTERNAL_KEY`: Alias for the same key (falls back to `INTERNAL_API_KEY`)
- `BACKEND_URL`: Backend API URL (default: http://localhost:18000 via SSH tunnel)

## Notes

- The script requires `requests` and `jinja2` Python packages
- Reports are saved to `docs/reports/feedback_triage/` (allowed by workflow rails)
- Previous reports in the same directory serve as format reference
- If no thumbs-down feedback exists for the date, the report will still be generated with empty sections
