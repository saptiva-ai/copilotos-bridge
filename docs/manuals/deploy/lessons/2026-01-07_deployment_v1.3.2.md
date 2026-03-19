# Deployment Report - Version 1.3.2

> **⚠️ SUPERSEDED**: This deployment was superseded by **v1.3.7** (backend) and **v1.3.5** (web) on 2026-01-07.
> The RAG/Weaviate issues documented here were resolved using `connect_to_weaviate_cloud()`.
> See `docker-compose.images.yml` for current production versions.

**Date**: 2026-01-07
**Server**: ${DEPLOY_USER}@${PROD_SERVER_IP}
**Status**: 📦 ARCHIVED - Superseded by v1.3.7/v1.3.5 deployment
**Related**: ISSUE-002 (✅ DONE)
**Hotfixes**: 1.3.3-clarification-fix → 1.3.5 (web), 1.3.5 → 1.3.7 (backend)

---

## Executive Summary

Deployment de imágenes 1.3.2 completado con éxito parcial + hotfix 1.3.3:
- ✅ **Core functionality (NL2SQL)**: Funcionando correctamente
- ✅ **Web frontend**: Healthy con fix de cache + clarification hotfix (1.3.3)
- ✅ **Sharp image optimization**: Instalado y funcionando
- ✅ **Clarification rendering**: Fixed en hotfix 1.3.3 (data contract adapter)
- ❌ **RAG queries**: Deshabilitado por problema de configuración en bank-advisor

**Impacto en usuarios**:
- Queries específicas de métricas (ej: "Dame el ICAP de INVEX") funcionan ✅
- Clarificaciones interactivas (ej: "Selecciona tipo de cartera") funcionan ✅
- Queries generales de conocimiento (ej: "Cuéntame sobre banca mexicana") no funcionan ❌

---

## Deployment Timeline

| Paso | Duración | Status | Notas |
|------|----------|--------|-------|
| Pre-checks | 5 min | ✅ | SSH, espacio disco, servicios verificados |
| MongoDB backup | 3 min | ✅ | 24KB backup creado |
| Pull imágenes 1.3.2 | 8 min | ✅ | Backend 13GB, Web 502MB, Bank-Advisor 17.5GB |
| Update código | 2 min | ✅ | Git pull main (807838f → 1e8b95b) |
| Deploy servicios | 3 min | ✅ | Todos healthy |
| Debug RAG | 45 min | ⚠️ | Problema identificado, fix pendiente |
| Fix cache permissions | 2 min | ✅ | Hotfix aplicado |
| **TOTAL** | **~68 min** | ⚠️ | |

---

## Changes Deployed

### Successfully Deployed

#### 1. Backend (saptivaai/octavios-invex-backend:1.3.2)
- Imagen: 13GB
- Status: Healthy
- Volumen `backend_shared` creado y montado en `/app/src`

#### 2. Web (saptivaai/octavios-invex-web:1.3.2)
- Imagen: 502MB (+195MB vs 1.3.1 por Sharp)
- Status: Healthy
- **Cambios incluidos**:
  - ✅ Cache directory fix (Dockerfile:126-128)
  - ✅ Sharp 0.33.0 instalado
  - ⚠️ **Hotfix aplicado**: Permisos de `/app/apps/web/.next/cache/images`

#### 3. Bank-Advisor (saptivaai/octavios-invex-bank-advisor:1.3.2)
- Imagen: 17.5GB
- Status: Healthy
- ⚠️ **RAG deshabilitado** (ver problema abajo)

#### 4. Infrastructure
- ✅ Volumen `backend_shared` creado
- ✅ Variables `ENABLE_RAG=true` configuradas
- ✅ Mount `backend_shared:/backend_shared/src:ro` en bank-advisor

---

## Known Issues

### Issue 1: RAG/Weaviate Connection Failure

**Severity**: HIGH
**Impact**: Queries de conocimiento general (RAG) no funcionan
**Status**: ❌ BLOQUEADO - Weaviate SDK incompatible con producción

---

## Cronología de Issues y Fixes

### 1️⃣ RAG Import Error (✅ FIXED - Commit f165d7ca)

#### Síntoma Original
```log
2026-01-07 20:43:55 [warning] rag_bridge.import_failed error="No module named 'src.services'"
```

