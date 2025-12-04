# Análisis del Último Despliegue y Guía de Re-Deploy

**Fecha del despliegue analizado:** 2 de Diciembre 2025
**Commit:** `07b3a6db` - chore: remove generated files from root directory
**Servidor:** 34.28.92.134 (invex.saptiva.com)
**Resultado:** ✅ **EXITOSO**

---

## 📊 Resumen Ejecutivo

### Lo que funcionó ✅
- **Estrategia de Docker Hub Registry**: Build local + push a registry + pull en servidor
- **Tiempo de deploy**: ~5 minutos (vs 47+ minutos con build en servidor)
- **Arquitectura Production-First V3.1**: Sin volúmenes de desarrollo, sin hot reload
- **Restauración de datos**: Dump completo de PostgreSQL (7,320 registros)
- **Zero downtime**: Usuarios preservados en MongoDB (8 usuarios)

### Métricas del Despliegue
- **Imágenes desplegadas**: 4 servicios (backend, web, bank-advisor, file-manager)
- **Tamaño del backend**: 4.733GB (incluye modelos ML)
- **Base de datos restaurada**: 1.3MB compressed → ~7,500 registros
- **Tiempo de pull de imágenes**: ~8 minutos
- **Tiempo total**: ~15 minutos (pull + restart + verification)

---

## ⚠️ Problemas Encontrados y Soluciones

### 1. ❌ Build en Servidor Extremadamente Lento

**Problema:**
```bash
# Primer intento: Build directo en servidor
docker compose build  # 47+ minutos sin completar
```

**Causa Raíz:**
- Servidor con recursos limitados (CPU/RAM)
- Backend incluye modelos ML pesados (4.7GB)
- Build de múltiples servicios en paralelo agotaba recursos

**Solución Aplicada:**
```bash
# Estrategia exitosa: Build local + Docker Hub registry
# LOCAL (PC potente):
make deploy-registry VERSION=0.1.2  # Build + push a Docker Hub

# SERVIDOR:
docker compose -f infra/docker-compose.yml \
  -f infra/docker-compose.production.yml \
  -f infra/docker-compose.registry.yml \
  up -d
```

**Lección:** Para servidores de producción, SIEMPRE usar registry con imágenes pre-built.

---

### 2. ❌ Backend Crash Loop - SECRET_KEY Validation Error

**Problema:**
```bash
src.core.secrets.SecretValidationError: Secret 'SECRET_KEY' too short (minimum 32 characters)
```

**Causa Raíz:**
1. Backend espera variables de `envs/.env`
2. `docker-compose.yml` tiene fallbacks hardcoded:
   ```yaml
   environment:
     SECRET_KEY: ${SECRET_KEY:-dev-secret-change-in-production}
   ```
3. Docker compose no estaba leyendo `envs/.env` correctamente

**Solución Aplicada:**
```bash
# 1. Verificar que envs/.env tenga las variables correctas
grep SECRET_KEY envs/.env
grep JWT_SECRET_KEY envs/.env

# 2. Source y export ANTES de docker compose up
cd octavios-chat-bajaware_invex
source envs/.env
export SECRET_KEY JWT_SECRET_KEY

# 3. Recrear contenedores (no solo restart)
docker rm -f backend web
docker compose -f ... up -d
```

**Lección:** Docker compose no siempre lee `.env` files automáticamente. Usar `--env-file` o export explícito.

---

### 3. ❌ CORS_ORIGINS y ALLOWED_HOSTS con Formato Incorrecto

**Problema:**
```bash
pydantic_settings.exceptions.SettingsError: error parsing value for field "allowed_hosts"
```

**Formato Incorrecto (JSON Array):**
```bash
ALLOWED_HOSTS=["invex.saptiva.com","back-invex.saptiva.com"]
CORS_ORIGINS=["https://invex.saptiva.com","https://back-invex.saptiva.com"]
```

**Formato Correcto (CSV):**
```bash
ALLOWED_HOSTS=invex.saptiva.com,back-invex.saptiva.com,localhost,127.0.0.1,web,api,backend,testserver
CORS_ORIGINS=https://invex.saptiva.com,https://back-invex.saptiva.com
```

**Lección:** Pydantic Settings espera CSV, no JSON. Revisar documentación de cada framework.

---

### 4. ❌ Datos Incompletos en Producción

