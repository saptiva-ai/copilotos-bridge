# Guía de Deploy - v1.4.5

## Resumen de Cambios

**Versión**: `1.4.5`
**Fecha**: 2026-01-14
**Branch**: `develop` → `main`

### Cambios Principales

| Componente | Cambio | Impacto | Ref |
|------------|--------|---------|-----|
| **backend** | Chart Persistence Fix (Bug 8) | Charts restauran al recargar página | `ec7c16bc` |
| **backend** | artifact_id en message metadata | tool_invocations array para frontend | `ec7c16bc` |
| **bank-advisor** | SISTEMA Inclusion Tests | Previene regresión de filters | `37332382` |
| **bank-advisor** | Schema Grounding Validator | Previene hallucinations de métricas | `6711e5db` |
| **tests** | E2E Chart Persistence Test | Valida flujo completo end-to-end | `40ec2372` |

### Bugs Resueltos

1. **Bug 8 (Chart Persistence)**: Charts no restauraban al regresar a conversación
   - **Fix**: artifact_id ahora se guarda en `message.metadata.tool_invocations`
   - **Validación**: Test E2E de 8 pasos pasa al 100%

2. **Bug 7 (Table Numbers) - Prevention**: LLM hallucina métricas inexistentes
   - **Fix**: SchemaValidator detecta métricas inválidas y sugiere alternativas
   - **Ejemplos**: `numero_creditos` → sugiere `cartera_vivienda_total`

### Tests Agregados

- ✅ **27 Unit Tests** (100% pass)
  - 8 tests SISTEMA inclusion (anti-regresión)
  - 19 tests Schema Validator
- ✅ **1 E2E Test** (100% pass)
  - Chart persistence full flow validation

---

## Preparación Pre-Deploy

### 1. Verificar Estado Local

```bash
cd /home/jazielflo/Proyects/octavios-chat-bajaware_invex
git status
git log --oneline -5

# Verificar que estás en develop con todos los commits
git branch
```

### 2. Merge a Main (si estás en develop)

```bash
# Asegurar que develop está actualizado
git checkout develop
git pull origin develop

# Merge a main
git checkout main
git pull origin main
git merge develop

# Resolver conflictos si hay
# Verificar que todo quedó bien
git log --oneline -5

# Push a main
git push origin main
```

---

## Paso 1: Build Local

### 1.1 Build de Imágenes

```bash
# OPCIÓN A: Usar script automatizado (recomendado)
./BUILD_v1.4.5.sh

# OPCIÓN B: Build manual con comandos individuales
docker build -t saptivaai/octavios-invex-backend:1.4.5 \
    -f apps/backend/Dockerfile \
    --target production \
    apps/backend/

docker build -t saptivaai/octavios-invex-web:1.4.5 \
    -f apps/web/Dockerfile \
    --target production \
    apps/web/

docker build -t saptivaai/octavios-invex-bank-advisor:1.4.5 \
    -f plugins/bank-advisor-private/Dockerfile \
    --target production \
    plugins/bank-advisor-private/
```

**NOTA IMPORTANTE**: El build context es el directorio de cada servicio (`apps/backend/`, etc.), NO el root del repo.

**Tiempo estimado**: 5-10 minutos (con cache)

### 1.2 Test Local (IMPORTANTE)

```bash
# Levantar con las nuevas imágenes
docker compose -f infra/docker-compose.yml down
docker compose -f infra/docker-compose.yml up -d

# Esperar 30s para startup
sleep 30

# Health checks
curl http://localhost:8000/api/health
# Debe devolver: {"status":"healthy","version":"..."}

curl http://localhost:8002/health
# Debe devolver: {"status":"healthy"}

curl -I http://localhost:3000
# Debe devolver: HTTP/1.1 200 OK

# Test funcional: Chart Persistence
# 1. Abrir http://localhost:3000
# 2. Hacer login (demo/Demo1234)
# 3. Preguntar: "Cartera total de BBVA en 2024"
# 4. Verificar que aparece chart
# 5. Recargar página (F5)
# 6. Verificar que el chart se restaura correctamente ✅

# Test E2E automatizado (opcional)
python tests/e2e/charts/test_chart_persistence.py
# Debe mostrar: ✅ CHART PERSISTENCE TEST PASSED
```

---

## Paso 2: Push a Docker Hub

### 2.1 Login

```bash
docker login
# Username: saptivaai
# Password: [solicitar al admin]
```

