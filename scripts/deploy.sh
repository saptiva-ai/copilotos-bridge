#!/bin/bash
# ========================================
# COPILOTOS BRIDGE - CONSOLIDATED DEPLOYMENT SCRIPT
# ========================================
# Unified deployment with versioning and automatic rollback
#
# Features:
# ✅ Multiple deployment methods (tar, registry, local)
# ✅ Automatic versioning (git SHA + timestamp)
# ✅ Pre-deployment backup
# ✅ Health check validation
# ✅ Automatic rollback on failure
# ✅ Manual rollback support
# ✅ Deployment history tracking
#
# Usage:
#   ./scripts/deploy.sh [METHOD] [OPTIONS]
#
# Methods:
#   tar       Transfer images via tar files (default, no registry needed)
#   registry  Pull from Docker registry (fastest if registry configured)
#   local     Deploy from local images (development)
#
# Options:
#   --skip-build       Skip building images
#   --skip-healthcheck Skip health verification (dangerous!)
#   --no-rollback      Don't rollback automatically on failure
#   --force            Skip confirmation prompts
#   --version VERSION  Deploy specific version (rollback use case)
#   -h, --help         Show this help
#
# Examples:
#   ./scripts/deploy.sh                    # Deploy via tar (default)
#   ./scripts/deploy.sh registry           # Deploy from GHCR
#   ./scripts/deploy.sh --skip-build       # Use existing images
#   ./scripts/deploy.sh --version abc123   # Deploy specific version
#
# Environment (from envs/.env.prod):
#   PROD_SERVER_HOST   SSH target (user@ip)
#   PROD_DEPLOY_PATH   Remote path (/opt/copilotos-bridge)
#   REGISTRY_URL       Docker registry (ghcr.io/...)

set -e
set -o pipefail

# ========================================
# CONFIGURATION
# ========================================
VERSION="1.0.0"
RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "
NC=""

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_HOME="$HOME/.copilotos-deploy"
VERSIONS_DIR="$DEPLOY_HOME/versions"
BACKUP_DIR="$DEPLOY_HOME/backups"

mkdir -p "$DEPLOY_HOME" "$VERSIONS_DIR" "$BACKUP_DIR"

# Load environment
if [ -f "$PROJECT_ROOT/envs/.env.prod" ]; then
    source "$PROJECT_ROOT/envs/.env.prod"
elif [ -f "$PROJECT_ROOT/envs/.env" ]; then
    source "$PROJECT_ROOT/envs/.env"
fi

# Variables with fallbacks
DEPLOY_SERVER="${DEPLOY_SERVER:-${PROD_SERVER_HOST:-}}"
DEPLOY_PATH="${DEPLOY_PATH:-${PROD_DEPLOY_PATH:-/opt/copilotos-bridge}}"
PROD_DOMAIN="${PROD_DOMAIN:-localhost}"
REGISTRY_URL="${REGISTRY_URL:-ghcr.io/saptiva-ai/copilotos-bridge}"

# ========================================
# PARSE ARGUMENTS
# ========================================
DEPLOY_METHOD="tar"
SKIP_BUILD=false
SKIP_HEALTHCHECK=false
NO_ROLLBACK=false
FORCE=false
SPECIFIC_VERSION=""

# First argument might be method
if [[ $# -gt 0 ]] && [[ ! "$1" =~ ^-- ]]; then
    case "$1" in
        tar|registry|local)
            DEPLOY_METHOD="$1"
            shift
            ;;
    esac
fi

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-healthcheck)
            SKIP_HEALTHCHECK=true
            shift
            ;;
        --no-rollback)
            NO_ROLLBACK=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --version)
            SPECIFIC_VERSION="$2"
            shift 2
            ;;
        -h|--help)
            cat << EOF
Consolidated Deployment Script v$VERSION

Usage: $0 [METHOD] [OPTIONS]

Methods:
  tar       Transfer via tar files (default, no registry)
  registry  Pull from Docker registry (requires GHCR access)
  local     Deploy from local images (dev only)

Options:
  --skip-build         Skip building images
  --skip-healthcheck   Skip health check (dangerous!)
  --no-rollback        Don't auto-rollback on failure
  --force              Skip confirmation prompts
  --version VERSION    Deploy specific version
  -h, --help           Show this help

