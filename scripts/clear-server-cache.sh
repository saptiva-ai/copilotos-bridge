#!/bin/bash
# ========================================
# CLEAR SERVER CACHE
# ========================================
# Clears Redis cache and restarts web container
# to ensure the latest version is served
#
# Usage: ./scripts/clear-server-cache.sh

set -e

# Configuration
DEPLOY_SERVER="${DEPLOY_SERVER:-jf@34.42.214.246}"
DEPLOY_PATH="${DEPLOY_PATH:-/home/jf/copilotos-bridge}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🧹 Clearing Server Cache${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}→${NC} Flushing Redis cache..."
ssh "$DEPLOY_SERVER" "docker exec copilotos-redis redis-cli -a \$(grep REDIS_PASSWORD $DEPLOY_PATH/infra/.env | cut -d= -f2) FLUSHALL" 2>/dev/null
echo -e "${GREEN}✓${NC} Redis cache cleared"

echo -e "${YELLOW}→${NC} Restarting web container..."
ssh "$DEPLOY_SERVER" "docker restart copilotos-web" >/dev/null
echo -e "${GREEN}✓${NC} Web container restarted"

echo ""
echo -e "${YELLOW}→${NC} Waiting for container to be healthy (15 seconds)..."
sleep 15

echo -e "${YELLOW}→${NC} Verifying deployment..."
STATUS=$(ssh "$DEPLOY_SERVER" "docker ps --format '{{.Status}}' --filter name=copilotos-web" 2>/dev/null)
echo -e "${GREEN}✓${NC} Container status: $STATUS"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ Cache cleared successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Test in browser (hard refresh: Ctrl+Shift+R)"
echo "  2. Or test in incognito mode"
echo "  3. If still cached, purge Cloudflare cache"
echo ""
