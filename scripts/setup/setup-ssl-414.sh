#!/bin/bash
# ========================================
# SSL/TLS SETUP SCRIPT FOR 414.SAPTIVA.COM
# ========================================
# Obtains and configures SSL certificates using Let's Encrypt
#
# This script:
# ✅ Creates necessary directories for Certbot
# ✅ Generates dummy certificates for initial nginx start
# ✅ Obtains real Let's Encrypt certificates
# ✅ Configures automatic certificate renewal
#
# Usage:
#   ./scripts/setup-ssl-414.sh [--staging]
#
# Options:
#   --staging  Use Let's Encrypt staging environment (for testing)
#
# Requirements:
#   - Domain 414.saptiva.com must point to this server's IP
#   - Ports 80 and 443 must be open
#   - Docker and Docker Compose installed
#
set -e
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DOMAIN="414.saptiva.com"
EMAIL="devops@saptiva.com"  # Update with actual email
STAGING=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --staging)
            STAGING=1
            shift
            ;;
        *)
            echo "Unknown option: $1"
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
# MAIN SETUP
# ========================================
main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  SSL/TLS SETUP FOR 414.SAPTIVA.COM                           ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ $STAGING -eq 1 ]; then
        log_warning "Running in STAGING mode (test certificates)"
    fi

    # Step 1: Verify domain DNS
    step "Step 1/5: Verify Domain DNS"

    log_info "Checking if $DOMAIN resolves to this server..."
    DOMAIN_IP=$(dig +short $DOMAIN | tail -1)
    SERVER_IP=$(curl -s ifconfig.me)

    if [ -z "$DOMAIN_IP" ]; then
        log_error "Domain $DOMAIN does not resolve"
        echo "Please configure DNS A record to point to $SERVER_IP"
        exit 1
    fi

    if [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
        log_warning "Domain resolves to $DOMAIN_IP but server IP is $SERVER_IP"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_success "Domain resolves correctly to $SERVER_IP"
    fi

    # Step 2: Create directories
    step "Step 2/5: Create Certificate Directories"

    log_info "Creating Certbot directories..."
    mkdir -p data/certbot/conf
    mkdir -p data/certbot/www
    mkdir -p logs/nginx

    log_success "Directories created"

    # Step 3: Create dummy certificates
    step "Step 3/5: Create Dummy Certificates"

    log_info "Generating self-signed certificates for initial nginx start..."

    mkdir -p "data/certbot/conf/live/$DOMAIN"

    if [ ! -f "data/certbot/conf/live/$DOMAIN/fullchain.pem" ]; then
        openssl req -x509 -nodes -newkey rsa:2048 \
            -days 1 \
            -keyout "data/certbot/conf/live/$DOMAIN/privkey.pem" \
            -out "data/certbot/conf/live/$DOMAIN/fullchain.pem" \
            -subj "/CN=$DOMAIN"

        # Create chain.pem (same as fullchain for dummy)
        cp "data/certbot/conf/live/$DOMAIN/fullchain.pem" \
           "data/certbot/conf/live/$DOMAIN/chain.pem"

        log_success "Dummy certificates created"
    else
        log_info "Certificates already exist, skipping"
    fi

    # Step 4: Start nginx
    step "Step 4/5: Start Nginx"

    log_info "Starting nginx container..."
    docker compose -f infra/docker-compose.414.saptiva.com.yml up -d nginx

    sleep 5

    # Check nginx is running
    if ! docker ps | grep -q "nginx"; then
        log_error "Nginx failed to start"
        docker compose -f infra/docker-compose.414.saptiva.com.yml logs nginx
        exit 1
    fi

    log_success "Nginx started successfully"

    # Step 5: Obtain Let's Encrypt certificates
    step "Step 5/5: Obtain Let's Encrypt Certificates"

    log_info "Requesting certificates from Let's Encrypt..."

    STAGING_ARG=""
    if [ $STAGING -eq 1 ]; then
        STAGING_ARG="--staging"
    fi

    docker compose -f infra/docker-compose.414.saptiva.com.yml run --rm certbot \
        certonly --webroot -w /var/www/certbot \
        $STAGING_ARG \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        -d $DOMAIN \
        --force-renewal

    if [ $? -eq 0 ]; then
        log_success "Certificates obtained successfully!"

        # Reload nginx to use real certificates
        log_info "Reloading nginx with real certificates..."
        docker compose -f infra/docker-compose.414.saptiva.com.yml exec nginx nginx -s reload

        log_success "Nginx reloaded"
    else
        log_error "Failed to obtain certificates"
        exit 1
    fi

    # Summary
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  SSL/TLS SETUP COMPLETE                                       ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Domain:${NC}       $DOMAIN"
    echo -e "${BLUE}Status:${NC}       SSL configured"
    echo -e "${BLUE}Renewal:${NC}      Automatic (certbot container)"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Test HTTPS:  https://$DOMAIN"
    echo "  2. Check SSL:   https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
    echo "  3. Deploy app:  make deploy-demo"
    echo ""
    echo -e "${YELLOW}Certificate renewal:${NC}"
    echo "  Certificates will auto-renew every 12 hours via certbot container"
    echo "  Manual renewal: docker compose -f infra/docker-compose.414.saptiva.com.yml run --rm certbot renew"
    echo ""
}

# Run main function
main "$@"