### 2.2 Push Imágenes

```bash
# Push backend
docker push saptivaai/octavios-invex-backend:1.4.5

# Push web
docker push saptivaai/octavios-invex-web:1.4.5

# Push bank-advisor
docker push saptivaai/octavios-invex-bank-advisor:1.4.5

# OPCIONAL: Tag como latest
docker tag saptivaai/octavios-invex-backend:1.4.5 saptivaai/octavios-invex-backend:latest
docker tag saptivaai/octavios-invex-web:1.4.5 saptivaai/octavios-invex-web:latest
docker tag saptivaai/octavios-invex-bank-advisor:1.4.5 saptivaai/octavios-invex-bank-advisor:latest

docker push saptivaai/octavios-invex-backend:latest
docker push saptivaai/octavios-invex-web:latest
docker push saptivaai/octavios-invex-bank-advisor:latest
```

**Tiempo estimado**: 10-15 minutos total

---

## Paso 3: Actualizar docker-compose.images.yml

### 3.1 Actualizar Versiones

```bash
# Editar infra/docker-compose.images.yml
# Cambiar las versiones a 1.4.5
```

O usar script (si existe):

```bash
./scripts/deploy/update-images.sh -v 1.4.5
```

### 3.2 Verificar y Commit

```bash
# Verificar cambios
cat infra/docker-compose.images.yml

# Debería mostrar:
# backend: saptivaai/octavios-invex-backend:1.4.5
# web: saptivaai/octavios-invex-web:1.4.5
# bank-advisor: saptivaai/octavios-invex-bank-advisor:1.4.5

# Commit
git add infra/docker-compose.images.yml
git commit -m "chore: bump images to v1.4.5 (chart persistence + schema validator + SISTEMA tests)"
git push origin main
```

---

## Paso 4: Deploy en Producción

### 4.1 Conectar al Servidor

```bash
# Solicitar IP y credenciales al admin
ssh jf@PROD_SERVER_IP
cd ~/octavios-chat-bajaware_invex
```

### 4.2 Backup (CRÍTICO - OBLIGATORIO)

```bash
# Crear directorio de backups si no existe
mkdir -p backups

# Backup MongoDB
docker exec octavios-chat-bajaware_invex-mongodb mongodump \
    --username="octavios_user" \
    --password="[SOLICITAR_PASSWORD]" \
    --authenticationDatabase=admin \
    --out=/tmp/backup-pre-1.4.5

# Copiar backup al host
docker cp octavios-chat-bajaware_invex-mongodb:/tmp/backup-pre-1.4.5 \
    ./backups/mongodb-backup-pre-1.4.5-$(date +%Y%m%d-%H%M%S)

# Comprimir
tar czf backups/mongodb-backup-pre-1.4.5-$(date +%Y%m%d-%H%M%S).tar.gz \
    backups/mongodb-backup-pre-1.4.5-*

echo "✅ Backup completado en backups/"
```

### 4.3 Actualizar Código

```bash
# Fetch y pull
git fetch origin
git checkout main
git pull origin main

# Verificar que tienes el commit con las nuevas imágenes
git log --oneline -3
# Debe mostrar: "chore: bump images to v1.4.5..."
```

### 4.4 Eliminar Named Volume (CRÍTICO)

```bash
# IMPORTANTE: Previene código viejo en el container
echo "🗑️  Eliminando named volume para evitar código stale..."

# Detener servicios afectados
docker compose -f infra/docker-compose.yml rm -sf backend bank-advisor

# Eliminar volume compartido
docker volume rm octavios-chat-bajaware_invex_backend_shared 2>/dev/null || true

echo "✅ Volume eliminado correctamente"
```

### 4.5 Pull Nuevas Imágenes

```bash
# Pull imágenes v1.4.5 desde Docker Hub
docker compose \
    -f infra/docker-compose.yml \
    -f infra/docker-compose.images.yml \
    pull backend web bank-advisor

# Verificar que se descargaron las correctas
docker images | grep saptivaai | grep 1.4.5
```

### 4.6 Deploy

```bash
# Levantar servicios con nuevas imágenes
docker compose \
    -f infra/docker-compose.yml \
    -f infra/docker-compose.images.yml \
    -f infra/docker-compose.production.yml \
    --env-file envs/.env \
    up -d

echo "🚀 Deploy iniciado. Esperando startup..."
sleep 30
```

### 4.7 Limpiar Redis Cache (IMPORTANTE)

