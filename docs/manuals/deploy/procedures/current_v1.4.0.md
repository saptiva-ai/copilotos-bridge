# Guía de Deploy - v1.4.0

## Resumen de Cambios

**Versión**: `1.4.0`
**Fecha**: 2026-01-08
**Branch**: `main` (commit 2efe0c53)

### Cambios Principales

| Componente | Cambio | Impacto |
|------------|--------|---------|
| **backend** | BUG-09 Truth-gating, BUG-13 Guardrails | Prevención de alucinaciones y negociación |
| **web** | P0 chart fixes, loading state | UX mejorada, charts estables |
| **bank-advisor** | Happy Path 97.5% | Casos 28, 29, 33 resueltos |

### Nuevos Servicios (backend)

- `universe_validation_service.py` - Validación CNBV de bancos
- `refusal_tracker.py` - Persistencia de rechazos en Redis
- `truth_gating_service.py` - Validación post-generación LLM

---

## Lecciones de Deployments Anteriores

### 1. Named Volume Override (CRÍTICO)
```bash
# SIEMPRE eliminar el volumen antes de desplegar
docker compose rm -f backend bank-advisor
docker volume rm octavios-chat-bajaware_invex_backend_shared
```

### 2. Weaviate Cloud Connection
- Usar `connect_to_weaviate_cloud()` no `connect_to_custom()`
- Ya resuelto en v1.3.7+

### 3. Web Cache Permissions
- El Dockerfile ya incluye el fix de `/app/apps/web/.next/cache/images`

---

## Paso 1: Build Local (Desarrollo)

### 1.1 Verificar código actualizado
```bash
cd /home/jazielflo/Proyects/octavios-chat-bajaware_invex
git checkout main
git pull origin main
git log --oneline -3
# Verificar: 2efe0c53 feat(backend): implement BUG-09 truth-gating...
```

### 1.2 Build de imágenes
```bash
# Build todos los servicios
./scripts/deploy/build-v1.4.0.sh

# O build individual
./scripts/deploy/build-v1.4.0.sh backend
./scripts/deploy/build-v1.4.0.sh web
./scripts/deploy/build-v1.4.0.sh bank-advisor
```

### 1.3 Test local
```bash
# Levantar con imágenes recién construidas
docker compose -f infra/docker-compose.yml up -d

# Verificar health
curl http://localhost:8000/api/health
curl http://localhost:8002/health
curl http://localhost:3000

# Ejecutar Happy Path
python tests/e2e/test_happy_path_suite.py
# Esperado: 39/40 (97.5%)
```

---

## Paso 2: Push a Docker Hub

### 2.1 Login
```bash
docker login
# User: saptivaai o jazielflores1998
```

### 2.2 Push imágenes
```bash
./scripts/deploy/push-v1.4.0.sh

# O push individual
./scripts/deploy/push-v1.4.0.sh backend
./scripts/deploy/push-v1.4.0.sh web
./scripts/deploy/push-v1.4.0.sh bank-advisor
```

**Tiempo estimado**: 10-15 minutos total

---

## Paso 3: Deploy en Producción

### 3.1 Conectar al servidor
```bash
ssh jf@PROD_SERVER_IP
cd ~/octavios-chat-bajaware_invex
```

### 3.2 Backup (CRÍTICO)
```bash
# Backup MongoDB (credentials from envs/.env)
docker exec octavios-chat-bajaware_invex-mongodb mongodump \
    --username="${MONGODB_USER}" \
    --password="${MONGODB_PASS}" \
    --authenticationDatabase=admin \
    --out=/tmp/backup-pre-1.4.0

docker cp octavios-chat-bajaware_invex-mongodb:/tmp/backup-pre-1.4.0 \
    ./backups/mongodb-backup-pre-1.4.0

tar czf backups/mongodb-backup-pre-1.4.0.tar.gz backups/mongodb-backup-pre-1.4.0
```

