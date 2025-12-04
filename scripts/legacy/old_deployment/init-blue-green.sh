#!/bin/bash
# ========================================
# BLUE/GREEN DEPLOYMENT - INITIALIZATION
# ========================================
# Inicializa la infraestructura necesaria para deployments blue/green.
#
# Este script debe ejecutarse UNA VEZ antes del primer deployment blue/green.
# Crea los volúmenes externos y levanta la capa de datos compartida.
#
# Usage:
#   ./scripts/init-blue-green.sh
#
# Pasos:
#   1. Crear volúmenes Docker externos
#   2. Levantar capa de datos (MongoDB + Redis)
#   3. Crear directorio de estado
#   4. Validar configuración nginx

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "

log_info() { echo -e "${BLUE}$1"; }
log_success() { echo -e "${GREEN}$1"; }
log_warning() { echo -e "${YELLOW}$1"; }
log_error() { echo -e "${RED}$1" >&2; }

echo ""
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "  Blue/Green Deployment Initialization"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ========================================
# Step 1: Crear volúmenes externos
# ========================================
log_info "Step 1/4: Creating external Docker volumes..."

for volume in octavios-data-mongodb octavios-data-mongodb-config octavios-data-redis; do
    if docker volume inspect "$volume" >/dev/null 2>&1; then
        log_warning "Volume $volume already exists (skipping)"
    else
        docker volume create "$volume"
        log_success "Created volume: $volume"
    fi
done

# ========================================
# Step 2: Verificar env file
# ========================================
log_info "Step 2/4: Checking environment configuration..."

if [ ! -f "$PROJECT_ROOT/envs/.env.prod" ]; then
    log_error "Missing envs/.env.prod"
    echo ""
    echo "Create this file with production configuration:"
    echo "  cp envs/.env.production.example envs/.env.prod"
    echo "  vim envs/.env.prod  # Edit credentials"
    exit 1
fi

log_success "Environment file found"

# ========================================
# Step 3: Levantar capa de datos
# ========================================
log_info "Step 3/4: Starting shared data layer..."

cd "$PROJECT_ROOT"
docker compose -f infra/docker-compose.data.yml up -d

# Esperar a que estén saludables
log_info "Waiting for MongoDB..."
timeout 60 bash -c 'until docker exec octavios-data-mongodb mongosh --eval "db.runCommand({ ping: 1 })" >/dev/null 2>&1; do sleep 2; done'
log_success "MongoDB is ready"

log_info "Waiting for Redis..."
timeout 30 bash -c 'until docker exec octavios-data-redis redis-cli ping >/dev/null 2>&1; do sleep 2; done'
log_success "Redis is ready"

# ========================================
# Step 4: Crear directorio de estado
# ========================================
log_info "Step 4/4: Creating deployment state directory..."

mkdir -p "$PROJECT_ROOT/.deploy"
echo "none" > "$PROJECT_ROOT/.deploy/current_color"
log_success "State directory created"

# ========================================
# Summary
# ========================================
echo ""
log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_success "  Initialization Complete!"
log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
log_info "Data layer status:"
docker compose -f infra/docker-compose.data.yml ps
echo ""
log_info "Next steps:"
echo "  1. Deploy first stack:"
echo "     docker compose -p octavios-blue -f infra/docker-compose.app.yml up -d"
echo ""
echo "  2. Check health:"
echo "     ./scripts/blue-green-switch.sh --status"
echo ""
echo "  3. Switch active color:"
echo "     ./scripts/blue-green-switch.sh blue"
echo ""
