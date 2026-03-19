# Plan

## Objective
- Ingest `Catera Analitica Benchmark v2.xlsx` into a queryable `bank_src_*` table.

## Scope
### In
- Resolve formula-driven date columns
- Unpivot wide-format monthly columns to long format
- Join/enrich with Sheet2 concept catalog
- Loader + migration + unit tests

### Out
- Production writes (until validated under parent task gates)
- UI changes

## Phases
### Phase 1 (Research)
- [ ] Confirm whether cached values exist (`openpyxl(data_only=True)`)
- [ ] If not, choose strategy (pre-calc export, xlcalculator, or alternative source)

### Phase 2 (Implement)
- [ ] Loader in `plugins/bank-advisor-private/etl/core/loaders/`
- [ ] Migration for target `bank_src_*` table
- [ ] Unit tests for: date header extraction, unpivot row counts, concept join

### Phase 3 (Validate)
- [ ] Dry-run loader on latest incoming file
- [ ] Validate period coverage vs `bank_src_reporte_r04a` (spot checks)

## Validation Commands
- `cd plugins/bank-advisor-private && .venv/bin/pytest -q -k benchmark_analitica`

## Success Criteria
- Deterministic parsing of month columns into `YYYYMM`
- No silent formula strings in date columns
- Row counts stable and explainable

