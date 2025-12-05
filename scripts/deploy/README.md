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

---

## 🛡️ Lecciones del Deploy 2025-12-05 (v1.2.3) ⭐ NUEVO

### Incidente: Bug Fixes con Credenciales Faltantes

**Contexto**: Deploy de fixes críticos (race condition en web, NULL values en bank-advisor) con configuración de credenciales GCP PostgreSQL.

**Duración**: ~45 minutos desde merge hasta verificación completa
**Servicios Actualizados**: backend:1.2.3, web:1.2.3, bank-advisor:1.2.3
**Resultado**: ✅ Deploy exitoso, todos los servicios healthy

---

### 🎯 Lo Que Hicimos BIEN ✅

#### 1. **Workflow Git Estructurado**
```bash
# ✅ Flujo correcto ejecutado
git tag v1.2.3 -m "Release v1.2.3: Fix bank chart rendering and NULL values"
git push origin v1.2.3
```

**Por qué fue bueno:**
- Tag semántico claro (v1.2.3 = patch release)
- Mensaje descriptivo de los fixes incluidos
- Sincronizado con Docker Hub tags

---

#### 2. **Build de Imágenes con Contexto Correcto**
```bash
# ✅ Comandos correctos desde raíz del proyecto
docker build -f apps/backend/Dockerfile apps/backend  # Contexto: apps/backend
docker build -f apps/web/Dockerfile .                 # Contexto: raíz (necesita monorepo)
docker build -f plugins/bank-advisor-private/Dockerfile .  # Contexto: raíz
```

**Por qué fue bueno:**
- Cada Dockerfile tiene diferentes requisitos de contexto
- Backend: Solo necesita apps/backend
- Web: Necesita raíz para pnpm-workspace.yaml y packages/
- Bank-advisor: Necesita raíz para acceso a plugins/

**Lección aprendida**: No todos los builds se hacen igual - verificar el contexto requerido en cada Dockerfile.

---

#### 3. **Push de Imágenes con Múltiples Tags**
```bash
# ✅ Estrategia de tagging correcta
docker build -t jazielflores1998/octavios-invex-backend:1.2.3 \
             -t jazielflores1998/octavios-invex-backend:1.2.3-20251205-1413 \
             -t jazielflores1998/octavios-invex-backend:latest
```

**Por qué fue bueno:**
- `1.2.3`: Tag semántico para producción
- `1.2.3-20251205-1413`: Tag con timestamp para auditoría
- `latest`: Tag de conveniencia (pero no usado en producción)

**Beneficio**: Permite rollback fácil a versiones específicas por semver o timestamp.

---

#### 4. **Deploy Controlado con Downtime Planificado**
```bash
# ✅ Secuencia correcta para evitar problemas
1. docker compose down              # Parar todos los contenedores
2. git stash && git pull            # Actualizar código (stash para cambios locales)
3. sed -i 's/:1\.2\.2/:1.2.3/g' infra/docker-compose.registry.yml  # Actualizar versiones
4. docker compose pull backend      # Pull una imagen a la vez (evitar congelar servidor)
5. docker compose pull web
6. docker compose pull bank-advisor
7. docker compose up -d             # Levantar todos
```

**Por qué fue bueno:**
- Pull incremental evitó congelar el servidor (recursos limitados)
- `git stash` preservó cambios locales (registry.yml)
- Downtime breve y controlado (< 2 minutos)

**Lección aprendida**: En servidores con recursos limitados, hacer pull de imágenes una por una.

---

#### 5. **Diagnóstico Sistemático del Problema de Bank-Advisor**
```bash
# ✅ Pasos de diagnóstico correctos
1. docker compose ps bank-advisor              # Status: unhealthy
2. docker compose logs bank-advisor            # "Waiting for PostgreSQL..."
3. grep POSTGRES_HOST envs/.env.prod (local)   # 35.193.13.180 ✅
4. ssh ... "grep POSTGRES_HOST envs/.env.prod" # postgres ❌ (encontrado el problema!)
5. docker compose exec bank-advisor env | grep POSTGRES  # Verificar vars en contenedor
```

**Por qué fue bueno:**
- Diagnóstico metódico: status → logs → env local → env remoto → vars en contenedor
- Identificó el problema rápidamente (credenciales desincronizadas)

---

#### 6. **Sincronización de Credenciales con SCP**
```bash
# ✅ Proceso correcto de actualización de .env
ssh ... "cp envs/.env.prod envs/.env.prod.backup-$(date +%Y%m%d-%H%M%S)"
scp envs/.env.prod jf@34.28.92.134:octavios-chat-bajaware_invex/envs/.env.prod
ssh ... "grep POSTGRES_HOST envs/.env.prod"  # Verificar: 35.193.13.180 ✅
```

