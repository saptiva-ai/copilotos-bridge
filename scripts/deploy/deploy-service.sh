#!/bin/bash
# ============================================================================
# GRANULAR SERVICE DEPLOYMENT SCRIPT
# ============================================================================
# Deploys specific services to production using Docker Hub registry
# Usage: ./scripts/deploy/deploy-service.sh <services> <version>
#
# Examples:
#   ./scripts/deploy/deploy-service.sh "backend" 0.2.2
#   ./scripts/deploy/deploy-service.sh "backend web" 0.2.2
#   ./scripts/deploy/deploy-service.sh "all" 0.2.2
# ============================================================================

set -e

# === CONFIGURACIÓN ===
SERVER="${DEPLOY_SERVER}"
PROJECT_DIR="${DEPLOY_PROJECT_DIR:-octavios-chat-bajaware_invex}"

# Validate required environment variables
if [ -z "$SERVER" ]; then
    log_error "DEPLOY_SERVER environment variable is required.

Example:
  export DEPLOY_SERVER='user@your-server-ip'
  $0 'backend' 0.2.2"
fi
SERVICES="${1:-}"
VERSION="${2:-}"
BACKUP_DB="${BACKUP_DB:-false}"  # Default: no backup for granular deploys

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Valid services
VALID_SERVICES=("backend" "web" "file-manager" "bank-advisor" "all")

# Funciones de logging
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; exit 1; }

# === VALIDACIÓN ===
if [ -z "$SERVICES" ] || [ -z "$VERSION" ]; then
    log_error "Services and version required.

Usage: $0 <services> <VERSION>

Examples:
  $0 'backend' 0.2.2          # Deploy only backend
  $0 'backend web' 0.2.2      # Deploy backend and web
  $0 'all' 0.2.2              # Deploy all services

Available services: ${VALID_SERVICES[*]}"
fi

# Parse services
if [ "$SERVICES" = "all" ]; then
    DEPLOY_SERVICES=("backend" "web" "file-manager" "bank-advisor")
else
    # Convert space-separated string to array
    read -ra DEPLOY_SERVICES <<< "$SERVICES"
fi

# Validate services
for service in "${DEPLOY_SERVICES[@]}"; do
    if [[ ! " ${VALID_SERVICES[@]} " =~ " ${service} " ]]; then
        log_error "Invalid service: $service
Valid services: ${VALID_SERVICES[*]}"
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "🚀 GRANULAR DEPLOY TO PRODUCTION"
echo "════════════════════════════════════════════════════════════"
echo ""
log_info "Version: $VERSION"
log_info "Server: $SERVER"
log_info "Directory: $PROJECT_DIR"
log_info "Services: ${DEPLOY_SERVICES[*]}"
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
read -p "Continue with deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warning "Deployment cancelled by user"
    exit 0
fi

# === PASO 1: Backup de Base de Datos (Opcional) ===
if [ "$BACKUP_DB" = "true" ]; then
    echo ""
    log_info "Step 1/7: Creating database backup..."
    ssh $SERVER "cd $PROJECT_DIR && \
        mkdir -p backups && \
        docker exec postgres pg_dump -U octavios -d bankadvisor \
        --no-owner --no-acl | gzip > backups/granular_deploy_$(date +%Y%m%d_%H%M%S).sql.gz" \
        && log_success "Backup created" \
        || log_warning "Could not create backup (may be first installation)"
else
    log_warning "Step 1/7: DB backup disabled"
fi

# === PASO 2: Pull de Código ===
echo ""
log_info "Step 2/7: Updating code on server..."
ssh $SERVER "cd $PROJECT_DIR && \
    git fetch origin && \
    git checkout main && \
    git pull origin main" \
    && log_success "Code updated" \
    || log_error "Failed to update code"

# === PASO 3: Actualizar Versión en Registry Override ===
echo ""
log_info "Step 3/7: Updating service versions in docker-compose.registry.yml..."

# Build sed command for each service
for service in "${DEPLOY_SERVICES[@]}"; do
    ssh $SERVER "cd $PROJECT_DIR && \
        sed -i '/jazielflores1998\/octavios-invex-${service}:/ s/:.*/:${VERSION}/g' infra/docker-compose.registry.yml"
