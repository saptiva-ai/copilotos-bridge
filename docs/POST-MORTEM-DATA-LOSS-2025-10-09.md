# POST-MORTEM: Pérdida de Datos MongoDB - 2025-10-09

**Fecha del Incidente:** 9 de Octubre, 2025
**Severidad:** CRÍTICA - Pérdida total de datos históricos de producción
**Tiempo de Detección:** ~30 minutos después del deployment
**Tiempo de Recuperación:** Irrecuperable
**Estado Final:** Base de datos reinicializada, datos históricos perdidos permanentemente

---

## 📋 RESUMEN EJECUTIVO

Durante un deployment de producción el 9 de octubre de 2025, se perdieron todos los datos históricos de MongoDB debido a una combinación de:
1. **Configuración incorrecta de volúmenes** entre entornos dev y prod
2. **Ausencia de backups automatizados** de la base de datos
3. **Múltiples reinicios de MongoDB** durante troubleshooting que sobrescribieron datos
4. **Falta de procedimientos documentados** de backup/restore

---

## 🕐 TIMELINE DEL INCIDENTE

### **20:00** - Inicio del Deployment
- Deployment iniciado con `make deploy-tar`
- Imágenes Docker construidas localmente con target de producción
- Transferencia exitosa de imágenes vía TAR a servidor

### **20:17** - Primer Error de Autenticación MongoDB
```
pymongo.errors.OperationFailure: Authentication failed
Credential mismatch: API buscando credenciales diferentes a las inicializadas
```
**Causa:** docker-compose.yml base tenía hardcoded `env_file: ../envs/.env` (dev) en lugar de `.env.prod`

### **20:25-20:45** - Múltiples Intentos de Fix
- Limpieza de volúmenes con `docker compose down -v` **(PUNTO CRÍTICO DE PÉRDIDA)**
- Creación de symlinks `.env -> .env.prod`
- Reintentos con diferentes configuraciones
- **Cada `down -v` eliminaba datos y recreaba volúmenes vacíos**

### **20:46** - Redirección a TAR Deployment
- Usuario solicitó enfoque más limpio
- Construcción de imágenes locales exitosa
- Problema: Web image usando target dev en lugar de runner

### **21:06** - Fix de Build Targets
- Script de deployment modificado para usar targets correctos:
  - API: `--target production`
  - Web: `--target runner`

### **21:46** - MongoDB Reinitializado
- Al reiniciar servicios, MongoDB creó base de datos nueva
- Usuario detectó pérdida de historial
- **Solo 1 usuario, 1 sesión, 2 mensajes** (datos de prueba del día)

### **21:52-22:00** - Intento de Recuperación
- Identificación de archivos históricos en `/opt/copilotos-bridge/data/mongodb/`
- Intento fallido de restauración manual
- **Problema:** Archivos sin catálogo correcto (`_mdb_catalog.wt`) son irrecuperables

### **22:04** - Aceptación y Reinicialización
- Decisión de empezar con base de datos limpia
- Todos los servicios healthy y funcionando

---

## 🔍 ANÁLISIS DE CAUSAS RAÍZ

### **Causa Primaria: Configuración de Volúmenes Inconsistente**

#### **Problema 1: Múltiples Ubicaciones de Datos**
```yaml
# docker-compose.yml (DEV) - Usaba Docker volumes anónimos
volumes:
  mongodb_data:
    driver: local

# docker-compose.prod.yml - Configurado para bind mounts
volumes:
  - /opt/copilotos-bridge/data/mongodb:/data/db
```

**Impacto:**
- Datos históricos en `/opt/copilotos-bridge/data/mongodb/` (nunca usado por prod)
- Datos de prod en `/var/lib/docker/volumes/copilotos-prod_mongodb_data/`
- **Dos sistemas completamente separados**

#### **Problema 2: COMPOSE_PROJECT_NAME Cambió**
```bash
# Original: COMPOSE_PROJECT_NAME=copilotos
# Producción: COMPOSE_PROJECT_NAME=copilotos-prod

# Resultado: Volúmenes diferentes
copilotos_mongodb_data       # Dev (371MB de datos históricos)
copilotos-prod_mongodb_data  # Prod (recreado vacío múltiples veces)
```

