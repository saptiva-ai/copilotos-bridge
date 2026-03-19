# Política de Adjuntos - No Herencias Implícitas

**Última actualización:** 2025-10-20
**Estado:** Implementado
**Principio rector:** "Nada de herencias implícitas de adjuntos"

---

## Resumen Ejecutivo

Esta política establece que **cada turno del chat usa exclusivamente los adjuntos enviados en ese turno**. No hay herencia ni acumulación de adjuntos entre turnos.

### Principio Fundamental

> **Política de adjuntos:** Un mensaje guarda exactamente los adjuntos enviados en su payload.
> No existe "herencia" de adjuntos desde turnos previos.
> El adaptador al LLM serializa solo el content del último turno del usuario, con sus imágenes.

---

## Arquitectura de la Solución

### 1. Frontend (Apps/Web)

**Archivo:** `apps/web/src/app/chat/_components/ChatView.tsx`

#### Cambios Implementados

**OBS-1: Log antes de enviar al backend** (Línea ~490)
```typescript
// OBS-1: Log payload before sending to backend
logDebug("[ChatView] payload_outbound", {
  text_len: msg.length,
  file_ids: fileIdsForBackend || [],
  nonce: placeholderId.slice(-8),
  metadata_present: !!userMessageMetadata,
});
```

**Limpieza absoluta de attachments** (Línea ~515)
```typescript
// POLÍTICA: Limpieza absoluta de attachments post-envío
// No heredar adjuntos entre turnos
if (filesV1Attachments.length > 0) {
  clearFilesV1Attachments();
  logDebug(
    "[ChatView] Attachments cleared post-send (no inheritance)",
    {
      cleared_count: filesV1Attachments.length,
    },
  );
}
```

**Comportamiento:**
- Después de `sendChatMessage()` exitoso, limpia TODOS los attachments
- No persiste adjuntos en el estado global para el próximo turno
- Cada turno comienza con estado limpio

---

### 2. Backend - Endpoint (Apps/API)

**Archivo:** `apps/api/src/routers/chat.py`

#### Cambios Implementados

**Eliminación del merge con session_attached_file_ids** (Línea ~233)
```python
# POLÍTICA DE ADJUNTOS: Un mensaje guarda exactamente los adjuntos enviados en su payload.
# No existe "herencia" de adjuntos desde turnos previos.
# Cada turno usa SOLO sus propios file_ids.
request_file_ids = list((request.file_ids or []) + (request.document_ids or []))

# OBS-2: Log post-normalización en backend
logger.info(
    "message_normalized",
    text_len=len(request.message or ""),
    file_ids_count=len(request_file_ids),
    file_ids=request_file_ids,
    nonce=context.request_id[:8]
)
```

**Antes (comportamiento eliminado):**
```python
# ELIMINADO: merge con session_attached_file_ids
merged_file_ids = list(
    dict.fromkeys(request_file_ids + session_file_ids)  # Herencia implícita
)
```

**Después:**
```python
# NUEVO: solo file_ids del request
request_file_ids = list((request.file_ids or []) + (request.document_ids or []))
```

---

### 3. Backend - Adaptador LLM

**Archivos nuevos:**
- `apps/api/src/services/files_presign.py` - Presign service con hash de contenido
- `apps/api/src/services/llm_message_serializer.py` - Serializer de mensajes a formato LLM

#### Arquitectura del Serializer

**Función principal:** `serialize_message_for_llm()`

```python
async def serialize_message_for_llm(
    message: ChatMessage,
    user_id: str,
    include_images: bool = True
) -> Dict[str, Any]:
    """
    Serialize a ChatMessage to LLM API format.

    Política: Las imágenes SOLO viven en el turno donde entraron.
    No se heredan adjuntos de mensajes previos.

    Returns:
        - Text-only: {"role": "user", "content": "text"}
        - Multimodal: {"role": "user", "content": [
            {"type": "text", "text": "..."},
            {"type": "input_image", "image_url": "https://...?hash=abc123"}
          ]}
    """
```

