#!/bin/bash
# ========================================
# COPILOTOS BRIDGE - TAR DEPLOYMENT SCRIPT
# ========================================
# Automated deployment using tar file transfer
# Usage: ./scripts/deploy-with-tar.sh [--skip-build] [--skip-transfer]
#
# This script:
# 1. Builds Docker images locally (with --no-cache)
# 2. Tags them correctly for docker-compose compatibility
# 3. Exports to compressed tar files
# 4. Transfers to production server
# 5. Loads images and restarts containers
#
# Environment variables:
#   DEPLOY_SERVER: SSH target (default: jf@34.42.214.246)
#   DEPLOY_PATH: Remote path (default: /home/jf/copilotos-bridge)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_SERVER="${DEPLOY_SERVER:-jf@34.42.214.246}"
DEPLOY_PATH="${DEPLOY_PATH:-/home/jf/copilotos-bridge}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_DIR="$HOME"

# Flags
SKIP_BUILD=false
SKIP_TRANSFER=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    --skip-transfer)
      SKIP_TRANSFER=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --skip-build      Skip building images (use existing)"
      echo "  --skip-transfer   Skip transfer (images already on server)"
      echo "  -h, --help        Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

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

step() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN} $1${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Verify we're on main branch
verify_branch() {
    cd "$PROJECT_ROOT"
    CURRENT_BRANCH=$(git branch --show-current)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        log_warning "Current branch is '$CURRENT_BRANCH', not 'main'"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Deployment cancelled"
            exit 1
        fi
    fi

    COMMIT=$(git log -1 --format="%h - %s")
    log_info "Deploying commit: $COMMIT"
}

# Build images
build_images() {
    step "Step 1/6: Building Docker Images"

    cd "$PROJECT_ROOT/infra"
    log_info "Building with --no-cache to ensure latest code..."

    env UID=$(id -u) GID=$(id -g) docker compose -f docker-compose.yml build --no-cache api web

    log_success "Images built successfully"
}

# Tag images with correct names
tag_images() {
    step "Step 2/6: Tagging Images"

    # Docker compose creates images with project name prefix (infra-*)
    # But uses them with compose service names (copilotos-*)
    # We need both tags for compatibility

    log_info "Tagging infra-api:latest -> copilotos-api:latest"
    docker tag infra-api:latest copilotos-api:latest

    log_info "Tagging infra-web:latest -> copilotos-web:latest"
    docker tag infra-web:latest copilotos-web:latest

    log_success "Images tagged correctly"
}

# Export to tar
export_images() {
    step "Step 3/6: Exporting Images to TAR"

    cd "$TEMP_DIR"

    log_info "Exporting API image (this may take 1-2 minutes)..."
    docker save copilotos-api:latest | gzip > copilotos-api.tar.gz
    API_SIZE=$(ls -lh copilotos-api.tar.gz | awk '{print $5}')
    log_success "API exported: $API_SIZE"

    log_info "Exporting Web image (this may take 2-3 minutes)..."
    docker save copilotos-web:latest | gzip > copilotos-web.tar.gz
    WEB_SIZE=$(ls -lh copilotos-web.tar.gz | awk '{print $5}')
    log_success "Web exported: $WEB_SIZE"
}

# Transfer to server
transfer_images() {
    step "Step 4/6: Transferring to Production Server"

    cd "$TEMP_DIR"

    log_info "Transferring to $DEPLOY_SERVER:$DEPLOY_PATH..."
    log_info "This may take 3-5 minutes depending on connection..."

    scp copilotos-api.tar.gz copilotos-web.tar.gz "$DEPLOY_SERVER:$DEPLOY_PATH/"

    log_success "Transfer completed"
}

# Load images on server
load_images() {
    step "Step 5/6: Loading Images on Server"

    log_info "Stopping containers..."
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH/infra && docker compose down"

    log_info "Removing old images..."
    ssh "$DEPLOY_SERVER" "docker rmi copilotos-web:latest copilotos-api:latest 2>/dev/null || true"

    log_info "Loading new images (this may take 2-3 minutes)..."
    ssh "$DEPLOY_SERVER" "
        cd $DEPLOY_PATH && \
        gunzip -c copilotos-api.tar.gz | docker load && \
        gunzip -c copilotos-web.tar.gz | docker load
    "

    log_success "Images loaded successfully"
}

# Start containers
start_containers() {
    step "Step 6/6: Starting Containers"

    log_info "Starting services..."
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH/infra && docker compose up -d"

    log_info "Waiting for services to be healthy (30 seconds)..."
    sleep 30

    # Verify deployment
    log_info "Verifying deployment..."
    HEALTH_STATUS=$(ssh "$DEPLOY_SERVER" "curl -s http://localhost:8001/api/health | jq -r '.status'" 2>/dev/null || echo "error")

    if [ "$HEALTH_STATUS" = "healthy" ]; then
        log_success "API is healthy"
    else
        log_error "API health check failed: $HEALTH_STATUS"
        log_warning "Check logs with: ssh $DEPLOY_SERVER 'docker logs copilotos-api'"
    fi

    # Check if SessionExpiredModal exists (verification of new code)
    if ssh "$DEPLOY_SERVER" "docker exec copilotos-web ls /app/apps/web/src/components/auth/SessionExpiredModal.tsx" &>/dev/null; then
        log_success "New code verified (SessionExpiredModal.tsx exists)"
    else
        log_warning "Could not verify new code deployment"
    fi
}

# Cleanup
cleanup() {
    step "Cleanup"

    log_info "Removing local tar files..."
    cd "$TEMP_DIR"
    rm -f copilotos-api.tar.gz copilotos-web.tar.gz

    log_info "Removing server tar files..."
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH && rm -f copilotos-*.tar.gz"

    log_success "Cleanup completed"
}

# Show summary
show_summary() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✅ DEPLOYMENT COMPLETED SUCCESSFULLY${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}Deployed commit:${NC}"
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH && git log -1 --format='  %h - %s (%ar)'"
    echo ""
    echo -e "${BLUE}Running containers:${NC}"
    ssh "$DEPLOY_SERVER" "docker ps --format '  {{.Names}}\t{{.Status}}' | grep copilotos"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Test the application: https://copiloto.saptiva.com"
    echo "  2. If you see old version, purge Cloudflare cache"
    echo "  3. Monitor logs: ssh $DEPLOY_SERVER 'docker logs -f copilotos-api'"
    echo ""
}

# Main execution
main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  COPILOTOS BRIDGE - AUTOMATED TAR DEPLOYMENT                  ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    verify_branch

    if [ "$SKIP_BUILD" = false ]; then
        build_images
        tag_images
        export_images
    else
        log_warning "Skipping build (using existing images)"
        tag_images
    fi

    if [ "$SKIP_TRANSFER" = false ]; then
        transfer_images
    else
        log_warning "Skipping transfer (assuming images already on server)"
    fi

    load_images
    start_containers
    cleanup
    show_summary
}

# Run main function
main "$@"
