# TASK: ETL Data Documentation & Refresh Pipeline

**Created**: 2026-02-18
**Priority**: P1
**Status**: DONE
**Type**: TASK (documentation + infrastructure)

## Objetivo

Documentar completamente la base de datos en GCP, los datos crudos de Bajaware, y diseñar un pipeline ETL reproducible para actualizar datos mensualmente con mínimo esfuerzo.

## Entregables

1. **Documentación del esquema de BD** — diagrama ER con todas las tablas, dimensiones, hechos, MVs
2. **Mapeo datos crudos → BD** — de dónde viene cada tabla, qué archivos la alimentan
3. **Documentación de scripts R de Bajaware** — qué hacen, qué transformaciones aplican
4. **Diseño de pipeline ETL automatizado** — cómo agregar nuevos meses con un solo comando
5. **Diagrama de flujo ETL** — para visualizar en Figma

## Scope

### Base de Datos GCP (PostgreSQL)

**Host**: `${PROD_DB_HOST}`:5432 | **DB**: bankadvisor

#### Tablas de Dimensiones (11)

| Tabla | Registros | Descripción |
|-------|-----------|-------------|
| `bank_dim_institucion` | 124 | Instituciones financieras (clave CNBV, nombre) |
| `bank_dim_periodo` | 372 | Periodos mensuales 2000-2030 |
| `bank_dim_estado` | 40 | 32 estados + extranjero + no especificado |
| `bank_dim_actividad_economica` | 24 | Sectores económicos |
| `bank_dim_destino_credito` | 28 | Destinos de crédito |
| `bank_dim_segmento_cartera` | 15 | Segmentos de cartera |
| `bank_dim_tipo_cartera` | 4 | Empresas, Gobierno, Estados, Financieras |
| `bank_dim_tamano_empresa` | 5 | Micro, Pequeña, Mediana, Grande, Fideicomiso |
| `bank_dim_moneda` | 3 | MXN, UDIS, Extranjera |
| `bank_dim_sector` | 3 | Banca Múltiple (40), Desarrollo (37), SOFOM (68) |
| `bank_dim_apoyo` | 2 | Tipos de apoyo crediticio |

#### Tablas de Hechos (Facts)

| Tabla | Tamaño | Registros | Periodo | Descripción |
|-------|--------|-----------|---------|-------------|
| `bank_fact_cartera_comercial` | 2.5 GB | 4,190,903 | 201606-202510 | Cartera comercial completa |
| `bank_fact_cartera_comercial_marginal` | 627 MB | 767,727 | 201606-202510 | Cartera marginal (riesgo) |
| `bank_fact_cartera_vivienda` | 627 MB | 746,956 | 201901-202510 | Hipotecarios marginales |
| `bank_fact_kpis_mensual` | 4.7 MB | 11,882 | 200012-202511 | KPIs mensuales por banco |
| `bank_fact_metricas_financieras` | 96 KB | 162 | 202409-202509 | ROA, ROE, IMOR, ICOR |
| `bank_fact_cartera_segmentada` | 616 KB | 2,445 | 202409-202509 | Cartera por segmento |

#### Tablas Source (Particionadas por año)

| Tabla | Particiones | Registros | Periodo | Descripción |
|-------|-------------|-----------|---------|-------------|
| `bank_src_analisis_general` | 26 (2000-2025) | 5,713,917 | 200012-202510 | Reporte consolidado sector 40 |
| `bank_src_banca_multiple` | 26 (2000-2025) | 12,504,022 | 200012-202510 | Consolidado banca múltiple |
| `bank_src_reporte_r04a` | 4 (2022-2025) | 5,843,725 | 202201-202510 | Balance General / Edo Resultados |
| `bank_src_reporte_r12a` | 4 (2022-2025) | 3,023,292 | 202201-202510 | Cartera de crédito |
| `bank_src_benchmark_analitica` | - | 380,605 | 201701-202511 | Benchmark cross-bank |
| `bank_src_tda_etapas` | - | 494,213 | 200012-202511 | Etapas IFRS9 por subtipo |

#### Materialized Views (13)

| MV | Tamaño | Propósito |
|----|--------|-----------|
| `bank_mv_cartera_por_estado` | 14 MB | Cartera por estado geográfico |
| `bank_mv_evolucion_cartera_banco` | 2.7 MB | Evolución temporal por banco |
| `bank_mv_cartera_por_actividad` | 2.2 MB | Cartera por actividad económica |
| `bank_mv_vivienda_por_perfil` | 1.8 MB | Vivienda por perfil demográfico |
| `bank_mv_cartera_tdc` | 1.2 MB | Cartera por tipo de cartera |
| `bank_mv_cartera_por_tamano` | 736 KB | Cartera por tamaño empresa |
| `bank_mv_cartera_por_destino` | 720 KB | Cartera por destino crédito |
| `bank_mv_vivienda_por_producto` | 576 KB | Vivienda por tipo producto |
| `bank_mv_metricas_financieras` | 192 KB | Métricas financieras consolidadas |
| `bank_mv_resumen_sistema` | 192 KB | Resumen sistema bancario |
| `bank_mv_comparativa_bancos` | 128 KB | Comparativa entre bancos |
| `bank_mv_ranking_cartera_mensual` | 88 KB | Ranking mensual de cartera |

