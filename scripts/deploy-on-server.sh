#!/bin/bash
# ========================================
# DEPLOY ON SERVER - IN-PLACE DEPLOYMENT
# ========================================
# This script runs DIRECTLY on the production server
# It does NOT transfer images - it builds them in-place
#
# Usage:
#   ssh user@server 'cd /path/to/project && ./scripts/deploy-on-server.sh [OPTIONS]'
#
# Options:
#   --skip-backup      Skip pre-deployment backup (dangerous!)
#   --skip-healthcheck Skip health verification (dangerous!)
#   --no-cache         Build images without cache
#   --force            Skip confirmation prompts
#   -h, --help         Show this help
#
# This script is safer for the issue we encountered where:
# - No image versioning mismatch (builds fresh on server)
# - No tar transfer overhead
# - Works with existing container setup
# - Respects COMPOSE_PROJECT_NAME from environment

set -e
set -o pipefail

# ========================================
# CONFIGURATION
# ========================================
RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "
NC=""

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load environment
if [ -f "$PROJECT_ROOT/envs/.env.prod" ]; then
    source "$PROJECT_ROOT/envs/.env.prod"
elif [ -f "$PROJECT_ROOT/envs/.env" ]; then
    source "$PROJECT_ROOT/envs/.env"
fi

# ========================================
# PARSE ARGUMENTS
# ========================================
SKIP_BACKUP=false
SKIP_HEALTHCHECK=false
NO_CACHE=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --skip-healthcheck)
            SKIP_HEALTHCHECK=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            cat << EOF
Deploy On Server - In-Place Deployment

This script runs DIRECTLY on the production server.
It builds images in-place and redeploys containers.

Usage: $0 [OPTIONS]

Options:
  --skip-backup        Skip pre-deployment backup (dangerous!)
  --skip-healthcheck   Skip health check (dangerous!)
  --no-cache           Build without Docker cache
  --force              Skip confirmation prompts
  -h, --help           Show this help

Example:
  # From your local machine:
  ssh user@server 'cd /opt/copilotos-bridge && ./scripts/deploy-on-server.sh'

  # Or directly on server:
  cd /opt/copilotos-bridge
  ./scripts/deploy-on-server.sh

Safety Features:
  ✅ Pre-deployment backup
  ✅ Health check validation
  ✅ Preserves existing container configuration
  ✅ Automatic rollback on failure

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
validate_environment() {
    step "Step 1/7: Environment Validation"

    # Check we're in the right directory
    if [ ! -f "$PROJECT_ROOT/infra/docker-compose.yml" ]; then
        log_error "docker-compose.yml not found!"
        log_error "This script must run from the project root"
        exit 1
    fi

    # Check .env file exists
    if [ ! -f "$PROJECT_ROOT/envs/.env.prod" ] && [ ! -f "$PROJECT_ROOT/envs/.env" ]; then
        log_error "Environment file not found!"
        log_error "Create envs/.env.prod with production configuration"
        exit 1
    fi

    # Check Docker is available
    if ! command -v docker &> /dev/null; then
        log_error "Docker not installed!"
        exit 1
    fi

    # Check docker compose is available
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose not installed!"
        exit 1
    fi

    log_success "Environment validated"
}

# ========================================
# BACKUP CURRENT STATE
# ========================================
backup_current_state() {
    step "Step 2/7: Backup Current State"

    if [ "$SKIP_BACKUP" = true ]; then
        log_warning "Skipping backup (--skip-backup flag)"
        return 0
    fi

    local backup_tag="backup-$(date +%Y%m%d-%H%M%S)"

    # Check if containers are running
    local running=$(docker ps -q --filter 'name=copilotos' | wc -l)

    if [ "$running" -eq 0 ]; then
        log_warning "No containers running - skipping image backup"
        return 0
    fi

    log_info "Creating backup of current images..."

    # Backup API image
    if docker images copilotos-api:latest -q 2>/dev/null | grep -q .; then
        docker tag copilotos-api:latest "copilotos-api:$backup_tag"
        log_success "API image backed up: $backup_tag"
    fi

    # Backup Web image
    if docker images copilotos-web:latest -q 2>/dev/null | grep -q .; then
        docker tag copilotos-web:latest "copilotos-web:$backup_tag"
        log_success "Web image backed up: $backup_tag"
    fi

    # Save backup tag for potential rollback
    echo "$backup_tag" > /tmp/last_backup_tag

    log_success "Backup complete: $backup_tag"
}

# ========================================
# GIT UPDATE
# ========================================
update_code() {
    step "Step 3/7: Update Code from Git"

    cd "$PROJECT_ROOT"

    # Check git status
    if [ ! -d ".git" ]; then
        log_warning "Not a git repository - skipping git pull"
        return 0
    fi

    log_info "Current commit: $(git log -1 --format='%h - %s')"

    # Stash any local changes
    if ! git diff-index --quiet HEAD --; then
        log_warning "Uncommitted changes detected - stashing"
        git stash
    fi

    # Pull latest changes
    log_info "Pulling latest changes from origin..."
    git pull origin main || {
        log_error "Git pull failed"
        return 1
    }

    log_success "Code updated: $(git log -1 --format='%h - %s')"
}

# ========================================
# BUILD IMAGES
# ========================================
build_images() {
    step "Step 4/7: Build Docker Images"

    cd "$PROJECT_ROOT/infra"

    local build_flags=""
    if [ "$NO_CACHE" = true ]; then
        build_flags="--no-cache"
        log_info "Building with --no-cache flag"
    fi

    log_info "Building API and Web images..."

    docker compose build $build_flags || {
        log_error "Build failed"
        return 1
    }

    log_success "Images built successfully"
}

