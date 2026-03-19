---
id: TASK-2026-02-09-1800__loader-nuevo2-cartera-analitica
title: Nuevo loader para nuevo2.csv (Cartera Analítica sin encabezados)
status: BACKLOG
priority: Media
phase: Research
scope_in:
  - Definir esquema de columnas para nuevo2.csv sin encabezados (287K filas)
  - Crear función loader en etl/core/loaders/
  - Crear tabla destino bank_src_cartera_analitica (o equivalente)
  - Agregar migración para la nueva tabla
  - Integrar en data_promotion.py specs
scope_out:
  - Escrituras en producción
  - Integración frontend / dashboard
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands: []
pr_files: []
test_status: ''
---

# Resumen
- Objetivo: Ingestar `nuevo2.csv` (Cartera Analítica sin encabezados, por región/institución/fideicomiso) en una nueva tabla `bank_src_*`.
- Padre: `docs/kanban/DOING/2026-02-09-1430__TASK__secure-prod-db-comparison-and-data-drop-policy/`

# Problema
`nuevo2.csv` llega sin encabezados de columna (287,050 filas). Contiene datos de cartera analítica desglosados por moneda, tipo de crédito, estado, institución (clave CNBV), fecha y ~15 columnas de métricas monetarias. Ningún loader existente puede procesarlo.

# Causa raíz
Este archivo nunca fue parte del alcance original del ETL. Es una nueva fuente de datos de la entrega de Bajaware.

# Hallazgos de investigación (de la tarea padre)
- **Filas**: 287,050 (sin encabezados)
- **Codificación**: UTF-8, saltos de línea Windows
- **Delimitador**: Coma (con valores numéricos entrecomillados que contienen comas: `"712,281,201"`)
- **Columnas inferidas** (25 en total):
  - Col 0: Tipo de moneda ("Pesos")
  - Col 1: Tipo de crédito ("Fideicomiso")
  - Col 2: Nombre del estado ("CIUDAD DE MEXICO")
  - Col 3: Código del estado (numérico: 9)
  - Col 4: Detalle de moneda ("Moneda nacional")
  - Col 5: Código desconocido (14)
  - Col 6: Nombre de institución ("Actinver", "Afirme", "Banamex")
  - Col 7: Clave CNBV de institución ("040133", "040062", "040002")
  - Col 8: Fecha (formato M/D/AA: "8/31/25")
  - Col 9: Bandera de fondeo ("Sin Fondeo de BD o FF", "Con Fondeo de BD O FF")
  - Cols 10-24: Métricas monetarias numéricas
- **Necesidad clave**: Los nombres de columna deben definirse (ya sea por documentación de Bajaware o por inferencia de los datos y alineación con reportes R04A/R12A).

# Solución
1. Investigación: Obtener definiciones de columna de Bajaware o inferir de datos + estructura de reportes regulatorios.
2. Crear constante `_NUEVO2_COLUMNS` con nombres inferidos.
3. Crear `load_cartera_analitica()` en `etl/core/loaders/`.
4. Crear migración para tabla `bank_src_cartera_analitica`.
5. Agregar a specs de promoción en `data_promotion.py`.

# Verificación
- [ ] Esquema de columnas definido y documentado
- [ ] Loader importa y dry-run exitoso
- [ ] SQL de migración revisado
- [ ] Dry-run de promoción incluye el archivo