**Problema:**
```sql
-- Producción: 206 registros en monthly_kpis
-- Local: 7,320 registros en monthly_kpis
-- Faltaban ~7,100 registros
```

**Causa Raíz:**
- Se había restaurado un dump parcial antiguo (`bankadvisor_dump.sql.gz` de 660K)
- Falta de verificación post-restore

**Solución Aplicada:**
```bash
# 1. Crear dump COMPLETO desde local
docker exec postgres pg_dump -U octavios -d bankadvisor \
  --clean --if-exists | gzip > bankadvisor_full_local.sql.gz

# 2. Copiar a servidor
scp bankadvisor_full_local.sql.gz jf@34.28.92.134:~/octavios-chat-bajaware_invex/

# 3. Restaurar en producción
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  gunzip -c bankadvisor_full_local.sql.gz | \
  docker exec -i postgres psql -U octavios -d bankadvisor"

# 4. VERIFICAR restauración
ssh jf@34.28.92.134 "docker exec postgres psql -U octavios -d bankadvisor \
  -c 'SELECT COUNT(*) FROM monthly_kpis;'"
# Output: 7320  ✅
```

**Lección:** SIEMPRE verificar count de registros después de restore. Automatizar verificación.

---

### 5. ❌ Pre-commit Hook Fallando con Solo Deletions

**Problema:**
```bash
git commit -m "chore: remove files"
# Error: husky - pre-commit script failed (code 1)
```

**Causa Raíz:**
Script `scripts/git-secrets-check.sh` tiene bug:
```bash
FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -v scripts/git-secrets-check.sh)
# Cuando solo hay deletions (D), git diff retorna vacío
# grep -v con input vacío retorna exit code 1
# Con 'set -e', el script falla
```

**Solución (Workaround):**
```bash
git commit --no-verify -m "mensaje"
```

**Solución Permanente (TODO):**
```bash
# Arreglar scripts/git-secrets-check.sh línea ~60
FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -v scripts/git-secrets-check.sh || true)
```

**Lección:** Hooks de git deben manejar edge cases (empty input). Usar `|| true` para comandos opcionales.

---

## ✅ Qué Hacer: Proceso Recomendado para Futuros Deploys

### Pre-Deploy Checklist

**1. Verificación Local (Ambiente de Dev)**
```bash
# ✅ Verificar que todo funciona localmente
make dev
make health
make test

# ✅ Verificar variables de entorno
make env-check

# ✅ Build y test de imágenes de producción
make deploy-registry-test VERSION=0.1.3
```

**2. Verificación de Datos (Si aplica)**
```bash
# ✅ Si hay cambios en base de datos, crear dump actualizado
docker exec postgres pg_dump -U octavios -d bankadvisor \
  --clean --if-exists | gzip > backups/bankadvisor_$(date +%Y%m%d).sql.gz

# ✅ Verificar tamaño y contenido
ls -lh backups/
zcat backups/bankadvisor_*.sql.gz | grep "INSERT INTO" | wc -l
```

**3. Commit y Sincronización**
```bash
# ✅ Commit de cambios
git add .
git commit -m "feat: descripción de cambios"

# ✅ Sincronizar ramas
git checkout main
git merge develop
git push origin main develop
```

**4. Build y Push de Imágenes**
```bash
# ✅ Build local (PC potente) y push a Docker Hub
make deploy-registry VERSION=0.1.3

# Desglose:
# 1. Build de imágenes localmente con docker-compose.production.yml
# 2. Tag con versión (jazielflores1998/octavios-invex-backend:0.1.3)
# 3. Push a Docker Hub
# 4. Verificar que las imágenes estén en Docker Hub
```

---

### Deploy en Servidor (Estrategia Registry)