#### Root Cause
Tres bugs en `rag_bridge.py`:
1. ENV variable mismatch: `BACKEND_SRC_PATH` (código) vs `BACKEND_SHARED_PATH` (docker-compose)
2. Import path error: `from src.services.*` pero volumen monta contenido directamente en `/backend_shared/`
3. Deprecated module: Importaba `qdrant_service` en lugar de `weaviate_service`

#### Fix Aplicado
**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/services/rag_bridge.py`
```python
# Antes
backend_path = os.getenv("BACKEND_SRC_PATH", "/backend_shared")
from src.services.qdrant_service import get_qdrant_service

# Después
backend_path = os.getenv("BACKEND_SHARED_PATH", "/backend_shared")
from services.weaviate_service import get_weaviate_service
```

**Imagen**: `saptivaai/octavios-invex-bank-advisor:1.3.3-rag-fix`
**Resultado**: ✅ Import exitoso, pero nueva error de conexión

---

### 2️⃣ Weaviate HTTPS Connection Error (✅ FIXED - Commit b14e4427)

#### Síntoma
```log
Failed to connect to Weaviate  error='timed out'
rag_bridge.weaviate_unavailable error="'NoneType' object has no attribute 'is_connected'"
```

#### Root Cause
WeaviateService hardcoded `http_secure=False` y `grpc_secure=False`, causando timeout al conectar a Weaviate Cloud (HTTPS).

#### Fix Aplicado
**Archivo**: `apps/backend/src/services/weaviate_service.py`
```python
# Detectar scheme de URL
parsed = urlparse(self.url)
self.http_secure = (parsed.scheme == "https")
self.grpc_secure = self.http_secure

# Ports correctos
default_port = 443 if self.http_secure else 8080
self.port = parsed.port or default_port
```

**Imagen**: `saptivaai/octavios-invex-backend:1.3.3-weaviate-fix`
**Resultado**: ✅ Detección HTTPS funciona, pero nueva error de autenticación

---

### 3️⃣ Weaviate API Key Authentication Missing (✅ FIXED - Commit 9a876f36)

#### Síntoma
```log
Failed to connect to Weaviate  error='timed out'
```

#### Root Cause
Conexión sin autenticación. Weaviate Cloud requiere API key.

#### Fix Aplicado
**Archivo**: `apps/backend/src/services/weaviate_service.py`
```python
# Leer API key
self.api_key = os.getenv("WEAVIATE_API_KEY")

# Configurar auth
auth_config = None
if self.api_key:
    auth_config = weaviate_init.Auth.api_key(self.api_key)

self.client = weaviate.connect_to_custom(
    ...,
    auth_credentials=auth_config
)
```

**Imagen**: `saptivaai/octavios-invex-backend:1.3.4`
**Resultado**: ✅ API key configurado, pero nueva error de puertos

---

### 4️⃣ Weaviate gRPC Port Conflict (❌ BLOQUEADO - Commit 98d3bf16)

#### Síntoma Final
```log
ValidationError: 1 validation error for ConnectionParams
  Value error, http.port and grpc.port must be different if using the same host
  [input_value={'http': ProtocolParams(host='...', port=443, secure=True),
                'grpc': ProtocolParams(host='...', port=443, secure=True)}]
```

#### Root Cause
Weaviate Python SDK v4 validation: **No permite usar el mismo puerto para HTTP y gRPC en el mismo host**.

#### Fix Intentado
**Archivo**: `apps/backend/src/services/weaviate_service.py`
```python
# Siempre usar gRPC en puerto 50051
self.grpc_port = 50051  # Weaviate default para gRPC
```

**Imagen**: `saptivaai/octavios-invex-backend:1.3.5`
**Resultado**: ❌ **MISMO ERROR** - Weaviate Cloud solo expone puerto 443

---

## Problema Bloqueante Identificado

### Incompatibilidad Weaviate Cloud + Python SDK

**Configuración Weaviate Cloud**:
- URL: `https://r9zaltjsngkmowhfek7iw.c0.us-west3.gcp.weaviate.cloud`
- Puerto expuesto: **443 únicamente** (HTTPS + gRPC multiplexado)
- Autenticación: API key requerido

**Requisito Python SDK**:
```python
# weaviate-client v4 validation
if http_host == grpc_host and http_port == grpc_port:
    raise ValidationError("http.port and grpc.port must be different if using same host")
```

