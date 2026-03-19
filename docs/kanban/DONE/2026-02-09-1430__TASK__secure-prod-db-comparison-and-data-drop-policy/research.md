# Research

## Questions
- Which incoming files are directly compatible with current loaders?
- Which files require adapters due to schema/encoding/header drift?
- What is the safest way to execute prod comparisons without exposing credentials?

## Findings
- Current ETL expects canonical filenames under `data/raw` and does not ingest from `incoming` by default.
- Incoming drop contains mixed quality:
  - Compatible examples: `CNBV_Cartera_Bancos_V2.xlsx`, `ICAP_Bancos.xlsx`, `TDA.xlsx`, `CASTIGOS.xlsx`.
  - Drift examples:
    - `040_R04A_419.csv` includes pivot/noise columns and structure drift vs canonical R04A.
    - `nuevo2.csv` appears headerless.
    - `QUEBRANTOS.csv` and `TASAS DATOS.csv` are UTF-16 tab-delimited.
- Migration baseline confirms normalized schema naming (`bank_dim_*`, `bank_fact_*`, `bank_src_*`, `bank_etl_*`).
- Production data quality finding:
  - `bank_fact_metricas_financieras` allows duplicates (no unique constraint) and currently has 3 duplicate groups for `institucion_id=96` (`CITIBANAMEX`) on `2024-09-01`, `2025-08-01`, `2025-09-01`.
  - Impact: queries that assume one row per bank-month can become non-deterministic (chart selection can flip rows depending on ORDER BY / planner).

### Implemented In Repo (2026-02-09)
- Promotion workflow (incoming -> canonical):
  - `plugins/bank-advisor-private/etl/core/data_promotion.py`
  - `plugins/bank-advisor-private/scripts/promote_incoming_drop.py`
  - Output: `plugins/bank-advisor-private/data/raw/current/` populated via symlinks (default).
- Smart CSV reader (UTF-16 BOM + tab delimiter):
  - `plugins/bank-advisor-private/etl/core/loaders/smart_csv.py`
  - `scan_csv_smart()` supports UTF-16 and tab-delimited inputs; unit tests added.
- Institutions reconcile (incoming Instituciones.xlsx -> dim):
  - `plugins/bank-advisor-private/etl/core/instituciones_reconcile.py`
  - `plugins/bank-advisor-private/scripts/reconcile_instituciones_dim.py`
  - Handles CNBV code normalization and INVEX remap (`040059` -> `040131`).
- Loader/schema robustness:
  - `DataPaths.be_bm` supports env override and discovers latest `BE_BM_*.xlsx` when the canonical file is missing.
  - `bank_dim_institucion` mapping is schema-robust (`codigo_cnbv` vs `clave_cnbv`).
- Hipotecarios/report loaders:
  - `etl/core/etl_hipotecarios.py` resolves known alias folders for incoming drops (e.g. `Reportes` -> `Reportes_Regulatorios`).
  - `etl/core/loaders/loaders_reportes_reg.py` discovers `*R04A*.csv`/`*R12A*.csv` and maps drift columns (`institucion` -> `clave_institucion`, `importe_pesos` -> `valor`).
- Validators:
  - `validator_r12a_quality.py` max period is dynamic (env `ETL_MAX_VALID_PERIOD` or current month).
- Safety:
  - ETL logging redacts DB URLs so `user:password@host` never prints to logs.

### Mapping Matrix (Raw -> ETL -> DB)
Core targets for the Bank Advisor plugin ETL (3NF schema):

