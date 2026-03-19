# Guia de Deploy - v1.4.2

## Resumen de Cambios

**Version**: `1.4.2`
**Fecha**: 2026-01-10
**Branch**: `main` (pendiente commit con version bump)

### Cambios Principales

| Componente | Cambio | Impacto |
|------------|--------|---------|
| **backend** | REFACTOR-001: 14 servicios streaming extraidos (-58% LOC), BA-003 SQL strip | Mantenibilidad, SQL ya no se muestra en chat |
| **web** | BUG-03/06 fixes, chart improvements, SQL strip optimization | UX mejorada, PNG download, Reset Zoom |
| **bank-advisor** | NLP improvements (92.5%), multi-tenant, BA-001/BA-002 | Mejor precision, eliminacion hardcodes INVEX |

### Nuevos Servicios (backend)

14 servicios extraidos en `apps/backend/src/services/streaming/`:
- `analytics_context.py` - Contexto para LLM con datos bancarios
- `audit_response_builder.py` - Construccion de respuestas de auditoria
- `auditor_formatter.py` - Formateo de resultados de validacion
- `chart_event_builder.py` - Construccion de eventos SSE para charts
- `chart_flow_handler.py` - Manejo del flujo completo de charts
- `chart_normalizer.py` - Normalizacion de datos de graficos
- `chunk_emitter.py` - Emision de chunks SSE
- `document_context.py` - Construccion de contexto de documentos
- `message_persistence.py` - Persistencia de mensajes
- `response_postprocessor.py` - Post-procesamiento (SQL strip)
- `saptiva_streamer.py` - Streaming con Saptiva LLM
- `token_budget.py` - Gestion de presupuesto de tokens

---

## Leciones de Deployments Anteriores

### 1. Named Volume Override (CRITICO)
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

### 1.1 Verificar codigo actualizado
```bash
cd /home/jazielflo/Proyects/octavios-chat-bajaware_invex
git checkout main
git pull origin main
git log --oneline -3
```

### 1.2 Build de imagenes
```bash
# Build todos los servicios con auto-increment de version
./scripts/deploy/build.sh --next

# O con version explicita
./scripts/deploy/build.sh -v 1.4.2

# O build individual
./scripts/deploy/build.sh -v 1.4.2 -s backend
./scripts/deploy/build.sh -v 1.4.2 -s web
./scripts/deploy/build.sh -v 1.4.2 -s bank-advisor
```

### 1.3 Test local
```bash
# Levantar con imagenes recien construidas
docker compose -f infra/docker-compose.yml up -d

# Verificar health
curl http://localhost:8000/api/health
curl http://localhost:8002/health
curl http://localhost:3000

# Ejecutar Happy Path representativo
pytest tests/e2e/test_happy_path_suite.py -k "rag or nl2sql or comparison" -v
```

---

## Paso 2: Push a Docker Hub

### 2.1 Login
```bash
docker login
# User: saptivaai
```

### 2.2 Push imagenes
```bash
./scripts/deploy/push.sh -v 1.4.2

# O push individual
./scripts/deploy/push.sh -v 1.4.2 -s backend
./scripts/deploy/push.sh -v 1.4.2 -s web
./scripts/deploy/push.sh -v 1.4.2 -s bank-advisor
```

**Tiempo estimado**: 10-15 minutos total

---

## Paso 3: Actualizar docker-compose.images.yml

```bash
./scripts/deploy/update-images.sh -v 1.4.2

# Verificar cambios
git diff infra/docker-compose.images.yml

# Commit
git add infra/docker-compose.images.yml
git commit -m "chore: bump images to v1.4.2"
git push origin main
```

---

## Paso 4: Deploy en Produccion

### 4.1 Conectar al servidor
```bash
ssh jf@PROD_SERVER_IP
cd ~/octavios-chat-bajaware_invex
```