### 3.3 Actualizar código
```bash
git fetch origin
git checkout main
git pull origin main
git log --oneline -1
# Verificar: 2efe0c53
```

### 3.4 ⚠️ Eliminar Named Volume (CRÍTICO)
```bash
# IMPORTANTE: Evita que código viejo sobreescriba el nuevo
docker compose -f infra/docker-compose.yml rm -f backend bank-advisor
docker volume rm octavios-chat-bajaware_invex_backend_shared 2>/dev/null || true
```

### 3.5 Pull y deploy
```bash
# Pull nuevas imágenes
docker compose \
    -f infra/docker-compose.yml \
    -f infra/docker-compose.images.yml \
    pull

# Deploy
docker compose \
    -f infra/docker-compose.yml \
    -f infra/docker-compose.images.yml \
    -f infra/docker-compose.production.yml \
    --env-file envs/.env \
    up -d
```

### 3.6 Verificación
```bash
# Esperar 30s para startup
sleep 30

# Health checks
curl http://localhost:8000/api/health
curl http://localhost:8002/health
curl -I http://localhost:3000

# Ver logs
docker compose -f infra/docker-compose.yml logs --tail=50 backend
docker compose -f infra/docker-compose.yml logs --tail=50 bank-advisor
docker compose -f infra/docker-compose.yml logs --tail=50 web

# Verificar versiones
docker compose -f infra/docker-compose.yml ps
```

---

## Checklist Post-Deploy

- [ ] Health checks pasando (backend, bank-advisor, web)
- [ ] Sin errores en logs
- [ ] Frontend accesible: https://invex.saptiva.com
- [ ] Query de prueba funciona: "Dame el IMOR de INVEX"
- [ ] Charts se renderizan correctamente
- [ ] No hay "Conversación no encontrada" flash

---

## Rollback

Si hay problemas:

```bash
# 1. Detener servicios
docker compose -f infra/docker-compose.yml down

# 2. Revertir a versión anterior
# Editar infra/docker-compose.images.yml:
#   backend: saptivaai/octavios-invex-backend:1.3.7
#   web: saptivaai/octavios-invex-web:1.3.5
#   bank-advisor: saptivaai/octavios-invex-bank-advisor:1.3.3-rag-fix

# 3. Levantar versión anterior
docker compose \
    -f infra/docker-compose.yml \
    -f infra/docker-compose.images.yml \
    -f infra/docker-compose.production.yml \
    --env-file envs/.env \
    up -d

# 4. Restaurar MongoDB si es necesario
tar xzf backups/mongodb-backup-pre-1.4.0.tar.gz
docker cp backups/mongodb-backup-pre-1.4.0 \
    octavios-chat-bajaware_invex-mongodb:/tmp/
docker exec octavios-chat-bajaware_invex-mongodb mongorestore \
    --username="${MONGODB_USER}" \
    --password="${MONGODB_PASS}" \
    --authenticationDatabase=admin \
    --drop \
    /tmp/mongodb-backup-pre-1.4.0
```

---

## Versiones de Imágenes

| Servicio | Anterior | Nueva |
|----------|----------|-------|
| backend | 1.3.7 | **1.4.0** |
| web | 1.3.5 | **1.4.0** |
| bank-advisor | 1.3.3-rag-fix | **1.4.0** |
| file-manager | 1.3.1 | 1.3.1 (sin cambios) |

---

## Troubleshooting

### Container unhealthy
```bash
docker compose logs backend --tail=100
# Buscar errores de import o conexión
```

### Código no actualizado en container
```bash
# Verificar que NO hay volume mount
docker inspect backend --format '{{json .Mounts}}' | jq .
# Si hay "backend_shared" → eliminar el volume
```

### Redis cache stale
```bash
docker exec redis redis-cli -a "${REDIS_PASS}" FLUSHDB
```

---

**Última actualización**: 2026-01-08
**Versión del documento**: 1.0