### **Causa Secundaria: Ausencia de Backups**

**Estado del Sistema de Backups:**
- ❌ No había backups automatizados de MongoDB
- ❌ No había cron jobs configurados
- ❌ No había snapshots de servidor
- ❌ No había documentación de procedimientos de backup
- ✅ Solo existía un backup manual de 108 bytes (casi vacío)

### **Causa Terciaria: Comandos Destructivos Durante Troubleshooting**

**Comandos Ejecutados que Causaron Pérdida:**
```bash
# 1. Limpieza de volúmenes (destruye datos)
docker compose down -v

# 2. Recreación de volúmenes vacíos
docker compose up -d

# 3. Remoción manual de imágenes antiguas
docker rmi copilotos-web:latest copilotos-api:latest

# 4. Múltiples reinicios de MongoDB
# Cada reinicio sin catálogo correcto creaba base de datos nueva
```

**Por qué fueron destructivos:**
- `-v` flag elimina volúmenes nombrados permanentemente
- Sin backups previos, la eliminación fue irrecuperable
- MongoDB sin `_mdb_catalog.wt` correcto no puede leer archivos de colección

### **Causa Cuaternaria: Docker Compose Override No Persistente**

El deployment script creaba `docker-compose.override.yml` temporalmente:
```bash
# Deployment script
ssh "$SERVER" "cat > docker-compose.override.yml <<EOF
image: copilotos-web:latest
build: {}
EOF"

# ...después...
ssh "$SERVER" "rm -f docker-compose.override.yml"
```

**Problema:** Al hacer `docker compose down/up` manual, el override no existía y Docker volvía a build target dev.

---

## 💥 IMPACTO DEL INCIDENTE

### **Datos Perdidos**
- ❌ **Todos los usuarios históricos** (cantidad desconocida)
- ❌ **Todas las sesiones de chat** anteriores a hoy
- ❌ **Todos los mensajes** históricos
- ❌ **Todo el historial de eventos**
- ❌ **Todas las fuentes de investigación**
- ❌ **Todas las tareas** guardadas

### **Datos Preservados**
- ✅ Código fuente (Git)
- ✅ Configuración de infraestructura
- ✅ Archivos de colección MongoDB (irrecuperables sin catálogo)

### **Impacto en Usuarios**
- Usuario actual (jaziel/jf@saptiva.com) perdió todo su historial
- Cualquier otro usuario que existiera perdió su cuenta y datos
- **Necesidad de re-registro** para todos los usuarios

### **Impacto Operacional**
- ~4 horas de downtime/troubleshooting
- Pérdida de confianza en sistema de deployment
- Urgencia crítica para implementar backups

---

## 🛡️ MEDIDAS PREVENTIVAS IMPLEMENTADAS INMEDIATAMENTE

### ✅ **1. Docker Compose Override Permanente**
Creado archivo permanente en servidor:
```yaml
# /home/jf/copilotos-bridge/infra/docker-compose.override.yml
version: '3.8'
services:
  api:
    image: copilotos-api:latest
    build: {}
  web:
    image: copilotos-web:latest
    build: {}
```

**Beneficio:** Previene que `docker compose up` reconstruya con target dev

### ✅ **2. Documentación de Configuración de Volúmenes**
```yaml
# PRODUCCIÓN - Usar volúmenes Docker nombrados
volumes:
  mongodb_data:
    name: copilotos-prod_mongodb_data
    driver: local

# NUNCA usar bind mounts para datos de producción
# NUNCA usar flag -v sin backup previo
```

---

## 🚨 PLAN DE ACCIÓN URGENTE (SIGUIENTES 24 HORAS)

### **Priority 1: Sistema de Backups Automatizados** 🔴

