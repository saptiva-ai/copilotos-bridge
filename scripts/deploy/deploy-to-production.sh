#!/bin/bash
# ============================================================================
# PRODUCTION DEPLOY SCRIPT - REGISTRY STRATEGY
# ============================================================================
# Despliega a producción usando imágenes pre-built de Docker Hub
# Versión: 2.0 (Registry-based)
# ============================================================================
set -e

# === CONFIGURACIÓN ===
SERVER="${DEPLOY_SERVER}"
PROJECT_DIR="${DEPLOY_PROJECT_DIR:-octavios-chat-bajaware_invex}"
VERSION="${1:-}"  # Primer argumento o variable de entorno
BACKUP_DB="${BACKUP_DB:-true}"  # true/false para backup antes de deploy

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Funciones de logging
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; exit 1; }

# === VALIDACIÓN ===
if [ -z "$SERVER" ]; then
    log_error "DEPLOY_SERVER environment variable is required.

Example:
  export DEPLOY_SERVER='user@your-server-ip'
  $0 0.1.4

Or use: source scripts/deploy/load-env.sh prod"
fi

if [ -z "$VERSION" ]; then
    log_error "Versión requerida. Uso: $0 <VERSION>

Ejemplo: $0 0.1.4
O con variable: VERSION=0.1.4 $0"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "🚀 DEPLOY A PRODUCCIÓN - REGISTRY STRATEGY"
echo "════════════════════════════════════════════════════════════"
echo ""
log_info "Versión: $VERSION"
log_info "Servidor: $SERVER"
log_info "Directorio: $PROJECT_DIR"
log_info "Backup DB: $BACKUP_DB"
echo ""

# === VALIDACIÓN PRE-DEPLOY ===
log_info "Running pre-deployment validation..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/validate-deploy.sh" ]; then
    if ! "$SCRIPT_DIR/validate-deploy.sh" "$VERSION"; then
        log_error "Pre-deployment validation failed. Fix errors before deploying."
    fi
    log_success "Pre-deployment validation passed"
else
    log_warning "Validation script not found at $SCRIPT_DIR/validate-deploy.sh"
fi
echo ""

# Confirmar deploy
read -p "¿Continuar con el deploy? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warning "Deploy cancelado por el usuario"
    exit 0
fi

# === PASO 1: Backup de Base de Datos (Opcional) ===
if [ "$BACKUP_DB" = "true" ]; then
    echo ""
    log_info "Paso 1/9: Creando backup de base de datos..."
    ssh $SERVER "cd $PROJECT_DIR && \
        mkdir -p backups && \
        docker exec postgres pg_dump -U octavios -d bankadvisor \
        --no-owner --no-acl | gzip > backups/pre_deploy_$(date +%Y%m%d_%H%M%S).sql.gz" \
        && log_success "Backup creado" \
        || log_warning "No se pudo crear backup (puede ser primera instalación)"
else
    log_warning "Paso 1/9: Backup de DB deshabilitado"
fi

# === PASO 2: Pull de Código ===
echo ""
log_info "Paso 2/9: Actualizando código en servidor..."
ssh $SERVER "cd $PROJECT_DIR && \
    git fetch origin && \
    git checkout main && \
    git pull origin main" \
    && log_success "Código actualizado" \
    || log_error "Fallo al actualizar código"

# === PASO 3: Actualizar Versión en Registry Override ===
echo ""
log_info "Paso 3/9: Actualizando versión en docker-compose.registry.yml..."
ssh $SERVER "cd $PROJECT_DIR && \
    sed -i 's/:0\.[0-9]*\.[0-9]*/:${VERSION}/g' infra/docker-compose.registry.yml && \
    grep 'image:' infra/docker-compose.registry.yml | head -4" \
    && log_success "Versión actualizada a $VERSION" \
    || log_error "Fallo al actualizar versión"

# === PASO 4: Pull de Imágenes Nuevas ===
echo ""
log_info "Paso 4/9: Descargando imágenes desde Docker Hub (versión $VERSION)..."
log_warning "Esto puede tomar 5-10 minutos dependiendo del tamaño de las imágenes..."
ssh $SERVER "cd $PROJECT_DIR && \
    docker compose -f infra/docker-compose.yml \
                   -f infra/docker-compose.production.yml \
                   -f infra/docker-compose.registry.yml \
                   pull" \
    && log_success "Imágenes descargadas" \
    || log_error "Fallo al descargar imágenes"

# === PASO 5: Detener y Recrear Contenedores ===
echo ""
log_info "Paso 5/9: Recreando contenedores con nuevas imágenes..."
ssh $SERVER "cd $PROJECT_DIR && \
    source envs/.env && \
    export SECRET_KEY JWT_SECRET_KEY && \
    docker compose -f infra/docker-compose.yml \
                   -f infra/docker-compose.production.yml \
                   -f infra/docker-compose.registry.yml \
                   up -d --force-recreate --no-build" \
    && log_success "Contenedores recreados" \
    || log_error "Fallo al recrear contenedores"