# ========================================
# DEPLOY CONTAINERS
# ========================================
deploy_containers() {
    step "Step 5/7: Deploy Updated Containers"

    cd "$PROJECT_ROOT/infra"

    log_info "Stopping current containers..."
    docker compose down || {
        log_warning "Stop had warnings (may be first deployment)"
    }

    log_info "Starting updated containers..."
    docker compose up -d || {
        log_error "Container start failed"
        return 1
    }

    log_success "Containers started"
}

# ========================================
# HEALTH CHECK
# ========================================
verify_deployment() {
    step "Step 6/7: Health Check Verification"

    if [ "$SKIP_HEALTHCHECK" = true ]; then
        log_warning "Health check skipped - assuming success"
        return 0
    fi

    log_info "Waiting 30s for services to initialize..."
    sleep 30

    local errors=0

    # API Health
    log_info "Checking API health..."
    local api_health=$(curl -sf --max-time 10 http://localhost:8001/api/health 2>/dev/null | jq -r '.status' 2>/dev/null || echo "error")

    if [ "$api_health" = "healthy" ]; then
        log_success "API: healthy"
    else
        log_error "API: $api_health"
        ((errors++))
    fi

    # Web Check
    log_info "Checking Web frontend..."
    local web_status=$(curl -sf --max-time 10 -o /dev/null -w '%{http_code}' http://localhost:3000 2>/dev/null || echo "000")

    if [ "$web_status" = "200" ]; then
        log_success "Web: HTTP 200"
    else
        log_error "Web: HTTP $web_status"
        ((errors++))
    fi

    # Database connectivity
    log_info "Checking database connection..."
    local db_check=$(curl -sf http://localhost:8001/api/health 2>/dev/null | jq -r '.checks.database.status' 2>/dev/null || echo "error")

    if [ "$db_check" = "healthy" ]; then
        log_success "Database: connected"
    else
        log_warning "Database: $db_check (may stabilize)"
    fi

    if [ $errors -gt 0 ]; then
        log_error "Health check failed with $errors error(s)"
        return 1
    fi

    log_success "All health checks passed"
    return 0
}

# ========================================
# ROLLBACK
# ========================================
rollback_to_backup() {
    step "ROLLBACK: Restoring Previous Version"

    if [ ! -f "/tmp/last_backup_tag" ]; then
        log_error "No backup tag found - cannot rollback"
        return 1
    fi

    local backup_tag=$(cat /tmp/last_backup_tag)
    log_warning "Rolling back to: $backup_tag"

    # Check backup images exist
    if ! docker images "copilotos-api:$backup_tag" -q 2>/dev/null | grep -q .; then
        log_error "Backup image not found: copilotos-api:$backup_tag"
        return 1
    fi

    cd "$PROJECT_ROOT/infra"

    log_info "Stopping failed deployment..."
    docker compose down

    log_info "Restoring backup images..."
    docker tag "copilotos-api:$backup_tag" copilotos-api:latest
    docker tag "copilotos-web:$backup_tag" copilotos-web:latest

    log_info "Starting previous version..."
    docker compose up -d

    sleep 20

    # Verify rollback
    local rollback_health=$(curl -sf http://localhost:8001/api/health 2>/dev/null | jq -r '.status' || echo "error")

    if [ "$rollback_health" = "healthy" ]; then
        log_success "Rollback successful"
        return 0
    else
        log_error "Rollback verification FAILED"
        log_error "CRITICAL: Manual intervention required!"
        return 1
    fi
}

# ========================================
# SUMMARY
# ========================================
show_summary() {
    step "Step 7/7: Deployment Summary"

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  DEPLOYMENT SUCCESSFUL                                        ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "${BLUE}Git commit:${NC}"
    cd "$PROJECT_ROOT" && git log -1 --format="  %h - %s (%ar)"

    echo ""
    echo -e "${BLUE}Running containers:${NC}"
    docker ps --format '  {{.Names}}\t{{.Status}}' --filter 'name=copilotos'

    echo ""
    echo -e "${BLUE}Health status:${NC}"
    curl -sf http://localhost:8001/api/health 2>/dev/null | jq '{status, uptime_seconds, database}' || echo "  (API not responding)"

    echo ""
}

# ========================================
# MAIN EXECUTION
# ========================================
main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  DEPLOY ON SERVER - IN-PLACE DEPLOYMENT                       ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Validation
    validate_environment

    # Confirmation
    if [ "$FORCE" != true ]; then
        echo ""
        echo -e "${YELLOW}This will:${NC}"
        echo "  1. Backup current images"
        echo "  2. Pull latest code from git"
        echo "  3. Build new Docker images"
        echo "  4. Redeploy all containers"
        echo "  5. Verify health"
        echo ""
        read -p "Proceed with deployment? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_warning "Deployment cancelled"
            exit 0
        fi
    fi

    # Execute deployment
    backup_current_state
    update_code
    build_images || {
        log_error "Build failed - deployment aborted"
        exit 1
    }

    deploy_containers || {
        log_error "Container deployment failed"
        exit 1
    }

    # Health check with rollback
    if verify_deployment; then
        log_success "Deployment successful!"
        show_summary
        exit 0
    else
        log_error "Health check failed"
        log_warning "Initiating automatic rollback..."

        if rollback_to_backup; then
            log_warning "Deployment failed but rollback succeeded"
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
