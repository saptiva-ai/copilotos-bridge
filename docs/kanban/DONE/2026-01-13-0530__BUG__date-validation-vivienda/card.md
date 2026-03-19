---
id: "BUG-2026-01-13-0530__date-validation-vivienda"
title: "Date Validation Failures in Cartera Vivienda Queries"
status: "DONE"
phase: "Validate"
priority: "MEDIUM"
scope_in:
  - "Investigate why date validation fails for vivienda queries"
  - "Verify data availability in monthly_kpis for cartera_vivienda"
  - "Fix time_range extraction or test assertions"
scope_out:
  - "Other metric date issues"
  - "Bank accumulation issues"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "python tests/e2e/conversation/test_hipotecario_bugs.py"
pr_files: []
test_status: "2 scenarios failing (HIP-005, HIP-016)"
---

# Summary
- Objective: Fix date validation failures in cartera vivienda multi-bank queries
- Constraints: Ensure tests reflect actual data availability

# Bug Description
Date validation fails because the dates field contains incorrect values (bank names instead of dates, or dates outside expected range).

## Affected Scenarios
| Test | Query | Issue |
|------|-------|-------|
| HIP-005 | "cartera vivienda de INVEX y BBVA" | Dates contain ['INVEX'] instead of date values |
| HIP-016 | "cartera hipotecaria de INVEX, BBVA y Santander" | Dates don't contain years 2019-2025 |

## Investigation Areas
1. Check `time_range` extraction in chart responses
2. Verify data availability for cartera_vivienda in DB
3. Review test assertions for expected date ranges

# Updates
- 2026-01-13 05:30 - Created from E2E test analysis.
- 2026-01-26 - **RESOLVED** via database fix:
  - Root cause: VIEW `bank_fact_cartera_vivienda_mensual` used UPPER(institucion::text) instead of FK
  - Fix 1: Updated `bank_dim_institucion.nombre_corto` from "BBVA México" to "BBVA"
  - Fix 2: Recreated VIEW with proper JOIN to `bank_dim_institucion`
  - Fix 3: Refreshed MVs `bank_mv_vivienda_por_perfil` and `bank_mv_vivienda_por_producto`
  - Data now consistent across all bank queries
