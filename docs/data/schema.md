# Catálogo del Esquema — bankadvisor (PostgreSQL @ GCP)

> Snapshot: 2026-03-04 | Host: ${PROD_DB_HOST}:5432 | DB: bankadvisor | Size: ~6 GB

**Docs relacionados**:
- [`source_mapping.md`](source_mapping.md) — Qué archivo alimenta cada tabla + gotchas conocidos
- [`etl_runbook.md`](etl_runbook.md) — Cómo ejecutar el ETL paso a paso + troubleshooting operativo

## Resumen

| Categoría | Prefijo | Tablas | Registros Totales | Tamaño |
|-----------|---------|--------|-------------------|--------|
| Dimensiones | `bank_dim_*` | 11 | ~620 | ~200 KB |
| Hechos | `bank_fact_*` | 6 | ~5.72M | ~3.86 GB |
| Sources | `bank_src_*` | 6 (+56 particiones) | ~27.96M | ~1.85 GB |
| Materialized Views | `bank_mv_*` | 13 | N/A | ~25 MB |
| Views | `bank_view_*`, legacy | 10 | N/A | 0 |
| ETL Control | `bank_etl_*` | 3 | ~100 | ~40 KB |
| Otros | `bm_*`, `etl_runs`, `query_logs` | 4 | ~10K | ~8 MB |

## Cobertura Temporal

| Tabla | Min Periodo | Max Periodo | Gap vs Hoy |
|-------|------------|------------|------------|
| `bank_src_analisis_general` | 200012 | 202510 | ~5 meses |
| `bank_src_banca_multiple` | 200012 | **202512** | ~3 meses |
| `bank_fact_cartera_comercial` | 201606 | 202510 | ~5 meses |
| `bank_fact_cartera_vivienda` | 201901 | 202510 | ~5 meses |
| `bank_src_reporte_r04a` | 202201 | **202512** | ~3 meses |
| `bank_src_reporte_r12a` | 202201 | 202510 | ~5 meses |
| `bank_src_benchmark_analitica` | 201701 | 202511 | ~4 meses |
| `bank_src_tda_etapas` | 200012 | 202511 | ~4 meses |
| `bank_fact_kpis_mensual` | 2000-12 | **2025-12** | ~3 meses |
| `bank_fact_metricas_financieras` | 2024-09 | 2025-09 | ~6 meses |
| `bank_fact_cartera_segmentada` | 2024-09 | 2025-09 | ~6 meses |

