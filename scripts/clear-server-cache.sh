#!/bin/bash
# ========================================
# COPILOTOS BRIDGE - CLEAR SERVER CACHE
# ========================================
# Clears Redis cache and restarts web container on production server
#
# Usage: ./scripts/clear-server-cache.sh
#        make clear-cache

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DEPLOY_SERVER="${DEPLOY_SERVER:-jf@34.42.214.246}"
DEPLOY_PATH="${DEPLOY_PATH:-/home/jf/copilotos-bridge}"

# Functions
log_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
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
echo -e "${GREEN}  ✅ Cache Cleared Successfully${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Hard refresh your browser: Ctrl+Shift+R (or Cmd+Shift+R on Mac)"
echo "  2. Test the application to verify new version is loaded"
echo ""
