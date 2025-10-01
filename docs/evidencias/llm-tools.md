# Evidencias Reproducibles: LLM + Tools Integration

**Fecha de generación**: 2025-09-30
**Versión del sistema**: Develop branch
**Estado de Deep Research**: ❌ DESHABILITADO (Kill switch activo)

---

## Variables de entorno

```bash
export BASE_URL="http://localhost:3000"
export API_URL="http://localhost:8001"
export TOKEN="<your-jwt-token>"
export USER_ID="<your-user-id>"
```

## 1. Obtener Feature Flags

**Descripción**: Verifica el estado de las feature flags, incluyendo el kill switch de Deep Research.

```bash
curl -X GET "${API_URL}/api/config/features" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Cache-Control: no-store"
```

**Respuesta esperada**:
```json
{
  "deep_research_kill_switch": true,
  "deep_research_enabled": false,
  "deep_research_auto": false,
  "deep_research_complexity_threshold": 0.7
}
```

**Headers clave**:
- `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`
- `Pragma: no-cache`

---

## 2. Enviar mensaje de chat simple (sin tools)

**Descripción**: Envío básico de mensaje usando solo SAPTIVA LLM (sin tools activas).

```bash
curl -X POST "${API_URL}/api/chat" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Cache-Control: no-store" \
  -d '{
    "message": "¿Qué es SAPTIVA?",
    "model": "Saptiva Turbo",
    "temperature": 0.7,
    "max_tokens": 1024,
    "stream": false,
    "tools_enabled": {}
  }'
```

**Respuesta esperada**:
```json
{
  "chat_id": "abc123...",
  "message_id": "msg456...",
  "content": "SAPTIVA es un modelo de lenguaje...",
  "role": "assistant",
  "model": "Saptiva Turbo",
  "created_at": "2025-09-30T...",
  "tokens": 256,
  "latency_ms": 1200,
  "finish_reason": "stop"
}
```

**Flujo interno (BE)**:
1. `POST /api/chat` → `apps/api/src/routers/chat.py:send_chat_message`
2. Verifica `deep_research_kill_switch` (activo → bypass coordinator)
3. Llama directamente a `SaptivaClient.chat_completion()` en `apps/api/src/services/saptiva_client.py:165`
4. Retorna respuesta con headers `Cache-Control: no-store`

**Archivo relevante**: `apps/api/src/routers/chat.py:129-172`

---

## 3. Activar Web Search (manual)

**Descripción**: Envío de mensaje con Web Search habilitado (feature flag).

> ⚠️ **NOTA**: Web Search actualmente es solo un **feature flag visual**. No hay implementación backend de scraping/fetching real en esta versión. El flag se envía al backend pero no se procesa.

```bash
curl -X POST "${API_URL}/api/chat" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Cache-Control: no-store" \
  -d '{
    "message": "¿Cuáles son las noticias más recientes sobre IA?",
    "model": "Saptiva Turbo",
    "tools_enabled": {
      "web_search": true
    }
  }'
```

**Comportamiento actual**:
- El parámetro `tools_enabled.web_search` se acepta pero **no se procesa** en el backend.
- El LLM responde basándose únicamente en su conocimiento interno.
- **No hay endpoint de web scraping/search implementado**.

**Archivos relevantes**:
- FE: `apps/web/src/types/tools.tsx:119` (definición de `web-search`)
- FE: `apps/web/src/lib/feature-flags.ts:9` (feature flag)
- BE: `apps/api/src/schemas/chat.py:90` (acepta tools_enabled pero no procesa)

---

## 4. Intentar activar Deep Research (bloqueado)

**Descripción**: Intento de forzar Deep Research con kill switch activo.

```bash
curl -X POST "${API_URL}/api/chat" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Cache-Control: no-store" \
  -d '{
    "message": "Investiga a fondo los últimos avances en computación cuántica",
    "model": "Saptiva Turbo",
    "tools_enabled": {
      "deep_research": true
    }
  }'
```

**Respuesta esperada**:
- Con kill switch activo, el sistema bypasa el Research Coordinator
- Se procesa como chat simple (sin Deep Research)
- Logs indican: `"Using simple Saptiva chat (kill switch active)"`

**Archivo relevante**: `apps/api/src/routers/chat.py:127-172`

**Intentar escalación manual** (también bloqueado):
```bash
curl -X POST "${API_URL}/api/chat/{CHAT_ID}/escalate" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json"
```

**Respuesta esperada (410 Gone)**:
```json
{
  "detail": {
    "error": "Deep Research feature is not available",
    "error_code": "DEEP_RESEARCH_DISABLED",
    "message": "Escalation to research is not available. This feature has been disabled.",
    "kill_switch": true
  }
}
```

**Archivo relevante**: `apps/api/src/routers/chat.py:362-379`

---

## 5. Enviar mensaje con adjuntos (Add Files)

**Descripción**: El frontend permite adjuntar archivos (PDF, imágenes, etc.), pero el backend **NO tiene implementado el procesamiento de archivos aún**.

