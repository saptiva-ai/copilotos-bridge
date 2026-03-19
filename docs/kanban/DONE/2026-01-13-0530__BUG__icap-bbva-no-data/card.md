---
id: "BUG-2026-01-13-0530__icap-bbva-no-data"
title: "ICAP de BBVA Returns No Data Traces"
status: "DONE"
phase: "Validate"
priority: "LOW"
scope_in:
  - "Investigate why ICAP query for BBVA returns empty chart"
  - "Verify ICAP data availability for BBVA in DB"
  - "Check SQL generation for this specific query"
scope_out:
  - "Other bank/metric combinations"
  - "General ICAP issues"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "python tests/e2e/conversation/test_hipotecario_bugs.py"
pr_files: []
test_status: "1 scenario failing (HIP-022)"
---

# Summary
- Objective: Fix ICAP query for BBVA returning empty chart
- Constraints: Must not affect other ICAP queries

# Bug Description
Query "ICAP de BBVA" returns a chart response but with no data traces.

## Affected Scenario
| Test | Query | Expected | Actual |
|------|-------|----------|--------|
| HIP-022 | "ICAP de BBVA" | Chart with ICAP data | Chart with 0 data traces |

## Investigation Areas
1. Check if BBVA has ICAP data in monthly_kpis
2. Review SQL generated for this query
3. Verify bank normalization for "BBVA"

# Updates
- 2026-01-13 05:30 - Created from E2E test analysis.
- 2026-01-26 - **RESOLVED** via database fix:
  - Root cause: `bank_dim_institucion.nombre_corto` was "BBVA México" instead of "BBVA"
  - Fix: `UPDATE bank_dim_institucion SET nombre_corto = 'BBVA' WHERE institucion_id = 2`
  - Refreshed MVs `bank_mv_vivienda_por_perfil` and `bank_mv_vivienda_por_producto`
  - BBVA data now accessible (238 records ICAP, 299 records Cartera Vivienda)
