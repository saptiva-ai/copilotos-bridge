# Guía: Ejecutar Tests E2E de Documentos

Este documento describe cómo ejecutar los tests E2E de documentos (`test_documents.py`) en el proyecto Copilotos Bridge.

## Resumen Ejecutivo

Los tests E2E de documentos prueban:
1. **Idempotencia de uploads**: Verificar que uploads con la misma `Idempotency-Key` devuelven el mismo `file_id`
2. **Autorización SSE**: Verificar que los eventos SSE requieren autenticación JWT

## Prerequisitos

✅ Contenedores corriendo:
```bash
docker ps | grep -E "copilotos-(api|mongodb|redis)"
```

Deberías ver:
- `copilotos-api` (puerto 8001)
- `copilotos-mongodb` (puerto 27018)
- `copilotos-redis` (puerto 6380)

Si no están corriendo:
```bash
cd /home/jazielflo/Proyects/copilotos-bridge
make dev
```

## Problema Identificado

Los tests E2E de documentos tienen un problema de compatibilidad entre:
- **Host local**: Necesita conectarse a `localhost:27018` y `localhost:6380`
- **Contenedor**: Usa hostnames de Docker (`mongodb:27017`, `redis:6379`)

Además, los imports en el test (`from apps.api.src...`) no coinciden con la estructura del contenedor (`/app/src/...`).

## Soluciones Propuestas

### Opción 1: Ejecutar en Contenedor (Recomendado)

**Ventajas**:
- Usa las configuraciones ya existentes del contenedor
- No requiere ajustar variables de entorno

**Desventajas**:
- Requiere ajustar los imports en el test

**Pasos**:
1. Copiar el test al contenedor con imports adaptados
2. Ejecutar pytest dentro del contenedor

**Script disponible**: `run_document_tests_docker.sh` (parcialmente implementado)

### Opción 2: Ejecutar en Host Local

**Ventajas**:
- Usa el venv local ya configurado
- Más fácil para debugging

**Desventajas**:
- Requiere configurar correctamente todas las variables de entorno
- El código de la aplicación construye URLs usando hostnames de Docker

**Script disponible**: `run_document_tests.sh`

**Configuración necesaria**:
```bash
# Cargar variables desde el backup
source /home/jazielflo/Proyects/backup/copilotos-bridge/envs/.env

# Sobrescribir URLs para usar localhost
export MONGODB_URL="mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27018/${MONGODB_DATABASE}?authSource=admin&directConnection=true"
export REDIS_URL="redis://:${REDIS_PASSWORD}@localhost:6380/0"
```

## Problemas Encontrados Durante la Implementación

### 1. Redis: Conexión al puerto incorrecto
**Síntoma**:
```
Redis cache connection failed error="Error 111 connecting to localhost:6379"
```

**Causa**: El código intenta conectarse a `redis:6379` (hostname Docker) en lugar de `localhost:6380` (host local).

**Solución**: Exportar tanto `REDIS_URL` como variables individuales (`REDIS_HOST`, `REDIS_PORT`).

### 2. MongoDB: Hostname incorrecto
**Síntoma**:
```
Connecting to MongoDB url='mongodb:27017/copilotos?authSource=admin'
ServerSelectionTimeoutError: No servers found yet
```

**Causa**: El código de `secrets.py` construye la URL usando variables individuales y usa el hostname `mongodb` en lugar de `localhost`.

**Solución**: Sobrescribir `MONGODB_URL` completo con `localhost:27018`.

### 3. Beanie no inicializado
**Síntoma**:
```
AttributeError: username
```

**Causa**: El fixture `auth_token` intenta usar modelos de Beanie antes de que se inicialicen correctamente.

**Solución**: El test ya tiene `Database.connect_to_mongo()` en el fixture (línea 39).

### 4. Imports incompatibles en contenedor
**Síntoma**:
```
ModuleNotFoundError: No module named 'apps'
```

**Causa**: Los imports como `from apps.api.src.main import app` son relativos al repo root, pero en el contenedor la estructura es `/app/src/`.

**Solución pendiente**: Crear versión del test con imports adaptados para contenedor.

## ✅ Estado Actual: RESUELTO

### Fix Implementado (2025-10-13)

