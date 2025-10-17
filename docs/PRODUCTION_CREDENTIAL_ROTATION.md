# 🔐 Rotación de Credenciales en Producción - Guía Completa

**CRÍTICO**: Esta guía es para ambientes de **PRODUCCIÓN**. Sigue cada paso cuidadosamente.

---

## ⚠️ Problemas Críticos que DEBES Evitar

### 1. ❌ NUNCA uses `docker compose restart` después de cambiar credenciales

**Problema**: `restart` no recarga variables de entorno del archivo `.env`.

**Síntoma**: Después de rotar credenciales y hacer `restart`, obtienes:
```
pymongo.errors.OperationFailure: Authentication failed.
redis.exceptions.AuthenticationError: invalid username-password pair
```

**Solución Correcta**: Usa `down` + `up`
```bash
# ❌ MAL
docker compose restart api

# ✅ BIEN
docker compose down api
docker compose up -d api
```

---

### 2. ❌ NUNCA borres volúmenes en producción para "arreglar" credenciales

**Problema**: Borrar volúmenes = **PÉRDIDA DE DATOS PERMANENTE**.

**Síntoma**: "Las credenciales no coinciden, voy a borrar todo y empezar de nuevo"

**Solución Correcta**: Usa los scripts de rotación segura:
```bash
# ✅ Rota la contraseña SIN tocar los datos
./scripts/rotate-mongo-credentials.sh OLD_PASS NEW_PASS
```

---

### 3. ❌ NUNCA ejecutes `make reset` en producción

**Problema**: `make reset` está diseñado SOLO para desarrollo. Borra todos los volúmenes.

**Si alguien lo ejecuta en PROD**:
```bash
make reset  # ⚠️ BORRA TODA LA BASE DE DATOS
```

**Consecuencia**: Pérdida total de datos de producción.

**Protección**: Documenta claramente en runbooks que `make reset` es SOLO para DEV.

---

### 4. ⚠️ `env_file` DEBE estar configurado en docker-compose.yml

**Problema**: Si MongoDB/Redis no tienen `env_file` definido, usan valores por defecto en lugar de leer el `.env`.

**Verificación**:
```bash
# Revisar que AMBOS servicios tengan env_file
grep -A 5 "mongodb:" infra/docker-compose.yml | grep env_file
grep -A 5 "redis:" infra/docker-compose.yml | grep env_file
```

**Debe aparecer**:
```yaml
mongodb:
  image: mongo:7.0
  env_file:
    - ../envs/.env  # ← CRÍTICO

redis:
  image: redis:7-alpine
  env_file:
    - ../envs/.env  # ← CRÍTICO
```

---

## ✅ Proceso Seguro de Rotación en Producción

### Pre-requisitos

- [ ] Tienes acceso SSH al servidor de producción
- [ ] Tienes permisos sudo
- [ ] Conoces las credenciales actuales (están en `envs/.env.prod`)
- [ ] Has probado la rotación en DEV/Staging primero
- [ ] Tienes un backup reciente (< 24 horas)

### Checklist de Seguridad

- [ ] **Ventana de mantenimiento programada** (notifica al equipo)
- [ ] **Backup completo creado** (`make backup-mongodb-prod`)
- [ ] **Verificar backup** (que el archivo existe y tiene tamaño > 0)
- [ ] **Plan de rollback preparado** (documentado abajo)
- [ ] **Monitoreo activo** (logs, errores, métricas)

---

## 📋 Procedimiento Paso a Paso

### Fase 1: Preparación (15 minutos antes)

```bash
# 1. Conectar al servidor de producción
ssh user@production-server

# 2. Ir al directorio del proyecto
cd /opt/copilotos-bridge

# 3. Verificar estado actual
make health

# Debe mostrar:
# ✅ API is healthy
# ✅ MongoDB is connected
# ✅ Redis is connected

# 4. Crear backup ANTES de la rotación
make backup-mongodb-prod

# Verificar que el backup se creó
ls -lh backups/mongodb-*.archive
# Debe mostrar un archivo con fecha/hora actual y tamaño > 0

# 5. Guardar credenciales actuales (para rollback)
cp envs/.env.prod envs/.env.prod.backup.$(date +%Y%m%d-%H%M%S)
```

---

### Fase 2: Rotación de MongoDB (5-10 minutos)

