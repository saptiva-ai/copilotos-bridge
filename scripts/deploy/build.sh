#!/bin/bash
set -e

# ============================================================================
# BUILD SCRIPT - Generalized
# ============================================================================
# Builds optimized production images with configurable version
#
# Usage:
#   ./scripts/deploy/build.sh -v 1.4.1                    # Specific version
#   ./scripts/deploy/build.sh --version 1.4.1 -s backend  # Specific service
#   ./scripts/deploy/build.sh --next                      # Auto-increment patch
#   ./scripts/deploy/build.sh --next minor                # Auto-increment minor
#   ./scripts/deploy/build.sh --dry-run -v 1.4.1          # Show what would be built
#   ./scripts/deploy/build.sh -v 1.4.1 --cache-from "type=gha,scope=backend" --cache-to "type=gha,mode=max,scope=backend"
#
# Options:
#   -v, --version VERSION   Version to build (e.g., 1.4.1)
#   -s, --service SERVICE   Service to build (backend|web|file-manager|dashboard|all)
#   --next [TYPE]           Auto-detect next version (patch|minor|major)
#   --dry-run               Show commands without executing
#   --no-cache              Build without Docker cache
#   --cache-from VALUE      Docker buildx cache-from (e.g., type=gha,scope=backend)
#   --cache-to VALUE        Docker buildx cache-to (e.g., type=gha,mode=max,scope=backend)
#   -h, --help              Show this help
# ============================================================================

# Defaults
VERSION=""
SERVICES=()
DRY_RUN=false
NO_CACHE=false
AUTO_INCREMENT=""
CACHE_FROM=""
CACHE_TO=""
DATETIME=$(date +"%Y%m%d-%H%M")
DOCKERHUB_USER="saptivaai"
PROJECT="octavios-invex"

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_help() {
    head -30 "$0" | tail -25
    exit 0
}

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Get current version from docker-compose.images.yml (source of truth)
get_current_version() {
    local version=$(grep -oP 'octavios-invex-backend:\K[0-9]+\.[0-9]+\.[0-9]+' "$PROJECT_ROOT/infra/docker-compose.images.yml" 2>/dev/null | head -1)

    if [ -z "$version" ]; then
        version="1.0.0"
    fi

    echo "$version"
}

# Increment version
increment_version() {
    local version="$1"
    local type="${2:-patch}"

    local major=$(echo "$version" | cut -d. -f1)
    local minor=$(echo "$version" | cut -d. -f2)
    local patch=$(echo "$version" | cut -d. -f3)

    case "$type" in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch|*)
            patch=$((patch + 1))
            ;;
    esac

    echo "${major}.${minor}.${patch}"
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
        --next)
            if [[ "$2" =~ ^(patch|minor|major)$ ]]; then
                AUTO_INCREMENT="$2"
                shift 2
            else
                AUTO_INCREMENT="patch"
                shift
            fi
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --cache-from)
            CACHE_FROM="$2"
            shift 2
            ;;
        --cache-to)
            CACHE_TO="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        *)
            # Assume it's a service if no flag
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

# Auto-increment version if requested
if [ -n "$AUTO_INCREMENT" ]; then
    CURRENT_VERSION=$(get_current_version)
    VERSION=$(increment_version "$CURRENT_VERSION" "$AUTO_INCREMENT")
    log_info "Auto-increment: $CURRENT_VERSION → $VERSION ($AUTO_INCREMENT)"
fi

# Validate version
if [ -z "$VERSION" ]; then
    log_error "Version is required. Use -v VERSION or --next"
    echo ""
    echo "Current version: $(get_current_version)"
    echo "Example: ./scripts/deploy/build.sh -v 1.4.1"
    echo "         ./scripts/deploy/build.sh --next"
    exit 1
fi

