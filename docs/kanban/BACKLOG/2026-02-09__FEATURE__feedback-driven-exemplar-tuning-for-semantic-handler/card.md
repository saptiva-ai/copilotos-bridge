---
status: DOING
---
# FEATURE: Feedback-driven exemplar tuning for semantic handler scorer

**Prioridad:** P2
**Fecha:** 2026-02-09
**Status:** BACKLOG

---

## Resumen

## Problema

El SemanticHandlerScorer usa exemplars estáticos hardcodeados. Cuando el sistema clasifica mal una query, no hay forma automática de mejorar los exemplars con datos reales.

El sistema de feedback (thumbs up/down) ya captura `original_query`, `intent`, `rating` en MongoDB (`message_feedback`), pero **no persiste `handler_name`** — el dato clave para saber qué handler procesó la query.

## Objetivo

Nivel 1 (offline, bajo riesgo):
1. Persistir `handler_name` en el feedback context para que cada thumbs-down tenga trazabilidad de qué handler se equivocó
2. Script ETL offline que extrae queries con feedback positivo (thumbs-up) agrupadas por handler, las embede, y las propone como nuevos exemplars candidatos
3. Archivo JSON de exemplars adicionales que el scorer carga al iniciar (además de los hardcodeados)

## Cambios esperados

### Persistir handler_name (backend)
- `RouteResult.handler_name` ya existe en memoria — propagarlo al `message_metadata` que se guarda en MongoDB
- Agregar `handler_name` al `FeedbackContext` dataclass en `feedback_service.py`

### Script ETL offline (nuevo)
- Leer feedback con rating=up de MongoDB
- Agrupar por handler_name
- Filtrar queries con alta confianza
- Exportar a JSON: `{handler_name: [query1, query2, ...]}`
- Opcional: validar con embeddings que las queries nuevas no conflicten con otros handlers

### Loader de exemplars dinámicos (plugin)
- `SemanticHandlerScorer` carga exemplars adicionales desde archivo JSON al iniciar
- Merge con HANDLER_EXEMPLARS estáticos
- Dedup por similaridad (no agregar si ya hay un exemplar muy cercano)

## Criterios de aceptación
- [ ] `handler_name` presente en feedback context de nuevos thumbs-up/down
- [ ] Script ETL exporta exemplars candidatos desde MongoDB
- [ ] Scorer carga exemplars dinámicos + estáticos sin regresión
- [ ] Tests unitarios para el merge de exemplars

---

## Criterios de Aceptación

- [ ] TODO

---

## Referencias

- N/A
