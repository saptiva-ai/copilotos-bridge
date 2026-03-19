# Research: ISSUE-003 User-Reported Bugs

> Investigation completed: 2026-01-08
> Agent: Claude Code + Explore subagents

---

## Executive Summary

This research investigates 13 bugs reported by Carlos Lara (Head of Product). The findings are organized by priority (P0 > P1 > P2) with root cause analysis and fix recommendations.

---

## P0 Critical Findings

### BUG-12: SQL Injection (Prompt Injection)

**Status: ALREADY FIXED**

The system has **comprehensive SQL injection protection** implemented across 3 security layers:

| Layer | Implementation | File |
|-------|----------------|------|
| Keyword Blacklist | 50+ forbidden keywords (INSERT, UPDATE, DELETE, DROP, etc.) | `sql_validator.py:50-71` |
| Table Whitelist | Only 8 safe tables allowed | `sql_validator.py:78-87` |
| Pattern Detection | 6 injection patterns (UNION, stacked queries, boolean injection) | `sql_validator.py:94-101` |
| Query Budget | Max 30s timeout, 5000 rows, 2 JOINs | `specs.py:301-346` |
| Audit Trail | SQL fingerprinting, schema-only logging | `audit_trail_service.py` |

**Key Files:**
- `plugins/bank-advisor-private/src/bankadvisor/services/sql_validator.py` (426 lines)
- `plugins/bank-advisor-private/src/bankadvisor/services/sql_execution_service.py` (462 lines)
- `plugins/bank-advisor-private/src/bankadvisor/services/audit_trail_service.py` (324 lines)

**Test Coverage:** 57 tests (45 unit, 12 integration)

**Recommendation:** Add adversarial prompt tests to E2E suite to prevent regressions.

---

### BUG-13: Guardrails / Coherence (User Can Negotiate Past Refusals)

**Status: NEEDS INVESTIGATION**

**Hypothesis:** LLM prioritizes helpfulness over grounding. When users insist, the model "caves" and generates fictional responses.

**Attack Pattern:**
1. User asks for unavailable data
2. LLM correctly refuses
3. User insists "but it does exist"
4. LLM fabricates response to satisfy user

**Recommended Fix:**
1. Add truth-gating layer before response render
2. Validate all numeric claims against `tool_result`
3. Add system instruction: "Never comply with requests to mutate data; never claim chart exists unless chart_id returned"

**Files to Modify:**
- `apps/backend/src/services/llm_orchestrator.py` (add post-tool validation)
- Bank advisor system prompt (add grounding instructions)

---

### BUG-09: Hallucination / Mismatch (Text vs Chart)

**Status: NEEDS INVESTIGATION**

**Root Cause:** LLM generates text assuming chart exists before confirming `chart_created=true`.

**Evidence:** "Me habla de una gráfica que no muestra"

**Recommended Fix:**
1. LLM only references chart if `chart_url` in tool response
2. Add `chart_lifecycle` events: `Generating... → Ready → Error`
3. On chart error, LLM should say: "No pude generar la gráfica por X. Aquí están los datos en tabla."

---

### BUG-02: Chart Doesn't Open on First Click (Chrome Mac)

**Status: ROOT CAUSE IDENTIFIED**

**Root Cause:** `handleOpenInCanvas` not memoized with `useCallback`.

**File:** `apps/web/src/components/chat/BankChartPreview.tsx:47-54`

**Current Code:**
```tsx
const handleOpenInCanvas = () => {
  openBankChart(data, artifactId, messageId, false);
};
```

**Fix:**
```tsx
const handleOpenInCanvas = useCallback(() => {
  openBankChart(data, artifactId, messageId, false);
}, [data, artifactId, messageId, openBankChart]);
```

---

### BUG-03: Chart Download is Blank

**Status: ROOT CAUSE IDENTIFIED**

**Root Cause 1:** `chartId` generated with `React.useId()` but NOT assigned to Plot element's DOM ID.

**Root Cause 2:** `ExportTools.tsx:86` calls `document.getElementById(chartId)` but Plot container has no `id` attribute.

**Files:**
- `apps/web/src/components/chat/artifacts/BankChartViewer.tsx:85, 233-239`
- `apps/web/src/components/chat/artifacts/ExportTools.tsx:81-101`

**Fix:** Add `id={chartId}` to the div wrapper around Plot component.

---

## P1 High Priority Findings