done

ssh $SERVER "cd $PROJECT_DIR && \
    grep 'image:' infra/docker-compose.registry.yml | grep -E '$(IFS='|'; echo "${DEPLOY_SERVICES[*]}")'" \
    && log_success "Versions updated to $VERSION" \
    || log_error "Failed to update versions"

# === PASO 4: Pull de Imágenes Específicas ===
echo ""
log_info "Step 4/7: Pulling images from Docker Hub (version $VERSION)..."
log_warning "This may take a few minutes depending on image sizes..."

PULL_SERVICES=$(IFS=' '; echo "${DEPLOY_SERVICES[*]}")
ssh $SERVER "cd $PROJECT_DIR && \
    docker compose -f infra/docker-compose.yml \
                   -f infra/docker-compose.production.yml \
                   -f infra/docker-compose.registry.yml \
                   pull $PULL_SERVICES" \
    && log_success "Images pulled" \
    || log_error "Failed to pull images"

# === PASO 5: Recrear Solo los Contenedores Específicos ===
echo ""
log_info "Step 5/7: Recreating containers for services: ${DEPLOY_SERVICES[*]}..."

UP_SERVICES=$(IFS=' '; echo "${DEPLOY_SERVICES[*]}")
ssh $SERVER "cd $PROJECT_DIR && \
    source envs/.env && \
    export SECRET_KEY JWT_SECRET_KEY && \
    docker compose -f infra/docker-compose.yml \
                   -f infra/docker-compose.production.yml \
                   -f infra/docker-compose.registry.yml \
                   up -d --force-recreate --no-build $UP_SERVICES" \
    && log_success "Containers recreated" \
    || log_error "Failed to recreate containers"

# === PASO 6: Esperar Health Checks ===
echo ""
log_info "Step 6/7: Waiting for services to be ready (30s)..."
for i in {1..3}; do
    echo -n "."
    sleep 10
done
echo ""
log_success "Services should be ready"

# === PASO 7: Verificación de Servicios ===
echo ""
log_info "Step 7/7: Verifying services..."
ssh $SERVER "cd $PROJECT_DIR && \
    docker compose -f infra/docker-compose.yml \
                   -f infra/docker-compose.production.yml \
                   ps --format 'table {{.Name}}\t{{.Status}}' | grep -E '$(IFS='|'; echo "${DEPLOY_SERVICES[*]}")'"

# === HEALTH CHECKS ===
echo ""
log_info "Running health checks..."

# Check which services were deployed and test their endpoints
for service in "${DEPLOY_SERVICES[@]}"; do
    case $service in
        "web")
            WEB_STATUS=$(ssh $SERVER "curl -s -o /dev/null -w '%{http_code}' https://invex.saptiva.com" || echo "000")
            if [ "$WEB_STATUS" = "200" ]; then
                log_success "Web OK (HTTP $WEB_STATUS)"
            else
                log_warning "Web responds with HTTP $WEB_STATUS"
            fi
            ;;
        "backend")
            API_STATUS=$(ssh $SERVER "curl -s -o /dev/null -w '%{http_code}' https://back-invex.saptiva.com/api/health" || echo "000")
            if [ "$API_STATUS" = "200" ]; then
                log_success "Backend API OK (HTTP $API_STATUS)"
            else
                log_warning "Backend API responds with HTTP $API_STATUS"
            fi
            ;;
    esac
done

# === RESUMEN ===
echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ GRANULAR DEPLOY COMPLETED"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📋 Summary:"
echo "  - Services deployed: ${DEPLOY_SERVICES[*]}"
echo "  - Version: $VERSION"
echo "  - URL Web: https://invex.saptiva.com"
echo "  - Backend API: https://back-invex.saptiva.com"
echo ""
echo "📊 Manual verification recommended:"
echo "  1. Open https://invex.saptiva.com and test functionality"
echo "  2. Check logs if there are any issues:"
for service in "${DEPLOY_SERVICES[@]}"; do
    echo "     ssh $SERVER 'cd $PROJECT_DIR && docker compose logs -f $service'"
done
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