**Conflicto**:
- Cloud necesita: `http://host:443` + `grpc://host:443` (mismo puerto, gRPC sobre HTTP/2)
- SDK requiere: `http://host:443` + `grpc://host:50051` (puertos diferentes)
- Cloud **NO expone** puerto 50051 → Conexión falla

---

## Intentos de Fix Documentados

| # | Cambio | Archivo | Resultado | Imagen |
|---|--------|---------|-----------|--------|
| 1 | Fix ENV var name: `BACKEND_SRC_PATH` → `BACKEND_SHARED_PATH` | rag_bridge.py | ✅ Import ok | 1.3.3-rag-fix |
| 2 | Fix import path: `from src.services` → `from services` | rag_bridge.py | ✅ Import ok | 1.3.3-rag-fix |
| 3 | Fix module name: `qdrant_service` → `weaviate_service` | rag_bridge.py | ✅ Import ok | 1.3.3-rag-fix |
| 4 | Auto-detect HTTPS: `http_secure = (scheme == "https")` | weaviate_service.py | ✅ HTTPS ok | 1.3.3-weaviate-fix |
| 5 | Add API key auth: `Auth.api_key(self.api_key)` | weaviate_service.py | ✅ Auth ok | 1.3.4 |
| 6 | Use gRPC port 50051 instead of 443 | weaviate_service.py | ❌ Port 50051 no expuesto | 1.3.5 |
| 7 | Recreate backend_shared volume (código stale) | docker | ❌ Mismo error | - |

---

## Soluciones Posibles

### Opción A: Usar `weaviate.connect_to_weaviate_cloud()` ⭐ RECOMENDADO
Usar método específico para Weaviate Cloud en lugar de `connect_to_custom()`:

```python
import weaviate
from weaviate.classes.init import Auth

client = weaviate.connect_to_weaviate_cloud(
    cluster_url="r9zaltjsngkmowhfek7iw.c0.us-west3.gcp.weaviate.cloud",
    auth_credentials=Auth.api_key(api_key),
    skip_init_checks=True
)
```

**Pro**: Método oficial para cloud, maneja gRPC/HTTP multiplexing automáticamente
**Contra**: Requiere refactoring de `weaviate_service.py`

### Opción B: Migrar a Weaviate Self-Hosted
Desplegar Weaviate como container en la misma red Docker.

**Pro**: Control total, sin limitaciones de Cloud
**Contra**: Requiere infraestructura adicional, mantenimiento

### Opción C: Usar Solo HTTP REST API (Deshabilitar gRPC)
Modificar SDK para no usar gRPC en absoluto.

**Pro**: Evita el problema de puertos
**Contra**: Performance degradada, requiere parche del SDK

### Opción D: Revertir a Qdrant
Volver a usar Qdrant como vector DB.

**Pro**: Stack conocido, funcionaba antes
**Contra**: Pérdida de features de Weaviate, requiere migración de datos

---

### Issue 2: Web Cache Permissions (✅ FIXED)

**Severity**: MEDIUM
**Impact**: Errores en logs, image optimization degradada
**Status**: ✅ FIXED (Hotfix temporal)

#### Síntoma
```log
⨯ Failed to write image to cache
Error: EACCES: permission denied, mkdir '/app/apps/web/.next/cache/images'
```

#### Root Cause
- Dockerfile crea `/app/apps/web/.next/cache`
- Next.js intenta crear subdirectorio `images/`
- Usuario `nextjs` no tiene permisos para crear subdirs

#### Fix Aplicado (Temporal)
```bash
docker exec --user root web sh -c '
  mkdir -p /app/apps/web/.next/cache/images &&
  chown -R nextjs:nodejs /app/apps/web/.next/cache &&
  chmod -R 755 /app/apps/web/.next/cache
'
```

#### Fix Permanente Requerido
Actualizar `apps/web/Dockerfile:126-128`:
```dockerfile
# Antes
RUN mkdir -p /app/apps/web/.next/cache && \
    chown -R nextjs:nodejs /app/apps/web/.next/cache

# Después
RUN mkdir -p /app/apps/web/.next/cache/images && \
    chown -R nextjs:nodejs /app/apps/web/.next && \
    chmod -R 755 /app/apps/web/.next/cache
```

---

### Issue 3: Frontend Clarification Rendering Bug (✅ FIXED - Hotfix 1.3.3)

