#!/bin/bash
# ============================================================================
# DEPLOYMENT VALIDATION SCRIPT
# ============================================================================
# Validates deployment prerequisites before pushing to production
# Usage: ./scripts/deploy/validate-deploy.sh <version>
# ============================================================================

set -e

VERSION="${1:-}"
REGISTRY_USER="jazielflores1998"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Validation counters
ERRORS=0
WARNINGS=0

echo ""
echo "════════════════════════════════════════════════════════════"
echo "🔍 PRE-DEPLOYMENT VALIDATION"
echo "════════════════════════════════════════════════════════════"
echo ""

# ============================================================================
# 1. VALIDATE REQUIRED ENVIRONMENT VARIABLES
# ============================================================================
log_info "Step 1/5: Validating environment variables..."

check_env_var() {
    local var_name="$1"
    local min_length="${2:-1}"

    if [ -z "${!var_name}" ]; then
        log_error "Environment variable $var_name is not set"
        ((ERRORS++))
        return 1
    fi

    local var_value="${!var_name}"
    local var_length=${#var_value}
    if [ "$var_length" -lt "$min_length" ]; then
        log_error "Environment variable $var_name is too short (${var_length} < ${min_length})"
        ((ERRORS++))
        return 1
    fi

    log_success "$var_name is set (${var_length} chars)"
    return 0
}

# Load environment file
if [ -f "envs/.env.prod" ]; then
    export $(grep -v '^#' envs/.env.prod | grep -E '^(SECRET_KEY|JWT_SECRET_KEY|DEPLOY_SERVER)=' | xargs)
fi

check_env_var "SECRET_KEY" 32
check_env_var "JWT_SECRET_KEY" 32
check_env_var "DEPLOY_SERVER"

echo ""

# ============================================================================
# 2. VALIDATE DOCKER HUB IMAGES EXIST
# ============================================================================
log_info "Step 2/5: Validating Docker Hub images..."

SERVICES=("backend" "web" "file-manager" "bank-advisor")

check_image_exists() {
    local service="$1"
    local version="$2"
    local image="${REGISTRY_USER}/octavios-invex-${service}:${version}"

    if docker manifest inspect "$image" > /dev/null 2>&1; then
        log_success "Image exists: $image"
        return 0
    else
        log_warning "Image NOT found: $image"
        ((WARNINGS++))
        return 1
    fi
}

if [ -n "$VERSION" ]; then
    for service in "${SERVICES[@]}"; do
        check_image_exists "$service" "$VERSION"
    done
else
    log_warning "No version specified, skipping image validation"
    ((WARNINGS++))
fi

echo ""

# ============================================================================
# 3. VALIDATE GIT STATUS
# ============================================================================
log_info "Step 3/5: Validating git status..."

if [ -n "$(git status --porcelain)" ]; then
    log_warning "Working directory has uncommitted changes"
    ((WARNINGS++))
else
    log_success "Working directory is clean"
fi

CURRENT_BRANCH=$(git branch --show-current)
log_info "Current branch: $CURRENT_BRANCH"

echo ""

# ============================================================================
# 4. VALIDATE DOCKER COMPOSE CONFIG
# ============================================================================
log_info "Step 4/5: Validating docker-compose configuration..."

if docker compose -f infra/docker-compose.yml \
                  -f infra/docker-compose.production.yml \
                  -f infra/docker-compose.registry.yml \
                  config > /dev/null 2>&1; then
    log_success "Docker Compose configuration is valid"
else
    log_error "Docker Compose configuration has errors"
    ((ERRORS++))
fi

echo ""

# ============================================================================
# 5. VALIDATE SSH CONNECTION TO PRODUCTION SERVER
# ============================================================================
log_info "Step 5/5: Validating SSH connection..."

if [ -n "$DEPLOY_SERVER" ]; then
    if ssh -o ConnectTimeout=5 -o BatchMode=yes "$DEPLOY_SERVER" "echo 'SSH OK'" > /dev/null 2>&1; then
        log_success "SSH connection to $DEPLOY_SERVER successful"
    else
        log_error "Cannot connect to $DEPLOY_SERVER via SSH"
        ((ERRORS++))
    fi
else
    log_warning "DEPLOY_SERVER not set, skipping SSH validation"
    ((WARNINGS++))
fi

echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo "════════════════════════════════════════════════════════════"
echo "📊 VALIDATION SUMMARY"
echo "════════════════════════════════════════════════════════════"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    log_success "All validations passed! Ready to deploy."
    exit 0
elif [ $ERRORS -eq 0 ]; then
    log_warning "$WARNINGS warning(s) found. Review before deploying."
    exit 0
else
    log_error "$ERRORS error(s) and $WARNINGS warning(s) found."
    log_error "Fix errors before deploying to production!"
    exit 1
fi