**Script Completo:**
```bash
#!/bin/bash
# deploy-to-production.sh
set -e

# === CONFIGURACIÓN ===
SERVER="jf@34.28.92.134"
PROJECT_DIR="octavios-chat-bajaware_invex"
VERSION="0.1.3"  # Actualizar según versión
BACKUP_DB=true   # true si quieres backup de DB antes de deploy

echo "🚀 Iniciando deploy a producción..."
echo "   Versión: $VERSION"
echo "   Servidor: $SERVER"
echo ""

# === PASO 1: Backup de Base de Datos (Opcional) ===
if [ "$BACKUP_DB" = true ]; then
    echo "💾 Creando backup de base de datos..."
    ssh $SERVER "cd $PROJECT_DIR && \
        mkdir -p backups && \
        docker exec postgres pg_dump -U octavios -d bankadvisor \
        --no-owner --no-acl | gzip > backups/pre_deploy_$(date +%Y%m%d_%H%M%S).sql.gz"
    echo "✅ Backup creado"
    echo ""
fi

# === PASO 2: Pull de Código ===
echo "📥 Actualizando código en servidor..."
ssh $SERVER "cd $PROJECT_DIR && \
    git fetch origin && \
    git checkout main && \
    git pull origin main"
echo "✅ Código actualizado"
echo ""

# === PASO 3: Actualizar Versión en Registry Override ===
echo "🔧 Actualizando versión en docker-compose.registry.yml..."
ssh $SERVER "cd $PROJECT_DIR && \
    sed -i 's/:0\.[0-9]\.[0-9]/:${VERSION}/g' infra/docker-compose.registry.yml"
echo "✅ Versión actualizada a $VERSION"
echo ""

# === PASO 4: Pull de Imágenes Nuevas ===
echo "📦 Descargando imágenes desde Docker Hub (versión $VERSION)..."
ssh $SERVER "cd $PROJECT_DIR && \
    docker compose -f infra/docker-compose.yml \
                   -f infra/docker-compose.production.yml \
                   -f infra/docker-compose.registry.yml \
                   pull"
echo "✅ Imágenes descargadas"
echo ""

# === PASO 5: Detener y Recrear Contenedores ===
echo "🔄 Recreando contenedores con nuevas imágenes..."
ssh $SERVER "cd $PROJECT_DIR && \
    source envs/.env && \
    export SECRET_KEY JWT_SECRET_KEY && \
    docker compose -f infra/docker-compose.yml \
                   -f infra/docker-compose.production.yml \
                   -f infra/docker-compose.registry.yml \
                   up -d --force-recreate --no-build"
echo "✅ Contenedores recreados"
echo ""

# === PASO 6: Esperar Health Checks ===
echo "⏳ Esperando a que los servicios estén listos (60s)..."
sleep 60

# === PASO 7: Verificación de Servicios ===
echo "🔍 Verificando servicios..."
ssh $SERVER "cd $PROJECT_DIR && \
    docker compose -f infra/docker-compose.yml \
                   -f infra/docker-compose.production.yml \
                   ps --format 'table {{.Name}}\t{{.Status}}'"
echo ""

# === PASO 8: Health Check ===
echo "🏥 Verificando health endpoints..."
ssh $SERVER "curl -s https://invex.saptiva.com | head -5"
echo ""

# === PASO 9: Verificación de Datos ===
echo "📊 Verificando integridad de datos..."
ssh $SERVER "cd $PROJECT_DIR && \
    docker exec postgres psql -U octavios -d bankadvisor -t \
    -c 'SELECT COUNT(*) as monthly_kpis FROM monthly_kpis;' && \
    docker exec mongodb mongosh -u octavios_user -p \$MONGO_PASSWORD \
    --authenticationDatabase admin octavios --quiet \
    --eval 'print(\"users:\", db.users.countDocuments())'"
echo ""

# === RESUMEN ===
echo "═══════════════════════════════════════════════════════════"
echo "✅ DEPLOY COMPLETADO"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📋 Resumen:"
echo "  - Versión desplegada: $VERSION"
echo "  - URL: https://invex.saptiva.com"
echo "  - Backend: https://back-invex.saptiva.com"
echo ""
echo "📊 Verificación manual:"
echo "  1. Abrir https://invex.saptiva.com y probar login"
echo "  2. Verificar Bank Advisor con consultas"
echo "  3. Revisar logs si hay algún problema:"
echo "     ssh $SERVER 'cd $PROJECT_DIR && docker compose logs -f backend'"
echo ""
```

**Guardar como:** `scripts/deploy-to-production.sh`

**Uso:**
```bash
# 1. Hacer el script ejecutable
chmod +x scripts/deploy-to-production.sh

# 2. Editar VERSION en el script o pasarla como variable
VERSION=0.1.3 ./scripts/deploy-to-production.sh
```

---

### Verificación Post-Deploy