| Canonical raw input (under `data/raw/current/`) | Loader key(s) | Transform output | Target table |
|---|---|---|---|
| `CNBV_Cartera_Bancos_V2.xlsx` | `cnbv` | `monthly_kpis` (legacy CNBV core) | `bank_fact_kpis_mensual` |
| `CASTIGOS.xlsx` | `castigos` | enrich `monthly_kpis` | `bank_fact_kpis_mensual` |
| `ICAP_Bancos.xlsx` | `icap` | enrich `monthly_kpis` | `bank_fact_kpis_mensual` |
| `TDA.xlsx` | `tda` | enrich `monthly_kpis` | `bank_fact_kpis_mensual` |
| `TE_Invex_Sistema.xlsx` (optional) | `te` | enrich `monthly_kpis` | `bank_fact_kpis_mensual` |
| `CorporateLoan_CNBVDB.csv` | `corporate_rates` | enrich `monthly_kpis` | `bank_fact_kpis_mensual` |
| `AnalisisGeneral/*` (optional) | `analisis_general` | multi-bank KPIs merged into `monthly_kpis` | `bank_fact_kpis_mensual` |
| `BE_BM_*.xlsx` (pm2/indicadores/cct) | `pm2`, `indicadores`, `cct` | `metricas_financieras` | `bank_fact_metricas_financieras` |
| `BE_BM_*.xlsx` (segment sheets) | `segments` | `metricas_segmentadas` | `bank_fact_cartera_segmentada` |
| `Instituciones.xlsx` | `instituciones` | mapping enrichment + dim reconcile | `bank_dim_institucion` (via reconcile script) |

Notes:
- The unified ETL (`etl.core.etl_unified`) writes only the three fact tables above.
- The larger "Hipotecarios" pipeline (`etl.core.etl_hipotecarios`) is responsible for `bank_src_*` tables (R04A/R12A/etc.) and related dims/partitions, and it requires a different directory layout (see `etl/core/etl_hipotecarios.py`).

### ETL Scripts: Gaps / Improvements Needed (drop-friendly)

#### Security
- Risk: ETL scripts log `db_url.split('@')[0]@***` which can include `user:password` (the password lives left-of-`@` in a PostgreSQL URL).
  - Affected: `plugins/bank-advisor-private/etl/core/etl_unified.py`, `plugins/bank-advisor-private/etl/core/etl_hipotecarios.py`.
  - Fix: replace with a safe redaction helper that never prints secrets (log host/dbname only, or `postgresql://USER@HOST/DB`).

#### Data Layout / Canonicalization
- `etl_unified` expects these filenames at the *root* of `--data-root`:
  - `CNBV_Cartera_Bancos_V2.xlsx`, `CASTIGOS.xlsx`, `Castigos Comerciales.xlsx`, `ICAP_Bancos.xlsx`, `TDA.xlsx`,
    `TE_Invex_Sistema.xlsx`, `CorporateLoan_CNBVDB.csv`, `Instituciones.xlsx`, plus `BE_BM_202509.xlsx`.
- Current repo layout has most of those under:
  - `plugins/bank-advisor-private/data/raw/incoming/drive-download-.../`
  - Not under `plugins/bank-advisor-private/data/raw/` root.
- Action: define a promotion workflow (incoming -> canonical) so `etl_unified` can run without manual copying.

#### BE_BM: Hardcoded month filename
- `DataPaths.be_bm` is hardcoded to `BE_BM_202509.xlsx`.
- Action: switch to "latest BE_BM_*.xlsx" discovery, or accept an override env/flag, to avoid monthly breakage.

#### Hipotecarios ETL: folder naming mismatch
- Fixed: `etl_hipotecarios` resolves known alias folders (e.g. `ReporteR04A-0419/`, `Reportes_Regulatorios/`) when canonical folders are missing.

#### Regulatory report loaders: filename + schema drift
- Fixed: loader now discovers `*R04A*.csv`/`*R12A*.csv`, picks the most recent match, and maps drift columns (`institucion` -> `clave_institucion`, `importe_pesos` -> `valor`) before transforms.

#### Duplicates in `metricas_financieras` likely originate upstream
- `merge_be_bm_metrics()` full-joins by `["institucion", "fecha_corte"]` without deduplication before joins.
- If BE_BM has duplicates per bank-month, those can flow into `bank_fact_metricas_financieras` (already observed in prod).
- Action: dedup inputs per `(institucion, fecha_corte)` with a deterministic rule (latest row, max non-null coverage, etc).

#### Validators have hardcoded max period (future false positives)
- Fixed: validators accept `max_valid_period=None` and resolve via `ETL_MAX_VALID_PERIOD` or current month (`YYYYMM`).