# === PASO 6: Esperar Health Checks ===
echo ""
log_info "Paso 6/9: Esperando a que los servicios estén listos (60s)..."
for i in {1..6}; do
    echo -n "."
    sleep 10
done
echo ""
log_success "Servicios deberían estar listos"

# === PASO 7: Verificación de Servicios ===
echo ""
log_info "Paso 7/9: Verificando servicios..."
ssh $SERVER "cd $PROJECT_DIR && \
    docker compose -f infra/docker-compose.yml \
                   -f infra/docker-compose.production.yml \
                   ps --format 'table {{.Name}}\t{{.Status}}'"

# === PASO 8: Health Check ===
echo ""
log_info "Paso 8/9: Verificando health endpoints..."

# Web
WEB_STATUS=$(ssh $SERVER "curl -s -o /dev/null -w '%{http_code}' https://invex.saptiva.com" || echo "000")
if [ "$WEB_STATUS" = "200" ]; then
    log_success "Web OK (HTTP $WEB_STATUS)"
else
    log_warning "Web responde con HTTP $WEB_STATUS"
fi

# Backend API
API_STATUS=$(ssh $SERVER "curl -s -o /dev/null -w '%{http_code}' https://back-invex.saptiva.com/api/health" || echo "000")
if [ "$API_STATUS" = "200" ]; then
    log_success "Backend API OK (HTTP $API_STATUS)"
else
    log_warning "Backend API responde con HTTP $API_STATUS"
fi

# === PASO 9: Verificación de Datos ===
echo ""
log_info "Paso 9/9: Verificando integridad de datos..."

# PostgreSQL - monthly_kpis
MONTHLY_KPIS=$(ssh $SERVER "cd $PROJECT_DIR && \
    docker exec postgres psql -U octavios -d bankadvisor -t \
    -c 'SELECT COUNT(*) FROM monthly_kpis;' 2>/dev/null | xargs" || echo "0")

if [ "$MONTHLY_KPIS" -ge 7000 ]; then
    log_success "PostgreSQL OK - monthly_kpis: $MONTHLY_KPIS registros"
elif [ "$MONTHLY_KPIS" -gt 0 ]; then
    log_warning "PostgreSQL - monthly_kpis: $MONTHLY_KPIS registros (esperado: 7320+)"
else
    log_warning "PostgreSQL - No se pudo verificar datos"
fi

# MongoDB - users
USERS=$(ssh $SERVER "cd $PROJECT_DIR && \
    docker exec mongodb mongosh -u octavios_user -p \\\$MONGO_PASSWORD \
    --authenticationDatabase admin octavios --quiet \
    --eval 'db.users.countDocuments()' 2>/dev/null" || echo "0")

if [ "$USERS" -gt 0 ]; then
    log_success "MongoDB OK - users: $USERS usuarios"
else
    log_warning "MongoDB - No se pudo verificar usuarios"
fi

# === RESUMEN ===
echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ DEPLOY COMPLETADO"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📋 Resumen:"
echo "  - Versión desplegada: $VERSION"
echo "  - URL Web: https://invex.saptiva.com (HTTP $WEB_STATUS)"
echo "  - Backend API: https://back-invex.saptiva.com (HTTP $API_STATUS)"
echo "  - DB Records: $MONTHLY_KPIS monthly_kpis, $USERS users"
echo ""
echo "📊 Verificación manual recomendada:"
echo "  1. Abrir https://invex.saptiva.com y probar login"
echo "  2. Verificar Bank Advisor con consultas"
echo "  3. Revisar logs si hay algún problema:"
echo "     ssh $SERVER 'cd $PROJECT_DIR && docker compose logs -f backend'"
echo ""

# Advertencias si algo falló
WARNINGS=0
[ "$WEB_STATUS" != "200" ] && ((WARNINGS++))
[ "$API_STATUS" != "200" ] && ((WARNINGS++))
[ "$MONTHLY_KPIS" -lt 7000 ] && [ "$MONTHLY_KPIS" -gt 0 ] && ((WARNINGS++))

if [ $WARNINGS -gt 0 ]; then
    echo "⚠️  ADVERTENCIAS:"
    echo "   Se detectaron $WARNINGS problemas. Revisa los logs arriba."
    echo "   Los servicios pueden estar iniciando aún. Espera 1-2 minutos"
    echo "   y vuelve a verificar con:"
    echo "   ssh $SERVER 'cd $PROJECT_DIR && docker compose ps'"
    echo ""
fi

echo "════════════════════════════════════════════════════════════"
echo ""