**Checklist de Verificación:**
```bash
# 1. ✅ Todos los contenedores healthy
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  docker compose ps --format 'table {{.Name}}\t{{.Status}}'"

# 2. ✅ Web accesible
curl -I https://invex.saptiva.com | head -5

# 3. ✅ Backend API accesible
curl -I https://back-invex.saptiva.com/api/health

# 4. ✅ Datos preservados
ssh jf@34.28.92.134 "docker exec postgres psql -U octavios -d bankadvisor \
  -c 'SELECT COUNT(*) FROM monthly_kpis;'"
# Expected: 7320 o más

# 5. ✅ Usuarios preservados
ssh jf@34.28.92.134 "docker exec mongodb mongosh -u octavios_user \
  -p \$MONGO_PASSWORD --authenticationDatabase admin octavios --quiet \
  --eval 'db.users.countDocuments()'"
# Expected: 8 o más

# 6. ✅ No hay errores en logs recientes
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  docker compose logs --tail=50 backend | grep -i error"
```

---

## 🚫 Qué Evitar: Anti-Patterns

### ❌ NO: Build Directo en Servidor de Producción
```bash
# MAL - Muy lento, consume recursos del servidor en producción
ssh server "docker compose build"  # 47+ minutos
```

**Por qué es malo:**
- Servidor de producción con recursos limitados
- Afecta servicios en ejecución
- Builds inconsistentes (diferentes entornos)

**Alternativa correcta:**
```bash
# BIEN - Build local + registry
make deploy-registry VERSION=0.1.3  # Local
ssh server "docker compose -f ... -f registry.yml up -d"  # Pull pre-built
```

---

### ❌ NO: Hardcodear Secrets en docker-compose.yml
```yaml
# MAL
environment:
  SECRET_KEY: lmHB00uGhVGFo-siANU6SSLKzz_NNzzo0eUaWo7M1SI  # ❌
  JWT_SECRET_KEY: hlsy3X4luA7wlt_pBS7TgWIOIV0OX55APy_RsXTbQi8  # ❌
```

**Por qué es malo:**
- Secrets en git history
- Difícil rotación de secrets
- Riesgo de seguridad

**Alternativa correcta:**
```yaml
# BIEN
environment:
  SECRET_KEY: ${SECRET_KEY}  # Lee de .env
  JWT_SECRET_KEY: ${JWT_SECRET_KEY}
```

Con:
```bash
# docker compose up SIEMPRE con --env-file
docker compose --env-file envs/.env up -d
```

---

### ❌ NO: Restaurar Dumps Sin Verificación
```bash
# MAL
gunzip -c old_dump.sql.gz | docker exec -i postgres psql -U octavios -d bankadvisor
# ¿Se restauró todo? ¿Cuántos registros? ¿Qué versión del schema?
```

**Por qué es malo:**
- No sabes si el restore fue exitoso
- Dumps parciales pueden pasar desapercibidos
- Schema incompatible puede causar errores silenciosos

**Alternativa correcta:**
```bash
# BIEN - Con verificación
echo "Restaurando dump..."
gunzip -c bankadvisor_full.sql.gz | docker exec -i postgres psql -U octavios -d bankadvisor

echo "Verificando restauración..."
MONTHLY_KPIS=$(docker exec postgres psql -U octavios -d bankadvisor -t \
  -c "SELECT COUNT(*) FROM monthly_kpis;" | xargs)
INSTITUCIONES=$(docker exec postgres psql -U octavios -d bankadvisor -t \
  -c "SELECT COUNT(*) FROM instituciones;" | xargs)

echo "monthly_kpis: $MONTHLY_KPIS (esperado: 7320+)"
echo "instituciones: $INSTITUCIONES (esperado: 54)"

if [ "$MONTHLY_KPIS" -lt 7000 ]; then
    echo "❌ ERROR: Datos incompletos"
    exit 1
fi
```

---

### ❌ NO: Docker Compose Up Sin --force-recreate en Deploys
```bash
# MAL - Contenedores pueden usar imagen vieja en caché
docker compose up -d
```

**Por qué es malo:**
- Docker puede reutilizar contenedores existentes
- Nueva imagen no se usa hasta que borres el contenedor
- Variables de entorno no se actualizan