#### **A. Backup Script de MongoDB**
```bash
#!/bin/bash
# /home/jf/scripts/backup-mongodb.sh

BACKUP_DIR="/home/jf/backups/mongodb"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Crear backup
docker exec copilotos-prod-mongodb mongodump \
  --uri="mongodb://copilotos_prod_user:ProdMongo2024!SecurePass@localhost:27017/copilotos?authSource=admin" \
  --gzip \
  --archive="/backup/copilotos_${DATE}.gz"

# Copiar del contenedor al host
docker cp copilotos-prod-mongodb:/backup/copilotos_${DATE}.gz ${BACKUP_DIR}/

# Limpiar backups antiguos
find ${BACKUP_DIR} -name "copilotos_*.gz" -mtime +${RETENTION_DAYS} -delete

# Log
echo "$(date): Backup completed - copilotos_${DATE}.gz" >> ${BACKUP_DIR}/backup.log
```

#### **B. Cron Job para Backups Automáticos**
```cron
# Backup MongoDB cada 6 horas
0 */6 * * * /home/jf/scripts/backup-mongodb.sh

# Backup completo diario a las 2 AM
0 2 * * * /home/jf/scripts/backup-full-system.sh
```

#### **C. Backup de Volúmenes Docker**
```bash
#!/bin/bash
# /home/jf/scripts/backup-docker-volumes.sh

BACKUP_DIR="/home/jf/backups/docker-volumes"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup MongoDB volume
docker run --rm \
  -v copilotos-prod_mongodb_data:/data \
  -v ${BACKUP_DIR}:/backup \
  alpine tar czf /backup/mongodb_${DATE}.tar.gz -C /data .

# Backup Redis volume (opcional pero recomendado)
docker run --rm \
  -v copilotos-prod_redis_data:/data \
  -v ${BACKUP_DIR}:/backup \
  alpine tar czf /backup/redis_${DATE}.tar.gz -C /data .
```

### **Priority 2: Procedimientos de Recuperación Documentados** 🟡

Crear `docs/DISASTER-RECOVERY.md` con:
1. Procedimiento completo de restore desde backup
2. Verificación de integridad de backups
3. Procedimiento de rollback de deployment
4. Contactos de emergencia

### **Priority 3: Monitoreo de Backups** 🟡

```bash
#!/bin/bash
# /home/jf/scripts/monitor-backups.sh

# Verificar que exista backup reciente (< 6 horas)
LATEST_BACKUP=$(find /home/jf/backups/mongodb -name "copilotos_*.gz" -mmin -360 | wc -l)

if [ $LATEST_BACKUP -eq 0 ]; then
  # Enviar alerta (configurar con servicio de alertas)
  echo "⚠️  WARNING: No MongoDB backup found in last 6 hours!" | mail -s "BACKUP ALERT" admin@saptiva.com
fi
```

### **Priority 4: Configuración de Volúmenes Consistente** 🟢

**Modificar `docker-compose.yml` base:**
```yaml
# NUNCA usar env_file hardcoded
# services:
#   mongodb:
#     env_file:  # <-- REMOVE THIS
#       - ../envs/.env
```

**Usar variables de entorno en su lugar:**
```yaml
services:
  mongodb:
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGODB_USER}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_PASSWORD}
```

---

## 📚 LECCIONES APRENDIDAS

### **1. Backups No Son Opcionales**
> "Si no está en backup, no existe"

- Los backups deben ser automáticos, frecuentes y verificados
- Política mínima: Backup cada 6 horas + Daily + Weekly + Monthly
- Retención: 30 días de backups horarios, 12 meses de backups mensuales

### **2. Flags Destructivos Requieren Confirmación**
```bash
# MAL: Destructivo sin confirmación
docker compose down -v

# MEJOR: Wrapper con confirmación
function docker-compose-down-volumes() {
  echo "⚠️  WARNING: This will DELETE all volumes!"
  echo "Volumes to be deleted:"
  docker compose config --volumes
  read -p "Are you sure? Type 'yes' to continue: " confirm
  if [ "$confirm" = "yes" ]; then
    docker compose down -v
  fi
}
```

### **3. Configuración de Entornos Debe Ser Explícita**
- Evitar hardcoded env_file paths
- Usar COMPOSE_PROJECT_NAME consistente entre entornos
- Documentar claramente diferencias entre dev/staging/prod

