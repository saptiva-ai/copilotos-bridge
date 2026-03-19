# Research: File Manager Thumbnails & Context

## Pipeline Completo (Upload → Thumbnail → Chat Context)

### Flujo de Upload
```
[Browser] → POST /api/files/upload (Next.js proxy)
    → [Backend] file_ingest.py:FileIngestService.ingest_file()
        → Valida MIME type, tamaño, idempotencia
        → storage.save() → guarda en filesystem /tmp/ o MinIO
        → Document.insert() en MongoDB (minio_bucket, minio_key)
        → Background: extract_text_from_file() → Redis cache
        → SSE events: RECEIVED → PROCESSING → READY/FAILED
    → [Frontend] useFiles.ts conecta SSE, actualiza Zustand store
    → PreviewAttachment.tsx renderiza thumbnail
```

### Flujo de Thumbnail
```
[PreviewAttachment] → canShowThumbnail = (isImage || isPdf) && isReady
    → [ThumbnailImage] fetch(`/api/documents/${fileId}/thumbnail`)
        → [Next.js proxy] /api/thumbnails/[fileId]/route.ts
            → Forward con Bearer token al backend
        → [Backend] documents.py:get_document_thumbnail()
            → Document.get(doc_id) → verifica ownership
            → is_legacy? (minio_bucket="temp" && minio_key=/tmp/...)
                → SI: pasa None/None → thumbnail_service retorna None → 404
                → NO: thumbnail_service.get_or_generate_thumbnail()
                    → Check MinIO thumbnails bucket (cache)
                    → Si no cached: genera desde source file
                        → PDF: PyMuPDF local o gRPC a file-manager
                        → Image: Pillow local
                    → Guarda en MinIO thumbnails bucket
                    → Retorna JPEG bytes
```

### Flujo de Contexto en Chat
```
[useSendMessage] → POST /api/chat/messages (con file_ids en body)
    → [StreamingHandler] → DocumentContextBuilder.build()
        → _retrieve_via_rag(): GetRelevantSegmentsTool (Qdrant)
            → max_segments=2, busca por conversacion + pregunta
        → Si RAG falla → _retrieve_from_cache()
            → DocumentService.get_document_text_from_cache()
            → Trunca a max_text_chars=4000 por documento
        → format_for_prompt(): "**Documentos adjuntos por el usuario:**\n{context}"
    → SystemPromptBuilder.build() inyecta contexto en system prompt
```

## Archivos Clave Analizados

| Archivo | Rol | Hallazgo |
|---------|-----|----------|
| `apps/web/src/components/chat/ThumbnailImage.tsx` | Carga thumbnail con auth | Retorna `null` en error (L103) - no hay fallback |
| `apps/web/src/components/chat/PreviewAttachment.tsx` | Preview de archivos | `shouldShowFallback` no cubre caso de ThumbnailImage fallido |
| `apps/web/src/app/api/thumbnails/[fileId]/route.ts` | Proxy Next.js | Double-hop innecesario si se usa presigned URL |
| `apps/backend/src/routers/documents.py:256-359` | Endpoint thumbnail | Legacy docs (L299-321) retornan 404 silenciosamente |
| `apps/backend/src/services/thumbnail_service.py` | Generacion de thumbnails | V3: soporta local PyMuPDF o gRPC, cache en MinIO |
| `apps/backend/src/services/file_ingest.py` | Pipeline de ingesta | No genera thumbnails durante upload |
| `plugins/public/file-manager/src/services/extraction.py` | Extraccion + OCR | Tiene `generate_pdf_thumbnail_bytes()` listo pero no se usa en upload |
| `apps/backend/src/services/streaming/document_context.py` | Contexto para LLM | max_segments=2, max_text_chars=4000 |
| `apps/web/src/hooks/useFiles.ts` | Hook de upload | SSE tracking, Zustand persistence por chatId |

## Bugs Confirmados

### BUG-1: ThumbnailImage retorna null sin fallback
**Archivo**: `ThumbnailImage.tsx:102-104`
```tsx
if (hasError || !imageUrl) {
    return null; // Let parent component show fallback icon
}
```
**Problema**: El padre `PreviewAttachment` ya eligio `shouldShowFallback=false` porque `canShowThumbnail=true`. Cuando `ThumbnailImage` retorna `null`, queda un espacio vacio. El fallback SVG no se muestra.