#### Dependency/runtime footgun (local)
- Running the ETL with system `python` may fail if `polars` is not installed.
- Action: document/standardize a single entrypoint (`plugins/bank-advisor-private/.venv/bin/python -m ...` or `uv run ...`)
  for both local and CI, to keep validation commands reproducible.

### Unclassified Files

#### `nuevo2.csv`
- **Rows**: 287,050 (headerless — no column names)
- **Encoding**: UTF-8 with Windows line endings (`\r\n`)
- **Structure**: Comma-delimited, ~25 columns. Sample columns appear to be:
  - Col 0: Currency type ("Pesos")
  - Col 1: Trust type ("Fideicomiso")
  - Col 2: State ("CIUDAD DE MEXICO")
  - Col 3: State code (9)
  - Col 4: Currency detail ("Moneda nacional")
  - Col 5: Unknown code (14)
  - Col 6: Institution name ("Actinver", "Afirme", "Banamex")
  - Col 7: CNBV institution code ("040133", "040062", "040002")
  - Col 8: Date (M/D/YY format: "8/31/25")
  - Col 9: Funding flag ("Sin Fondeo de BD o FF", "Con Fondeo de BD O FF")
  - Cols 10-24: Numeric metrics (some with comma formatting: "712,281,201")
- **Classification**: Cartera Analítica by region/institution/trust type. Not mappable to any current loader. Requires a new loader + header inference or a companion column definition. **Future ticket**.

#### `Catera Analitica Benchmark v2.xlsx` — IMPLEMENTED
- **Sheet1**: 87 institutions × 104 periods × 332 concept codes (wide format). Row 7 = header, rows 8+ = data.
- **Sheet2**: 100 rows concept catalog (R04A-style codes).
- **Loader**: `etl/core/loaders/loaders_benchmark.py` — reads with openpyxl, unpivots to long format.
- **Migration**: `migrations/054_create_benchmark_analitica.sql` — creates `bank_src_benchmark_analitica`.
- **Dry-run result**: 380,605 non-zero rows.
- **Status**: Implemented and tested. Ticket `2026-02-09-1801__TASK__...` moved to REVIEW.

#### `CREADOR DE TDA.xlsx` (23MB) — NEW DISCOVERY
- **Sheet "TDA"**: 37,162 rows × 14 cols. Summary pivot: `cve_institucion`, `cve_periodo`, `Sum of Cartera etapa 3`, `Sum of Cartera TOT`. The TDA ratio = Etapa3/TOT.
- **Sheet "BD TDA"**: 37,160 rows × 78 cols. **Full raw data** with complete Etapa breakdown:
  - 15 columns × 4 Etapas (ET1, ET2, ET3, VR) + 15 TOT columns = 75 value columns
  - Credit types: Comerciales (Empresarial, Entidades Financieras, Gubernamentales), Consumo (Tarjeta, Personales, Nomina, Automotriz, Bienes Muebles, Arrendamiento, Otros), Vivienda, ABCD
  - 135 institutions, 300 periods (200012 to 202511)
- **Relationship to TDA.xlsx**: `TDA.xlsx` (633KB, 17,443 rows) contains only the final TDA percentage. `CREADOR DE TDA.xlsx` is its **source** — the full Etapa granularity that Tableau uses for all Etapa % charts, cartera vencida, and cartera composition analysis.
- **Prod gap**: `bank_fact_kpis_mensual.tda_cartera_total` has only **23 non-null rows** out of 5,537. The TDA merge (`merge_tda()` in transforms.py) is failing silently for most institution-month pairs.
- **Classification**: Maps to a NEW dedicated loader + table. The Etapa granularity data is not available from any existing source in prod. **High-priority ticket needed**.

#### `TE_Invex_Sistema.xlsx` (9KB) — MISSING FROM INCOMING
- **Content**: 19 rows × 3 cols: `Fecha1` (bimonthly dates 2019-10 to 2024-06), `Sistema` (system-wide effective rate), `Invex Consumo` (Invex-specific consumer rate).
- **Present in**: Tableau `.twbx` package (embedded) but **not in the main incoming drop folder**.
- **Prod mapping**: Populates `bank_fact_kpis_mensual.tasa_sistema` and `tasa_invex_consumo` (220 rows in prod — more than the source, suggesting CorporateLoan also contributes).
- **Status**: Optional enrichment. Available via existing `load_te_invex()` loader. Just needs to be placed in `data/raw/current/`.