### **4. Testing en Staging Es Obligatorio**
- NUNCA deployar a producción sin testing en staging
- Staging debe replicar producción lo más cercano posible
- Incluir tests de disaster recovery en staging

### **5. Documentación Es Crítica**
- Procedimientos de backup/restore deben estar documentados
- Runbooks para incidentes comunes
- Diagramas de arquitectura actualizados

---

## 📋 CHECKLIST DE PREVENCIÓN

### **Antes de Cada Deployment:**
- [ ] Backup manual de MongoDB tomado
- [ ] Verificar que backup automático más reciente es < 6 horas
- [ ] Testing completo en staging/dev
- [ ] Verificar que docker-compose.override.yml existe en prod
- [ ] Verificar COMPOSE_PROJECT_NAME es consistente
- [ ] Plan de rollback documentado

### **Durante Deployment:**
- [ ] NO usar `docker compose down -v` sin backup reciente
- [ ] Verificar logs de MongoDB para errores de autenticación
- [ ] Verificar que contenedores usan imágenes correctas (production target)
- [ ] Verificar health checks de todos los servicios

### **Después de Deployment:**
- [ ] Verificar todos los servicios healthy
- [ ] Verificar datos de MongoDB intactos (sample queries)
- [ ] Verificar logs no tienen errores críticos
- [ ] Tomar backup post-deployment
- [ ] Documentar cualquier issue encontrado

---

## 🎯 MÉTRICAS DE ÉXITO

Para considerar este incidente **resuelto y prevenido**, necesitamos:

### **Métricas Técnicas:**
- ✅ Sistema de backups automatizados implementado y funcionando
- ✅ Al menos 7 días de backups exitosos verificados
- ✅ Procedimientos de disaster recovery documentados y testeados
- ✅ docker-compose.override.yml permanente en producción
- ✅ Alertas configuradas para fallos de backup

### **Métricas Operacionales:**
- ✅ Zero data loss en próximos 90 días
- ✅ Tiempo de recuperación de backup < 15 minutos (testeado)
- ✅ 100% de deployments siguen checklist de prevención

### **Métricas de Proceso:**
- ✅ Staging environment configurado y en uso
- ✅ Pre-deployment testing obligatorio implementado
- ✅ Runbooks actualizados y accesibles

---

## 🔗 REFERENCIAS Y DOCUMENTOS RELACIONADOS

- `docs/DEPLOYMENT.md` - Procedimientos de deployment
- `docs/DISASTER-RECOVERY.md` - Procedimientos de recuperación (a crear)
- `scripts/backup-mongodb.sh` - Script de backup (a crear)
- `scripts/deploy-with-tar.sh` - Script de deployment (ya existe)

---

## ✍️ FIRMAS Y APROBACIONES

**Preparado por:** Claude (AI Assistant)
**Revisado por:** Jaziel Flores (jf@saptiva.com)
**Fecha:** 9 de Octubre, 2025
**Próxima Revisión:** 16 de Octubre, 2025 (verificar implementación de medidas)

---

## 🔄 SEGUIMIENTO

| Acción | Responsable | Fecha Límite | Estado |
|--------|-------------|--------------|---------|
| Implementar backup automático MongoDB | DevOps | 10-Oct-2025 | ⏳ Pendiente |
| Configurar cron jobs | DevOps | 10-Oct-2025 | ⏳ Pendiente |
| Crear DISASTER-RECOVERY.md | DevOps | 10-Oct-2025 | ⏳ Pendiente |
| Testear procedimiento de restore | DevOps | 11-Oct-2025 | ⏳ Pendiente |
| Configurar staging environment | DevOps | 13-Oct-2025 | ⏳ Pendiente |
| Implementar alertas de backup | DevOps | 11-Oct-2025 | ⏳ Pendiente |
| Review de este documento | Team Lead | 16-Oct-2025 | ⏳ Pendiente |

---

**ESTE INCIDENTE NO DEBE REPETIRSE.**

**Prioridad máxima: Implementar sistema de backups en las próximas 24 horas.**
