---
id: "TASK-2026-03-02__etl-refresh-diciembre-2025"
title: "ETL Refresh: Cargar datos de Diciembre 2025"
status: "DONE"
phase: "Validate"
scope_in:
  - "Promover nueva entrega drive-download-20260302T184043Z-1-001 a incoming/"
  - "Actualizar symlinks en current/"
  - "Cargar datos de Dic 2025 (periodo 202512) en tablas source y fact"
  - "Refresh de materialized views"
  - "Validar cobertura temporal post-carga"
scope_out:
  - "Cartera Comercial y Vivienda (no incluidos en esta entrega)"
  - "BE_BM workbook (no incluido — sin actualización de metricas_financieras ni cartera_segmentada)"
  - "Migraciones de schema"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "make etl-freshness"
pr_files: []
test_status: ""
---

# Summary
- Objective: Cargar los datos de Diciembre 2025 (periodo 202512) a la BD PostgreSQL usando la nueva entrega de Bajaware del 2 de marzo 2026.
- Constraints: No hay BE_BM workbook actualizado en esta entrega, por lo que `bank_fact_metricas_financieras` y `bank_fact_cartera_segmentada` no se actualizan. No hay CSVs de cartera comercial/vivienda nuevos.

# Archivos Nuevos o Actualizados (vs entrega 2026-02-12)

## Archivos que CRECIERON (contienen datos nuevos hasta 202512)
| Archivo | Anterior | Nuevo | Delta | Tabla destino |
|---------|----------|-------|-------|---------------|
| `sh_datos_40.csv` | NO EXISTÍA | 533 MB | **NUEVO** | `bank_src_banca_multiple` |
| `040_R04A_419.csv` | 64 MB | 204 MB | +139 MB | `bank_src_reporte_r04a` |
| `CorporateLoan_CNBVDB.csv` | 270 MB | 283 MB | +13 MB | `bank_fact_kpis_mensual` (tasas) |
| `ICAP_Bancos.xlsx` | 479 KB | 618 KB | +138 KB | `bank_fact_kpis_mensual` (icap) |
| `CASTIGOS.xlsx` | 450 KB | 510 KB | +60 KB | `bank_fact_kpis_mensual` (castigos) |
| `CNBV_Cartera_Bancos_V2.xlsx` | 3.36 MB | 3.37 MB | +11 KB | `bank_fact_kpis_mensual` (cartera) |

## Archivos completamente nuevos (no existían antes)
| Archivo | Tamaño | Descripción |
|---------|--------|-------------|
| `ACTUALIZACION INVEX.pdf/.docx` | 4.7 MB | Documento descriptivo de Bajaware |
| `Creador CorporateLoan.xlsx` | 9.2 MB | Archivo fuente/creador de CorporateLoan |
| `Creador_castigos.xlsx` | 4.9 MB | Archivo fuente/creador de castigos |
| `Cuentas_desc.xlsx` | 10 KB | Catálogo de descripciones de cuentas |
| `FD239760.xlsx` | 3.2 MB | Archivo nuevo (por investigar) |
| `cat_conceptos_40.xlsx` | 44 KB | Catálogo de conceptos sector 40 |
| `tda IFRS9.xlsx` | 68 KB | TDA con etapas IFRS9 |
| `Nueva carpeta/` | — | CSVs mensuales 2024-07 a 2025-12 (Serie Histórica BM) |
| `Serie Historica_BM.R` | 1.7 KB | Script R de serie histórica |
| `castigos.csv` | 3 KB | CSV complementario de castigos |

## Archivos SIN CAMBIOS (mismo tamaño)
`Catera Analitica Benchmark v2.xlsx`, `Castigos Comerciales.xlsx`, `Instituciones.xlsx`, `TDA.xlsx`, `QUEBRANTOS.csv`, `TASAS DATOS.csv`, `nuevo2.csv`

# Cobertura temporal confirmada
- `sh_datos_40.csv`: hasta **202512** (Dic 2025)
- `040_R04A_419.csv`: hasta **202512** (Dic 2025)
- `CorporateLoan_CNBVDB.csv`: hasta **12/31/25** (Dic 2025)

# Updates
- 2026-03-02 13:00 - Creada. Research de archivos en nueva entrega completado.
- 2026-03-02 13:30 - Auditoría de BD completada. Plan detallado escrito.
- 2026-03-02 14:31 - ETL completado. Resultados:
  - `bank_src_banca_multiple`: 202512 (+147,684 rows incremental)
  - `bank_src_reporte_r04a`: 202512 (+184,871 rows incremental)
  - `bank_fact_kpis_mensual`: 11,913 rows (antes 11,882), max 2025-12-01, 63 bancos
  - INVEX Dic 2025: cartera $52B, ICAP 16.38%, IMOR 2.65%, TDA 2.43%
  - 31 bancos con datos en Dic 2025 (6 completos + 25 con imor_comercial)
  - MVs refrescadas
  - Bugs corregidos: ICAP/TDA INVEX (code 040059→040131), unique index para UPSERT
  - Limitación: market_share vacío (depende de AnalisisGeneral max 202510)
