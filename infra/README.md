# Infrastructure

Configuración completa de infraestructura para **Octavios Chat** usando Docker Compose con arquitectura de overlays para desarrollo, testing y producción.

---

## 📁 Estructura

```
infra/
├── docker-compose.yml              # 🔵 BASE: Configuración canónica (552 líneas)
├── docker-compose.dev.yml          # 🟢 DEV: Overlays para desarrollo (67 líneas)
├── docker-compose.production.yml   # 🔴 PROD: Overlays para producción (71 líneas)
├── docker-compose.registry.yml     # 🟡 REGISTRY: Usa imágenes de Docker Hub (27 líneas)
│
├── nginx/                          # Configuraciones de NGINX
│   ├── nginx.conf                  # Config principal
│   ├── dev.conf                    # Config desarrollo
│   └── conf.d/                     # Configuraciones adicionales
│
├── monitoring/                     # Stack de monitoreo (Prometheus, Loki, Grafana)
│   ├── README.md                   # Ver docs/observability/
│   ├── prometheus.yml
│   ├── loki.yml
│   ├── promtail.yml
│   └── grafana/                    # Dashboards y datasources
│
├── observability/                  # Observabilidad (OpenTelemetry, métricas)
│   ├── prometheus.yml
│   ├── prometheus-alerts.yml
│   ├── otel-collector-config.yml
│   └── grafana/
│
├── backups/                        # Backups de bases de datos y configuraciones
│   └── envs/                       # Respaldos de archivos .env
│
└── archive/                        # Archivos legacy/deprecated (NO USAR)
    └── docker-compose-deprecated/
```

---

## 🎯 Arquitectura Docker Compose

### 📐 Diseño de 4 Capas (Overlay Pattern)

La infraestructura usa **Docker Compose multi-file overlay** para máxima flexibilidad y reutilización:

```bash
# Capas que se aplican en orden:
1. docker-compose.yml              → Base (servicios core, volúmenes, networks)
2. docker-compose.dev.yml          → Overlays desarrollo (hot reload, bind mounts)
3. docker-compose.production.yml   → Overlays producción (optimizaciones, seguridad)
4. docker-compose.registry.yml     → Overlays registry (imágenes pre-built)
```

**Composición según escenario:**

| Escenario | Archivos usados | Comando |
|-----------|----------------|---------|
| **Desarrollo local** | `base` + `dev` | `make dev` |
| **Testing E2E** | `base` + `dev` + `profile=testing` | `make test.e2e` |
| **Producción (build local)** | `base` + `production` | `docker compose -f infra/docker-compose.yml -f infra/docker-compose.production.yml up -d` |
| **Producción (registry)** | `base` + `production` + `registry` | `make prod.up REGISTRY=1` |

---

## 🐳 Servicios Disponibles

### Core Services (Siempre activos)

| Servicio | Imagen | Puerto | Descripción |
|----------|--------|--------|-------------|
| **mongodb** | `mongo:7.0` | 27018 | Base de datos principal con auth |
| **redis** | `redis:7-alpine` | 6379 | Cache y sesiones |
| **minio** | `minio/minio:latest` | 9000, 9001 | Object storage (S3-compatible) |
| **qdrant** | `qdrant/qdrant:latest` | 6333 | Vector database para RAG |
| **backend** | Build local / Registry | 8000 | FastAPI backend |
| **web** | Build local / Registry | 3000 | Next.js frontend |
| **file-manager** | Build local / Registry | 8002 | Servicio de gestión de archivos |
| **bank-advisor** | Build local / Registry | 8003 | Asesor bancario especializado |

### Optional Services (Profiles)

| Servicio | Profile | Puerto | Uso |
|----------|---------|--------|-----|
| **nginx** | `production` | 80, 443 | Reverse proxy + TLS |
| **playwright** | `testing` | - | E2E testing environment |
| **postgres** | `analytics` | 5432 | Analytics database (futuro) |

---

## 🚀 Uso Rápido

### Desarrollo Local

```bash
# Iniciar stack completo de desarrollo
make dev

# Iniciar servicios específicos
make dev.backend
make dev.web

# Ver logs
make logs
make logs S=backend  # Solo backend

# Rebuild específico
make rebuild.backend
```

### Testing

```bash
# Tests E2E (levanta Playwright)
make test.e2e

# Tests de API
make test.api

# Tests de auditoría
./scripts/testing/test_audit_flow.sh
```

### Producción

