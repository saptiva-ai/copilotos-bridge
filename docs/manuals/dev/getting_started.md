# Guia de Inicio Rapido - Saptiva OctaviOS Chat

Esta guia te ayudara a levantar el stack completo de desarrollo en tu maquina local.

---

## Prerrequisitos

Antes de comenzar, asegurate de tener instalado:

- **Docker Desktop** (v20.10 o superior)
  - [Instalar en Mac](https://docs.docker.com/desktop/install/mac-install/)
  - [Instalar en Windows](https://docs.docker.com/desktop/install/windows-install/)
  - [Instalar en Linux](https://docs.docker.com/desktop/install/linux-install/)
- **Git** (v2.30 o superior)
- **Make** (usualmente pre-instalado en Mac/Linux, en Windows usar WSL2)
- **Cuenta en Saptiva** (para obtener API key)
  - Registrate en: https://lab.saptiva.com/lab/api-keys

### Verificar Instalacion

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

## Inicio Rapido (5 minutos)

### Opcion 1: Setup Interactivo (Recomendado)

Este metodo te guiara paso a paso con prompts interactivos:

```bash
# 1. Clonar el repositorio
git clone git@github.com:saptiva-ai/octavios-chat-bajaware_invex.git
cd octavios-chat-bajaware_invex

# 2. Setup interactivo (te pedira la API key y configurara todo)
make setup

# 3. Levantar el stack
make dev

# 4. Crear usuario demo
make create-demo-user
```

**Listo!** Accede a:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Opcion 2: Setup Manual

Si prefieres configurar manualmente:

```bash
# 1. Clonar el repositorio
git clone git@github.com:saptiva-ai/octavios-chat-bajaware_invex.git
cd octavios-chat-bajaware_invex

# 2. Crear archivo de configuracion
cp .env.example envs/.env

# 3. Editar envs/.env y configurar:
#    - SAPTIVA_API_KEY   (REQUERIDO - obtener de lab.saptiva.com)
#    - Opcional: cambiar contraseñas de MongoDB y Redis
nano envs/.env  # o usa tu editor favorito

# 4. Levantar el stack
make dev

# 5. Crear usuario demo
make create-demo-user
```

---

## Pasos Detallados

### Paso 1: Obtener API Key de Saptiva

1. Ve a: https://lab.saptiva.com/lab/api-keys
2. Crea una cuenta o inicia sesion
3. Genera una nueva API key
4. Copia la key

**Importante**: Guarda esta key de forma segura, no la compartas ni la subas a Git.

### Paso 2: Configuracion del Entorno

El setup interactivo (`make setup`) te preguntara:

```
SAPTIVA API Configuration

SAPTIVA_API_KEY (required):
  Get your API key from: https://lab.saptiva.com/lab/api-keys

> Enter value: [pega tu API key aqui]

Security Configuration

Auto-generating secure secrets...
  JWT_SECRET_KEY generated (64 chars)
  SECRET_KEY generated (64 chars)
  MONGODB_PASSWORD generated (24 chars)
  REDIS_PASSWORD generated (24 chars)
```

El script generara automaticamente contraseñas seguras para MongoDB y Redis.

### Paso 3: Levantar el Stack

```bash
make dev
```

Este comando:
1. Verifica que exista el archivo `envs/.env`
2. Levanta los contenedores en modo desarrollo:
   - MongoDB (base de datos)
   - Redis (cache)
   - MinIO (almacenamiento de archivos)
   - Backend (FastAPI - puerto 8000)
   - Web (Next.js - puerto 3000)
   - File Manager (gestion de archivos - puerto 8001)
   - Bank Advisor (plugin bancario - puerto 8002)
3. Ejecuta health checks automaticos

**Salida esperada:**

```
Development environment started
  Frontend:     http://localhost:3000
  Backend:      http://localhost:8000
  File Manager: http://localhost:8001
  Bank Advisor: http://localhost:8002

Health Check
  Backend:       Healthy
  File Manager:  Healthy
  Frontend:      Healthy
  MongoDB:       Connected
  Redis:         Connected
```

### Paso 4: Crear Usuario Demo

```bash
make create-demo-user
```

Este comando crea un usuario de prueba con credenciales:
- **Usuario**: `demo`
- **Email**: `demo@example.com`
- **Contraseña**: `Demo1234`

### Paso 5: Acceder a la Aplicacion

Abre tu navegador en:

1. **Frontend**: http://localhost:3000
2. Inicia sesion con:
   - Usuario: `demo`
   - Contraseña: `Demo1234`

---

## Comandos Utiles

### Desarrollo Diario

```bash
# Ver logs de todos los servicios
make logs

# Ver logs de un servicio especifico
make logs S=backend
make logs S=web

# Seguir logs en tiempo real
make logs-follow S=backend

# Verificar salud de servicios
make health

# Ver estado de contenedores
make status

# Reiniciar todos los servicios
make restart

# Reiniciar un servicio especifico
make restart S=backend

# Detener todos los servicios
make stop
```

### Reconstruir Servicios

```bash
# Reconstruir un servicio individual
make rebuild.backend
make rebuild.web
make rebuild.bank-advisor
make rebuild.file-manager

# Reconstruir todo el entorno de desarrollo
make dev-rebuild

# Reset completo (detener, limpiar, reconstruir)
make dev-reset
```

### Limpieza

```bash
# Limpiar contenedores y cache de Next.js
make clean

# Limpiar cache de Python y Next.js
make clean-cache

# Limpieza profunda (elimina volumenes de datos)
make clean-deep
```

### Base de Datos

```bash
# Acceder a MongoDB shell
make db.shell

# Ver estadisticas de la base de datos
make db.stats

# Hacer backup de la base de datos
make db.backup

# Restaurar desde backup
make db.restore
```

### Testing

```bash
# Ejecutar todos los tests
make test

# Tests del backend (API)
make test T=api

# Tests del frontend (web)
make test T=web

# Tests E2E
make test T=e2e

# Tests MCP
make test T=mcp

# Test local con .venv (sin Docker)
make test-local TEST_FILE="tests/unit/test_x.py"
make test-local TEST_FILE="tests/unit/test_x.py" TEST_ARGS="-k my_case"
```

### Pre-Deploy

```bash
# Verificacion completa antes de deploy
make pre-deploy

# Solo regression tests
make pre-deploy.quick

# Lint solamente
make pre-deploy.lint
```

### Seguridad

```bash
# Instalar git hooks de seguridad
make install-hooks

# Linting
make pre-deploy.lint
```

---

## Estructura del Proyecto

```
octavios-chat-bajaware_invex/
├── apps/
│   ├── backend/               # Backend FastAPI (puerto 8000)
│   │   ├── src/
│   │   │   ├── routers/       # Endpoints de la API
│   │   │   ├── models/        # Modelos de MongoDB
│   │   │   ├── services/      # Logica de negocio
│   │   │   ├── schemas/       # Schemas Pydantic
│   │   │   └── core/          # Configuracion
│   │   └── tests/
│   ├── web/                   # Frontend Next.js (puerto 3000)
│   │   ├── src/
│   │   │   ├── app/           # App Router
│   │   │   ├── components/    # Componentes React
│   │   │   └── lib/           # Utilidades
│   │   └── package.json
│   └── dashboard/             # Dashboard Plotly Dash (puerto 8050)
├── plugins/
│   ├── bank-advisor-private/  # Plugin bancario (puerto 8002)
│   └── file-manager/         # Gestion de archivos (puerto 8001)
├── infra/
│   ├── docker-compose.yml     # Compose base
│   ├── docker-compose.dev.yml # Overlay de desarrollo
│   └── docker-compose.production.yml
├── envs/
│   ├── .env                   # Desarrollo (crear con make setup)
│   └── .env.prod              # Produccion
├── scripts/
│   ├── setup/                 # Scripts de configuracion
│   ├── testing/               # Scripts de testing
│   ├── database/              # Operaciones de BD
│   ├── deploy/                # Scripts de deploy
│   └── maintenance/           # Mantenimiento
├── docs/                      # Documentacion
├── Makefile                   # Comandos principales
└── .env.example               # Plantilla de configuracion
```

---

## Puertos de los Servicios

| Servicio | Puerto Host | Descripcion |
|----------|-------------|-------------|
| Backend | 8000 | FastAPI - API principal |
| Web | 3000 | Next.js - Frontend |
| File Manager | 8001 | Gestion de archivos |
| Bank Advisor | 8002 | Plugin bancario |
| Dashboard | 8050 | Plotly Dash - Metricas |
| MongoDB | 27018 | Base de datos |
| Redis | 6380 | Cache |
| MinIO API | 9000 | Object storage (API) |
| MinIO Console | 9001 | Object storage (UI) |

---

## Configuracion Avanzada

### Ejecutar sin Docker (Avanzado)

La guia principal se enfoca en un setup con Docker, que es el metodo recomendado. Si eres un usuario avanzado y prefieres correr los servicios directamente en tu maquina, consulta nuestra guia avanzada.

**Guia:** [Correr el stack sin Docker](./advanced_setup.md)

### Variables de Entorno Importantes

#### Desarrollo Local (envs/.env)

```bash
# API Key (REQUERIDO)
SAPTIVA_API_KEY=${SAPTIVA_API_KEY}

# URLs de desarrollo (por defecto)
NODE_ENV=development
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# Base de datos (Docker)
MONGODB_HOST=mongodb
MONGODB_PORT=27017
MONGODB_USER=${MONGODB_USER}
MONGODB_PASSWORD=${MONGODB_PASSWORD}
MONGODB_DATABASE=${MONGODB_DATABASE}

# Redis (Docker)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}
```

### Usar MongoDB Atlas (Nube)

Si prefieres usar MongoDB Atlas en lugar de local:

```bash
# En envs/.env, comenta las lineas de MongoDB local y usa:
MONGODB_URL=mongodb+srv://${MONGODB_USER}:${MONGODB_PASSWORD}@cluster.mongodb.net/${MONGODB_DATABASE}?retryWrites=true&w=majority
```

---

## Solucion de Problemas

### Error: "API key not configured"

```bash
# 1. Verificar que existe envs/.env
ls -la envs/.env

# 2. Verificar que contiene SAPTIVA_API_KEY
grep SAPTIVA_API_KEY envs/.env

# 3. Si no existe, ejecutar setup
make setup
```

### Error: "Cannot connect to MongoDB"

```bash
# Verificar que MongoDB este corriendo
docker ps | grep mongodb

# Reiniciar contenedor de MongoDB
docker restart octavios-chat-bajaware_invex-mongodb

# Ver logs de MongoDB
docker logs octavios-chat-bajaware_invex-mongodb
```

### Error: "Port 3000 already in use"

```bash
# Encontrar el proceso usando el puerto
lsof -i :3000  # Mac/Linux
netstat -ano | findstr :3000  # Windows

# Matar el proceso o cambiar el puerto en envs/.env
```

### Frontend muestra codigo antiguo

```bash
# Limpiar cache de Next.js y reconstruir
make clean-cache
make rebuild.web
```

### Error: "bun not found" en contenedor web

```bash
# La imagen fue construida para produccion. Reconstruir para desarrollo:
docker rm octavios-chat-bajaware_invex-web
docker volume rm octavios-chat-bajaware_invex_web_node_modules
make dev-reset
```

### Errores de permisos con node_modules

```bash
# Dar permisos al usuario actual
sudo chown -R $(id -u):$(id -g) .

# O reconstruir sin cache
make dev-reset
```

### Error: "Docker daemon not running"

```bash
# Mac: Abrir Docker Desktop
open -a Docker

# Linux: Iniciar Docker
sudo systemctl start docker

# Windows: Iniciar Docker Desktop desde el menu de inicio
```

---

## Proximos Pasos

### 1. Explorar la API

Visita http://localhost:8000/docs para ver la documentacion interactiva de la API (Swagger UI).

### 2. Desarrollar

```bash
# El hot-reload esta habilitado automaticamente
# Edita archivos en apps/backend/src/ o apps/web/src/
# Los cambios se reflejaran automaticamente

# Para backend (FastAPI):
# - Edita archivos en apps/backend/src/
# - El servidor se reinicia automaticamente con uvicorn --reload

# Para frontend (Next.js):
# - Edita archivos en apps/web/src/
# - Next.js recarga automaticamente el navegador
```

### 3. Contribuir

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

## Soporte

### Obtener Ayuda

```bash
# Ver todos los comandos disponibles
make help

# Ayuda por categoria
make help.dev       # Comandos de desarrollo
make help.test      # Comandos de testing
make help.db        # Comandos de base de datos
make help.deploy    # Comandos de deploy
```

### Recursos

- **Documentacion**: Ver carpeta `docs/`
- **Issues**: Reportar problemas en GitHub Issues
- **API Docs**: http://localhost:8000/docs (cuando el stack este corriendo)

---

## Checklist de Verificacion

Antes de comenzar a desarrollar, verifica:

- [ ] Docker Desktop esta corriendo
- [ ] Archivo `envs/.env` existe y tiene `SAPTIVA_API_KEY` configurado
- [ ] `make dev` ejecutado exitosamente
- [ ] Todos los servicios estan healthy (`make health` muestra Healthy)
- [ ] Usuario demo creado (`make create-demo-user`)
- [ ] Puedes acceder a http://localhost:3000
- [ ] Puedes iniciar sesion con demo/Demo1234
- [ ] API Docs accesible en http://localhost:8000/docs

---

### Comandos mas usados:

```bash
make dev               # Levantar el stack
make logs S=backend    # Ver logs del backend
make restart           # Reiniciar servicios
make stop              # Detener todo
make health            # Verificar salud
make create-demo-user  # Crear usuario demo
make help              # Ver todos los comandos
```

---

**Ultima actualizacion**: 2026-02-23
