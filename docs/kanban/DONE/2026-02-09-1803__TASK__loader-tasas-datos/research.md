# Research

## Questions
- What is the full column schema of TASAS DATOS.csv?
- Does a tasas/interest-rate table already exist in prod?
- How does this relate to existing TDA.xlsx data?

## Findings

### File Structure
- **Shape**: 24 rows x 3 columns — very small, one-row-per-(institution, currency) snapshot
- **Columns**: `Descripcion` (str, bank name), `Moneda` (str: "Moneda nacional" / "Moneda extranjera"), `Prom. Tasa Efectiva Promedio` (float64)
- **Encoding**: UTF-16 LE, tab-delimited (handled by `scan_csv_smart()`)
- **Institutions**: 12 banks x 2 currencies = 24 rows

### Prod DB Comparison
- **No dedicated table exists** in prod for tasas
- Columns `tasa_mn` (1,520 rows), `tasa_me` (1,339), `tasa_sistema` (220), `tasa_invex_consumo` (220) already exist in `bank_fact_kpis_mensual`
- Those columns are populated by TDA.xlsx and CorporateLoan_CNBVDB.csv loaders

### Assessment: LOW PRIORITY — likely redundant
- TASAS DATOS.csv contains only 24 rows (12 banks x 2 currencies) with a single "Tasa Efectiva Promedio" value
- `bank_fact_kpis_mensual.tasa_mn` / `tasa_me` already has this data with monthly time series (1,520+ rows over 9+ years)
- The CSV appears to be a **point-in-time average** of the same rates already tracked monthly
### Redundancy Verified (2026-02-09)
- Compared CSV values against `bank_fact_kpis_mensual.tasa_mn` and `tasa_me`
- **Values do NOT match** — different metric:
  - INVEX MN: CSV=14.56% vs Prod=18.38% (Jul 2025)
  - AFIRME MN: CSV=14.09% vs Prod=16.37% (Jul 2025)
  - AFIRME ME: CSV=6.25% vs Prod=8.34% (Jul 2025)
- The CSV measures "Prom. Tasa Efectiva Promedio" (weighted effective rate) which is a **different calculation** from the simple rate averages in kpis_mensual
- However: only 24 rows (12 banks × 2 currencies), **no date column**, no time series
- **Conclusion**: Not directly redundant, but too small (24 rows, no temporal dimension) to justify a dedicated table. The effective rate metric could be derived from raw CorporateLoan data if needed.
- **Decision**: CLOSED — insufficient data volume to justify new infrastructure. If future drops include monthly TASAS DATOS with date column, reopen.

## References
- Parent task research: `docs/kanban/DOING/2026-02-09-1430__TASK__secure-prod-db-comparison-and-data-drop-policy/research.md`
- Source file: `data/raw/incoming/drive-download-20260209T193355Z-1-001/TASAS DATOS.csv`
- UTF-16 helper: `plugins/bank-advisor-private/etl/core/loaders/smart_csv.py:scan_csv_smart()`
