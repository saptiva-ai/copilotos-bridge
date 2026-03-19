# Plan

## Objective
- Load `TASAS DATOS.csv` into a new `bank_src_tasas` table with normalized institutions and periods.

## Scope
### In
- Discover full schema and datatypes
- Loader + migration
- Unit tests for encoding/delimiter + date parsing

### Out
- Production writes
- UI integration

## Phases
### Phase 1 (Research)
- [ ] Confirm schema and grain (per institution per month?)
- [ ] Decide mapping to existing metrics (corporate rates vs system rates)

### Phase 2 (Implement)
- [ ] Loader in `plugins/bank-advisor-private/etl/core/loaders/` using `scan_csv_smart()`
- [ ] Migration for `bank_src_tasas`
- [ ] Unit tests for parsing, normalization, typing

## Validation Commands
- `cd plugins/bank-advisor-private && .venv/bin/pytest -q -k tasas`

## Success Criteria
- Correct date parsing, no month/day swaps
- Institutions joinable to `bank_dim_institucion`

