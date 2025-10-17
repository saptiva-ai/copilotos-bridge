# 🔐 Gestión de Credenciales - Guía Completa

**Objetivo:** Rotar credenciales SIN perder datos de producción.

---

## 📋 **Tabla de Contenidos**

1. [Estructura de Archivos por Ambiente](#estructura-de-archivos-por-ambiente)
2. [Rotación Segura de Credenciales](#rotación-segura-de-credenciales)
3. [Buenas Prácticas](#buenas-prácticas)
4. [Troubleshooting](#troubleshooting)

---

## 1️⃣ **Estructura de Archivos por Ambiente**

### **Separación de Configuraciones**

```
envs/
├── .env                    # DEV (ignorado en git)
├── .env.local              # DEV local (ignorado en git)
├── .env.local.example      # Plantilla para DEV
├── .env.prod               # PROD (ignorado en git, NUNCA commitear)
└── .env.prod.example       # Plantilla para PROD (sin credenciales reales)
```

### **Contenido de cada archivo:**

#### **envs/.env (Desarrollo)**
```bash
# MongoDB Development
MONGODB_USER=copilotos_dev_user
MONGODB_PASSWORD=dev_password_123
MONGODB_DATABASE=copilotos_dev

# Redis Development
REDIS_PASSWORD=dev_redis_pass

# JWT Development (NUNCA usar en PROD)
JWT_SECRET_KEY=dev-jwt-secret-change-in-production
```

#### **envs/.env.prod (Producción)**
```bash
# MongoDB Production
MONGODB_USER=copilotos_prod_user
MONGODB_PASSWORD=SecureProdPass2024!Complex
MONGODB_DATABASE=copilotos

# Redis Production
REDIS_PASSWORD=ProdRedis2024!Secure

# JWT Production (generado con openssl rand -base64 64)
JWT_SECRET_KEY=<64-char-random-string>
```

### **Reglas de Oro:**

✅ **SÍ hacer:**
- Usar credenciales diferentes en DEV vs PROD
- Mantener `.env.prod` en servidor PROD únicamente
- Actualizar `.env.*.example` con estructura (sin valores reales)

❌ **NO hacer:**
- Commitear archivos `.env` con credenciales reales
- Usar credenciales de DEV en PROD
- Compartir credenciales de PROD por email/Slack

---

## 2️⃣ **Rotación Segura de Credenciales**

### **MongoDB - Rotación SIN perder datos**

#### **Paso 1: Verificar credenciales actuales**
```bash
grep MONGODB_PASSWORD envs/.env
# Salida: MONGODB_PASSWORD=old_password_here
```

#### **Paso 2: Ejecutar script de rotación**
```bash
./scripts/rotate-mongo-credentials.sh \
  "old_password_here" \
  "NewSecurePass2024!"
```

**Lo que hace el script:**
1. Conecta a MongoDB con credenciales viejas
2. Ejecuta `db.changeUserPassword()` con nueva password
3. **NO borra volúmenes** → datos intactos

#### **Paso 3: Actualizar .env**
```bash
# Editar envs/.env
MONGODB_PASSWORD=NewSecurePass2024!
```

#### **Paso 4: Reiniciar servicios**
```bash
# Reinicio suave (sin borrar volúmenes)
docker compose restart api
```

---

### **Redis - Rotación Temporal**

Redis es más simple pero la rotación es temporal en runtime:

```bash
./scripts/rotate-redis-credentials.sh "NewRedisPass2024!"
```

Luego actualizar `envs/.env` y reiniciar:
```bash
docker compose restart redis api
```

---

## 3️⃣ **Buenas Prácticas**

### **Generación de Credenciales Seguras**

#### **MongoDB/Redis Passwords (32 caracteres):**
```bash
openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
# Ejemplo: xK9mP2nQ5wR8tY4uI1oP7aS3dF6gH0jL
```

#### **JWT Secret (64 caracteres):**
```bash
openssl rand -base64 64 | tr -d '\n'
# Ejemplo: longísima string de 64+ caracteres
```

### **Rotación Programada**

| Credencial | Frecuencia Recomendada | Criticidad |
|------------|------------------------|------------|
| JWT_SECRET_KEY | Cada 6 meses | 🔴 Alta |
| MONGODB_PASSWORD | Cada 3 meses | 🔴 Alta |
| REDIS_PASSWORD | Cada 3 meses | 🟡 Media |
| SAPTIVA_API_KEY | Según política de Saptiva | 🔴 Alta |

### **Checklist Pre-Rotación**

- [ ] ✅ Backup completo de MongoDB (`make backup-mongodb-prod`)
- [ ] ✅ Verificar que servicios están healthy
- [ ] ✅ Notificar al equipo de ventana de mantenimiento
- [ ] ✅ Probar rotación en DEV primero
- [ ] ✅ Preparar rollback plan

---

## 4️⃣ **Troubleshooting**

### **Problema: "Authentication failed" después de cambiar credenciales**

**Causa:** MongoDB/Redis aún usan credenciales viejas en el volumen.

**Solución SIN perder datos:**

#### **Opción A: Usar script de rotación (recomendado)**
```bash
./scripts/rotate-mongo-credentials.sh OLD_PASS NEW_PASS
```

#### **Opción B: Revertir temporalmente**
1. Volver a credenciales viejas en `envs/.env`
2. Reiniciar servicios
3. Planear rotación con script

#### **Opción C: Manual (solo si scripts fallan)**
```bash
# Conectar con password viejo
docker exec -it copilotos-mongodb mongosh admin \
  -u copilotos_prod_user \
  -p OLD_PASSWORD

# Dentro de mongosh:
> db.changeUserPassword('copilotos_prod_user', 'NEW_PASSWORD')
> exit

# Actualizar .env y reiniciar
```

---

### **Problema: Olvidé la contraseña de PROD**

**Recuperación de emergencia (SOLO PROD, con mucho cuidado):**

1. **Detener API** (para prevenir conexiones fallidas):
   ```bash
   docker compose stop api
   ```

2. **Reiniciar MongoDB SIN auth**:
   ```bash
   docker exec -it copilotos-mongodb mongod --noauth
   ```

3. **Conectar y resetear password**:
   ```bash
   docker exec -it copilotos-mongodb mongosh
   > use admin
   > db.changeUserPassword('copilotos_prod_user', 'NEW_TEMP_PASSWORD')
   ```

4. **Reiniciar MongoDB normalmente**:
   ```bash
   docker compose restart mongodb
   ```

5. **Actualizar .env y arrancar API**:
   ```bash
   docker compose start api
   ```

---

### **Problema: Necesito rotar en ambiente con múltiples réplicas**

Para ambientes de alta disponibilidad:

1. Rotar en replica primaria primero
2. Esperar sincronización con secundarias
3. Actualizar configuración de todas las réplicas
4. Reiniciar una por una (rolling restart)

---

## 🚨 **Emergencia: Perdí el volumen de PROD**

### **Plan de Disaster Recovery:**

#### **1. Restaurar desde backup más reciente**
```bash
# Listar backups disponibles
ls -lh /opt/backups/copilotos-production/

# Restaurar
./scripts/restore-mongodb.sh /path/to/backup.archive
```

#### **2. Verificar integridad**
```bash
make db-stats
make db-collections
```

#### **3. Re-crear usuarios si es necesario**
```bash
docker exec -it copilotos-mongodb mongosh admin
> db.createUser({
    user: "copilotos_prod_user",
    pwd: "NEW_PASSWORD",
    roles: [{ role: "readWrite", db: "copilotos" }]
  })
```

---

## 📊 **Monitoreo de Credenciales**

### **Script de Auditoría**

Crea un script para verificar que las credenciales funcionan:

```bash
#!/bin/bash
# scripts/audit-credentials.sh

echo "🔍 Auditando credenciales..."

# Test MongoDB
docker exec copilotos-api python3 -c "
from motor.motor_asyncio import AsyncIOMotorClient
import os, asyncio
async def test():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URL'))
    try:
        await client.admin.command('ping')
        print('✅ MongoDB: OK')
    except Exception as e:
        print(f'❌ MongoDB: {e}')
asyncio.run(test())
" || echo "❌ MongoDB: FAIL"

# Test Redis
docker exec copilotos-api python3 -c "
import redis, os
url = os.getenv('REDIS_URL')
r = redis.from_url(url)
try:
    r.ping()
    print('✅ Redis: OK')
except Exception as e:
    print(f'❌ Redis: {e}')
" || echo "❌ Redis: FAIL"
```

---

## ✅ **Checklist de Migración DEV → PROD**

Cuando migres de desarrollo a producción:

- [ ] Generar nuevas credenciales seguras (no reutilizar DEV)
- [ ] Crear `envs/.env.prod` con credenciales PROD
- [ ] Verificar que `.gitignore` incluye `envs/.env.prod`
- [ ] Configurar backups automáticos diarios
- [ ] Documentar quién tiene acceso a credenciales
- [ ] Configurar alertas de fallo de autenticación
- [ ] Probar rotación de credenciales en staging primero

---

## 📚 **Referencias**

- [MongoDB User Management](https://www.mongodb.com/docs/manual/tutorial/manage-users-and-roles/)
- [Redis Security](https://redis.io/docs/management/security/)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/) (para ambientes avanzados)
- [Disaster Recovery Guide](./DISASTER-RECOVERY.md)

---

**Última actualización:** 2025-10-10
**Autor:** Claude Code / Equipo Saptiva
