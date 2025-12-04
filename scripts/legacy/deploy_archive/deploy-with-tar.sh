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
# Environment variables (loaded from envs/.env.prod if present):
#   PROD_SERVER_HOST: SSH target (e.g., user@ip-address)
#   PROD_DEPLOY_PATH: Remote deployment path
#   PROD_DOMAIN: Production domain (for display)
#   DEPLOY_SERVER: Legacy alias for PROD_SERVER_HOST
#   DEPLOY_PATH: Legacy alias for PROD_DEPLOY_PATH
#
# Configuration: Run 'make setup-interactive-prod' to configure

set -e  # Exit on error

# Status symbols for output
RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "
NC=""

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_DIR="$HOME"

# Load production environment if available
if [ -f "$PROJECT_ROOT/envs/.env.prod" ]; then
    source "$PROJECT_ROOT/envs/.env.prod"
elif [ -f "$PROJECT_ROOT/envs/.env" ]; then
    source "$PROJECT_ROOT/envs/.env"
fi

# Use environment variables with fallback to legacy defaults
# Priority: PROD_SERVER_HOST > DEPLOY_SERVER > fallback
DEPLOY_SERVER="${DEPLOY_SERVER:-${PROD_SERVER_HOST:-your-ssh-user@your-server-ip-here}}"
DEPLOY_PATH="${DEPLOY_PATH:-${PROD_DEPLOY_PATH:-/opt/octavios-bridge}}"
PROD_DOMAIN="${PROD_DOMAIN:-your-domain.com}"

# Validate configuration
if [ "$DEPLOY_SERVER" = "your-ssh-user@your-server-ip-here" ]; then
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}▲  ERROR: Production server not configured!${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}Please configure production deployment settings:${NC}"
    echo ""
    echo -e "  ${GREEN}make setup-interactive-prod${NC}"
    echo ""
    echo -e "${YELLOW}Or manually create envs/.env.prod with:${NC}"
    echo "  PROD_SERVER_IP=your-actual-server-ip"
    echo "  PROD_SERVER_USER=your-ssh-user"
    echo "  PROD_DEPLOY_PATH=/path/to/deployment"
    echo "  PROD_DOMAIN=your-domain.com"
    echo ""
    exit 1
fi

# Flags
SKIP_BUILD=false
SKIP_TRANSFER=false
INCREMENTAL=false
PARALLEL=false

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
    --incremental)
      INCREMENTAL=true
      shift
      ;;
    --parallel)
      PARALLEL=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 ▸"
      echo ""
      echo "Options:"
      echo "  --skip-build      Skip building images (use existing)"
      echo "  --skip-transfer   Skip transfer (images already on server)"
      echo "  --incremental     Use incremental build (with cache, faster)"
      echo "  --parallel        Use parallel export+transfer (experimental)"
      echo "  -h, --help        Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                       # Full deployment with clean build"
      echo "  $0 --incremental         # Fast deployment with cached build"
      echo "  $0 --skip-build          # Use existing images"
      echo "  $0 --incremental --parallel  # Fastest (experimental)"
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
    echo -e "${GREEN}${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}${NC} $1"
}

log_error() {
    echo -e "${RED}${NC} $1"
}

step() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}$1${NC}"
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

    # Store local commit for later comparison
    LOCAL_COMMIT=$(git log -1 --format="%h")
    LOCAL_COMMIT_MSG=$(git log -1 --format="%h - %s")
    log_info "Deploying commit: $LOCAL_COMMIT_MSG"
}

# Build images
build_images() {
    step "Step 1/6: Building Docker Images"

    cd "$PROJECT_ROOT"

    if [ "$INCREMENTAL" = true ]; then
        log_info "Building with cache (incremental mode)..."
        log_warning "This is faster but may not include all changes if dependencies changed"

        log_info "Building API image..."
        docker build -f apps/api/Dockerfile -t infra-api:latest --target production apps/api

        log_info "Building Web image..."
        docker build -f apps/web/Dockerfile \
            --build-arg NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8001}" \
            --build-arg NEXT_PUBLIC_MAX_FILE_SIZE_MB="${NEXT_PUBLIC_MAX_FILE_SIZE_MB:-50}" \
            -t infra-web:latest \
            --target runner .
    else
        log_info "Building with --no-cache to ensure latest code..."

        log_info "Building API image..."
        docker build -f apps/api/Dockerfile -t infra-api:latest --target production --no-cache apps/api

        log_info "Building Web image..."
        docker build -f apps/web/Dockerfile \
            --build-arg NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8001}" \
            --build-arg NEXT_PUBLIC_MAX_FILE_SIZE_MB="${NEXT_PUBLIC_MAX_FILE_SIZE_MB:-50}" \
            -t infra-web:latest \
            --target runner \
            --no-cache .
    fi

    log_success "Images built successfully"
}

# Tag images with correct names
tag_images() {
    step "Step 2/6: Tagging Images"

    # Docker compose creates images with project name prefix (infra-*)
    # But uses them with compose service names (octavios-*)
    # We need both tags for compatibility

    log_info "Tagging infra-api:latest -> octavios-api:latest"
    docker tag infra-api:latest octavios-api:latest

    log_info "Tagging infra-web:latest -> octavios-web:latest"
    docker tag infra-web:latest octavios-web:latest

    log_success "Images tagged correctly"
}

