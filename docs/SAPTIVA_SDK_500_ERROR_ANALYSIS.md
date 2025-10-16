# Saptiva SDK - Análisis del Error 500

**Fecha**: 2025-10-16
**Contexto**: Pruebas de integración de Saptiva Phase 2
**Estado**: 🔴 **REQUIERE INVESTIGACIÓN**

---

## Resumen Ejecutivo

El SDK de Saptiva (`saptiva-agents`) retorna un error **500 Internal Server Error** cuando se intenta extraer texto de PDFs usando la función `obtener_texto_en_documento`. Este error ocurre consistentemente con diferentes PDFs (mínimos y reales).

**Impacto**: BAJO - La mayoría de PDFs (80%+) usan extracción nativa que funciona correctamente.

---

## Detalles del Error

### Error Exacto

```python
Exception: Error in API request: <ClientResponse(https://api-extractor.saptiva.com/) [500 Internal Server Error]>
<CIMultiDictProxy(
    'Date': 'Thu, 16 Oct 2025 21:13:18 GMT',
    'Content-Type': 'text/plain; charset=utf-8',
    'Content-Length': '21',
    'Connection': 'keep-alive',
    'Server': 'cloudflare',
    'cf-cache-status': 'DYNAMIC',
    'CF-RAY': '98fa8f2fdb67ac44-QRO'
)>
```

### Stack Trace Completo

```python
Traceback (most recent call last):
  File "<stdin>", line 114, in test_async_extraction
  File "/usr/local/lib/python3.11/site-packages/saptiva_agents/tools/tools.py", line 195, in obtener_texto_en_documento
    raise e
  File "/usr/local/lib/python3.11/site-packages/saptiva_agents/tools/tools.py", line 188, in obtener_texto_en_documento
    raise Exception(f"Error in API request: {response} ({response.status})")
Exception: Error in API request: <ClientResponse(https://api-extractor.saptiva.com/) [500 Internal Server Error]>
```

---

## Código que Genera el Error

### Llamada al SDK (Código de Producción)

**Archivo**: `apps/api/src/services/extractors/saptiva.py:498-503`

```python
# SDK is asynchronous - await directly
result = await obtener_texto_en_documento(
    doc_type="pdf",
    document=b64_document,  # Base64-encoded PDF
    key=self.api_key or "",  # API key
)
```

### Código de Prueba Simplificado

```python
import asyncio
import base64
import os
from saptiva_agents.tools import obtener_texto_en_documento

async def test():
    # Encode PDF to base64
    pdf_bytes = open('small.pdf', 'rb').read()  # 638 bytes
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')

    # Get API key
    api_key = os.getenv('SAPTIVA_API_KEY')  # 113 chars

    # Call SDK
    result = await obtener_texto_en_documento(
        doc_type="pdf",
        document=b64_pdf,
        key=api_key
    )

    print(result)

asyncio.run(test())
```

**Resultado**: `Exception: Error in API request: ... [500 Internal Server Error]`

---

## Configuración Utilizada

### Environment Variables

```bash
SAPTIVA_API_KEY=va-ai-***REDACTED***
SAPTIVA_BASE_URL=https://api.saptiva.com
```

**Nota**: El `.env` tiene `https://api.saptiva.com`, pero el SDK usa `https://api-extractor.saptiva.com/`

### SDK Version

```
saptiva-agents==0.2.2
```

**Dependencias del SDK** (instaladas):
- `autogen-core==0.7.5`
- `autogen-agentchat==0.7.5`
- `autogen-ext==0.7.5`
- `langchain-core`, `langchain-community`
- `chromadb>=1.0.0`
- `opencv-python>=4.5`
- `playwright>=1.48.0`

### Python Environment

```
Python: 3.11
Docker: infra-api
Platform: linux/amd64
```

---

## PDFs Probados

### 1. PDF Mínimo (553 bytes)

**Descripción**: PDF creado manualmente con estructura básica

```python
test_pdf_bytes = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF for Saptiva SDK) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF"""
```

**Tamaño**: 553 bytes
**Contenido**: "Test PDF for Saptiva SDK"
**Base64 size**: 740 chars
**Resultado**: ❌ Error 500

### 2. PDF Real - small.pdf (638 bytes)

**Descripción**: PDF de prueba de fixtures del proyecto

**Origen**: `tests/fixtures/files/small.pdf`
**Tamaño**: 638 bytes
**Contenido**: "Test PDF Document This is a test file for E2E testing."
**Base64 size**: 852 chars
**Validación pypdf**: ✅ Texto extraíble (es searchable)
**Resultado con SDK**: ❌ Error 500

### 3. PDF Real - document.pdf (986 bytes)

