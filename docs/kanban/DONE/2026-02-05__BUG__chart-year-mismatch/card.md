---
status: DONE
priority: Alta
---
# BUG: Gráfica Muestra Año Diferente al Solicitado

## Status: DOING - Reabierto por nuevos feedbacks (2026-02-10)

## Descripción

Cuando el usuario pide datos de un año específico, el **texto de la respuesta es correcto** pero la **gráfica muestra datos de otro año**.

## Feedback Relacionado (2026-02-05)

| ID | Comentario |
|----|------------|
| FDBK-0074 | "el texto de la respuesta esta bien, me da la cartera en 2023, pero la grafica no, me muestra de otro año que no pedí, en este caso de 2024" |
| FDBK-0073 | "únicamente me dio la tabla comparando los dos años que le pedí pero no la grafica lo cual fue lo que le pedí" |
| FDBK-0072 | "el valor que menciona en enero 2025 (15,048.23) no corresponde al de la tabla y gráfico (15,047.93)" |

## Root Cause (Confirmed & Fixed)

1. **Parser** ✅ - Detectaba correctamente el año
2. **Handlers** ✅ **FIXED** - Ahora pasan `time_range` a use cases
3. **SQL Gen** ✅ **FIXED** - Usa fecha del usuario en vez de MAX(fecha)

## Implementation Summary

**7 archivos modificados:**

| Archivo | Cambio |
|---------|--------|
| `handlers/base.py` | Helper `_extract_time_range()` |
| `handlers/financial_handler.py` | Pasa fechas al servicio |
| `handlers/metricas_financieras_handler.py` | Pasa fechas al use case |
| `handlers/evolucion_banco_handler.py` | Pasa fechas al use case |
| `services/analytics_service.py` | Filtro de fecha en SQL |
| `use_cases/financial_metrics.py` | Date params en DTO y SQL |
| `use_cases/growth_evolution.py` | Date params en DTO y SQL |

## Acceptance Criteria

- [x] Handlers extraen y pasan `spec.time_range`
- [x] SQL usa time_range cuando está disponible
- [x] Fallback a MAX(fecha) cuando no hay fechas
- [x] Validación de sintaxis pasó
- [x] Tests básicos de import pasaron
- [ ] Deploy a producción
- [ ] E2E: "cartera 2023" → gráfica solo 2023

### Reopened: 2026-02-10 (Triage automatizado)

| ID | Fecha | Query | Problema | Stale-chart verdict |
|----|-------|-------|----------|---------------------|
| FDBK-0109 | 2026-02-10 | "compare la cartera comercial de invex en 2025 vs 2024" | Esperaba overlay 2 lineas (2024 y 2025), recibio graficas separadas | STALE + COMPARISON_FORMAT |
| FDBK-0111 | 2026-02-10 | "cartera comercial de invex en 2024" | Artefactos residuales muestran 2025 en vez de 2024 | STALE (artefactos de query anterior en misma conv) |

**Nuevo patron:** FDBK-0109 revela que el handler de comparacion temporal no genera overlay (2 traces en 1 chart). En cambio genera artefactos individuales por año. El usuario espera una sola grafica con lineas superpuestas.

### Deep Investigation (2026-02-10)

**Previous fix (2026-02-05)**: Added `_extract_time_range(spec)` helper to `BaseHandler`, wired it through `financial_handler`, `metricas_financieras_handler`, and `evolucion_banco_handler`. SQL generation now uses user's requested date range instead of `MAX(fecha)`. Also added `_ensure_multi_year_coverage()` to expand date range when user mentions multiple years (e.g., "2024 y 2025").

**Gap identified**: FDBK-0109 query "compare la cartera comercial de invex en 2025 vs 2024" never reaches the overlay chart builder because `ComparativeRatioHandler.SUPPORTED_METRICS = {"imor", "icor", "icap", "icap_total"}` — "cartera_comercial" is **not** in this set. The query falls through the handler chain:

**Code trace**:

| Step | File:Line | What happens | Problem |
|------|-----------|-------------|---------|
| 1 | `comparative_handler.py:26` | `has_metric = entities.metric_id.lower() in self.SUPPORTED_METRICS` | Returns `False` for cartera_comercial → handler skipped |
| 2 | `metricas_financieras_handler.py:113` | `_COMPARISON_PATTERN.search(query_lower)` catches "vs" | Returns `False` → handler defers comparison queries |
| 3 | Falls to NL2SQL | Generates separate SQL queries per year | 2 individual charts instead of 1 overlay chart |