Examples:
  $0                       # Deploy via tar
  $0 registry              # Deploy from registry
  $0 --version abc123      # Rollback to version

Configuration:
  Set in envs/.env.prod:
    PROD_SERVER_HOST=user@server-ip
    PROD_DEPLOY_PATH=/opt/copilotos-bridge
    REGISTRY_URL=ghcr.io/org/repo

EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h for help"
            exit 1
            ;;
    esac
done

# ========================================
# LOGGING FUNCTIONS
# ========================================
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✔${NC} $1"; }
log_warning() { echo -e "${YELLOW}▲${NC} $1"; }
log_error() { echo -e "${RED}✖${NC} $1"; }

step() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ========================================
# VALIDATION
# ========================================
validate_config() {
    if [ -z "$DEPLOY_SERVER" ]; then
        log_error "PROD_SERVER_HOST not configured!"
        echo ""
        echo "Configure in envs/.env.prod:"
        echo "  PROD_SERVER_HOST=user@server-ip"
        echo "  PROD_DEPLOY_PATH=/opt/copilotos-bridge"
        echo ""
        echo "Or run: make setup-interactive-prod"
        exit 1
    fi

    # Test SSH connection
    if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$DEPLOY_SERVER" "echo 2>&1" > /dev/null 2>&1; then
        log_error "Cannot connect to $DEPLOY_SERVER"
        echo "Check SSH keys and network connectivity"
        exit 1
    fi

    log_success "Configuration validated"
}

# ========================================
# VERSION MANAGEMENT
# ========================================
generate_version() {
    cd "$PROJECT_ROOT"
    local git_sha=$(git log -1 --format="%h")
    local timestamp=$(date +%Y%m%d-%H%M%S)
    echo "${git_sha}-${timestamp}"
}

get_current_version() {
    ssh "$DEPLOY_SERVER" "[ -f $DEPLOY_PATH/.deploy/current_version ] && \
        cat $DEPLOY_PATH/.deploy/current_version || echo 'none'" 2>/dev/null || echo "none"
}

save_version_info() {
    local version=$1
    local status=$2
    local method=$3
    local timestamp=$(date -Iseconds)

    # Local history
    echo "$timestamp|$version|$status|$method" >> "$VERSIONS_DIR/history.log"

    # Remote tracking
    ssh "$DEPLOY_SERVER" "
        mkdir -p $DEPLOY_PATH/.deploy
        echo '$timestamp|$version|$status|$method' >> $DEPLOY_PATH/.deploy/versions.log
        echo '$version' > $DEPLOY_PATH/.deploy/current_version
        echo '$method' > $DEPLOY_PATH/.deploy/current_method
    "
}

list_deployment_history() {
    log_info "Recent deployments:"
    if [ -f "$VERSIONS_DIR/history.log" ]; then
        tail -5 "$VERSIONS_DIR/history.log" | while IFS='|' read -r ts ver status method; do
            local color=$GREEN
            [[ "$status" == "failed" ]] && color=$RED
            [[ "$status" == "rollback" ]] && color=$YELLOW
            echo -e "  ${color}[$status]${NC} $ver (via $method) - $ts"
        done
    else
        echo "  No deployment history"
    fi
}

# ========================================
# BACKUP CURRENT VERSION
# ========================================
backup_current_deployment() {
    step "Step 1/7: Backup Current Deployment"

    CURRENT_VERSION=$(get_current_version)

    if [ "$CURRENT_VERSION" = "none" ]; then
        log_warning "First deployment - no backup needed"
        return 0
    fi

    log_info "Current version: $CURRENT_VERSION"

    # Backup running images
    local running=$(ssh "$DEPLOY_SERVER" "docker ps -q --filter 'name=copilotos-api' | wc -l")

    if [ "$running" -eq 0 ]; then
        log_warning "No containers running - skipping backup"
        return 0
    fi

    log_info "Creating backup tags..."
    ssh "$DEPLOY_SERVER" "
        docker tag copilotos-api:latest copilotos-api:backup-$CURRENT_VERSION 2>/dev/null || true
        docker tag copilotos-web:latest copilotos-web:backup-$CURRENT_VERSION 2>/dev/null || true
    " || log_warning "Backup tagging failed (non-critical)"

    log_success "Backup created: backup-$CURRENT_VERSION"
}