#### `Invex_Tablero_202406_v2021.4.twbx` (24MB) — Tableau Dashboard
- **Type**: Packaged Tableau workbook (ZIP containing `.twb` + data files).
- **Embedded data**: All core files (CNBV, Instituciones, CASTIGOS, Castigos Comerciales, CorporateLoan, ICAP, TDA) + `TE_Invex_Sistema.xlsx`.
- **Dashboard**: "Benchmark" — 47 worksheets covering: CC (Cartera Comercial), CT (Cartera Total), Cart_Venc (Cartera Vencida), Etapas, ICAP, ICOR, IMORA, PE (Perdida Esperada), Quebrantos, Reservas, TDA, Tasas.
- **Not a data source** — it's a visualization tool. The `.twb` inside defines calculated fields that document the business logic.

#### `Invex_Tablero_V3.twb` (3.5MB) — Standalone Tableau Workbook
- Different from the `.twbx`-embedded version (3.6MB, different MD5).
- Likely a newer iteration (standalone, no embedded data). Same structure and calculated fields.

### Prod vs Incoming Data Gap Analysis

Based on `bank_fact_kpis_mensual` (5,537 rows, 19 banks, 299 periods):

| Metric | Prod coverage | Source file | Gap severity |
|--------|---------------|-------------|--------------|
| `cartera_total` | 5,537 (100%) | CNBV_Cartera_Bancos_V2.xlsx | None |
| `icap_total` | 4,359 (79%) | ICAP_Bancos.xlsx | Low |
| `tasa_sistema` / `tasa_invex_consumo` | 220 (4%) | TE_Invex_Sistema.xlsx (19 rows) + CorporateLoan | Medium — TE file missing from incoming |
| `tda_cartera_total` | **23 (0.4%)** | TDA.xlsx (17,443 rows) | **CRITICAL** — merge failing silently |
| `quebrantos_comerciales` | 20 (0.4%) | QUEBRANTOS.csv (46 rows) | Low — closed as redundant |
| `tasa_mn` / `tasa_me` | sparse | CorporateLoan_CNBVDB.csv | Medium |

#### Critical finding: TDA data loss
- TDA.xlsx has **17,443 rows** covering 142 institutions × 300 periods.
- Only **23 rows** survive into prod `bank_fact_kpis_mensual.tda_cartera_total`.
- Root cause hypothesis: `merge_tda()` joins on `["fecha_month", "institucion"]` — institution code normalization or date format mismatch causing left-join to produce NULL for most pairs.
- **Action needed**: Debug the TDA merge pipeline. The data exists but the join is dropping >99.8% of it.

#### New data source: CREADOR DE TDA (Etapa breakdown)
- **BD TDA** sheet has 37,160 rows with full Etapa 1/2/3/VR granularity per credit sub-type.
- This data powers the Tableau charts: Etapa % composition, Cartera Vencida ratios, IMORA.
- Currently **no table exists** in prod for this granularity level.
- **Action needed**: New table `bank_src_tda_etapas` (or similar) + dedicated loader.

### Tableau Business Logic (Calculated Fields)

The Tableau `.twb` contains ~60 calculated fields that document how Bajaware/Invex computes key metrics. These are the reference formulas:

#### Core Portfolio Aggregations
- `Cartera Total = Comercial_Total + Consumo_Total + Vivienda_Total`
- `Cartera Comercial Total = Empresarial + Entidades_Financieras + Entidades_Gubernamentales`
- `Cartera Comercial SG (Sin Gob) = Empresarial + Entidades_Financieras` (excludes government)
- Each segment sums across all 4 Etapas: `Empresarial = ET1 + ET2 + ET3 + VR`