**Archivos modificados**:

1. **`src/core/secrets.py:109-154`** ✅
   - Modificado `get_database_url()` para priorizar URLs completas del entorno
   - Si existe `MONGODB_URL` o `REDIS_URL`, las usa directamente
   - Fallback: construir desde variables individuales (producción)
   - Mantiene compatibilidad con código existente

2. **`src/core/redis_cache.py:30-47`** ✅
   - Cambiado de usar `celery_broker_url` a `redis_url`
   - Ahora respeta `REDIS_URL` del entorno correctamente

### Scripts Creados

1. **`run_document_tests.sh`** ✅ **FUNCIONANDO**
   - Carga variables desde el backup `.env`
   - Sobrescribe URLs para usar localhost
   - Ejecuta pytest en host local
   - **Estado**: ✅ Tests se ejecutan, MongoDB y Redis conectados

2. **`run_document_tests_docker.sh`** ⚠️
   - Ejecuta tests dentro del contenedor
   - **Estado**: Requiere ajustar imports en test (no prioritario)

### Resultados de Tests (2025-10-13)

```bash
$ ./run_document_tests.sh

✅ MongoDB: Conectado a localhost:27018
✅ Redis: Conectado a localhost:6380
✅ Tests ejecutándose
⚠️  test_upload_idempotency: FALLA (bug de idempotencia, no de config)
⚠️  test_sse_requires_authorization: ERROR (event loop closed)
```

**Logs clave**:
- `Successfully connected to MongoDB database=copilotos`
- `Redis cache connected successfully url=localhost:6380/0`
- `Upload stored` - El sistema funciona correctamente

### Ajustes Realizados en `test_documents.py`

✅ Ya implementado en el test original:
- `get_settings.cache_clear()` (línea 36)
- `Database.connect_to_mongo()` si no está conectado (líneas 38-39)

✅ No se requirieron cambios adicionales en el test

## Problemas Restantes (No de Configuración)

Los siguientes problemas son **bugs del código de la aplicación**, no de configuración:

### 1. Test de Idempotencia Fallando

**Síntoma**:
```python
assert '68ed6eb7b7d09c87ebd39e83' == '68ed6eb7b7d09c87ebd39e84'
```

**Causa**:
- Log muestra: `"Failed to deserialize idempotency payload"`
- El payload guardado en Redis tiene un esquema diferente al esperado
- Validación Pydantic falla con 5 errores de campos faltantes

**Solución pendiente**: Revisar `src/schemas/files.py` o el servicio de idempotencia

### 2. Event Loop Cerrado

**Síntoma**:
```
RuntimeError: Event loop is closed
```

**Causa**: Pytest-asyncio cierra el event loop entre tests

**Solución pendiente**: Ajustar configuración de pytest o usar fixtures de sesión

### Solución Alternativa: Tests adaptados para contenedor

**Crear**: `tests/e2e/test_documents_container.py`

Cambios necesarios:
```python
# En vez de:
from apps.api.src.main import app
from apps.api.src.models.document import Document
# ...

# Usar:
from src.main import app
from src.models.document import Document
# ...
```

## ✅ Comando para Ejecutar Tests

```bash
cd /home/jazielflo/Proyects/copilotos-bridge/apps/api
./run_document_tests.sh
```

**Resultado esperado**:
- MongoDB y Redis se conectan correctamente
- Tests se ejecutan (algunos pueden fallar por bugs del código)
- Los errores ya NO son de configuración de URLs

## Referencias

- **Archivo de tests**: `apps/api/tests/e2e/test_documents.py`
- **Credenciales**: `/home/jazielflo/Proyects/backup/copilotos-bridge/envs/.env`
- **Scripts**: `apps/api/run_document_tests*.sh`

## Conclusión

Los tests E2E de documentos requieren ajustes adicionales en:
1. **Código de aplicación**: Para respetar `MONGODB_URL` y `REDIS_URL` del entorno
2. **O en los tests**: Crear versión con imports compatibles con el contenedor

Se recomienda la **Opción 1** (fijar el código de aplicación) ya que beneficiará también a otros escenarios de testing.

---

**Última actualización**: 2025-10-13
**Autor**: Claude Code (sesión con jazielflo)