```bash
# 1. Verificar credenciales actuales
grep MONGODB_PASSWORD envs/.env.prod
# Anota la contraseña actual: OLD_MONGO_PASS

# 2. Generar nueva contraseña segura
NEW_MONGO_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
echo "Nueva contraseña MongoDB: $NEW_MONGO_PASS"

# ⚠️ IMPORTANTE: Guarda esta contraseña en lugar seguro (1Password, etc.)

# 3. Ejecutar script de rotación
./scripts/rotate-mongo-credentials.sh "OLD_MONGO_PASS" "$NEW_MONGO_PASS"

# Debe mostrar:
# ✅ Rotación completada!

# 4. Actualizar archivo .env.prod
nano envs/.env.prod
# Cambiar: MONGODB_PASSWORD=$NEW_MONGO_PASS

# 5. Recargar servicios (CRÍTICO: usar down+up, NO restart)
docker compose -f infra/docker-compose.yml down api
docker compose -f infra/docker-compose.yml up -d api

# 6. Esperar a que API esté lista (30-60 segundos)
watch -n 2 'curl -s http://localhost:8001/api/health | jq'

# Presiona Ctrl+C cuando veas: "status": "healthy"

# 7. Verificar que API puede conectar a MongoDB
make health

# Debe mostrar:
# ✅ API is healthy
# ✅ MongoDB is connected
```

---

### Fase 3: Rotación de Redis (5-10 minutos)

```bash
# 1. Verificar credenciales actuales de Redis
grep REDIS_PASSWORD envs/.env.prod

# 2. Generar nueva contraseña segura
NEW_REDIS_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
echo "Nueva contraseña Redis: $NEW_REDIS_PASS"

# ⚠️ IMPORTANTE: Guarda esta contraseña en lugar seguro

# 3. Ejecutar script de rotación
./scripts/rotate-redis-credentials.sh "$NEW_REDIS_PASS"

# Debe mostrar:
# ✅ Rotación temporal completada!

# 4. Actualizar archivo .env.prod
nano envs/.env.prod
# Cambiar: REDIS_PASSWORD=$NEW_REDIS_PASS

# 5. Recargar servicios (CRÍTICO: usar down+up, NO restart)
docker compose -f infra/docker-compose.yml down redis api
docker compose -f infra/docker-compose.yml up -d redis api

# 6. Esperar a que servicios estén listos
sleep 10
make health

# Debe mostrar:
# ✅ API is healthy
# ✅ MongoDB is connected
# ✅ Redis is connected
```

---

### Fase 4: Verificación Post-Rotación (5 minutos)

```bash
# 1. Verificar que usuarios pueden hacer login
# (Usar un usuario de prueba o Postman)
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"test_user","password":"test_password"}'

# Debe devolver: {"access_token":"..."}

# 2. Verificar logs de errores
docker logs copilotos-api --tail 50 | grep -i error

# No debe haber errores de autenticación

# 3. Verificar métricas
# - Usuarios activos
# - Tasa de errores
# - Latencia de respuestas

# 4. Crear backup POST-rotación
make backup-mongodb-prod

# 5. Verificar que el backup nuevo contiene los datos
ls -lh backups/mongodb-*.archive
```

---

### Fase 5: Actualizar Vault/Secrets Manager

```bash
# ⚠️ CRÍTICO: Actualiza las credenciales en tu secrets manager

# Ejemplos según tu infraestructura:

# AWS Secrets Manager:
aws secretsmanager update-secret \
  --secret-id copilotos/prod/mongodb-password \
  --secret-string "$NEW_MONGO_PASS"

# 1Password CLI:
op item edit "Copilotos Production" \
  "MongoDB Password=$NEW_MONGO_PASS"

# Kubernetes Secrets:
kubectl create secret generic copilotos-credentials \
  --from-literal=mongodb-password="$NEW_MONGO_PASS" \
  --dry-run=client -o yaml | kubectl apply -f -

# HashiCorp Vault:
vault kv put secret/copilotos/prod \
  mongodb_password="$NEW_MONGO_PASS"
```

---

## 🔙 Plan de Rollback

### Si algo sale mal durante la rotación:

#### Opción 1: Revertir credenciales (más rápido, sin pérdida de datos)

```bash
# 1. Detener servicios
docker compose -f infra/docker-compose.yml down api redis

# 2. Restaurar archivo .env.prod anterior
cp envs/.env.prod.backup.TIMESTAMP envs/.env.prod

# 3. Obtener credencial vieja
OLD_MONGO_PASS=$(grep MONGODB_PASSWORD envs/.env.prod.backup.TIMESTAMP | cut -d= -f2)
OLD_REDIS_PASS=$(grep REDIS_PASSWORD envs/.env.prod.backup.TIMESTAMP | cut -d= -f2)

# 4. Rotar HACIA ATRÁS (usando contraseña nueva como "old" y vieja como "new")
./scripts/rotate-mongo-credentials.sh "$NEW_MONGO_PASS" "$OLD_MONGO_PASS"
./scripts/rotate-redis-credentials.sh "$OLD_REDIS_PASS"

# 5. Reiniciar servicios
docker compose -f infra/docker-compose.yml up -d

# 6. Verificar
make health
```

