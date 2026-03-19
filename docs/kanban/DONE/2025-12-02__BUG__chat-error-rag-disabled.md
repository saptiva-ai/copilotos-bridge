# ISSUE-002: Error en Chat - RAG Deshabilitado y Problemas de Permisos

**Status**: ✅ DONE
**Priority**: HIGH
**Created**: 2026-01-07
**Closed**: 2026-01-07
**Type**: Bug Fix / Infrastructure
**Environment**: Production (jf@34.171.0.60)
**Code Status**: ✅ ALL FIXES DEPLOYED (v1.3.7 backend, v1.3.5 web)

## Overview

Usuarios experimentan error "Error en el chat - Ocurrió un error al renderizar el chat" cuando realizan queries de conocimiento general como "Cuéntame todo lo que sabes de la banca mexicana". El issue tiene múltiples causas relacionadas con configuración de producción.

## Síntomas Reportados

### Error en Frontend
```
💬 Error en el chat
Ocurrió un error al renderizar el chat. Intenta recargar la página.
[Botón: Recargar página]
```

### Queries Afectadas
- Preguntas generales de conocimiento: "Cuéntame todo sobre banca mexicana"
- Queries que requieren contexto RAG
- Definiciones amplias sin métricas específicas

### Queries NO Afectadas
- Métricas específicas: "Dame el ICAP de INVEX" ✅
- Queries NL2SQL con banco/métrica clara ✅

---

## Root Cause Analysis

### 🔴 Causa 1: RAG Deshabilitado en Bank-Advisor (CRÍTICO)

**Log Evidence:**
```
2026-01-07 18:34:56 [warning] rag_bridge.import_failed
  error="No module named 'src.services'"
  message='Main backend services not available. RAG disabled.'
```

**Análisis:**
- Bank-advisor intenta importar módulos del backend desde `/backend_shared`
- En producción, no hay volumen compartido montado
- RAG queda deshabilitado, solo funciona NL2SQL
- Queries generales de conocimiento fallan o devuelven clarification vacía

**Ubicación del código:**
- `plugins/bank-advisor-private/src/core/rag_bridge.py`
- `infra/docker-compose.yml` (sección bank-advisor)

**Impacto:**
- **Severidad**: ALTA - Funcionalidad core deshabilitada
- **Usuarios Afectados**: Todos los que hacen queries de conocimiento
- **Workaround Actual**: Sistema devuelve clarification, pero UX es mala

---

### 🟡 Causa 2: Error de Permisos en Web Cache (SOLUCIONADO)

**Log Evidence:**
```
⨯ Failed to write image to cache
  Error: EACCES: permission denied, mkdir '/app/apps/web/.next/cache'
  errno: -13, code: 'EACCES', syscall: 'mkdir'
```

**Análisis:**
- Next.js en modo standalone requiere directorio `.next/cache`
- Imagen Docker no creaba este directorio en build
- Contenedor corre como usuario `nextjs` sin permisos para crear directorios

**Solución Aplicada:** ✅
```bash
# Como root en el contenedor
mkdir -p /app/apps/web/.next/cache
chown -R nextjs:nodejs /app/apps/web/.next/cache
```

**Estado**: RESUELTO (temporal) - Requiere fix permanente en Dockerfile

---

### 🟠 Causa 3: Sharp Missing en Production (SECUNDARIO)

**Log Evidence:**
```
⨯ Error: 'sharp' is required to be installed in standalone mode
  for the image optimization to function correctly
```

**Análisis:**
- Next.js Image Optimization requiere `sharp` en modo standalone
- Dependencia no incluida en `package.json` de web
- No causa crash pero degrada performance de imágenes

**Impacto:**
- **Severidad**: MEDIA - Feature degradado, no crítico
- **Workaround**: Next.js usa fallback sin optimización

---

## Impact Assessment

| Categoría | Impacto |
|-----------|---------|
| **Funcionalidad** | Alta - RAG core feature deshabilitado |
| **UX** | Alta - Error confuso para usuario |
| **Performance** | Media - Sharp missing afecta imágenes |
| **SEO/Analytics** | Baja - No afectado |
| **Seguridad** | Ninguna - No hay vulnerabilidades |

