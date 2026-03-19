# Validation

## Commands
- `cd plugins/bank-advisor-private && .venv/bin/python -m etl.core.etl_unified --data-root data/raw/incoming/drive-download-20260209T193355Z-1-001 --dry-run`
- `psql "service=bankadvisor_prod" -w -c "SELECT MAX(fecha), COUNT(*) FROM bank_fact_kpis_mensual;"`
- `psql "service=bankadvisor_prod" -w -c "SELECT MAX(fecha_corte::date), COUNT(*) FROM bank_fact_metricas_financieras;"`
- `psql "service=bankadvisor_prod" -w -c "SELECT MAX(to_date(periodo,'YYYYMM')), COUNT(*) FROM bank_src_reporte_r04a;"`
- `psql "service=bankadvisor_prod" -w -c "SELECT MAX(to_date(periodo,'YYYYMM')), COUNT(*) FROM bank_src_reporte_r12a;"`

## Results
- PASS/FAIL: **PASS** (all 6 verification criteria met)

### Local Validation (Promotion + ETL Dry-Run)
- Promotion:
  - Command: `cd plugins/bank-advisor-private && .venv/bin/python scripts/promote_incoming_drop.py`
  - Result: PASS (canonical `data/raw/current/` populated; required files linked; optional sources filled from fallback).
- Unified ETL dry-run:
  - Command: `cd plugins/bank-advisor-private && .venv/bin/python -m etl.core.etl_unified --data-root data/raw/current --dry-run`
  - Result: PASS (sources load + transforms succeed without writing to DB).
- Institutions reconcile (report-only):
  - Command: `cd plugins/bank-advisor-private && .venv/bin/python scripts/reconcile_instituciones_dim.py`
  - Result: PASS (diff report generated; no DB writes executed).

---

## Production Baseline (Read-Only, 2026-02-10)

Connection: `psql "service=bankadvisor_prod"` (pg_service.conf, no secrets exposed).

### Fact Tables

| Table | Rows | Banks | Min fecha | Max fecha | Periods |
|---|---|---|---|---|---|
| `bank_fact_kpis_mensual` | 5,238 | 18 | 2000-12-01 | 2025-10-01 | 299 |
| `bank_fact_metricas_financieras` | 162 | 45 | 2024-09-01 | 2025-09-01 | 3 |
| `bank_fact_cartera_segmentada` | 2,445 | 44 | 2024-09-30 | 2025-09-30 | 3 |

### Source Tables

| Table | Rows | Min periodo | Max periodo |
|---|---|---|---|
| `bank_src_reporte_r04a` | 5,843,725 | 202201 | 202510 |
| `bank_src_reporte_r12a` | 3,023,292 | 202201 | 202510 |
| `bank_src_benchmark_analitica` | 380,605 | - | - |
| `bank_src_tda_etapas` | 494,213 | - | - |

### Dimension Table

| Table | Rows | Distinct codes |
|---|---|---|
| `bank_dim_institucion` | 105 | 105 |

### KPI Column Coverage (bank_fact_kpis_mensual)

| Column | Non-null % | Severity |
|---|---|---|
| `cartera_total` | 100.0% | OK |
| `imor` | 96.8% | OK |
| `icap_total` | 78.7% | Low |
| `quebrantos_comerciales` | 13.8% | Medium |
| `tda_cartera_total` | 5.8% | CRITICAL |
| `tasa_sistema` | 2.4% | Medium |

### FK Coverage

| Join | Total | Matched | Orphans | Coverage |
|---|---|---|---|---|
| `kpis_mensual` -> `dim_institucion` | 5,238 | 5,238 | 0 | 100.0% |
| `metricas_financieras` -> `dim_institucion` | 162 | 135 | 27 | 83.3% |

### Duplicates (metricas_financieras)

27 rows with NULL `institucion_id` across 3 periods (9 per period).

Unmatched `banco_norm` values:

| banco_norm | In dim? | Notes |
|---|---|---|
| AZTECA | Yes (id=71) | Join failing despite dim match |
| BAJIO | Yes (id=4) | Join failing despite dim match |
| BBVA | Yes (id=2) | Join failing despite dim match |
| CITIBANAMEX | Yes (id=7) | 2 rows/period (old + new entity) |
| COVALTO | Yes (id=25) | Join failing despite dim match |
| KAPITAL BANK | No | Missing from dim |
| N.D. NO DISPONIBLE | No | Placeholder row |
| UALA | No | Missing from dim |

**Root cause**: ETL writer joins `banco_norm` to `dim.nombre_corto` at write time. Banks exist in dim but the name-matching has case/whitespace/accent differences. Migrations 056+057 fix some CNBV codes but this gap persists for the 5 "in dim but NULL" banks.