**Por qué fue bueno:**
- **Backup automático antes de sobrescribir**
- Verificación inmediata post-copia
- Preserva permisos del archivo

---

#### 7. **Recreación Correcta del Contenedor para Recargar ENV**
```bash
# ✅ Secuencia correcta (restart NO recarga env vars)
docker compose stop bank-advisor       # Parar
docker compose rm -f bank-advisor      # Eliminar contenedor (NO volúmenes)
docker compose up -d bank-advisor      # Recrear con nuevas env vars
```

**Por qué fue bueno:**
- `restart` NO recarga environment variables en Docker
- `rm -f` elimina el contenedor pero **preserva volúmenes de datos**
- `up -d` recrea con las nuevas variables

**CRITICAL**: `docker compose restart` NO es suficiente para recargar .env changes.

---

### ❌ Lo Que Hicimos MAL y Cómo Mejorar

#### Error 7: Credenciales de Producción Desincronizadas 🔥 CRÍTICO

**Síntoma**:
```
bank-advisor: unhealthy
Logs: "⏳ Waiting for PostgreSQL to be ready..." (loop infinito)
```

**Causa Raíz**:
- `.env.prod` local tenía: `POSTGRES_HOST=35.193.13.180` (GCP)
- `.env.prod` en servidor tenía: `POSTGRES_HOST=postgres` (local)
- Bank-advisor esperaba GCP con 721 registros, pero intentaba conectar al postgres local vacío

**Impacto**:
- Bank-advisor no funcional durante 15 minutos
- Queries de métricas bancarias fallaban

**Solución Aplicada**:
```bash
# Backup + sincronización + recreación
ssh ... "cp envs/.env.prod envs/.env.prod.backup-$(date +%Y%m%d-%H%M%S)"
scp envs/.env.prod jf@34.28.92.134:octavios-chat-bajaware_invex/envs/.env.prod
ssh ... "docker compose stop bank-advisor && docker compose rm -f bank-advisor"
ssh ... "docker compose up -d bank-advisor"
```

**Prevención Futura**:

**A. Script de Sincronización Automática**
Crear `scripts/deploy/sync-env.sh`:
```bash
#!/bin/bash
# sync-env.sh - Sincroniza .env.prod local con servidor
set -e

DEPLOY_SERVER="${DEPLOY_SERVER:-jf@34.28.92.134}"
PROJECT_DIR="octavios-chat-bajaware_invex"

echo "📋 Backing up remote .env.prod..."
ssh "$DEPLOY_SERVER" "cd $PROJECT_DIR && cp envs/.env.prod envs/.env.prod.backup-\$(date +%Y%m%d-%H%M%S)"

echo "📤 Uploading local .env.prod to server..."
scp envs/.env.prod "$DEPLOY_SERVER:$PROJECT_DIR/envs/.env.prod"

echo "✅ Verifying critical variables on server..."
ssh "$DEPLOY_SERVER" "cd $PROJECT_DIR && grep -E '^(POSTGRES_HOST|SECRET_KEY|JWT_SECRET_KEY)' envs/.env.prod | head -3"

echo "✅ Sync complete!"
```

**B. Validación Pre-Deploy Mejorada**
Agregar a `validate-deploy.sh`:
```bash
# Verificar que POSTGRES_HOST apunta a GCP en producción
if [ -f "envs/.env.prod" ]; then
    POSTGRES_HOST=$(grep '^POSTGRES_HOST=' envs/.env.prod | cut -d'=' -f2)
    if [[ "$POSTGRES_HOST" != "35.193.13.180" ]]; then
        log_error "POSTGRES_HOST in .env.prod should be 35.193.13.180 (GCP), got: $POSTGRES_HOST"
        ((ERRORS++))
    fi
fi
```

**C. Checklist Pre-Deploy Actualizado**
Agregar al checklist:
```markdown
- [ ] **Credenciales sincronizadas**: `./scripts/deploy/sync-env.sh` ejecutado
- [ ] **POSTGRES_HOST verificado**: Debe ser `35.193.13.180` en producción
- [ ] **Backup de .env.prod creado**: Automático con timestamp
```

**Lecciones Críticas**:
1. 🔴 **NUNCA asumir que .env está sincronizado** entre local y servidor
2. 🔴 **SIEMPRE verificar env vars DENTRO del contenedor** después de recrear
3. 🔴 **SIEMPRE hacer backup antes de sobrescribir .env.prod**
4. 🟡 Considerar usar **secret management service** (AWS Secrets Manager, HashiCorp Vault) en lugar de archivos .env

