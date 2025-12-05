# 🚀 Deploy Quick Start - Servidor de Producción

> **Plan completo:** Ver `docs/deployment/MIGRATION_PLAN_QDRANT.md`
>
> ⚠️ **IMPORTANTE:** Este documento usa variables de entorno definidas en `envs/.env.prod`
> Ver `envs/.env.prod.example` para configuración requerida.

---

## ⚡ Resumen Ejecutivo (30 min total)

### **Paso 0: Configurar Variables de Entorno**

Crea o edita `envs/.env.prod` con tu configuración:

```bash
# Copia el template
cp envs/.env.prod.example envs/.env.prod

# Edita con tus valores reales
nano envs/.env.prod
```

**Variables requeridas:**
- `PROD_SERVER_IP` - IP del servidor de producción
- `PROD_SERVER_USER` - Usuario SSH
- `PROD_SERVER_HOST` - Usuario@IP (e.g., user@1.2.3.4)
- `PROD_DEPLOY_PATH` - Path absoluto en el servidor
- `PROD_DOMAIN` - Dominio de producción
- `MONGODB_PASSWORD` - Contraseña de MongoDB

> ⚠️ **NUNCA** commitees `envs/.env.prod` al repositorio

---

### **Paso 1: Auditoría Pre-Deploy (5 min)**

```bash
# Cargar variables de entorno
source envs/.env.prod

# Copiar y ejecutar script de auditoría
scp scripts/audit-production-state.sh ${PROD_SERVER_HOST}:${PROD_DEPLOY_PATH}/scripts/
ssh ${PROD_SERVER_HOST} "chmod +x ${PROD_DEPLOY_PATH}/scripts/audit-production-state.sh"
ssh ${PROD_SERVER_HOST} 'bash -s' < scripts/audit-production-state.sh

# Descargar reporte
scp ${PROD_SERVER_HOST}:${PROD_DEPLOY_PATH}/audit-report-*.json ./
```

**Revisa:** Número de usuarios, sesiones, documentos. **Guarda estos números.**

---

### **Paso 2: Backup (10 min)**

```bash
# Backup de volúmenes Docker
scp scripts/backup-docker-volumes.sh ${PROD_SERVER_HOST}:${PROD_DEPLOY_PATH}/scripts/
ssh ${PROD_SERVER_HOST} "cd ${PROD_DEPLOY_PATH} && \
  chmod +x scripts/backup-docker-volumes.sh && \
  ./scripts/backup-docker-volumes.sh --backup-dir ~/backups/volumes"

# Verificar backup
ssh ${PROD_SERVER_HOST} 'ls -lh ~/backups/volumes/*/*.tar.gz'
```

**Criterio:** Archivos > 100KB creados exitosamente.

---

### **Paso 3: Deploy con TAR (15-20 min)**

```bash
# Asegurarse de que las variables están cargadas
source envs/.env.prod

# Opción recomendada: Deploy completo con build limpio
./scripts/deploy-with-tar.sh

# O si tienes prisa y ya hiciste build antes:
./scripts/deploy-with-tar.sh --incremental
```

**El script hace:**
1. Build de imágenes (API + Web)
2. Export a TAR comprimido
3. Transfer a servidor vía SCP
4. Git pull en servidor
5. Load imágenes nuevas
6. Restart contenedores
7. Health check automático

---

### **Paso 4: Verificación (5 min)**

```bash
# Health check API
ssh ${PROD_SERVER_HOST} 'curl -s http://localhost:8001/api/health | jq'

# Debe responder: {"status": "healthy", ...}

# Verificar Qdrant (nuevo contenedor)
ssh ${PROD_SERVER_HOST} 'docker ps | grep qdrant'
ssh ${PROD_SERVER_HOST} 'curl -s http://localhost:6333/collections | jq'

# Verificar datos persistidos (debe coincidir con auditoría)
ssh ${PROD_SERVER_HOST} "docker exec octavios-chat-capital414-mongodb mongosh \
  --username octavios_user \
  --password ${MONGODB_PASSWORD} \
  --authenticationDatabase admin \
  --quiet \
  --eval 'use octavios; db.users.countDocuments()'"
```