> ⚠️ **ESTADO ACTUAL**: La UI de adjuntos está implementada, pero no hay endpoints de:
> - Upload de archivos
> - Parsing de PDFs
> - Generación de embeddings
> - Vector store/RAG

```bash
# Este endpoint NO EXISTE actualmente
curl -X POST "${API_URL}/api/files/upload" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@documento.pdf"
# Respuesta: 404 Not Found
```

**Archivos relevantes (solo UI)**:
- `apps/web/src/components/chat/ChatComposer/ChatComposer.tsx:467-520` (drag & drop, validación)
- `apps/web/src/types/tools.tsx:117` (tool `add-files`)

**TO-DO** (no implementado):
- Endpoint `/api/files/upload`
- Servicio de parsing (PyPDF2, pdfplumber, etc.)
- Embeddings (OpenAI, Cohere, etc.)
- Vector store (Pinecone, Weaviate, PostgreSQL con pgvector)
- RAG retrieval en el prompt builder

---

## 6. Health check del sistema

**Descripción**: Verificar que el backend y el LLM están operativos.

```bash
curl -X GET "${API_URL}/api/health" \
  -H "Content-Type: application/json"
```

**Respuesta esperada**:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-30T...",
  "version": "0.1.0",
  "uptime_seconds": 12345,
  "checks": {
    "database": "ok",
    "saptiva_api": "ok",
    "redis_cache": "ok"
  }
}
```

---

## 7. Obtener historial de chat

**Descripción**: Cargar mensajes previos de una conversación con research tasks asociados.

```bash
curl -X GET "${API_URL}/api/history/${CHAT_ID}?limit=50&offset=0&include_research_tasks=true" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Cache-Control: no-store"
```

**Respuesta esperada**:
```json
{
  "chat_id": "abc123...",
  "messages": [
    {
      "id": "msg1",
      "role": "user",
      "content": "Hola",
      "created_at": "2025-09-30T...",
      "metadata": {}
    },
    {
      "id": "msg2",
      "role": "assistant",
      "content": "Hola, ¿en qué puedo ayudarte?",
      "model": "Saptiva Turbo",
      "tokens": 15,
      "latency_ms": 800,
      "created_at": "2025-09-30T..."
    }
  ],
  "total_count": 2,
  "has_more": false
}
```

**Headers clave**:
- `Cache-Control: no-store`

**Archivo relevante**: `apps/api/src/routers/chat.py:483-630`

---

## 8. Logs y trazas

**Ver logs del backend**:
```bash
cd apps/api
tail -f logs/app.log
```

**Ver logs del frontend (dev)**:
```bash
cd apps/web
npm run dev
# O verificar console del navegador
```

**Buscar traza de una request**:
```bash
grep "chat_id" apps/api/logs/app.log | grep "abc123"
```

---

## Resumen de estado actual

| Tool / Feature        | Estado FE | Estado BE | Endpoint                    | Implementación                          |
|-----------------------|-----------|-----------|-----------------------------|-----------------------------------------|
| Web Search            | ✅ UI      | ❌ No      | N/A                         | Solo feature flag, sin scraping real    |
| Deep Research         | ✅ UI      | ✅ Sí      | `/api/research/deep`        | ❌ **DESHABILITADO** (kill switch)       |
| Add Files (PDF, etc.) | ✅ UI      | ❌ No      | `/api/files/upload` ❌      | Solo validación FE, sin backend         |
| Google Drive          | ✅ UI      | ❌ No      | N/A                         | Solo feature flag                       |
| Canvas                | ✅ UI      | ❌ No      | N/A                         | Solo feature flag                       |
| Agent Mode            | ✅ UI      | ❌ No      | N/A                         | Solo feature flag                       |
| Chat Simple           | ✅ UI      | ✅ Sí      | `/api/chat`                 | ✅ Funcional con Saptiva LLM             |
| Escalate to Research  | ✅ UI      | ✅ Sí      | `/api/chat/{id}/escalate`   | ❌ Bloqueado por kill switch             |

---

## Próximos pasos (fuera de scope de este documento)

1. **Implementar Web Search**:
   - Añadir servicio de scraping/fetching (Beautiful Soup, Playwright)
   - Endpoint `/api/tools/web-search`
   - Integrar resultados en el prompt del LLM

2. **Implementar PDF → RAG**:
   - Endpoint `/api/files/upload`
   - Parser (PyPDF2, pdfplumber, pymupdf)
   - Servicio de embeddings (OpenAI, Cohere, sentence-transformers)
   - Vector store (Pinecone, Weaviate, pgvector)
   - Retrieval en prompt builder

3. **Habilitar Deep Research** (cuando sea necesario):
   - Cambiar `DEEP_RESEARCH_KILL_SWITCH=false`
   - Testear flujo completo con Aletheia
   - Validar streaming y reportes

---

**Contacto**: Para más información, consulta `apps/api/README.md` y `apps/web/README.md`.
