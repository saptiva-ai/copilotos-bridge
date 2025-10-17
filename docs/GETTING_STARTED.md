# 🚀 Guía de Inicio Rápido - Copilotos Bridge

Esta guía te ayudará a levantar el stack completo de desarrollo en tu máquina local.

---

## 📋 Prerrequisitos

Antes de comenzar, asegúrate de tener instalado:

- **Docker Desktop** (v20.10 o superior)
  - [Instalar en Mac](https://docs.docker.com/desktop/install/mac-install/)
  - [Instalar en Windows](https://docs.docker.com/desktop/install/windows-install/)
  - [Instalar en Linux](https://docs.docker.com/desktop/install/linux-install/)
- **Git** (v2.30 o superior)
- **Make** (usualmente pre-instalado en Mac/Linux, en Windows usar WSL2)
- **Cuenta en Saptiva** (para obtener API key)
  - Regístrate en: https://lab.saptiva.com/lab/api-keys

### Verificar Instalación

```bash
# Verificar Docker
docker --version
docker compose version

# Verificar Git
git --version

# Verificar Make
make --version
```

---

## 🎯 Inicio Rápido (5 minutos)

### Opción 1: Setup Interactivo (Recomendado) ⭐

Este método te guiará paso a paso con prompts interactivos:

```bash
# 1. Clonar el repositorio
git clone https://github.com/saptiva-ai/copilotos-bridge.git
cd copilotos-bridge

# 2. Setup interactivo (te pedirá la API key y configurará todo)
make setup

# 3. Levantar el stack
make dev

# 4. Crear usuario demo
make create-demo-user
```

**¡Listo!** Accede a:
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

### Opción 2: Setup Manual

Si prefieres configurar manualmente:

```bash
# 1. Clonar el repositorio
git clone <repository-url>
cd copilotos-bridge

# 2. Crear archivo de configuración
cp .env.example envs/.env

# 3. Editar envs/.env y configurar:
#    - SAPTIVA_API_KEY=tu-api-key-aqui  (⚠️ REQUERIDO)
#    - Opcional: cambiar contraseñas de MongoDB y Redis
nano envs/.env  # o usa tu editor favorito

# 4. Levantar el stack
make dev

# 5. Crear usuario demo
make create-demo-user
```

---

## 📝 Pasos Detallados

### Paso 1: Obtener API Key de Saptiva

1. Ve a: https://saptiva.com/dashboard/api-keys
2. Crea una cuenta o inicia sesión
3. Genera una nueva API key
4. Copia la key (formato: `va-ai-xxxxx...`)

⚠️ **Importante**: Guarda esta key de forma segura, no la compartas ni la subas a Git.

### Paso 2: Configuración del Entorno

El setup interactivo (`make setup`) te preguntará:

```
🔑 SAPTIVA API Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SAPTIVA_API_KEY (required):
  Get your API key from: https://saptiva.com/dashboard/api-keys
  Format: va-ai-xxxxx...

> Enter value: [pega tu API key aquí]

✓ SAPTIVA API key configured

🔐 Security Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Auto-generating secure secrets...
✓ JWT_SECRET_KEY generated (64 chars)
✓ SECRET_KEY generated (64 chars)
✓ MONGODB_PASSWORD generated (24 chars)
✓ REDIS_PASSWORD generated (24 chars)
```

El script generará automáticamente contraseñas seguras para MongoDB y Redis.

### Paso 3: Levantar el Stack

```bash
make dev
```

Este comando:
1. ✅ Verifica que exista el archivo `envs/.env`
2. ✅ Levanta los contenedores en modo desarrollo:
   - MongoDB (base de datos)
   - Redis (caché)
   - API (backend FastAPI)
   - Web (frontend Next.js 14)
3. ✅ Espera 10 segundos para que los servicios arranquen
4. ✅ Verifica la salud de todos los servicios

**Salida esperada:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Services started
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Frontend: http://localhost:3000
   API:      http://localhost:8001
   Docs:     http://localhost:8001/docs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Health Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   API Health:        ✓ Healthy
  Frontend:          ✓ Healthy
   MongoDB:           ✓ Connected
   Redis:             ✓ Connected
```

### Paso 4: Crear Usuario Demo

```bash
make create-demo-user
```

Este comando crea un usuario de prueba con credenciales:
- **Usuario**: `demo`
- **Email**: `demo@example.com`
- **Contraseña**: `Demo1234`

### Paso 5: Acceder a la Aplicación

Abre tu navegador en:

1. **Frontend**: http://localhost:3000
2. Inicia sesión con:
   - Usuario: `demo`
   - Contraseña: `Demo1234`

---

## 🛠️ Comandos Útiles

### Desarrollo Diario

```bash
# Ver logs de todos los servicios
make logs

# Ver logs solo del API
make logs-api

# Ver logs solo del frontend
make logs-web

# Verificar salud de servicios
make health

# Ver estado de contenedores
make status

# Reiniciar todos los servicios
make restart

# Detener todos los servicios
make stop
```

### Problemas Comunes

```bash
# ❌ Los cambios de código no se reflejan?
make rebuild-api    # Reconstruir API
make rebuild-web    # Reconstruir Web
make rebuild-all    # Reconstruir todo

# ❌ Errores de caché?
make clean-next     # Limpiar caché de Next.js
make fresh          # Inicio fresco (limpia y reconstruye)

# ❌ Errores de autenticación?
make delete-demo-user   # Eliminar usuario demo
make clear-redis-local  # Limpiar caché de Redis
make create-demo-user   # Recrear usuario demo

# 🔍 Diagnóstico completo
make diag           # Diagnóstico rápido
make debug-full     # Diagnóstico completo
```

### Base de Datos

```bash
# Acceder a MongoDB shell
make shell-db

# Ver estadísticas de la base de datos
make db-stats

# Ver colecciones y conteos
make db-collections

# Hacer backup de la base de datos
make db-backup

# Restaurar desde backup
make db-restore
```

### Testing

```bash
# Ejecutar todos los tests
make test-all

# Tests del API
make test-api

# Tests del frontend
make test-web

# Tests E2E
make test-e2e
```

### Seguridad

```bash
# Instalar git hooks de seguridad
make install-hooks

# Ejecutar auditoría de seguridad
make security-audit

# Verificar código
make lint
make lint-fix
```

---

## 📁 Estructura del Proyecto

```
copilotos-bridge/
├── apps/
│   ├── api/                    # Backend FastAPI
│   │   ├── src/
│   │   │   ├── routers/       # Endpoints de la API
│   │   │   ├── models/        # Modelos de MongoDB
│   │   │   ├── services/      # Lógica de negocio
│   │   │   └── core/          # Configuración
│   │   └── requirements.txt
│   └── web/                    # Frontend Next.js 14
│       ├── src/
│       │   ├── app/           # App Router
│       │   ├── components/    # Componentes React
│       │   └── lib/           # Utilidades
│       └── package.json
├── packages/
│   └── shared/                 # Código compartido
├── infra/
│   ├── docker-compose.yml      # Compose base
│   ├── docker-compose.dev.yml  # Compose desarrollo
│   └── docker-compose.prod.yml # Compose producción
├── envs/
│   ├── .env                    # Desarrollo (crear desde .env.example)
│   ├── .env.prod               # Producción (crear con make setup-interactive-prod)
│   └── .env.local              # Overrides locales
├── scripts/
│   ├── interactive-env-setup.sh   # Setup interactivo
│   ├── deploy-with-tar.sh         # Deploy a producción
│   └── clear-server-cache.sh      # Limpiar caché
├── .env.example                # Plantilla de configuración
├── Makefile                    # Comandos principales
└── GETTING_STARTED.md          # Esta guía
```

---

## 🔧 Configuración Avanzada

### Variables de Entorno Importantes

#### Desarrollo Local (envs/.env)

```bash
# API Key (REQUERIDO)
SAPTIVA_API_KEY=va-ai-xxxxx...

# URLs de desarrollo (por defecto)
NODE_ENV=development
API_BASE_URL=http://localhost:8001
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8001/api

# Base de datos local (Docker)
MONGODB_HOST=mongodb
MONGODB_PORT=27017
MONGODB_USER=copilotos_user
MONGODB_PASSWORD=secure_password_change_me  # Cambiar por uno fuerte
MONGODB_DB=copilotos

# Redis local (Docker)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_password_change_me  # Cambiar por uno fuerte

# Modelos disponibles
CHAT_ALLOWED_MODELS=["Saptiva Turbo","Saptiva Cortex","Saptiva Ops","Saptiva Legacy","Saptiva Coder"]
CHAT_DEFAULT_MODEL=Saptiva Turbo

# Feature flags (habilitar/deshabilitar funcionalidades)
FEATURE_WEB_SEARCH_ENABLED=true
FEATURE_DEEP_RESEARCH_ENABLED=true
NEXT_PUBLIC_FEATURE_WEB_SEARCH=true
NEXT_PUBLIC_FEATURE_DEEP_RESEARCH=true
```

### Usar MongoDB Atlas (Nube)

Si prefieres usar MongoDB Atlas en lugar de local:

```bash
# En envs/.env, comenta las líneas de MongoDB local y usa:
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/copilotos?retryWrites=true&w=majority
```

### Configurar Aletheia (Opcional)

Aletheia proporciona capacidades de investigación profunda:

```bash
# En envs/.env
ALETHEIA_BASE_URL=https://aletheia.saptiva.ai
ALETHEIA_API_KEY=tu-aletheia-api-key
ALETHEIA_TIMEOUT_SECONDS=120
```

---

## 🐛 Solución de Problemas

### ❌ Error: "API key not configured"

```bash
# Solución:
# 1. Verificar que existe envs/.env
ls -la envs/.env

# 2. Verificar que contiene SAPTIVA_API_KEY
grep SAPTIVA_API_KEY envs/.env

# 3. Si no existe, ejecutar setup
make setup
```

### ❌ Error: "Cannot connect to MongoDB"

```bash
# Verificar que MongoDB esté corriendo
docker ps | grep mongodb

# Reiniciar contenedor de MongoDB
docker restart copilotos-mongodb

# Ver logs de MongoDB
docker logs copilotos-mongodb
```

### ❌ Error: "Port 3000 already in use"

```bash
# Encontrar el proceso usando el puerto
lsof -i :3000  # Mac/Linux
netstat -ano | findstr :3000  # Windows

# Matar el proceso o cambiar el puerto en envs/.env
PORT=3001
```

### ❌ Frontend muestra código antiguo

```bash
# Limpiar caché de Next.js y reconstruir
make clean-next
make rebuild-web

# O hacer un fresh start
make fresh
```

### ❌ Errores de permisos con node_modules

```bash
# Dar permisos al usuario actual
sudo chown -R $(id -u):$(id -g) .

# O reconstruir con --no-cache
make rebuild-all
```

### ❌ Error: "Docker daemon not running"

```bash
# Mac: Abrir Docker Desktop
open -a Docker

# Linux: Iniciar Docker
sudo systemctl start docker

# Windows: Iniciar Docker Desktop desde el menú de inicio
```

---

## 📚 Próximos Pasos

### 1. Explorar la API

Visita http://localhost:8001/docs para ver la documentación interactiva de la API (Swagger UI).

Endpoints principales:
- `POST /api/auth/login` - Autenticación
- `GET /api/auth/me` - Obtener usuario actual
- `POST /api/chat` - Enviar mensaje al chat
- `GET /api/sessions` - Listar sesiones de chat
- `GET /api/models` - Modelos disponibles

### 2. Desarrollar

```bash
# El hot-reload está habilitado automáticamente
# Edita archivos en apps/api/src/ o apps/web/src/
# Los cambios se reflejarán automáticamente

# Para backend (FastAPI):
# - Edita archivos en apps/api/src/
# - El servidor se reinicia automáticamente con uvicorn --reload

# Para frontend (Next.js):
# - Edita archivos en apps/web/src/
# - Next.js recarga automáticamente el navegador
```

### 3. Leer Documentación

- **README.md** - Visión general del proyecto
- **docs/DEPLOY_GUIDE.md** - Guía de despliegue a producción
- **docs/TROUBLESHOOTING.md** - Solución de problemas comunes
- **docs/SECURITY_AUDIT_REPORT.md** - Informe de auditoría de seguridad

### 4. Contribuir

```bash
# 1. Crear rama para tu feature
git checkout -b feature/mi-nueva-funcionalidad

# 2. Hacer cambios y commit
git add .
git commit -m "feat: agregar nueva funcionalidad"

# 3. Push y crear Pull Request
git push origin feature/mi-nueva-funcionalidad
```

---

## 🆘 Soporte

### Obtener Ayuda

```bash
# Ver todos los comandos disponibles
make help

# Ejecutar diagnóstico completo
make debug-full

# Ver guía de troubleshooting
cat docs/TROUBLESHOOTING.md
```

### Recursos

- **Documentación**: Ver carpeta `docs/`
- **Issues**: Reportar problemas en GitHub Issues
- **API Docs**: http://localhost:8001/docs (cuando el stack esté corriendo)

---

## ✅ Checklist de Verificación

Antes de comenzar a desarrollar, verifica:

- [ ] Docker Desktop está corriendo
- [ ] Archivo `envs/.env` existe y tiene `SAPTIVA_API_KEY` configurado
- [ ] `make dev` ejecutado exitosamente
- [ ] Todos los servicios están healthy (`make health` muestra ✓)
- [ ] Usuario demo creado (`make create-demo-user`)
- [ ] Puedes acceder a http://localhost:3000
- [ ] Puedes iniciar sesión con demo/Demo1234
- [ ] API Docs accesible en http://localhost:8001/docs

---

## 🎉 ¡Listo!

Ahora tienes el stack completo corriendo localmente. ¡Feliz desarrollo! 🚀

### Comandos más usados:

```bash
make dev               # Levantar el stack
make logs              # Ver logs
make restart           # Reiniciar servicios
make stop              # Detener todo
make health            # Verificar salud
make create-demo-user  # Crear usuario demo
make help              # Ver todos los comandos
```

---

**Última actualización**: 2025-01-09
