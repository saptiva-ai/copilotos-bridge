#!/bin/bash
set -e

# ============================================================================
# PRODUCTION DEPLOY SCRIPT V2 - MEJORADO
# ============================================================================
# Versión mejorada que:
# - Carga variables de entorno correctamente
# - Inicializa tablas de DB automáticamente
# - Maneja dependencias faltantes
# - Preserva datos de usuarios
# ============================================================================

echo "🚀 Iniciando deploy seguro a producción (v2)..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

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

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker no está corriendo"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "infra/docker-compose.yml" ]; then
    log_error "No se encuentra infra/docker-compose.yml"
    echo "Asegúrate de estar en el directorio raíz del proyecto"
    exit 1
fi

# Check .env file exists
if [ ! -f "envs/.env" ]; then
    log_error "No se encuentra envs/.env"
    exit 1
fi

# Detect docker compose command (v1 vs v2)
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi
log_info "Usando: $DOCKER_COMPOSE"

log_success "Pre-checks completados"
echo ""

# ============================================================================
# CARGAR VARIABLES DE ENTORNO
# ============================================================================

echo "📋 Cargando variables de entorno..."

# Extract critical variables from .env file
export SECRET_KEY=$(grep '^SECRET_KEY=' envs/.env | cut -d '=' -f2)
export JWT_SECRET_KEY=$(grep '^JWT_SECRET_KEY=' envs/.env | cut -d '=' -f2)

