# BUG-014: Ranking IMOR False Negative

**Status:** FIXED
**Priority:** High
**Reported:** 2026-01-09
**Fixed:** 2026-01-09

## Problem

Query: "¿Cuál es el ranking de bancos por IMOR?"

**Observed behavior:**
- LLM responds: "No encuentro información sobre el ranking de bancos por IMOR en el documento disponible."
- BUT the chart IS displayed correctly with ranking data for all banks
- Chart shows IMOR with "Promedio: 1.99%" in the sidebar

**Expected behavior:**
- LLM should acknowledge the ranking data and provide analysis of which banks lead/trail

## Root Cause

For ranking queries:
1. `bank_names` is intentionally `[]` (empty) because no specific banks are requested
2. The chart contains data for ALL banks (from SQL: `SELECT * FROM ... ORDER BY imor`)
3. BUT the LLM context says "Bancos: " (empty) so LLM thinks there's no data
4. The `_extract_chart_statistics()` function extracts stats correctly from plotly traces
5. BUT the context doesn't convey that it's a ranking of ALL banks

## Fix Applied

**File:** `apps/backend/src/routers/chat/handlers/streaming_handler.py`

**Changes:**
1. Detect when `bank_names_list` is empty
2. Extract actual bank names from plotly trace data
3. Set `is_ranking = True` when banks are extracted from traces
4. Add ranking-specific context for the LLM with instructions to:
   - Mention who leads the ranking
   - Highlight positions of relevant banks
   - Compare extreme values
   - Provide context about high/low rankings

## Testing

Query: "¿Cuál es el ranking de bancos por IMOR?"

Expected response should:
- Acknowledge the ranking data exists
- Mention which banks have highest/lowest IMOR
- Provide context about what IMOR means
- NOT say "No encuentro información"

## Test Coverage

**Unit tests:** 47 cases
- `apps/backend/tests/unit/test_ranking_context_extraction.py`

**E2E tests:** 34 cases
- `tests/e2e/test_ranking_false_negative.py`

Run tests:
```bash
# Unit tests
python -c "exec(open('apps/backend/tests/unit/test_ranking_context_extraction.py').read())"

# E2E tests (requires backend)
python tests/e2e/test_ranking_false_negative.py --category imor
```

## Commits

| Commit | Description |
|--------|-------------|
| `e9f2b3f1` | Fix: detect ranking, extract banks from traces |
| `9c1f86d6` | Tests: initial 14 unit + 7 e2e |
| `4f5087f0` | Tests: enhanced 47 unit + 34 e2e |

## Deployment

**Container to update:** `backend` only

The fix is in `apps/backend/src/routers/chat/handlers/streaming_handler.py`