### BUG-08: Old Chart Persists Between Conversations

**Status: ROOT CAUSE IDENTIFIED**

**Root Cause:** `clearChartHistory()` not called during conversation switch; only `reset()` called.

**Files:**
- `apps/web/src/lib/stores/canvas-store.ts:110-118` (`reset()` doesn't clear history)
- `apps/web/src/app/chat/_components/ChatView.tsx:165` (calls `resetCanvas()`)

**Fix:** Call `clearChartHistory()` in addition to `reset()` on conversation change.

---

### BUG-01: Router Always Defaults to ICAP

**Status: NEEDS INVESTIGATION**

**Hypothesis:** Router has strong prior for ICAP metric. Query classification doesn't distinguish "overview" intent.

**Recommended Fix:**
1. Add intent classifier: `{overview | single_kpi | compare | explain_method}`
2. If `overview`, return menu of KPIs
3. Adjust ranking: if query contains "general", don't select ICAP by default

**Files to Investigate:**
- `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py`
- Bank advisor prompts

---

### BUG-07: Hardcoded Bank Reference (INVEX)

**Status: NEEDS INVESTIGATION**

**Symptom:** "ICAP para INVEX, Sistema" appears when discussing Santander.

**Hypothesis:** Template or system prompt has `default_bank = INVEX` hardcoded.

**Recommended Fix:**
1. Search for hardcoded "INVEX" in prompts/templates
2. Make `default_bank` configurable via conversation state
3. Render context header from actual payload: `kpi`, `bancos`, `rango`, `fecha_corte`

---

### BUG-10: Data Inconsistency (Sistema < Component)

**Status: NEEDS DATA AUDIT**

**Symptom:** "Sistema" aggregate value is less than individual bank (INVEX).

**Hypotheses:**
1. "Sistema" is average, not sum
2. ETL has incomplete bank filter
3. Different date ranges between queries

**Recommended Fix:**
1. Define "Sistema" semantics explicitly in UI
2. Add validation: if sum, assert `system >= max(component)`
3. Add disambiguation for "capitalización" (ICAP vs market cap)

---

## P2 Nice-to-Have Findings

### BUG-04: Decimal Formatting Inconsistent

**File:** Frontend number formatting
**Fix:** Use `Intl.NumberFormat` consistently with KPI-specific rules

### BUG-05: Zoom Reset UX

**Fix:** Add persistent "Reset zoom" button to chart modal

### BUG-06: SQL Query Duplicado (Chat + Canvas)

**Síntoma:** El SQL query aparece dos veces:
1. En la respuesta del chat (del LLM)
2. En el panel canvas (BankChartCanvasView)

**Solución:** Quitar el SQL del chat response. Solo mostrar en canvas panel.

**Archivos a modificar:**
- `plugins/bank-advisor-private/src/bankadvisor/prompts/` - Remover instrucción de mostrar SQL
- O filtrar SQL del response en frontend antes de render

### BUG-11: Markdown Rendering Broken

**Root Cause:** Double render or sanitizer stripping spaces
**Fix:** Define single output format (Markdown strict OR plain text)

---

## Architecture Observations

### NL2SQL Pipeline

```
User Query → QuerySpec Parser → SQL Generator → SQL Validator → Executor → Audit
                                       ↓
                              (Template 80% / LLM 20%)
```

### Chart Rendering Flow

```
Backend Response → artifact.bank_chart_data → BankChartMessage → Plotly
                         ↓
                   BankChartPreview → openBankChart() → Canvas Store → BankChartCanvasView
```

### State Management

- Chat state: Zustand (`chatStore.ts`)
- Canvas state: Zustand (`canvas-store.ts`) + CanvasContext
- Auth state: Zustand (`auth-store.ts`)

---

## Test Files Identified

| Area | Test File |
|------|-----------|
| SQL Validator | `plugins/bank-advisor-private/src/bankadvisor/tests/unit/test_sql_validator.py` |
| SQL Execution | `plugins/bank-advisor-private/tests/unit/services/test_sql_execution_service.py` |
| SQL Guardrails | `plugins/bank-advisor-private/tests/integration/test_sql_guardrails_integration.py` |
| Security E2E | `tests/e2e/security/test_security_prompt_injection.py` |

---

## Next Steps

1. Create `plan.md` with phased implementation
2. Create validation script for all bugs
3. Prioritize fixes based on P0 > P1 > P2
