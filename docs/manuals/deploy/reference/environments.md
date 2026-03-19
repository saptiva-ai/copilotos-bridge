# 🔧 Docker Compose: Configuración de env_file

**Fecha:** 2025-10-10
**Estado:** ✅ Configuración Correcta y Validada

---

## ⚠️ Por Qué es Crítico

### Problema sin `env_file`

Sin la directiva `env_file` en docker-compose.yml, los servicios:

1. **No leen el archivo .env automáticamente** al iniciarse
2. **Usan valores por defecto** definidos en el docker-compose.yml
3. **Ignoran cambios** en el archivo .env
4. **Causan desincronización** entre credenciales esperadas vs reales

**Consecuencia Real**: Después de rotar credenciales en `.env`, los contenedores seguían usando las contraseñas antiguas, resultando en errores de autenticación que parecían requerir borrar volúmenes (y perder datos).

---

## ✅ Configuración Actual

### `/home/jazielflo/Proyects/backup/copilotos-bridge/infra/docker-compose.yml`

```yaml
mongodb:
  image: mongo:7.0
  container_name: ${COMPOSE_PROJECT_NAME:-copilotos}-mongodb
  restart: unless-stopped
  env_file:                    # ← CRÍTICO
    - ../envs/.env
  environment:
    MONGO_INITDB_ROOT_USERNAME: ${MONGODB_USER:-copilotos_user}
    MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_PASSWORD:-secure_password_change_me}
    MONGO_INITDB_DATABASE: ${MONGODB_DATABASE:-copilotos}

redis:
  image: redis:7-alpine
  container_name: ${COMPOSE_PROJECT_NAME:-copilotos}-redis
  restart: unless-stopped
  env_file:                    # ← CRÍTICO
    - ../envs/.env
  command: >
    redis-server
    --requirepass ${REDIS_PASSWORD:-redis_password_change_me}

api:
  build:
    context: ../api
    dockerfile: Dockerfile.dev
  container_name: ${COMPOSE_PROJECT_NAME:-copilotos}-api
  restart: unless-stopped
  env_file:                    # ← CRÍTICO
    - ../envs/.env
  environment:
    MONGODB_USER: ${MONGODB_USER:-copilotos_user}
    MONGODB_PASSWORD: ${MONGODB_PASSWORD:-secure_password_change_me}
    REDIS_PASSWORD: ${REDIS_PASSWORD:-redis_password_change_me}
```

---

## 🔍 Cómo Funciona

### Orden de Prioridad de Variables de Entorno

Docker Compose aplica variables de entorno en este orden (de mayor a menor prioridad):

1. **Comando `docker compose -e VAR=value`** (línea de comandos)
2. **Variables de shell** del sistema operativo actual
3. **Sección `environment:`** en docker-compose.yml
4. **Archivo especificado en `env_file:`** (nuestro caso: `../envs/.env`)
5. **Valores por defecto** en la sintaxis `${VAR:-default}`

### Ejemplo Práctico

**Archivo envs/.env:**
```env
MONGODB_PASSWORD=g1pcNMZPQDnZEfsVtiLphQtV6A991gZq
```

**Sin env_file** (❌ INCORRECTO):
```yaml
mongodb:
  # No tiene env_file
  environment:
    MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_PASSWORD:-secure_password_change_me}
```

**Resultado**: Usa `secure_password_change_me` porque no encuentra `MONGODB_PASSWORD` en el entorno.

**Con env_file** (✅ CORRECTO):
```yaml
mongodb:
  env_file:
    - ../envs/.env
  environment:
    MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_PASSWORD:-secure_password_change_me}
```

**Resultado**: Usa `g1pcNMZPQDnZEfsVtiLphQtV6A991gZq` del archivo .env.

---

## 🧪 Validación

### Comando de Verificación

Para verificar que un servicio tiene `env_file` configurado:

```bash
# Verificar MongoDB
grep -A 5 "mongodb:" infra/docker-compose.yml | grep env_file

# Verificar Redis
grep -A 5 "redis:" infra/docker-compose.yml | grep env_file

# Verificar API
grep -A 5 "api:" infra/docker-compose.yml | grep env_file
```

**Salida esperada**: Debe aparecer `- ../envs/.env` para cada servicio.

