---
id: "BUG-2026-02-17__quebrantos-cc-data-mismatch"
title: "Quebrantos CC data in bank_fact_kpis_mensual doesn't match Tableau"
status: "DONE"
phase: "Validate"
scope_in:
  - "Investigate scale mismatch between DB and Tableau values"
  - "Identify correct source data in incoming/ and Tableau TWB formulas"
  - "Fix/backfill quebrantos_comerciales for 10 target banks"
  - "Verify exclude_zeros and skip_currency_scale behavior"
scope_out:
  - "Frontend changes (pipeline already registered)"
  - "New loaders for unrelated metrics"
artifacts:
  card: card.md
plan_phase: 4
---

# Problem

E2E test `test_quebrantos_cc_snapshot_bar_chart.py` reveals that
`bank_fact_kpis_mensual.quebrantos_comerciales` does NOT match Tableau
"Quebrantos CC" view.

## Root Cause (RESOLVED)

**Tableau screenshot is from an older version of CASTIGOS.xlsx** — irreconcilable
with current data. The TWB was saved with 1363 rows, but the current XLSX has
2142 rows (updated with newer periods and revised data).

### Investigation Findings

1. **Tableau formula confirmed**: `[LIB_CASTIGOS_COMERC] + [QUITAS_COMER]`
   (TWB line 1379, worksheet "Quebrantos")
2. **TWB date filter**: Jan-Jun 2024 with `SUM()` aggregation — NOT a single
   month as the screenshot implied
3. **Data version mismatch**: No date range from the current XLSX matches
   the screenshot values at any scale (tested 10+ combinations)
4. **Backfill script already existed**: `scripts/data/backfill_castigos.py`
   correctly reads from CASTIGOS.xlsx "CASTIGOS" sheet with formula
   `(LIB_CASTIGOS_COMERC + QUITAS_COMER) * 1,000,000` (MDP to pesos)

### Institution Code Corrections

| Bank | Correct Code | Wrong Assumption |
|------|-------------|-----------------|
| BANSI | 040060 | 040136 (=INTERCAM BANCO) |
| SABADELL | 040156 | 040149 (=FORJADORES) |

## Resolution

1. **Ran `backfill_castigos.py`** against production DB on 2026-02-17
   - 4549 rows updated (quebrantos_comerciales + castigos_acum_comercial + imora)
   - All 10 target banks now have 47 periods of data (202201-202511)
   - Also populated `castigos_acum_comercial` and `imora` columns

2. **Post-backfill DB state** (202501):

   | Bank | Quebrantos (pesos) | MDP |
   |------|-------------------|-----|
   | AFIRME | 2,560,781 | 2.56 |
   | MIFEL | 12,339,663 | 12.34 |
   | MONEX | 1,707,845 | 1.71 |
   | VE POR MAS | 3,546,021 | 3.55 |
   | INVEX | 0 | 0.00 |
   | BANCO BASE | 0 | 0.00 |
   | BANCREA | 0 | 0.00 |
   | BANSI | 0 | 0.00 |
   | MULTIVA | 0 | 0.00 |
   | SABADELL | 0 | 0.00 |

## Pipeline Status (DONE)

`hip_quebrantos_cc` registered in 5 files (committed in `0ede5d9f`).

## Test

```bash
python3.11 tests/e2e/charts/test_quebrantos_cc_snapshot_bar_chart.py
python3.11 tests/e2e/charts/test_quebrantos_cc_yearly_bar_chart.py
```

Previous: 7/12 PASS (data missing)
After backfill: pending re-run

## References

- Backfill script: `scripts/data/backfill_castigos.py`
- CASTIGOS.xlsx: 2142 rows, "CASTIGOS" sheet, MDP values
- Tableau TWB: `Invex_Tablero_V3.twb`, worksheets "Quebrantos" and "Quebrantos (4)"
- Prod DB column: `bank_fact_kpis_mensual.quebrantos_comerciales`