> **Nota (2026-03-04)**: `bank_fact_kpis_mensual` ahora tiene Dic 2025 completo para los **10 bancos peer**
> (INVEX, AFIRME, BANCO BASE, BANCREA, BANSI, MIFEL, MONEX, MULTIVA, SABADELL, VE POR MAS)
> incluyendo ICAP, ICOR, cartera, cartera_comercial_sin_gob, tasa_mn y tasa_me.
> Excepción: BANSI `tasa_me` = NULL (gap genuino desde Jun 2022).
> Ver [`source_mapping.md` § Gaps Dic 2025](source_mapping.md#9-gaps-de-datos-dic-2025-corregido-2026-03-04).

## Diagramas

- **Diagrama ER**: [`er_diagram.mermaid`](er_diagram.mermaid)
- **Flujo ETL**: [`etl_flow.mermaid`](etl_flow.mermaid)
- **Mapeo fuente→tabla**: [`source_mapping.md`](source_mapping.md)

## Tablas de Dimensiones

### bank_dim_institucion (124 rows)
Fuente única de verdad para instituciones financieras.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `institucion_id` | SERIAL PK | Surrogate key para JOINs |
| `clave_cnbv` | VARCHAR(20) UK | Código oficial CNBV (10 dígitos, ej: 0000040059) |
| `nombre_corto` | VARCHAR(100) | Nombre normalizado (BBVA, INVEX, BANORTE) |
| `nombre_completo` | VARCHAR(300) | Nombre legal completo |
| `tipo_institucion` | VARCHAR(100) | Banca Múltiple, Banca Desarrollo, SOFOM |
| `sector_cnbv` | VARCHAR(10) | Código de sector (40, 37, 68) |
| `activo` | BOOLEAN | Institución vigente |

Referenciada por: 6 tablas fact (FK `institucion_id`).

### bank_dim_periodo (372 rows)
Dimensión temporal pre-generada 2000-2030.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `periodo_id` | INT PK | Formato YYYYMM (202501 = enero 2025) |
| `fecha` | DATE | Primer día del mes |
| `anio` | SMALLINT | Año |
| `mes` | SMALLINT | Mes (1-12) |
| `trimestre` | SMALLINT | Q1-Q4 |
| `semestre` | SMALLINT | S1-S2 |
| `periodo_str` | VARCHAR(6) | "202501" — para JOIN con tablas fact/src |
| `es_cierre_anual` | BOOLEAN | Diciembre |

Referenciada por: 6 tablas fact (FK `periodo_id`).

### bank_dim_estado (40 rows)
Geografía: 32 estados mexicanos + 8 entradas especiales.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `estado_id` | SERIAL PK | Surrogate key |
| `clave_estado` | VARCHAR(5) UK | Código corto (AGS, CDMX, JAL) |
| `nombre_estado` | VARCHAR(100) | Nombre completo |
| `region` | VARCHAR(50) | Norte, Centro, Sureste, etc. |
| `zona_economica` | VARCHAR(50) | Frontera Norte, Bajío, Centro, etc. |

### Otras dimensiones

| Tabla | Rows | Columnas clave |
|-------|------|---------------|
| `bank_dim_actividad_economica` | 24 | clave, nombre (SCIAN) |
| `bank_dim_moneda` | 3 | MXN, UDIS, Extranjera |
| `bank_dim_sector` | 3 | Banca Múltiple(40), Desarrollo(37), SOFOM(68) |
| `bank_dim_apoyo` | 2 | Con/Sin apoyo |
| `bank_dim_destino_credito` | 28 | Capital de trabajo, Activo fijo, etc. |
| `bank_dim_tipo_cartera` | 4 | Empresas, Gobierno, Estados, Financieras |
| `bank_dim_tamano_empresa` | 5 | Micro, Pequeña, Mediana, Grande, Fideicomiso |
| `bank_dim_segmento_cartera` | 15 | EMPRESAS, VIVIENDA, CONSUMO_TARJETA, etc. |

## Tablas de Hechos

### bank_fact_cartera_comercial (4.19M rows, 2.5 GB)
Tabla más grande — cartera comercial con desglose dimensional completo.

**PK compuesta**: sector + institución + periodo + país + estado + actividad + moneda + apoyo + destino + tipo_cartera + tamaño

**Métricas**: numero_creditos, saldo, monto_dispuesto, tasa_por_saldo, tasa_por_monto_dispuesto, plazo, etapa1/2/3, valor_razonable

**FKs**: 10 dimensiones (todas las dimensiones del modelo)

### bank_fact_kpis_mensual (11,913 rows, ~5 MB)
KPIs mensuales pre-calculados por banco. Tabla principal para consultas del chat.

**49 columnas** incluyendo: cartera_total, cartera_vencida, etapas, icap, imor, imora, tda, tasas, market_share, reservas, castigos, pe, icap_ccb/ccf

**Unique Index**: `uq_kpis_banco_fecha ON (banco_norm, fecha)` — requerido para UPSERT incremental

**Convenciones de unidades**:

| Tipo de métrica | Unidad en BD | Ejemplo |
|-----------------|-------------|---------|
| Cartera (total, vencida, etapas, comercial, consumo, vivienda) | Pesos | INVEX: 49,754,432,341 |
| ICAP | Porcentaje | 15.76 = 15.76% |
| IMOR / IMORA | Decimal (ratio) | 0.0225 = 2.25% |
| Tasas (tasa_mn, tasa_me) | Decimal (ratio) | 0.093 = 9.3% |
| market_share_pct | Porcentaje | 0.64 = 0.64% |

**Fuentes**: Dos pipelines alimentan esta tabla:
- **Legacy** (CNBV Excel `CNBV_Cartera_Bancos_V2.xlsx`): datos en MDP (millones de pesos). `load_cnbv_cartera()` aplica ×1,000 pero esto es insuficiente — los valores quedan ×1,000 menores que pesos. Produce 7 bancos. ICAP como decimal (0.15 = 15%).
- **Análisis General** (CSV `040_TO.csv`): cartera ya en pesos, ICAP como %. Solo IMOR/IMORA se normaliza (÷100 → decimal) en `transform_analisis_general_to_kpis()`. Produce 18 bancos.

**Bancos dual-source** (existen en ambos pipelines): INVEX, BBVA, BANORTE, SANTANDER, HSBC, CITIBANAMEX. Para estos, AG tiene prioridad en el merge (fix fecha type cast 2026-03-02).

**Orden de ejecución obligatorio**: Legacy → AG upsert → fix manual meses sin AG. Ejecutar legacy solo (sin AG después) deja los 7 bancos en escala ×1,000 menor.

**Cobertura temporal por fuente (entrega 2026-03-02)**:
- AG CSV: max Oct 2025 (no incluido en la entrega, versión anterior)
- Legacy Excel: max Dic 2025 (Nov = copia de Oct en origen)
- Para Dic 2025: solo 6 bancos legacy tienen datos. Peers AG-only (AFIRME, MONEX, etc.) no tienen Dic → `AVG(solo target) = target` en gráficas de promedio.

### bank_fact_metricas_financieras (162 rows, 96 KB)
Métricas del balance general y estado de resultados.

**Métricas**: activo_total, inversiones_financieras, captacion_total, capital_contable, resultado_neto, roa_12m, roe_12m, imor, icor, perdida_esperada

### bank_fact_cartera_segmentada (2,445 rows, 616 KB)
Cartera desglosada por segmento de crédito (15 tipos).

**Métricas por segmento**: cartera_total, imor, icor, perdida_esperada

## Tablas Source (Particionadas)

### bank_src_analisis_general (5.71M rows, partitioned ×26)
Reporte consolidado CNBV sector 40. Particionado `RANGE(periodo)` por año.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `sector` | VARCHAR(10) PK | Sector CNBV |
| `periodo` | VARCHAR(6) PK | YYYYMM — partition key |
| `institucion` | VARCHAR(10) PK | Código institución |
| `concepto` | BIGINT PK | Código concepto financiero |
| `importe` | NUMERIC(20,2) | Valor monetario |

### bank_src_reporte_r04a (5.84M rows, partitioned ×4)
Balance General / Estado de Resultados. Particiones: 2022-2025.

Incluye columna `moneda` (15=MXN) para filtrado de castigos.

### bank_src_tda_etapas (494K rows)
Etapas IFRS9 por subtipo de crédito. **Nota**: usa `cve_periodo` (INTEGER) en vez de `periodo` (VARCHAR).

## Migraciones

59 migraciones SQL en `plugins/bank-advisor-private/migrations/` (000-059).

Hitos clave:
- `000-003`: Schema inicial + índices
- `010-017`: Cartera comercial/vivienda, reportes regulatorios
- `020-023`: Dimensiones normalizadas (bank_dim_*)
- `025-026`: Renombre a prefijo bank_*
- `030-032`: Materialized views + funciones refresh
- `033-040`: Foreign keys + población de FKs
- `041-051`: Limpieza y optimización
- `052-059`: Benchmark, TDA, IMOR comercial, CVC

## ETL Control

| Tabla | Descripción |
|-------|-------------|
| `bank_etl_execution_log` | Log de ejecuciones ETL |
| `bank_etl_quality_metrics` | Métricas de calidad post-carga |
| `bank_etl_validation_results` | Resultados de validaciones |
| `etl_runs` | Tracking histórico de ETL runs |
| `query_logs` | Logs de queries del chatbot (RAG feedback) |