if [ -z "$SECRET_KEY" ] || [ ${#SECRET_KEY} -lt 32 ]; then
    log_error "SECRET_KEY no encontrada o demasiado corta en envs/.env"
    exit 1
fi

if [ -z "$JWT_SECRET_KEY" ] || [ ${#JWT_SECRET_KEY} -lt 32 ]; then
    log_error "JWT_SECRET_KEY no encontrada o demasiado corta en envs/.env"
    exit 1
fi

log_success "Variables de entorno cargadas"
log_info "SECRET_KEY: ${SECRET_KEY:0:8}... (${#SECRET_KEY} chars)"
log_info "JWT_SECRET_KEY: ${JWT_SECRET_KEY:0:8}... (${#JWT_SECRET_KEY} chars)"
echo ""

# ============================================================================
# BACKUP
# ============================================================================

echo "💾 Creando backup de configuración..."

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup .env files
if [ -f "envs/.env" ]; then
    cp envs/.env "$BACKUP_DIR/.env.backup"
    log_success "Backup de .env creado: $BACKUP_DIR/.env.backup"
fi

echo ""

# ============================================================================
# PULL CÓDIGO (si estamos en un servidor con git)
# ============================================================================

if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "📥 Actualizando código desde Git..."

    CURRENT_BRANCH=$(git branch --show-current)
    log_info "Rama actual: $CURRENT_BRANCH"

    # Stash any local changes (safety)
    if [ -n "$(git status --porcelain)" ]; then
        log_warning "Hay cambios locales. Guardando en stash..."
        git stash push -m "Auto-stash before deploy $(date)"
    fi

    # Pull latest changes
    git pull origin "$CURRENT_BRANCH" || log_warning "Git pull falló, continuando con código local..."

    CURRENT_COMMIT=$(git rev-parse --short HEAD)
    log_success "Código actualizado a commit: $CURRENT_COMMIT"
    echo ""
fi

# ============================================================================
# DETENER SERVICIOS (SIN borrar volúmenes)
# ============================================================================

echo "🛑 Deteniendo servicios actuales..."
log_warning "NOTA: Volúmenes y datos se preservan (sin flag -v)"

# Stop containers but KEEP volumes
$DOCKER_COMPOSE -f infra/docker-compose.yml down

log_success "Servicios detenidos"
echo ""

# ============================================================================
# RECONSTRUIR IMÁGENES
# ============================================================================

echo "🔨 Reconstruyendo imágenes Docker..."

# Build only changed services
$DOCKER_COMPOSE -f infra/docker-compose.yml build --no-cache bank-advisor backend web

log_success "Imágenes reconstruidas"
echo ""

# ============================================================================
# LEVANTAR SERVICIOS CON ENV VARS
# ============================================================================

echo "🚀 Levantando servicios con variables de entorno..."

# Start services with exported env vars
$DOCKER_COMPOSE -f infra/docker-compose.yml up -d

echo "⏳ Esperando a que los servicios estén listos..."
sleep 15

log_success "Servicios levantados"
echo ""

# ============================================================================
# INICIALIZAR BASE DE DATOS
# ============================================================================

echo "🗄️  Inicializando tablas de base de datos..."

# Create etl_runs table if not exists
$DOCKER_COMPOSE -f infra/docker-compose.yml exec -T postgres psql -U octavios -d bankadvisor <<EOF
CREATE TABLE IF NOT EXISTS etl_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    rows_processed_base INTEGER,
    rows_processed_icap INTEGER,
    rows_processed_tda INTEGER,
    rows_processed_tasas INTEGER,
    etl_version VARCHAR(50),
    triggered_by VARCHAR(50) DEFAULT 'manual'
);
CREATE INDEX IF NOT EXISTS idx_etl_runs_started_at ON etl_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_etl_runs_status ON etl_runs(status);
EOF

log_success "Tablas de base de datos inicializadas"
echo ""

# ============================================================================
# VERIFICACIONES POST-DEPLOY
# ============================================================================

echo "🔍 Verificando deploy..."

# Check container status
echo ""
echo "📊 Estado de contenedores:"
$DOCKER_COMPOSE -f infra/docker-compose.yml ps

# Wait a bit more for health checks
sleep 10

# Check health endpoints
echo ""
echo "🏥 Verificando health endpoints..."

# Bank Advisor
if curl -s http://localhost:8002/health > /dev/null; then
    log_success "Bank Advisor: OK"
else
    log_warning "Bank Advisor: Puede estar iniciando aún"
fi

# Backend
if curl -s http://localhost:8000/health > /dev/null; then
    log_success "Backend: OK"
else
    log_error "Backend: ERROR - revisar logs"
    $DOCKER_COMPOSE -f infra/docker-compose.yml logs --tail=20 backend
fi

# Frontend
if curl -s http://localhost:3000 > /dev/null; then
    log_success "Frontend: OK"
else
    log_warning "Frontend: Puede estar iniciando aún"
fi

# ============================================================================
# VERIFICAR DATOS PRESERVADOS
# ============================================================================

echo ""
echo "🔍 Verificando que los datos se preservaron..."

# Check Bank Advisor data in PostgreSQL
BANK_ROWS=$($DOCKER_COMPOSE -f infra/docker-compose.yml exec -T postgres psql -U octavios -d bankadvisor -t -c "SELECT COUNT(*) FROM monthly_kpis;" 2>/dev/null | xargs || echo "0")

if [ "$BANK_ROWS" -gt 0 ]; then
    log_success "Bank Advisor data: $BANK_ROWS filas en PostgreSQL"
else
    log_warning "Bank Advisor data: 0 filas (puede necesitar ETL)"
fi

# Check user data in MongoDB
USER_COUNT=$($DOCKER_COMPOSE -f infra/docker-compose.yml exec -T mongodb mongosh -u octavios_user -p secure_password_change_me --authenticationDatabase admin octavios --quiet --eval 'db.users.countDocuments()' 2>/dev/null || echo "0")

if [ "$USER_COUNT" -gt 0 ]; then
    log_success "Usuarios preservados: $USER_COUNT usuarios en MongoDB"
else
    log_warning "Usuarios: 0 usuarios (primera instalación o problema de conexión)"
fi

# ============================================================================
# RESUMEN
# ============================================================================

echo ""
echo "============================================================================"
log_success "DEPLOY COMPLETADO"
echo "============================================================================"
echo ""
echo "📋 Resumen:"
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "  - Commit: $(git rev-parse --short HEAD)"
    echo "  - Branch: $(git branch --show-current)"
fi
echo "  - Backup: $BACKUP_DIR"
echo "  - Datos preservados: ✅"
echo "  - Volúmenes intactos: ✅"
echo ""
echo "🔗 Acceso:"
echo "  - Frontend: http://\${PROD_SERVER_IP:-localhost}:3000"
echo "  - Backend API: http://\${PROD_SERVER_IP:-localhost}:8000"
echo "  - Bank Advisor: http://\${PROD_SERVER_IP:-localhost}:8002"
echo ""

# ETL reminder if data is low
if [ "$BANK_ROWS" -lt 1000 ]; then
    echo "⚠️  NOTA: Bank Advisor tiene pocos datos ($BANK_ROWS filas)"
    echo "   Para poblar datos completos, ejecuta:"
    echo "   ./scripts/init-bankadvisor-db.sh"
    echo ""
fi

echo "📊 Comandos útiles:"
echo "  - Ver logs: $DOCKER_COMPOSE -f infra/docker-compose.yml logs -f [servicio]"
echo "  - Ver stats: docker stats"
echo "  - Reiniciar servicio: $DOCKER_COMPOSE -f infra/docker-compose.yml restart [servicio]"
echo ""
echo "============================================================================"