### 4.2 Backup (CRITICO)
```bash
# Backup MongoDB (credentials from envs/.env)
docker exec octavios-chat-bajaware_invex-mongodb mongodump \
    --username="${MONGODB_USER}" \
    --password="${MONGODB_PASS}" \
    --authenticationDatabase=admin \
    --out=/tmp/backup-pre-1.4.2

docker cp octavios-chat-bajaware_invex-mongodb:/tmp/backup-pre-1.4.2 \
    ./backups/mongodb-backup-pre-1.4.2

tar czf backups/mongodb-backup-pre-1.4.2.tar.gz backups/mongodb-backup-pre-1.4.2
```

### 4.3 Actualizar codigo
```bash
git fetch origin
git checkout main
git pull origin main
git log --oneline -1
```

### 4.4 Eliminar Named Volume (CRITICO)
```bash
# IMPORTANTE: Evita que codigo viejo sobreescriba el nuevo
docker compose -f infra/docker-compose.yml rm -f backend bank-advisor
docker volume rm octavios-chat-bajaware_invex_backend_shared 2>/dev/null || true
```

### 4.5 Pull y deploy
```bash
# Pull nuevas imagenes
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

### 4.6 Limpiar cache de Redis (IMPORTANTE)
```bash
# Limpiar cache para evitar datos stale despues del deploy
docker exec redis redis-cli FLUSHDB
# O si Redis tiene password:
# docker exec redis redis-cli -a "${REDIS_PASS}" FLUSHDB
```

### 4.7 Verificacion
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
- [ ] Redis cache limpiado (`docker exec redis redis-cli FLUSHDB`)
- [ ] Frontend accesible: https://invex.saptiva.com
- [ ] Query de prueba funciona: "Dame el IMOR de INVEX"
- [ ] Charts se renderizan correctamente
- [ ] SQL no aparece en el chat (solo en panel de canvas)
- [ ] PNG download funciona

---

## Rollback

Si hay problemas:

```bash
# 1. Detener servicios
docker compose -f infra/docker-compose.yml down

# 2. Revertir a version anterior
# Editar infra/docker-compose.images.yml:
#   backend: saptivaai/octavios-invex-backend:1.4.1
#   web: saptivaai/octavios-invex-web:1.4.1
#   bank-advisor: saptivaai/octavios-invex-bank-advisor:1.4.1

# 3. Levantar version anterior
docker compose \
    -f infra/docker-compose.yml \
    -f infra/docker-compose.images.yml \
    -f infra/docker-compose.production.yml \
    --env-file envs/.env \
    up -d

# 4. Restaurar MongoDB si es necesario
tar xzf backups/mongodb-backup-pre-1.4.2.tar.gz
docker cp backups/mongodb-backup-pre-1.4.2 \
    octavios-chat-bajaware_invex-mongodb:/tmp/
docker exec octavios-chat-bajaware_invex-mongodb mongorestore \
    --username="${MONGODB_USER}" \
    --password="${MONGODB_PASS}" \
    --authenticationDatabase=admin \
    --drop \
    /tmp/mongodb-backup-pre-1.4.2
```

---

## Versiones de Imagenes

| Servicio | Anterior | Nueva |
|----------|----------|-------|
| backend | 1.4.1 | **1.4.2** |
| web | 1.4.1 | **1.4.2** |
| bank-advisor | 1.4.1 | **1.4.2** |
| file-manager | 1.3.1 | 1.3.1 (sin cambios) |

---

## Troubleshooting

### Container unhealthy
```bash
docker compose logs backend --tail=100
# Buscar errores de import o conexion
```

### Codigo no actualizado en container
```bash
# Verificar que NO hay volume mount
docker inspect backend --format '{{json .Mounts}}' | jq .
# Si hay "backend_shared" -> eliminar el volume
```

### Redis cache stale
```bash
docker exec redis redis-cli -a "${REDIS_PASS}" FLUSHDB
```

### Streaming services not found
```bash
# Verificar que los servicios estan en el container
docker exec backend python -c "from services.streaming import *; print('OK')"
```

---

**Ultima actualizacion**: 2026-01-10
**Version del documento**: 1.0