**Secondary gap (FDBK-0111)**: Stale artifacts from previous query in same conversation. When a user asks "cartera 2025" then "cartera 2024" in the same session, old artifacts (charts) from the first query may persist in the frontend if not properly replaced.

**Fix strategy**:
1. **For FDBK-0109** (COMPARISON_FORMAT): Either expand `ComparativeRatioHandler.SUPPORTED_METRICS` to include cartera metrics, or create a dedicated `CarteraComparativeHandler` that handles cartera comparison queries with overlay traces.
2. **For FDBK-0111** (STALE artifacts): Frontend must clear previous artifacts when a new query response arrives in the same conversation.

### Reopened: 2026-02-11 (Triage automatizado)

| ID | Fecha | Query | Problema | Stale-chart verdict |
|----|-------|-------|----------|---------------------|
| FDBK-0118 | 2026-02-11 | "Para el periodo enero 2024 vs enero 2025. Cual es el % variacion de la cartera total de INVEX vs [9 bancos]. Grafica de barras horizontal." | 1 trace en vez de 2 (COMPARISON_FORMAT), falta 2024 en x_range (STALE) | COMPARISON_FORMAT + STALE |
| FDBK-0122 | 2026-02-11 | "Graficame la cartera total de INVEX y comparala contra el promedio de [9 bancos]" | Esperaba grafica lineal comparativa, recibio tabla markdown | No chart generado |
| FDBK-0128 | 2026-02-11 | "Muestrame la cartera total de INVEX y comparala contra el promedio de [9 bancos]" | Esperaba grafica con dos lineas (INVEX vs promedio), sin overlay | No overlay |

**Patron persistente (3ra ocurrencia, 25 STALE + 4 COMPARISON_FORMAT):** Queries de comparacion de cartera no generan overlay porque `ComparativeRatioHandler.SUPPORTED_METRICS` no incluye cartera. Nuevo sub-patron: "promedio de grupo" no soportado como tipo de comparación (FDBK-0122, FDBK-0128). En total 3 sub-patrones activos: (1) STALE año faltante, (2) COMPARISON_FORMAT 1-trace-en-vez-de-2, (3) avg-group no soportado.

### Fix: Multi-Bank Routing (2026-02-11)

**Relacionado con FDBK-0109/0118/0122:** Queries de comparación de cartera multi-banco ahora se rutean a `EvolutionUseCase` (soporta `List[str]` de bancos) en vez de caer a NL2SQL. Esto genera overlay charts con 12+ puntos temporales por banco en vez de bar charts resumen de 2 puntos.

**Cambio clave:** `EvolucionBancoHandler.handle()` ahora detecta `len(banks) > 1` y delega a `_handle_multi_bank()`.

### Fix: Type Whitelist + Silent Discard (2026-02-11)

**Root cause descubierto:** `main.py:execute_bank_analytics()` filtraba resultados con `type in ["data", "clarification", "error", "empty", "knowledge"]`. Todos los handlers retornan `type: "chart"` — **no estaba en la lista**. Resultado: el 100% de los resultados de handlers eran descartados silenciosamente y el NL2SQL corría como fallback.

**Fix:** Agregar `"chart"` al whitelist. **Impacto:** GD-7 pasó de 2 puntos (resumen) a 598 puntos (evolución temporal completa).

### Refactor: HU3 → NLP Pipeline (2026-02-11)

Renombrado de variables, logs y comentarios internos de `hu3_*` a nombres descriptivos (`nlp_result`, `nlp_pipeline.*`, `nlp_handler`). ~18 archivos afectados, solo naming — sin cambios de lógica.

## Prioridad

🔴 **Critica** - 8 reportes de usuarios (persistente desde 2026-02-05)

## Workflow Status

| Phase | Status |
|-------|--------|
| Research | ✅ Completado |
| Plan | ✅ Completado |
| Implement | ✅ Multi-bank routing + type whitelist fix |
| Validate | ✅ E2E 9/9 passed (GD-7: 598 points, 2 banks) |
| Deploy | ⬜ Pendiente |

