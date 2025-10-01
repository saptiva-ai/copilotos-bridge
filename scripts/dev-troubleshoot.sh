#!/bin/bash
# Development troubleshooting script - fixes common issues
# Usage: ./scripts/dev-troubleshoot.sh [issue-type]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_NAME=${COMPOSE_PROJECT_NAME:-copilotos}

show_help() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  🛠️  Development Troubleshooting Tool${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${GREEN}Usage:${NC}"
    echo -e "  ./scripts/dev-troubleshoot.sh [issue-type]"
    echo ""
    echo -e "${GREEN}Issue Types:${NC}"
    echo -e "  ${YELLOW}ports${NC}           - Fix port conflicts"
    echo -e "  ${YELLOW}permissions${NC}     - Fix file permission issues"
    echo -e "  ${YELLOW}cache${NC}           - Clear all caches (Docker, Next.js, Python)"
    echo -e "  ${YELLOW}volumes${NC}         - Fix volume mount issues"
    echo -e "  ${YELLOW}rebuild${NC}         - Full rebuild with clean slate"
    echo -e "  ${YELLOW}database${NC}        - Fix database connection issues"
    echo -e "  ${YELLOW}redis${NC}           - Fix Redis connection issues"
    echo -e "  ${YELLOW}all${NC}             - Run all fixes (nuclear option)"
    echo ""
    echo -e "${GREEN}Examples:${NC}"
    echo -e "  ./scripts/dev-troubleshoot.sh ports"
    echo -e "  ./scripts/dev-troubleshoot.sh cache"
    echo -e "  ./scripts/dev-troubleshoot.sh all"
    echo ""
}

fix_ports() {
    echo -e "${YELLOW}Fixing port conflicts...${NC}"
    echo ""

    # Check for processes on common ports
    PORTS=(3000 8001 27018 6380)
    for port in "${PORTS[@]}"; do
        PID=$(lsof -ti:$port 2>/dev/null || echo "")
        if [ -n "$PID" ]; then
            echo -e "  ${YELLOW}Port $port is in use by PID $PID${NC}"
            read -p "    Kill process? [y/N] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                kill -9 $PID 2>/dev/null || true
                echo -e "    ${GREEN}✓ Process killed${NC}"
            fi
        else
            echo -e "  ${GREEN}✓ Port $port is available${NC}"
        fi
    done

    echo ""
    echo -e "${GREEN}✓ Port conflict check complete${NC}"
    echo ""
}

fix_permissions() {
    echo -e "${YELLOW}Fixing file permissions...${NC}"
    echo ""

    # Fix ownership of common directories
    if [ -d "apps/web/.next" ]; then
        echo -e "  Fixing Next.js build directory permissions..."
        sudo chown -R $(id -u):$(id -g) apps/web/.next 2>/dev/null || true
    fi

    if [ -d ".venv" ]; then
        echo -e "  Fixing Python venv permissions..."
        sudo chown -R $(id -u):$(id -g) .venv 2>/dev/null || true
    fi

    # Fix node_modules if exists
    if [ -d "apps/web/node_modules" ]; then
        echo -e "  Fixing node_modules permissions..."
        sudo chown -R $(id -u):$(id -g) apps/web/node_modules 2>/dev/null || true
    fi

    echo ""
    echo -e "${GREEN}✓ Permissions fixed${NC}"
    echo ""
}

fix_cache() {
    echo -e "${YELLOW}Clearing all caches...${NC}"
    echo ""

    # Stop services first
    echo -e "  Stopping services..."
    docker compose -p ${PROJECT_NAME} -f infra/docker-compose.yml -f infra/docker-compose.dev.yml down 2>/dev/null || true

    # Clear Next.js cache
    echo -e "  Clearing Next.js cache..."
    rm -rf apps/web/.next 2>/dev/null || true
    rm -rf apps/web/.swc 2>/dev/null || true

    # Clear Python cache
    echo -e "  Clearing Python cache..."
    find apps/api -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find apps/api -type f -name "*.pyc" -delete 2>/dev/null || true

    # Clear Docker build cache
    echo -e "  Clearing Docker build cache..."
    docker builder prune -f 2>/dev/null || true

    # Clear dangling Docker volumes
    echo -e "  Clearing dangling volumes..."
    docker volume prune -f 2>/dev/null || true

    echo ""
    echo -e "${GREEN}✓ All caches cleared${NC}"
    echo -e "${BLUE}Run 'make dev' to restart services${NC}"
    echo ""
}

