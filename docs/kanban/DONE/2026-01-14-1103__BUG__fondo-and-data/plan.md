# Implementation Plan: ISSUE-007 — Multiple Data & UX Bugs

**Status**: Planning
**Last Updated**: 2026-01-14
**Estimated Phases**: 5

---

## Overview

This plan addresses 8 related bugs affecting data accuracy, UX, and persistence in the Bank Advisor chat system. Issues are organized by layer (data, parsing, UX, persistence) with cross-cutting observability improvements.

---

## Phase 1: Mongo Investigation & Evidence Collection

**Goal**: Locate exact documents/conversations causing each bug and confirm root causes.

### Tasks

1. **Identify environment and database**
   - Confirm which environment Carlos/Cris were using (production/demo/staging)
   - Document connection string (without credentials) and database name
   - Verify tenant/namespace configuration
   - Check if multi-tenant routing is involved

2. **Verify data recency for each metric**
   - Query `max(date)` for IMOR, ICAP, CARTERA_VIVIENDA_TOTAL collections
   - Compare against expected range (should have Sep/Oct 2025 per Cris)
   - Document schema of date fields (Date object vs string, format)
   - Check if 2025 data exists but in different schema/collection

3. **Find conversations matching screenshots**
   - Search by text patterns from screenshots (see queries in issue.md)
   - Extract `conversation_id`, `message_id`, `artifact_id` for each
   - Document timestamps (should be 2026-01-13 or 2026-01-14)

4. **Analyze IMOR/ICAP "2024%" documents**
   - Find messages containing "2024%" text
   - Extract raw documents from IMOR/ICAP collections referenced
   - Document field structure: `{ date, year, value, bank, ... }`
   - Identify if `value` is missing/null and `year` exists
   - Trace parsing logic that converts doc → formatted string

5. **Analyze chart error for CARTERA_VIVIENDA_TOTAL**
   - Find artifact by metric_key or error message
   - Validate artifact schema: `{ series: [{ x, y }], ... }`
   - Check for null/NaN/string values in series data
   - Document expected vs actual payload

6. **Analyze table with incorrect numbers**
   - Find message with "Evolución de la cartera hipotecaria"
   - Check if table includes source attribution (doc IDs, citations)
   - Verify if numbers match raw data or are synthesized/hallucinated

7. **Analyze clarification rendering**
   - Find message with "Necesito un poco más de información"
   - Extract `ui_blocks`, `actions`, or `suggestions` structure
   - Document current schema and how frontend maps it to components

8. **Analyze chart persistence failure**
   - Find conversation with ICAP chart (BBVA vs Santander)
   - Verify if artifact exists in DB and is linked to message
   - Check artifact_id references in messages
   - Document rehydration flow when loading conversation history

### Deliverables

- `research.md` with:
  - Table: screenshot → conversation_id, message_id, artifact_id
  - Root cause confirmation for each bug (with evidence)
  - Environment configuration details
  - Sample documents/payloads showing the issue

---

## Phase 2: Data Layer Fixes

**Goal**: Fix incorrect data, wrong connections, and parsing errors.

### Tasks

1. **Fix environment/database connection**
   - If connected to wrong DB: update configuration to point to current data
   - If multi-tenant routing issue: fix tenant resolution logic
   - Add validation on startup: log max(date) for key metrics

2. **Fix IMOR/ICAP parsing (2024% bug)**
   - Locate where metric values are formatted: `f"{value}%"`
   - Add validation: if `value is None or value > 1000`, mark as invalid
   - Fix fallback logic: do NOT use `doc.get("value", doc.get("year"))`
   - Add unit tests:
     - `test_metric_with_missing_value_returns_none()`
     - `test_metric_percentage_above_100_raises_error()`
     - `test_year_not_used_as_value_fallback()`

3. **Fix unit conversion errors**
   - Review if percentages are stored as decimals (0.02) or integers (2)
   - Ensure consistent conversion: `value * 100` applied exactly once
   - Add logging: before/after formatting for debugging

4. **Add data validation guards**
   - Before returning metrics: validate schema
   - Reject documents where `value == year` (obvious error)
   - Reject percentages > 100% (unless explicitly allowed for certain metrics)
   - Return structured error instead of invalid data

### Files to Modify

- `plugins/bank-advisor-private/src/bankadvisor/repositories/kpi_repository.py`
- `plugins/bank-advisor-private/src/bankadvisor/repositories/financial_repository.py`
- `plugins/bank-advisor-private/src/bankadvisor/handlers/multi_metric_handler.py`
- `plugins/bank-advisor-private/src/bankadvisor/runtime_config.py` (if DB connection issue)

### Tests

- `plugins/bank-advisor-private/src/bankadvisor/tests/unit/test_kpi_repository.py` (new)
- `plugins/bank-advisor-private/src/bankadvisor/tests/unit/test_handlers.py` (existing, add cases)

---

## Phase 3: Chart & Artifact Fixes

**Goal**: Fix chart loading errors and persistence issues.

### Tasks

1. **Add artifact payload validation**
   - Define JSON schema for chart artifacts:
     ```json
     {
       "type": "chart",
       "series": [{ "x": Date|string, "y": number }],
       "metadata": { "metric_key": string, "bank": string, ... }
     }
     ```
   - Validate before saving to DB
   - Validate before sending to frontend
   - If invalid: return structured error with request_id

2. **Fix chart error handling**
   - If series is empty: return 200 with `{ data: [], message: "No data for range" }`
   - Don't return error status for empty results
   - Frontend should show "No hay datos" instead of "Error"

