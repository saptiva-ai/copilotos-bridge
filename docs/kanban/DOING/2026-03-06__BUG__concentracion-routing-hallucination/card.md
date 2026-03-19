# BUG: concentracion-routing-hallucination

**Prioridad:** P1
**Fecha:** 2026-03-06
**Status:** DOING

---

## Resumen

## Reporte de Alucinación: "Concentración" mezcla métricas distintas

**Reportado por**: Fernando de Bajaware (`fsaavedra@bajaware.com`)
**Servidor**: invex.saptiva.com
**Fecha incidente**: 2026-03-04
**Sessions afectadas**: `d8ecb878`, `5a6e73ef`, `6fba7584`

### Problema

El usuario pregunta por "concentración de cartera por actividad económica" (sector SCIAN) pero el sistema devuelve datos de "concentración de mercado" (Top 5/Top 10 bancos). El LLM reinterpreta los números y alucina categorías sectoriales inexistentes.

### Root Cause (auditoría completada)

**A. Routing incorrecto** — `ResumenSistemaHandler` (posición 4) captura "concentración" antes que `CarteraActividadHandler` (posición 5). Keyword "concentración" en `SISTEMA_KEYWORDS` es demasiado amplio. Patrón `REGIONAL_EXCLUSIONS` ya existe pero falta equivalente `ACTIVIDAD_EXCLUSIONS`.

**B. Alucinación LLM** — Recibe `top5_pct=74.0` y lo reetiqueta como "sector servicios 74%". El `ANALYSIS_SYSTEM_PROMPT` no define qué significa "CONCENTRACION BANCARIA" ni distingue entre tipos de concentración.

**C. Prompts sin definición** — Los archivos en `bankadvisor/prompts/` no mencionan "concentración" ni una sola vez.

### Fix propuesto (3 partes)

**Fix A (routing)**: Agregar `ACTIVIDAD_EXCLUSIONS` a `resumen_sistema_handler.py` (análogo a `REGIONAL_EXCLUSIONS`)
**Fix B (prompt)**: Definir métricas de concentración en `ANALYSIS_SYSTEM_PROMPT` 
**Fix C (semantic)**: Refinar exemplars en `semantic_handler_scorer.py`

### Archivos afectados

- `plugins/bank-advisor-private/src/bankadvisor/handlers/resumen_sistema_handler.py`
- `plugins/bank-advisor-private/src/bankadvisor/fsm/agents/analysis_agent.py`
- `plugins/bank-advisor-private/src/bankadvisor/services/semantic_handler_scorer.py`

### Evidencia

Todas las respuestas muestran `handler_name: "resumen_sistema"` y `handlers_tried: ["multi_metric", "metricas_financieras", "evolucion_banco", "resumen_sistema"]` — `cartera_actividad` nunca fue evaluado.

---

## Criterios de Aceptación

- [ ] TODO

---

## Referencias

- N/A
