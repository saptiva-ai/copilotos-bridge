#!/bin/bash
set -e

# ============================================================================
# PUSH SCRIPT - Generalized
# ============================================================================
# Pushes production images to Docker Hub with configurable version
#
# Usage:
#   ./scripts/deploy/push.sh -v 1.4.1                    # Specific version
#   ./scripts/deploy/push.sh -v 1.4.1 -s backend         # Specific service
#   ./scripts/deploy/push.sh -v 1.4.1 --skip-latest      # Don't push :latest
#   ./scripts/deploy/push.sh --dry-run -v 1.4.1          # Show what would be pushed
#
# Options:
#   -v, --version VERSION   Version to push (required)
#   -s, --service SERVICE   Service to push (backend|web|file-manager|dashboard|all)
#   --skip-latest           Don't push the :latest tag
#   --dry-run               Show commands without executing
#   -h, --help              Show this help
# ============================================================================

# Defaults
VERSION=""
SERVICES=()
DRY_RUN=false
SKIP_LATEST=false
DOCKERHUB_USER="saptivaai"
PROJECT="octavios-invex"

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    head -25 "$0" | tail -20
    exit 0
}

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Get current version from docker-compose.images.yml
get_current_version() {
    grep -oP 'backend:\K[0-9]+\.[0-9]+\.[0-9]+' "$PROJECT_ROOT/infra/docker-compose.images.yml" 2>/dev/null | head -1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -s|--service)
            SERVICES+=("$2")
            shift 2
            ;;
        --skip-latest)
            SKIP_LATEST=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            if [[ "$1" =~ ^(backend|web|file-manager|dashboard|all)$ ]]; then
                SERVICES+=("$1")
            else
                log_error "Unknown option: $1"
                show_help
            fi
            shift
            ;;
    esac
done

# Validate version
if [ -z "$VERSION" ]; then
    log_error "Version is required. Use -v VERSION"
    echo ""
    echo "Current version: $(get_current_version)"
    echo "Example: ./scripts/deploy/push.sh -v 1.4.1"
    exit 1
fi

# Default to all services if none specified
if [ ${#SERVICES[@]} -eq 0 ] || [[ " ${SERVICES[*]} " =~ " all " ]]; then
    SERVICES=("backend" "web" "file-manager" "dashboard")
fi

echo "=================================================="
echo "📤 Pushing Images to Docker Hub - v${VERSION}"
echo "=================================================="
echo "   User: $DOCKERHUB_USER"
echo "   Version: $VERSION"
echo "   Services: ${SERVICES[*]}"
echo "   Skip Latest: $SKIP_LATEST"
echo "   Dry Run: $DRY_RUN"
echo ""

# Verify docker login (supports credential helpers and legacy auth)
if [ "$DRY_RUN" = false ]; then
    log_info "Verificando login en Docker Hub..."
    DOCKER_LOGGED_IN=false

    # Method 1: check docker info (works with legacy inline credentials)
    if docker info 2>/dev/null | grep -q "Username"; then
        DOCKER_LOGGED_IN=true
    fi

    # Method 2: check config.json auths (works with credential helpers/stores)
    if [ "$DOCKER_LOGGED_IN" = false ] && [ -f "$HOME/.docker/config.json" ]; then
        if python3 -c "
import json, sys
with open('$HOME/.docker/config.json') as f:
    cfg = json.load(f)
auths = cfg.get('auths', {})
sys.exit(0 if any('docker.io' in k for k in auths) else 1)
" 2>/dev/null; then
            DOCKER_LOGGED_IN=true
        fi
    fi

    if [ "$DOCKER_LOGGED_IN" = true ]; then
        log_success "Login verificado"
    else
        if [ "${CI:-false}" = "true" ]; then
            log_error "Docker Hub login required (CI mode, no interactive prompt)"
            exit 1
        fi
        log_warn "No estás logueado en Docker Hub"
        echo "   Ejecuta: docker login -u $DOCKERHUB_USER"
        read -p "¿Continuar de todas formas? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi
echo ""

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] $*"
    else
        "$@"
    fi
}

push_with_retry() {
    local image="$1"
    local max_attempts=3
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo "   → Pushing $image (attempt $attempt/$max_attempts)..."
        if run_cmd docker push "$image"; then
            return 0
        fi
        log_warn "Push failed, retrying in 5s..."
        sleep 5
        ((attempt++))
    done

    log_error "Failed to push $image after $max_attempts attempts"
    return 1
}

for service in "${SERVICES[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 Pushing $service..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    IMAGE="${DOCKERHUB_USER}/${PROJECT}-${service}"

    # Push version tag
    push_with_retry "${IMAGE}:${VERSION}"

    # Push latest tag (unless skipped)
    if [ "$SKIP_LATEST" = false ]; then
        push_with_retry "${IMAGE}:latest"
    fi

    log_success "$service pushed successfully"
    echo ""
done

echo "=================================================="
log_success "All Images Pushed - v${VERSION}"
echo "=================================================="
echo ""
echo "🔗 Images disponibles en:"
for service in "${SERVICES[@]}"; do
    echo "   - https://hub.docker.com/r/${DOCKERHUB_USER}/${PROJECT}-${service}/tags"
done
echo ""
echo "📝 Next steps:"
echo "   1. Update docker-compose.images.yml:"
echo "      ./scripts/deploy/update-images.sh -v ${VERSION}"
echo "   2. Deploy to production:"
echo "      ./scripts/deploy/deploy.sh -v ${VERSION}"
echo ""