**Fix propuesto**: ThumbnailImage debe comunicar el error al padre (callback `onError`) para que PreviewAttachment reactive el fallback.

### BUG-2: Legacy documents sin source file
**Archivo**: `documents.py:299-321`
```python
is_legacy = (
    doc.minio_bucket == "temp"
    and doc.minio_key
    and doc.minio_key.startswith("/tmp/")
)
```
**Problema**: Documentos pre-MinIO guardaron path local en `minio_key`. Despues de restart del container, el archivo ya no existe en `/tmp/`. El endpoint retorna 404 pero el frontend no maneja este caso.

**Fix propuesto**: Para legacy docs, intentar re-upload a MinIO si el archivo aun existe, o mostrar fallback con mensaje "Re-upload necesario".

### BUG-3: Doble renderizado - espacio vacio transitorio
**Archivo**: `PreviewAttachment.tsx:94-97`
```tsx
const canShowThumbnail = (isImage || isPdf) && isReady;
const shouldShowFallback = isProcessing || isFailed || !canShowThumbnail;
```
**Problema**: Cuando `canShowThumbnail=true`, se renderiza `ThumbnailImage` que hace fetch async. Durante el fetch hay un spinner, pero si falla, desaparece todo.

## Puntos de Mejora

### MEJORA-1: Eager thumbnail generation
**Donde**: `file_ingest.py` o background task post-upload
**Que**: Generar thumbnail inmediatamente despues de que el archivo esta en MinIO, en paralelo con text extraction.
**Beneficio**: Primer render del thumbnail es instantaneo (ya cacheado en MinIO).

### MEJORA-2: Presigned URL directa
**Donde**: Thumbnail endpoint retorna URL en vez de bytes
**Que**: Generar presigned URL de MinIO thumbnails bucket, frontend usa `<img src={presignedUrl}>` directamente.
**Beneficio**: Elimina double-hop, reduce latencia, permite cache del browser.
**Riesgo**: Presigned URLs expiran (mitigable con 1h TTL + refresh).

### MEJORA-3: Aumentar contexto RAG
**Donde**: `DocumentContextBuilder.__init__()`
**Que**: `max_segments=5` (de 2), `max_text_chars=12000` (de 4000)
**Beneficio**: Mejor cobertura para documentos largos.
**Riesgo**: Mas tokens en prompt → mas costo. Necesita evaluar tradeoff.

### MEJORA-4: Document summary cache
**Donde**: Nuevo campo en Document model o Redis
**Que**: Generar resumen de 500 chars al momento de ingesta (via LLM o extractive).
**Beneficio**: Referencia rapida sin full RAG, util para multi-turn.

### MEJORA-5: Extender TTL de cache o persistir en MongoDB
**Donde**: `documents.py:REDIS_DOCUMENT_TTL` + Document model
**Que**: Mover texto extraido a MongoDB (persistente) con Redis como cache L1.
**Beneficio**: Contexto disponible indefinidamente, no solo 1 hora.

### MEJORA-6: Estado onError en ThumbnailImage
**Donde**: `ThumbnailImage.tsx` + `PreviewAttachment.tsx`
**Que**: Agregar callback `onError` para que el padre reactive el fallback SVG.
**Beneficio**: Nunca queda espacio vacio - siempre hay feedback visual.

## Prioridad Sugerida

| # | Item | Impacto | Esfuerzo | Prioridad |
|---|------|---------|----------|-----------|
| 1 | BUG-1 + MEJORA-6: Fix fallback thumbnail | Alto | Bajo (1-2h) | P0 |
| 2 | MEJORA-1: Eager thumbnail gen | Alto | Medio (3-4h) | P1 |
| 3 | MEJORA-5: Persistir texto en MongoDB | Alto | Medio (3-4h) | P1 |
| 4 | MEJORA-3: Aumentar segmentos RAG | Medio | Bajo (1h) | P1 |
| 5 | BUG-2: Legacy doc migration | Medio | Medio (2-3h) | P2 |
| 6 | MEJORA-2: Presigned URL | Medio | Alto (4-6h) | P2 |
| 7 | MEJORA-4: Document summary | Bajo | Alto (6-8h) | P3 |
