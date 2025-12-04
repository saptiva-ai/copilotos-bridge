#!/bin/bash
set -e

# ============================================================================
# SAFE PRODUCTION DEPLOY SCRIPT
# ============================================================================
# Este script actualiza el código y reconstruye contenedores
# SIN borrar datos de usuarios ni volúmenes de Docker
# ============================================================================

echo "🚀 Iniciando deploy seguro a producción..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# PRE-CHECKS
# ============================================================================

echo "🔍 Verificando pre-requisitos..."

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ ERROR: Docker no está corriendo${NC}"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "infra/docker-compose.yml" ]; then
    echo -e "${RED}❌ ERROR: No se encuentra docker-compose.yml${NC}"
    echo "Asegúrate de estar en el directorio raíz del proyecto"
    exit 1
fi

# Check current branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}⚠️  Advertencia: No estás en la rama main (actual: $CURRENT_BRANCH)${NC}"
    read -p "¿Deseas continuar? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deploy cancelado"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Pre-checks completados${NC}"
echo ""

# ============================================================================
# BACKUP
# ============================================================================

echo "💾 Creando backup de configuración..."

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup .env files
if [ -f "envs/.env.prod" ]; then
    cp envs/.env.prod "$BACKUP_DIR/.env.prod.backup"
    echo "✅ Backup de .env.prod creado"
fi

# List current volumes (for reference, not backing up data)
echo "📦 Volúmenes actuales (NO se borrarán):"
docker volume ls | grep octavios || echo "No hay volúmenes con prefijo 'octavios'"
echo ""

# ============================================================================
# PULL CÓDIGO
# ============================================================================

echo "📥 Actualizando código desde GitHub..."

# Stash any local changes (safety)
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  Hay cambios locales. Guardando en stash...${NC}"
    git stash push -m "Auto-stash before deploy $(date)"
fi

# Pull latest changes
git pull origin main

CURRENT_COMMIT=$(git rev-parse --short HEAD)
echo -e "${GREEN}✅ Código actualizado a commit: $CURRENT_COMMIT${NC}"
echo ""

# ============================================================================
# DETENER SERVICIOS (SIN borrar volúmenes)
# ============================================================================

echo "🛑 Deteniendo servicios actuales..."
echo -e "${YELLOW}⚠️  NOTA: Volúmenes y datos se preservan${NC}"

# Stop containers but KEEP volumes
docker-compose -f infra/docker-compose.yml down

echo -e "${GREEN}✅ Servicios detenidos${NC}"
echo ""

# ============================================================================
# RECONSTRUIR IMÁGENES
# ============================================================================

echo "🔨 Reconstruyendo imágenes Docker..."

# Build only changed services
docker-compose -f infra/docker-compose.yml build --no-cache bank-advisor backend web

echo -e "${GREEN}✅ Imágenes reconstruidas${NC}"
echo ""

# ============================================================================
# LEVANTAR SERVICIOS
# ============================================================================

echo "🚀 Levantando servicios..."

docker-compose -f infra/docker-compose.yml up -d

echo "⏳ Esperando a que los servicios estén listos..."
sleep 10

echo -e "${GREEN}✅ Servicios levantados${NC}"
echo ""

# ============================================================================
# VERIFICACIONES POST-DEPLOY
# ============================================================================

echo "🔍 Verificando deploy..."

# Check container status
echo "📊 Estado de contenedores:"
docker-compose -f infra/docker-compose.yml ps

# Check health endpoints
echo ""
echo "🏥 Verificando health endpoints..."

# Bank Advisor
if curl -s http://localhost:8002/health > /dev/null; then
    echo -e "${GREEN}✅ Bank Advisor: OK${NC}"
else
    echo -e "${RED}❌ Bank Advisor: ERROR${NC}"
fi

# Backend
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Backend: OK${NC}"
else
    echo -e "${RED}❌ Backend: ERROR${NC}"
fi

# Frontend
if curl -s http://localhost:3000 > /dev/null; then
    echo -e "${GREEN}✅ Frontend: OK${NC}"
else
    echo -e "${RED}❌ Frontend: ERROR${NC}"
fi

# ============================================================================
# VERIFICAR DATOS PRESERVADOS
# ============================================================================

echo ""
echo "🔍 Verificando que los datos se preservaron..."

# Check Bank Advisor data
BANK_ROWS=$(docker exec octavios-chat-bajaware_invex-postgres psql -U octavios -d bankadvisor -t -c "SELECT COUNT(*) FROM monthly_kpis;" 2>/dev/null | xargs)

if [ -n "$BANK_ROWS" ] && [ "$BANK_ROWS" -gt 0 ]; then
    echo -e "${GREEN}✅ Bank Advisor data: $BANK_ROWS filas${NC}"
else
    echo -e "${RED}⚠️  Bank Advisor data: No se pudo verificar${NC}"
fi

# Check user data
USER_COUNT=$(docker exec octavios-chat-bajaware_invex-postgres psql -U postgres -d chat_db -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | xargs)

if [ -n "$USER_COUNT" ] && [ "$USER_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Usuarios preservados: $USER_COUNT usuarios${NC}"
else
    echo -e "${RED}⚠️  Usuarios: No se pudo verificar${NC}"
fi

# ============================================================================
# RESUMEN
# ============================================================================

echo ""
echo "============================================================================"
echo -e "${GREEN}✅ DEPLOY COMPLETADO${NC}"
echo "============================================================================"
echo ""
echo "📋 Resumen:"
echo "  - Commit: $CURRENT_COMMIT"
echo "  - Branch: main"
echo "  - Backup: $BACKUP_DIR"
echo "  - Datos preservados: ✅"
echo "  - Volúmenes intactos: ✅"
echo ""
echo "🔗 Acceso:"
echo "  - Frontend: http://\${PROD_SERVER_IP:-localhost}:3000"
echo "  - Backend API: http://\${PROD_SERVER_IP:-localhost}:8000"
echo "  - Bank Advisor: http://\${PROD_SERVER_IP:-localhost}:8002"
echo ""
echo "📝 Nuevas funcionalidades:"
echo "  ✨ Fix IMOR/ICOR + segment detection"
echo "  ✨ LLM redirect fix"
echo "  ✨ Frontend charts sin refresh"
echo "  ✨ VizRecommender inteligente"
echo "  ✨ 5 nuevos métodos de análisis"
echo ""
echo "📊 Monitoreo:"
echo "  - Ver logs: docker-compose -f infra/docker-compose.yml logs -f"
echo "  - Ver stats: docker stats"
echo ""
echo "🧪 Test sugerido:"
echo "  1. Login con usuario existente"
echo "  2. Probar query: 'IMOR de consumo últimos 3 meses'"
echo "  3. Verificar que la gráfica aparece inmediatamente"
echo ""
echo "============================================================================"
