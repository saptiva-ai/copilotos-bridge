# Research: ETL Refresh Diciembre 2025

## Entrega analizada
- Ruta: `/mnt/c/Users/Jaziel Flores/Downloads/drive-download-20260302T184043Z-1-001`
- Fecha: 2026-03-02
- Entrega anterior: `drive-download-20260212T024209Z-1-001` (periodo max: 202510-202511)

## Hallazgos clave

### 1. Datos con nuevos periodos (hasta 202512)
- **sh_datos_40.csv** — Banca Múltiple General. Archivo NUEVO en esta entrega (533 MB). Periodos hasta 202512. Antes se usaba `BancaMultipleGeneral/sh_datos_40/sh_datos_40.csv` del directorio estático.
- **040_R04A_419.csv** — Reporte R04A. Creció de 64 MB a 204 MB (+217%). Periodos hasta 202512.
- **CorporateLoan_CNBVDB.csv** — Tasas MN/ME. Creció +13 MB. Datos hasta 12/31/25.
- **ICAP_Bancos.xlsx** — ICAP total/CCB/CCF. Creció +138 KB. Probablemente incluye Dic 2025.
- **CASTIGOS.xlsx** — Quebrantos comerciales. Creció +60 KB.
- **CNBV_Cartera_Bancos_V2.xlsx** — Cartera/etapas/reservas. Creció +11 KB.

