# Plan

## Objective
- Load `QUEBRANTOS.csv` into a new `bank_src_quebrantos` table with normalized institution keys.

## Scope
### In
- Discover full schema and datatypes
- Loader + migration
- Unit tests for encoding/delimiter + type normalization

### Out
- Production writes
- UI integration

## Phases
### Phase 1 (Research)
- [ ] Confirm columns and meaning (Bajaware spec)
- [ ] Confirm grain: institution x period or institution snapshot

### Phase 2 (Implement)
- [ ] Loader in `plugins/bank-advisor-private/etl/core/loaders/` using `scan_csv_smart()`
- [ ] Migration for `bank_src_quebrantos`
- [ ] Unit tests: parse, normalize CNBV codes, numeric casting

## Validation Commands
- `cd plugins/bank-advisor-private && .venv/bin/pytest -q -k quebrantos`

## Success Criteria
- Loader works on UTF-16 + tab-delimited inputs
- Institution identifiers can be joined to `bank_dim_institucion`