**OBS-3: Log antes de llamar al LLM** (en `build_llm_messages_from_history`)
```python
logger.info("llm_payload_tail",
           last_user_content_parts=len(content),
           text_parts=len(text_parts),
           image_parts=len(image_parts),
           image_url_hashes=image_url_hashes)
```

**Presign con hash de contenido:**
```python
# Genera URL con hash para cache-busting
content_seed = f"{file_id}:{document.filename}:{document.created_at}"
content_hash = hashlib.sha256(content_seed.encode()).hexdigest()[:8]
presigned_url = f"{base_url}/api/files/{file_id}/content?hash={content_hash}"
```

---

## Observabilidad (3 Puntos de Log)

### OBS-1: Frontend → Antes de POST

**Ubicación:** `ChatView.tsx:490`

```typescript
logDebug("[ChatView] payload_outbound", {
  text_len: number,
  file_ids: string[],
  nonce: string,
  metadata_present: boolean
});
```

**Qué verificar:**
- `file_ids` debe contener SOLO los file_ids del turno actual
- No debe incluir file_ids de turnos anteriores

---

### OBS-2: Backend → Post-normalización

**Ubicación:** `chat.py:239`

```python
logger.info("message_normalized",
    text_len=int,
    file_ids_count=int,
    file_ids=list[str],
    nonce=str
)
```

**Qué verificar:**
- `file_ids` debe coincidir con el payload del frontend (OBS-1)
- `file_ids_count` debe ser igual al número de adjuntos enviados en este turno

---

### OBS-3: Adaptador → Justo antes de LLM

**Ubicación:** `llm_message_serializer.py:143`

```python
logger.info("llm_payload_tail",
    last_user_content_parts=int,
    text_parts=int,
    image_parts=int,
    image_url_hashes=list[str]
)
```

**Qué verificar:**
- `image_parts` debe coincidir con `file_ids_count` del turno actual
- `image_url_hashes` debe contener hashes únicos de URLs presignadas
- No debe incluir hashes de imágenes de turnos anteriores

---

## Tests

### Test Unitario: `test_messages_images.py`

**Ubicación:** `apps/api/tests/test_messages_images.py`

#### Test 1: Segunda imagen reemplaza a la primera (Database)
```python
@pytest.mark.asyncio
async def test_second_image_replaces_first_in_message():
    # Verifica que msg_2.file_ids == [file_id_2]
    # NO debe contener file_id_1
```

#### Test 2: Serializer no hereda imágenes
```python
@pytest.mark.asyncio
async def test_llm_serializer_includes_only_message_images():
    # Verifica que serialize_message_for_llm(msg_2)
    # solo incluye file_002, no file_001
```

#### Test 3: Build messages no acumula
```python
@pytest.mark.asyncio
async def test_build_llm_messages_no_accumulation():
    # Verifica que cada mensaje del historial
    # mantiene SOLO sus propios file_ids
```

**Ejecutar tests:**
```bash
cd apps/api
pytest tests/test_messages_images.py -v
```

---

### Script de Verificación: `repro_second_image.sh`

**Ubicación:** `scripts/repro_second_image.sh`

**Uso:**
```bash
# Setup (create fixtures first)
cd scripts/fixtures
# Add meme.png and cover.png

# Run verification
API=http://localhost:8000 TOKEN=your-token ./scripts/repro_second_image.sh
```

**Qué hace:**
1. Sube primera imagen (meme.png) → obtiene `file_id_1`
2. Envía primer mensaje con `file_id_1`
3. Sube segunda imagen (cover.png) → obtiene `file_id_2`
4. Envía segundo mensaje con `file_id_2`
5. Verifica que `file_id_1 != file_id_2`

**Output esperado:**
```
✅ PASS: Two distinct file_ids sent
   Primera: file_abc123
   Segunda: file_def456
```

---

## Fixtures Requeridos

**Ubicación:** `scripts/fixtures/`

Crear dos imágenes de prueba:

1. **meme.png** - Primera imagen (ejemplo: captura de meme/RoboCop)
2. **cover.png** - Segunda imagen (ejemplo: portada de libro)

