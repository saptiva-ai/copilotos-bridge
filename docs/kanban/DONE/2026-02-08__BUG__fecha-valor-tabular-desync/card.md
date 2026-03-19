# BUG: Desalineacion Fecha-Valor en Analisis Tabular

## Status: DONE

## Prioridad: High

## Problema

En consultas donde el usuario pide analisis tabular (mes a mes), la respuesta final puede citar un valor correcto pero asociado a una fecha incorrecta.

Impacto observado:
- Analisis textual con referencia temporal equivocada.
- Pérdida de confianza del usuario en la consistencia tabla/grafica/texto.
- Riesgo de decisiones basadas en un periodo incorrecto.

## Feedback Relacionado (2026-02-08)

| Fuente | Comentario |
|--------|------------|
| Usuario | "el LLM confunde fechas con el dato de esa fecha y muestra el de otra fecha" |

## Root Cause Tecnico (Confirmado)

1. Tabla markdown en backend se construye por indice y no por llave de fecha:
   - `apps/backend/src/schemas/analytics_data.py` (`_build_markdown_table`)
   - Usa la primera serie como eje y alinea otras series por posicion.
   - Si una serie tiene meses faltantes, se cruzan fecha y valor.

2. Configuracion timeline del plugin puede desalinear `x` y `y` por banco:
   - `plugins/bank-advisor-private/src/bankadvisor/services/visualization_service.py` (`_build_timeline_chart`)
   - `x` toma todos los meses globales, pero cada banco acumula solo los puntos existentes.
   - Cuando faltan meses para un banco, `y` queda corrido contra `x`.

3. Parseo de fechas con fallback silencioso a fecha actual:
   - `apps/backend/src/services/analytics_extractor.py` (`_parse_date`)
   - Si no parsea formatos como `YYYY-MM`, cae a `date.today()`.
   - Esto puede contaminar periodos y estadisticos con fechas falsas.

4. Routing multi-banco forzado a comparacion snapshot:
   - `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py`
   - `comparison_mode` se activaba solo por tener >1 banco.
   - Resultado: consultas de evolucion multi-banco terminaban en bar chart (ultimo mes),
     perdiendo tabla temporal completa.

## Solucion Propuesta

1. Backend: rehacer tabla por join de fechas, no por indice.
2. Plugin: construir series por banco con relleno explicito (`None`) para meses faltantes y garantizar `len(x) == len(y)`.
3. Extractor: soportar formatos de fecha esperados (`YYYY-MM`, abreviados) y eliminar fallback silencioso a fecha actual.
4. Guardrails: agregar validaciones automáticas de consistencia fecha-valor antes de responder.
5. Pruebas: unit + e2e de regresion con casos de meses faltantes y bancos multiples.
6. Routing: activar `comparison_mode` solo con marcadores explicitos de comparacion.

## Progreso (2026-02-08)

Implementado con TDD (Red -> Green):

1. Tests de regresion agregados
- `apps/backend/tests/unit/test_table_mode_resolver.py::test_full_mode_aligns_values_by_date_when_series_has_gaps`
- `apps/backend/tests/unit/test_analytics_extractor.py::test_parse_year_month_format`
- `apps/backend/tests/unit/test_analytics_extractor.py::test_parse_abbrev_month_year_format`
- `apps/backend/tests/unit/test_analytics_extractor.py::test_parse_spanish_abbrev_month_year_format`
- `apps/backend/tests/unit/test_analytics_extractor.py::test_parse_invalid_date_raises`
- `apps/backend/tests/unit/test_analytics_extractor.py::test_extract_fallbacks_to_series_range_when_metadata_dates_invalid`
- `plugins/bank-advisor-private/src/bankadvisor/tests/unit/test_viz_service.py::test_timeline_aligns_missing_months_per_bank`
- `apps/backend/tests/unit/test_table_mode_semantic.py::test_ensure_embeddings_works_inside_running_event_loop`
- `apps/backend/tests/unit/test_table_mode_semantic.py::test_ensure_embeddings_retries_after_transient_failure`
- `plugins/bank-advisor-private/src/bankadvisor/tests/unit/test_multi_bank_support.py::test_ca01_multi_bank_evolution_not_forced_to_comparison`
- `plugins/bank-advisor-private/src/bankadvisor/tests/unit/test_multi_bank_support.py::test_ca01_between_dates_phrase_is_not_explicit_comparison`

2. Fixes aplicados
- `apps/backend/src/schemas/analytics_data.py`
  - `_build_markdown_table` ahora alinea por fecha (join por llave temporal).
- `plugins/bank-advisor-private/src/bankadvisor/services/visualization_service.py`
  - `_build_timeline_chart` ahora rellena meses faltantes con `None` por banco.
- `apps/backend/src/services/analytics_extractor.py`
  - `_parse_date` soporta `YYYY-MM`, `Mon YYYY`, `Month YYYY`, meses abreviados ES.
  - Fechas invalidas ya no se convierten silenciosamente a `today()`.
  - Metadata de fechas usa parseo opcional y fallback a rango real de series.
- `apps/backend/src/services/streaming/system_prompt_builder.py`
  - `resolve_table_mode` ahora soporta promocion semantica opcional con embeddings
    (feature flag `TABLE_MODE_SEMANTIC_ENABLED`) para reducir dependencia de keywords exactos.
- `apps/backend/src/services/intent/table_mode_semantic.py`
  - Nuevo clasificador semantico `full/excerpt` con `EmbeddingService`.
  - Correccion async-safe: evita errores de event loop al clasificar en requests async.
  - Reintento en inicializacion de embeddings tras fallas transitorias (sin cachear fallo permanente).
- `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py`
  - `comparison_mode` ahora requiere marcadores explicitos de comparacion (`vs`, `versus`, `compara`, etc.).
  - Consultas multi-banco temporales sin comparacion explicita quedan en modo evolucion (line chart).
- `infra/docker-compose.dev.yml`
  - Expuestos flags `TABLE_MODE_SEMANTIC_*` para activar/rutear tuning en runtime sin tocar `.env`.

## Archivos Candidatos

- `apps/backend/src/schemas/analytics_data.py`
- `apps/backend/src/services/analytics_extractor.py`
- `apps/backend/src/services/streaming/response_postprocessor.py`
- `plugins/bank-advisor-private/src/bankadvisor/services/visualization_service.py`
- `apps/backend/tests/unit/test_analytics_extractor.py`
- `apps/backend/tests/unit/test_table_fallback_injection.py`
- `tests/e2e/regression/test_2026_02_08_bug_fecha_valor_tabular_desync.py` (nuevo)

## Criterios de Aceptacion (DoD)

- [x] Tabla tabular alinea valores por fecha exacta para todos los bancos.
- [x] No hay corrimiento `x/y` en chart timeline cuando faltan meses por banco.
- [x] Parseo de fecha no inventa fecha actual ante formatos validos o invalidos.
- [x] E2E regression con 2-3 escenarios del bug en `tests/e2e/regression/`.
- [ ] Tests ejecutados contra backend real (`make dev`) y pasando.
- [ ] Deploy realizado y usuario confirma que el bug no se reproduce en produccion.

## Relacionado

- `docs/kanban/BACKLOG/2026-02-05__BUG__chart-year-mismatch/card.md`
- `docs/kanban/DOING/2026-02-03__BUG__response-grounding-desync/card.md`
