# Research: ETL Data Documentation & Refresh Pipeline

**Date**: 2026-02-18

## 1. Esquema Actual de BD — Inventario Completo

### 1.1 Modelo Star Schema

```
                    ┌──────────────────────┐
                    │  bank_dim_institucion │ 124 rows
                    │  (surrogate: id)     │
                    └──────────┬───────────┘
                               │
    ┌──────────────┐    ┌──────┴──────┐    ┌──────────────────┐
    │ dim_estado   │    │  FACT       │    │ dim_periodo      │ 372 rows
    │ 40 rows      ├────┤  TABLES     ├────┤ (2000-2030)      │
    └──────────────┘    └──────┬──────┘    └──────────────────┘
                               │
    ┌──────────────┐    ┌──────┴──────┐    ┌──────────────────┐
    │ dim_moneda   │    │             │    │ dim_sector       │
    │ 3 rows       ├────┤             ├────┤ 3 rows           │
    └──────────────┘    └─────────────┘    └──────────────────┘
```

### 1.2 Tipos de Columna periodo

**INCONSISTENCIA DETECTADA**: Las tablas usan tipos mixtos para `periodo`:

| Tabla | Columna | Tipo | Formato |
|-------|---------|------|---------|
| `bank_fact_cartera_comercial` | `periodo` | VARCHAR(6) | "202510" |
| `bank_fact_cartera_vivienda` | `periodo` | VARCHAR(6) | "202510" |
| `bank_src_analisis_general` | `periodo` | VARCHAR(6) | "202510" |
| `bank_src_banca_multiple` | `periodo` | VARCHAR(6) | "202510" |
| `bank_src_reporte_r04a` | `periodo` | VARCHAR(6) | "202510" |
| `bank_src_reporte_r12a` | `periodo` | VARCHAR(6) | "202510" |
| `bank_src_benchmark_analitica` | `periodo` | INTEGER | 202511 |
| `bank_src_tda_etapas` | `cve_periodo` | INTEGER | 202511 |
| `bank_fact_kpis_mensual` | `fecha` | TIMESTAMP | 2025-11-01 |
| `bank_fact_metricas_financieras` | `fecha_corte` | TEXT | "2025-09-01" |
| `bank_fact_cartera_segmentada` | `fecha_corte` | TEXT | "2025-09-30" |

**Recomendación**: Todas deberían usar `periodo_id` (FK → bank_dim_periodo). Ya existe `periodo_id` en varias tablas pero conviven ambos campos.

### 1.3 FK Status

- `bank_fact_cartera_comercial`: tiene FKs pero muchas son `NOT VALID` (no se validaron contra datos existentes)
- `bank_fact_kpis_mensual`: tiene FKs válidas a dim_institucion y dim_periodo
- Las tablas `_src_` no tienen FKs (diseño intencional — son staging tables)

### 1.4 Tamaño Total de la BD

Estimado: ~5.5 GB de datos factuales + ~500 MB de fuentes + ~25 MB de MVs ≈ **~6 GB total**

## 2. Mapeo Fuente → Tabla

### 2.1 Fuentes de Datos y su Destino

