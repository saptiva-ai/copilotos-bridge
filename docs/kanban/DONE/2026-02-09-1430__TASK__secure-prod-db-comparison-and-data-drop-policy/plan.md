# Plan

## Objective
- Define and execute a safe analysis workflow for production parity and recurring incoming data drops.

## Scope
### In
- Credential-safe prod read-only checks.
- Incoming-to-canonical ingestion policy.
- Mapping and drift classification for current drop.

### Out
- Production writes.
- Schema redesign.
- Non-ETL product features.

## Phases
### Phase 1
- [ ] Inventory current ETL canonical inputs and destination tables.
- [ ] Inventory incoming files and classify by compatibility.

#### Phase 1 Files
- `plugins/bank-advisor-private/etl/core/loaders_unified.py`
- `plugins/bank-advisor-private/etl/core/transforms.py`
- `plugins/bank-advisor-private/etl/core/db_writer_3nf.py`
- `plugins/bank-advisor-private/data/raw/incoming/drive-download-20260209T193355Z-1-001/*`

### Phase 2
- [ ] Define secure secret-handling workflow for prod comparisons.
- [ ] Define read-only SQL baseline and parity checklist.

#### Phase 2 Files
- `docs/kanban/BACKLOG/2026-02-09-1430__TASK__secure-prod-db-comparison-and-data-drop-policy/research.md`
- `docs/kanban/BACKLOG/2026-02-09-1430__TASK__secure-prod-db-comparison-and-data-drop-policy/validate.md`

### Phase 3
- [ ] Define ingestion policy for recurring drops with promotion gates.
- [ ] Produce follow-up implementation tickets for required adapters.

#### Phase 3 Files
- `docs/kanban/BACKLOG/2026-02-09-1430__TASK__secure-prod-db-comparison-and-data-drop-policy/card.md`
- `docs/kanban/BACKLOG/2026-02-09-1430__TASK__secure-prod-db-comparison-and-data-drop-policy/research.md`

## Validation Commands
- `cd plugins/bank-advisor-private && .venv/bin/python -m etl.core.etl_unified --data-root data/raw/incoming/drive-download-20260209T193355Z-1-001 --dry-run`
- `psql "service=bankadvisor_prod" -w -c "SELECT MAX(fecha), COUNT(*) FROM bank_fact_kpis_mensual;"`
- `psql "service=bankadvisor_prod" -w -c "SELECT MAX(to_date(periodo,'YYYYMM')), COUNT(*) FROM bank_src_reporte_r04a;"`

## Success Criteria
- No secret values are committed, printed, or copied into docs.
- Incoming delivery can be classified into direct-load vs adapter-required.
- Prod baseline checklist is reproducible and read-only.
