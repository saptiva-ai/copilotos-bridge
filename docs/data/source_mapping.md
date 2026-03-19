# Mapeo: Fuente de Datos → Tabla Destino

> Referencia rápida de qué archivo alimenta cada tabla en PostgreSQL,
> más base de conocimiento consolidada de gotchas y problemas conocidos.

## Contenido

- [Tablas Source (Grandes Volúmenes CNBV)](#tablas-source-grandes-volúmenes-cnbv)
- [Tablas Fact (Cartera Detallada)](#tablas-fact-cartera-detallada)
- [Tablas Fact (KPIs — ETL Unificado)](#tablas-fact-kpis--etl-unificado)
- [Tablas de Dimensiones](#tablas-de-dimensiones)
- [Materialized Views](#materialized-views)
- [Scripts R de Bajaware (Legacy)](#scripts-r-de-bajaware-legacy)
- **[Gotchas Conocidos](#gotchas-conocidos)** ← base de conocimiento
  - [Índice de Síntomas](#índice-de-síntomas--solución)
  - [1. Unidades y Escala](#1-unidades-y-escala)
  - [2. Código de Institución INVEX](#2-código-de-institución-invex-040059-vs-040131)
  - [3. tasa_mn / tasa_me (4 bugs)](#3-tasa_mn--tasa_me-cadena-de-4-bugs--corregido-2026-03-03)
  - [4. periodo_id y pipeline Legacy](#4-periodo_id-y-pipeline-legacy)
  - [5. Merge legacy↔AG: tipo de fecha](#5-merge-legacyag-tipo-de-fecha)
  - [6. Calidad de Datos de Origen](#6-calidad-de-datos-de-origen)
  - [7. Constraints Técnicos](#7-constraints-técnicos)
  - [8. Castigos: dos fuentes, dos semánticas](#8-castigos-dos-fuentes-dos-semánticas-corregido-2026-03-04)
  - [9. Gaps de datos Dic 2025](#9-gaps-de-datos-dic-2025-corregido-2026-03-04)
  - [10. CSV version gap (tasas Dic 2025)](#10-csv-version-gap-tasas-dic-2025--corregido-2026-03-04)

---

## Tablas Source (Grandes Volúmenes CNBV)

| Archivo Fuente | Tamaño | Loader Python | Tabla Destino | Registros | Periodo |
|----------------|--------|---------------|---------------|-----------|---------|
| `040_TO.csv` (AnalisisGeneral) | 747 MB | `loaders_analisis_general.py` | `bank_src_analisis_general` (partitioned ×26) | 5.71M | 2000-2025 |
| `sh_datos_40.csv` (BancaMultiple) | 527 MB | `loaders_banca_multiple.py` | `bank_src_banca_multiple` (partitioned ×26) | 12.5M+ | 2000-2025 |
| `040_R04A_*.csv` (ReporteR04A) | 293+64 MB | `loaders_reportes_reg.py` | `bank_src_reporte_r04a` (partitioned ×4) | 5.84M | 2022-2025 |
| `040_R12A_*.csv` (ReporteR12A) | 142 MB | `loaders_reportes_reg.py` | `bank_src_reporte_r12a` (partitioned ×4) | 3.02M | 2022-2025 |
| `Catera Analitica Benchmark v2.xlsx` | 49 MB | `loaders_benchmark.py` | `bank_src_benchmark_analitica` | 380K | 2017-2025 |
| `CREADOR DE TDA.xlsx` | 23 MB | `loaders_tda_etapas.py` | `bank_src_tda_etapas` | 494K | 2000-2025 |

> **Nota symlink**: El loader espera `BM_SH_DATOS_40.csv` en `current/`. Si la entrega trae `sh_datos_40.csv`:
> `ln -sf ../incoming/<entrega>/sh_datos_40.csv plugins/bank-advisor-private/data/raw/current/BM_SH_DATOS_40.csv`

## Tablas Fact (Cartera Detallada)

| Archivo Fuente | Tamaño | Loader Python | Tabla Destino | Registros | Periodo |
|----------------|--------|---------------|---------------|-----------|---------|
| `CarteraComercial/Base_Historica_Comercial/` | 175 MB ZIP | `loaders_cartera_comercial.py` | `bank_fact_cartera_comercial` (2.5 GB) | 4.19M | 2016-2025 |
| (misma fuente) | — | `loaders_cartera_comercial.py` | `bank_fact_cartera_comercial_marginal` (627 MB) | 767K | 2016-2025 |
| `Hipotecarios_Marginales.csv` | 201 MB | `loaders_cartera_vivienda.py` | `bank_fact_cartera_vivienda` (627 MB) | 746K | 2019-2025 |

## Tablas Fact (KPIs — ETL Unificado)

El **ETL Unificado** (`etl_unified.py`) combina 8+ fuentes → `bank_fact_kpis_mensual`:

| Archivo Fuente | Campo(s) que aporta |
|----------------|---------------------|
| `CNBV_Cartera_Bancos_V2.xlsx` | cartera_total, cartera_vencida, etapas 1/2/3, cartera_comercial_sin_gob, reservas |
| `CASTIGOS.xlsx` | quebrantos_comerciales (castigos) |
| `Castigos Comerciales.xlsx` | castigos_acum_comercial |
| `ICAP_Bancos.xlsx` | icap_total, icap_ccb, icap_ccf |
| `TDA.xlsx` | tda_cartera_total |
| `TE_Invex_Sistema.xlsx` | tasa_sistema, tasa_invex_consumo |
| `CorporateLoan_CNBVDB.csv` | tasa_mn, tasa_me |
| `Instituciones.xlsx` | código → nombre (→ `bank_dim_institucion`) |
| `040_TO.csv` (vía AG transform) | cartera_total multi-banco, icap, imor, imora |
| `sh_datos_40.csv` (concepto 40100200, saldo=130) | entidades_gubernamentales_total |

> **Nota**: `cartera_comercial_sin_gob = cartera_comercial_total - entidades_gubernamentales_total`.
> La fuente de `entidades_gubernamentales_total` es Banca Múltiple (`sh_datos_40.csv`), NO Análisis General.

### Tablas Fact (Métricas Financieras — BE_BM workbook)

| Hoja del workbook `BE_BM_*.xlsx` | Tabla Destino | Campo(s) |
|----------------------------------|---------------|----------|
| Pm2 | `bank_fact_metricas_financieras` | activo_total, captacion, capital_contable, resultado_neto |
| Indicadores | `bank_fact_metricas_financieras` | roa_12m, roe_12m |
| CCT | `bank_fact_metricas_financieras` | imor, icor, perdida_esperada |
| 15 segments | `bank_fact_cartera_segmentada` | cartera por segmento (15 tipos) |

### IMOR Comercial (Loader Dedicado)

| Fuente | Campo(s) | Loader |
|--------|----------|--------|
| `CNBV_Cartera_Bancos_V2.xlsx` + `Castigos Comerciales.xlsx` | `imor_comercial`, `cvc_cc` | `loaders_imor_comercial.py` |

Calcula IMOR comercial sin gobierno (`cartera_vencida_SG / cartera_total_SG`) y CVC (`castigos / cartera_total_SG`).
Usa `ON CONFLICT (banco_norm, fecha) DO UPDATE`.

## Tablas de Dimensiones

| Fuente | Tabla | Registros | Notas |
|--------|-------|-----------|-------|
| `Instituciones.xlsx` + SQL | `bank_dim_institucion` | 124 | 10-digit CNBV codes |
| Migración `021_bank_dim_periodo.sql` | `bank_dim_periodo` | 372 | Generado 2000-2030 |
| `catalogs/inegi_entidades_municipios.xlsx` + SQL | `bank_dim_estado` | 40 | 32 estados + especiales |
| `catalogs/scian_estructura2023.xlsx` | `bank_dim_actividad_economica` | 24 | SCIAN sectors |
| Migraciones SQL | `bank_dim_moneda` | 3 | MXN, UDIS, Extranjera |
| Migraciones SQL | `bank_dim_sector` | 3 | Banca Múltiple/Desarrollo/SOFOM |
| Migraciones SQL | `bank_dim_apoyo` | 2 | Tipos de apoyo |
| Migraciones SQL | `bank_dim_destino_credito` | 28 | Destinos crediticios |
| Migraciones SQL | `bank_dim_tipo_cartera` | 4 | Empresas/Gobierno/etc. |
| Migraciones SQL | `bank_dim_tamano_empresa` | 5 | MiPyMEs + Grande + Fideicomiso |
| `BE_BM_*.xlsx` segments | `bank_dim_segmento_cartera` | 15 | Auto-populated from ETL |

## Materialized Views

Las MVs se derivan de fact + dim via `bank_mv_refresh_all()`.

| MV | Se genera de | Propósito |
|----|-------------|-----------|
| `bank_mv_ranking_cartera_mensual` | `kpis_mensual` × `institucion` | Top N bancos por cartera |
| `bank_mv_evolucion_cartera_banco` | `cartera_comercial` × dims | Serie temporal por banco |
| `bank_mv_cartera_por_estado` | `cartera_comercial` × `estado` | Distribución geográfica |
| `bank_mv_cartera_por_actividad` | `cartera_comercial` × `actividad_economica` | Distribución por sector |
| `bank_mv_cartera_por_tamano` | `cartera_comercial` × `tamano_empresa` | MiPyMEs vs Grande |
| `bank_mv_cartera_por_destino` | `cartera_comercial` × `destino_credito` | Por tipo de crédito |
| `bank_mv_cartera_tdc` | `cartera_comercial` × `tipo_cartera` | Por tipo de cartera |
| `bank_mv_comparativa_bancos` | `kpis_mensual` | Comparación multi-banco |
| `bank_mv_resumen_sistema` | `kpis_mensual` (SISTEMA) | Agregado del sistema |
| `bank_mv_metricas_financieras` | `metricas_financieras` | ROA/ROE/ICOR consolidado |
| `bank_mv_vivienda_por_perfil` | `cartera_vivienda` | Perfil demográfico |
| `bank_mv_vivienda_por_producto` | `cartera_vivienda` | Por producto hipotecario |

## Scripts R de Bajaware (Legacy)

| Script R | Equivalente Python | Estado |
|----------|--------------------|--------|
| `CorporateLoan_BM.R` | `loaders_unified.py:load_corporate_loan()` | Reemplazado — Python no hardcodea fechas |
| `Castigos_BM.R` | `bank_view_castigos_comerciales` (migración 060) | Reemplazado — vista SQL sobre R04A con los 13 conceptos |

---

# Gotchas Conocidos

> Base de conocimiento consolidada. Categorizados por tema para localización rápida.
> Para procedimientos operativos, ver [`etl_runbook.md`](etl_runbook.md).

## Índice de Síntomas → Solución

| Síntoma que ves | Causa probable | Sección |
|-----------------|---------------|---------|
| Cartera de INVEX/BBVA/etc. ~1000× menor que peers | Meses sin cobertura AG, datos legacy sin corregir | [§1 Escala](#factores-de-corrección-para-meses-legacy-only) |
| ICAP de banco dual-source aparece como 0.15 en vez de 15 | `ICAP_Bancos.xlsx` almacena ratio decimal; `merge_icap()` no normaliza | [§1 Escala](#icap-de-icap_bancosxlsx-en-escala-decimal) |
| Spike en Ene 2023: valor ~2× del esperado | Legacy + AG se sumaron en vez de AG reemplazar legacy | [§1 Escala](#spike-enero-2023-patrón-de-duplicación-legacyag) |
| `etapa_3` ≠ `cartera_vencida` (está ÷1000) | Concepto AG 40100341 mapea a `cartera_vencida`, no a `etapa_3` | [§1 Escala](#cartera_total_etapa_3-nunca-actualizada-por-ag) |
| `etapa_1` pre-2022 con valores incoherentes | Datos legacy pre-IFRS9, no representan etapas reales | [§1 Escala](#etapa_1-pre-2022-datos-pre-ifrs9) |
| ICAP/TDA de INVEX es NULL | Código 040059 no matchea con 040131 en merge | [§2 Código INVEX](#2-código-de-institución-invex-040059-vs-040131) |
| tasa_mn / tasa_me de INVEX = 0 o NULL | Cadena de 4 bugs en merge CorporateLoan | [§3 Tasas](#3-tasa_mn--tasa_me-cadena-de-4-bugs--corregido-2026-03-03) |
| Datos existen en BD pero no aparecen en frontend | `periodo_id` es NULL → filtro SQL los excluye | [§4 periodo_id](#4-periodo_id-y-pipeline-legacy) |
| Join legacy↔AG produce 0 registros silenciosamente | Tipo `Date` vs `Datetime` en columna `fecha` | [§5 Fecha type](#5-merge-legacyag-tipo-de-fecha) |
| Nov 2025 = Oct 2025 (valores idénticos) | Datos de origen duplicados por Bajaware | [§6 Calidad](#nov-2025--oct-2025-en-cnbv_cartera) |
| `cartera_consumo_total` siempre 0 | Pipeline Legacy no calcula esta métrica (solo AG) | [§6 Calidad](#cartera_consumo_total--0-en-pipeline-legacy) |
| `ON CONFLICT` falla en upsert | Falta unique index `uq_kpis_banco_fecha` | [§7 Constraints](#unique-constraint-para-upsert) |
| ETL muere con exit 137 (OOM) | AG + CorporateLoan consume >2 GB RAM | [§7 Constraints](#oom-con-analisisgeneral) |
| Datos de Ahorro Famsa (~39% tasa) contaminan INVEX | CorporateLoan CSV tiene ambas instituciones con código 040131 | [§2 CorporateLoan](#corporateloan-colisión-ahorro-famsa) |
| `market_share_pct` no se calcula | ETL ejecutado sin AnalisisGeneral | [§7 Constraints](#oom-con-analisisgeneral) |
| Solo 7 bancos después del ETL (faltan AFIRME, BAJIO, etc.) | ETL legacy sin AG produce solo bancos del CNBV Excel | [§1 Escala](#escala-legacy-vs-análisis-general) |
| Quebrantos T1 2025: BD muestra 31 MDP en vez de 53 MDP | Se cargó desde `Castigos Comerciales.xlsx` (acumulados) en vez de `CASTIGOS.xlsx` (flujos) | [§8 Castigos](#8-castigos-dos-fuentes-dos-semánticas-corregido-2026-03-04) |
| 4 bancos sin quebrantos históricos (MONEX, MIFEL, AFIRME, BANCO BASE) | ETL `load_castigos()` no insertaba todos los bancos de `CASTIGOS.xlsx` | [§8 Castigos](#8-castigos-dos-fuentes-dos-semánticas-corregido-2026-03-04) |
| ICAP/ICOR devuelve solo INVEX en comparación multi-banco Dic 2025 | Pipeline ICAP_Bancos.xlsx no procesó Dic 2025 para 9 bancos | [§9 Gaps Dic 2025](#9-gaps-de-datos-dic-2025-corregido-2026-03-04) |
| 5 bancos sin cartera en comparación Dic 2025 (BANCREA, BANSI, MULTIVA, SABADELL, VPM) | Pipeline AG no cargó Dic 2025 para 5 bancos | [§9 Gaps Dic 2025](#9-gaps-de-datos-dic-2025-corregido-2026-03-04) |
| Tasa MN/ME diverge de PPT del cliente (0.07–1.07pp) | CSV `backfill_tasas.py` apuntaba a versión Feb 12 (sin Dic 2025) | [§10 CSV version gap](#10-csv-version-gap-tasas-dic-2025--corregido-2026-03-04) |

---

## 1. Unidades y Escala

### Convenciones de la BD

| Tipo de métrica | Unidad en BD | Ejemplo |
|-----------------|-------------|---------|
| Cartera (total, vencida, etapas, comercial) | Pesos | 49,754,432,341 |
| ICAP | Porcentaje | 15.76 = 15.76% |
| IMOR / IMORA | Decimal (ratio) | 0.0225 = 2.25% |
| Tasas (tasa_mn, tasa_me) | Decimal (ratio) | 0.093 = 9.3% |
| market_share_pct | Porcentaje | 0.64 = 0.64% |

### Escala Legacy vs Análisis General

Dos pipelines alimentan `bank_fact_kpis_mensual` con **escalas diferentes**:

| Pipeline | Fuente | Cartera | ICAP | IMOR/IMORA | Bancos |
|----------|--------|---------|------|------------|--------|
| **Legacy** | `CNBV_Cartera_Bancos_V2.xlsx` | MDP (×1000 insuf.) | Decimal (0.15) | — | 7 |
| **Análisis General** | `040_TO.csv` | Pesos | Porcentaje (15.76) | Porcentaje → ÷100 | 18+ |

- `load_cnbv_cartera()` aplica ×1,000 al Excel MDP — insuficiente, queda ×1,000 menor que pesos
- `transform_analisis_general_to_kpis()` solo normaliza IMOR/IMORA (÷100 → decimal)
- Cartera e ICAP de AG pasan sin cambio (ya están en la convención de BD)
- **NUNCA dividir cartera ÷1000 ni ICAP ÷100** — rompe la escala de los 18 bancos AG

### 6 bancos dual-source

INVEX, BBVA, BANORTE, SANTANDER, HSBC y CITIBANAMEX existen en **ambos** pipelines.
AG tiene prioridad en el merge. **Orden de ejecución obligatorio**:

```
1. Legacy (7 bancos, escala incorrecta)
2. AG upsert (18+ bancos, sobreescribe legacy para meses cubiertos)
3. Fix manual SQL para meses sin cobertura AG
```

**Ejecutar legacy solo (sin AG después) deja valores ×1,000 menores.**

### ICAP de ICAP_Bancos.xlsx en escala decimal

`ICAP_Bancos.xlsx` almacena ICAP como **ratio decimal** (0.1576) para TODAS las instituciones.
`merge_icap()` pasa el valor sin normalizar. Para bancos AG-only esto no importa (AG produce
ICAP en porcentaje y AG tiene prioridad en el merge). Pero para los 6 dual-source + SISTEMA,
el ICAP queda en decimal porque `merge_icap()` se aplica después del merge legacy↔AG.

**Bancos afectados**: INVEX, BBVA, BANORTE, SANTANDER, HSBC, CITIBANAMEX (108 meses c/u),
SISTEMA (69 meses, 2017-01 a 2022-09).

**Fix DB (2026-03-03)**: `UPDATE SET icap_total = icap_total * 100 WHERE icap_total < 1` — 717 filas.

**Fix código pendiente**: `merge_icap()` en `transforms.py` debería multiplicar ×100 al cargar
desde ICAP_Bancos.xlsx, o normalizar post-merge para que la convención de BD (porcentaje) se cumpla.

### Factores de corrección para meses legacy-only

Cuando AG no cubre un mes, o cuando un ETL legacy sobreescribe datos AG con `--upsert`,
los 6 bancos dual-source + SISTEMA quedan en escala legacy. Factores para fix manual:

| Columna | Factor | Razón |
|---------|--------|-------|
| `cartera_total`, `_vencida`, `_etapa_1`, `_etapa_2`, `_consumo`, `_vivienda` | ×1,000 | MDP×1000 → pesos |
| `cartera_comercial_total`, `cartera_comercial_sin_gob` | ×1,000,000 | MDP (×1000 sobre miles) → pesos |
| `icap_total` | ×100 | Decimal (0.15) → porcentaje (15.0) |

**Método preferido**: En lugar de multiplicar por factores, restaurar directamente desde
`bank_src_analisis_general` usando el concepto AG correspondiente (ver tabla abajo).
Los factores son un fallback para cuando no hay datos AG disponibles.

| Columna kpis | Concepto AG | Disponible desde |
|-------------|-------------|-----------------|
| `cartera_total` | 40100185 | 200012 |
| `cartera_vencida` | 40100341 | 200012 |
| `cartera_comercial_total` | 40100186 | 200012 |
| `cartera_vivienda_total` | 40100217 | 200012 |
| `cartera_consumo_total` | 40100206 | 200012 |
| `cartera_total_etapa_1` | 40100263 | **202201** (IFRS9) |
| `cartera_total_etapa_2` | 40100302 | **202201** (IFRS9) |

**Restauración desde AG** (ejemplo para INVEX cartera_vencida):
```sql
UPDATE bank_fact_kpis_mensual k
SET cartera_vencida = ag.importe
FROM bank_src_analisis_general ag
WHERE k.banco_norm = 'INVEX'
  AND ag.institucion = '040059'
  AND ag.concepto = 40100341
  AND ag.periodo = TO_CHAR(k.fecha, 'YYYYMM')
  AND k.fecha < '2022-01-01';
```

**Detección automática**:
```sql
-- Bancos con cartera sospechosamente baja
SELECT banco_norm, COUNT(*)
FROM bank_fact_kpis_mensual
WHERE banco_norm IN ('INVEX','BBVA','BANORTE','SANTANDER','HSBC','CITIBANAMEX','SISTEMA')
  AND cartera_total > 0
  AND cartera_total < CASE
    WHEN banco_norm = 'SISTEMA' THEN 100e9
    WHEN banco_norm = 'INVEX' THEN 500e6
    ELSE 10e9 END
GROUP BY banco_norm;
```

### Spike Enero 2023: patrón de duplicación legacy↔AG

En Ene 2023 (y posiblemente otros meses), los valores de INVEX se **duplican** (exactamente 2×)
porque tanto el pipeline legacy como AG escriben al mismo row y sus valores se suman en vez
de AG reemplazar a legacy.

**Columnas afectadas**: `cartera_total`, `cartera_comercial_total`, `cartera_vivienda_total`,
`cartera_vencida`, `cartera_total_etapa_1`, `cartera_total_etapa_2`.

**Detección**: Comparar kpis vs AG source:
```sql
SELECT k.fecha, k.cartera_total, ag.importe as ag_total,
       (k.cartera_total / ag.importe)::numeric(10,2) as ratio
FROM bank_fact_kpis_mensual k
JOIN bank_src_analisis_general ag
  ON ag.institucion = '040059' AND ag.concepto = 40100185
  AND ag.periodo = TO_CHAR(k.fecha, 'YYYYMM')
WHERE k.banco_norm = 'INVEX'
  AND (k.cartera_total / ag.importe)::numeric(10,2) > 1.5;
```

**Fix**: Restaurar el valor correcto desde AG source para cada columna afectada.

### cartera_total_etapa_3 nunca actualizada por AG

El concepto AG `40100341` (NPL/cartera etapa 3) se mapea a `cartera_vencida` en
`ANALISIS_GENERAL_CONCEPT_MAP`, **NO** a `cartera_total_etapa_3`. Por lo tanto,
`etapa_3` retiene siempre el valor legacy (= `cartera_vencida / 1000`).

**Fix DB (2026-03-03)**: `SET cartera_total_etapa_3 = cartera_vencida` — 107 filas INVEX.

**Fix código pendiente**: Agregar `etapa_3 = cartera_vencida` post-merge en el ETL,
o mapear concepto 40100341 también a `cartera_total_etapa_3`.

### etapa_1 pre-2022: datos pre-IFRS9

Los conceptos AG para etapas IFRS9 (40100263, 40100302) solo existen desde **Ene 2022**.
Los valores de `cartera_total_etapa_1` pre-2022 vienen del legacy y representan un concepto
diferente (no etapas IFRS9). Multiplicar ×1000 produce valores > cartera_total para 2017-2019.

**Estado**: No corregidos. Los valores pre-2022 no tienen equivalente IFRS9 real.

### cartera_comercial_sin_gob en escala MDP

`cartera_comercial_sin_gob` se computa como `cartera_comercial_total - entidades_gubernamentales_total`
en `transforms.py:981`. Para bancos dual-source, ambas fuentes están en MDP → el resultado
queda en MDP. No hay concepto AG para esta columna, solo se puede corregir con ×1,000,000.

**Fix DB (2026-03-03)**: ×1M para INVEX (108 filas) + 5 bancos grandes (539 filas) + ÷2 spike Ene 2023.

## 2. Código de Institución INVEX (040059 vs 040131)

- `Instituciones.xlsx` usa `040059` — **código correcto de INVEX** (Banxico CEP + SAT)
- `040131` es **Banco Ahorro Famsa** (revocado 2020), NO INVEX
- `enrich_with_instituciones()` remapea `040059` → `040131` (compatibilidad histórica con ICAP/TDA)
- **Todos los merges** deben remapear `040059` → `040131` en su fuente antes del join
- Fix aplicado en: `merge_icap()`, `merge_tda()`, `merge_corporate_rates()` (`transforms.py`)

### CorporateLoan: colisión Ahorro Famsa

El CSV `CorporateLoan_CNBVDB.csv` contiene datos reales de Ahorro Famsa con código `040131`.
Si se remapea `040059 → 040131` sin filtrar primero, los datos de INVEX se mezclan con Famsa.

**Fix (2026-03-03)**: `merge_corporate_rates()` filtra registros de Ahorro Famsa **antes**
del remap, usando un snapshot de fechas pre-revocación como heurística.

## 3. tasa_mn / tasa_me (cadena de 4 bugs — corregido 2026-03-03)

El CSV `CorporateLoan_CNBVDB.csv` tiene **13,543 registros válidos** de INVEX (Jun 2016 – Dic 2025),
pero la tasa aparecía como 0/NULL en la BD. Fue una cadena de 4 bugs:

| # | Bug | Causa | Fix |
|---|-----|-------|-----|
| 1 | **Merge collision** | Join con código remapeado matcheaba Ahorro Famsa (~39%) en vez de INVEX (~13%) | Filtrar Famsa + remap en `merge_corporate_rates()` |
| 2 | **mean() vs weighted avg** | `mean()` ignora tamaño de cartera; Bajaware usa `Tasa_ponderada` | Cambiar a weighted avg por `Total Portfolio` en `load_corporate_loan()` |
| 3 | **Aggregation 0/0 = NaN** | `Σ(tasa×cartera)/Σ(cartera)` = NaN cuando `cartera_total = 0` (INVEX 2017-2021) | Fallback a `mean()` cuando denominador = 0 en `_build_aggregation_expressions()` |
| 4 | **periodo_id NULL** | ETL manual no pobla `periodo_id` → frontend filtra `WHERE periodo_id >= :pstart` → datos invisibles | Asegurar `periodo_id = YYYYMM` post-upsert (ver § periodo_id) |

### Detalle técnico del weighted avg

CorporateLoan tiene ~170 filas por banco/mes (estado × tamaño). Se agrega con:
`Σ(tasa × Total_Portfolio) / Σ(Total_Portfolio)` — consistente con Tableau `Tasa_ponderada`.

Requiere `schema_overrides={"Total Portfolio": pl.Utf8}` porque `scan_csv` con `ignore_errors=True`
descartaba valores con comas (ej. "393,968") silenciosamente.

## 4. periodo_id y pipeline Legacy

- `periodo_id` (FK a `bank_dim_periodo`, formato YYYYMM) es **requerido** por el frontend
- `peer_average.py` filtra con `kpi.periodo_id >= :pstart` — `NULL` nunca pasa este filtro
- `db_writer_3nf.py` lo popula automáticamente desde `fecha` via la dimensión
- **ETL manual o upsert directo**: `periodo_id` queda NULL → datos invisibles
- **Siempre verificar post-ETL**:
  ```sql
  SELECT COUNT(*) FROM bank_fact_kpis_mensual WHERE periodo_id IS NULL;
  ```
- **Fix de emergencia**:
  ```sql
  UPDATE bank_fact_kpis_mensual
  SET periodo_id = EXTRACT(YEAR FROM fecha)::int * 100 + EXTRACT(MONTH FROM fecha)::int
  WHERE periodo_id IS NULL;
  ```

## 5. Merge legacy↔AG: tipo de fecha

- Legacy produce `fecha` como `Date`, AG produce `Datetime`
- Sin cast, el join falla silenciosamente (capturado por try-except)
- Fix: cast `fecha` al tipo del otro lado antes del join en `transforms.py` y `transforms_pipeline.py`

## 6. Calidad de Datos de Origen

### Nov 2025 = Oct 2025 en CNBV_Cartera

Entrega `drive-download-20260302T184043Z-1-001`: **58 instituciones × 35 columnas numéricas**
son 100% idénticas entre Oct y Nov 2025. Dic 2025 sí tiene valores distintos y legítimos.

Esto es un problema de datos de origen (Bajaware), no del ETL.
Pendiente: solicitar datos reales de Nov a Bajaware.

### cartera_consumo_total = 0 en pipeline Legacy

El pipeline Legacy no calcula `cartera_consumo_total` — solo AG la produce.
Para meses sin cobertura AG, esta métrica será 0 para bancos dual-source.
No hay fix manual posible sin datos AG.

## 7. Constraints Técnicos

### Unique constraint para UPSERT
- `bank_fact_kpis_mensual` requiere `UNIQUE INDEX uq_kpis_banco_fecha ON (banco_norm, fecha)`
- Creado 2026-03-02; si se recrea la tabla, **recrear el index**

### OOM con AnalisisGeneral
- ETL Unificado + AG consume >2 GB RAM → OOM (exit 137) en WSL
- Sin AG: produce ~7 bancos pero preserva los otros con `--upsert`
- `market_share_pct` depende de AG (necesita SISTEMA con cartera_total del mes)

### Particiones por año
Las tablas particionadas necesitan particiones creadas manualmente para años nuevos.
Ver `etl_runbook.md` → Troubleshooting § Particiones.

## 8. Castigos: dos fuentes, dos semánticas (corregido 2026-03-04)

Existen **dos archivos** de castigos comerciales en las entregas de Bajaware:

| Archivo | Columna clave | Semántica | Valores | Uso en ETL |
|---------|---------------|-----------|---------|------------|
| `CASTIGOS.xlsx` | `LIB_CASTIGOS_COMERC` | Flujo mensual bruto (castigos liberados) | Siempre ≥ 0 | `load_castigos()` → `quebrantos_comerciales` |
| `Castigos Comerciales.xlsx` | `CASTIGOS ACUMULADOS COMERCIAL` | Acumulado anual | Se resetea en Enero, puede decrecer (reversiones) | `load_castigos_comerciales()` → `castigos_acum_comercial` + IMOR Comercial |

### Por qué importa

Si se calcula `delta_mensual = acum[mes] - acum[mes-1]` sobre `Castigos Comerciales.xlsx`,
los deltas pueden ser **negativos** (reversiones contables). Estos negativos reducen los totales
trimestrales significativamente:

| Métrica T1 2025 | CASTIGOS.xlsx (flujos) | Castigos Comerciales.xlsx (deltas positivos) | Castigos Comerciales.xlsx (deltas netos) |
|-----------------|------------------------|----------------------------------------------|------------------------------------------|
| Grupo peer (10 bancos) | **51.06 MDP** | 30.70 MDP | 18.87 MDP |
| MIFEL | 37.33 MDP | 18.37 MDP | 15.51 MDP |

### Regla

- `quebrantos_comerciales` en `bank_fact_kpis_mensual` → siempre desde `CASTIGOS.xlsx`
- `Castigos Comerciales.xlsx` solo se usa para `imor_comercial` (CVC = castigos / cartera) y `castigos_acum_comercial`
- **Nunca** usar deltas de acumulados para poblar `quebrantos_comerciales`

### Códigos de institución

- `CASTIGOS.xlsx` usa códigos de 6 dígitos: `040059` (INVEX), `040112` (MONEX)
- `bank_dim_institucion.clave_cnbv` usa 10 dígitos: `0000040059`
- Mapeo: `clave_cnbv.lstrip("0").zfill(6)` → código Excel

### Fix DB (2026-03-04)

1652 rows actualizadas desde `CASTIGOS.xlsx` (46 bancos × ~36 meses promedio).
Solo `UPDATE WHERE quebrantos_comerciales IS NULL OR = 0` (no sobreescribe datos existentes).
Backup: `bank_fact_kpis_mensual_qc_bak_20260304`.

## 9. Gaps de datos Dic 2025 (corregido 2026-03-04)

El cliente Invex reportó 7 thumbs-down al usar comparaciones multi-banco con barras horizontales.
La investigación reveló que **5 de 7 bugs eran gaps de datos ETL**, no bugs de código.

### Tabla resumen de gaps por métrica y grupo de bancos

| Métrica | INVEX | AFIRME, BASE, MIFEL, MONEX | BANCREA, BANSI, MULTIVA, SABADELL, VPM |
|---------|-------|---------------------------|---------------------------------------|
| ICAP | Dic 2025 ✅ (16.38) | **Nov 2025** (último) | **Nov 2025** (último) |
| ICOR | Dic 2025 ✅ (2.37) | **Nov 2025** (último) | **Nov 2025** (último) |
| Cartera | Dic 2025 ✅ | Dic 2025 ✅ | **Nov 2025** (último) |
| sin_gob / eg | Dic 2025 ✅ | Dic 2025 ✅ | **NULL** |
| Tasa MN | Dic 2025 ✅ | Dic 2025 ✅ | Dic 2025 ✅ |
| Tasa ME | Dic 2025 ✅ | Dic 2025 ✅ | Dic 2025 ✅ (excepto BANSI: Jun 2022) |

### Root cause

1. **ICAP/ICOR (9 bancos)**: El pipeline `ICAP_Bancos.xlsx` no procesó Dic 2025 para los 9 bancos peer.
   INVEX tenía datos porque su ICAP viene de un pipeline separado (institution code 040131).
2. **Cartera (5 bancos AG-only)**: El pipeline Análisis General (`040_TO.csv`) no cargó Dic 2025
   para BANCREA, BANSI, MULTIVA, SABADELL y VE POR MAS.
3. **sin_gob / eg (5 bancos AG-only)**: `entidades_gubernamentales_total` viene de `sh_datos_40.csv`
   (concepto 40100200, saldo=130). No cargada en el ETL anterior para estos 5 bancos.
4. **BANSI tasa_me**: Último dato Jun 2022 — gap histórico genuino, no bug de ETL.

### Fixes aplicados (UPDATEs quirúrgicos)

**ICAP** — 9 bancos actualizados directamente desde `ICAP_Bancos.xlsx` (valor decimal × 100):

| Banco | icap_total Dic 2025 |
|-------|---------------------|
| AFIRME | 14.39 |
| BANCO BASE | 14.59 |
| BANCREA | 18.45 |
| BANSI | 37.21 |
| MIFEL | 13.28 |
| MONEX | 21.85 |
| MULTIVA | 14.72 |
| SABADELL | 44.24 |
| VE POR MAS | 16.81 |

**ICOR** — 9 bancos, calculado como `reservas_etapa_todas / cartera_vencida` desde CNBV:

| Banco | icor Dic 2025 |
|-------|---------------|
| AFIRME | 1.52 |
| BANCO BASE | 1.40 |
| BANCREA | 0.73 |
| BANSI | 0.87 |
| MIFEL | 1.42 |
| MONEX | 1.80 |
| MULTIVA | 1.56 |
| SABADELL | 2.25 |
| VE POR MAS | 0.81 |

**Cartera** — 5 bancos AG-only cargados desde `CNBV_Cartera_Bancos_V2.xlsx` (MDP × 1e6 → pesos):

| Banco | cartera_total (B) | cartera_vencida (B) | cartera_comercial_total (B) |
|-------|-------------------|---------------------|-----------------------------|
| BANCREA | 41.59 | 0.66 | 41.59 |
| BANSI | 29.63 | 0.73 | 29.63 |
| MULTIVA | 93.36 | 0.81 | 93.36 |
| SABADELL | 107.41 | 0.15 | 107.41 |
| VE POR MAS | 53.66 | 0.59 | 53.66 |

**sin_gob / eg** — 5 bancos cargados desde `sh_datos_40.csv` (concepto 40100200, saldo=130):

| Banco | eg_total (B) | sin_gob (B) |
|-------|-------------|-------------|
| BANCREA | 2.18 | 39.41 |
| BANSI | 10.16 | 19.47 |
| MULTIVA | 26.76 | 66.60 |
| SABADELL | 4.86 | 102.55 |
| VE POR MAS | 4.84 | 48.82 |

**Extras**: Etapa 3, reservas, INVEX `institucion_id` NULL → 31 (301 filas).

**MVs refrescadas**: `bank_mv_refresh_all()` post-fix.

### BANSI tasa_me — gap histórico

BANSI dejó de reportar `tasa_me` en Jun 2022. Es un gap genuino de la fuente CNBV,
no un bug del ETL. En gráficas multi-banco de tasa ME, BANSI aparecerá en la tabla
de texto pero no en la barra (dato NULL).

## 10. CSV version gap (tasas Dic 2025) — corregido 2026-03-04

### El patrón "CSV version gap"

El script `backfill_tasas.py` apuntaba al CSV `CorporateLoan_CNBVDB.csv` de la entrega
**Feb 12** (`drive-download-20260212T`). Esta versión NO contenía datos de Dic 2025.

Solo la entrega **Mar 2** (`drive-download-20260302T`) incluye Dic 2025 con valores
de promedio ponderado por portafolio (consistentes con la PPT del cliente Invex).

### Discrepancias corregidas (5 UPDATEs)

| Banco | Moneda | Columna | BD anterior | CSV correcto (Mar 2) | Delta |
|-------|--------|---------|-------------|----------------------|-------|
| BANCO BASE | ME | tasa_me | 0.0699 | 0.0688 | -0.11pp |
| BANCO BASE | MN | tasa_mn | 0.1044 | 0.1037 | -0.07pp |
| BANCREA | ME | tasa_me | 0.0858 | 0.0751 | -1.07pp |
| INVEX | ME | tasa_me | 0.0826 | 0.0808 | -0.18pp |
| MONEX | ME | tasa_me | 0.0649 | 0.0642 | -0.07pp |

### Valores que ya eran correctos (14)

AFIRME MN/ME, BANSI MN, MIFEL MN/ME, MULTIVA MN/ME, SABADELL MN/ME,
VE POR MAS MN/ME, INVEX MN, MONEX MN, BANCREA MN.

### Validación

- CSV Mar 2 coincide exactamente con PPT del cliente (delta <0.01pp).
- Post-fix: bot devuelve valores con **delta = 0.0000pp** vs CSV.
- 27/27 E2E replay checks passed (ver `tests/e2e/charts/test_feedback_replay_2026_03_04.py`).

### Prevención

Al ejecutar `backfill_tasas.py` o cualquier script de backfill, **siempre verificar que el CSV
apunta a la entrega más reciente**. Patrón de detección:

```sql
-- Verificar que Dic 2025 existe en la BD
SELECT banco_norm, tasa_mn, tasa_me
FROM bank_fact_kpis_mensual
WHERE fecha = '2025-12-01'
  AND banco_norm IN ('INVEX','BANCO BASE','BANCREA','MONEX')
ORDER BY banco_norm;
```

Si los valores no coinciden con la PPT del cliente, la causa más probable es un CSV desactualizado.