fix_volumes() {
    echo -e "${YELLOW}Fixing volume mount issues...${NC}"
    echo ""

    # Check if volume mounts exist
    if docker ps -a --format '{{.Names}}' | grep -q "${PROJECT_NAME}-api"; then
        echo -e "  Checking API volume mounts..."
        MOUNTS=$(docker inspect ${PROJECT_NAME}-api --format='{{range .Mounts}}{{.Destination}}{{"\n"}}{{end}}' 2>/dev/null)

        if echo "$MOUNTS" | grep -q "/app/src"; then
            echo -e "  ${GREEN}✓ API source code is mounted${NC}"
        else
            echo -e "  ${YELLOW}⚠ API source code is NOT mounted${NC}"
            echo -e "    Add this to infra/docker-compose.yml under api service:"
            echo -e "    ${BLUE}volumes:${NC}"
            echo -e "    ${BLUE}  - ../apps/api/src:/app/src:ro${NC}"
        fi
    fi

    # Recreate volumes
    echo -e "  Recreating containers to apply volume changes..."
    docker compose -p ${PROJECT_NAME} -f infra/docker-compose.yml -f infra/docker-compose.dev.yml down 2>/dev/null || true
    docker compose -p ${PROJECT_NAME} -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up -d 2>/dev/null || true

    echo ""
    echo -e "${GREEN}✓ Volume configuration updated${NC}"
    echo ""
}

fix_rebuild() {
    echo -e "${RED}⚠️  Full rebuild - this will take several minutes${NC}"
    echo ""
    read -p "Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Cancelled${NC}"
        exit 0
    fi

    echo -e "${YELLOW}Starting full rebuild...${NC}"
    echo ""

    # Stop everything
    echo -e "  1. Stopping all services..."
    docker compose -p ${PROJECT_NAME} -f infra/docker-compose.yml -f infra/docker-compose.dev.yml down 2>/dev/null || true

    # Clear caches
    echo -e "  2. Clearing caches..."
    rm -rf apps/web/.next 2>/dev/null || true
    find apps/api -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

    # Rebuild without cache
    echo -e "  3. Rebuilding all containers (this may take 5-10 minutes)..."
    docker compose -p ${PROJECT_NAME} -f infra/docker-compose.yml -f infra/docker-compose.dev.yml build --no-cache

    # Start services
    echo -e "  4. Starting services..."
    docker compose -p ${PROJECT_NAME} -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up -d

    echo ""
    echo -e "${GREEN}✓ Full rebuild complete${NC}"
    echo -e "${BLUE}Waiting for services to be healthy...${NC}"
    sleep 15
    echo ""
}

fix_database() {
    echo -e "${YELLOW}Fixing database connection issues...${NC}"
    echo ""

    # Check MongoDB container
    if docker ps --format '{{.Names}}' | grep -q "${PROJECT_NAME}-mongodb"; then
        echo -e "  ${GREEN}✓ MongoDB container is running${NC}"

        # Test connection
        if docker exec ${PROJECT_NAME}-mongodb mongosh --eval "db.runCommand('ping')" > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓ MongoDB is accepting connections${NC}"
        else
            echo -e "  ${RED}✗ MongoDB not responding${NC}"
            echo -e "    Restarting MongoDB..."
            docker restart ${PROJECT_NAME}-mongodb
            sleep 5
        fi
    else
        echo -e "  ${RED}✗ MongoDB container not running${NC}"
        echo -e "    Starting MongoDB..."
        docker compose -p ${PROJECT_NAME} -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up -d mongodb
    fi

    echo ""
    echo -e "${GREEN}✓ Database check complete${NC}"
    echo ""
}

fix_redis() {
    echo -e "${YELLOW}Fixing Redis connection issues...${NC}"
    echo ""

    # Check Redis container
    if docker ps --format '{{.Names}}' | grep -q "${PROJECT_NAME}-redis"; then
        echo -e "  ${GREEN}✓ Redis container is running${NC}"

        # Test connection
        if docker exec ${PROJECT_NAME}-redis redis-cli ping > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓ Redis is accepting connections${NC}"
        else
            echo -e "  ${RED}✗ Redis not responding${NC}"
            echo -e "    Restarting Redis..."
            docker restart ${PROJECT_NAME}-redis
            sleep 5
        fi
    else
        echo -e "  ${RED}✗ Redis container not running${NC}"
        echo -e "    Starting Redis..."
        docker compose -p ${PROJECT_NAME} -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up -d redis
    fi

    # Clear Redis cache
    echo -e "  Clearing Redis cache..."
    docker exec ${PROJECT_NAME}-redis redis-cli -a redis_password_change_me FLUSHALL 2>/dev/null || true

    echo ""
    echo -e "${GREEN}✓ Redis check complete${NC}"
    echo ""
}

fix_all() {
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  ⚠️  NUCLEAR OPTION - Full System Reset${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "This will:"
    echo -e "  • Stop all services"
    echo -e "  • Clear all caches"
    echo -e "  • Fix permissions"
    echo -e "  • Rebuild containers"
    echo -e "  • Restart everything"
    echo ""
    read -p "Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Cancelled${NC}"
        exit 0
    fi

    fix_ports
    fix_cache
    fix_permissions
    fix_rebuild
    fix_database
    fix_redis

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✓ All fixes applied${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Main script logic
case "${1:-}" in
    ports)
        fix_ports
        ;;
    permissions)
        fix_permissions
        ;;
    cache)
        fix_cache
        ;;
    volumes)
        fix_volumes
        ;;
    rebuild)
        fix_rebuild
        ;;
    database)
        fix_database
        ;;
    redis)
        fix_redis
        ;;
    all)
        fix_all
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac
