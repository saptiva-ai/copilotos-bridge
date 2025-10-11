#!/bin/bash
# ========================================
# CONFIGURATION VALIDATION SCRIPT
# ========================================
# Validates configuration consistency across environments
#
# Usage: ./scripts/validate-config.sh

set -e

# Status symbols
RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "
NC=""

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0

# Functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}${NC} $1"
}

log_error() {
    echo -e "${RED}${NC} $1"
    ((ERRORS++))
}

log_warning() {
    echo -e "${YELLOW}${NC} $1"
}

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}         CONFIGURATION VALIDATION                            ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check required environment files exist
log_info "Checking environment files..."

if [ ! -f "$PROJECT_ROOT/envs/.env" ]; then
    log_error "envs/.env not found"
else
    log_success "envs/.env exists"
fi

if [ ! -f "$PROJECT_ROOT/envs/.env.prod" ]; then
    log_error "envs/.env.prod not found"
else
    log_success "envs/.env.prod exists"
fi

# Check required variables in .env.prod
log_info "Validating required variables in .env.prod..."

REQUIRED_VARS=(
    "MONGODB_USER"
    "MONGODB_PASSWORD"
    "MONGODB_DATABASE"
    "REDIS_PASSWORD"
    "JWT_SECRET_KEY"
    "SECRET_KEY"
    "SAPTIVA_API_KEY"
    "PROD_SERVER_IP"
    "PROD_SERVER_USER"
    "PROD_DEPLOY_PATH"
    "PROD_DOMAIN"
)

for VAR in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${VAR}=" "$PROJECT_ROOT/envs/.env.prod" 2>/dev/null; then
        log_error "Missing required variable in .env.prod: $VAR"
    else
        log_success "$VAR is defined"
    fi
done

# Validate docker-compose files syntax
log_info "Validating docker-compose.yml syntax..."
cd "$PROJECT_ROOT/infra"

if docker compose -f docker-compose.yml config > /dev/null 2>&1; then
    log_success "docker-compose.yml is valid"
else
    log_error "docker-compose.yml has syntax errors"
fi

if [ -f "docker-compose.prod.yml" ]; then
    log_info "Validating docker-compose.prod.yml syntax..."
    if docker compose -f docker-compose.yml -f docker-compose.prod.yml config > /dev/null 2>&1; then
        log_success "docker-compose.prod.yml is valid"
    else
        log_error "docker-compose.prod.yml has syntax errors"
    fi
fi

# Check for hardcoded env_file in base compose
log_info "Checking for hardcoded env_file directives..."

if grep -q "env_file:" "$PROJECT_ROOT/infra/docker-compose.yml"; then
    log_warning "Found env_file directive in docker-compose.yml"
    log_warning "Consider using environment variables instead for better flexibility"
fi

# Validate Dockerfiles exist
log_info "Checking Dockerfiles..."

if [ ! -f "$PROJECT_ROOT/apps/api/Dockerfile" ]; then
    log_error "apps/api/Dockerfile not found"
else
    log_success "apps/api/Dockerfile exists"
fi

if [ ! -f "$PROJECT_ROOT/apps/web/Dockerfile" ]; then
    log_error "apps/web/Dockerfile not found"
else
    log_success "apps/web/Dockerfile exists"
fi

# Check for production build targets in Dockerfiles
log_info "Validating Dockerfile build targets..."

if grep -q "FROM.*AS production" "$PROJECT_ROOT/apps/api/Dockerfile"; then
    log_success "API Dockerfile has 'production' target"
else
    log_error "API Dockerfile missing 'production' target"
fi

if grep -q "FROM.*AS runner" "$PROJECT_ROOT/apps/web/Dockerfile"; then
    log_success "Web Dockerfile has 'runner' target"
else
    log_error "Web Dockerfile missing 'runner' target"
fi

# Check deployment scripts exist
log_info "Checking deployment scripts..."

SCRIPTS=(
    "scripts/deploy-with-tar.sh"
    "scripts/backup-mongodb.sh"
    "scripts/restore-mongodb.sh"
)

for SCRIPT in "${SCRIPTS[@]}"; do
    if [ ! -f "$PROJECT_ROOT/$SCRIPT" ]; then
        log_error "$SCRIPT not found"
    elif [ ! -x "$PROJECT_ROOT/$SCRIPT" ]; then
        log_warning "$SCRIPT exists but is not executable"
    else
        log_success "$SCRIPT is ready"
    fi
done

# Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}VALIDATION PASSED${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    log_success "All configuration checks passed"
    exit 0
else
    echo -e "${RED}VALIDATION FAILED${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    log_error "Found $ERRORS error(s). Please fix before deployment."
    exit 1
fi