```bash
# Deploy con build local
docker compose -f infra/docker-compose.yml \
               -f infra/docker-compose.production.yml \
               up -d --build

# Deploy con imágenes de Docker Hub (recomendado)
make prod.up REGISTRY=1

# O manualmente:
docker compose -f infra/docker-compose.yml \
               -f infra/docker-compose.production.yml \
               -f infra/docker-compose.registry.yml \
               pull && \
docker compose -f infra/docker-compose.yml \
               -f infra/docker-compose.production.yml \
               -f infra/docker-compose.registry.yml \
               up -d
```

---

## 🔧 Configuración

### Variables de Entorno

Archivo principal: **`envs/.env`** (gitignored)

```bash
# MongoDB
MONGODB_USER=octavios_user
MONGODB_PASSWORD=YOUR_MONGODB_PASSWORD_HERE
MONGODB_DATABASE=octavios
MONGODB_PORT=27018

# Redis
REDIS_PASSWORD=YOUR_REDIS_PASSWORD_HERE

# MinIO (S3)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=YOUR_MINIO_PASSWORD_HERE

# Backend
SECRET_KEY=YOUR_SECRET_KEY_HERE
ANTHROPIC_API_KEY=YOUR_ANTHROPIC_KEY_HERE
OPENAI_API_KEY=YOUR_OPENAI_KEY_HERE
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Ver `envs/.env.example` para lista completa.

### Perfiles Docker Compose

Activar servicios opcionales con `--profile`:

```bash
# Levantar con NGINX (producción)
docker compose -f infra/docker-compose.yml --profile production up -d

# Levantar con Playwright (testing)
docker compose -f infra/docker-compose.yml --profile testing up -d

# Múltiples perfiles
docker compose -f infra/docker-compose.yml \
  --profile production \
  --profile analytics \
  up -d
```

---

## 📊 Monitoreo y Observabilidad

### Monitoring Stack (Prometheus + Loki + Grafana)

```bash
# Iniciar stack de monitoreo
make obs-up

# Acceder a Grafana
open http://localhost:3001
# Login: admin/admin

# Ver métricas
open http://localhost:9090  # Prometheus

# Detener monitoreo
make obs-down
```

**Documentación completa:** [`docs/observability/`](../docs/observability/)

### Configuraciones

- **Prometheus**: `infra/monitoring/prometheus.yml` (scraping)
- **Loki**: `infra/monitoring/loki.yml` (logs storage)
- **Promtail**: `infra/monitoring/promtail.yml` (log collection)
- **Alertas**: `infra/observability/prometheus-alerts.yml`
- **OpenTelemetry**: `infra/observability/otel-collector-config.yml`

---

## 🔒 NGINX (Producción)

### Configuraciones

| Archivo | Propósito |
|---------|-----------|
| `nginx/nginx.conf` | Config principal, optimizaciones, security headers |
| `nginx/dev.conf` | Reverse proxy para desarrollo |
| `nginx/conf.d/` | Configuraciones adicionales modulares |

### Uso

```bash
# En desarrollo (usa nginx/dev.conf)
make dev

# En producción (usa nginx/nginx.conf)
docker compose -f infra/docker-compose.yml \
               -f infra/docker-compose.production.yml \
               --profile production up -d
```

---

## 🗄️ Backups

### Base de Datos

```bash
# Backup MongoDB
make db.backup

# Restore desde backup
make db.restore BACKUP=/path/to/backup.gz

# Listar backups disponibles
make db.backups
```

**Ubicación:** `infra/backups/` (gitignored en root `.gitignore` como `backups/`)

**Scripts:** Ver [`scripts/database/`](../scripts/database/)

### Configuraciones

Los archivos `.env` se respaldan automáticamente en `infra/backups/envs/` durante deploys.

---

## 🏗️ Build y Registry

### Build Local

```bash
# Build todos los servicios
make build

# Build específico
make build.backend
make build.web

# Rebuild forzado (sin cache)
make rebuild.backend FORCE=1
```

### Docker Hub Registry

El proyecto usa **Docker Hub** como registry para producción:

**Registry:** `docker.io/jazielflores1998`

**Imágenes:**
- `jazielflores1998/octavios-invex-backend:0.1.2`
- `jazielflores1998/octavios-invex-web:0.1.2`
- `jazielflores1998/octavios-invex-file-manager:0.1.2`
- `jazielflores1998/octavios-invex-bank-advisor:0.1.2`

**Scripts de deploy:** Ver [`scripts/deploy/`](../scripts/deploy/)

```bash
# Tag y push a Docker Hub
./scripts/deploy/tag-dockerhub.sh 0.1.3
./scripts/deploy/push-dockerhub.sh

# Deploy a producción usando registry
./scripts/deploy/deploy-to-production.sh
```

---

## 🛠️ Operaciones Comunes

### Health Checks

```bash
# Ver estado de servicios
make ps
docker compose -f infra/docker-compose.yml ps