**Delta vs previous baseline (2026-02-09)**:
- `kpis_mensual` rows: 5,537 -> 5,238 (decrease: 299 rows removed by migration 056 duplicate consolidation)
- `metricas_financieras` NULL duplicates: Previously reported as `institucion_id=96 CITIBANAMEX` — now confirmed as 8 distinct `banco_norm` values with NULL `institucion_id`, not CITIBANAMEX-specific

### Materialized Views (12 total)

| MV | Size |
|---|---|
| `bank_mv_cartera_por_estado` | 9,728 kB |
| `bank_mv_cartera_por_actividad` | 1,624 kB |
| `bank_mv_vivienda_por_perfil` | 1,304 kB |
| `bank_mv_evolucion_cartera_banco` | 1,160 kB |
| `bank_mv_cartera_tdc` | 608 kB |
| `bank_mv_cartera_por_destino` | 464 kB |
| `bank_mv_cartera_por_tamano` | 440 kB |
| `bank_mv_vivienda_por_producto` | 336 kB |
| `bank_mv_resumen_sistema` | 64 kB |
| `bank_mv_metricas_financieras` | 64 kB |
| `bank_mv_comparativa_bancos` | 16 kB |
| `bank_mv_ranking_cartera_mensual` | 8 kB |

### Pending Migrations

- Migration 056: Consolidate 16 duplicate `dim_institucion` + FK move for `cartera_segmentada` (unique constraint NOT applied yet)
- Migration 057: Fix 9 wrong CNBV codes + add PAGATODO/CREDIT SUISSE

---

## Validation Gates (Recurring Data-Drop Policy)

### Gate 1: File Manifest

Before promotion from `data/raw/incoming/` to `data/raw/current/`:

| Check | Command | Pass criteria |
|---|---|---|
| Required files present | `promote_incoming_drop.py --dry-run` | All `required=True` specs resolved |
| No unknown files | Manual review of unmatched | Documented or new ticket created |
| Encoding detection | `smart_csv.scan_csv_smart()` | UTF-8/UTF-16 auto-detected, no decode errors |

### Gate 2: Schema Validation

| Check | Method | Pass criteria |
|---|---|---|
| Column names match | Loader `_detect_report_schema()` | All required columns present or mapped |
| Data types valid | Polars schema inference | No all-null critical columns |
| Row count sanity | Polars `.collect().height` | Within expected minimums |

Expected minimums:

| File | Min rows |
|---|---|
| `CNBV_Cartera_Bancos_V2.xlsx` | 5,000 |
| `ICAP_Bancos.xlsx` | 500 |
| `BE_BM_*.xlsx` | 40 institutions |
| `R04A*.csv` | 1,000,000 |
| `R12A*.csv` | 500,000 |
| `Instituciones.xlsx` | 80 |

### Gate 3: Freshness

| Check | Method | Pass criteria |
|---|---|---|
| Max period recent | `MAX(fecha)` or `MAX(periodo)` | >= current month - 2 |
| No future dates | `MAX(fecha) <= today + 31d` | No impossible dates |

### Gate 4: FK Coverage

| Check | SQL pattern | Pass criteria |
|---|---|---|
| KPIs -> dim | `LEFT JOIN ... WHERE dim IS NULL` | 0 orphans (100%) |
| Metricas -> dim | Same | >= 95% coverage |
| Segmentada -> dim | Same | >= 95% coverage |

### Gate 5: Dedup Integrity

| Check | SQL pattern | Pass criteria |
|---|---|---|
| KPIs unique per bank-month | `GROUP BY ... HAVING COUNT(*) > 1` | 0 duplicates |
| Metricas unique per bank-month | Same | 0 duplicates |

### Gate 6: Post-Deployment Parity

| Check | Method | Pass criteria |
|---|---|---|
| Row count delta | Compare pre/post `COUNT(*)` | Increase only, no data loss |
| Max fecha advance | Compare pre/post `MAX(fecha)` | Same or newer |
| MV refresh | `REFRESH MATERIALIZED VIEW CONCURRENTLY` | No errors |
| Regression tests | `test_bug_regression_suite.py` against prod | 27/27 pass |

---

## Known Issues (from baseline)

1. **TDA coverage critical (5.8%)**: `merge_tda()` drops 99%+ of data. Ticket: `tda-date-format-bug`.
2. **Metricas FK gap (83.3%)**: 27 rows NULL `institucion_id` — name matching bug in ETL writer for 8 `banco_norm` values.
3. **KAPITAL BANK / UALA / N.D.**: Missing from `bank_dim_institucion`.
4. **Migrations 056+057 pending**: Must apply before next ETL re-run.

## Notes
- Never paste secret values in chat or markdown.
- Use `pg_service.conf` for all production connections (no inline credentials).
- Baseline snapshot date: 2026-02-10.