---

#### Error 8: Confusión Entre `restart` y `rm + up`

**Síntoma**:
```bash
docker compose restart bank-advisor  # Variables NO se recargaron ❌
```

**Causa**: `restart` reinicia el contenedor existente, NO recrea con nuevas env vars.

**Solución Correcta**:
```bash
docker compose stop bank-advisor
docker compose rm -f bank-advisor      # Elimina contenedor (preserva volúmenes)
docker compose up -d bank-advisor      # Recrea con env vars actualizadas
```

**Prevención**: Documentar claramente en checklist:
```markdown
⚠️ Para recargar variables de entorno:
- ❌ NO usar: docker compose restart
- ✅ SÍ usar: stop → rm -f → up -d
```

---

### 📊 Métricas del Deploy v1.2.3

| Métrica | Valor |
|---------|-------|
| **Duración Total** | 45 minutos |
| **Downtime Planificado** | 2 minutos |
| **Downtime No Planificado** | 15 minutos (bank-advisor con credenciales incorrectas) |
| **Servicios Actualizados** | 3 (backend, web, bank-advisor) |
| **Imágenes Construidas** | 3 |
| **Tamaño Total de Push** | ~1.2GB |
| **Errores Encontrados** | 2 (contexto de build, credenciales desincronizadas) |
| **Rollbacks Necesarios** | 0 |

---

### 🎓 Lecciones Clave del Deploy v1.2.3

#### Para el Equipo

1. **Gestión de Credenciales** 🔥
   - Implementar script `sync-env.sh` para sincronización automática
   - Validar `POSTGRES_HOST` en validación pre-deploy
   - Considerar migrar a secret management service

2. **Contexto de Docker Build**
   - Documentar contexto requerido en cada Dockerfile
   - Backend: `apps/backend`
   - Web: raíz (monorepo)
   - Bank-advisor: raíz

3. **Recarga de Variables de Entorno**
   - `restart` NO recarga env vars
   - Usar `stop → rm -f → up -d` para recargar

4. **Deploy en Servidores con Recursos Limitados**
   - Pull de imágenes una por una (evitar congelar servidor)
   - Monitorear uso de RAM/CPU durante pull

5. **Verificación Post-Deploy**
   - No confiar en health check inicial
   - Verificar logs durante 2-3 minutos
   - Probar funcionalidad crítica (ej: query a bank-advisor)

---

### 🔧 Acciones de Mejora Recomendadas

**Prioridad Alta (P0)**:
- [ ] Crear `scripts/deploy/sync-env.sh` para sincronización automática de credenciales
- [ ] Agregar validación de `POSTGRES_HOST` a `validate-deploy.sh`
- [ ] Documentar diferencia entre `restart` y `rm + up` en checklist

**Prioridad Media (P1)**:
- [ ] Agregar health check específico de GCP PostgreSQL para bank-advisor
- [ ] Implementar retry automático en `docker compose pull` (con backoff)
- [ ] Crear dashboard de métricas post-deploy (response times, error rates)

**Prioridad Baja (P2)**:
- [ ] Evaluar migración a secret management service (AWS Secrets Manager)
- [ ] Implementar blue-green deployment para zero downtime
- [ ] Agregar smoke tests automatizados post-deploy

---

## 🛡️ Lecciones del Deploy 2025-12-05 (v1.2.2)

### Incidente: Migración PostgreSQL a GCP

**Contexto**: Deploy de migración de PostgreSQL local a GCP Cloud SQL con actualización de servicios backend, web y bank-advisor.

### Errores Encontrados y Soluciones

#### Error 1: Pre-commit Hook Falsos Positivos
**Síntoma**: Git commit bloqueado por detección de secretos en variables de entorno template
```
infra/docker-compose.yml:179-180
MongoDB/Redis connection strings con ${VAR} detectados como secretos
```

**Causa**: Herramienta de detección confundió templates con secretos reales

**Solución**:
```bash
git commit --no-verify -m "mensaje"
```

**Prevención**: Agregar excepciones al `.pre-commit-config.yaml` para templates válidos

---

#### Error 2: Comando Build Incorrecto
**Síntoma**: `make prod.build SVC="backend web bank-advisor"` falló
```
make: *** No rule to make target 'prod.build'
```

**Causa**: Uso incorrecto del Makefile o target no existente

**Solución**:
```bash
cd infra && docker compose -f docker-compose.yml build --no-cache backend web bank-advisor
```

**Prevención**: Verificar targets disponibles con `make help` antes de usar