# ========================================
# BUILD IMAGES
# ========================================
build_images() {
    step "Step 2/7: Build Docker Images (v$NEW_VERSION)"

    if [ "$SKIP_BUILD" = true ]; then
        log_warning "Skipping build - using existing images"
        return 0
    fi

    cd "$PROJECT_ROOT"

    log_info "Building API image..."
    docker build -f apps/api/Dockerfile \
        -t "copilotos-api:$NEW_VERSION" \
        -t "copilotos-api:latest" \
        --target production \
        --no-cache \
        apps/api

    log_info "Building Web image..."
    docker build -f apps/web/Dockerfile \
        -t "copilotos-web:$NEW_VERSION" \
        -t "copilotos-web:latest" \
        --target runner \
        --no-cache \
        .

    log_success "Images built: $NEW_VERSION"
}

# ========================================
# DEPLOY METHOD: TAR
# ========================================
deploy_via_tar() {
    step "Step 3/7: Deploy via TAR Transfer"

    cd "$DEPLOY_HOME"

    # Export
    log_info "Exporting API image..."
    docker save "copilotos-api:$NEW_VERSION" "copilotos-api:latest" | \
        gzip > "api-${NEW_VERSION}.tar.gz"
    local api_size=$(du -h "api-${NEW_VERSION}.tar.gz" | cut -f1)
    log_success "API: $api_size"

    log_info "Exporting Web image..."
    docker save "copilotos-web:$NEW_VERSION" "copilotos-web:latest" | \
        gzip > "web-${NEW_VERSION}.tar.gz"
    local web_size=$(du -h "web-${NEW_VERSION}.tar.gz" | cut -f1)
    log_success "Web: $web_size"

    # Transfer
    log_info "Transferring to $DEPLOY_SERVER..."
    scp -q "api-${NEW_VERSION}.tar.gz" "web-${NEW_VERSION}.tar.gz" \
        "$DEPLOY_SERVER:$DEPLOY_PATH/" || {
        log_error "Transfer failed"
        return 1
    }
    log_success "Transfer complete"

    # Load on server
    log_info "Loading images on server..."
    ssh "$DEPLOY_SERVER" "
        cd $DEPLOY_PATH
        gunzip -c api-${NEW_VERSION}.tar.gz | docker load
        gunzip -c web-${NEW_VERSION}.tar.gz | docker load
        rm -f api-${NEW_VERSION}.tar.gz web-${NEW_VERSION}.tar.gz
    " || {
        log_error "Image loading failed"
        return 1
    }

    # Cleanup local
    rm -f "api-${NEW_VERSION}.tar.gz" "web-${NEW_VERSION}.tar.gz"

    log_success "TAR deployment complete"
}

# ========================================
# DEPLOY METHOD: REGISTRY
# ========================================
deploy_via_registry() {
    step "Step 3/7: Deploy via Docker Registry"

    # Push to registry
    log_info "Tagging for registry: $REGISTRY_URL"
    docker tag "copilotos-api:$NEW_VERSION" "$REGISTRY_URL/api:$NEW_VERSION"
    docker tag "copilotos-api:latest" "$REGISTRY_URL/api:latest"
    docker tag "copilotos-web:$NEW_VERSION" "$REGISTRY_URL/web:$NEW_VERSION"
    docker tag "copilotos-web:latest" "$REGISTRY_URL/web:latest"

    log_info "Pushing images to registry..."
    docker push "$REGISTRY_URL/api:$NEW_VERSION" || {
        log_error "Push failed - check registry authentication"
        return 1
    }
    docker push "$REGISTRY_URL/api:latest"
    docker push "$REGISTRY_URL/web:$NEW_VERSION"
    docker push "$REGISTRY_URL/web:latest"
    log_success "Images pushed to registry"

    # Pull on server
    log_info "Pulling images on server..."
    ssh "$DEPLOY_SERVER" "
        docker pull $REGISTRY_URL/api:$NEW_VERSION
        docker pull $REGISTRY_URL/web:$NEW_VERSION
        docker tag $REGISTRY_URL/api:$NEW_VERSION copilotos-api:latest
        docker tag $REGISTRY_URL/web:$NEW_VERSION copilotos-web:latest
    " || {
        log_error "Pull failed on server"
        return 1
    }

    log_success "Registry deployment complete"
}

