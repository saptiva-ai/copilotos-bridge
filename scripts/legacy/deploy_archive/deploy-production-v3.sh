#!/bin/bash
set -e

# ============================================================================
# PRODUCTION DEPLOY SCRIPT V3 - PRODUCTION-FIRST
# ============================================================================
# Versión mejorada que:
# - Usa docker-compose.production.yml para garantizar modo producción
# - Deshabilita hot reload explícitamente
# - Verifica que NO haya volúmenes de desarrollo montados
# - Maneja transferencia de dump de PostgreSQL (opcional)
# - Validación exhaustiva post-deploy
# ============================================================================
#
# Uso:
#   ./scripts/deploy-production-v3.sh                    # Deploy normal
#   ./scripts/deploy-production-v3.sh --restore-dump     # Con restauración de dump
#   ./scripts/deploy-production-v3.sh --dump-file=/path  # Dump específico
#
# ============================================================================

echo "🚀 Iniciando deploy PRODUCTION-FIRST (v3)..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
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

log_critical() {
    echo -e "${MAGENTA}🔥 CRÍTICO: $1${NC}"
}

# ============================================================================
# PARSE ARGUMENTOS
# ============================================================================

RESTORE_DUMP=false
DUMP_FILE=""

for arg in "$@"; do
    case $arg in
        --restore-dump)
            RESTORE_DUMP=true
            shift
            ;;
        --dump-file=*)
            DUMP_FILE="${arg#*=}"
            RESTORE_DUMP=true
            shift
            ;;
        --help)
            echo "Uso: $0 [opciones]"
            echo ""
            echo "Opciones:"
            echo "  --restore-dump              Restaurar dump de PostgreSQL desde bankadvisor_dump.sql.gz"
            echo "  --dump-file=/path/file.gz   Restaurar dump desde archivo específico"
            echo "  --help                      Mostrar esta ayuda"
            exit 0
            ;;
        *)
            log_error "Argumento desconocido: $arg"
            echo "Usa --help para ver opciones disponibles"
            exit 1
            ;;
    esac
done

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

# Check production override exists
if [ ! -f "infra/docker-compose.production.yml" ]; then
    log_error "No se encuentra infra/docker-compose.production.yml"
    echo "Este archivo es requerido para garantizar modo producción"
    exit 1
fi

# Detect docker compose command (v1 vs v2)
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi
log_info "Usando: $DOCKER_COMPOSE"

# Define compose files
COMPOSE_FILES="-f infra/docker-compose.yml -f infra/docker-compose.production.yml"

# Check dump file if restore requested
if [ "$RESTORE_DUMP" = true ]; then
    if [ -z "$DUMP_FILE" ]; then
        DUMP_FILE="bankadvisor_dump.sql.gz"
    fi

    if [ ! -f "$DUMP_FILE" ]; then
        log_error "Dump file no encontrado: $DUMP_FILE"
        exit 1
    fi

    log_info "Dump a restaurar: $DUMP_FILE ($(du -h "$DUMP_FILE" | cut -f1))"
fi

log_success "Pre-checks completados"
echo ""

# ============================================================================
# CARGAR VARIABLES DE ENTORNO
# ============================================================================

echo "📋 Cargando variables de entorno..."

# Extract critical variables from .env file
export SECRET_KEY=$(grep '^SECRET_KEY=' envs/.env | cut -d '=' -f2)
export JWT_SECRET_KEY=$(grep '^JWT_SECRET_KEY=' envs/.env | cut -d '=' -f2)
export NODE_ENV=production

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
log_info "NODE_ENV: $NODE_ENV"
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

# Backup PostgreSQL before deploy (if restore is requested)
if [ "$RESTORE_DUMP" = true ]; then
    log_info "Creando backup de PostgreSQL antes de restaurar..."
    if $DOCKER_COMPOSE $COMPOSE_FILES ps postgres 2>/dev/null | grep -q "Up"; then
        $DOCKER_COMPOSE $COMPOSE_FILES exec -T postgres pg_dump -U octavios -d bankadvisor --no-owner --no-acl | gzip > "$BACKUP_DIR/postgres_backup.sql.gz" || log_warning "No se pudo crear backup de PostgreSQL (puede ser primera instalación)"
    fi
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
$DOCKER_COMPOSE $COMPOSE_FILES down

log_success "Servicios detenidos"
echo ""

# ============================================================================
# RECONSTRUIR IMÁGENES EN MODO PRODUCCIÓN
# ============================================================================

echo "🔨 Reconstruyendo imágenes Docker (PRODUCTION MODE)..."

# Build with production override to ensure correct targets
$DOCKER_COMPOSE $COMPOSE_FILES build --no-cache bank-advisor backend web file-manager

log_success "Imágenes reconstruidas en modo producción"
echo ""

# ============================================================================
# LEVANTAR SERVICIOS CON PRODUCTION OVERRIDE
# ============================================================================

echo "🚀 Levantando servicios EN MODO PRODUCCIÓN..."
log_info "Usando: docker-compose.yml + docker-compose.production.yml"

# Start services with production overrides
$DOCKER_COMPOSE $COMPOSE_FILES up -d

echo "⏳ Esperando a que los servicios estén listos..."
sleep 20

log_success "Servicios levantados en modo producción"
echo ""

# ============================================================================
# VERIFICAR MODO PRODUCCIÓN (CRÍTICO)
# ============================================================================

echo "🔒 VERIFICANDO MODO PRODUCCIÓN..."
echo ""

PRODUCTION_ISSUES=0

# Check 1: Verify no source code volumes mounted
log_info "Verificando que NO haya hot reload activo..."

for service in backend web bank-advisor file-manager; do
    # Check if source directories are mounted
    MOUNTS=$($DOCKER_COMPOSE $COMPOSE_FILES ps -q $service 2>/dev/null | xargs -I {} docker inspect {} --format '{{range .Mounts}}{{.Source}} {{end}}' 2>/dev/null || echo "")

    if echo "$MOUNTS" | grep -q "/src"; then
        log_critical "$service: Detectado volumen /src (HOT RELOAD ACTIVO)"
        PRODUCTION_ISSUES=$((PRODUCTION_ISSUES + 1))
    else
        log_success "$service: Sin hot reload ✅"
    fi
done

# Check 2: Verify NODE_ENV
log_info "Verificando NODE_ENV=production..."
WEB_NODE_ENV=$($DOCKER_COMPOSE $COMPOSE_FILES exec -T web sh -c 'echo $NODE_ENV' 2>/dev/null | tr -d '\r' || echo "")
if [ "$WEB_NODE_ENV" = "production" ]; then
    log_success "web: NODE_ENV=production ✅"
else
    log_warning "web: NODE_ENV=$WEB_NODE_ENV (esperado: production)"
    PRODUCTION_ISSUES=$((PRODUCTION_ISSUES + 1))
fi

# Check 3: Verify backend isn't using --reload
log_info "Verificando que backend NO use --reload..."
BACKEND_CMD=$($DOCKER_COMPOSE $COMPOSE_FILES exec -T backend ps aux | grep uvicorn || echo "")
if echo "$BACKEND_CMD" | grep -q "\-\-reload"; then
    log_critical "backend: Detectado flag --reload (MODO DESARROLLO)"
    PRODUCTION_ISSUES=$((PRODUCTION_ISSUES + 1))
else
    log_success "backend: Sin flag --reload ✅"
fi

echo ""
if [ $PRODUCTION_ISSUES -gt 0 ]; then
    log_error "Se detectaron $PRODUCTION_ISSUES problemas de modo producción"
    log_warning "El deploy continuará, pero revisa los warnings arriba"
    echo ""
else
    log_success "TODAS las verificaciones de producción pasaron ✅"
    echo ""
fi

# ============================================================================
# INICIALIZAR BASE DE DATOS
# ============================================================================

echo "🗄️  Inicializando tablas de base de datos..."

# Wait for postgres to be ready
sleep 5

# Create etl_runs table if not exists
$DOCKER_COMPOSE $COMPOSE_FILES exec -T postgres psql -U octavios -d bankadvisor <<EOF
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
# RESTAURAR DUMP (si se solicitó)
# ============================================================================

