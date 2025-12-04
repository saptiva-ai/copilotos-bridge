#!/bash
# ========================================
# FAST API-ONLY DEPLOYMENT
# ========================================
# For rapid iteration when debugging API changes
# Skips web, MongoDB, Redis - only rebuilds and deploys API container
#
# Usage: ./scripts/deploy-api-only.sh
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
    echo -e "${BLUE}║  FAST API-ONLY DEPLOYMENT - 414.SAPTIVA.COM                  ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    log_warning "Only deploying API container (Web/DB unchanged)"

    # Step 1: Build API image only
    step "Step 1/4: Build API Image"

    log_info "Building API image..."
    docker build -f apps/api/Dockerfile -t octavios-api:latest --target production apps/api

    log_success "API image built successfully"

    # Step 2: Export API image only
    step "Step 2/4: Export API Image"

    log_info "Exporting API image..."
    docker save octavios-api:latest | gzip > /tmp/api-only.tar.gz

    FILESIZE=$(du -h /tmp/api-only.tar.gz | cut -f1)
    log_success "API image exported: $FILESIZE"

    # Step 3: Transfer to server
    step "Step 3/4: Transfer to Server"

    log_info "Transferring API image to $DEMO_SERVER..."
    scp /tmp/api-only.tar.gz "$DEMO_SERVER:/tmp/"
    log_success "Transfer complete"

    # Step 4: Load and restart API container only
    step "Step 4/4: Deploy API Container"

    log_info "Loading API image and restarting container..."
    ssh "$DEMO_SERVER" "
        gunzip -c /tmp/api-only.tar.gz | docker load
        rm /tmp/api-only.tar.gz
        cd $DEMO_PATH
        docker compose --env-file envs/.env.prod -f infra/docker-compose.cloudflare.yml up -d --no-deps --force-recreate api
        echo 'Waiting for API to start...'
        sleep 10
        docker compose --env-file envs/.env.prod -f infra/docker-compose.cloudflare.yml ps api
    "

    log_success "API container deployed"

    # Cleanup local tar
    rm -f /tmp/api-only.tar.gz

    # Summary
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  API-ONLY DEPLOYMENT COMPLETE                                 ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Domain:${NC}       https://414.saptiva.com/api"
    echo -e "${BLUE}Status:${NC}       API container restarted"
    echo ""
    echo -e "${YELLOW}Note:${NC} Web, MongoDB, Redis, MinIO unchanged"
    echo ""
}

main "$@"