#### Opción 2: Restaurar desde backup (si Opción 1 falla)

```bash
# ⚠️ ADVERTENCIA: Perderás datos creados DESPUÉS del backup

# 1. Detener servicios
docker compose -f infra/docker-compose.yml down

# 2. Restaurar backup
BACKUP_FILE=$(ls -t backups/mongodb-*.archive | head -1)
./scripts/restore-mongodb.sh "$BACKUP_FILE"

# 3. Restaurar credenciales antiguas
cp envs/.env.prod.backup.TIMESTAMP envs/.env.prod

# 4. Reiniciar todo desde cero
docker compose -f infra/docker-compose.yml up -d

# 5. Verificar
make health
```

---

## 🚨 Troubleshooting

### Problema: "Authentication failed" después de rotación

**Diagnóstico**:
```bash
# Ver logs de MongoDB
docker logs copilotos-mongodb --tail 50 | grep -i auth

# Ver qué contraseña tiene el contenedor
docker inspect copilotos-mongodb --format='{{range .Config.Env}}{{println .}}{{end}}' | grep MONGO_INITDB
```

**Causa Común**: Usaste `restart` en lugar de `down`+`up`

**Solución**:
```bash
docker compose -f infra/docker-compose.yml down api
docker compose -f infra/docker-compose.yml up -d api
```

---

### Problema: Backup restore falla con "Authentication failed"

**Causa**: Intentas restaurar con credenciales nuevas pero el backup usa las viejas

**Solución**:
```bash
# Restaurar debe usar la contraseña ACTUAL (post-rotación)
CURRENT_PASS=$(grep MONGODB_PASSWORD envs/.env.prod | cut -d= -f2)

docker exec copilotos-mongodb mongorestore \
  --uri="mongodb://copilotos_prod_user:$CURRENT_PASS@localhost:27017/copilotos?authSource=admin" \
  --archive=/tmp/backup.archive \
  --drop
```

---

### Problema: Redis no acepta nueva contraseña

**Diagnóstico**:
```bash
# Verificar que Redis tenga la contraseña correcta
docker exec copilotos-redis redis-cli -a "$NEW_REDIS_PASS" PING

# Debe devolver: PONG
```

**Causa Común**: Redis necesita restart completo (no solo CONFIG SET)

**Solución**:
```bash
docker compose -f infra/docker-compose.yml down redis
docker compose -f infra/docker-compose.yml up -d redis
```

---

## 📊 Métricas de Éxito

Después de la rotación, verifica:

- [ ] **Disponibilidad**: API responde con 200 OK
- [ ] **Autenticación**: Usuarios pueden hacer login
- [ ] **Base de datos**: Queries funcionan correctamente
- [ ] **Cache**: Redis responde a comandos
- [ ] **Logs limpios**: Sin errores de autenticación
- [ ] **Backups**: Nuevo backup creado y verificado
- [ ] **Secrets manager**: Credenciales actualizadas
- [ ] **Documentación**: Runbook actualizado con fecha de última rotación

---

## 📅 Calendario de Rotación Recomendado

| Credencial | Frecuencia | Última Rotación | Próxima Rotación |
|------------|------------|-----------------|------------------|
| MongoDB Password | 3 meses | __________ | __________ |
| Redis Password | 3 meses | __________ | __________ |
| JWT Secret Key | 6 meses | __________ | __________ |
| Saptiva API Key | Por política | __________ | __________ |

---

## 🔗 Referencias

- [Guía de Credenciales General](./CREDENTIAL_MANAGEMENT.md)
- [Comandos Make](./MAKEFILE_CREDENTIAL_COMMANDS.md)
- [Disaster Recovery](./DISASTER-RECOVERY.md)
- [Troubleshooting Común](./COMMON_ISSUES.md)

---

## ✅ Checklist Final

Antes de marcar la rotación como completada:

- [ ] Todas las fases ejecutadas sin errores
- [ ] Health check passing (API, MongoDB, Redis)
- [ ] Login de usuarios funcional
- [ ] Backup post-rotación creado
- [ ] Secrets manager actualizado
- [ ] Equipo notificado del cambio
- [ ] Calendario de rotación actualizado
- [ ] Archivos de backup antiguos etiquetados
- [ ] Monitoreo activo por 24 horas
- [ ] Documentación de runbook actualizada

---

**Última actualización:** 2025-10-10
**Autor:** Claude Code / Equipo Saptiva
**Revisado por:** __________
**Próxima revisión:** __________
