#!/bin/bash
set -e

# ============================================================================
# UPDATE IMAGES SCRIPT - Generalized
# ============================================================================
# Updates docker-compose.images.yml with new version tags
#
# Usage:
#   ./scripts/deploy/update-images.sh -v 1.4.1                    # Specific version
#   ./scripts/deploy/update-images.sh -v 1.4.1 -s backend         # Specific service
#   ./scripts/deploy/update-images.sh -v 1.4.1 --changelog "..."  # With changelog
#   ./scripts/deploy/update-images.sh --dry-run -v 1.4.1          # Show changes
#
# Options:
#   -v, --version VERSION   Version to set (required)
#   -s, --service SERVICE   Service to update (backend|web|file-manager|dashboard|all)
#   -c, --changelog TEXT    Changelog text to add in comments
#   --dry-run               Show changes without applying
#   -h, --help              Show this help
# ============================================================================

# Defaults
VERSION=""
SERVICES=()
DRY_RUN=false
CHANGELOG=""

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGES_FILE="$PROJECT_ROOT/infra/docker-compose.images.yml"

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

# Get current version from docker-compose.images.yml (defaults to backend)
get_current_version() {
    grep -oP 'backend:\K[0-9]+\.[0-9]+\.[0-9]+' "$IMAGES_FILE" 2>/dev/null | head -1
}

# Get current version for a specific service
get_service_version() {
    local service="$1"
    grep -oP "octavios-invex-${service}:\K[0-9]+\.[0-9]+\.[0-9]+" "$IMAGES_FILE" 2>/dev/null | head -1
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
        -c|--changelog)
            CHANGELOG="$2"
            shift 2
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
    echo "Example: ./scripts/deploy/update-images.sh -v 1.4.1"
    exit 1
fi

# Default to all services if none specified
if [ ${#SERVICES[@]} -eq 0 ] || [[ " ${SERVICES[*]} " =~ " all " ]]; then
    SERVICES=("backend" "web")
fi

HEADER_VERSION=$(get_current_version)

echo "=================================================="
echo "📝 Updating docker-compose.images.yml"
echo "=================================================="
echo "   Header version: v${HEADER_VERSION}"
echo "   Target:  v${VERSION}"
echo "   Services: ${SERVICES[*]}"
echo "   Dry Run: $DRY_RUN"
echo ""

# Show per-service versions
for svc in "${SERVICES[@]}"; do
    svc_ver=$(get_service_version "$svc")
    echo "   ${svc}: v${svc_ver:-unknown}"
done
echo ""

if [ ! -f "$IMAGES_FILE" ]; then
    log_error "Images file not found: $IMAGES_FILE"
    exit 1
fi

# Create backup
if [ "$DRY_RUN" = false ]; then
    cp "$IMAGES_FILE" "${IMAGES_FILE}.bak"
    log_info "Backup created: ${IMAGES_FILE}.bak"
fi

# Update version in header comment
update_file() {
    local pattern="$1"
    local replacement="$2"

    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] Would replace: $pattern → $replacement"
    else
        # Use perl for in-place replacement (more portable than sed -i)
        perl -i -pe "s|$pattern|$replacement|g" "$IMAGES_FILE"
    fi
}

# Update header version (only when updating main services, not dashboard-only)
if [[ " ${SERVICES[*]} " =~ " backend " ]] || [[ " ${SERVICES[*]} " =~ " web " ]]; then
    log_info "Updating header version..."
    update_file "PRODUCTION IMAGES - v${HEADER_VERSION}" "PRODUCTION IMAGES - v${VERSION}"
else
    log_info "Skipping header update (dashboard has independent version track)"
fi

# Update changelog comment if provided
if [ -n "$CHANGELOG" ]; then
    log_info "Updating changelog..."
    # Replace the Changes section
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] Would update changelog to: $CHANGELOG"
    fi
fi

# Update each service
for service in "${SERVICES[@]}"; do
    echo ""
    log_info "Updating $service to v${VERSION}..."

    case $service in
        backend|web)
            svc_current=$(get_service_version "$service")
            if [ -z "$svc_current" ]; then
                log_error "$service: Could not detect current version in $IMAGES_FILE"
            elif [ "$svc_current" = "$VERSION" ]; then
                log_info "$service: already at v${VERSION}, skipping"
            else
                log_info "$service: $svc_current → $VERSION"
                update_file "octavios-invex-${service}:${svc_current}" "octavios-invex-${service}:${VERSION}"
                log_success "$service updated"
            fi
            ;;
        dashboard)
            dash_current=$(get_service_version "dashboard")
            if [ -z "$dash_current" ]; then
                log_error "dashboard: Could not detect current version in $IMAGES_FILE"
            else
                log_info "dashboard: $dash_current → $VERSION"
                update_file "octavios-invex-dashboard:${dash_current}" "octavios-invex-dashboard:${VERSION}"
                log_success "dashboard updated"
            fi
            ;;
        file-manager)
            fm_current=$(get_service_version "file-manager")
            if [ -z "$fm_current" ]; then
                log_error "file-manager: Could not detect current version in $IMAGES_FILE"
            elif [ "$fm_current" = "$VERSION" ]; then
                log_info "file-manager: already at v${VERSION}, skipping"
            else
                log_info "file-manager: $fm_current → $VERSION"
                update_file "octavios-invex-file-manager:${fm_current}" "octavios-invex-file-manager:${VERSION}"
                log_success "file-manager updated"
            fi
            ;;
        *)
            log_error "Unknown service: $service"
            ;;
    esac
done

echo ""

if [ "$DRY_RUN" = true ]; then
    log_info "Dry run complete. No changes made."
else
    log_success "docker-compose.images.yml updated to v${VERSION}"
    echo ""
    echo "📋 Updated file:"
    grep -E "^#|image:" "$IMAGES_FILE" | head -20
fi

echo ""
echo "=================================================="
log_success "Update Complete"
echo "=================================================="
echo ""
echo "📝 Next steps:"
echo "   1. Review changes: git diff infra/docker-compose.images.yml"
echo "   2. Commit: git add infra/docker-compose.images.yml && git commit -m 'chore: update images to v${VERSION}'"
echo "   3. Deploy: ./scripts/deploy/deploy.sh -v ${VERSION}"
echo ""
