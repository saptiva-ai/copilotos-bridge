#!/bin/bash
# ========================================
# COPILOTOS BRIDGE - QUICK ROLLBACK
# ========================================
# Fast rollback to previous or specific version
#
# Usage:
#   ./scripts/rollback.sh              # Rollback to previous version
#   ./scripts/rollback.sh VERSION      # Rollback to specific version
#   ./scripts/rollback.sh --list       # List available versions
#   ./scripts/rollback.sh --help       # Show help

set -e

RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "
NC=""

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_HOME="$HOME/.octavios-deploy"

# Load environment
if [ -f "$PROJECT_ROOT/envs/.env.prod" ]; then
    source "$PROJECT_ROOT/envs/.env.prod"
fi

DEPLOY_SERVER="${DEPLOY_SERVER:-${PROD_SERVER_HOST:-}}"
DEPLOY_PATH="${DEPLOY_PATH:-${PROD_DEPLOY_PATH:-/opt/octavios-bridge}}"

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✔${NC} $1"; }
log_warning() { echo -e "${YELLOW}▲${NC} $1"; }
log_error() { echo -e "${RED}✖${NC} $1"; }

# ========================================
# GET CURRENT VERSION
# ========================================
get_current_version() {
    ssh "$DEPLOY_SERVER" "cat $DEPLOY_PATH/.deploy/current_version 2>/dev/null" || echo "unknown"
}

# ========================================
# LIST VERSIONS
# ========================================
list_versions() {
    echo ""
    log_info "Available versions for rollback:"
    echo ""

    # From local history
    if [ -f "$DEPLOY_HOME/versions/history.log" ]; then
        echo "Recent deployments:"
        tail -10 "$DEPLOY_HOME/versions/history.log" | tac | while IFS='|' read -r ts ver status method; do
            local icon="✔"
            local color=$GREEN
            case "$status" in
                failed) icon="✖"; color=$RED ;;
                rollback) icon="↩"; color=$YELLOW ;;
            esac
            echo -e "  ${color}$icon${NC} $ver - $ts (via $method)"
        done
    fi

    echo ""

    # From server backups
    log_info "Available backup images on server:"
    ssh "$DEPLOY_SERVER" "docker images --format '{{.Repository}}:{{.Tag}}' | grep backup | sort -r | head -10" || \
        echo "  No backup images found"

    echo ""
}

# ========================================
# CONFIRM ROLLBACK
# ========================================
confirm_rollback() {
    local target_version=$1
    local current_version=$2

    echo ""
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  ROLLBACK CONFIRMATION                                        ║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Current version:${NC}  $current_version"
    echo -e "${BLUE}Rollback to:${NC}      $target_version"
    echo ""
    echo -e "${YELLOW}▲ This will:"
    echo "  - Stop current containers"
    echo "  - Restore previous version"
    echo "  - Restart services"
    echo ""
    read -p "Proceed with rollback? (yes/NO) " -r
    echo ""

    if [[ ! "$REPLY" =~ ^(yes|YES)$ ]]; then
        log_warning "Rollback cancelled"
        exit 0
    fi
}

# ========================================
# EXECUTE ROLLBACK
# ========================================
execute_rollback() {
    local target_version=$1

    log_info "Starting rollback to $target_version..."
    echo ""

    # Check if backup exists
    local backup_api=$(ssh "$DEPLOY_SERVER" \
        "docker images -q octavios-api:backup-$target_version" || echo "")

    if [ -z "$backup_api" ]; then
        log_error "Backup not found for version: $target_version"
        echo ""
        echo "Try one of these:"
        list_versions
        exit 1
    fi

    # Stop current
    log_info "Stopping current deployment..."
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH/infra && docker compose down" || {
        log_error "Failed to stop containers"
        exit 1
    }

    # Restore backup
    log_info "Restoring backup images..."
    ssh "$DEPLOY_SERVER" "
        docker tag octavios-api:backup-$target_version octavios-api:latest
        docker tag octavios-web:backup-$target_version octavios-web:latest
    " || {
        log_error "Failed to restore backup images"
        exit 1
    }

    # Start
    log_info "Starting services with version $target_version..."
    ssh "$DEPLOY_SERVER" "cd $DEPLOY_PATH/infra && docker compose up -d" || {
        log_error "Failed to start services"
        exit 1
    }

    # Wait and verify
    log_info "Waiting 20s for services to start..."
    sleep 20

    log_info "Verifying health..."
    local health=$(ssh "$DEPLOY_SERVER" \
        "curl -sf http://localhost:8001/api/health | jq -r '.status'" || echo "error")

    if [ "$health" = "healthy" ]; then
        log_success "Rollback successful!"

        # Update version tracking
        ssh "$DEPLOY_SERVER" "echo '$target_version' > $DEPLOY_PATH/.deploy/current_version"

        echo ""
        echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ROLLBACK COMPLETE                                            ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${BLUE}System is now running version:${NC} ${GREEN}$target_version${NC}"
        echo ""
        echo -e "${YELLOW}Next steps:${NC}"
        echo "  1. Verify application: Test critical features"
        echo "  2. Monitor logs: make logs"
        echo "  3. If stable: Fix and redeploy with ./scripts/deploy.sh"
        echo ""
    else
        log_error "Health check failed after rollback: $health"
        log_error "System may be unstable - check logs immediately!"
        exit 1
    fi
}

# ========================================
# MAIN
# ========================================
main() {
    if [ -z "$DEPLOY_SERVER" ]; then
        log_error "PROD_SERVER_HOST not configured"
        echo "Set in envs/.env.prod"
        exit 1
    fi

    # Parse arguments
    case "${1:-}" in
        --list|-l)
            list_versions
            exit 0
            ;;
        --help|-h)
            cat << EOF
Quick Rollback Script

Usage:
  $0                  # Rollback to previous version
  $0 VERSION          # Rollback to specific version
  $0 --list           # List available versions
  $0 --help           # Show this help

Examples:
  $0                        # Auto-rollback to previous
  $0 abc123-20251011        # Rollback to specific version
  $0 --list                 # Show version history

EOF
            exit 0
            ;;
        "")
            # Auto-rollback to previous
            CURRENT_VERSION=$(get_current_version)

            # Get previous from history
            PREVIOUS_VERSION=$(tail -2 "$DEPLOY_HOME/versions/history.log" | head -1 | cut -d'|' -f2)

            if [ -z "$PREVIOUS_VERSION" ]; then
                log_error "No previous version found in history"
                list_versions
                exit 1
            fi

            confirm_rollback "$PREVIOUS_VERSION" "$CURRENT_VERSION"
            execute_rollback "$PREVIOUS_VERSION"
            ;;
        *)
            # Rollback to specific version
            TARGET_VERSION="$1"
            CURRENT_VERSION=$(get_current_version)

            confirm_rollback "$TARGET_VERSION" "$CURRENT_VERSION"
            execute_rollback "$TARGET_VERSION"
            ;;
    esac
}

main "$@"