# Health checks individuales
curl http://localhost:8000/health     # Backend
curl http://localhost:3000/api/health # Frontend
```

### Logs

```bash
# Todos los logs
make logs

# Servicio específico
make logs S=backend

# Follow mode
docker compose -f infra/docker-compose.yml logs -f backend web
```

### Restart y Rebuild

```bash
# Restart sin rebuild
make restart

# Restart servicio específico
docker compose -f infra/docker-compose.yml restart backend

# Rebuild + restart
make rebuild.backend
```

### Limpieza

```bash
# Detener todos los servicios
make down

# Detener y eliminar volúmenes (¡CUIDADO!)
make clean

# Eliminar imágenes sin usar
docker image prune -a
```

---

## 📦 Volúmenes

### Named Volumes (Persistentes)

| Volume | Uso |
|--------|-----|
| `mongodb_data` | Datos de MongoDB |
| `mongodb_config` | Configuración MongoDB |
| `redis_data` | Datos de Redis |
| `minio_data` | Object storage (MinIO) |
| `qdrant_storage` | Vector database |
| `postgres_data` | PostgreSQL (analytics) |

### Bind Mounts (Desarrollo)

En modo desarrollo (`docker-compose.dev.yml`), se montan:
- `../apps/backend` → `/app/apps/backend` (Hot reload)
- `../apps/web` → `/app/apps/web` (Hot reload)
- `../packages` → `/app/packages` (Shared libs)

**Producción NO usa bind mounts** (código dentro de imagen).

---

## 🌐 Networking

### Network: `octavios-network`

Todos los servicios se comunican vía la red interna `octavios-network` (bridge).

**Resolución DNS interna:**
- `mongodb:27017` (desde otros containers)
- `redis:6379`
- `backend:8000`
- `web:3000`

**Desde host:** Usa `localhost` + puerto mapeado (ej: `localhost:27018` para MongoDB).

---

## 🎓 Referencias

### Makefile

El **Makefile** es el orquestador principal. Ver comandos disponibles:

```bash
make help           # Ayuda general
make help.dev       # Comandos desarrollo
make help.prod      # Comandos producción
make help.db        # Comandos base de datos
make help.test      # Comandos testing
```

### Scripts

- **Deploy:** [`scripts/deploy/`](../scripts/deploy/)
- **Database:** [`scripts/database/`](../scripts/database/)
- **Testing:** [`scripts/testing/`](../scripts/testing/)

### Documentación

- **Observability:** [`docs/observability/`](../docs/observability/)
- **Setup:** [`docs/setup/`](../docs/setup/)

---

## 🚨 Troubleshooting

### Puerto ya en uso

```bash
# Ver qué usa el puerto
lsof -i :8000

# Detener servicio específico
make down
docker compose -f infra/docker-compose.yml stop backend
```

### MongoDB no arranca

```bash
# Ver logs
make logs S=mongodb

# Verificar permisos de volumen
docker volume inspect octavios-chat-bajaware_invex_mongodb_data

# Recrear volumen (¡PIERDE DATOS!)
make clean
make dev
```

### Build falla

```bash
# Limpiar cache de Docker
docker builder prune -a

# Rebuild sin cache
make rebuild.backend FORCE=1
```

### Servicios lentos

```bash
# Verificar recursos
docker stats

# Ver uso de volúmenes
docker system df
```

---

## 📋 Checklist Pre-Deploy

Antes de deploy a producción:

- [ ] Actualizar `envs/.env.prod` con secrets seguros
- [ ] Build y tag de imágenes: `./scripts/deploy/tag-dockerhub.sh X.Y.Z`
- [ ] Push a Docker Hub: `./scripts/deploy/push-dockerhub.sh`
- [ ] Backup de DB en servidor: `make db.backup` (remoto)
- [ ] Test smoke en staging (si existe)
- [ ] Verificar CORS_ORIGINS incluye dominio de producción
- [ ] Verificar SECRET_KEY es diferente de dev
- [ ] Revisar health checks: `/health` endpoints
- [ ] Deploy: `./scripts/deploy/deploy-to-production.sh`
- [ ] Verificar logs post-deploy: `make logs`

---

## 🔗 Enlaces Rápidos

| Servicio | Dev | Prod (ejemplo) |
|----------|-----|----------------|
| Frontend | http://localhost:3000 | https://yourdomain.com |
| Backend API | http://localhost:8000 | https://yourdomain.com/api |
| API Docs | http://localhost:8000/docs | https://yourdomain.com/docs |
| MinIO Console | http://localhost:9001 | - |
| Grafana | http://localhost:3001 | - |
| Prometheus | http://localhost:9090 | - |

---

**Última actualización:** 2024-12-03
**Versión:** 2.0 (Overlay Architecture)
