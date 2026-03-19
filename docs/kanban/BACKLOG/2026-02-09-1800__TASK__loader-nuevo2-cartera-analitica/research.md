# Investigación

## Preguntas
- ¿Cuáles son los nombres exactos de columna para nuevo2.csv?
- ¿Este archivo corresponde a un formato regulatorio existente de la CNBV?
- ¿Qué columnas de métricas se mapean a campos existentes de bank_fact/bank_src?

## Hallazgos

### Estructura del archivo (confirmado con .venv_gpu + polars)
- **Dimensiones**: 287,050 filas × 25 columnas (sin encabezados)
- **Codificación**: UTF-8 con saltos de línea Windows, delimitado por comas (valores numéricos entrecomillados)
- **Esquema de columnas** (inferido):

| Col | Nombre inferido | Tipo | Únicos | Valores de ejemplo |
|-----|----------------|------|--------|--------------------|
| 1 | moneda_tipo | str | 1 | "Pesos" (100%) |
| 2 | tipo_credito | str | 3 | MiPyMEs (55%), Grande (41%), Fideicomiso (4%) |
| 3 | estado | str | 32 | Todos los estados mexicanos |
| 4 | estado_code | int | 32 | Códigos CNBV de estado (1-32) |
| 5 | moneda_detalle | str | 3 | MN (70%), ME (29%), UDIS (0.5%) |
| 6 | moneda_code | int | 3 | 14=MN, 4=ME, 8=UDIS |
| 7 | institucion_nombre | str | 42 | Invex, Santander, HSBC, etc. |
| 8 | clave_cnbv | int | 40 | Códigos 040xxx (040059=Invex) |
| 9 | fecha | str | 4 | 8/31/25, 9/30/25, 10/31/25, 11/30/25 |
| 10 | tipo_fondeo | str | 2 | Sin Fondeo BD/FF (69%), Con Fondeo BD/FF (31%) |
| 11-25 | (métricas) | mixto | - | Valores monetarios, porcentajes, conteos |

- **Dimensiones clave**: 42 instituciones × 32 estados × 3 tipos de crédito × 3 monedas × 2 tipos de fondeo × 4 meses
- **Rango de fechas**: Ago–Nov 2025 (4 cortes mensuales)

### Comparación con BD de producción
- **No existe tabla equivalente** en producción
- `bank_fact_cartera_comercial` (4.2M filas) es la coincidencia conceptual más cercana — cartera de préstamos comerciales por institución
- `bank_fact_cartera_comercial` tiene columnas: banco_norm, fecha, varias métricas de cartera + desgloses geográficos/tamaño
- Sin embargo, nuevo2.csv agrega dimensiones de **desglose geográfico a nivel estado** + **tipo de crédito** + **tipo de fondeo** que no existen en la tabla fact

### Evaluación: PRIORIDAD MEDIA-ALTA — datos dimensionales nuevos
- Esto NO es redundante — proporciona datos de cartera comercial a un grano de **estado × tipo de crédito × tipo de fondeo** que no existe en producción
- El rango de 4 meses (Ago-Nov 2025) es reciente y extiende más allá de los datos en prod (kpis_mensual llega hasta Jul 2025)
- La falta de encabezados es el principal bloqueante — se necesita confirmación de Bajaware para nombres de columnas 11-25
- **Tabla destino**: `bank_src_cartera_analitica` con nombres de columna inferidos + relaciones FK de institución/estado/periodo

## Referencias
- Investigación de tarea padre: `docs/kanban/DOING/2026-02-09-1430__TASK__secure-prod-db-comparison-and-data-drop-policy/research.md`
- Archivo fuente: `data/raw/incoming/drive-download-20260209T193355Z-1-001/nuevo2.csv`
