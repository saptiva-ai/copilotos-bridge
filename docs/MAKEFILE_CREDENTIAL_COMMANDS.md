# 🔐 Makefile Credential Management Commands

## Overview

Se han integrado comandos de gestión de credenciales directamente en el Makefile para facilitar la rotación segura de contraseñas y el reset del ambiente de desarrollo.

---

## 🆕 Nuevos Comandos

### 1. `make generate-credentials`

Genera credenciales aleatorias seguras para usar en archivos `.env`.

**Uso:**
```bash
make generate-credentials
```

**Salida:**
```
🔐 Secure Credential Generator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MongoDB/Redis Password (32 characters):
gpo2lTwR3JRoZn3Bk8O2kpt25LoVDcl9

JWT Secret Key (64 characters):
nbOGCY9CEaS6XZoCvJ6WqecjsvswiSO6oXp0LZnd/AxIsAASXHPCxD/wcLxUBuiEBlRlDUFjSBCsv2hDmGLjZQ==
```

**Cuándo usar:**
- Configuración inicial de un nuevo ambiente
- Cuando necesites generar credenciales frescas
- Para crear credenciales de producción

---

### 2. `make rotate-mongo-password`

Rota la contraseña de MongoDB **SIN PERDER DATOS**.

**Uso:**
```bash
make rotate-mongo-password
```

**Proceso interactivo:**
1. Verifica que MongoDB esté corriendo
2. Muestra la contraseña actual en `envs/.env`
3. Solicita contraseña vieja (actual)
4. Solicita contraseña nueva
5. Ejecuta el script de rotación
6. Te indica cómo actualizar `.env`

**Cuándo usar:**
- Rotación programada cada 3 meses
- Cuando sospeches que credenciales fueron comprometidas
- Antes de promover de DEV a PROD

**⚠️ IMPORTANTE:**
- **No borra volúmenes** - tus datos quedan intactos
- Usa `db.changeUserPassword()` internamente
- Probar PRIMERO en DEV antes de PROD

---

### 3. `make rotate-redis-password`

Rota la contraseña de Redis **SIN PERDER DATOS**.

**Uso:**
```bash
make rotate-redis-password
```

**Proceso interactivo:**
1. Verifica que Redis esté corriendo
2. Muestra la contraseña actual en `envs/.env`
3. Solicita contraseña nueva
4. Ejecuta el script de rotación
5. Te indica cómo actualizar `.env`

**Cuándo usar:**
- Rotación programada cada 3 meses
- Cuando sospeches que credenciales fueron comprometidas
- Antes de promover de DEV a PROD

**⚠️ IMPORTANTE:**
- La rotación es **temporal en runtime**
- Debes actualizar `envs/.env` y reiniciar para persistir
- No borra el volumen de datos

---

### 4. `make reset`

Reset completo del ambiente: **BORRA TODO** y genera credenciales nuevas.

**Uso:**
```bash
make reset
```

**Proceso:**
1. Solicita confirmación (debes escribir "reset")
2. Detiene todos los contenedores
3. Borra volúmenes de MongoDB y Redis
4. Genera credenciales aleatorias seguras
5. Actualiza `envs/.env` automáticamente
6. Reinicia el ambiente de desarrollo

**Cuándo usar:**
- Ambiente de desarrollo corrupto
- Desincronización de credenciales que causa errores de autenticación
- Quieres empezar desde cero
- Testing de setup inicial

**⚠️ PELIGRO:**
- **BORRA TODA LA BASE DE DATOS**
- **NO USAR EN PRODUCCIÓN**
- Solo para desarrollo

---

## 📝 Ejemplos de Uso

### Ejemplo 1: Primera vez configurando el ambiente

```bash
# 1. Clonar el repo y crear archivo .env
cp envs/.env.local.example envs/.env

# 2. Generar credenciales seguras
make generate-credentials

# 3. Copiar las contraseñas generadas en envs/.env
nano envs/.env

# 4. Iniciar el ambiente
make dev

# 5. Crear usuario demo
make create-demo-user
```

---

### Ejemplo 2: Rotación programada en DEV (cada 3 meses)

```bash
# 1. Verificar que todo está corriendo
make health

# 2. Rotar contraseña de MongoDB
make rotate-mongo-password
# Ingresa contraseña vieja: secure_password_change_me
# Ingresa contraseña nueva: NewSecurePass2024!

# 3. Actualizar envs/.env
nano envs/.env
# MONGODB_PASSWORD=NewSecurePass2024!

# 4. Reiniciar servicios
make restart

# 5. Verificar que funciona
make health
make test-login

# 6. Repetir para Redis
make rotate-redis-password
# Ingresa contraseña nueva: NewRedisPass2024!

# 7. Actualizar envs/.env
nano envs/.env
# REDIS_PASSWORD=NewRedisPass2024!

# 8. Reiniciar servicios nuevamente
make restart

# 9. Verificar
make health
```