**Requisitos:**
- Formato: PNG (preferible) o JPG
- Tamaño: < 10 MB
- Contenido visual distinto para verificación manual

**Crear fixtures rápido:**
```bash
mkdir -p scripts/fixtures
# Copiar tus imágenes de prueba
cp ~/Pictures/meme.png scripts/fixtures/
cp ~/Pictures/cover.png scripts/fixtures/
```

---

## Verificación del Fix (Checklist)

### Logs muestran comportamiento correcto

- [ ] OBS-1: `payload_outbound` muestra solo file_ids del turno actual
- [ ] OBS-2: `message_normalized` coincide con OBS-1
- [ ] OBS-3: `llm_payload_tail` muestra `image_url_hashes` correctos

### Tests pasan

- [ ] `test_second_image_replaces_first_in_message` → PASS
- [ ] `test_llm_serializer_includes_only_message_images` → PASS
- [ ] `test_build_llm_messages_no_accumulation` → PASS

### Script de verificación pasa

- [ ] `repro_second_image.sh` → ✅ PASS: Two distinct file_ids sent

### URLs presignadas no colisionan

- [ ] URLs incluyen `?hash={content_hash}` para cache-busting
- [ ] No se observan respuestas cacheadas incorrectas en CDN

---

## Casos de Uso

### Caso 1: Usuario envía imagen, luego otra

**Flujo:**
1. Usuario adjunta `gato.png` y envía "¿Qué animal es?"
2. Sistema guarda mensaje con `file_ids: ["file_001"]`
3. LLM recibe `[{type: "text", ...}, {type: "input_image", image_url: "...file_001..."}]`
4. Usuario adjunta `perro.png` y envía "¿Y este?"
5. Sistema guarda mensaje con `file_ids: ["file_002"]` (NO ["file_001", "file_002"])
6. LLM recibe SOLO `perro.png` en el segundo turno

**Resultado esperado:**
- LLM responde sobre el perro (segunda imagen)
- NO responde sobre el gato (primera imagen no está en el payload)

---

### Caso 2: Usuario envía texto sin imágenes después de imagen

**Flujo:**
1. Usuario adjunta `factura.pdf` y envía "Resúmelo"
2. Sistema guarda mensaje con `file_ids: ["file_003"]`
3. Usuario envía "¿Cuál es el total?" (sin adjuntos)
4. Sistema guarda mensaje con `file_ids: []`
5. LLM recibe solo texto en el segundo turno

**Resultado esperado:**
- LLM debe responder basándose en el historial textual
- NO debe recibir la factura.pdf nuevamente en el payload

**Nota:** Si el usuario quiere referirse a la factura anterior, debe re-adjuntarla o el LLM debe usar contexto del historial de mensajes previos (texto).

---

## Decision Records

### ¿Por qué eliminar session_attached_file_ids?

**Antes:** El sistema "mergeaba" file_ids del request con los del session, acumulando adjuntos.

**Problema:** Esto causaba que:
- La segunda imagen se enviaba JUNTO con la primera al LLM
- No había forma de "reemplazar" una imagen, solo acumular
- Consumía tokens innecesarios enviando imágenes antiguas

**Solución:** Eliminar el merge. Cada turno usa SOLO sus propios file_ids.

---

### ¿Por qué limpiar attachments en el frontend?

**Antes:** `useFiles` persistía attachments en `filesStore` por `chatId`, y NO limpiaba automáticamente.

**Problema:**
- El usuario veía la imagen previa en el composer del siguiente turno
- Si no la removía manualmente, se re-enviaba implícitamente

**Solución:** `clearFilesV1Attachments()` inmediatamente después de `sendChatMessage()` exitoso.

---

### ¿Por qué presign con hash de contenido?

**Problema:** CDN/browser cache podía servir imagen antigua si la URL era idéntica.

**Solución:** Incluir `?hash={sha256[:8]}` en la URL presignada, único por `file_id + filename + created_at`.

**Trade-off:** Si el mismo archivo se sube dos veces, genera dos URLs distintas (ineficiencia menor vs. correctitud).

---

