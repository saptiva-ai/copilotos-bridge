---
id: "TASK-2026-01-14-2130__tasa-mn-column-missing"
title: "Fix tasa_mn data population for all banks in monthly_kpis"
status: "DONE"
phase: "Validated"
scope_in:
  - "Fix ETL to merge corporate rates for ALL banks (not just legacy CNBV)"
  - "Run ETL to repopulate monthly_kpis with full tasa_mn data"
scope_out:
  - "Database schema changes (columns already exist)"
  - "Changes to application code (already supports these columns)"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 2
validation_commands:
  - "SELECT banco_norm, COUNT(*), COUNT(tasa_mn), COUNT(tasa_me) FROM monthly_kpis GROUP BY banco_norm ORDER BY banco_norm;"
pr_files:
  - "plugins/bank-advisor-private/etl/core/transforms.py"
test_status: "PASSED"
priority: "high"
related_test: "Test 33 - Happy Path Suite"
---

# Summary

- **Objective**: Fix ETL pipeline to populate `tasa_mn` and `tasa_me` for ALL banks, not just legacy CNBV banks.
- **Impact**: Test 33 ("¿Cuál es la tasa de crédito corporativo en moneda nacional?") returns empty chart for most banks.
- **Target Environment**: GCP Production PostgreSQL

# Problem Description

## Updated Investigation (2026-01-19)

**Database columns DO exist** but only 7 of 19 banks have data:

```sql
-- Actual data distribution (from production inspection)
banco_norm    | total_rows | rows_with_tasa_mn | rows_with_tasa_me
--------------+------------+-------------------+-------------------
AFIRME        |        299 |                 0 |                 0
BAJIO         |        299 |                 0 |                 0
BANORTE       |        299 |                43 |                43
BBVA          |        299 |                43 |                43
CITIBANAMEX   |        299 |                43 |                43
HSBC          |        299 |                43 |                43
INVEX         |        299 |                43 |                43
SANTANDER     |        299 |                43 |                43
SISTEMA       |        299 |                43 |                43
...
```

## Root Cause

The ETL pipeline (`transforms.py`) had a bug:

1. **Corporate rates** are loaded from `CorporateLoan_CNBVDB.csv` with institution codes
2. **Legacy CNBV pipeline** (line 1136) calls `merge_corporate_rates()` which joins by `institucion` code
3. **Analisis General merge** (line 1172) adds banks like AFIRME, BAJIO that ONLY come from AG
4. **AG doesn't have tasa_mn** - it only has metrics from CNBV Analisis General source
5. **Banks from AG never get corporate rates** because the merge happens BEFORE they're added

**Only these banks had tasa_mn (processed by legacy CNBV):**
- INVEX, SISTEMA, BBVA, SANTANDER, BANORTE, HSBC, CITIBANAMEX

**Banks missing tasa_mn (only from Analisis General):**
- AFIRME, BAJIO, AZTECA, BANREGIO, INBURSA, MIFEL, MONEX, SCOTIABANK, etc.

## Test Failure

- **Test 33**: "¿Cuál es la tasa de crédito corporativo en moneda nacional?"
- **Expected**: Chart with corporate loan rate data for all banks
- **Actual**: "Chart has no data points" (for banks like AFIRME)
- **Root Cause**: `tasa_mn` is NULL for banks that only come from Analisis General

# Solution Implemented

## Code Changes

**File: `plugins/bank-advisor-private/etl/core/transforms.py`**

Added new function `merge_corporate_rates_final()` (lines 647-765):
- Maps `institucion` code to `banco_norm` using `BANCO_NORM_TO_INSTITUCION`
- Merges corporate rates by `banco_norm` + `fecha` (not by `institucion` code)
- Coalesces with existing values (preserves legacy-merged values)
- Called AFTER Analisis General merge (line 1434)

```python
# New mapping from banco_norm to institution code
BANCO_NORM_TO_INSTITUCION = {
    "BBVA": "040012",
    "SANTANDER": "040014",
    "BANORTE": "040072",
    "HSBC": "040021",
    "CITIBANAMEX": "040002",
    "INVEX": "040131",
    "AFIRME": "040062",
    "BAJIO": "040030",
    # ... 19 banks total
}

def merge_corporate_rates_final(monthly_kpis, corp_rates_df):
    """
    Merge corporate rates into ALL banks by banco_norm.
    Called AFTER Analisis General merge to ensure AG-only banks get rates.
    """
    # Creates reverse mapping: institucion -> banco_norm
    # Joins by banco_norm + fecha (month)
    # Coalesces with existing tasa_mn/tasa_me
```

## ETL Pipeline Order

```
Before Fix:
1. Legacy CNBV → merge_corporate_rates (by institucion) → only 7 banks get rates
2. Analisis General merge → adds AFIRME, BAJIO, etc. WITHOUT rates
3. Result: 7 banks with rates, 12+ without

After Fix:
1. Legacy CNBV → merge_corporate_rates (by institucion) → 7 banks get rates
2. Analisis General merge → adds AFIRME, BAJIO, etc. without rates
3. merge_corporate_rates_final (by banco_norm) → ALL 19 banks get rates
4. Result: ALL mapped banks have rates
```

# Required Actions

1. **[DONE] Code Fix** - Added `merge_corporate_rates_final()` function
2. **[DONE] Re-run ETL** - Executed unified ETL to repopulate data
3. **[DONE] Verify** - Confirmed all 19 banks have data in GCP Production

# References

- ETL transforms: `plugins/bank-advisor-private/etl/core/transforms.py`
- Corporate rates loader: `plugins/bank-advisor-private/etl/core/loaders_unified.py:493-618`
- Bank mapping: `BANCO_NORM_TO_INSTITUCION` in transforms.py
- Previous investigation: `research.md`

# Updates

- 2026-01-14 21:30 - Created. Issue discovered during Happy Path Test Suite analysis.
- 2026-01-19 - Root cause identified: corporate rates only merged for legacy banks, not AG banks.
- 2026-01-19 - Fix implemented: added `merge_corporate_rates_final()` function in transforms.py.
- 2026-01-20 - ETL executed in GCP Production. All 19 banks now have tasa_mn data:
  - AFIRME: 110, AUTOFIN: 97, AZTECA: 110, BAJIO: 89, BANCO BASE: 110
  - BANORTE: 50, BANREGIO: 105, BBVA: 48, BMONEX: 110, CITIBANAMEX: 50
  - HSBC: 50, INBURSA: 110, INTERACCIONES: 25, INVEX: 50, MIFEL: 110
  - MONEX: 109, SANTANDER: 50, SCOTIABANK: 109, SISTEMA: 28
- 2026-01-20 - **TASK CLOSED** - Verified and moved to DONE.