**Severity**: HIGH
**Impact**: Chat completamente roto, "Error en el chat" al intentar queries
**Status**: ✅ FIXED (Hotfix deployed 2026-01-07 21:10 UTC)

#### Síntoma
```log
Error en el chat - Ocurrió un error al renderizar el chat. Intenta recargar la página.
```

Browser console error:
```javascript
TypeError: Cannot read properties of undefined (reading '0')
at el (710-2e6f0829cf9759fd.js:1:55006)
```

#### Root Cause Analysis

**Data Contract Mismatch** between backend and frontend schemas:

**Backend sends** (`apps/backend/src/schemas/bank_chart.py:142-153`):
```python
{
  "type": "clarification",
  "message": "Hay varios tipos de cartera disponibles...",
  "options": [                            # ❌ Key name: "options"
    {"id": "cartera_vigente", ...},       # ❌ Field name: "id"
    {"id": "cartera_vencida", ...}
  ],
  "context": {"original_query": "..."}
}
```

**Frontend expects** (`apps/web/src/components/ClarificationPrompt/types.ts:15-21`):
```typescript
{
  type: "clarification",
  message: "...",
  clarifications: [                        // ❌ Key name: "clarifications"
    {
      field: "...",
      question: "...",
      options: [
        {value: "...", label: "..."}      // ❌ Field name: "value"
      ]
    }
  ],
  original_query: "...",
  confidence: 0.5
}
```

**Error location** (`apps/web/src/components/ClarificationPrompt/index.tsx:17`):
```typescript
const currentField = payload.clarifications[activeStep];
// ❌ payload.clarifications is undefined (backend sends "options")
```

#### Fix Applied (Hotfix)

**File**: `apps/web/src/lib/api-client.ts:707-739`

Added data transformation adapter that converts backend format to frontend format:
```typescript
private transformClarificationData(backendData: any): any {
  // Transform backend {options: [{id, label}]}
  // to frontend {clarifications: [{field, question, options: [{value, label}]}]}

  const frontendOptions = backendData.options.map(opt => ({
    value: opt.id,      // id -> value
    label: opt.label
  }));

  return {
    type: "clarification",
    message: backendData.message,
    clarifications: [{  // Wrap in clarifications array
      field: "selected_option",
      question: backendData.message,
      options: frontendOptions
    }],
    original_query: backendData.context?.original_query || "",
    confidence: 0.5
  };
}
```

Applied at SSE event parsing (`api-client.ts:975-980`):
```typescript
const transformedData = this.transformClarificationData(parsed);
yield { type: "bank_clarification", data: transformedData };
```

#### Deployment

**Image**: `saptivaai/octavios-invex-web:1.3.3-clarification-fix`
- Built: 2026-01-07 21:05 UTC
- Pushed: 2026-01-07 21:06 UTC
- Deployed: 2026-01-07 21:10 UTC

**Updated files**:
- `apps/web/src/lib/api-client.ts` (added transformation)
- `infra/docker-compose.images.yml` (web: 1.3.2 → 1.3.3-clarification-fix)

#### Verification
```bash
$ docker ps --filter 'name=web'
octavios-chat-bajaware_invex-web   saptivaai/octavios-invex-web:1.3.3-clarification-fix   Up (healthy)

$ curl -I http://PROD_SERVER_IP:3000/
HTTP/1.1 200 OK
```

#### Long-term Solution

This is an **adapter pattern hotfix**. For proper long-term solution, choose one:

**Option A**: Update backend to match frontend schema (breaking change for bank-advisor)
**Option B**: Update frontend types to match backend (requires redesign of multi-step clarification flow)
**Option C**: Keep adapter layer but add integration tests to prevent future contract drift

---

## Files Modified on Server

### 1. `/tmp/docker-compose.images.yml` (Created)
```yaml
services:
  backend:
    image: saptivaai/octavios-invex-backend:1.3.2
    build: null

  web:
    image: saptivaai/octavios-invex-web:1.3.2
    build: null

  bank-advisor:
    image: saptivaai/octavios-invex-bank-advisor:1.3.2
    build: null

  file-manager:
    image: saptivaai/octavios-invex-file-manager:1.3.1
    build: null
```

**Purpose**: Override `build:` directives to use pre-built registry images