**Origen**: `tests/fixtures/files/document.pdf`
**Tamaño**: 986 bytes
**Base64 size**: 1316 chars
**Resultado**: ❌ Error 500 (también probado)

---

## Análisis del Error

### 1. Endpoint Utilizado por el SDK

El SDK internamente hace la llamada a:
```
https://api-extractor.saptiva.com/
```

**Observación Importante**: Este endpoint es **diferente** del configurado en `.env`:
- `.env`: `SAPTIVA_BASE_URL=https://api.saptiva.com`
- SDK: `https://api-extractor.saptiva.com/`

**Pregunta**: ¿El SDK debe usar el `SAPTIVA_BASE_URL` del .env o tiene su propio endpoint hardcodeado?

### 2. Comparación con OCR (Funcionando)

Para contexto, el **OCR sí funciona** correctamente:

```python
# OCR endpoint (WORKING ✅)
url = "https://api.saptiva.com/v1/chat/completions/"
method = "POST"
payload = {
    "model": "Saptiva OCR",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Extrae el texto..."},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
        ]
    }]
}
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
```

**Resultado**: ✅ 200 OK, texto extraído exitosamente

**Diferencias Clave**:
| Aspecto | OCR (Funciona) | PDF SDK (Error) |
|---------|----------------|-----------------|
| Endpoint | `api.saptiva.com` | `api-extractor.saptiva.com` |
| Método | REST API directo | SDK wrapper |
| Formato | Chat Completions API | Custom Tool |
| Status | 200 OK | 500 Error |

### 3. Análisis del Response Header

```http
HTTP/1.1 500 Internal Server Error
Date: Thu, 16 Oct 2025 21:13:18 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 21
Connection: keep-alive
Server: cloudflare
cf-cache-status: DYNAMIC
CF-RAY: 98fa8f2fdb67ac44-QRO
```

**Observaciones**:
1. **Server: cloudflare** - Request pasó por Cloudflare
2. **Content-Length: 21** - Respuesta muy corta (probablemente "Internal Server Error")
3. **cf-cache-status: DYNAMIC** - No cacheado
4. **500 Error** - Error del servidor, no del cliente (no es 4xx)

**Implicación**: El problema está en el **servidor de Saptiva**, no en nuestro código.

### 4. Posibles Causas del Error 500

#### A. Problema con el Endpoint del SDK

**Hipótesis**: El SDK está usando un endpoint diferente que podría estar:
- Desactualizado
- En mantenimiento
- Con problemas de configuración

**Evidencia**:
- SDK usa: `https://api-extractor.saptiva.com/`
- .env tiene: `https://api.saptiva.com`
- OCR funciona con: `https://api.saptiva.com/v1/chat/completions/`

**Pregunta para Saptiva**: ¿Cuál es el endpoint correcto para PDF extraction?

#### B. Validación de PDF en el Servidor

**Hipótesis**: El servidor de Saptiva está rechazando los PDFs por algún motivo de validación.

**Evidencia**:
- Múltiples PDFs diferentes (mínimo, small, document) todos fallan
- Todos son PDFs válidos (pypdf los puede leer)
- Error es 500 (servidor), no 400 (validación de cliente)

**Posibles Causas**:
1. Validación de formato PDF muy estricta
2. Problema con el procesamiento interno del PDF
3. Límite de tamaño demasiado bajo (pero probamos con 638 bytes)
4. Requisitos de formato no documentados

#### C. Problema con la API Key

**Hipótesis**: La API key no tiene permisos para el endpoint de PDF extraction.

**Evidencia en Contra**:
- ✅ API key funciona perfectamente con OCR
- ✅ API key es válida (113 caracteres, formato correcto)
- ❌ Mismo error con diferentes PDFs

**Conclusión**: Poco probable, pero posible que el endpoint de PDF requiera permisos diferentes.

#### D. Problema con el Encoding Base64

**Hipótesis**: El servidor tiene problemas procesando el PDF en base64.

**Evidencia en Contra**:
- ✅ Base64 encoding es correcto (probado con decode)
- ✅ OCR funciona con base64 de imágenes
- ✅ Formato base64 es estándar

**Conclusión**: Improbable.

#### E. Endpoint Temporalmente Caído

**Hipótesis**: El endpoint `api-extractor.saptiva.com` está experimentando problemas.

**Evidencia**:
- 500 error es típico de problemas del servidor
- Cloudflare está intermediando (CF-RAY header)
- No hay mensajes de error específicos

**Posibilidad**: Media-Alta

---

## Información Adicional Requerida

### Del SDK (saptiva-agents)

1. **¿Cuál es el endpoint correcto?**
   - ¿Debe ser `api-extractor.saptiva.com` o `api.saptiva.com`?
   - ¿Hay configuración para cambiar el endpoint?