## Feedback Vinculado

**9 reporte(s)** de usuarios en produccion.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0073 | `cb6c6879` | hazme una grafica comparando la cartera comercial de INVE... | únicamente me dio la tabla comparando los dos años que le pedí pero no la gra... | 2026-02-05 |
| 2 | FDBK-0074 | `cb6c6879` | muéstrame la cartera comercial de INVEX en 2023 | el texto de la respuesta esta bien, me da la cartera en 2023, pero la grafica... | 2026-02-05 |
| 3 | FDBK-0091 | `cb6c6879` | muestrame la cartera cartera comercial de invex en 2025 | - no me dio la cartera de 2025, me mostró la de 2024 - en el texto menciona q... | 2026-02-06 |
| 4 | FDBK-0092 | `cb6c6879` | muéstrame una grafica en la que se compare la cartera com... | me mostro la cartera comercial solo de 2024 y menciona que para 2025 no hay i... | 2026-02-06 |
| 5 | FDBK-0109 | `cb6c6879` | muestrame una grafica en la que se compare la cartera comercial de invex en 2025 vs 2024 | esperaba una gráfica que tuviera las líneas de 2024 y 2025 separadas — los datos presentados en el texto son incorrectos | 2026-02-10 |
| 6 | FDBK-0111 | `cb6c6879` | muéstrame la cartera comercial de invex en 2024 | despliega los datos correctamente en la grafica y tabla — en el texto confunde los meses y cantidades | 2026-02-10 |
| 7 | FDBK-0118 | `85338a1e` | Para el periodo enero 2024 vs enero 2025. Comparativa cartera INVEX vs 9 bancos | 1 trace en vez de overlay, datos incorrectos | 2026-02-11 |
| 8 | FDBK-0122 | `85338a1e` | Graficame la cartera total de INVEX vs promedio de 9 bancos | esperaba grafica lineal comparativa, recibio tabla | 2026-02-11 |
| 9 | FDBK-0128 | `85338a1e` | Muestrame cartera total INVEX vs promedio de 9 bancos | esperaba grafica con dos lineas comparando INVEX vs promedio | 2026-02-11 |

<details>
<summary>Detalle completo de feedbacks</summary>

### FDBK-0073
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `9ae671a7-3a03-498f-a6c3-c142f665825a`
- **Message**: `ac3be9da-ec9e-469b-bcde-53952a855240`
- **Rating**: 👎
- **Query**: "hazme una grafica comparando la cartera comercial de INVEX de 2024 y de 2025"
- **Feedback**: "únicamente me dio la tabla comparando los dos años que le pedí pero no la grafica lo cual fue lo que le pedí"
- **Fecha**: 2026-02-05T16:36:13.397Z

### FDBK-0074
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `9ae671a7-3a03-498f-a6c3-c142f665825a`
- **Message**: `7face999-d2a7-494a-afb5-b2b2aeab24b5`
- **Rating**: 👎
- **Query**: "muéstrame la cartera comercial de INVEX en 2023"
- **Feedback**: "el texto de la respuesta esta bien, me da la cartera en 2023, pero la grafica no, me muestra de otro año que no pedí, en este caso de 2024"
- **Fecha**: 2026-02-05T16:39:00.973Z

### FDBK-0091
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `5652c5bf-e97c-4812-a20a-6d029a7ae9ae`
- **Message**: `eecfd311-7296-4525-994d-587f959b0103`
- **Rating**: 👎
- **Query**: "muestrame la cartera cartera comercial de invex en 2025"
- **Feedback**: "- no me dio la cartera de 2025, me mostró la de 2024
  - en el texto menciona que no hay información de 2025"
- **Fecha**: 2026-02-06T15:57:01.543Z

### FDBK-0092
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `5652c5bf-e97c-4812-a20a-6d029a7ae9ae`
- **Message**: `81d6d362-441d-48e9-9be5-06529cac6124`
- **Rating**: 👎
- **Query**: "muéstrame una grafica en la que se compare la cartera comercial de INVEX de 2024 y 2025"
- **Feedback**: "me mostro la cartera comercial solo de 2024 y menciona que para 2025 no hay información"
- **Fecha**: 2026-02-06T15:58:41.666Z

</details>