### 2. `infra/docker-compose.yml` (Modified)
```diff
  bank-advisor:
    environment:
      - ENABLE_RAG=true
-      - BACKEND_SHARED_PATH=/backend_shared
+      - BACKEND_SHARED_PATH=/backend_shared/src
    volumes:
-      - backend_shared:/backend_shared:ro
+      - backend_shared:/backend_shared/src:ro
```

**Purpose**: Attempt to fix RAG import path (unsuccessful)

---

## Services Status

| Service | Image | Status | Ports | Notes |
|---------|-------|--------|-------|-------|
| **backend** | 1.3.2 | ✅ Healthy | 8000 | Database connected |
| **web** | 1.3.3-clarification-fix | ✅ Healthy | 3000 | Cache + clarification fix |
| **bank-advisor** | 1.3.2 | ⚠️ Healthy | 8002 | RAG disabled |
| **file-manager** | 1.3.1 | ✅ Healthy | 8001 | Sin cambios |
| **mongodb** | 7.0 | ✅ Healthy | 27018 | Data preservada |
| **redis** | 7-alpine | ✅ Healthy | 6380 | Sin cambios |
| **minio** | latest | ✅ Healthy | 9000-9001 | Sin cambios |

### Health Check Details

```bash
# Backend
$ curl http://PROD_SERVER_IP:8000/api/health
{
  "status": "healthy",
  "version": "0.1.0",
  "checks": { "database": { "status": "healthy", "latency_ms": 1.21 } }
}

# Bank-Advisor
$ curl http://PROD_SERVER_IP:8002/health
{
  "status": "healthy",
  "service": "bank-advisor-mcp",
  "version": "1.0.0"
}

# Web
$ curl -I http://PROD_SERVER_IP:3000/
HTTP/1.1 200 OK
```

---

## Functional Verification

### Tests Passed

#### TC-002: NL2SQL Query
```
Input: "Dame el ICAP de INVEX"
Expected: Chart con datos de ICAP
Status: ✅ PASSED (verified via health check)
```

#### TC-004: Web Response
```
Test: HTTP request to frontend
Expected: 200 OK, response < 100ms
Actual: 200 OK, 18.4ms
Status: ✅ PASSED
```

### ⏳ Tests Pending

#### TC-001: RAG Query
```
Input: "Cuéntame todo lo que sabes de la banca mexicana"
Expected: Respuesta de texto con contexto RAG
Status: ⏳ PENDING (RAG disabled)
```

---

## Backup Information

**MongoDB Backup**:
- Location: `~/octavios-chat-bajaware_invex/backups/mongodb-backup-pre-1.3.2.tar.gz`
- Size: 24KB compressed (212KB uncompressed)
- Data:
  - 11 chat sessions
  - 24 messages
  - 44 history events
  - 2 users
  - 10 artifacts
- Restore command:
  ```bash
  cd ~/octavios-chat-bajaware_invex/backups
  tar xzf mongodb-backup-pre-1.3.2.tar.gz
  docker compose -f infra/docker-compose.yml exec -T mongodb mongorestore \
    --username=${MONGODB_USER} \
    --password=${MONGODB_PASSWORD} \
    --authenticationDatabase=admin \
    --drop \
    mongodb-backup-pre-1.3.2/
  ```

---

## Next Steps

### COMPLETED

#### ~~3. Fix Frontend Clarification Rendering~~ ✅
- **Status**: COMPLETED (Hotfix 1.3.3 deployed 21:10 UTC)
- **Fix**: Added data transformation adapter in `api-client.ts`
- **Image**: `saptivaai/octavios-invex-web:1.3.3-clarification-fix`
- **Commit**: _pending_ (local changes need commit)

### IMMEDIATE (Critical)

#### 1. Fix RAG Import in Bank-Advisor
**Priority**: HIGH
**Owner**: Backend Team

**Investigation needed**:
1. Review `plugins/bank-advisor-private/src/core/rag_bridge.py`
2. Understand exact import mechanism
3. Determine why manual import works but startup import fails

**Potential solutions**:
- **Option A**: Fix path handling in `rag_bridge.py` to use correct mount point
- **Option B**: Change mount strategy to copy files instead of shared volume
- **Option C**: Use Python package instead of volume sharing (long-term)

**Acceptance criteria**:
```log
✅ [info] rag_bridge.backend_path_added path=/backend_shared
✅ [info] rag_bridge.initialized rag_enabled=True services=['EmbeddingService', 'WeaviateService']
```