```bash
# Limpiar cache para evitar datos stale después del deploy
echo "🧹 Limpiando Redis cache..."

docker exec redis redis-cli FLUSHDB

# O si Redis tiene password:
# REDIS_PASS=$(grep REDIS_PASSWORD envs/.env | cut -d= -f2)
# docker exec redis redis-cli -a "${REDIS_PASS}" FLUSHDB

echo "✅ Cache limpiado"
```

---

## Paso 5: Verificación Post-Deploy

### 5.1 Health Checks

```bash
echo "🔍 Verificando health de servicios..."

# Backend
curl http://localhost:8000/api/health
echo ""

# Bank-Advisor
curl http://localhost:8002/health
echo ""

# Web (solo status code)
curl -I http://localhost:3000 | head -1

echo "✅ Health checks completados"
```

### 5.2 Verificar Logs

```bash
# Ver logs de cada servicio (últimas 50 líneas)
echo "📋 Logs Backend:"
docker compose -f infra/docker-compose.yml logs --tail=50 backend | grep -E "(ERROR|WARN|Started|Listening)"

echo ""
echo "📋 Logs Bank-Advisor:"
docker compose -f infra/docker-compose.yml logs --tail=50 bank-advisor | grep -E "(ERROR|WARN|Started|Uvicorn)"

echo ""
echo "📋 Logs Web:"
docker compose -f infra/docker-compose.yml logs --tail=50 web | grep -E "(ERROR|ready|started)"

# Buscar errores críticos
echo ""
echo "🔍 Buscando errores críticos..."
docker compose -f infra/docker-compose.yml logs --tail=200 | grep -i "error" | tail -10
```

### 5.3 Verificar Versiones de Imágenes

```bash
echo "📦 Versiones deployadas:"
docker compose -f infra/docker-compose.yml ps --format "table {{.Service}}\t{{.Image}}\t{{.Status}}"
```

### 5.4 Tests Funcionales Manuales

Abrir en navegador: `https://invex.saptiva.com` (o la URL de producción)

1. **Login**
   - Usuario: `demo`
   - Password: `[USE_DEMO_CREDENTIALS]`

2. **Test 1: Query Básica**
   - Preguntar: "Dame el IMOR de INVEX"
   - ✅ Debe responder con dato numérico y chart

3. **Test 2: Chart con SISTEMA** (validar fix SISTEMA)
   - Preguntar: "Cartera total de SISTEMA en 2024"
   - ✅ Debe generar chart (no "banco no encontrado")

4. **Test 3: Chart Persistence** (validar Bug 8 fix)
   - Preguntar: "Cartera total de BBVA en 2024"
   - ✅ Debe aparecer chart
   - Recargar página (F5)
   - ✅ Chart debe restaurarse automáticamente

5. **Test 4: Métrica Inválida** (validar schema validator)
   - Preguntar: "Número de créditos hipotecarios de BBVA"
   - ✅ Debe pedir clarificación o sugerir `cartera_vivienda_total`

6. **Test 5: PNG Download**
   - Generar cualquier chart
   - Click en botón "Download PNG"
   - ✅ Debe descargar imagen correctamente

---

## Checklist Post-Deploy

- [ ] **Health checks pasando**
  - [ ] Backend: `curl http://localhost:8000/api/health`
  - [ ] Bank-Advisor: `curl http://localhost:8002/health`
  - [ ] Web: `curl -I http://localhost:3000`

- [ ] **Sin errores en logs**
  - [ ] Backend logs sin ERROR
  - [ ] Bank-Advisor logs sin ERROR
  - [ ] Web logs sin ERROR

- [ ] **Redis cache limpiado**
  - [ ] `docker exec redis redis-cli FLUSHDB` ejecutado

- [ ] **Frontend accesible**
  - [ ] URL pública responde: https://invex.saptiva.com

- [ ] **Tests funcionales pasando**
  - [ ] Query básica funciona: "Dame el IMOR de INVEX"
  - [ ] SISTEMA funciona: "Cartera total de SISTEMA"
  - [ ] Chart persistence funciona: Chart restaura al recargar (F5)
  - [ ] Schema validator funciona: Rechaza métricas inválidas
  - [ ] PNG download funciona

- [ ] **Verificaciones técnicas**
  - [ ] Named volume `backend_shared` eliminado antes del deploy
  - [ ] Imágenes v1.4.5 correctas: `docker compose ps`
  - [ ] Backup MongoDB creado en `backups/`