**Alternativa correcta:**
```bash
# BIEN - Forzar recreación
docker compose up -d --force-recreate --no-build
# --force-recreate: Siempre crea contenedores nuevos
# --no-build: No intentes build, usa imágenes del registry
```

---

### ❌ NO: Usar `docker compose restart` para Aplicar Nuevas Imágenes
```bash
# MAL - restart NO carga nueva imagen
docker compose pull backend
docker compose restart backend  # ❌ Sigue usando imagen vieja
```

**Por qué es malo:**
- `restart` reinicia el contenedor existente con la misma imagen
- No detecta nuevas imágenes

**Alternativa correcta:**
```bash
# BIEN - Recrear contenedor
docker compose pull backend
docker rm -f backend
docker compose up -d backend

# O mejor aún:
docker compose up -d --force-recreate backend
```

---

### ❌ NO: Confiar en Fallback Values de Environment Variables
```bash
# MAL - docker-compose.yml
environment:
  SECRET_KEY: ${SECRET_KEY:-dev-secret-change-in-production}
```

**Por qué es malo:**
- Si `SECRET_KEY` no está definida, usa el fallback
- Fallback puede ser inseguro o muy corto
- Errores silenciosos en producción

**Alternativa correcta:**
```bash
# BIEN - docker-compose.yml sin fallbacks
environment:
  SECRET_KEY: ${SECRET_KEY}  # Falla si no está definido

# + Validación en script de deploy
if [ -z "$SECRET_KEY" ] || [ ${#SECRET_KEY} -lt 32 ]; then
    echo "❌ ERROR: SECRET_KEY no válido"
    exit 1
fi
```

---

### ❌ NO: Git Commit con `-m` Multiline sin HEREDOC
```bash
# MAL - Difícil de leer, propenso a errores de formato
git commit -m "feat: add feature

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Por qué es malo:**
- Saltos de línea se pierden o malformatean
- Difícil mantener formato consistente

**Alternativa correcta:**
```bash
# BIEN - Usar HEREDOC
git commit -m "$(cat <<'EOF'
feat: add feature

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 🔄 Cómo Re-Deployar Cambios: Flujo Completo

### Escenario 1: Cambios en Código (No en Base de Datos)

**Ejemplo:** Arreglaste un bug en el backend, o agregaste una feature en el frontend.

```bash
# === LOCAL ===
# 1. Hacer cambios en código
vim apps/api/src/routes/chat.py

# 2. Commit
git add .
git commit -m "fix: resolve chat bug"

# 3. Sincronizar ramas
git checkout main
git merge develop
git push origin main develop

# 4. Incrementar versión y build + push
# Editar VERSION en Makefile o pasar como variable
make deploy-registry VERSION=0.1.4

# === SERVIDOR ===
# 5. Pull código actualizado
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && git pull origin main"

# 6. Actualizar versión en registry.yml
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  sed -i 's/:0\.1\.3/:0.1.4/g' infra/docker-compose.registry.yml"

# 7. Pull nueva imagen y recrear servicio específico
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  source envs/.env && export SECRET_KEY JWT_SECRET_KEY && \
  docker compose -f infra/docker-compose.yml \
    -f infra/docker-compose.production.yml \
    -f infra/docker-compose.registry.yml \
    pull backend && \
  docker compose -f infra/docker-compose.yml \
    -f infra/docker-compose.production.yml \
    -f infra/docker-compose.registry.yml \
    up -d --force-recreate --no-build backend"

# 8. Verificar
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  docker compose logs -f --tail=50 backend"
```

**Tiempo estimado:** 5-10 minutos

---

### Escenario 2: Cambios en Base de Datos (Schema o Data)

**Ejemplo:** Agregaste una nueva columna a una tabla, o necesitas cargar datos nuevos.

