---
status: REVIEW
---
# BUG: Catalog content mismatch: message.content has generic template instead of response_text

**Prioridad:** P1
**Fecha:** 2026-02-09
**Status:** DOING

---

## Resumen
Catalog responses son autoritativos. El post-processing del streaming layer estaba corrigiendo falsos negativos ("No se encontró...") y reemplazaba el contenido con una plantilla genérica, causando desincronización entre `message.content` y `response_text` al persistir/recargar historial.

## Evidencia (prod 2026-02-09)

**Conversación**: `2aacb224` → msg `77ac09f8`
**content**: "A continuación se presentan los datos solicitados sobre el código..."
**response_text**: "No se encontró banco con clave 040032"

### Síntoma
Cuando el catalog fast path retorna `response_text`, el campo `message.content` ya fue committed con una plantilla genérica por el streaming layer. Al recargar la conversación desde historial, se muestra el texto genérico en lugar de la respuesta real.

### 3 instancias en 7 días
- msg `77ac09f8` (IXE 040032)
- msg `8dbbfc74` (catalog)
- msg `e8a21d98` (catalog)

### Archivos clave
- `apps/backend/src/services/bank_analytics_client.py` (`handle_catalog_query()`)
- `apps/backend/src/routers/chat.py` (streaming commit)
- `apps/backend/src/services/message_service.py` (persistence)

### Criterio de aceptación
- [x] `message.content` === `response_text` cuando catalog fast path se activa (no post-processing)
- [x] Test unitario que verifica que el catalog response no se modifica por post-processing
- [ ] Validar en prod con query de catálogo

---

## Criterios de Aceptación

- [ ] Confirmar en producción que al consultar catálogo (ej. "a que banco pertenece la clave 040032") el historial muestra el texto real, no la plantilla genérica.

---

## Updates
- 2026-02-09 - Fix implementado en streaming post-processing (skip para `path_taken=catalog` y `bank_chart_data.type=catalog`) + tests unitarios.

---

## Referencias

- N/A