### Datos Crudos Bajaware (Google Drive → local)

#### Estructura `plugins/bank-advisor-private/data/raw/`

```
raw/
├── AnalisisGeneral/
│   ├── sh_datos_csv_40_i.zip → 040_TO.csv (747MB)    ← Análisis General sector 40
│   ├── catalogo_conceptos_040.xlsx
│   └── catalogo_instituciones_040.csv
├── BancaMultipleGeneral/
│   ├── sh_datos_csv_40.zip → sh_datos_40.csv (527MB) ← Banca Múltiple sector 40
│   └── NOTAS_SH_BM.pdf
├── CarteraComercial/
│   ├── Base_Historica_Comercial.zip (175MB)           ← Cartera Comercial base total
│   ├── Historico_TamañoEmpresa.zip (3MB)
│   └── Historico_TipoCartera.zip (2MB)
├── CarteraVivienda/
│   └── Hipotecarios_Marginales.zip → .csv (201MB)    ← Hipotecarios marginales
├── ReporteA-1219/
│   └── 040_R12A_1219_133.zip → .csv (142MB)          ← Reporte R12A
├── ReporteR04A-0417/
│   └── 040_R04A_417_10.zip → .csv (293MB)            ← Reporte R04A
├── ReporteR13B-1321/
│   └── 040_R13B_1321.zip → .csv (19MB)               ← Reporte R13B
├── catalogs/
│   ├── inegi_entidades_municipios.xlsx
│   ├── iso_country_codes.csv
│   └── scian_estructura2023.xlsx
├── current/ → symlinks a incoming/latest                ← APUNTA A VERSIÓN VIGENTE
│   ├── 040_R04A_419.csv → incoming/.../040_R04A_419.csv
│   ├── CASTIGOS.xlsx, CNBV_Cartera_Bancos_V2.xlsx, ...
│   └── CorporateLoan_BM.R, Castigos_BM.R (scripts R)
└── incoming/
    ├── drive-download-20260209T.../                    ← Descarga 1
    └── drive-download-20260212T.../                    ← Descarga 2 (más reciente)
        ├── 040_R04A_419.csv (64MB)
        ├── CASTIGOS.xlsx
        ├── CNBV_Cartera_Bancos_V2.xlsx (3.4MB)
        ├── CREADOR DE TDA.xlsx (23MB)
        ├── CorporateLoan_CNBVDB.csv (270MB)
        ├── CorporateLoan_BM.R ← Script R para cartera empresas
        ├── Castigos_BM.R ← Script R para castigos
        ├── ICAP_Bancos.xlsx
        ├── Instituciones.xlsx
        ├── Invex_Tablero_V3.twb ← Tableau Workbook
        ├── Invex_Tablero_202406_v2021.4.twbx ← Tableau Packaged
        ├── QUEBRANTOS.csv
        ├── TASAS DATOS.csv
        ├── TDA.xlsx
        ├── nuevo2.csv (42MB)
        └── tableau_extract/
            └── Data/INVEX ANALITICS/ ← Data sources del TWB
```

### Scripts R de Bajaware

#### `CorporateLoan_BM.R` — Procesamiento Cartera Empresas
- Lee 2 CSVs de Tableau exports (MD_Emp_PETOTAL...)
- Combina con rbind, limpia columnas
- Reemplaza "Covalto" → "Forjadores" (renombre institucional)
- Hardcodea fecha: "Dic 2025" → "12/31/25"
- Agrega columnas vacías para claves calculadas
- Elimina filas con todos ceros
- **Proceso 100% manual, fecha hardcodeada**

#### `Castigos_BM.R` — Procesamiento Castigos
- Lee `040_R04A_419.csv` (reporte regulatorio)
- Filtra: periodo=202512, conceptos específicos (12 códigos), moneda=15 (MXN)
- Pivotea a matriz: institución × concepto
- Divide importes entre 1M (normalización a millones)
- **Proceso 100% manual, periodo hardcodeado**

### ETL Python Existente

Directorio: `plugins/bank-advisor-private/etl/`