# Export to tar
export_images() {
    step "Step 3/6: Exporting Images to TAR"

    cd "$TEMP_DIR"

    if [ "$PARALLEL" = true ]; then
        log_info "Exporting images in parallel..."
        docker save octavios-api:latest | gzip > octavios-api.tar.gz &
        API_PID=$!
        docker save octavios-web:latest | gzip > octavios-web.tar.gz &
        WEB_PID=$!

        wait $API_PID
        API_SIZE=$(ls -lh octavios-api.tar.gz | awk '{print $5}')
        log_success "API exported: $API_SIZE"

        wait $WEB_PID
        WEB_SIZE=$(ls -lh octavios-web.tar.gz | awk '{print $5}')
        log_success "Web exported: $WEB_SIZE"
    else
        log_info "Exporting API image (this may take 1-2 minutes)..."
        docker save octavios-api:latest | gzip > octavios-api.tar.gz
        API_SIZE=$(ls -lh octavios-api.tar.gz | awk '{print $5}')
        log_success "API exported: $API_SIZE"

        log_info "Exporting Web image (this may take 2-3 minutes)..."
        docker save octavios-web:latest | gzip > octavios-web.tar.gz
        WEB_SIZE=$(ls -lh octavios-web.tar.gz | awk '{print $5}')
        log_success "Web exported: $WEB_SIZE"
    fi
}

# Transfer to server
transfer_images() {
    step "Step 4/6: Transferring to Production Server"

    cd "$TEMP_DIR"

    log_info "Transferring to $DEPLOY_SERVER:$DEPLOY_PATH..."
    log_info "This may take 3-5 minutes depending on connection..."

    scp octavios-api.tar.gz octavios-web.tar.gz "$DEPLOY_SERVER:$DEPLOY_PATH/"

    log_success "Transfer completed"
}

# Load images on server
load_images() {
    step "Step 5/6: Loading Images on Server"

    # Update code on server first
    log_info "Updating code on server (git pull)..."
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH && git pull origin main"

    # Verify server has correct commit
    SERVER_COMMIT=$(ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH && git log -1 --format='%h - %s'")
    log_info "Server commit: $SERVER_COMMIT"

    log_info "Stopping containers..."
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH/infra && docker compose down"

    log_info "Removing old images..."
    ssh "$DEPLOY_SERVER" "docker rmi octavios-web:latest octavios-api:latest 2>/dev/null || true"

    log_info "Loading new images (this may take 2-3 minutes)..."
    ssh "$DEPLOY_SERVER" "
        cd $DEPLOY_PATH && \
        gunzip -c octavios-api.tar.gz | docker load && \
        gunzip -c octavios-web.tar.gz | docker load
    "

    log_success "Images loaded successfully"
}

# Start containers
start_containers() {
    step "Step 6/6: Starting Containers"

    log_info "Creating compose override to use loaded images..."
    ssh "$DEPLOY_SERVER" "cat > $DEPLOY_PATH/infra/docker-compose.override.yml <<'EOF'
version: '3.8'
services:
  api:
    image: octavios-api:latest
    build: {}
  web:
    image: octavios-web:latest
    build: {}
EOF
"

    log_info "Starting services with loaded production images..."
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH/infra && docker compose up -d"

    log_info "Cleaning up override file..."
    ssh "$DEPLOY_SERVER" "rm -f $DEPLOY_PATH/infra/docker-compose.override.yml"

    log_info "Waiting for services to be healthy (30 seconds)..."
    sleep 30

    # Verify deployment
    log_info "Verifying deployment..."
    HEALTH_STATUS=$(ssh "$DEPLOY_SERVER" "curl -s http://localhost:8001/api/health | jq -r '.status'" 2>/dev/null || echo "error")

    if [ "$HEALTH_STATUS" = "healthy" ]; then
        log_success "API is healthy"
    else
        log_error "API health check failed: $HEALTH_STATUS"
        log_warning "Check logs with: ssh $DEPLOY_SERVER 'docker logs octavios-prod-api'"
    fi

    # Verify web container is using production build (no webpack dev warnings)
    log_info "Verifying Web is using production build..."
    WEB_LOGS=$(ssh "$DEPLOY_SERVER" "docker logs octavios-prod-web 2>&1 | tail -5")
    if echo "$WEB_LOGS" | grep -q "webpack"; then
        log_error "Web is running in development mode!"
        log_warning "Check logs with: ssh $DEPLOY_SERVER 'docker logs octavios-prod-web'"
    else
        log_success "Web is running in production mode"
    fi
}

# Cleanup
cleanup() {
    step "Cleanup"

    log_info "Removing local tar files..."
    cd "$TEMP_DIR"
    rm -f octavios-api.tar.gz octavios-web.tar.gz

    log_info "Removing server tar files..."
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH && rm -f octavios-*.tar.gz"

    log_success "Cleanup completed"
}

# Show summary
show_summary() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}DEPLOYMENT COMPLETED SUCCESSFULLY${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Get server commit
    SERVER_COMMIT=$(ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH && git log -1 --format='%h'")

    echo -e "${BLUE}Deployed commit:${NC}"
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH && git log -1 --format='  %h - %s (%ar)'"

    # Compare commits
    if [ "$LOCAL_COMMIT" != "$SERVER_COMMIT" ]; then
        echo ""
        log_warning "Local commit ($LOCAL_COMMIT) differs from server commit ($SERVER_COMMIT)"
        echo "  This might happen if:"
        echo "  - Server had uncommitted changes"
        echo "  - Git pull brought in different commits"
        echo "  - Someone else pushed to the server"
    fi

    echo ""
    echo -e "${BLUE}Running containers:${NC}"
    ssh "$DEPLOY_SERVER" "docker ps --format '  {{.Names}}\t{{.Status}}' | grep octavios"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Clear cache: make clear-cache"
    echo "  2. Test the application: https://$PROD_DOMAIN"
    echo "  3. Hard refresh browser: Ctrl+Shift+R (or Cmd+Shift+R)"
    echo "  4. Monitor logs: ssh $DEPLOY_SERVER 'docker logs -f octavios-api'"
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