---

### Ejemplo 3: Error "Authentication failed" - Reset completo

```bash
# Síntoma: API no puede conectar a MongoDB/Redis
# Error: "Authentication failed" o "invalid username-password pair"

# Solución 1: Reset completo (desarrollo)
make reset
# Escribe: reset (para confirmar)

# El comando:
# - Borra volúmenes
# - Genera credenciales nuevas
# - Actualiza envs/.env automáticamente
# - Reinicia todo

# Después del reset:
make create-demo-user
make health
```

---

### Ejemplo 4: Preparar ambiente de producción

```bash
# 1. Generar credenciales de producción
make generate-credentials

# Salida:
# MongoDB/Redis Password: xK9mP2nQ5wR8tY4uI1oP7aS3dF6gH0jL
# JWT Secret: <long-64-char-string>

# 2. Crear archivo envs/.env.prod
nano envs/.env.prod

# 3. Copiar credenciales generadas
MONGODB_USER=copilotos_prod_user
MONGODB_PASSWORD=xK9mP2nQ5wR8tY4uI1oP7aS3dF6gH0jL
REDIS_PASSWORD=<otra-password-segura>
JWT_SECRET_KEY=<long-64-char-string>

# 4. NUNCA commitear envs/.env.prod
echo "envs/.env.prod" >> .gitignore

# 5. Almacenar en vault seguro (1Password, AWS Secrets Manager, etc.)
```

---

## 🔒 Mejores Prácticas

### Frecuencia de Rotación Recomendada

| Credencial          | Frecuencia | Criticidad |
|---------------------|------------|------------|
| JWT_SECRET_KEY      | 6 meses    | 🔴 Alta    |
| MONGODB_PASSWORD    | 3 meses    | 🔴 Alta    |
| REDIS_PASSWORD      | 3 meses    | 🟡 Media   |
| SAPTIVA_API_KEY     | Por política | 🔴 Alta  |

### Checklist de Rotación de Credenciales

- [ ] ✅ Hacer backup completo de MongoDB (`make backup-mongodb-prod`)
- [ ] ✅ Verificar que servicios están healthy (`make health`)
- [ ] ✅ Notificar al equipo (ventana de mantenimiento)
- [ ] ✅ Probar rotación en DEV primero
- [ ] ✅ Tener plan de rollback preparado
- [ ] ✅ Documentar quién hizo el cambio y cuándo
- [ ] ✅ Actualizar credenciales en vault seguro

### Separación DEV vs PROD

```bash
# Desarrollo
envs/.env                   # Credenciales simples, ignorado en git
MONGODB_PASSWORD=dev_password_123

# Producción
envs/.env.prod              # Credenciales fuertes, ignorado en git, solo en servidor
MONGODB_PASSWORD=xK9mP2nQ5wR8tY4uI1oP7aS3dF6gH0jL
```

---

## 🛠️ Troubleshooting

### Error: "MongoDB container not running"

**Solución:**
```bash
make dev
make rotate-mongo-password
```

---

### Error: "MONGODB_PASSWORD not found"

**Causa:** Falta la variable en `envs/.env`

**Solución:**
```bash
# Agregar manualmente
echo "MONGODB_PASSWORD=secure_password_change_me" >> envs/.env
make rotate-mongo-password
```

---

### Error: Script rotation failed

**Causa:** Contraseña vieja incorrecta

**Solución:**
```bash
# Verificar contraseña actual
grep MONGODB_PASSWORD envs/.env

# Intentar con la contraseña correcta
make rotate-mongo-password
```

---

### Reset no funciona

**Solución nuclear:**
```bash
# Limpieza manual completa
make stop-all
docker volume rm copilotos_mongodb_data copilotos_mongodb_config copilotos_redis_data
docker system prune -f

# Regenerar credenciales
make generate-credentials

# Actualizar envs/.env con las nuevas credenciales

# Reiniciar
make dev
make create-demo-user
```

---

## 📚 Documentación Relacionada

- [Gestión de Credenciales Completa](./CREDENTIAL_MANAGEMENT.md) - Guía detallada con procedimientos de emergencia
- [Disaster Recovery](./DISASTER-RECOVERY.md) - Procedimientos de respaldo y recuperación
- [Common Issues](./COMMON_ISSUES.md) - Problemas comunes y soluciones

---

## 🔗 Scripts Subyacentes

Los comandos del Makefile ejecutan estos scripts internamente:

- `scripts/rotate-mongo-credentials.sh` - Rotación de MongoDB
- `scripts/rotate-redis-credentials.sh` - Rotación de Redis
- `scripts/interactive-env-setup.sh` - Setup interactivo inicial

---

**Última actualización:** 2025-10-10
**Autor:** Claude Code / Equipo Saptiva
