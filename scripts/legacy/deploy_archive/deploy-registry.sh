#!/bin/bash
set -e

# ============================================================================
# REGISTRY-BASED DEPLOY SCRIPT
# ============================================================================
# Deploy usando imágenes pre-construidas desde Docker Hub
# Mucho más rápido que construir en el servidor
# ============================================================================
#
# Uso:
#   ./scripts/deploy-registry.sh
#
# ============================================================================

echo "🚀 Iniciando deploy con imágenes pre-construidas (Docker Hub)..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# ============================================================================
# PRE-CHECKS
# ============================================================================

echo "🔍 Verificando pre-requisitos..."

if ! docker info > /dev/null 2>&1; then
    log_error "Docker no está corriendo"
    exit 1
fi

if [ ! -f "infra/docker-compose.yml" ]; then
    log_error "No se encuentra infra/docker-compose.yml"
    exit 1
fi

if [ ! -f "infra/docker-compose.production.yml" ]; then
    log_error "No se encuentra infra/docker-compose.production.yml"
    exit 1
fi

if [ ! -f "infra/docker-compose.registry.yml" ]; then
    log_error "No se encuentra infra/docker-compose.registry.yml"
    exit 1
fi

# Detect docker compose command
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

log_success "Pre-checks completados"
echo ""

# ============================================================================
# COMPOSE FILES
# ============================================================================

COMPOSE_FILES="-f infra/docker-compose.yml -f infra/docker-compose.production.yml -f infra/docker-compose.registry.yml"

log_info "Usando compose files:"
log_info "  1. docker-compose.yml (base)"
log_info "  2. docker-compose.production.yml (production overrides)"
log_info "  3. docker-compose.registry.yml (registry images)"
echo ""

# ============================================================================
# PULL LATEST IMAGES
# ============================================================================

echo "📥 Pulling latest images from Docker Hub..."

$DOCKER_COMPOSE $COMPOSE_FILES pull backend web file-manager bank-advisor

log_success "Images pulled successfully"
echo ""

# ============================================================================
# DETENER SERVICIOS
# ============================================================================

echo "🛑 Deteniendo servicios actuales..."
log_warning "NOTA: Volúmenes y datos se preservan"

$DOCKER_COMPOSE $COMPOSE_FILES down

log_success "Servicios detenidos"
echo ""

# ============================================================================
# LEVANTAR SERVICIOS
# ============================================================================

echo "🚀 Levantando servicios con imágenes del registry..."

$DOCKER_COMPOSE $COMPOSE_FILES up -d

echo "⏳ Esperando a que los servicios estén listos..."
sleep 20

log_success "Servicios levantados"
echo ""

# ============================================================================
# VERIFICACIONES POST-DEPLOY
# ============================================================================

echo "🔍 Verificando deploy..."
echo ""

# Check container status
echo "📊 Estado de contenedores:"
$DOCKER_COMPOSE $COMPOSE_FILES ps

# Wait for health checks
sleep 10

# Check health endpoints
echo ""
echo "🏥 Verificando health endpoints..."

# Bank Advisor
if curl -s http://localhost:8002/health > /dev/null; then
    log_success "Bank Advisor: OK"
else
    log_warning "Bank Advisor: Iniciando..."
fi

# Backend
if curl -s http://localhost:8000/api/health > /dev/null; then
    log_success "Backend: OK"
else
    log_warning "Backend: Iniciando..."
fi

# Frontend
if curl -s http://localhost:3000 > /dev/null; then
    log_success "Frontend: OK"
else
    log_warning "Frontend: Iniciando..."
fi

# ============================================================================
# VERIFICAR DATOS
# ============================================================================

echo ""
echo "🔍 Verificando datos..."

# Check Bank Advisor data
BANK_ROWS=$($DOCKER_COMPOSE $COMPOSE_FILES exec -T postgres psql -U octavios -d bankadvisor -t -c "SELECT COUNT(*) FROM monthly_kpis;" 2>/dev/null | xargs || echo "0")

if [ "$BANK_ROWS" -gt 0 ]; then
    log_success "Bank Advisor data: $BANK_ROWS filas"
else
    log_warning "Bank Advisor data: 0 filas"
fi

# Check user data
USER_COUNT=$($DOCKER_COMPOSE $COMPOSE_FILES exec -T mongodb mongosh -u octavios_user -p secure_password_change_me --authenticationDatabase admin octavios --quiet --eval 'db.users.countDocuments()' 2>/dev/null || echo "0")

if [ "$USER_COUNT" -gt 0 ]; then
    log_success "Usuarios: $USER_COUNT usuarios"
else
    log_warning "Usuarios: 0 usuarios"
fi

# ============================================================================
# RESUMEN
# ============================================================================

echo ""
echo "============================================================================"
log_success "DEPLOY CON REGISTRY COMPLETADO"
echo "============================================================================"
echo ""
echo "📋 Resumen:"
echo "  - Método: Docker Hub registry (sin build)"
echo "  - Versión: 0.1.2"
echo "  - Tiempo: ~2-3 minutos (vs 30+ minutos con build)"
echo "  - Datos preservados: ✅"
echo ""
echo "🔗 Acceso:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend API: http://localhost:8000"
echo "  - Bank Advisor: http://localhost:8002"
echo ""
echo "📊 Comandos útiles:"
echo "  - Ver logs: $DOCKER_COMPOSE $COMPOSE_FILES logs -f [servicio]"
echo "  - Ver stats: docker stats"
echo "  - Reiniciar: $DOCKER_COMPOSE $COMPOSE_FILES restart [servicio]"
echo ""
echo "============================================================================"
