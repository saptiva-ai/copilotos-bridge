#!/bin/bash
# Quick diagnostic script for troubleshooting Copilotos Bridge issues
# Usage: ./scripts/quick-diagnostic.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_NAME=${COMPOSE_PROJECT_NAME:-copilotos}

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🔍 Copilotos Bridge Quick Diagnostic${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ============================================================================
# 1. Container Status
# ============================================================================
echo -e "${YELLOW}1. Checking Container Status...${NC}"
CONTAINERS=("${PROJECT_NAME}-api" "${PROJECT_NAME}-web" "${PROJECT_NAME}-mongodb" "${PROJECT_NAME}-redis")
ALL_RUNNING=true

for container in "${CONTAINERS[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "  ${GREEN}✓${NC} ${container} is running"
    else
        echo -e "  ${RED}✗${NC} ${container} is NOT running"
        ALL_RUNNING=false
    fi
done
echo ""

if [ "$ALL_RUNNING" = false ]; then
    echo -e "${RED}⚠️  Some containers are not running. Run: make dev${NC}"
    echo ""
fi

# ============================================================================
# 2. Health Checks
# ============================================================================
echo -e "${YELLOW}2. Running Health Checks...${NC}"

# API Health
if curl -sf http://localhost:8001/api/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} API health endpoint responding"
else
    echo -e "  ${RED}✗${NC} API health endpoint not responding"
    echo -e "    Check logs: ${BLUE}make logs-api${NC}"
fi

# Frontend Health
if curl -sf http://localhost:3000/healthz > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Frontend health check passing"
else
    # Try alternative health check
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Frontend is responding"
    else
        echo -e "  ${RED}✗${NC} Frontend not responding"
        echo -e "    Check logs: ${BLUE}make logs-web${NC}"
    fi
fi

# MongoDB Connection
if docker exec ${PROJECT_NAME}-mongodb mongosh --eval "db.runCommand('ping')" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} MongoDB connection successful"
else
    echo -e "  ${RED}✗${NC} MongoDB connection failed"
    echo -e "    Check logs: ${BLUE}docker logs ${PROJECT_NAME}-mongodb${NC}"
fi

# Redis Connection
if docker exec ${PROJECT_NAME}-redis redis-cli ping > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Redis connection successful"
else
    echo -e "  ${RED}✗${NC} Redis connection failed"
    echo -e "    Check logs: ${BLUE}docker logs ${PROJECT_NAME}-redis${NC}"
fi
echo ""

# ============================================================================
# 3. Volume Mounts (Important for Code Sync)
# ============================================================================
echo -e "${YELLOW}3. Checking Volume Mounts...${NC}"
API_MOUNTS=$(docker inspect ${PROJECT_NAME}-api --format='{{range .Mounts}}{{.Destination}}{{"\n"}}{{end}}' 2>/dev/null)

if echo "$API_MOUNTS" | grep -q "/app/src"; then
    echo -e "  ${GREEN}✓${NC} API source code is volume mounted"
    echo -e "    This ensures latest code is always used"
else
    echo -e "  ${YELLOW}⚠${NC}  API source code is NOT volume mounted"
    echo -e "    Code changes require rebuild: ${BLUE}make rebuild-api${NC}"
fi
echo ""

# ============================================================================
# 4. File Sync Check (if volume mounted)
# ============================================================================
if echo "$API_MOUNTS" | grep -q "/app/src"; then
    echo -e "${YELLOW}4. Verifying File Synchronization...${NC}"

    # Check models/chat.py
    LOCAL_MD5=$(md5sum apps/api/src/models/chat.py 2>/dev/null | cut -d' ' -f1)
    CONTAINER_MD5=$(docker exec ${PROJECT_NAME}-api md5sum /app/src/models/chat.py 2>/dev/null | cut -d' ' -f1)

    if [ "$LOCAL_MD5" = "$CONTAINER_MD5" ]; then
        echo -e "  ${GREEN}✓${NC} models/chat.py is in sync"
    else
        echo -e "  ${RED}✗${NC} models/chat.py differs between host and container"
        echo -e "    Local:     $LOCAL_MD5"
        echo -e "    Container: $CONTAINER_MD5"
        echo -e "    ${YELLOW}Try restarting: make restart${NC}"
    fi
    echo ""
fi

