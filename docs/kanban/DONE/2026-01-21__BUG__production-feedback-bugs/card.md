---
id: "BUG-2026-01-21__production-feedback-bugs"
title: "Production Feedback Bugs - Chart & Data Consistency"
status: "DONE"
phase: "Complete"
priority: "HIGH"
source: "Production Feedback Analysis"
reported_by: "User 7f5aa3b9-8f98-459e-abc2-0148b23486f9"
scope_in:
  - "Fix chart not updating between queries"
  - "Fix LLM data hallucination for regional breakdowns"
  - "Ensure data consistency across conversation turns"
scope_out:
  - "New features"
  - "Performance optimizations"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "make test T=api TEST_ARGS='-k chart'"
  - "make test T=web"
pr_files: []
test_status: "passed"
fix_commits:
  - "d1e6636c"  # BUG-1: Chart comparison fix (v1.4.18)
  - "da5940a7"  # BUG-2/3: Hallucination prevention
---

# Summary
- **Objective**: Fix 3 critical bugs reported via production feedback that degrade user trust
- **Constraints**: Must maintain backward compatibility; no breaking changes to API
- **Impact**: 75% of all feedback is negative (3/4), all from same user session

# Bug Inventory

## BUG-1: Chart Not Updating (P2 - High)

| Field | Value |
|-------|-------|
| **Feedback ID** | `ae1200ad-7477-4512-80e2-7c2d31d344b7` |
| **Date** | 2026-01-21 20:22:51 UTC |
| **Latency** | 32ms |
| **Rating** | 👎 DOWN |

### User Comment
> "el grafico no se actualiza, se queda pendiente del anterior"

### Query
```
CARTERA_COMERCIAL de INVEX de 2025 puedes mostrar un comparativo por region?
```

### Technical Analysis
- The chart component in the frontend does not re-render when new data arrives
- Previous chart data persists visually even though new data was returned
- Likely a React state/key issue in the chart component

### Affected Components
- `apps/web/src/components/chat/ChartRenderer.tsx` (probable)
- `apps/web/src/components/chat/MessageContent.tsx` (probable)

---

## BUG-2: Data Hallucination - Regional Breakdown (P1 - Critical)

| Field | Value |
|-------|-------|
| **Feedback ID** | `d9ebc2af-6612-48a8-a095-d50c307c6c03` |
| **Date** | 2026-01-21 20:24:48 UTC |
| **Latency** | 86ms |
| **Rating** | 👎 DOWN |

### User Comment
> "el saldo se modifico al presentarlo distribuido por entidad federativa"

### Query
```
CARTERA_COMERCIAL de INVEX de 2025 puedes concentrar en una tabla el comparativo previo por region?
```

### Technical Analysis
- User asked for regional breakdown
- LLM generated **fictional regional data** that doesn't exist in the database:
  - Centro: 7,745,103,317 MDP (47.2%)
  - Occidente: 4,471,864,208 MDP (27.3%)
  - Norte: 3,249,782,454 MDP (19.8%)
  - Sur: 1,935,836,993 MDP (11.8%)
  - Sureste: 1,243,876,543 MDP (7.6%)
  - **Total hallucinated: 18,646,463,515 MDP**
- Actual data in DB: **16,402,586,992 MDP** (national only, no regional breakdown)
- The SQL query only returns national data, but LLM fabricated regional distribution

### Root Cause
- bank-advisor returns only national-level data
- LLM hallucinates regional breakdown when asked
- No validation that response data matches actual query results

### Affected Components
- `plugins/bank-advisor-private/src/` - NLP pipeline
- `apps/backend/src/services/streaming/` - Response generation

---

## BUG-3: Data Inconsistency Across Turns (P1 - Critical)

| Field | Value |
|-------|-------|
| **Feedback ID** | `a4e5d6a6-ea03-4735-ab41-fef3e558f8ad` |
| **Date** | 2026-01-21 20:27:36 UTC |
| **Latency** | 24ms |
| **Rating** | 👎 DOWN |

### User Comment
> "El dato que presenta ahora difiere del que primero presento y no es capaz de explicar porque se origina la diferencia"

### Query
```
cual es el saldo de la cartera comercial de invex a octubre de 2025?
```

### Technical Analysis
- First response: **16,402,586,992 MDP** (correct, from DB)
- Later response after regional question: **18,646,463,515 MDP** (hallucinated sum)
- LLM repeated the hallucinated figure instead of the real one
- User noticed the inconsistency and asked for clarification
- LLM could not explain the discrepancy

### Data Comparison
| Source | Value | Status |
|--------|-------|--------|
| Database (real) | 16,402,586,992 MDP | ✅ Correct |
| LLM hallucination | 18,646,463,515 MDP | ❌ Fabricated |
| Difference | +2,243,876,523 MDP | 13.7% inflation |

---

# Proposed Fixes

## Fix 1: Chart Re-render (BUG-1)
- Add unique `key` prop to chart component based on message ID
- Force re-mount when data changes
- Clear previous chart state before rendering new data

## Fix 2: Hallucination Guard (BUG-2 & BUG-3)
- Validate LLM response against actual SQL results
- If LLM claims data that doesn't exist in response, flag it
- Add system prompt: "Only use data from the provided SQL results. Do not invent or estimate values."
- When regional data is requested but doesn't exist, respond honestly: "Regional breakdown is not available in the database"

## Fix 3: Data Consistency Check
- Track numerical values mentioned in conversation
- Alert if LLM contradicts previously stated figures
- Add metadata validation between turns

---

# Acceptance Criteria

- [x] Chart updates correctly when new query is made (fixed: `d1e6636c`)
- [x] LLM does not fabricate regional/granular data that doesn't exist (fixed: `da5940a7`)
- [x] Same query returns consistent values across conversation turns (fixed: `da5940a7`)
- [x] User can trust numerical data presented by the system
- [ ] Add E2E test for multi-turn data consistency (optional enhancement)

# Updates
- 2026-01-21 18:45 - Created from production feedback analysis (report: `reports/BankAdvisor_Metrics_Report_2026-01-21.pdf`)
- 2026-01-26 - BUG-1 fixed in v1.4.18 (`d1e6636c`): Improved chart comparison logic
- 2026-01-27 - BUG-2/3 fixed (`da5940a7`): Added grounding instructions to prevent hallucination
- 2026-01-29 - Research complete. All bugs already fixed. Moved to DONE.