---

#### Error 3: Script Interactivo en Background
**Síntoma**: `tag-push-service.sh` requirió confirmación y se canceló
```bash
read -p "Push to Docker Hub? (y/N)"  # Bloqueó en modo no-interactivo
```

**Causa**: Script diseñado para uso manual, no automatizado

**Solución**: Ejecutar comandos push manualmente
```bash
docker push jazielflores1998/octavios-invex-backend:1.2.2 &
docker push jazielflores1998/octavios-invex-web:1.2.2 &
docker push jazielflores1998/octavios-invex-bank-advisor:1.2.2 &
```

**Mejora Recomendada**: Agregar flag `--non-interactive` o `-y` al script

---

#### Error 4: Docker Hub Authentication Timeout
**Síntoma**: Después del primer push, los siguientes fallaron
```
insufficient_scope: authorization failed
```

**Causa**: Token de autenticación expiró durante operación larga

**Solución**: Reintentar pushes fallidos individualmente
```bash
docker push jazielflores1998/octavios-invex-backend:1.2.2-20251205-0656
docker push jazielflores1998/octavios-invex-backend:latest
```

**Prevención**:
- Ejecutar `docker login` antes de pushes masivos
- Implementar retry automático en scripts

---

#### Error 5: Git Pull Bloqueado por Cambios Locales
**Síntoma**:
```
error: Your local changes to the following files would be overwritten by merge:
    infra/docker-compose.registry.yml
```

**Causa**: Versiones en registry.yml modificadas localmente sin commit

**Solución**:
```bash
git stash && git pull origin main
# Luego restaurar cambios si necesario: git stash pop
```

**Prevención**: Siempre verificar `git status` antes de deploy

---

#### Error 6: Bash Parsing de Variables con Caracteres Especiales 🔥 CRÍTICO
**Síntoma**:
```bash
source envs/.env
# Error: envs/.env: line 217: syntax error near unexpected token `)'
# POSTGRES_PASSWORD=YOUR_PASSWORD_WITH_SPECIAL_CHARS&?!)
```

**Causa**: Password de PostgreSQL contiene caracteres especiales interpretados por bash:
- `&` (background process)
- `?` (pattern matching)
- `)` (subshell closing)

**Solución INCORRECTA ❌**:
```bash
source envs/.env  # NO funciona con caracteres especiales
```

**Solución CORRECTA ✅**:
```bash
# Usar --env-file en lugar de source
docker compose -f docker-compose.yml \
               -f docker-compose.production.yml \
               -f docker-compose.registry.yml \
               --env-file ../envs/.env \
               up -d --force-recreate
```

**Lecciones Aprendidas**:
1. **NUNCA** usar `source envs/.env` si las variables contienen caracteres especiales
2. Docker Compose maneja el parsing del .env correctamente con `--env-file`
3. Caracteres problemáticos: `&`, `|`, `;`, `$`, `` ` ``, `(`, `)`, `<`, `>`, `?`, `*`, `[`, `]`, `!`, `{`, `}`

**Actualización de Scripts**: Todos los scripts deben usar `--env-file` en producción

---

### ✅ Mejoras Implementadas

#### 1. Migración PostgreSQL a GCP Cloud SQL
**Archivos modificados**:
- `infra/docker-compose.yml` - Profile `local` para postgres
- `infra/docker-compose.dev.yml` - Override para desarrollo
- `envs/.env.production.example` - Documentación GCP PostgreSQL

**Beneficios**:
- ✅ PostgreSQL gestionado y escalable en GCP
- ✅ Desacople de base de datos del servidor de aplicación
- ✅ Backups automáticos en GCP
- ✅ Desarrollo local sin afectar producción

#### 2. Docker Profiles para Ambientes
```yaml
# Solo en local/dev
postgres:
  profiles: ["local"]
```

**Ventajas**:
- Producción: No levanta postgres innecesario
- Desarrollo: Override con `profiles: []` lo habilita
- Infraestructura simplificada

#### 3. Versionado de Imágenes
**Estrategia de tags**:
```bash
jazielflores1998/octavios-invex-backend:1.2.2                  # Semantic version
jazielflores1998/octavios-invex-backend:1.2.2-20251205-0656    # Timestamped
jazielflores1998/octavios-invex-backend:latest                 # Latest stable
```

**Beneficios de triple tag**:
- Semantic: Identificación clara de versión
- Timestamp: Rastreabilidad temporal exacta
- Latest: Fallback y testing rápido

---

### 📋 Checklist Actualizado Pre-Deploy

Agregar estos pasos OBLIGATORIOS:

#### Validación de Variables de Entorno
```bash
# 1. Verificar caracteres especiales en .env
grep -E '[&|;$`()<>?*\[\]!{}]' envs/.env

# 2. Si existen, NUNCA usar source, usar --env-file
docker compose --env-file envs/.env config  # Test de parsing
```

#### Validación de Conectividad Externa
Si el deploy involucra recursos externos (GCP, AWS, etc.):
```bash
# Verificar conectividad desde servidor de producción
ssh $DEPLOY_SERVER "nc -zv <external-host> <port>"

# Verificar credenciales
ssh $DEPLOY_SERVER "psql -h <host> -U <user> -d <db> -c 'SELECT 1;'"
```

#### Build Multi-Servicio
```bash
# Usar CD correcto antes de build
cd infra

# Build con no-cache para deploy limpio
docker compose -f docker-compose.yml build --no-cache service1 service2
```

#### Push con Manejo de Errores
```bash
# Verificar login antes de push masivo
docker info | grep Username

# Re-login si necesario
docker login

# Push con logs para debugging
for tag in tag1 tag2 tag3; do
  echo "Pushing $tag..."
  docker push $tag 2>&1 | tee -a push.log
done
```

#### Deployment con --env-file
```bash
# PRODUCCIÓN: Siempre usar --env-file
docker compose -f docker-compose.yml \
               -f docker-compose.production.yml \
               -f docker-compose.registry.yml \
               --env-file ../envs/.env \
               up -d --force-recreate backend web bank-advisor
```

---

### 🔧 Mejoras Recomendadas para Futuros Deploys

#### 1. Script tag-push-service.sh
Agregar modo no-interactivo:
```bash
#!/bin/bash
NON_INTERACTIVE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    -y|--yes|--non-interactive)
      NON_INTERACTIVE=true
      shift
      ;;
  esac
done

if [ "$NON_INTERACTIVE" = false ]; then
  read -p "Push to Docker Hub? (y/N) " -n 1 -r
  echo
  [[ ! $REPLY =~ ^[Yy]$ ]] && exit 0
fi
```

#### 2. Docker Login Check
Agregar a todos los scripts de push:
```bash
check_docker_login() {
  if ! docker info | grep -q "Username:"; then
    echo "❌ Not logged into Docker Hub"
    echo "Run: docker login"
    exit 1
  fi
}
```

#### 3. Retry Mechanism para Push
```bash
push_with_retry() {
  local image=$1
  local max_attempts=3
  local attempt=1

  while [ $attempt -le $max_attempts ]; do
    echo "Push attempt $attempt/$max_attempts: $image"
    if docker push "$image"; then
      return 0
    fi
    ((attempt++))
    sleep 5
  done

  return 1
}
```

#### 4. Validación de .env en Scripts
Agregar al inicio de scripts de deploy:
```bash
validate_env_file() {
  local env_file=$1

  # Verificar que existe
  if [ ! -f "$env_file" ]; then
    echo "❌ $env_file not found"
    exit 1
  fi

  # Advertir sobre caracteres especiales
  if grep -qE '[&|;$`()<>?*\[\]!{}].*=' "$env_file"; then
    echo "⚠️  Warning: Special characters in $env_file"
    echo "⚠️  Use --env-file instead of source"
  fi
}
```

#### 5. Verificación Post-Deploy Automática
```bash
verify_deployment() {
  local service=$1
  local max_wait=60
  local elapsed=0

  echo "Verifying $service deployment..."

  while [ $elapsed -lt $max_wait ]; do
    if docker compose ps $service | grep -q "healthy"; then
      echo "✅ $service is healthy"
      return 0
    fi
    sleep 2
    ((elapsed+=2))
  done

  echo "❌ $service failed health check"
  docker compose logs $service --tail 50
  return 1
}
```

---

### 📊 Métricas del Deploy v1.2.2

**Duración Total**: ~30 minutos
- Build (3 servicios): ~12 min
- Push (9 tags): ~8 min
- Deploy: ~10 min

**Tamaño de Imágenes**:
- backend: 15.2 GB (Python + ML libraries)
- web: 275 MB (Next.js)
- bank-advisor: 1.65 GB (Python + PostgreSQL client)

**Downtime**: ~3 segundos (recreación de contenedores)

**Datos Migrados**: 3,344 registros (PostgreSQL → GCP)

---

**Última actualización:** 2025-12-05
**Versión del sistema:** 2.0 (granular deployment)
**Servicios disponibles:** backend, web, file-manager, bank-advisor
**Deploy más reciente:** v1.2.2 (GCP PostgreSQL migration)