# ============================================================================
# 5. Database Collections
# ============================================================================
echo -e "${YELLOW}5. Checking Database Collections...${NC}"
DB_COLLECTIONS=$(docker exec ${PROJECT_NAME}-mongodb mongosh copilotos \
    --eval "db.getCollectionNames().forEach(function(c) { print(c + ':' + db[c].countDocuments({})); })" \
    --quiet 2>/dev/null || echo "")

if [ -n "$DB_COLLECTIONS" ]; then
    echo "$DB_COLLECTIONS" | while read -r line; do
        echo -e "  ${BLUE}•${NC} $line"
    done
else
    echo -e "  ${RED}✗${NC} Cannot connect to database"
fi
echo ""

# ============================================================================
# 6. Recent Errors in Logs
# ============================================================================
echo -e "${YELLOW}6. Checking for Recent Errors...${NC}"
RECENT_ERRORS=$(docker logs ${PROJECT_NAME}-api --tail=50 2>&1 | grep -iE "error|exception|failed" | head -5)

if [ -z "$RECENT_ERRORS" ]; then
    echo -e "  ${GREEN}✓${NC} No recent errors found in API logs"
else
    echo -e "  ${YELLOW}⚠${NC}  Recent errors detected:"
    echo "$RECENT_ERRORS" | while read -r line; do
        echo -e "    ${RED}•${NC} $line"
    done
    echo -e "    View full logs: ${BLUE}make logs-api${NC}"
fi
echo ""

# ============================================================================
# 7. Environment Variables Check
# ============================================================================
echo -e "${YELLOW}7. Checking Critical Environment Variables...${NC}"

# Check if SAPTIVA_API_KEY is set
SAPTIVA_KEY=$(docker exec ${PROJECT_NAME}-api env 2>/dev/null | grep "SAPTIVA_API_KEY=" | cut -d'=' -f2)
if [ -n "$SAPTIVA_KEY" ] && [ "$SAPTIVA_KEY" != "" ]; then
    echo -e "  ${GREEN}✓${NC} SAPTIVA_API_KEY is configured"
else
    echo -e "  ${YELLOW}⚠${NC}  SAPTIVA_API_KEY not found or empty"
    echo -e "    Set it in envs/.env file"
fi

# Check MongoDB URL
MONGODB_URL=$(docker exec ${PROJECT_NAME}-api env 2>/dev/null | grep "MONGODB_URL=" | cut -d'=' -f2)
if [ -n "$MONGODB_URL" ]; then
    echo -e "  ${GREEN}✓${NC} MONGODB_URL is configured"
else
    echo -e "  ${RED}✗${NC} MONGODB_URL not found"
fi

# Check Redis URL
REDIS_URL=$(docker exec ${PROJECT_NAME}-api env 2>/dev/null | grep "REDIS_URL=" | cut -d'=' -f2)
if [ -n "$REDIS_URL" ]; then
    echo -e "  ${GREEN}✓${NC} REDIS_URL is configured"
else
    echo -e "  ${RED}✗${NC} REDIS_URL not found"
fi
echo ""

# ============================================================================
# 8. Port Availability
# ============================================================================
echo -e "${YELLOW}8. Checking Port Availability...${NC}"

check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Port $port ($service) is in use"
    else
        echo -e "  ${RED}✗${NC} Port $port ($service) is not in use"
    fi
}

check_port 3000 "Frontend"
check_port 8001 "API"
check_port 27018 "MongoDB"
check_port 6380 "Redis"
echo ""

# ============================================================================
# Summary & Recommendations
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  📋 Summary & Quick Actions${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ "$ALL_RUNNING" = false ]; then
    echo -e "${RED}🔴 Action Required:${NC} Start services"
    echo -e "   ${BLUE}make dev${NC}"
    echo ""
fi

echo -e "${GREEN}Useful Commands:${NC}"
echo -e "  ${BLUE}make help${NC}              - Show all available commands"
echo -e "  ${BLUE}make health${NC}            - Run health checks"
echo -e "  ${BLUE}make logs${NC}              - View all service logs"
echo -e "  ${BLUE}make debug-full${NC}        - Complete diagnostic report"
echo -e "  ${BLUE}make db-collections${NC}    - Show database collections"
echo -e "  ${BLUE}make create-demo-user${NC}  - Create demo user for testing"
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Diagnostic complete${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