### 2. Archivos nuevos por investigar
- **FD239760.xlsx** (3.2 MB) — Nombre no reconocido, podría ser un archivo temporal o nuevo reporte.
- **Creador CorporateLoan.xlsx** / **Creador_castigos.xlsx** — Archivos "creador" que generan los CSVs finales. Útiles como referencia pero no se cargan directamente.
- **cat_conceptos_40.xlsx** — Catálogo de conceptos del sector 40. Podría servir para enriquecer queries.
- **tda IFRS9.xlsx** — TDA con desglose IFRS9. Diferente de `CREADOR DE TDA.xlsx`.
- **Nueva carpeta/** — 18 CSVs mensuales (2024-07 a 2025-12) + Script R + .RData. Output del script `Serie Historica_BM.R`.
- **castigos.csv** — CSV pequeño, posible output procesado.
- **ACTUALIZACION INVEX.pdf** — Documento descriptivo de qué incluye la actualización.

### 3. Archivos sin cambios
Los siguientes archivos son idénticos (mismo byte size): Benchmark, Castigos Comerciales, Instituciones, TDA, QUEBRANTOS, TASAS DATOS, nuevo2.

### 4. Archivos NO incluidos en esta entrega
- **040_TO.csv** (Análisis General) — NO incluido. `bank_src_analisis_general` no se puede actualizar.
- **BE_BM_*.xlsx** (workbook métricas financieras) — NO incluido. `bank_fact_metricas_financieras` y `bank_fact_cartera_segmentada` quedan en periodo max anterior.
- **Cartera Comercial/Vivienda** — NO incluidos.
- **040_R12A_*.csv** (Reporte R12A) — NO incluido.

### 5. Nota sobre el usuario
El usuario confirma que Bajaware actualizó especialmente ICAP y demás métricas. Los archivos que crecieron son consistentes con esa información.

## Estado actual de la BD (verificado 2026-03-02)

### Cobertura temporal por tabla
| Tabla | Min | Max actual | Max tras refresh |
|-------|-----|-----------|-----------------|
| `bank_src_banca_multiple` | 200012 | **202510** | 202512 |
| `bank_src_analisis_general` | 200012 | **202510** | 202510 (sin archivo) |
| `bank_src_reporte_r04a` | 202201 | **202510** | 202512 |
| `bank_src_reporte_r12a` | 202201 | **202510** | 202510 (sin archivo) |
| `bank_src_benchmark_analitica` | 201701 | **202511** | 202511 (sin cambios) |
| `bank_src_tda_etapas` | 200012 | **202511** | 202511 (sin cambios) |
| `bank_fact_kpis_mensual` | 2000-12 | **2025-11** | 2025-12 |
| `bank_fact_metricas_financieras` | 2024-09 | **2025-09** | 2025-09 (sin workbook) |
| `bank_fact_cartera_segmentada` | 2024-09 | **2025-09** | 2025-09 (sin workbook) |
| `bank_fact_cartera_comercial` | 201606 | **202510** | 202510 (sin archivo) |
| `bank_fact_cartera_vivienda` | 201901 | **202510** | 202510 (sin archivo) |

### Huecos en Nov 2025 (periodo actual más reciente)
**58 bancos** tienen fila en Nov 2025, pero con datos incompletos:

| Métrica | Bancos con dato | % cobertura | Nota |
|---------|----------------|-------------|------|
| `icap_total` | 49/58 | 84% | Parcialmente cargado |
| `imor` | **20/58** | **34%** | MUY incompleto |
| `market_share_pct` | **0/58** | **0%** | Totalmente vacío |
| `tda_cartera_total` | 28/58 | 48% | Parcialmente cargado |
| `tasa_mn` | 38/58 | 65% | Parcial |
| `icap_ccb` | 49/58 | 84% | Parcial |
| `imor_comercial` | 39/58 | 67% | Parcial |

Comparado con Oct 2025 (57 bancos):
- `imor`: 36/57 (63%) → Nov cayó a 34%
- `market_share`: 16/57 (28%) → Nov cayó a 0%
- `tda`: 37/57 (65%) → Nov cayó a 48%

**Conclusión**: Nov 2025 fue cargado parcialmente. Los nuevos archivos deberían llenar estos huecos Y agregar Dic 2025.

### INVEX específicamente (Nov 2025)
- cartera, icap, imora, tda, tasa_mn, quebrantos, castigos: **OK**
- `imor`: **NULL** (faltante)
- `market_share_pct`: **NULL** (faltante)

### SISTEMA específicamente (Nov 2025)
- cartera, imora, quebrantos, cc_sin_gob, pe_sg: **OK**
- `icap_total`: **NULL**
- `imor`: **NULL**
- `market_share_pct`: **NULL**
- `tda_cartera_total`: **NULL**
- `tasa_mn`: **NULL**
- `icap_ccb`: **NULL**

### Dic 2025 (target)
**CERO registros** en todas las tablas — nada cargado aún.

### Particiones
- Particiones 2025 **existen** para las 4 tablas particionadas
- Particiones 2026 **NO existen** (no necesarias aún — datos llegan hasta 202512)

### ETL History
Solo 2 ejecuciones registradas (Dec 2025), ambas exitosas, versión `2.0.0-unified`.

### Materialized Views (12 MVs activas)
Todas presentes. Necesitarán refresh post-carga:
- `bank_mv_comparativa_bancos`, `bank_mv_resumen_sistema` → dependen de KPIs
- `bank_mv_ranking_cartera_mensual` → depende de KPIs
- Las MVs de cartera (estado, actividad, tamaño, etc.) no cambiarán (sin nuevos datos de cartera comercial)

## Plan de acción recomendado

### Fase 1: Promover archivos
1. Copiar entrega a `incoming/drive-download-20260302T184043Z-1-001/`
2. Actualizar symlinks en `current/` para los 6 archivos que cambiaron

### Fase 2: Cargar sources (tablas particionadas)
1. `sh_datos_40.csv` → `bank_src_banca_multiple` (incremental: solo 202511-202512)
2. `040_R04A_419.csv` → `bank_src_reporte_r04a` (incremental: solo 202511-202512)

### Fase 3: ETL Unificado (KPIs)
1. Ejecutar ETL unificado con los 6 archivos actualizados
2. Esto debería llenar huecos de Nov 2025 (ICAP, IMOR, market_share) + crear filas Dec 2025
3. Fuentes: CNBV_Cartera_Bancos_V2, CASTIGOS, ICAP_Bancos, CorporateLoan_CNBVDB, + transform de bank_src_analisis_general/banca_multiple

### Fase 4: Refresh MVs
1. `SELECT bank_mv_refresh_all();`
2. Solo afecta MVs que dependen de KPIs (comparativa, resumen, ranking)

### Fase 5: Validación
1. `make etl-freshness`
2. Verificar INVEX y SISTEMA para Dic 2025 tengan ICAP, IMOR, market_share
3. Verificar que Nov 2025 huecos se llenaron