### Usuarios Afectados
- ✅ Queries NL2SQL (métricas específicas): **Funcionan**
- ❌ Queries RAG (conocimiento general): **Fallan**
- ⚠️ Queries ambiguas: **Devuelven clarification**

### Servicios Afectados
- ✅ Backend: Healthy, funcionando
- ⚠️ Bank-Advisor: Healthy, pero RAG disabled
- ✅ Web: Healthy (después de fix de cache)
- ✅ MongoDB, Redis, Minio: Sin problemas

---

## Solution Plan

### Phase 1: Fix Inmediato - Web Cache (✅ COMPLETADO)

**Objetivo**: Resolver error de permisos que podría causar crashes

**Acciones Tomadas:**
```bash
✅ 1. Crear directorio cache manualmente
✅ 2. Asignar permisos correctos (nextjs:nodejs)
✅ 3. Verificar servicio healthy
```

**Resultado**: Web estable, error de permisos resuelto temporalmente

---

### Phase 2: Fix Permanente - Web Dockerfile (✅ COMPLETADO)

**Objetivo**: Asegurar que cache directory se crea en build time

**Implementación Completada** (Commit: `2978e09e` - 2026-01-07):

**Archivo**: `apps/web/Dockerfile:126-128`
```dockerfile
# Create cache directory with correct permissions to prevent EACCES errors
RUN mkdir -p /app/apps/web/.next/cache && \
    chown -R nextjs:nodejs /app/apps/web/.next/cache
```

**Tareas Completadas:**
- [x] ✅ Editar `apps/web/Dockerfile` (líneas 126-128)
- [x] ✅ Fix integrado en commit 2978e09e
- [ ] ⏳ Rebuild imagen: `docker build -t saptivaai/octavios-invex-web:1.3.2`
- [ ] ⏳ Push a DockerHub
- [ ] ⏳ Deploy en producción
- [ ] ⏳ Verificar logs sin errores de permisos

**Código Status**: ✅ IMPLEMENTADO
**Deployment Status**: ⏳ PENDIENTE

---

### Phase 3: Agregar Sharp a Web (✅ COMPLETADO)

**Objetivo**: Habilitar optimización de imágenes en producción

**Implementación Completada** (Commits: `2978e09e` + `1e8b95b4` - 2026-01-07):

**Archivo**: `apps/web/package.json`
```json
{
  "dependencies": {
    "sharp": "^0.33.0"  // ✅ AGREGADO
  }
}
```

**Archivo**: `bun.lock`
- ✅ Sharp con todas las dependencias nativas instaladas
- ✅ Incluye bindings para múltiples plataformas (linux-x64, darwin-arm64, etc.)
- ✅ 52 líneas de configuración agregadas en commit 1e8b95b4

**Tareas Completadas:**
- [x] ✅ Agregar `sharp` a `package.json` (commit 2978e09e)
- [x] ✅ Actualizar lockfile con `bun install` (commit 1e8b95b4)
- [x] ✅ Dependencias nativas incluidas en bun.lock
- [ ] ⏳ Rebuild y test localmente
- [ ] ⏳ Deploy a producción

**Código Status**: ✅ IMPLEMENTADO
**Deployment Status**: ⏳ PENDIENTE

---

### Phase 4: Habilitar RAG en Bank-Advisor (✅ COMPLETADO)

**Objetivo**: Restaurar funcionalidad RAG para queries de conocimiento

**Implementación Completada** (Commit: `2978e09e` - 2026-01-07):

#### ✅ Opción A Implementada: Volumen Compartido

**Cambios en** `infra/docker-compose.yml:242-260`:

```yaml
services:
  backend:
    volumes:
      # ✅ IMPLEMENTADO: Compartir módulos con bank-advisor
      - backend_shared:/app/src:ro

  bank-advisor:
    volumes:
      - ../plugins/bank-advisor-private/data:/app/data:ro
      # ✅ IMPLEMENTADO: Montar volumen compartido del backend
      - backend_shared:/backend_shared:ro
    environment:
      # ✅ IMPLEMENTADO: Variables para habilitar RAG
      - ENABLE_RAG=true
      - BACKEND_SHARED_PATH=/backend_shared
    depends_on:
      backend:
        condition: service_healthy  # ✅ IMPLEMENTADO

volumes:
  backend_shared:  # ✅ IMPLEMENTADO: Volumen compartido definido
```