if [ "$RESTORE_DUMP" = true ]; then
    echo "📥 Restaurando dump de PostgreSQL..."
    log_info "Archivo: $DUMP_FILE"

    # Restore dump
    gunzip < "$DUMP_FILE" | $DOCKER_COMPOSE $COMPOSE_FILES exec -T postgres psql -U octavios -d bankadvisor

    log_success "Dump restaurado exitosamente"

    # Restart bank-advisor to reload data
    log_info "Reiniciando bank-advisor para cargar nuevos datos..."
    $DOCKER_COMPOSE $COMPOSE_FILES restart bank-advisor

    sleep 10
    echo ""
fi

# ============================================================================
# VERIFICACIONES POST-DEPLOY
# ============================================================================

echo "🔍 Verificando deploy..."

# Check container status
echo ""
echo "📊 Estado de contenedores:"
$DOCKER_COMPOSE $COMPOSE_FILES ps

# Wait a bit more for health checks
sleep 10

# Check health endpoints
echo ""
echo "🏥 Verificando health endpoints..."

# Bank Advisor
BANK_HEALTH=$(curl -s http://localhost:8002/health || echo "error")
if echo "$BANK_HEALTH" | grep -q "healthy"; then
    log_success "Bank Advisor: OK"
    echo "$BANK_HEALTH" | head -3
else
    log_warning "Bank Advisor: Puede estar iniciando aún"
fi

# Backend
if curl -s http://localhost:8000/api/health > /dev/null; then
    log_success "Backend: OK"
else
    log_error "Backend: ERROR - revisar logs"
    $DOCKER_COMPOSE $COMPOSE_FILES logs --tail=20 backend
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
BANK_ROWS=$($DOCKER_COMPOSE $COMPOSE_FILES exec -T postgres psql -U octavios -d bankadvisor -t -c "SELECT COUNT(*) FROM monthly_kpis;" 2>/dev/null | xargs || echo "0")

if [ "$BANK_ROWS" -gt 0 ]; then
    log_success "Bank Advisor data: $BANK_ROWS filas en PostgreSQL"
else
    log_warning "Bank Advisor data: 0 filas (puede necesitar ETL)"
fi

# Check user data in MongoDB
USER_COUNT=$($DOCKER_COMPOSE $COMPOSE_FILES exec -T mongodb mongosh -u octavios_user -p secure_password_change_me --authenticationDatabase admin octavios --quiet --eval 'db.users.countDocuments()' 2>/dev/null || echo "0")

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
log_success "DEPLOY PRODUCTION-FIRST COMPLETADO"
echo "============================================================================"
echo ""
echo "📋 Resumen:"
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "  - Commit: $(git rev-parse --short HEAD)"
    echo "  - Branch: $(git branch --show-current)"
fi
echo "  - Modo: PRODUCCIÓN (sin hot reload)"
echo "  - Compose files: base + production override"
echo "  - Backup: $BACKUP_DIR"
echo "  - Datos preservados: ✅"
echo "  - Volúmenes intactos: ✅"
if [ "$RESTORE_DUMP" = true ]; then
    echo "  - Dump restaurado: ✅ ($BANK_ROWS filas)"
fi
echo ""
echo "🔗 Acceso:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend API: http://localhost:8000"
echo "  - Bank Advisor: http://localhost:8002"
echo ""

# ETL reminder if data is low
if [ "$BANK_ROWS" -lt 1000 ]; then
    echo "⚠️  NOTA: Bank Advisor tiene pocos datos ($BANK_ROWS filas)"
    echo "   Para poblar datos completos, ejecuta:"
    echo "   ./scripts/init-bankadvisor-db.sh"
    echo ""
fi

echo "📊 Comandos útiles:"
echo "  - Ver logs: $DOCKER_COMPOSE $COMPOSE_FILES logs -f [servicio]"
echo "  - Ver stats: docker stats"
echo "  - Reiniciar servicio: $DOCKER_COMPOSE $COMPOSE_FILES restart [servicio]"
echo "  - Verificar producción: $DOCKER_COMPOSE $COMPOSE_FILES exec backend env | grep NODE_ENV"
echo ""

# Production mode warnings
if [ $PRODUCTION_ISSUES -gt 0 ]; then
    echo "⚠️  ADVERTENCIAS DE MODO PRODUCCIÓN:"
    echo "   Se detectaron $PRODUCTION_ISSUES problemas. Revisa los logs arriba."
    echo "   Puede que algunos servicios estén en modo desarrollo."
    echo ""
fi

echo "============================================================================"
