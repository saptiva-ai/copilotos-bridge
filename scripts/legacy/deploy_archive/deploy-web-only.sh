#!/bin/bash
# ========================================
# FAST WEB-ONLY DEPLOYMENT
# ========================================
# For rapid iteration when debugging web changes
# Skips API, MongoDB, Redis - only rebuilds and deploys web container
#
# Usage: ./scripts/deploy-web-only.sh
#
set -e
set -o pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DEMO_SERVER="jf@34.172.67.93"
DEMO_PATH="/home/jf/capital414-chat"

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

main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  FAST WEB-ONLY DEPLOYMENT - 414.SAPTIVA.COM                  ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    log_warning "Only deploying web container (API/DB unchanged)"

    # Step 1: Build web image only
    step "Step 1/4: Build Web Image"

    # Load env vars for build args (except NEXT_PUBLIC_API_URL which has special handling)
    if [[ -f "envs/.env.prod" ]]; then
        export $(grep -v '^#' envs/.env.prod | grep -E 'NEXT_PUBLIC|APP_NAME|FEATURE' | grep -v 'NEXT_PUBLIC_API_URL' | xargs)
    fi

    log_info "Building Web image with production variables..."
    # IMPORTANT: Do NOT include /api suffix - routes already include it
    # Force the correct URL without /api (override any .env.prod setting)
    docker build -f apps/web/Dockerfile \
        --build-arg NEXT_PUBLIC_API_URL="https://414.saptiva.com" \
        --build-arg NEXT_PUBLIC_APP_NAME="${NEXT_PUBLIC_APP_NAME:-Saptiva Copilot OS - Capital 414}" \
        --build-arg NEXT_PUBLIC_MAX_FILE_SIZE_MB="${NEXT_PUBLIC_MAX_FILE_SIZE_MB:-50}" \
        --build-arg NEXT_PUBLIC_FEATURE_WEB_SEARCH="${NEXT_PUBLIC_FEATURE_WEB_SEARCH:-false}" \
        --build-arg NEXT_PUBLIC_FEATURE_DEEP_RESEARCH="${NEXT_PUBLIC_FEATURE_DEEP_RESEARCH:-false}" \
        --build-arg NEXT_PUBLIC_FEATURE_ADD_FILES="${NEXT_PUBLIC_FEATURE_ADD_FILES:-true}" \
        --build-arg NEXT_PUBLIC_FEATURE_GOOGLE_DRIVE="${NEXT_PUBLIC_FEATURE_GOOGLE_DRIVE:-false}" \
        --build-arg NEXT_PUBLIC_FEATURE_CANVAS="${NEXT_PUBLIC_FEATURE_CANVAS:-false}" \
        --build-arg NEXT_PUBLIC_FEATURE_AGENT_MODE="${NEXT_PUBLIC_FEATURE_AGENT_MODE:-false}" \
        --build-arg NEXT_PUBLIC_FEATURE_MIC="${NEXT_PUBLIC_FEATURE_MIC:-false}" \
        -t octavios-web:latest --target runner .

    log_success "Web image built successfully"

    # Step 2: Export web image only
    step "Step 2/4: Export Web Image"

    log_info "Exporting web image..."
    docker save octavios-web:latest | gzip > /tmp/web-only.tar.gz

    FILESIZE=$(du -h /tmp/web-only.tar.gz | cut -f1)
    log_success "Web image exported: $FILESIZE"

    # Step 3: Transfer to server
    step "Step 3/4: Transfer to Server"

    log_info "Transferring web image to $DEMO_SERVER..."
    scp /tmp/web-only.tar.gz "$DEMO_SERVER:/tmp/"
    log_success "Transfer complete"

    # Step 4: Load and restart web container only
    step "Step 4/4: Deploy Web Container"

    log_info "Loading web image and restarting container..."
    ssh "$DEMO_SERVER" "
        gunzip -c /tmp/web-only.tar.gz | docker load
        rm /tmp/web-only.tar.gz
        cd $DEMO_PATH
        docker compose --env-file envs/.env.prod -f infra/docker-compose.cloudflare.yml up -d --no-deps --force-recreate web
        echo 'Waiting for web to start...'
        sleep 5
        docker compose --env-file envs/.env.prod -f infra/docker-compose.cloudflare.yml ps web
    "

    log_success "Web container deployed"

    # Cleanup local tar
    rm -f /tmp/web-only.tar.gz

    # Summary
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  WEB-ONLY DEPLOYMENT COMPLETE                                 ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Domain:${NC}       https://414.saptiva.com"
    echo -e "${BLUE}Status:${NC}       Web container restarted"
    echo ""
    echo -e "${YELLOW}Note:${NC} API, MongoDB, Redis, MinIO unchanged"
    echo ""
}

main "$@"