**Tareas Completadas:**
- [x] ✅ Editar `docker-compose.yml` (líneas 242-260, commit 2978e09e)
- [x] ✅ Agregar volumen `backend_shared`
- [x] ✅ Configurar depends_on con health check
- [x] ✅ Configurar variables ENABLE_RAG y BACKEND_SHARED_PATH
- [ ] ⏳ Deploy y verificar logs: "rag_bridge.initialized"
- [ ] ⏳ Test con query: "Cuéntame sobre banca mexicana"

**Código Status**: ✅ IMPLEMENTADO
**Deployment Status**: ⏳ PENDIENTE

---

#### Opción B: Crear Paquete Compartido Python (Alternativa)

**Objetivo**: Extraer servicios comunes a paquete instalable

**Estructura Propuesta:**
```
packages/
└── saptiva-common/
    ├── setup.py
    ├── src/
    │   └── saptiva_common/
    │       ├── __init__.py
    │       ├── rag_service.py
    │       ├── embedding_service.py
    │       └── qdrant_service.py
    └── README.md
```

**Cambios Requeridos:**

1. **Crear paquete**:
```bash
mkdir -p packages/saptiva-common/src/saptiva_common
# Mover servicios RAG compartidos
cp apps/backend/src/services/rag_service.py packages/saptiva-common/src/saptiva_common/
```

2. **Instalar en ambos servicios**:
```dockerfile
# En backend y bank-advisor Dockerfiles
COPY packages/saptiva-common /tmp/saptiva-common
RUN pip install /tmp/saptiva-common
```

3. **Actualizar imports**:
```python
# Antes
from src.services.rag_service import RAGService

# Después
from saptiva_common.rag_service import RAGService
```

**Pros:**
- ✅ Desacoplamiento total entre servicios
- ✅ Código compartido versionado
- ✅ Escalable para más servicios

**Contras:**
- ❌ Más trabajo inicial (refactor)
- ❌ Requiere gestión de versiones
- ❌ Más complejidad en builds

**Estimación**: 1-2 días
**Prioridad**: BAJA (solución Opción A es suficiente)

---

### Phase 5: Production Deployment (⏳ EN PROGRESO)

**Objetivo**: Desplegar todas las imágenes 1.3.2 con los fixes a producción

**Build Status** (2026-01-07 19:50):

| Servicio | Imagen | Tag | Tamaño | Status Build | Registry |
|----------|--------|-----|--------|--------------|----------|
| **Backend** | saptivaai/octavios-invex-backend | 1.3.2 | 13GB | ✅ Construida | ✅ Pushed |
| **Web** | saptivaai/octavios-invex-web | 1.3.2 | 502MB | ✅ Construida | ✅ Pushed |
| **Bank-Advisor** | saptivaai/octavios-invex-bank-advisor | 1.3.2 | 17.5GB | ✅ Construida | ✅ Pushed |
| **File-Manager** | saptivaai/octavios-invex-file-manager | 1.3.1 | 661MB | ✅ Construida | ✅ Pushed |

**Manifest Verification:**
```bash
✅ docker manifest inspect saptivaai/octavios-invex-web:1.3.2
✅ Image ID: d2a89143b511 (2026-01-07T19:50:38Z)
✅ Platform: linux/amd64
✅ Includes cache directory fix (lines 126-128 in Dockerfile)
```

**Deployment Tasks:**

**5.1 Pre-Deployment Checklist**
- [x] ✅ Verificar imágenes en DockerHub registry
- [ ] ⏳ Backup de volúmenes de producción (MongoDB, Redis)
- [ ] ⏳ Verificar conectividad SSH a ${PROD_SERVER_IP}
- [ ] ⏳ Verificar espacio en disco en servidor de producción
- [ ] ⏳ Notificar a usuarios de ventana de mantenimiento (opcional)