## Limitaciones Conocidas

### 1. Sin soporte para "contexto multi-imagen"

**Escenario no soportado:**
```
Usuario: *adjunta imagen1.png* "Compara con imagen2.png"
```

**Razón:** Para enviar dos imágenes en un turno, ambas deben adjuntarse en el mismo mensaje.

**Workaround:** Usuario debe re-adjuntar imagen1.png junto con imagen2.png en el mismo turno.

---

### 2. LLM no "recuerda" imágenes previas por payload

**Comportamiento actual:**
- Si un turno previo tenía una imagen, el LLM solo la "vio" en ese turno
- En turnos posteriores, el LLM solo tiene el texto de su respuesta previa, no la imagen

**Implicaciones:**
- El usuario no puede decir "¿y la primera imagen?" sin re-adjuntarla
- El LLM puede responder basándose en su descripción textual previa (del historial de mensajes)

**Solución futura:** Implementar "memory" de imágenes con embeddings visuales persistentes.

---

## Migraciones y Retrocompatibilidad

### Datos Existentes

**Mensajes antiguos con session_attached_file_ids:**
- Los mensajes existentes en MongoDB mantienen sus `file_ids` como fueron guardados
- No se requiere migración de datos
- La nueva lógica solo afecta mensajes nuevos

### Sesiones Antiguas

**ChatSession.attached_file_ids:**
- Este campo ya no se usa para "mergear" con nuevos mensajes
- Se mantiene por retrocompatibilidad, pero no afecta el comportamiento nuevo
- Futuro: Deprecar y remover este campo (breaking change)

---

## Soporte y Troubleshooting

### Problema: Segunda imagen no aparece en la respuesta

**Diagnóstico:**
1. Revisar logs OBS-1: ¿Se envió el `file_id` correcto?
2. Revisar logs OBS-2: ¿El backend recibió el `file_id`?
3. Revisar logs OBS-3: ¿El payload al LLM incluyó la `image_url`?
4. Verificar presign: ¿La URL es válida y no expiró?

**Soluciones:**
- Si OBS-1 está mal: Problema en el frontend (attachments no limpiados)
- Si OBS-2 está mal: Problema en el endpoint (merge incorrecto)
- Si OBS-3 está mal: Problema en el serializer (presign falló)

---

### Problema: Primera imagen sigue apareciendo en segundo turno

**Causa probable:** Frontend no limpió attachments post-envío.

**Verificación:**
```typescript
// Buscar en ChatView.tsx
if (filesV1Attachments.length > 0) {
  clearFilesV1Attachments();  // ← Debe ejecutarse
}
```

**Fix:** Asegurar que `clearFilesV1Attachments()` se llama SIEMPRE después de éxito, no solo si `readyFiles.length > 0`.

---

## Roadmap Futuro

### Corto plazo (Sprint actual)
- [x] Implementar política "no herencias"
- [x] Agregar observabilidad (3 logs)
- [x] Escribir tests unitarios
- [ ] Ejecutar tests E2E con Playwright (opcional)
- [ ] Validar con usuarios beta

### Mediano plazo (Próximo mes)
- [ ] Implementar caché de embeddings visuales para "memoria" de imágenes
- [ ] Agregar UI para "re-adjuntar imagen previa" con un click
- [ ] Deprecar `ChatSession.attached_file_ids`
- [ ] Soporte para comparación multi-imagen en un turno

### Largo plazo (Trimestre)
- [ ] Implementar "visual RAG" con búsqueda de imágenes previas
- [ ] Soporte para videos (frames → imágenes)
- [ ] Optimización de presign: pooling de URLs para reducir S3 calls

---

## Referencias

- **Código Backend:** `apps/api/src/routers/chat.py`
- **Código Frontend:** `apps/web/src/app/chat/_components/ChatView.tsx`
- **Serializer LLM:** `apps/api/src/services/llm_message_serializer.py`
- **Tests:** `apps/api/tests/test_messages_images.py`
- **Script:** `scripts/repro_second_image.sh`
- **Fixtures:** `scripts/fixtures/`

---

**Fin del documento**
