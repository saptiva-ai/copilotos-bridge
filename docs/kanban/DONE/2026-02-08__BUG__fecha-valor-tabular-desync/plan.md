# Plan: Fecha-Valor Tabular Desync

## Objective

Eliminar desalineaciones entre fecha y valor en texto, tabla y grafica para consultas bancarias tabulares.

## Scope

### In
- Alineacion determinista por fecha en contexto/tablas.
- Normalizacion segura de series temporales con meses faltantes.
- Parseo de fechas robusto en extractor backend.
- Cobertura de regresion en unit y e2e.

### Out
- Cambios de UX visual no relacionados al bug.
- Refactor amplio del pipeline NL2SQL.
- Optimizaciones de rendimiento no vinculadas al defecto.

## Phases

### Phase 1: Contract de Datos Fecha-Valor
- [ ] Rediseñar `_build_markdown_table` para join por fecha (no por indice).
- [ ] Corregir `_build_timeline_chart` para respetar eje temporal y padding de faltantes.
- [ ] Asegurar coherencia entre `plotly_config`, contexto LLM y fallback tabular.

#### Phase 1 Files
- `apps/backend/src/schemas/analytics_data.py`
- `plugins/bank-advisor-private/src/bankadvisor/services/visualization_service.py`
- `apps/backend/src/services/streaming/response_postprocessor.py`

### Phase 2: Robustez de Fechas
- [ ] Extender parser de fechas (`YYYY-MM`, formatos abreviados controlados).
- [ ] Eliminar fallback silencioso a `date.today()` para evitar contaminacion temporal.
- [ ] Definir politica: descartar punto invalido o fail-fast segun contexto.

#### Phase 2 Files
- `apps/backend/src/services/analytics_extractor.py`
- `apps/backend/tests/unit/test_analytics_extractor.py`

### Phase 3: Validacion y Regresion
- [ ] Agregar pruebas unitarias para series desalineadas.
- [ ] Agregar regression e2e que valide fecha exacta en texto/tabla/chart.
- [ ] Ejecutar suite objetivo y documentar evidencias en `validate.md`.

#### Phase 3 Files
- `apps/backend/tests/unit/test_table_fallback_injection.py`
- `apps/backend/tests/unit/test_analytics_extractor.py`
- `tests/e2e/regression/test_2026_02_08_bug_fecha_valor_tabular_desync.py` (nuevo)
- `docs/kanban/BACKLOG/2026-02-08__BUG__fecha-valor-tabular-desync/validate.md`

## Validation Commands

- `make dev`
- `cd apps/backend && .venv/bin/pytest tests/unit/test_analytics_extractor.py -q`
- `cd apps/backend && .venv/bin/pytest tests/unit/test_table_fallback_injection.py -q`
- `python tests/e2e/regression/test_2026_02_08_bug_fecha_valor_tabular_desync.py`

## Success Criteria

- No existe mapping incorrecto fecha-valor en escenarios con meses faltantes.
- E2E reproduciendo bug original pasa en verde.
- No regresiones en rutas existentes de chart y table fallback.