3. **Fix chart persistence**
   - Ensure artifacts are saved to MongoDB (not just in-memory)
   - Ensure `artifact_id` is included in message document
   - Test artifact creation/retrieval flow end-to-end

4. **Fix chart rehydration**
   - When loading conversation history: fetch associated artifacts
   - Frontend: request artifacts by ID if not included in message payload
   - Add logging: "Loaded conversation X with Y artifacts"

5. **Handle blank/empty messages gracefully**
   - Don't clear panel state on empty message
   - Ignore empty submissions (or prompt user)

### Files to Modify

- `apps/backend/src/services/bank_analytics_client.py` — artifact validation
- `apps/backend/src/routers/chat/` — artifact storage/retrieval
- `apps/web/components/chat/MessageCard.tsx` (or similar) — rehydration
- `apps/web/components/charts/ChartPanel.tsx` (or similar) — error handling

### Tests

- `tests/e2e/conversation/test_artifact_persistence.py` (new)
- Test: create chart → close conversation → reopen → verify chart restored

---

## Phase 4: UX Fixes (Clarification Rendering)

**Goal**: Render clarification questions as input forms, not buttons.

### Tasks

1. **Define clarification message schema**
   - Backend should distinguish:
     - `clarification_questions`: require user input (text/dropdown/date)
     - `quick_replies`: actionable options (buttons)
   - Example:
     ```json
     {
       "type": "clarification",
       "questions": [
         { "text": "¿De qué banco?", "input_type": "dropdown", "options": ["BBVA", "Santander", ...] },
         { "text": "¿Para qué periodo?", "input_type": "date_range" }
       ]
     }
     ```

2. **Update backend to use new schema**
   - Modify streaming_handler or clarification logic
   - Emit `clarification_questions` instead of generic `actions`

3. **Update frontend renderer**
   - Map `input_type: "dropdown"` → dropdown/autocomplete component
   - Map `input_type: "date_range"` → date picker
   - Keep buttons only for `quick_replies` with concrete values

4. **Add examples/tests**
   - Test: trigger clarification → verify input forms rendered
   - Test: submit dropdown selection → verify query continues

### Files to Modify

- `apps/backend/src/routers/chat/handlers/streaming_handler.py` — clarification emission
- `apps/web/components/chat/ClarificationBlock.tsx` (or create) — rendering logic

### Tests

- `tests/e2e/conversation/test_clarification_ux.py` (new)

---

## Phase 5: Table Grounding & Observability

**Goal**: Prevent hallucinations in tables and improve debugging.

### Tasks

1. **Add source attribution to tables**
   - When generating tables: require document IDs or source citations
   - If no sources: return "No tengo los datos exactos" instead of synthesizing
   - Add validation: reject table generation without sources

2. **Add observability to all responses**
   - Include in logs (and optionally in debug UI):
     - `request_id`: unique per query
     - `metric_key`: which metric(s) were queried
     - `tenant`, `env`: environment context
     - `artifact_id`: for charts
     - `source_docs`: IDs of documents used
   - Make it easy to trace from user report → logs → data

3. **Add unit tests for edge cases**
   - Test: metric with missing value → returns None, not year
   - Test: empty series → "no data" message, not error
   - Test: percentage > 100 → validation error
   - Test: clarification with questions → input forms, not buttons
   - Test: artifact without series → validation error before save

### Files to Modify

- `apps/backend/src/routers/chat/handlers/streaming_handler.py` — logging
- `plugins/bank-advisor-private/src/bankadvisor/handlers/` — source attribution
- `apps/backend/src/services/tool_execution_service.py` — request_id propagation

### Tests

- Add unit tests across all modified files
- Add integration test: end-to-end query with observability

---

## Validation & Testing

After all phases, perform:

1. **Regression testing**
   - Run existing test suites: `make test T=api`, `make test T=web`
   - Run bank-advisor unit tests: `cd plugins/bank-advisor-private && pytest`

2. **Manual validation with screenshots**
   - Replicate each scenario from the 8 screenshots
   - Verify fixes:
     - IMOR/ICAP show correct values (< 100%)
     - System reports correct data range
     - Tables have source attribution
     - Clarifications show as input forms
     - Charts load and persist correctly

3. **Data quality checks**
   - Query Mongo: verify max(date) matches expectations
   - Sample random metrics: verify values are reasonable
   - Check logs for request_id propagation

4. **Document validation results**
   - Update `validate.md` with:
     - Test results (pass/fail for each scenario)
     - Screenshots of fixes (before/after)
     - Confirmation from Carlos/Cris that issues are resolved

---

## Risk & Dependencies

### Risks
- **Environment confusion**: If we don't identify the correct environment, we might fix the wrong instance
- **Schema changes**: If ETL pipeline changed schema, might need broader refactor
- **Multiple root causes**: Some issues might have overlapping causes requiring careful coordination

### Dependencies
- Access to production/demo MongoDB (read-only sufficient for Phase 1)
- Confirmation from Fernando Saavedra on expected data range
- Clarification from Carlos/Cris on which environment they were using

### Mitigation
- Start with Phase 1 (investigation) to reduce uncertainty
- Add comprehensive logging before making changes
- Test in staging/demo before production deployment

---

## Notes

This plan treats each bug category as a separate phase, but some fixes overlap:
- Data layer fixes (Phase 2) resolve multiple issues (IMOR, ICAP, data recency)
- Observability (Phase 5) helps with all future debugging

Estimate: 3-5 days depending on Phase 1 findings and access to production data.