```
GOOGLE DRIVE (Bajaware)                    POSTGRESQL
═══════════════════════════                ═══════════════════════════
040_TO.csv (747MB)                    →    bank_src_analisis_general (partitioned)
  └─ AnalisisGeneral/sh_datos_csv_40_i/

sh_datos_40.csv (527MB)              →    bank_src_banca_multiple (partitioned)
  └─ BancaMultipleGeneral/sh_datos_40/

Base_Historica_Comercial/ (175MB zip) →    bank_fact_cartera_comercial (2.5GB)
  └─ CarteraComercial/                     bank_fact_cartera_comercial_marginal (627MB)

Hipotecarios_Marginales.csv (201MB)  →    bank_fact_cartera_vivienda (627MB)
  └─ CarteraVivienda/

040_R04A_417_10.csv (293MB)          →    bank_src_reporte_r04a (partitioned)
  └─ ReporteR04A-0417/

040_R12A_1219_133.csv (142MB)        →    bank_src_reporte_r12a (partitioned)
  └─ ReporteA-1219/

040_R04A_419.csv (64MB)              →    bank_src_reporte_r04a (append incremental)
  └─ incoming/drive-download-*/            Usado también por Castigos_BM.R

CorporateLoan_CNBVDB.csv (270MB)     →    bank_fact_cartera_comercial (update)
  └─ incoming/drive-download-*/            Procesado por CorporateLoan_BM.R

CNBV_Cartera_Bancos_V2.xlsx          →    bank_src_benchmark_analitica
Catera Analitica Benchmark v2.xlsx   →    bank_src_benchmark_analitica
CREADOR DE TDA.xlsx                  →    bank_src_tda_etapas
CASTIGOS.xlsx                        →    bank_fact_kpis_mensual (campo castigos)
ICAP_Bancos.xlsx                     →    bank_fact_kpis_mensual (campo icap)
TDA.xlsx                             →    bank_fact_kpis_mensual (campo tda)
TE_Invex_Sistema.xlsx                →    bank_fact_kpis_mensual (tasas)
Instituciones.xlsx                   →    bank_dim_institucion
QUEBRANTOS.csv                       →    bank_fact_kpis_mensual (campo quebrantos)
TASAS DATOS.csv                      →    bank_fact_kpis_mensual (tasas mn/me)

BE_BM_202509.xlsx (16 hojas)        →    bank_fact_kpis_mensual (orquestador principal)
                                          bank_fact_metricas_financieras
                                          bank_fact_cartera_segmentada
```

### 2.2 ETL Unificado (etl_unified.py)

Procesa las 8 fuentes del "workbook" principal:
1. `BE_BM_202509.xlsx` — 16 hojas con KPIs precalculados
2. `CNBV_Cartera_Bancos_V2.xlsx` — Benchmark histórico
3. `ICAP_Bancos.xlsx` — Índice de Capitalización
4. `TDA.xlsx` — Tasa de Distribución de Activos
5. `TE_Invex_Sistema.xlsx` — Tasas de Equilibrio
6. `CorporateLoan_CNBVDB.csv` — Cartera empresarial detallada
7. `CASTIGOS.xlsx` — Castigos y quebrantos
8. `Instituciones.xlsx` — Catálogo de instituciones

### 2.3 Loaders Específicos (grandes volúmenes)

Los CSVs de CNBV (>100MB) se cargan con loaders especializados en `etl/core/loaders/`:
- `loaders_analisis_general.py` → 040_TO.csv
- `loaders_banca_multiple.py` → sh_datos_40.csv
- `loaders_cartera_comercial.py` → Base_Historica_Comercial
- `loaders_cartera_vivienda.py` → Hipotecarios_Marginales.csv
- `loaders_reportes_reg.py` → R04A, R12A
- `loaders_benchmark.py` → Benchmark analítica
- `loaders_tda_etapas.py` → TDA etapas IFRS9

## 3. Análisis de Scripts R de Bajaware

### 3.1 CorporateLoan_BM.R

**Propósito**: Transformar exports de Tableau de cartera empresarial para carga manual.

**Pasos**:
1. Leer 2 CSVs: `MD_Emp_PETOTAL.TamanioEmpresasEstado_MDR_Sector_IFRS9 (1).csv` y variante
2. `rbind()` — combinar ambos
3. Drop columnas: Textbox3, Textbox6, Actividad_Economica_agregada
4. Limpiar "Escala": quitar prefijo "Montos expresados en : "
5. Transliterar acentos con `iconv(..., "ASCII//TRANSLIT")`
6. Renombrar: "Covalto" → "Forjadores"
7. **HARDCODE**: "Dic 2025" → "12/31/25"
8. Agregar columnas vacías: clave_estado, clave_moneda, clave_inst, Clientes, Créditos
9. Copiar columnas: Tasa_ponderada_MD → Tasa_ponderada_MD2, Cartera_vigente → Etapa1, Cartera_vencida → Etapa3
10. Reordenar 25 columnas
11. Filtrar filas con todos ceros