# Default to all services if none specified
if [ ${#SERVICES[@]} -eq 0 ] || [[ " ${SERVICES[*]} " =~ " all " ]]; then
    SERVICES=("backend" "web" "file-manager" "dashboard")
fi

cd "$PROJECT_ROOT"

echo "=============================================="
echo "🔨 Building Production Images v${VERSION}"
echo "=============================================="
echo "   Project: $PROJECT_ROOT"
echo "   Version: $VERSION"
echo "   DateTime: $DATETIME"
echo "   Services: ${SERVICES[*]}"
echo "   Dry Run: $DRY_RUN"
echo "   No Cache: $NO_CACHE"
echo "   Cache From: ${CACHE_FROM:-none}"
echo "   Cache To: ${CACHE_TO:-none}"
echo ""

# Build --no-cache flag string
NO_CACHE_FLAG=""
if [ "$NO_CACHE" = true ]; then
    NO_CACHE_FLAG="--no-cache"
fi

# Build cache flags for buildx
CACHE_FROM_FLAG=""
CACHE_TO_FLAG=""
if [ -n "$CACHE_FROM" ]; then
    CACHE_FROM_FLAG="--cache-from $CACHE_FROM"
fi
if [ -n "$CACHE_TO" ]; then
    CACHE_TO_FLAG="--cache-to $CACHE_TO"
fi

# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] $*"
    else
        "$@"
    fi
}

for service in "${SERVICES[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔨 Building $service..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    case $service in
        backend)
            run_cmd docker buildx build $NO_CACHE_FLAG $CACHE_FROM_FLAG $CACHE_TO_FLAG \
                --target production \
                --build-arg BUILDKIT_INLINE_CACHE=1 \
                --load \
                -t "octavios-chat-bajaware_invex-backend:latest" \
                -t "${DOCKERHUB_USER}/${PROJECT}-backend:${VERSION}" \
                -t "${DOCKERHUB_USER}/${PROJECT}-backend:${VERSION}-${DATETIME}" \
                -t "${DOCKERHUB_USER}/${PROJECT}-backend:latest" \
                -f apps/backend/Dockerfile \
                apps/backend/
            ;;

        web)
            run_cmd docker buildx build $NO_CACHE_FLAG $CACHE_FROM_FLAG $CACHE_TO_FLAG \
                --target runner \
                --build-arg BUILDKIT_INLINE_CACHE=1 \
                --build-arg API_BASE_URL=http://backend:8000 \
                --build-arg NEXT_PUBLIC_APP_NAME="Saptiva Copilot OS" \
                --load \
                -t "octavios-chat-bajaware_invex-web:latest" \
                -t "${DOCKERHUB_USER}/${PROJECT}-web:${VERSION}" \
                -t "${DOCKERHUB_USER}/${PROJECT}-web:${VERSION}-${DATETIME}" \
                -t "${DOCKERHUB_USER}/${PROJECT}-web:latest" \
                -f apps/web/Dockerfile \
                .
            ;;

        dashboard)
            run_cmd docker buildx build $NO_CACHE_FLAG $CACHE_FROM_FLAG $CACHE_TO_FLAG \
                --build-arg BUILDKIT_INLINE_CACHE=1 \
                --load \
                -t "octavios-chat-bajaware_invex-dashboard:latest" \
                -t "${DOCKERHUB_USER}/${PROJECT}-dashboard:${VERSION}" \
                -t "${DOCKERHUB_USER}/${PROJECT}-dashboard:${VERSION}-${DATETIME}" \
                -t "${DOCKERHUB_USER}/${PROJECT}-dashboard:latest" \
                -f apps/dashboard/Dockerfile \
                apps/dashboard/
            ;;

        file-manager)
            run_cmd docker buildx build $NO_CACHE_FLAG $CACHE_FROM_FLAG $CACHE_TO_FLAG \
                --build-arg BUILDKIT_INLINE_CACHE=1 \
                --load \
                -t "octavios-chat-bajaware_invex-file-manager:latest" \
                -t "${DOCKERHUB_USER}/${PROJECT}-file-manager:${VERSION}" \
                -t "${DOCKERHUB_USER}/${PROJECT}-file-manager:${VERSION}-${DATETIME}" \
                -t "${DOCKERHUB_USER}/${PROJECT}-file-manager:latest" \
                -f plugins/public/file-manager/Dockerfile \
                .
            ;;

        *)
            log_error "Unknown service: $service"
            continue
            ;;
    esac

    log_success "$service built successfully"
    echo ""
done

echo "=============================================="
log_success "Build Complete - v${VERSION}"
echo "=============================================="
echo ""
echo "📦 Images created:"
for service in "${SERVICES[@]}"; do
    echo "   - ${DOCKERHUB_USER}/${PROJECT}-${service}:${VERSION}"
done
echo ""
echo "📝 Next steps:"
echo "   1. Test locally: docker compose up -d"
echo "   2. Push: ./scripts/deploy/push.sh -v ${VERSION}"
echo "   3. Deploy: ./scripts/deploy/deploy.sh -v ${VERSION}"
echo ""