#### Risk Metrics
- `IMORA = (Comercial_ET3_SG + Castigos_Acumulados_Comercial) / (Comercial_ET1_SG + ET2_SG + ET3_SG)`
- `ICOR = Reservas_SG / Cartera_Vencida` (coverage ratio)
- `PE Total = Reservas_Etapa_Todas × (-1) / Cartera_Total`
- `PE Total SG = (Reservas_Todas - Res_Gub - Res_Consumo) × (-1) / Cartera_Total`
- `Cartera Vencida = Comercial_ET3_SG + Vivienda_ET3`
- `Cartera Vencida % = Comercial_ET3_SG / (ET1_SG + ET2_SG + ET3_SG)`

#### Etapa Composition (% of total)
- `CT_Etapa1 = (Comercial_ET1 + Consumo_ET1 + Vivienda_ET1) / Cartera_Total`
- `CT_Etapa2 = (Comercial_ET2 + Consumo_ET2 + Vivienda_ET2) / Cartera_Total`
- `CT_Etapa3 = (Comercial_ET3 + Consumo_ET3 + Vivienda_ET3) / Cartera_Total`

#### Quebrantos
- `Quebrantos CC = LIB_CASTIGOS_COMERC + QUITAS_COMER`
- `Castigos Acumulados = RUNNING_SUM(SUM(LIB_CASTIGOS_COMERC))`

#### Invex-specific filters
- Almost every metric has an "Invex" variant: `IF [DESCRIPCION] = 'INVEX' THEN <metric> ELSE 0/NULL END`
- This is the pattern for benchmarking Invex against peers.

#### Rate calculations (CorporateLoan datasource)
- `Tasa Todos = IF Average_Rate = 0 THEN NULL ELSE Average_Rate / 100`
- `Tasa Prom Pond = SUM(Total_Portfolio × Tasa) / SUM(Total_Portfolio)` (weighted average)
- `TDA = Non_Performing_Portfolio / Total_Portfolio`

#### TDA datasource
- `TDA % Total = TDA_Cartera_Total / 100`
- `TDA Invex = IF DESCRIPCION = 'INVEX' THEN TDA_Cartera_Total ELSE NULL END / 100`

#### Datasource → File Mapping
| Tableau Datasource | Source File(s) | Join Key |
|---|---|---|
| Sheet1+ (Varias conexiones) | CNBV_Cartera_Bancos_V2.xlsx + Instituciones.xlsx + CASTIGOS.xlsx + Castigos Comerciales.xlsx | cve_institucion |
| ICAP Bancos | ICAP_Bancos.xlsx | Banco (name-based) |
| CorporateLoan | CorporateLoan_CNBVDB.csv + Instituciones.xlsx | cve_institucion |
| TE_Invex_Sistema | TE_Invex_Sistema.xlsx | standalone (date only) |
| TDA | TDA.xlsx + Instituciones.xlsx | cve_institucion |

### Closed/Resolved Items

#### `QUEBRANTOS.csv` — CLOSED (redundant)
- 46 rows, verified as exact match with `bank_fact_kpis_mensual.quebrantos_comerciales` for Jan 2022.
- Ticket `2026-02-09-1802__TASK__...` moved to DONE.

#### `TASAS DATOS.csv` — CLOSED (insufficient data)
- 24 rows, bimonthly 2019-10 to 2023-06. Contains "Tasa Efectiva Promedio" (different metric from CorporateLoan rates).
- Too small (24 rows, no date dimension beyond the series) to justify new infrastructure.
- Ticket `2026-02-09-1803__TASK__...` moved to DONE.

## References
- `plugins/bank-advisor-private/etl/core/loaders_unified.py`
- `plugins/bank-advisor-private/etl/core/transforms.py`
- `plugins/bank-advisor-private/etl/core/db_writer_3nf.py`
- `plugins/bank-advisor-private/etl/core/loaders/loaders_benchmark.py`
- `plugins/bank-advisor-private/migrations/054_create_benchmark_analitica.sql`
- `plugins/bank-advisor-private/migrations/036_cleanup_rename_to_bank_prefix.sql`
- Tableau workbook: `Invex_Tablero_202406_v2021.4.twbx` (extracted to `/tmp/twbx_extract/`)
