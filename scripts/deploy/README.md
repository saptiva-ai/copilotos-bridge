# Deploy Scripts

Scripts de deployment y gestión de imágenes Docker.

## Scripts Disponibles

### 🚀 Deployment Principal

- **`deploy-to-production.sh`** - ⭐ Deploy completo a producción vía Docker Hub registry
  ```bash
  # En servidor de producción:
  ./scripts/deploy/deploy-to-production.sh 0.1.3

  # O con Makefile:
  make deploy-registry VERSION=0.1.3
  ```

  **Qué hace:**
  1. Backup de base de datos (opcional)
  2. Pull de código desde Git
  3. Actualiza versión en docker-compose.registry.yml
  4. Pull de imágenes desde Docker Hub
  5. Recrea contenedores con nuevas imágenes
  6. Health checks automáticos
  7. Verificación de datos

### 🏷️  Image Tagging

- **`tag-dockerhub.sh`** - Tag de imágenes para Docker Hub
  ```bash
  ./scripts/deploy/tag-dockerhub.sh 0.1.3
  ```

- **`tag-images.sh`** - Tag de imágenes locales
  ```bash
  ./scripts/deploy/tag-images.sh 0.1.3
  ```

### 📤 Registry Push

- **`push-dockerhub.sh`** - Push de imágenes a Docker Hub
  ```bash
  ./scripts/deploy/push-dockerhub.sh

  # O con Makefile:
  make registry-push
  ```

### ▶️  Production Start

- **`start-production.sh`** - Iniciar servicios en producción
  ```bash
  ./scripts/deploy/start-production.sh
  ```

## Workflow Completo de Deployment

### LOCAL: Build y Push a Docker Hub

```bash
# 1. Build imágenes localmente
make prod.build

# 2. Tag para Docker Hub
./scripts/deploy/tag-dockerhub.sh 0.1.3

# 3. Push a Docker Hub
./scripts/deploy/push-dockerhub.sh

# O todo en uno:
make deploy-registry VERSION=0.1.3
```

### SERVIDOR: Deploy desde Docker Hub

```bash
# SSH al servidor
ssh usuario@servidor

# Deploy desde registry
cd proyecto
./scripts/deploy/deploy-to-production.sh 0.1.3
```

## Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DEPLOY_SERVER` | user@YOUR_PRODUCTION_SERVER | Servidor de producción (SSH) |
| `DEPLOY_PROJECT_DIR` | octavios-chat-bajaware_invex | Directorio del proyecto |
| `BACKUP_DB` | true | Hacer backup antes de deploy |

## Ejemplos

### Deploy Completo

```bash
# LOCAL: Preparar y subir imágenes
VERSION=0.1.4 make deploy-registry

# SERVIDOR: Desplegar
ssh servidor
cd proyecto
./scripts/deploy/deploy-to-production.sh 0.1.4
```

### Solo Tag y Push

```bash
./scripts/deploy/tag-dockerhub.sh 0.1.5
./scripts/deploy/push-dockerhub.sh
```

### Deploy Sin Backup

```bash
BACKUP_DB=false ./scripts/deploy/deploy-to-production.sh 0.1.3
```

## Ver También

- **`docs/DEPLOY_ANALISIS_Y_GUIA.md`** - Guía completa de deployment
- **`docs/ARQUITECTURA_SCRIPTS_Y_DOCKER.md`** - Arquitectura Docker Compose
- **`scripts/README.md`** - Organización de scripts

---

**⚠️  IMPORTANTE:**
- Siempre hacer backup antes de deploy en producción
- Usar versionado semántico (major.minor.patch)
- Verificar health checks después del deploy
- Probar en demo antes de producción