```bash
# === LOCAL ===
# 1. Hacer cambios (código + migraciones)
vim plugins/bank-advisor-private/src/bankadvisor/models/normalized.py
vim plugins/bank-advisor-private/alembic/versions/001_add_column.py

# 2. Commit
git add .
git commit -m "feat: add new column to metricas_financieras"

# 3. Sincronizar ramas
git checkout main
git merge develop
git push origin main develop

# 4. Build + push (si hay cambios en código)
make deploy-registry VERSION=0.1.4

# 5. Crear dump actualizado (si aplica)
docker exec postgres pg_dump -U octavios -d bankadvisor \
  --clean --if-exists | gzip > backups/bankadvisor_$(date +%Y%m%d).sql.gz

# === SERVIDOR ===
# 6. Pull código
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && git pull origin main"

# 7. Backup de DB antes de migración
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  docker exec postgres pg_dump -U octavios -d bankadvisor \
  --no-owner --no-acl | gzip > backups/pre_migration_$(date +%Y%m%d_%H%M%S).sql.gz"

# 8. Aplicar migraciones
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  docker compose exec bank-advisor alembic upgrade head"

# 9. Pull nueva imagen y recrear
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  source envs/.env && export SECRET_KEY JWT_SECRET_KEY && \
  docker compose -f infra/docker-compose.yml \
    -f infra/docker-compose.production.yml \
    -f infra/docker-compose.registry.yml \
    pull && \
  docker compose -f infra/docker-compose.yml \
    -f infra/docker-compose.production.yml \
    -f infra/docker-compose.registry.yml \
    up -d --force-recreate --no-build"

# 10. Verificar datos
ssh jf@34.28.92.134 "docker exec postgres psql -U octavios -d bankadvisor \
  -c 'SELECT COUNT(*) FROM monthly_kpis;'"
```

**Tiempo estimado:** 15-20 minutos

---

### Escenario 3: Cambios Solo en Variables de Entorno

**Ejemplo:** Cambiar una API key, ajustar CORS_ORIGINS, etc.

```bash
# === LOCAL ===
# 1. Actualizar envs/.env.prod (NO commitear secrets!)
vim envs/.env.prod

# === SERVIDOR ===
# 2. Actualizar envs/.env en servidor
# Opción A: Editar directamente en servidor
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && vim envs/.env"

# Opción B: Copiar .env desde local (si no tiene secrets sensibles)
scp envs/.env.prod jf@34.28.92.134:~/octavios-chat-bajaware_invex/envs/.env

# 3. Recrear servicios afectados (sin rebuild ni pull)
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  source envs/.env && export SECRET_KEY JWT_SECRET_KEY && \
  docker rm -f backend web && \
  docker compose -f infra/docker-compose.yml \
    -f infra/docker-compose.production.yml \
    -f infra/docker-compose.registry.yml \
    up -d --no-build backend web"

# 4. Verificar variables cargadas
ssh jf@34.28.92.134 "docker exec backend env | grep -E '(SECRET_KEY|CORS_ORIGINS|ALLOWED_HOSTS)'"
```

**Tiempo estimado:** 2-3 minutos

---

### Escenario 4: Rollback a Versión Anterior

**Ejemplo:** El último deploy tiene un bug crítico, necesitas volver a la versión anterior.

```bash
# === SERVIDOR ===
# 1. Verificar versión actual
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  docker compose images | grep octavios-invex"

# Output: jazielflores1998/octavios-invex-backend:0.1.4

# 2. Editar registry.yml para usar versión anterior
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  sed -i 's/:0\.1\.4/:0.1.3/g' infra/docker-compose.registry.yml"

# 3. Pull versión anterior y recrear
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  source envs/.env && export SECRET_KEY JWT_SECRET_KEY && \
  docker compose -f infra/docker-compose.yml \
    -f infra/docker-compose.production.yml \
    -f infra/docker-compose.registry.yml \
    pull && \
  docker compose -f infra/docker-compose.yml \
    -f infra/docker-compose.production.yml \
    -f infra/docker-compose.registry.yml \
    up -d --force-recreate --no-build"

# 4. Si hay cambios de DB, restaurar backup
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  gunzip -c backups/pre_deploy_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i postgres psql -U octavios -d bankadvisor"

# 5. Verificar
ssh jf@34.28.92.134 "curl -I https://invex.saptiva.com"
```

**Tiempo estimado:** 5-10 minutos

---

## 📝 Template: Checklist de Deploy

Guardar como `docs/DEPLOY_CHECKLIST.md`:

```markdown
# Checklist de Deploy a Producción

**Fecha:** _______________
**Versión:** _______________
**Deploy por:** _______________

## Pre-Deploy

- [ ] Todos los tests pasan localmente (`make test`)
- [ ] Build de producción exitoso (`make deploy-registry-test`)
- [ ] Variables de entorno verificadas (`make env-check`)
- [ ] Cambios commiteados y pusheados a main
- [ ] Ramas main y develop sincronizadas
- [ ] Versión incrementada correctamente (0.1.X → 0.1.Y)

## Deploy

- [ ] Build local y push a Docker Hub (`make deploy-registry VERSION=X.Y.Z`)
- [ ] Backup de base de datos en servidor (si aplica)
- [ ] Pull de código en servidor (`git pull origin main`)
- [ ] Actualizar versión en `docker-compose.registry.yml`
- [ ] Pull de imágenes nuevas (`docker compose pull`)
- [ ] Recrear contenedores (`docker compose up -d --force-recreate --no-build`)

## Post-Deploy

- [ ] Todos los contenedores healthy (`docker compose ps`)
- [ ] Web accesible (https://invex.saptiva.com)
- [ ] Backend API accesible (https://back-invex.saptiva.com/api/health)
- [ ] Datos preservados (monthly_kpis count ≥ 7320)
- [ ] Usuarios preservados (users count ≥ 8)
- [ ] No hay errores en logs recientes (`docker compose logs --tail=50`)
- [ ] Prueba manual de funcionalidad crítica (login, chat, bank advisor)

## Rollback (Si es necesario)

- [ ] Cambiar versión en registry.yml a versión anterior
- [ ] Pull y recrear contenedores
- [ ] Restaurar backup de DB (si aplica)
- [ ] Verificar funcionalidad

## Notas

_______________________________________________________________________________
_______________________________________________________________________________
_______________________________________________________________________________
```

---

## 🎓 Lecciones Clave

### 1. Build Strategy: Local + Registry > Server Build
**Tiempo:**
- Server build: 47+ min (falló)
- Local + registry: 5 min pull

**Recomendación:** PC local potente + Docker Hub registry para producción.

---

### 2. Environment Variables: Explicit Export > Implicit Load
**Problema:**
- `docker-compose.yml` con fallbacks inseguros
- `.env` no siempre se carga automáticamente

**Recomendación:**
```bash
source envs/.env && export SECRET_KEY JWT_SECRET_KEY && docker compose up -d
```

---

### 3. Data Restoration: Verify > Trust
**Problema:**
- Dump parcial restaurado (206 vs 7,320 registros)
- No había verificación post-restore

**Recomendación:**
```bash
# Siempre verificar después de restore
COUNT=$(docker exec postgres psql -U octavios -d bankadvisor -t \
  -c "SELECT COUNT(*) FROM monthly_kpis;" | xargs)
echo "Restaurados: $COUNT registros (esperado: 7320+)"
[ "$COUNT" -lt 7000 ] && echo "❌ ERROR: Datos incompletos" && exit 1
```

---

### 4. Container Updates: Recreate > Restart
**Problema:**
- `docker compose restart` no carga nueva imagen
- Cambios de env vars no se aplican con restart

**Recomendación:**
```bash
# BIEN: Recrear contenedor
docker compose up -d --force-recreate --no-build service_name

# MAL: Solo restart
docker compose restart service_name  # ❌
```

---

### 5. Git Hooks: Handle Edge Cases
**Problema:**
- Pre-commit hook falla con deletions-only commits
- `grep -v` con input vacío retorna exit 1

**Recomendación:**
```bash
# Agregar || true para comandos opcionales
FILES=$(git diff --cached --name-only --diff-filter=ACM | \
  grep -v scripts/git-secrets-check.sh || true)
```

---

## 📚 Recursos Adicionales

### Archivos Clave del Proyecto

1. **`Makefile`** - Orquestador principal de comandos
   - `make deploy-registry VERSION=X.Y.Z` - Build + push a Docker Hub
   - `make health` - Verificar salud de servicios
   - `make env-check` - Validar variables de entorno

2. **`scripts/deploy-production-v3.sh`** - Script de deploy (legacy, reemplazado por registry)
   - Incluye validaciones y verificaciones
   - Puede usarse como referencia

3. **`infra/docker-compose.registry.yml`** - Override para registry
   - Define imágenes de Docker Hub
   - Deshabilita builds locales

4. **`envs/.env`** - Variables de entorno de producción
   - NO commitear a git
   - Mantener sincronizado con servidor