---

## 🆘 Si algo falla: Rollback

```bash
# 1. Detener contenedores
ssh ${PROD_SERVER_HOST} "cd ${PROD_DEPLOY_PATH}/infra && docker compose down"

# 2. Ver backups disponibles
ssh ${PROD_SERVER_HOST} 'ls -lh ~/backups/volumes/*'

# 3. Restaurar volumen (ejemplo MongoDB)
ssh ${PROD_SERVER_HOST} 'docker volume rm octavios-chat-capital414_mongodb_data && \
  docker volume create octavios-chat-capital414_mongodb_data && \
  docker run --rm \
    -v octavios-chat-capital414_mongodb_data:/target \
    -v ~/backups/volumes/TIMESTAMP:/backup:ro \
    alpine:latest \
    tar xzf /backup/octavios-chat-capital414_mongodb_data-*.tar.gz -C /target'

# 4. Reiniciar contenedores
ssh ${PROD_SERVER_HOST} "cd ${PROD_DEPLOY_PATH}/infra && docker compose up -d"
```

**Ver instrucciones completas de restore:**
```bash
ssh ${PROD_SERVER_HOST} 'cat ~/backups/volumes/TIMESTAMP/RESTORE_INSTRUCTIONS.txt'
```

---

## 📊 Checklist Rápido

Antes de empezar:
- [ ] Código pusheado a `main`
- [ ] Tests locales OK (`make test`)
- [ ] `envs/.env.prod` configurado correctamente
- [ ] Acceso SSH funcionando
- [ ] Espacio en disco servidor > 10GB

Durante deploy:
- [ ] Variables de entorno cargadas (`source envs/.env.prod`)
- [ ] Auditoría descargada ✓
- [ ] Backups creados ✓
- [ ] Deploy ejecutado ✓
- [ ] Health checks OK ✓
- [ ] Datos verificados ✓

---

## 🔧 Comandos Útiles

```bash
# Cargar variables de entorno
source envs/.env.prod

# Monitoreo de logs
ssh ${PROD_SERVER_HOST} 'docker logs -f --tail=50 octavios-chat-capital414-api'

# Ver todos los contenedores
ssh ${PROD_SERVER_HOST} 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Reiniciar servicio específico
ssh ${PROD_SERVER_HOST} "cd ${PROD_DEPLOY_PATH}/infra && docker compose restart api"

# Ver uso de recursos
ssh ${PROD_SERVER_HOST} 'docker stats --no-stream'
```

---

## 🎯 Cambios Principales de Esta Versión

**Nuevo:**
- ✅ Contenedor **Qdrant** para RAG (vector database)
- ✅ Volúmenes `qdrant_data` y `qdrant_snapshots`
- ✅ Mejoras en UI de auditoría (canvas streaming)
- ✅ Thumbnails persistentes en MinIO

**Sin cambios:**
- ⚪ Esquema de MongoDB (backward compatible)
- ⚪ Datos de usuarios/sesiones/documentos
- ⚪ Configuración de Redis

---

## 📞 Soporte

**Si tienes problemas:**
1. Revisa logs: `ssh ${PROD_SERVER_HOST} 'docker compose logs --tail=100'`
2. Consulta plan completo: `docs/deployment/MIGRATION_PLAN_QDRANT.md`
3. Ejecuta rollback si es crítico (ver arriba)

---

## 🔒 Nota de Seguridad

Este documento **NO** contiene credenciales hardcodeadas. Todas las variables sensibles (IPs, usuarios, contraseñas, paths) se leen desde `envs/.env.prod` que está en `.gitignore`.

**Variables de entorno usadas:**
- `${PROD_SERVER_IP}` - IP del servidor
- `${PROD_SERVER_USER}` - Usuario SSH
- `${PROD_SERVER_HOST}` - Host SSH completo
- `${PROD_DEPLOY_PATH}` - Path de deployment
- `${MONGODB_PASSWORD}` - Password de MongoDB

Ver `envs/.env.prod.example` para template completo.

---

**Creado:** 2025-11-23
**Tiempo total estimado:** 30-40 minutos