### Verificación en Tiempo de Ejecución

Verificar qué variables de entorno tiene un contenedor:

```bash
# Ver todas las variables de MongoDB
docker inspect copilotos-mongodb --format='{{range .Config.Env}}{{println .}}{{end}}'

# Ver solo las variables de MONGO
docker inspect copilotos-mongodb --format='{{range .Config.Env}}{{println .}}{{end}}' | grep MONGO

# Verificar la contraseña específica (cuidado: expone la contraseña)
docker inspect copilotos-mongodb --format='{{range .Config.Env}}{{println .}}{{end}}' | grep MONGO_INITDB_ROOT_PASSWORD
```

**Lo que DEBE aparecer**: La contraseña del archivo `.env`, NO el valor por defecto.

---

## 🚨 Problemas Comunes

### Problema 1: Olvidar env_file en un servicio

**Síntoma**: Después de rotar credenciales, un servicio no puede conectar.

**Diagnóstico**:
```bash
# Comparar contraseña en .env vs contenedor
echo "Contraseña en .env:"
grep MONGODB_PASSWORD envs/.env

echo "Contraseña en contenedor:"
docker inspect copilotos-mongodb --format='{{range .Config.Env}}{{println .}}{{end}}' | grep MONGO_INITDB_ROOT_PASSWORD
```

**Solución**: Agregar `env_file` y recrear el contenedor:
```bash
# Agregar a docker-compose.yml:
mongodb:
  env_file:
    - ../envs/.env

# Recrear contenedor
docker compose down mongodb
docker compose up -d mongodb
```

### Problema 2: Ruta incorrecta en env_file

**Síntoma**: `ERROR: Couldn't find env file`

**Causas**:
```yaml
# ❌ INCORRECTO: Ruta relativa desde donde ejecutas docker compose
env_file:
  - .env                    # Solo funciona si ejecutas desde /infra

# ✅ CORRECTO: Ruta relativa desde donde está docker-compose.yml
env_file:
  - ../envs/.env            # Funciona desde cualquier lugar
```

**Solución**: Usar rutas relativas al archivo docker-compose.yml.

### Problema 3: Contenedor ya existe con variables viejas

**Síntoma**: Agregas `env_file` pero el contenedor sigue usando valores antiguos.

**Causa**: Las variables de entorno se establecen al CREAR el contenedor, no al iniciarlo.

**Solución**: Recrear (no solo reiniciar):
```bash
# ❌ INCORRECTO
docker compose restart mongodb

# ✅ CORRECTO
docker compose down mongodb
docker compose up -d mongodb
```

---

## 📋 Checklist de Configuración

Al agregar un nuevo servicio a docker-compose.yml:

- [ ] Agregar directiva `env_file: - ../envs/.env`
- [ ] Definir variables en sección `environment:` con valores por defecto
- [ ] Documentar las variables requeridas en `envs/.env`
- [ ] Probar rotación de credenciales sin pérdida de datos
- [ ] Verificar que `restart` no funciona, solo `down`+`up`

---

## 🔗 Referencias Relacionadas

- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/)
- [Gestión de Credenciales](credentials.md)

---

## 📊 Estado de Servicios

| Servicio | env_file | Variables Críticas | Estado |
|----------|----------|-------------------|--------|
| mongodb | ✅ | MONGODB_USER, MONGODB_PASSWORD | ✅ Configurado |
| redis | ✅ | REDIS_PASSWORD | ✅ Configurado |
| api | ✅ | MONGODB_PASSWORD, REDIS_PASSWORD | ✅ Configurado |
| web | ✅ | NEXT_PUBLIC_API_URL | ✅ Configurado |

---

## 🎯 Conclusión

La configuración de `env_file` en docker-compose.yml es **CRÍTICA** para:

1. ✅ Sincronizar credenciales entre .env y contenedores
2. ✅ Permitir rotación segura sin pérdida de datos
3. ✅ Evitar errores de autenticación difíciles de diagnosticar
4. ✅ Facilitar gestión de configuración centralizada

**Regla de Oro**: Todo servicio que use credenciales del archivo `.env` DEBE tener la directiva `env_file`.

---

**Última actualización:** 2025-10-10
**Verificado por:** Claude Code
**Estado:** ✅ Producción Ready
