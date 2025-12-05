# Deploy Scripts - Guía Completa

Scripts de deployment para Octavios - Soporta deployments granulares y completos.

## 📋 Tabla de Contenidos

- [Scripts Disponibles](#scripts-disponibles)
- [Setup Inicial](#-setup-inicial)
- [Deployment Granular (NUEVO)](#-deployment-granular-nuevo)
- [Deployment Completo (Legacy)](#-deployment-completo-legacy)
- [Workflow Recomendado](#-workflow-recomendado)
- [Variables de Entorno](#-variables-de-entorno)
- [Troubleshooting](#-troubleshooting)
- [Mejores Prácticas](#-mejores-prácticas)
- [Validación Pre-Deploy](#-validación-pre-deploy)
- [Checklist Pre-Deploy](#-checklist-pre-deploy)

## 🛠️ Scripts Disponibles

### Deployment Granular (v2.0)

#### **`deploy-service.sh`** - ⭐ Deploy selectivo de servicios
Despliega servicios específicos a producción (backend, web, file-manager, bank-advisor).

```bash
./scripts/deploy/deploy-service.sh "backend" 0.2.2          # Solo backend
./scripts/deploy/deploy-service.sh "backend web" 0.2.2      # Backend + web
./scripts/deploy/deploy-service.sh "all" 0.2.2              # Todos los servicios
```

#### **`detect-changes.sh`** - Detecta servicios modificados
Compara cambios en git para identificar qué servicios necesitan deploy.

```bash
./scripts/deploy/detect-changes.sh              # vs HEAD~1
./scripts/deploy/detect-changes.sh v0.2.1       # vs tag específico
```

#### **`tag-push-service.sh`** - Tag y push selectivo
Etiqueta y sube servicios específicos a Docker Hub.

```bash
./scripts/deploy/tag-push-service.sh "backend" 0.2.2        # Solo backend
./scripts/deploy/tag-push-service.sh "all" 0.2.2            # Todos
```

#### **`load-env.sh`** - Carga variables de entorno
Helper para cargar variables de deployment.

```bash
source scripts/deploy/load-env.sh prod          # Cargar .env.prod
source scripts/deploy/load-env.sh dev           # Cargar .env
```

### Deployment Completo (Legacy)

#### **`deploy-to-production.sh`** - Deploy completo
Despliega todos los servicios a producción.

```bash
./scripts/deploy/deploy-to-production.sh 0.2.2
```

#### **`tag-dockerhub.sh`** - Tag de todas las imágenes

```bash
./scripts/deploy/tag-dockerhub.sh 0.2.2
```

#### **`push-dockerhub.sh`** - Push de todas las imágenes

```bash
./scripts/deploy/push-dockerhub.sh
```

## 🚀 Setup Inicial

### 1. Configurar Variables de Entorno

Asegúrate de que `envs/.env.prod` tiene:

```bash
DEPLOY_SERVER=user@your-server-ip
DEPLOY_PROJECT_DIR=/home/user/project-dir
PROD_DOMAIN=your-domain.com
```

### 2. Verificar Acceso SSH

```bash
ssh $DEPLOY_SERVER "echo 'SSH OK'"
```

### 3. Cargar Variables

```bash
source scripts/deploy/load-env.sh prod
```

## 🎯 Deployment Granular (NUEVO)

### Ventajas
- ✅ Deploy solo lo que cambió
- ✅ Menor riesgo (servicios independientes)
- ✅ Más rápido (menos imágenes)
- ✅ Zero-downtime por servicio

### Workflow Completo

```bash
# 1. Detectar cambios
CHANGED=$(./scripts/deploy/detect-changes.sh | tail -1)
echo "Servicios modificados: $CHANGED"

# 2. Build solo lo modificado
make prod.build SVC="$CHANGED"

# 3. Tag y push
./scripts/deploy/tag-push-service.sh "$CHANGED" 0.2.2

# 4. Deploy
source scripts/deploy/load-env.sh prod
./scripts/deploy/deploy-service.sh "$CHANGED" 0.2.2
```

### Ejemplos de Uso

#### Deploy Backend (Bug Fix)

```bash
# Build
make prod.build SVC=backend

# Tag y push
./scripts/deploy/tag-push-service.sh "backend" 0.2.3

# Deploy
source scripts/deploy/load-env.sh prod
./scripts/deploy/deploy-service.sh "backend" 0.2.3
```

#### Deploy Frontend + Backend

```bash
# Build ambos
make prod.build SVC="backend web"

# Tag y push ambos
./scripts/deploy/tag-push-service.sh "backend web" 0.2.3

# Deploy
source scripts/deploy/load-env.sh prod
./scripts/deploy/deploy-service.sh "backend web" 0.2.3
```

#### Deploy con Detección Automática

```bash
CHANGED=$(./scripts/deploy/detect-changes.sh v0.2.2 | tail -1)

if [ ! -z "$CHANGED" ]; then
  make prod.build SVC="$CHANGED"
  ./scripts/deploy/tag-push-service.sh "$CHANGED" 0.2.3
  source scripts/deploy/load-env.sh prod
  ./scripts/deploy/deploy-service.sh "$CHANGED" 0.2.3
else
  echo "No changes detected"
fi
```

## 📦 Deployment Completo (Legacy)

### Workflow Tradicional

```bash
# LOCAL: Build y Push
make prod.build
./scripts/deploy/tag-dockerhub.sh 0.2.2
./scripts/deploy/push-dockerhub.sh

# SERVIDOR: Deploy
./scripts/deploy/deploy-to-production.sh 0.2.2
```

### Con Makefile

```bash
# Build todos los servicios
make prod.build

# O con servicios específicos
make prod.build SVC="backend web"

# O solo lo que cambió
make prod.build CHANGED=1

# O pull desde registry
make prod.build REGISTRY=1
```

## 💡 Workflow Recomendado

### Para Bug Fixes (1 servicio)
```bash
# ✅ Usa deployment granular
source scripts/deploy/load-env.sh prod
make prod.build SVC=backend
./scripts/deploy/tag-push-service.sh "backend" 0.2.3
./scripts/deploy/deploy-service.sh "backend" 0.2.3
```

### Para Features (2-3 servicios)
```bash
# ✅ Usa deployment granular
source scripts/deploy/load-env.sh prod
make prod.build SVC="backend web"
./scripts/deploy/tag-push-service.sh "backend web" 0.2.3
./scripts/deploy/deploy-service.sh "backend web" 0.2.3
```

### Para Releases Mayores
```bash
# ✅ Usa deployment completo
./scripts/deploy/tag-dockerhub.sh 0.3.0
./scripts/deploy/push-dockerhub.sh
./scripts/deploy/deploy-to-production.sh 0.3.0
```

## 📊 Variables de Entorno

| Variable | Ejemplo | Descripción |
|----------|---------|-------------|
| `DEPLOY_SERVER` | user@server-ip | Servidor de producción (SSH) |
| `DEPLOY_PROJECT_DIR` | /home/user/project | Directorio del proyecto |
| `PROD_DOMAIN` | example.com | Dominio de producción |
| `BACKUP_DB` | false (default) | Backup antes de deploy granular |

## 🐛 Troubleshooting

### Error: "DEPLOY_SERVER environment variable is required"

```bash
source scripts/deploy/load-env.sh prod
```

### Error: "No such image"

```bash
# Opción 1: Build
make prod.build SVC=backend

# Opción 2: Pull desde Docker Hub
docker pull jazielflores1998/octavios-invex-backend:0.2.2
```

### Error: "Failed to pull images"

```bash
# Verificar que existe en Docker Hub
curl -s "https://hub.docker.com/v2/repositories/jazielflores1998/octavios-invex-backend/tags" | grep "0.2.2"

# Si no existe, hacer push
./scripts/deploy/tag-push-service.sh "backend" 0.2.2
```

### Error: "Service unhealthy"

```bash
# Ver logs
ssh $DEPLOY_SERVER "cd $DEPLOY_PROJECT_DIR && docker compose logs backend"

# Rollback
source scripts/deploy/load-env.sh prod
./scripts/deploy/deploy-service.sh "backend" 0.2.1
```

### Error: "No space left on device"

```bash
# Limpiar imágenes antiguas
ssh $DEPLOY_SERVER "docker system prune -a --filter 'until=72h' -f"
```

## 📈 Monitoreo Post-Deploy

### Health Checks

```bash
# Backend
curl -s https://back-invex.saptiva.com/api/health | jq

# Frontend
curl -s -o /dev/null -w "%{http_code}" https://invex.saptiva.com
```

### Ver Logs

```bash
# Backend
ssh $DEPLOY_SERVER "cd $DEPLOY_PROJECT_DIR && docker compose logs -f backend"

# Todos
ssh $DEPLOY_SERVER "cd $DEPLOY_PROJECT_DIR && docker compose logs -f"
```

### Verificar Versiones Desplegadas

```bash
ssh $DEPLOY_SERVER "cd $DEPLOY_PROJECT_DIR && grep 'image:' infra/docker-compose.registry.yml"
```

## 🔐 Seguridad

### Variables Sensibles

**NUNCA** hardcodear en scripts:
- ❌ Passwords
- ❌ API keys
- ❌ JWT secrets

Usar `envs/.env.prod` (en `.gitignore`).

### SSH

- Usa SSH keys
- Limita IPs autorizadas
- Considera bastion host

## 📚 Referencias

- [Environment Variables](../../envs/.env.prod.example)
- [Makefile Targets](../../Makefile)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [Docker Hub Registry](https://hub.docker.com/u/jazielflores1998)

---

## 🎯 Mejores Prácticas

### Resumen de Incidentes y Soluciones

**Incidente 2025-12-04**: Deploy fallido por:
1. ❌ Variables de entorno (SECRET_KEY, JWT_SECRET_KEY) no propagándose correctamente
2. ❌ Referencias a versiones de imágenes inexistentes en Docker Hub (web:0.2.2, file-manager:0.2.2)

**Soluciones Implementadas**:
- ✅ Validación automática pre-deploy con `validate-deploy.sh`
- ✅ Variables de entorno explícitas en `docker-compose.production.yml`
- ✅ Versionado flexible con variables de entorno en `docker-compose.registry.yml`

### Gestión de Variables de Entorno

#### ❌ Problema Anterior

Las variables sensibles en `envs/.env` no se propagaban correctamente a los contenedores porque:
- Valores con espacios/caracteres especiales causaban errores de parsing
- `env_file` de Docker Compose no siempre funciona en producción
- No había validación de que las variables llegaran a los contenedores

#### ✅ Solución Implementada

**1. Paso Explícito de Variables Críticas**

En `infra/docker-compose.production.yml`:

```yaml
services:
  backend:
    environment:
      # Critical secrets - must be set via environment or .env file
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
```

**2. Cargar Variables Antes de Deploy**

```bash
# Método 1: Helper script (recomendado)
source scripts/deploy/load-env.sh prod

# Verificar que están cargadas
echo "SECRET_KEY length: ${#SECRET_KEY}"
echo "JWT_SECRET_KEY length: ${#JWT_SECRET_KEY}"
```

**DO** ✅:
- Usar `source scripts/deploy/load-env.sh prod` antes de deploy
- Validar con `validate-deploy.sh` antes de cambios
- Mantener `envs/.env.prod` en `.gitignore`
- Usar valores generados aleatoriamente para secrets (ej: `openssl rand -base64 32`)

**DON'T** ❌:
- Hardcodear secrets en archivos docker-compose
- Commitear `envs/.env.prod` a git
- Usar valores cortos o predecibles para SECRET_KEY/JWT_SECRET_KEY
- Asumir que env_file funcionará en producción sin validar

### Gestión de Versiones de Imágenes

#### ❌ Problema Anterior

Versiones hardcodeadas en `docker-compose.registry.yml`:

```yaml
# ANTES (hardcoded - malo)
services:
  web:
    image: jazielflores1998/octavios-invex-web:0.2.2  # ❌ No existe!
```

**Problemas:**
- Si la imagen no existe en Docker Hub → deploy falla
- Cambiar versiones requiere editar archivo manualmente
- No hay validación antes de deploy
- Difícil hacer rollback rápido

#### ✅ Solución Implementada

**Versionado con Variables de Entorno**

En `infra/docker-compose.registry.yml`:

```yaml
services:
  backend:
    image: jazielflores1998/octavios-invex-backend:${BACKEND_VERSION:-0.2.2}
    build: null

  web:
    image: jazielflores1998/octavios-invex-web:${WEB_VERSION:-0.2.1}
    build: null
```

**Ventajas:**
- Valores por defecto seguros (`:-0.2.1`)
- Override por servicio: `BACKEND_VERSION=0.2.3 docker compose up`
- No necesitas editar archivos para cambiar versiones
- Más fácil hacer rollback

**Verificación Manual**

Antes de cambiar versiones en producción:

```bash
# Verificar que la imagen existe
docker manifest inspect jazielflores1998/octavios-invex-backend:0.2.3

# Listar todas las versiones disponibles
curl -s "https://hub.docker.com/v2/repositories/jazielflores1998/octavios-invex-backend/tags" | jq -r '.results[].name'
```

**DO** ✅:
- Validar existencia de imágenes antes de deploy con `validate-deploy.sh`
- Usar semantic versioning (0.2.3, no "latest")
- Mantener versiones por defecto conservadoras
- Documentar qué cambió en cada versión (CHANGELOG)

**DON'T** ❌:
- Usar tag `latest` en producción
- Asumir que una versión existe sin verificar
- Cambiar versiones directamente en servidor sin validar
- Deployar versiones no probadas en staging

---

## 🔍 Validación Pre-Deploy

### Script `validate-deploy.sh`

Todos los scripts de deploy ahora ejecutan automáticamente validación que verifica:

```bash
./scripts/deploy/validate-deploy.sh 0.2.2
```

**Verificaciones realizadas:**

1. **Variables de Entorno Críticas**
   - `SECRET_KEY` (mínimo 32 caracteres)
   - `JWT_SECRET_KEY` (mínimo 32 caracteres)
   - `DEPLOY_SERVER` (servidor de producción)

2. **Imágenes Docker Hub**
   - Verifica que las imágenes existen en Docker Hub antes de intentar deploy
   - Usa `docker manifest inspect` para validar cada versión

3. **Estado de Git**
   - Advierte si hay cambios uncommitted
   - Muestra branch actual

4. **Configuración Docker Compose**
   - Valida sintaxis de archivos compose
   - Verifica que los overlays se combinan correctamente

5. **Conectividad SSH**
   - Prueba conexión al servidor de producción
   - Timeout de 5 segundos

**Resultado:**
- ❌ Exit code 1 si hay **errores** → Deploy bloqueado
- ⚠️ Exit code 0 con **warnings** → Deploy permitido pero con advertencias
- ✅ Exit code 0 sin warnings → Todo OK

### Uso Manual

```bash
# Validar antes de deploy
source scripts/deploy/load-env.sh prod
./scripts/deploy/validate-deploy.sh 0.2.2

# Si pasa validación, proceder con deploy
./scripts/deploy/deploy-service.sh "backend" 0.2.2
```

---

## ✅ Checklist Pre-Deploy

### Antes de CUALQUIER Deploy

- [ ] **Environment cargado**: `source scripts/deploy/load-env.sh prod`
- [ ] **Validación pasada**: `./scripts/deploy/validate-deploy.sh <VERSION>`
- [ ] **Imágenes existen en Docker Hub**: Validación automática + verificación manual
- [ ] **Código commiteado**: `git status` limpio
- [ ] **Branch correcto**: Normalmente `main`
- [ ] **Changelog actualizado**: Documentar cambios en versión

### Deploy Granular Adicional

- [ ] **Servicios correctos identificados**: Usa `./scripts/deploy/detect-changes.sh`
- [ ] **Build solo servicios necesarios**: `make prod.build SVC="backend web"`
- [ ] **Versión incrementada apropiadamente**: Patch (0.2.2 → 0.2.3) para fixes

### Deploy Completo Adicional

- [ ] **Notificar stakeholders**: Deploy completo puede tener breve downtime
- [ ] **Backup automático habilitado**: `BACKUP_DB=true`
- [ ] **Todos los servicios built**: `make prod.build`
- [ ] **Todas las imágenes pushed**: `./scripts/deploy/push-dockerhub.sh`

### Post-Deploy

- [ ] **Health checks OK**: Validación automática en script
- [ ] **Endpoints responden 200**: Web, Backend API
- [ ] **Prueba funcionalidad crítica**: Login, Bank Advisor query
- [ ] **Revisar logs**: No errores en últimos minutos
- [ ] **Verificar métricas**: Prometheus/Grafana si disponible

---

**Última actualización:** 2025-12-04
**Versión del sistema:** 2.0 (granular deployment)
**Servicios disponibles:** backend, web, file-manager, bank-advisor