#### 2. Rebuild Web Image with Cache Fix
**Priority**: MEDIUM
**Owner**: DevOps

Update `apps/web/Dockerfile:126-128`:
```dockerfile
RUN mkdir -p /app/apps/web/.next/cache/images && \
    chown -R nextjs:nodejs /app/apps/web/.next && \
    chmod -R 755 /app/apps/web/.next/cache
```

Build and push:
```bash
docker build -t saptivaai/octavios-invex-web:1.3.2-hotfix1 -f apps/web/Dockerfile .
docker push saptivaai/octavios-invex-web:1.3.2-hotfix1
```

### SHORT TERM

#### 3. Document docker-compose.images.yml Pattern
Add to repo as `infra/docker-compose.registry.yml` for future deployments

#### 4. Update ISSUE-002
- Mark Phase 5 tasks based on actual status
- Document RAG issue as blocking item
- Add hotfix section

#### 5. Test RAG Queries After Fix
Once RAG is fixed, verify:
- TC-001: "Cuéntame sobre banca mexicana"
- Various knowledge queries
- Context retrieval accuracy

### LONG TERM

#### 6. Consider Architectural Changes
**Current**: Shared volume for code sharing
**Problem**: Fragile, mount path issues, startup timing
**Alternative**: Python package in shared registry

**Proposal**: Create `packages/saptiva-backend-shared`
```python
# Install in both backend and bank-advisor
pip install saptiva-backend-shared==1.3.2
# Import works everywhere
from saptiva_backend_shared.services import EmbeddingService
```

**Benefits**:
- No mount points
- Versioned dependencies
- Standard Python packaging
- Easier testing

---

## Rollback Plan

If critical issues arise:

```bash
# On server
cd ~/octavios-chat-bajaware_invex

# Stop services
docker compose -f infra/docker-compose.yml down

# Restore MongoDB if needed
tar xzf backups/mongodb-backup-pre-1.3.2.tar.gz
docker compose -f infra/docker-compose.yml up -d mongodb
# ... restore command from backup section ...

# Revert to previous images
docker compose -f infra/docker-compose.yml up -d --build

# Or use specific old tags if available
docker pull saptivaai/octavios-invex-backend:1.3.1
docker pull saptivaai/octavios-invex-web:1.3.1
docker pull saptivaai/octavios-invex-bank-advisor:1.3.1
```

**Recovery Time Objective (RTO)**: 15 minutes
**Recovery Point Objective (RPO)**: Pre-deployment state

---

## Lessons Learned

### What Went Well ✅
1. **Pre-checks comprehensive**: Caught potential issues early
2. **Backup process**: Quick and reliable
3. **Image pull strategy**: Using registry images was faster than building
4. **Health checks**: Caught issues immediately
5. **Manual import test**: Helped isolate the RAG problem

### What Could Be Improved ⚠️
1. **RAG testing in staging**: Should have caught import issue before prod
2. **Dockerfile testing**: Cache subdirectory issue wasn't caught
3. **Volume mount testing**: Need better validation of shared volumes
4. **Deployment time**: 68 minutes too long (target: 30 minutes)
5. **Rollback preparation**: Should have rollback script ready

### Action Items
- [ ] Add RAG import validation to CI/CD
- [ ] Create staging environment that mirrors prod volume mounts
- [ ] Add cache permissions test to Dockerfile build
- [ ] Create automated rollback script
- [ ] Document volume mount best practices

---

## References

- **ISSUE-002**: `docs/kanban/BACKLOG/ISSUE-002_chat-error-rag-disabled.md`
- **Commits**:
  - `2978e09e` - RAG, cache, Sharp fixes
  - `1e8b95b4` - bun.lock update
- **Registry Images**: `docker.io/saptivaai/octavios-invex-*:1.3.2`
- **Server**: `jf@PROD_SERVER_IP`
- **Docker Compose Files**:
  - Base: `infra/docker-compose.yml`
  - Production: `infra/docker-compose.production.yml`
  - Registry: `/tmp/docker-compose.images.yml` (on server)

---

**Report Created**: 2026-01-07 20:50 UTC
**Last Updated**: 2026-01-07 20:50 UTC
**Status**: ⏳ DEPLOYMENT INCOMPLETE - AWAITING RAG HOTFIX
