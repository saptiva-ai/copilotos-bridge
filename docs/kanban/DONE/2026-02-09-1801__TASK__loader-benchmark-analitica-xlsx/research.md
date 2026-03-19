# Research

## Questions
- Does `openpyxl(data_only=True)` return computed dates or None?
- What is the exact institution/concept/date grain of the data?
- How does this benchmark relate to existing R04A data in `bank_src_reporte_r04a`?

## Findings

### File Structure (confirmed with .venv_gpu + openpyxl data_only=True)
- **Sheet1**: 309,537 total rows. Actual data starts at row 8.
  - Row 1: Date headers (Dec 2000 onwards) — formulas resolve to `datetime` with `data_only=True`
  - Row 7: `cve_institucion`, `cve_periodo`, then 332 concept codes as column headers
  - Row 8+: Data rows with `institucion` (040xxx), `periodo` (YYYYMM), then 332 monetary values
  - **11,719 data rows** (row 8 onwards with non-null institution)
  - **87 real institutions** (040xxx codes)
  - **104 unique periods**: 2017-01 to 2025-11 (8.9 years monthly)
  - **332 unique concepts** (R04A/R12A-style 12-digit codes: 100000000000 through 800000000000)
- **Sheet2**: 100 rows — concept catalog with `Concepto`, `Etapa`, `Descripcion`, `Desc entrada`, `ORDEN ENTRADA`
  - Concepts include Etapa 1 (130*), Etapa 2 (101800*), Etapa 3 (101800*) categories
  - Covers cartera comercial, consumo, vivienda, gubernamental

### Prod DB Comparison
- `bank_src_reporte_r04a`: 5.84M rows, concepts `101*` and `111*` only, periods 2022-01 to 2025-10 (3.8 years)
- `bank_src_reporte_r12a`: 3.02M rows, has `130*` concepts but different granularity
- **Benchmark adds**:
  - Concept codes `100*`, `130*`, `131*`, `660*`, `670*`, `800*` — many NOT in current R04A
  - Historical depth back to **2017-01** (vs R04A starting at 2022-01 = 5 extra years)
  - Pre-aggregated (one value per institution/period/concept) vs raw R04A (multiple rows per concept with sector/moneda/tipo_saldo breakdown)

### Assessment: MEDIUM PRIORITY — genuine new data
- This is NOT redundant with R04A/R12A — it adds:
  1. **5 years of extra history** (2017-2021)
  2. **New concept families** (100*, 130*, 660*, 670*, 800*) not in current R04A
  3. **Pre-aggregated benchmark** format (one value per bank/month/concept vs R04A's multi-dimensional rows)
- Layout is wide-format (332 concept columns) → needs unpivot to long-format for DB storage
- `data_only=True` successfully resolves formulas — no need for xlcalc
- **Target table**: `bank_src_benchmark_analitica` with schema `(cve_institucion, periodo, concepto, importe)`

## References
- Parent task research: `docs/kanban/DOING/2026-02-09-1430__TASK__secure-prod-db-comparison-and-data-drop-policy/research.md`
- Source file: `data/raw/incoming/drive-download-20260209T193355Z-1-001/Catera Analitica Benchmark v2.xlsx`