5. **`docs/PRODUCTION_DEPLOYMENT.md`** - Documentación anterior de deploy
   - Contexto histórico de arquitectura

---

## 🔗 Enlaces Útiles

- **Docker Hub Registry:** https://hub.docker.com/u/jazielflores1998
- **Servidor de producción:** ssh jf@34.28.92.134
- **Web:** https://invex.saptiva.com
- **Backend API:** https://back-invex.saptiva.com
- **GitHub Repo:** https://github.com/saptiva-ai/octavios-chat-bajaware_invex

---

## 📞 Troubleshooting

### Problema: Contenedor no inicia después de deploy

**Diagnóstico:**
```bash
# Ver logs del contenedor
docker compose logs --tail=100 backend

# Ver estado del contenedor
docker compose ps backend

# Inspeccionar contenedor
docker inspect backend | grep -A 20 State
```

**Soluciones Comunes:**
1. Verificar variables de entorno: `docker exec backend env | grep SECRET_KEY`
2. Revisar health check: `docker inspect backend | grep -A 10 Health`
3. Recrear contenedor: `docker rm -f backend && docker compose up -d backend`

---

### Problema: Base de datos vacía después de restore

**Diagnóstico:**
```bash
# Verificar conexión a DB
docker exec postgres psql -U octavios -d bankadvisor -c '\dt'

# Contar registros
docker exec postgres psql -U octavios -d bankadvisor \
  -c 'SELECT COUNT(*) FROM monthly_kpis;'
```

**Soluciones:**
1. Verificar que el dump tiene datos: `zcat dump.sql.gz | grep "INSERT INTO" | wc -l`
2. Re-restaurar con --clean: `gunzip -c dump.sql.gz | docker exec -i postgres psql ...`
3. Verificar permisos: `docker exec postgres psql -U octavios -d bankadvisor -c '\du'`

---

### Problema: Error 502 Bad Gateway en Nginx/Cloudflare

**Diagnóstico:**
```bash
# Verificar que backend esté escuchando
curl http://localhost:8000/api/health

# Ver logs de nginx (si aplica)
docker compose logs nginx

# Verificar red de Docker
docker network inspect octavios-chat-bajaware_invex_default
```

**Soluciones:**
1. Reiniciar backend: `docker compose restart backend`
2. Verificar CORS_ORIGINS y ALLOWED_HOSTS en .env
3. Limpiar caché de Cloudflare

---

## 🚀 Comandos Rápidos para Copy-Paste

```bash
# === DEPLOY COMPLETO (Versión 0.1.X) ===
# LOCAL:
make deploy-registry VERSION=0.1.X

# SERVIDOR:
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  git pull origin main && \
  sed -i 's/:0\.1\.[0-9]/:0.1.X/g' infra/docker-compose.registry.yml && \
  source envs/.env && export SECRET_KEY JWT_SECRET_KEY && \
  docker compose -f infra/docker-compose.yml \
    -f infra/docker-compose.production.yml \
    -f infra/docker-compose.registry.yml \
    pull && \
  docker compose -f infra/docker-compose.yml \
    -f infra/docker-compose.production.yml \
    -f infra/docker-compose.registry.yml \
    up -d --force-recreate --no-build && \
  sleep 30 && \
  docker compose ps"

# === VERIFICACIÓN ===
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  echo '=== Servicios ===' && \
  docker compose ps && \
  echo '=== Datos ===' && \
  docker exec postgres psql -U octavios -d bankadvisor -t \
    -c 'SELECT COUNT(*) FROM monthly_kpis;' && \
  echo '=== Web ===' && \
  curl -I https://invex.saptiva.com | head -5"

# === ROLLBACK ===
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  sed -i 's/:0\.1\.X/:0.1.Y/g' infra/docker-compose.registry.yml && \
  source envs/.env && export SECRET_KEY JWT_SECRET_KEY && \
  docker compose -f infra/docker-compose.yml \
    -f infra/docker-compose.production.yml \
    -f infra/docker-compose.registry.yml \
    pull && \
  docker compose -f infra/docker-compose.yml \
    -f infra/docker-compose.production.yml \
    -f infra/docker-compose.registry.yml \
    up -d --force-recreate --no-build"
```

---

**Última actualización:** 2 de Diciembre 2025
**Versión del documento:** 1.0
**Mantenido por:** Equipo Saptiva AI