**5.2 Deployment Execution**
```bash
# En servidor de producción (${PROD_SERVER_USER}@${PROD_SERVER_IP})

# 1. Pull nuevas imágenes
docker pull saptivaai/octavios-invex-backend:1.3.2
docker pull saptivaai/octavios-invex-web:1.3.2
docker pull saptivaai/octavios-invex-bank-advisor:1.3.2

# 2. Actualizar docker-compose.yml con nuevos tags
# Esto ya está en el repo - solo hacer pull del código

# 3. Restart servicios con nuevas imágenes
cd /path/to/octavios-chat-bajaware_invex
docker compose -f infra/docker-compose.yml -f infra/docker-compose.production.yml down
docker compose -f infra/docker-compose.yml -f infra/docker-compose.production.yml up -d

# 4. Verificar health checks
docker compose -f infra/docker-compose.yml ps
```

**5.3 Post-Deployment Verification**
- [ ] ⏳ Verificar todos los servicios healthy
- [ ] ⏳ Verificar logs de bank-advisor: "rag_bridge.initialized rag_enabled=True"
- [ ] ⏳ Verificar logs de web: Sin errores EACCES
- [ ] ⏳ Test TC-001: Query RAG "Cuéntame sobre banca mexicana"
- [ ] ⏳ Test TC-002: Query NL2SQL "Dame el ICAP de INVEX"
- [ ] ⏳ Verificar image optimization (sharp) funciona

**5.4 Monitoring (Primeras 24 horas)**
```bash
# Logs en tiempo real
docker logs -f octavios-chat-bajaware_invex-bank-advisor 2>&1 | grep -E "(rag_bridge|rag_enabled)"
docker logs -f octavios-chat-bajaware_invex-web 2>&1 | grep -E "(EACCES|Error|sharp)"
docker logs -f octavios-chat-bajaware_invex-backend 2>&1 | grep -E "(rag_service|embedding)"
```

**Rollback Plan:**
```bash
# Si algo falla, revertir a 1.3.1
docker pull saptivaai/octavios-invex-backend:1.3.1
docker pull saptivaai/octavios-invex-web:1.3.1
docker pull saptivaai/octavios-invex-bank-advisor:1.3.1

# Restart con versión anterior
docker compose -f infra/docker-compose.yml -f infra/docker-compose.production.yml down
docker compose -f infra/docker-compose.yml -f infra/docker-compose.production.yml up -d
```

**Estimación**: 30 minutos deployment + 2 horas monitoring
**Prioridad**: 🔴 ALTA - Usuarios afectados por RAG disabled

---

## Testing Strategy

### Test Cases Post-Fix

#### TC-001: Query RAG General
```
Input: "Cuéntame todo lo que sabes de la banca mexicana"
Expected: Respuesta de texto con información general de RAG
Actual: [PENDIENTE VERIFICAR]
```

#### TC-002: Query NL2SQL Específica
```
Input: "Dame el ICAP de INVEX"
Expected: Chart con datos de ICAP
Actual: ✅ Funciona correctamente
```

#### TC-003: Query Ambigua
```
Input: "¿Cómo está el mercado?"
Expected: Clarification pidiendo banco/métrica
Actual: [PENDIENTE VERIFICAR]
```

#### TC-004: Web Image Optimization
```
Test: Cargar imagen de perfil/logo
Expected: Sin errores EACCES en logs
Actual: ✅ Resuelto (cache directory creado)
```

### Logs de Validación

**Bank-Advisor (RAG Habilitado):**
```
✅ [info] rag_bridge.backend_path_added path=/backend_shared
✅ [info] rag_bridge.initialized rag_enabled=True
❌ [warning] rag_bridge.import_failed  # Este debe desaparecer
```

**Web (Sin errores de permisos):**
```
✅  ✓ Ready in 300ms
❌  ⨯ Error: EACCES: permission denied  # Este debe desaparecer
```

---

## Rollback Plan

### Si falla Phase 2-3 (Web fixes)
```bash
# Revertir a imagen anterior
docker pull saptivaai/octavios-invex-web:1.3.1
docker compose -f infra/docker-compose.yml up -d web

# Recrear cache manualmente (workaround)
docker exec --user root octavios-chat-bajaware_invex-web \
  mkdir -p /app/apps/web/.next/cache && \
  chown -R nextjs:nodejs /app/apps/web/.next/cache
```

### Si falla Phase 4 (RAG habilitado)
```bash
# Revertir docker-compose.yml
git checkout infra/docker-compose.yml

# Restart servicios
docker compose -f infra/docker-compose.yml down
docker compose -f infra/docker-compose.yml up -d
```

**Impacto de rollback**: Volver al estado actual (RAG disabled, NL2SQL funcional)

---

## Success Metrics

| Métrica | Antes (Prod) | Código (Dev) | Target Post-Deploy |
|---------|--------------|--------------|-------------------|
| **RAG Queries Success Rate** | 0% ❌ | ✅ Implementado | 95% ✅ |
| **Web Error Logs (EACCES)** | ~10/min ⚠️ | ✅ Fixed (Dockerfile:126-128) | 0 ✅ |
| **Image Optimization** | Disabled ⚠️ | ✅ Sharp en package.json | Enabled ✅ |
| **User Reported Errors** | 2-3/día | - | 0 |
| **Build Size (Web)** | 307MB (v1.3.1) | 502MB (v1.3.2) +195MB | Expected (Sharp natives) |

### KPIs de Validación (Post-Deploy)
- [ ] ⏳ Logs de bank-advisor muestran "rag_bridge.initialized rag_enabled=True"
- [ ] ⏳ Logs de web sin errores EACCES
- [ ] ⏳ Query "Cuéntame sobre banca mexicana" devuelve respuesta RAG coherente
- [ ] ⏳ No más reportes de "Error en el chat"
- [ ] ⏳ Sharp optimization funciona (verificar imágenes renderizadas)

### Code Verification (✅ Completado)
- [x] ✅ docker-compose.yml incluye volumen backend_shared
- [x] ✅ Variables ENABLE_RAG=true y BACKEND_SHARED_PATH configuradas
- [x] ✅ Dockerfile web crea cache directory con permisos correctos
- [x] ✅ package.json incluye sharp ^0.33.0
- [x] ✅ bun.lock actualizado con todas las dependencias nativas de sharp

---

## Timeline

| Phase | Prioridad | Status | Commits | Estimación Original | Tiempo Real |
|-------|-----------|--------|---------|---------------------|-------------|
| Phase 1 (Cache fix) | 🔴 ALTA | ✅ COMPLETADO | Manual fix | 30 min | ~30 min |
| Phase 2 (Dockerfile web) | 🟡 MEDIA | ✅ COMPLETADO | 2978e09e | 30 min | Incluido en Phase 4 |
| Phase 3 (Sharp) | 🟡 MEDIA | ✅ COMPLETADO | 2978e09e + 1e8b95b4 | 1 hora | Incluido en Phase 4 |
| Phase 4 (RAG) | 🔴 ALTA | ✅ COMPLETADO | 2978e09e | 2 horas | ~2 horas |
| Phase 5 (Deployment) | 🔴 ALTA | ⏳ EN PROGRESO | - | 30 min + 2h monitor | TBD |

**Código Completado**: ✅ 2026-01-07 (Phases 1-4)
**Builds Completados**: ✅ 2026-01-07 19:50 (Web, Backend, Bank-Advisor 1.3.2)
**Registry Push**: ✅ 2026-01-07 19:50
**Production Deploy**: ⏳ PENDIENTE

**Secuencia Ejecutada**:
1. ✅ Phase 4 (RAG) - Commit integral 2978e09e incluyó fixes 2-3-4
2. ✅ Phase 3 (Sharp) - Lock actualizado en commit 1e8b95b4
3. ✅ Builds de imágenes 1.3.2
4. ⏳ Phase 5 (Production Deployment) - En progreso

---

## Dependencies

### Servicios Involucrados
- Backend (8000) - Proveedor de RAG services
- Bank-Advisor (8002) - Consumidor de RAG
- Web (3000) - Frontend afectado por errores

### Archivos a Modificar
- `infra/docker-compose.yml` (Phase 4)
- `apps/web/Dockerfile` (Phase 2, 3)
- `apps/web/package.json` (Phase 3)

### Variables de Entorno Nuevas
```bash
# Bank-Advisor
ENABLE_RAG=true
BACKEND_SHARED_PATH=/backend_shared
```

---

## Related Issues

- `ISSUE-001`: Happy Path Test Failures - Algunos fallos podrían estar relacionados con RAG disabled
- Deploy Manual Workflow - Este fix requiere nuevo deploy

---

## Monitoring Post-Deploy

### Logs a Vigilar

```bash
# Bank-Advisor: RAG status
docker logs -f octavios-chat-bajaware_invex-bank-advisor 2>&1 | grep -E "(rag_bridge|rag_enabled)"

# Web: Permission errors
docker logs -f octavios-chat-bajaware_invex-web 2>&1 | grep -E "(EACCES|Error|sharp)"

# Backend: RAG calls
docker logs -f octavios-chat-bajaware_invex-backend 2>&1 | grep -E "(rag_service|embedding)"
```

### Health Checks
```bash
# Verificar todos los servicios
curl http://${PROD_SERVER_IP}:8000/api/health  # Backend
curl http://${PROD_SERVER_IP}:8002/health      # Bank-Advisor
curl http://${PROD_SERVER_IP}:3000/           # Web
```

---

## Notes

### Contexto de Producción
- Servidor: `${PROD_SERVER_USER}@${PROD_SERVER_IP}`
- Imágenes: DockerHub `saptivaai/octavios-invex-*`
- MongoDB: Data preservada en volúmenes
- Deploy: Manual (no CI/CD automático)

### Lecciones Aprendidas
1. **Volúmenes compartidos**: Necesarios para arquitectura de plugins
2. **Cache directories**: Deben crearse en build time con permisos correctos
3. **RAG testing**: Debería estar en test suite (agregar a ISSUE-001)
4. **Logs estructurados**: Facilitan debugging en producción

---

## Next Steps

**✅ Completado - Code Implementation**
- [x] ✅ Ejecutar Phase 1-4 (todos los fixes de código)
- [x] ✅ Rebuild imágenes con fixes (1.3.2)
- [x] ✅ Push a DockerHub registry

**⏳ Immediate (Owner: DevOps) - DEPLOYMENT**
- [ ] ⏳ Ejecutar Phase 5.1: Pre-Deployment Checklist
- [ ] ⏳ Ejecutar Phase 5.2: Production Deployment
- [ ] ⏳ Ejecutar Phase 5.3: Post-Deployment Verification
  - [ ] Verificar logs de bank-advisor: "rag_bridge.initialized"
  - [ ] Test TC-001: Query RAG "Cuéntame sobre banca mexicana"
  - [ ] Test TC-002: Query NL2SQL "Dame el ICAP de INVEX"
- [ ] ⏳ Ejecutar Phase 5.4: Monitoring (primeras 24h)

**Short Term (Owner: Backend Team)**
- [ ] Documentar lecciones aprendidas del deployment
- [ ] Actualizar este issue a DONE cuando deployment esté completo
- [ ] Agregar métricas de RAG success rate al dashboard

**Long Term (Owner: Architecture Team)**
- [ ] Evaluar Opción B (paquete compartido) para escalabilidad
- [ ] Documentar arquitectura de volúmenes compartidos
- [ ] Agregar RAG queries a test suite automatizado
- [ ] Considerar health check específico para RAG status

---

**Created**: 2026-01-07
**Last Updated**: 2026-01-07 19:50 (Phase 5 Added, Builds Verified)
**Status**: READY_FOR_DEPLOYMENT (Code ✅ | Builds ✅ | Deploy ⏳)
**Assignee**: DevOps Team (Deployment)

**Summary**:
- ✅ Phases 1-4 COMPLETADAS en código (commits 2978e09e + 1e8b95b4)
- ✅ Imágenes 1.3.2 construidas y pusheadas al registry
- ⏳ Pendiente: Deployment a producción (Phase 5)