# ========================================
# DEPLOY METHOD: LOCAL
# ========================================
deploy_via_local() {
    step "Step 3/7: Deploy Locally (Dev Mode)"

    log_warning "Local deployment - for development only!"

    cd "$PROJECT_ROOT/infra"
    docker compose down
    docker compose up -d

    log_success "Local deployment started"
}

# ========================================
# START DEPLOYMENT
# ========================================
start_deployment() {
    step "Step 4/7: Start Deployment on Server"

    log_info "Stopping current containers..."
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH/infra && docker compose down" || {
        log_warning "Stop failed (containers may not be running)"
    }

    log_info "Starting new containers..."
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH/infra && docker compose up -d" || {
        log_error "Container start failed"
        return 1
    }

    log_success "Containers started"
}

# ========================================
# HEALTH CHECK
# ========================================
verify_deployment() {
    step "Step 5/7: Health Check Verification"

    if [ "$SKIP_HEALTHCHECK" = true ]; then
        log_warning "Health check skipped - assuming success"
        return 0
    fi

    log_info "Waiting 30s for services to initialize..."
    sleep 30

    # API Health
    log_info "Checking API health..."
    local api_health=$(ssh "$DEPLOY_SERVER" \
        "curl -sf --max-time 10 http://localhost:8001/api/health | jq -r '.status' 2>/dev/null" || echo "error")

    if [ "$api_health" = "healthy" ]; then
        log_success "API: healthy"
    else
        log_error "API: $api_health"
        return 1
    fi

    # Web Check
    log_info "Checking Web frontend..."
    local web_status=$(ssh "$DEPLOY_SERVER" \
        "curl -sf --max-time 10 -o /dev/null -w '%{http_code}' http://localhost:3000" || echo "000")

    if [ "$web_status" = "200" ]; then
        log_success "Web: HTTP 200"
    else
        log_error "Web: HTTP $web_status"
        return 1
    fi

    # Database connectivity
    log_info "Checking database connection..."
    local db_check=$(ssh "$DEPLOY_SERVER" \
        "curl -sf http://localhost:8001/api/health | jq -r '.checks.database.status' 2>/dev/null" || echo "error")

    if [ "$db_check" = "healthy" ]; then
        log_success "Database: connected"
    else
        log_warning "Database: $db_check (may stabilize)"
    fi

    log_success "All health checks passed"
    return 0
}

# ========================================
# ROLLBACK
# ========================================
rollback_to_previous() {
    step "ROLLBACK: Restoring Previous Version"

    if [ "$CURRENT_VERSION" = "none" ]; then
        log_error "No previous version to rollback to"
        return 1
    fi

    log_warning "Rolling back to: $CURRENT_VERSION"

    # Check backup exists
    local backup_exists=$(ssh "$DEPLOY_SERVER" \
        "docker images -q copilotos-api:backup-$CURRENT_VERSION" || echo "")

    if [ -z "$backup_exists" ]; then
        log_error "Backup images not found for $CURRENT_VERSION"
        log_error "Manual intervention required!"
        return 1
    fi

    # Restore backup
    log_info "Stopping failed deployment..."
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH/infra && docker compose down"

    log_info "Restoring backup images..."
    ssh "$DEPLOY_SERVER" "
        docker tag copilotos-api:backup-$CURRENT_VERSION copilotos-api:latest
        docker tag copilotos-web:backup-$CURRENT_VERSION copilotos-web:latest
    "

    log_info "Starting previous version..."
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH/infra && docker compose up -d"

    sleep 20

    # Verify rollback
    local rollback_health=$(ssh "$DEPLOY_SERVER" \
        "curl -sf http://localhost:8001/api/health | jq -r '.status'" || echo "error")

    if [ "$rollback_health" = "healthy" ]; then
        log_success "Rollback successful"
        save_version_info "$CURRENT_VERSION" "rollback" "$DEPLOY_METHOD"
        return 0
    else
        log_error "Rollback verification FAILED"
        log_error "CRITICAL: Manual intervention required!"
        return 1
    fi
}

