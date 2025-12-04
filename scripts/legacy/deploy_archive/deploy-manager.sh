#!/bin/bash
################################################################################
# Deploy Manager - Consolidates deployment logic for different environments
#
# Usage:
#   ./scripts/deploy-manager.sh <ENV> <MODE>
#
# Examples:
#   ./scripts/deploy-manager.sh demo fast
#   ./scripts/deploy-manager.sh prod safe
#
# Environments: demo, prod
# Modes: fast (skip build), safe (with backups), tar (standard)
################################################################################

set -e

ENV=$1
MODE=${2:-safe} # Default to safe if not specified

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ -z "$ENV" ]; then
    echo -e "${RED}❌ Error: Entorno no especificado${NC}"
    echo "Uso: $0 <ENV> <MODE>"
    echo "  ENV:  demo, prod"
    echo "  MODE: fast, safe, tar (default: safe)"
    exit 1
fi

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================

case "$ENV" in
  "demo")
    SERVER_HOST="jf@34.172.67.93"
    DEPLOY_PATH="/home/jf/capital414-chat"
    ;;
  "prod")
    # Load from .env if available
    if [ -f "envs/.env.prod" ]; then
        source envs/.env.prod
        SERVER_HOST="${PROD_SERVER_USER}@${PROD_SERVER_IP}"
        DEPLOY_PATH="${PROD_DEPLOY_PATH}"
    else
        echo -e "${RED}❌ Error: envs/.env.prod no encontrado${NC}"
        exit 1
    fi
    ;;
  *)
    echo -e "${RED}❌ Error: Entorno desconocido: $ENV${NC}"
    echo "Entornos disponibles: demo, prod"
    exit 1
    ;;
esac

echo -e "${BLUE}🚀 Desplegando a $ENV ($SERVER_HOST) en modo $MODE...${NC}"

# ============================================================================
# DEPLOYMENT STRATEGY SELECTOR
# ============================================================================

case "$MODE" in
  "fast")
    # Fast deployment without rebuilding images
    echo -e "${YELLOW}⚡ Modo rápido: usando imágenes existentes${NC}"
    ./scripts/deploy.sh tar --skip-build --host "$SERVER_HOST" --path "$DEPLOY_PATH"
    ;;
  "safe")
    # Safe deployment with backups (Recommended)
    echo -e "${GREEN}🛡️  Modo seguro: con backups automáticos${NC}"
    ssh "$SERVER_HOST" "cd $DEPLOY_PATH && ./scripts/deploy-on-server.sh"
    ;;
  "tar")
    # Standard tarball deployment
    echo -e "${BLUE}📦 Modo tarball: despliegue estándar${NC}"
    ./scripts/deploy.sh tar --host "$SERVER_HOST" --path "$DEPLOY_PATH"
    ;;
  *)
    echo -e "${RED}❌ Modo desconocido: $MODE${NC}"
    echo "Modos disponibles: fast, safe, tar"
    exit 1
    ;;
esac

echo -e "${GREEN}✅ Despliegue completado${NC}"