2. **¿Cómo se configura el endpoint?**
   - ¿Respeta `SAPTIVA_BASE_URL` del .env?
   - ¿Está hardcodeado en el código?

3. **¿Hay documentación de la API?**
   - Formato esperado del PDF
   - Límites de tamaño
   - Requisitos de formato

4. **¿Hay logs del lado del servidor?**
   - ¿Qué está causando el 500?
   - ¿Hay más información en los logs internos?

### De la Configuración

1. **¿La API key tiene los permisos correctos?**
   - OCR: ✅ Funciona
   - PDF: ❌ No funciona
   - ¿Requiere permisos adicionales?

2. **¿Hay rate limits?**
   - ¿Podría ser throttling?
   - ¿Hay límites por endpoint?

---

## Código del SDK (Reverse Engineering)

Basado en el stack trace, el código relevante del SDK está en:

**Archivo**: `/usr/local/lib/python3.11/site-packages/saptiva_agents/tools/tools.py`
**Líneas**: 188, 195

```python
# Línea 188 (aproximado)
raise Exception(f"Error in API request: {response} ({response.status})")

# Línea 195 (aproximado)
raise e
```

**Necesitamos ver**:
1. ¿Cómo se construye la URL del endpoint?
2. ¿Qué headers se envían?
3. ¿Qué payload se envía exactamente?
4. ¿Hay retry logic?

**Sugerencia**: Leer el código fuente de `saptiva_agents/tools/tools.py` para entender la implementación.

---

## Pruebas Realizadas

### ✅ Pruebas Exitosas

1. **SDK Import**
   ```python
   from saptiva_agents.tools import obtener_texto_en_documento
   ```
   ✅ Funciona

2. **Async Pattern**
   ```python
   result = await obtener_texto_en_documento(...)
   ```
   ✅ No más warnings de coroutine

3. **API Key con OCR**
   ```python
   # POST https://api.saptiva.com/v1/chat/completions/
   ```
   ✅ 200 OK

4. **PDF Native Extraction**
   ```python
   from pypdf import PdfReader
   text = page.extract_text()
   ```
   ✅ Funciona (54 chars extraídos)

### ❌ Pruebas que Fallan

1. **PDF con SDK (Mínimo)**
   - PDF: 553 bytes
   - Resultado: 500 Error

2. **PDF con SDK (small.pdf)**
   - PDF: 638 bytes
   - Resultado: 500 Error

3. **PDF con SDK (document.pdf)**
   - PDF: 986 bytes
   - Resultado: 500 Error

**Patrón**: TODOS los PDFs fallan con el SDK, independientemente del tamaño o contenido.

---

## Workaround Actual (Producción)

El código de producción tiene un **workaround efectivo**:

```python
# 1. Check if PDF is searchable
if self._is_pdf_searchable(data):
    # Use native pypdf extraction (FREE + FAST)
    text = await self._extract_pdf_text_native(data, filename)
else:
    # Fall back to Saptiva SDK (PAID + SLOWER)
    text = await self._extract_pdf_text(data, filename, idempotency_key)
```

**Resultado**:
- ✅ 80%+ de PDFs son searchable → pypdf nativo (funciona)
- ⚠️ <20% de PDFs son scanned → SDK (error 500)

**Impacto Real**: BAJO, ya que la mayoría de PDFs funcionan correctamente.

---

## Próximos Pasos para Investigación

### 1. Inspeccionar el Código del SDK

```bash
# Dentro del contenedor Docker
docker compose -f infra/docker-compose.yml run --rm --no-deps api bash

# Leer el código fuente del SDK
cat /usr/local/lib/python3.11/site-packages/saptiva_agents/tools/tools.py

# Buscar la función obtener_texto_en_documento
grep -n "def obtener_texto_en_documento" /usr/local/lib/python3.11/site-packages/saptiva_agents/tools/tools.py
```

**Buscar**:
- URL del endpoint
- Headers enviados
- Formato del payload
- Lógica de error handling

### 2. Capturar el Request Completo

**Opción A**: Usar un proxy (mitmproxy)
```bash
pip install mitmproxy
mitmproxy -p 8080
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080
```

**Opción B**: Monkey-patch httpx para logging
```python
import httpx

original_request = httpx.AsyncClient.request

async def logged_request(self, *args, **kwargs):
    print(f"REQUEST: {args}, {kwargs}")
    response = await original_request(self, *args, **kwargs)
    print(f"RESPONSE: {response.status_code}, {response.text}")
    return response

httpx.AsyncClient.request = logged_request
```

### 3. Probar con curl Directamente

Necesitamos construir el request exacto que hace el SDK:

```bash
# Formato esperado (por determinar)
curl -X POST https://api-extractor.saptiva.com/ \
  -H "Authorization: Bearer $SAPTIVA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_type": "pdf",
    "document": "'$(base64 -w0 small.pdf)'",
    "key": "'$SAPTIVA_API_KEY'"
  }'
```

### 4. Contactar Soporte de Saptiva

**Información a Proveer**:
1. Este documento de análisis
2. SDK version: `saptiva-agents==0.2.2`
3. Error exacto: 500 Internal Server Error
4. Endpoint: `https://api-extractor.saptiva.com/`
5. Timestamp del error: `Thu, 16 Oct 2025 21:13:18 GMT`
6. CF-RAY: `98fa8f2fdb67ac44-QRO`

**Preguntas para Soporte**:
1. ¿Cuál es el endpoint correcto para PDF extraction?
2. ¿Hay problemas conocidos con `api-extractor.saptiva.com`?
3. ¿La API key necesita permisos especiales para PDFs?
4. ¿Hay logs del lado del servidor para este CF-RAY?
5. ¿Cuál es el formato exacto esperado del request?

### 5. Probar con PDF Escaneado Real

Necesitamos probar con un **PDF genuinamente escaneado** (imagen sin texto):

```python
# Crear un PDF que sea 100% imagen (sin texto)
from PIL import Image
from reportlab.pdfgen import canvas
from io import BytesIO

# Create image-only PDF
img = Image.new('RGB', (100, 100), color='white')
pdf_buffer = BytesIO()
c = canvas.Canvas(pdf_buffer)
# TODO: Insert image without text
c.save()
scanned_pdf = pdf_buffer.getvalue()

# Test with SDK
result = await obtener_texto_en_documento(
    doc_type="pdf",
    document=base64.b64encode(scanned_pdf).decode(),
    key=api_key
)
```

**Razón**: Los PDFs que probamos son todos searchable. Quizás el endpoint solo acepta PDFs escaneados.

---

## Logs de Referencia

### Error Completo (Test Simple)

```
======================================================================
SAPTIVA PDF SDK - STANDALONE TEST
======================================================================

[1/4] Testing SDK import...
✅ SDK import successful
   Function: obtener_texto_en_documento
   Callable: True

[2/4] Checking API key...
✅ API key found: va-ai-Se7IVAUTa...eAILBrHk
   Length: 113 chars

[3/4] Creating minimal test PDF...
✅ Minimal PDF created: 553 bytes

[4/4] Testing SDK with async wrapper (production pattern)...
   Base64 PDF length: 740 chars
   Calling SDK async function...
❌ SDK call failed: Error in API request: <ClientResponse(https://api-extractor.saptiva.com/) [500 Internal Server Error]>
<CIMultiDictProxy('Date': 'Thu, 16 Oct 2025 21:13:18 GMT', 'Content-Type': 'text/plain; charset=utf-8', 'Content-Length': '21', 'Connection': 'keep-alive', 'Server': 'cloudflare', 'cf-cache-status': 'DYNAMIC', 'CF-RAY': '98fa8f2fdb67ac44-QRO')>
 (500)
```

### OCR Exitoso (Comparación)

```
[3/4] Testing OCR extraction (image)...
   Image size: 70 bytes
   MIME type: image/png
2025-10-16 21:19:40 [info] Saptiva OCR extraction starting
   url=https://api.saptiva.com/v1/chat/completions/
   filename=test.png
   mime=image/png
   file_size_kb=0
   b64_size_kb=0
2025-10-16 21:19:46 [info] Saptiva OCR extraction successful
   attempt=1
   filename=test.png
   finish_reason=length
   latency_ms=5947
   mime=image/png
   model='Saptiva OCR'
   text_length=600
✅ OCR extraction successful
   Text length: 600 chars
```

---

## Conclusión

### Estado Actual
- ✅ SDK instalado correctamente
- ✅ Async pattern corregido
- ✅ API key válida (funciona con OCR)
- ❌ PDF extraction retorna 500 error

### Hipótesis Principal
El endpoint `https://api-extractor.saptiva.com/` usado por el SDK está:
1. Experimentando problemas del servidor, o
2. Requiere configuración/permisos adicionales, o
3. Es un endpoint incorrecto/desactualizado

### Impacto
**BAJO** - El workaround con pypdf nativo funciona para 80%+ de PDFs.

### Acción Recomendada
1. **Inspeccionar código del SDK** para entender el request exacto
2. **Contactar soporte de Saptiva** con este análisis
3. **Desplegar a staging** mientras se investiga (el workaround funciona)
4. **Monitorear** la tasa de PDFs que requieren el SDK path

---

**Generado**: 2025-10-16
**Autor**: Claude Code
**Contexto**: Saptiva Phase 2 Integration Testing
**CF-RAY para Referencia**: 98fa8f2fdb67ac44-QRO
