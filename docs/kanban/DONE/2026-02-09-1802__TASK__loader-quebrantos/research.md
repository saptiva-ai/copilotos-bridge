# Research

## Questions
- What is the full column schema of QUEBRANTOS.csv?
- Does a quebrantos/charge-off table already exist in prod?
- How does this relate to existing CASTIGOS.xlsx data?

## Findings

### File Structure
- **Shape**: 46 rows x 3 columns — very small, one-row-per-institution snapshot
- **Columns**: `Institucion1` (int, CNBV code), `Bancos` (str, name), `Quebrantos CC` (float64, commercial charge-offs)
- **Encoding**: UTF-16 LE, tab-delimited (handled by `scan_csv_smart()`)

### Prod DB Comparison
- **No dedicated table exists** in prod for quebrantos
- Column `quebrantos_comerciales` already exists in `bank_fact_kpis_mensual` (706 rows, 2017-01 to 2025-07)
- That column is populated by the CASTIGOS.xlsx loader, not from QUEBRANTOS.csv

### Assessment: LOW PRIORITY — likely redundant
- QUEBRANTOS.csv contains only 46 rows (one per institution) with a single aggregated metric
- `bank_fact_kpis_mensual.quebrantos_comerciales` already has this data with monthly time series (706 rows over 8.5 years)
- The CSV appears to be a **point-in-time snapshot** of the same metric that's already tracked monthly
### Redundancy Verified (2026-02-09)
- Compared all 46 values against `bank_fact_kpis_mensual.quebrantos_comerciales`
- **Exact match with January 2022 data**:
  - BANAMEX(CITIBANAMEX): CSV=1656.649021 vs Prod=1656.649021
  - BBVA: CSV=3374.255931 vs Prod=3374.25593142
  - SANTANDER: CSV=5121.295069 vs Prod=5121.29506933
  - BANORTE: CSV=1536.831682 vs Prod=1536.8316820700002
  - INVEX: CSV=120.247180 (no comparable row in prod — Invex only appears from later dates)
- **Conclusion**: QUEBRANTOS.csv is a static snapshot of Jan 2022 commercial write-offs. This data already exists in prod with 8.5 years of monthly history.
- **Decision**: CLOSED — no loader needed

## References
- Parent task research: `docs/kanban/DOING/2026-02-09-1430__TASK__secure-prod-db-comparison-and-data-drop-policy/research.md`
- Source file: `data/raw/incoming/drive-download-20260209T193355Z-1-001/QUEBRANTOS.csv`
- UTF-16 helper: `plugins/bank-advisor-private/etl/core/loaders/smart_csv.py:scan_csv_smart()`