**Columnas output**: Escala, Tamaño_empresa, Estado, clave_estado, Moneda, clave_moneda, Institución, clave_inst, Periodo, Apoyo, Cartera_total, Cartera_vigente, Cartera_vencida, IMOR, Clientes, Créditos, Tasa_ponderada, Plazo_ponderado, Monto_dispuesto, Tasa_ponderada_MD, Tasa_ponderada_MD2, Etapa1, Textbox2, Etapa3, Textbox5

### 3.2 Castigos_BM.R

**Propósito**: Extraer castigos de reporte regulatorio R04A.

**Pasos**:
1. Leer `040_R04A_419.csv`
2. Pad instituciones a 6 dígitos
3. **HARDCODE**: filtrar periodo=202512 y 13 conceptos específicos y moneda=15
4. Pivot: institución × concepto (dcast)
5. Reordenar los 13 conceptos en orden específico
6. Dividir importes entre 1M (normalización a millones)
7. Exportar `castigos.csv`

**Conceptos de castigos**:
- 112800105001, 112800105002, 112800105003 (castigos principales)
- 112800106001, 112800106002 (recuperaciones)
- 112800204002, 112800204004 (castigos consumo)
- 112800305005, 112800305006, 112800305007 (castigos vivienda)
- 112800506017, 112800506018, 112800506019 (otros)

## 4. Patrón `current/` + `incoming/`

Ya existe un sistema de versionamiento de datos:
```
incoming/
  drive-download-20260209T.../  ← descarga anterior
  drive-download-20260212T.../  ← descarga más reciente

current/  ← symlinks a la descarga vigente
  CorporateLoan_CNBVDB.csv → ../incoming/drive-download-20260212T.../CorporateLoan_CNBVDB.csv
  ...
```

Este patrón es bueno como base: descargas inmutables en `incoming/`, punteros en `current/`.

## 5. Gaps y Oportunidades

### 5.1 Datos Faltantes
- Los scripts R hardcodean "Dic 2025" / periodo=202512, sugiriendo que Bajaware ya tiene datos hasta diciembre 2025
- La BD solo llega a Oct/Nov 2025
- Gap de ~2-4 meses según la tabla

### 5.2 Proceso Actual (Manual)
1. Bajaware descarga datos de portal CNBV
2. Procesa con R (hardcodea fechas)
3. Exporta a Tableau como datasource
4. Alguien descarga desde Google Drive como ZIP
5. Se extrae y se corre ETL Python manualmente

### 5.3 Diseño Propuesto — ETL Refresh

```
TRIGGER: Nueva descarga de Google Drive
    │
    ▼
[1] INGEST: copiar a incoming/drive-download-{timestamp}/
    │
    ▼
[2] PROMOTE: actualizar symlinks en current/
    │
    ▼
[3] DETECT: smart_csv.py identifica periodos nuevos
    │
    ▼
[4] LOAD: loaders incrementales (solo periodos nuevos)
    │  ├─ loader_analisis_general → partición nueva
    │  ├─ loader_banca_multiple → partición nueva
    │  ├─ loader_cartera_comercial → UPSERT por PK
    │  ├─ loader_cartera_vivienda → UPSERT
    │  ├─ loader_reportes_reg → partición nueva
    │  ├─ loader_benchmark → UPSERT
    │  └─ loader_tda_etapas → UPSERT
    │
    ▼
[5] TRANSFORM: etl_unified → KPIs, métricas, segmentada
    │
    ▼
[6] REFRESH: materialized views (13 MVs)
    │
    ▼
[7] VALIDATE: validator suite (calidad, integridad, business rules)
    │
    ▼
[8] LOG: etl_runs + etl_quality_metrics
```

### 5.4 Migración de R → Python

Los 2 scripts R se pueden reemplazar completamente:
- `CorporateLoan_BM.R` → ya cubierto por `loaders_cartera_comercial.py`
- `Castigos_BM.R` → lógica de filtrado y pivot se puede agregar a `loaders_reportes_reg.py`

La diferencia es que nuestro ETL Python ya parametriza el periodo y no lo hardcodea.