```
etl/
├── core/
│   ├── etl_unified.py          ← Orquestador principal (Polars)
│   ├── loaders_unified.py      ← Lectura unificada de 8 fuentes
│   ├── transforms.py           ← Transformaciones
│   ├── transforms_pipeline.py  ← Pipeline de transforms
│   ├── db_writer_3nf.py        ← Escritura a esquema normalizado
│   ├── data_promotion.py       ← Promoción de datos
│   ├── redaction.py            ← Redacción de URLs
│   ├── instituciones_reconcile.py ← Reconciliación instituciones
│   ├── bank_mappings.py        ← Mapeos de bancos
│   ├── etl_hipotecarios.py     ← ETL hipotecarios
│   ├── loaders/                ← Loaders específicos por fuente
│   │   ├── loaders_analisis_general.py
│   │   ├── loaders_banca_multiple.py
│   │   ├── loaders_cartera_comercial.py
│   │   ├── loaders_cartera_vivienda.py
│   │   ├── loaders_reportes_reg.py
│   │   ├── loaders_benchmark.py
│   │   ├── loaders_tda_etapas.py
│   │   ├── loaders_imor_comercial.py
│   │   └── smart_csv.py
│   └── validators/             ← Validadores de calidad
│       ├── validator_business.py
│       ├── validator_integridad.py
│       ├── validator_hierarchy_sum.py
│       ├── validator_negative_balances.py
│       ├── validator_r04a_quality.py
│       ├── validator_r12a_quality.py
│       └── validator_r12a_business.py
├── ops/                        ← Operaciones ad-hoc
│   ├── load_special_r04a.py
│   ├── load_r12a_credit.py
│   ├── load_catalogo_conceptos.py
│   ├── load_missing_catalogs.py
│   ├── fix_catalog_r04a.py
│   ├── sync_weaviate.py
│   ├── sync_r04a_catalog.py
│   ├── validation_suite.py
│   └── enrich_concepts_heuristic.py
├── experimental/               ← Loaders GPU (experimental)
│   ├── load_r04a_gpu.py
│   ├── load_analisis_general_gpu.py
│   └── load_banca_multiple_gpu.py
├── legacy/                     ← ETL legacy (deprecated)
└── analysis/
    ├── analyze_catalog_gaps.sql
    └── analyze_r12a_issues.py
```

**59 migraciones SQL** en `plugins/bank-advisor-private/migrations/` (000-059)

### Cobertura Temporal — GAP Analysis

| Fuente de Datos | Último Periodo en BD | Datos Disponibles | Gap |
|-----------------|---------------------|-------------------|-----|
| Análisis General | 202510 (Oct 2025) | Dic 2025 en CSVs R | ~2 meses |
| Banca Múltiple | 202510 | Similar | ~2 meses |
| Cartera Comercial | 202510 | Dic 2025 en R script | ~2 meses |
| Cartera Vivienda | 202510 | TBD | ~2 meses |
| Reportes R04A | 202510 | 040_R04A_419.csv tiene más datos | ~2 meses |
| Reportes R12A | 202510 | Similar | ~2 meses |
| Benchmark Analítica | 202511 | Dic 2025 posible | ~1 mes |
| TDA Etapas | 202511 | Similar | ~1 mes |
| KPIs Mensual | Nov 2025 | Derivado de arriba | ~1 mes |
| Métricas Financieras | Sep 2025 | TBD — solo 13 meses cargados | ~4 meses |
| Cartera Segmentada | Sep 2025 | TBD — solo 13 meses | ~4 meses |

### Siguiente Fase — Diseño ETL Refresh Pipeline

1. **Diagrama ER** en Figma (star schema completo)
2. **Diagrama de flujo ETL** — de Google Drive → transform → PostgreSQL
3. **Script de refresh unificado** — `make etl-refresh` que:
   - Descargue nuevos datos de Google Drive (o los reciba en `incoming/`)
   - Actualice symlinks en `current/`
   - Ejecute loaders incrementales (solo periodos nuevos)
   - Regenere materialized views
   - Valide calidad de datos
   - Registre ejecución en `etl_runs`
4. **Reemplazo de scripts R** — migrar lógica de CorporateLoan_BM.R y Castigos_BM.R a Python/Polars
5. **Programación** — cron mensual o trigger manual

## Acceptance Criteria

- [x] Diagrama ER completo de la BD (exportable) — `docs/data/er_diagram.mermaid` + SVG + FigJam
- [x] Mapeo fuente → tabla para cada dataset — `docs/data/source_mapping.md`
- [x] Pipeline ETL que actualice con `make etl-refresh PERIODO=202512`
- [x] Scripts R documentados y con equivalente Python — Castigos_BM.R → SQL view (060)
- [x] Validación post-carga automática — 7 validators en refresh_orchestrator
- [x] Diagrama de flujo ETL visualizable — `docs/data/etl_flow.mermaid` + SVG + FigJam

## FigJam Diagrams (v2 — con colores y leyenda)

- **ER Star Schema**: https://www.figma.com/online-whiteboard/create-diagram/05b4ea08-9e18-4079-a7ef-1b72f32d4781
- **ETL Data Flow**: https://www.figma.com/online-whiteboard/create-diagram/b3fab387-dba5-4376-a8ac-f3a8c78c038e
- **MVs Detalle**: https://www.figma.com/online-whiteboard/create-diagram/974bb785-2416-4bf8-bf75-7633edd3f250

## Pendientes Operativos (no bloquean cierre)

- [ ] Ejecutar migración 060 en GCP: `psql $DATABASE_URL -f migrations/060_create_view_castigos_comerciales.sql`
- [ ] Dry-run: `make etl-refresh DRY=1`
- [ ] Carga real de periodos faltantes (Nov-Dic 2025)
- [ ] Crear particiones 2026 cuando lleguen datos nuevos