# ========================================
# CLEANUP
# ========================================
cleanup_old_versions() {
    step "Step 6/7: Cleanup"

    log_info "Cleaning old Docker images (keeping last 5)..."
    ssh "$DEPLOY_SERVER" "
        docker images 'copilotos-api' --format '{{.Repository}}:{{.Tag}}' | \
            grep -v latest | grep -v backup | tail -n +6 | xargs -r docker rmi 2>/dev/null || true
        docker images 'copilotos-web' --format '{{.Repository}}:{{.Tag}}' | \
            grep -v latest | grep -v backup | tail -n +6 | xargs -r docker rmi 2>/dev/null || true
    " 2>/dev/null || log_warning "Cleanup had warnings (non-critical)"

    log_success "Cleanup complete"
}

# ========================================
# SUMMARY
# ========================================
show_deployment_summary() {
    step "Step 7/7: Deployment Summary"

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  DEPLOYMENT SUCCESSFUL                                        ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "${BLUE}Version:${NC}      ${GREEN}$NEW_VERSION${NC}"
    echo -e "${BLUE}Method:${NC}       $DEPLOY_METHOD"
    echo -e "${BLUE}Server:${NC}       $DEPLOY_SERVER"
    echo -e "${BLUE}Domain:${NC}       https://$PROD_DOMAIN"

    echo ""
    echo -e "${BLUE}Git commit:${NC}"
    cd "$PROJECT_ROOT" && git log -1 --format="  %h - %s (%ar)"

    echo ""
    echo -e "${BLUE}Running containers:${NC}"
    ssh "$DEPLOY_SERVER" \
        "docker ps --format '  {{.Names}}\t{{.Status}}' --filter 'name=copilotos'" || true

    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Test:     https://$PROD_DOMAIN"
    echo "  2. Monitor:  make logs"
    echo "  3. Rollback: ./scripts/deploy.sh --version $CURRENT_VERSION"
    echo ""

    list_deployment_history
}

# ========================================
# MAIN EXECUTION
# ========================================
main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  COPILOTOS BRIDGE - CONSOLIDATED DEPLOYMENT                   ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Validate
    validate_config

    # Version management
    if [ -n "$SPECIFIC_VERSION" ]; then
        NEW_VERSION="$SPECIFIC_VERSION"
        log_info "Deploying specific version: $NEW_VERSION"
        SKIP_BUILD=true
    else
        NEW_VERSION=$(generate_version)
        log_info "New version: $NEW_VERSION"
    fi

    CURRENT_VERSION=$(get_current_version)
    log_info "Current version: $CURRENT_VERSION"

    echo ""
    echo -e "${BLUE}Method:${NC}  $DEPLOY_METHOD"
    echo -e "${BLUE}Server:${NC}  $DEPLOY_SERVER"
    echo ""

    # Confirmation
    if [ "$FORCE" != true ]; then
        read -p "Proceed with deployment? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_warning "Deployment cancelled"
            exit 0
        fi
    fi

    # Execute deployment
    backup_current_deployment

    if [ "$DEPLOY_METHOD" = "local" ]; then
        build_images
        deploy_via_local
        # No health check for local
        log_success "Local deployment complete"
        exit 0
    fi

    build_images

    # Deploy based on method
    case "$DEPLOY_METHOD" in
        tar)
            deploy_via_tar || { log_error "TAR deployment failed"; exit 1; }
            ;;
        registry)
            deploy_via_registry || { log_error "Registry deployment failed"; exit 1; }
            ;;
        *)
            log_error "Unknown method: $DEPLOY_METHOD"
            exit 1
            ;;
    esac

    start_deployment || {
        log_error "Container start failed"
        exit 1
    }

    # Health check with rollback
    if verify_deployment; then
        log_success "Deployment successful!"
        save_version_info "$NEW_VERSION" "success" "$DEPLOY_METHOD"
        cleanup_old_versions
        show_deployment_summary
        exit 0
    else
        log_error "Health check failed"
        save_version_info "$NEW_VERSION" "failed" "$DEPLOY_METHOD"

        if [ "$NO_ROLLBACK" = true ]; then
            log_warning "Auto-rollback disabled - leaving failed deployment"
            exit 1
        fi

        log_warning "Initiating automatic rollback..."
        if rollback_to_previous; then
            log_warning "Deployment failed but rollback succeeded"
            log_info "System is running previous version: $CURRENT_VERSION"
            exit 1
        else
            log_error "CRITICAL: Both deployment and rollback failed"
            log_error "Manual intervention required immediately!"
            exit 2
        fi
    fi
}

# Run
main "$@"