---

## Rollback (Si Hay Problemas)

### Opción 1: Rollback Rápido (Sin pérdida de datos)

```bash
# 1. Detener servicios
docker compose -f infra/docker-compose.yml down

# 2. Editar infra/docker-compose.images.yml
# Cambiar versiones a:
#   backend: 1.4.3
#   web: 1.4.3
#   bank-advisor: 1.4.4

# 3. Levantar versión anterior
docker compose \
    -f infra/docker-compose.yml \
    -f infra/docker-compose.images.yml \
    -f infra/docker-compose.production.yml \
    --env-file envs/.env \
    up -d

# 4. Limpiar cache
docker exec redis redis-cli FLUSHDB

echo "✅ Rollback a v1.4.3/1.4.4 completado"
```

### Opción 2: Rollback con Restauración de BD (Si hay corrupción)

```bash
# 1. Detener servicios
docker compose -f infra/docker-compose.yml down

# 2. Restaurar MongoDB
BACKUP_FILE="backups/mongodb-backup-pre-1.4.5-[TIMESTAMP].tar.gz"
tar xzf "$BACKUP_FILE" -C backups/

docker cp backups/mongodb-backup-pre-1.4.5-[TIMESTAMP] \
    octavios-chat-bajaware_invex-mongodb:/tmp/

docker exec octavios-chat-bajaware_invex-mongodb mongorestore \
    --username="octavios_user" \
    --password="[PASSWORD]" \
    --authenticationDatabase=admin \
    --drop \
    /tmp/mongodb-backup-pre-1.4.5-[TIMESTAMP]

# 3. Continuar con Opción 1 (cambiar versiones y levantar)
```

---

## Troubleshooting

### Issue: Container unhealthy después del deploy

```bash
# Ver logs detallados
docker compose logs backend --tail=200

# Buscar:
# - "ModuleNotFoundError" → Verificar que el volume backend_shared se eliminó
# - "Connection refused" → Verificar que MongoDB/Redis están corriendo
# - "ImportError" → Verificar que la imagen es la correcta (v1.4.5)
```

**Solución común**: Eliminar volume y reiniciar

```bash
docker compose rm -sf backend
docker volume rm octavios-chat-bajaware_invex_backend_shared
docker compose up -d backend
```

### Issue: Chart no restaura después del deploy

**Causa**: Nueva funcionalidad solo aplica a charts creados DESPUÉS del deploy

**Verificación**:
1. Crear un chart NUEVO post-deploy
2. Recargar página
3. El chart NUEVO debe restaurarse

**Charts viejos**: No tienen `tool_invocations` en metadata (se crearon antes del fix)

### Issue: "No encontré datos" en queries válidas

```bash
# Limpiar cache de Redis
docker exec redis redis-cli FLUSHDB

# Reiniciar bank-advisor
docker compose restart bank-advisor

# Verificar logs
docker compose logs bank-advisor --tail=50
```

### Issue: Frontend no carga (white screen)

```bash
# Verificar logs de Next.js
docker compose logs web --tail=100

# Buscar "Module not found" → Problema con standalone build
# Solución: Verificar que la imagen es 1.4.5
docker compose ps web
```

---

## Versiones de Imágenes

| Servicio | Anterior | Nueva | Cambios |
|----------|----------|-------|---------|
| backend | 1.4.3 | **1.4.5** | Chart persistence fix (Bug 8) |
| web | 1.4.3 | **1.4.5** | Soporte para artifact restoration |
| bank-advisor | 1.4.4 | **1.4.5** | SISTEMA tests + Schema validator |
| file-manager | 1.3.1 | 1.3.1 | Sin cambios |

---

## Commits Incluidos

1. **ec7c16bc** - fix(chat): add artifact_id to message metadata for chart persistence (BUG-8)
2. **37332382** - test(bankadvisor): add unit tests for SISTEMA inclusion anti-regression
3. **6711e5db** - feat(bankadvisor): add schema grounding validator to prevent metric hallucinations
4. **40ec2372** - test(e2e): add chart persistence E2E test (Bug 8 verification)
5. **4d057d3d** - docs(bankadvisor): add quality improvements summary
6. **9408b13c** - docs(bankadvisor): update quality improvements with E2E test completion

---

**Última actualización**: 2026-01-14
**Versión del documento**: 1.0
**Autor**: Claude Code
**Revisado por**: [Pendiente]
