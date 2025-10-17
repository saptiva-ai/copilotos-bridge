#!/bin/bash
# ========================================
# COPILOTOS BRIDGE - CLEAR SERVER CACHE
# ========================================
# Clears Redis cache and restarts web container on production server
#
# Usage: ./scripts/clear-server-cache.sh
#        make clear-cache
#
# Environment variables (loaded from envs/.env.prod if present):
#   PROD_SERVER_HOST: SSH target (e.g., user@ip-address)
#   PROD_DEPLOY_PATH: Remote deployment path
#   DEPLOY_SERVER: Legacy alias for PROD_SERVER_HOST
#   DEPLOY_PATH: Legacy alias for PROD_DEPLOY_PATH

set -e

# Status symbols
RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "
NC=""
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load production environment if available
if [ -f "$PROJECT_ROOT/envs/.env.prod" ]; then
    source "$PROJECT_ROOT/envs/.env.prod"
elif [ -f "$PROJECT_ROOT/envs/.env" ]; then
    source "$PROJECT_ROOT/envs/.env"
fi

# Use environment variables with fallback to legacy defaults
DEPLOY_SERVER="${DEPLOY_SERVER:-${PROD_SERVER_HOST:-your-ssh-user@your-server-ip-here}}"
DEPLOY_PATH="${DEPLOY_PATH:-${PROD_DEPLOY_PATH:-/opt/copilotos-bridge}}"

# Validate configuration
if [ "$DEPLOY_SERVER" = "your-ssh-user@your-server-ip-here" ]; then
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}▲  ERROR: Production server not configured!${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}Please run:${NC} ${GREEN}make setup-interactive-prod${NC}"
    echo ""
    exit 1
fi

# Functions
log_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}${NC} $1"
}

log_error() {
    echo -e "${RED}${NC} $1"
}

echo ""
echo -e "${BLUE}Clearing Production Server Cache...${NC}"
echo ""

# Get Redis password from server
log_info "Getting Redis password..."
REDIS_PASSWORD=$(ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH/infra && grep REDIS_PASSWORD .env | cut -d'=' -f2")

if [ -z "$REDIS_PASSWORD" ]; then
    log_error "Could not retrieve Redis password"
    exit 1
fi

# Flush Redis cache
log_info "Flushing Redis cache..."
FLUSH_RESULT=$(ssh "$DEPLOY_SERVER" "docker exec copilotos-redis redis-cli -a '$REDIS_PASSWORD' FLUSHALL 2>&1 | grep OK" || echo "")

if [ -n "$FLUSH_RESULT" ]; then
    log_success "Redis cache cleared"
else
    log_error "Failed to clear Redis cache"
    exit 1
fi

# Verify cache is empty
DBSIZE=$(ssh "$DEPLOY_SERVER" "docker exec copilotos-redis redis-cli -a '$REDIS_PASSWORD' DBSIZE 2>/dev/null | tail -1")
log_info "Redis DBSIZE: $DBSIZE"

# Restart web container to clear Next.js internal cache
log_info "Restarting web container..."
ssh "$DEPLOY_SERVER" "docker restart copilotos-web" > /dev/null

log_success "Web container restarted"

# Wait for container to be healthy
log_info "Waiting for web container to be healthy..."
sleep 8

# Check container status
CONTAINER_STATUS=$(ssh "$DEPLOY_SERVER" "docker ps --filter name=copilotos-web --format '{{.Status}}'" 2>/dev/null)
log_info "Container status: $CONTAINER_STATUS"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Cache Cleared Successfully${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Hard refresh your browser: Ctrl+Shift+R (or Cmd+Shift+R on Mac)"
echo "  2. Test the application to verify new version is loaded"
echo ""
