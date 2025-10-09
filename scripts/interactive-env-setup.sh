#!/bin/bash
################################################################################
# Interactive Environment Setup Script
#
# Creates .env file with secure defaults and user input for sensitive values.
# Supports both development and production environments.
#
# Usage:
#   ./scripts/interactive-env-setup.sh [development|production]
#
# Features:
#   - Auto-generates strong secrets (JWT, passwords)
#   - Validates user input
#   - Preserves existing values (with confirmation)
#   - No hardcoded secrets
#   - Idempotent (safe to run multiple times)
################################################################################

set -e  # Exit on error

# ============================================================================
# COLORS & FORMATTING
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}" >&2
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

generate_secret() {
    # Generate cryptographically secure random string
    openssl rand -hex 32 2>/dev/null || echo "$(date +%s | sha256sum | head -c 64)"
}

generate_password() {
    # Generate strong password (24 characters, alphanumeric + symbols)
    openssl rand -base64 24 2>/dev/null | tr -d "=+/" | cut -c1-24 || echo "ChangeMe$(date +%s)"
}

validate_email() {
    local email="$1"
    if [[ "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        return 0
    else
        return 1
    fi
}

validate_url() {
    local url="$1"
    if [[ "$url" =~ ^https?:// ]]; then
        return 0
    else
        return 1
    fi
}

prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local secret="${4:-false}"

    if [ -n "$default" ]; then
        if [ "$secret" = "true" ]; then
            # Don't show full secret, just hint
            local hint="${default:0:8}...${default: -4}"
            echo -en "${CYAN}$prompt${NC} ${YELLOW}[current: $hint]${NC}: "
        else
            echo -en "${CYAN}$prompt${NC} ${YELLOW}[$default]${NC}: "
        fi
    else
        echo -en "${CYAN}$prompt${NC}: "
    fi

    read -r input
    echo "${input:-$default}"
}

prompt_yes_no() {
    local prompt="$1"
    local default="${2:-n}"

    if [ "$default" = "y" ]; then
        echo -en "${CYAN}$prompt${NC} ${YELLOW}[Y/n]${NC}: "
    else
        echo -en "${CYAN}$prompt${NC} ${YELLOW}[y/N]${NC}: "
    fi

    read -r response
    response="${response:-$default}"

    if [[ "$response" =~ ^[Yy] ]]; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# MAIN CONFIGURATION
# ============================================================================

# Determine environment
ENVIRONMENT="${1:-development}"
if [ "$ENVIRONMENT" != "development" ] && [ "$ENVIRONMENT" != "production" ]; then
    print_error "Invalid environment. Use 'development' or 'production'."
    echo "Usage: $0 [development|production]"
    exit 1
fi

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENVS_DIR="$PROJECT_ROOT/envs"
ENV_FILE="$ENVS_DIR/.env"
ENV_LOCAL_FILE="$ENVS_DIR/.env.local"

if [ "$ENVIRONMENT" = "development" ]; then
    TEMPLATE_FILE="$ENVS_DIR/.env.local.example"
    TARGET_FILE="$ENV_LOCAL_FILE"
else
    TEMPLATE_FILE="$ENVS_DIR/.env.production.example"
    TARGET_FILE="$ENVS_DIR/.env.prod"
fi

# ============================================================================
# WELCOME & CHECKS
# ============================================================================

clear
print_header "🤖 CopilotOS - Interactive Environment Setup"

echo -e "${BOLD}Environment:${NC} $ENVIRONMENT"
echo -e "${BOLD}Target File:${NC} $TARGET_FILE"
echo ""

# Check for required tools
if ! command -v openssl &> /dev/null; then
    print_warning "openssl not found. Using fallback for secret generation."
    sleep 1
fi

# Check if target file exists
EXISTING_VALUES=()
if [ -f "$TARGET_FILE" ]; then
    print_warning "File $TARGET_FILE already exists."
    if ! prompt_yes_no "Do you want to update it (existing values will be preserved)?"; then
        print_info "Aborted. No changes made."
        exit 0
    fi
    echo ""
    print_info "Loading existing values..."
    # shellcheck disable=SC1090
    source "$TARGET_FILE" 2>/dev/null || true
fi

# ============================================================================
# COLLECT CONFIGURATION
# ============================================================================

print_header "📝 Configuration"

# ──────────────────────────────────────────────────────────────────────────
# 1. BASIC CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────
echo -e "${BOLD}1. Basic Configuration${NC}"
echo ""

COMPOSE_PROJECT_NAME=$(prompt_with_default \
    "Project name (for Docker Compose)" \
    "${COMPOSE_PROJECT_NAME:-copilotos}" \
    "COMPOSE_PROJECT_NAME")

if [ "$ENVIRONMENT" = "production" ]; then
    DOMAIN=$(prompt_with_default \
        "Server domain or IP" \
        "${DOMAIN:-localhost}" \
        "DOMAIN")
else
    DOMAIN="localhost"
fi

echo ""

# ──────────────────────────────────────────────────────────────────────────
# 1.5. DEPLOYMENT CONFIGURATION (Production only)
# ──────────────────────────────────────────────────────────────────────────
if [ "$ENVIRONMENT" = "production" ]; then
    echo -e "${BOLD}1.5. Deployment Configuration${NC}"
    echo ""

    print_info "These settings are used by deployment scripts (make deploy-*, etc.)"
    echo ""

    PROD_SERVER_IP=$(prompt_with_default \
        "Production server IP address" \
        "${PROD_SERVER_IP:-$DOMAIN}" \
        "PROD_SERVER_IP")

    PROD_SERVER_USER=$(prompt_with_default \
        "SSH username for deployment" \
        "${PROD_SERVER_USER:-$(whoami)}" \
        "PROD_SERVER_USER")

    PROD_DEPLOY_PATH=$(prompt_with_default \
        "Deployment path on server" \
        "${PROD_DEPLOY_PATH:-/opt/copilotos-bridge}" \
        "PROD_DEPLOY_PATH")

    PROD_BACKUP_DIR=$(prompt_with_default \
        "Backup directory on server" \
        "${PROD_BACKUP_DIR:-/opt/backups/copilotos-production}" \
        "PROD_BACKUP_DIR")

    # Constructed values
    PROD_SERVER_HOST="${PROD_SERVER_USER}@${PROD_SERVER_IP}"
    DEPLOY_SERVER="${PROD_SERVER_HOST}"
    DEPLOY_PATH="${PROD_DEPLOY_PATH}"
    BACKUP_DIR="${PROD_BACKUP_DIR}"

    print_success "Deployment configuration set"
    echo ""
fi

echo ""

# ──────────────────────────────────────────────────────────────────────────
# 2. DATABASE CREDENTIALS
# ──────────────────────────────────────────────────────────────────────────
echo -e "${BOLD}2. Database Credentials${NC}"
echo ""

if [ -z "$MONGODB_PASSWORD" ] || [ "$MONGODB_PASSWORD" = "secure_password_change_me" ]; then
    print_info "Generating secure MongoDB password..."
    MONGODB_PASSWORD=$(generate_password)
    print_success "Generated: ${MONGODB_PASSWORD:0:8}...${MONGODB_PASSWORD: -4}"
else
    if prompt_yes_no "Use existing MongoDB password?"; then
        print_success "Using existing MongoDB password"
    else
        MONGODB_PASSWORD=$(generate_password)
        print_success "Generated new MongoDB password"
    fi
fi

MONGODB_USER=$(prompt_with_default \
    "MongoDB username" \
    "${MONGODB_USER:-copilotos_user}" \
    "MONGODB_USER")

if [ -z "$REDIS_PASSWORD" ] || [ "$REDIS_PASSWORD" = "redis_password_change_me" ]; then
    print_info "Generating secure Redis password..."
    REDIS_PASSWORD=$(generate_password)
    print_success "Generated: ${REDIS_PASSWORD:0:8}...${REDIS_PASSWORD: -4}"
else
    if prompt_yes_no "Use existing Redis password?"; then
        print_success "Using existing Redis password"
    else
        REDIS_PASSWORD=$(generate_password)
        print_success "Generated new Redis password"
    fi
fi

echo ""

# ──────────────────────────────────────────────────────────────────────────
# 3. SECURITY SECRETS
# ──────────────────────────────────────────────────────────────────────────
echo -e "${BOLD}3. Security Secrets${NC}"
echo ""

if [ -z "$JWT_SECRET_KEY" ] || [ "$JWT_SECRET_KEY" = "dev-jwt-secret-change-in-production" ]; then
    print_info "Generating JWT secret key (64 characters)..."
    JWT_SECRET_KEY=$(generate_secret)
    print_success "Generated secure JWT secret"
else
    if prompt_yes_no "Use existing JWT secret key?"; then
        print_success "Using existing JWT secret"
    else
        JWT_SECRET_KEY=$(generate_secret)
        print_success "Generated new JWT secret"
    fi
fi

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "dev-secret-change-in-production" ]; then
    print_info "Generating application secret key (64 characters)..."
    SECRET_KEY=$(generate_secret)
    print_success "Generated secure application secret"
else
    if prompt_yes_no "Use existing application secret key?"; then
        print_success "Using existing application secret"
    else
        SECRET_KEY=$(generate_secret)
        print_success "Generated new application secret"
    fi
fi

echo ""

# ──────────────────────────────────────────────────────────────────────────
# 4. EXTERNAL API KEYS
# ──────────────────────────────────────────────────────────────────────────
echo -e "${BOLD}4. External API Keys${NC}"
echo ""

print_warning "SAPTIVA API key is REQUIRED for the application to work."
while true; do
    SAPTIVA_API_KEY=$(prompt_with_default \
        "SAPTIVA API key" \
        "${SAPTIVA_API_KEY:-}" \
        "SAPTIVA_API_KEY" \
        "true")

    if [ -z "$SAPTIVA_API_KEY" ] || [ "$SAPTIVA_API_KEY" = "your-saptiva-api-key-here" ]; then
        print_error "SAPTIVA API key cannot be empty!"
        if ! prompt_yes_no "Do you want to enter it now?"; then
            print_warning "Skipping SAPTIVA API key. You'll need to set it manually later."
            SAPTIVA_API_KEY="your-saptiva-api-key-here"
            break
        fi
    else
        print_success "SAPTIVA API key set"
        break
    fi
done

SAPTIVA_BASE_URL=$(prompt_with_default \
    "SAPTIVA base URL" \
    "${SAPTIVA_BASE_URL:-https://api.saptiva.com}" \
    "SAPTIVA_BASE_URL")

echo ""
print_info "Aletheia is optional (for deep research features)."
if prompt_yes_no "Do you want to configure Aletheia?"; then
    ALETHEIA_BASE_URL=$(prompt_with_default \
        "Aletheia base URL" \
        "${ALETHEIA_BASE_URL:-https://aletheia.saptiva.ai}" \
        "ALETHEIA_BASE_URL")

    ALETHEIA_API_KEY=$(prompt_with_default \
        "Aletheia API key (optional)" \
        "${ALETHEIA_API_KEY:-}" \
        "ALETHEIA_API_KEY" \
        "true")
else
    ALETHEIA_BASE_URL="${ALETHEIA_BASE_URL:-https://aletheia.saptiva.ai}"
    ALETHEIA_API_KEY="${ALETHEIA_API_KEY:-}"
fi

echo ""

# ──────────────────────────────────────────────────────────────────────────
# 5. FRONTEND CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────
echo -e "${BOLD}5. Frontend Configuration${NC}"
echo ""

if [ "$ENVIRONMENT" = "production" ]; then
    NEXT_PUBLIC_API_URL=$(prompt_with_default \
        "API URL (frontend will connect to this)" \
        "http://${DOMAIN}:8001" \
        "NEXT_PUBLIC_API_URL")

    NODE_ENV="production"
else
    NEXT_PUBLIC_API_URL="http://localhost:8001"
    NODE_ENV="development"
fi

print_success "Frontend configured"

echo ""

# ============================================================================
# GENERATE .ENV FILE
# ============================================================================

print_header "💾 Generating Configuration File"

# Create backup if file exists
if [ -f "$TARGET_FILE" ]; then
    BACKUP_FILE="${TARGET_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$TARGET_FILE" "$BACKUP_FILE"
    print_info "Backup created: $BACKUP_FILE"
fi

# Generate .env file
cat > "$TARGET_FILE" << EOF
# ============================================================================
# AUTO-GENERATED ENVIRONMENT CONFIGURATION
# ============================================================================
# Generated on: $(date '+%Y-%m-%d %H:%M:%S')
# Environment: $ENVIRONMENT
# DO NOT COMMIT THIS FILE TO VERSION CONTROL
# ============================================================================

# ============================================================================
# BASIC CONFIGURATION
# ============================================================================
COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME
DOMAIN=$DOMAIN
NODE_ENV=$NODE_ENV

# ============================================================================
# DEPLOYMENT CONFIGURATION (Production)
# ============================================================================
$(if [ "$ENVIRONMENT" = "production" ]; then
cat << DEPLOY_CONF
PROD_SERVER_IP=$PROD_SERVER_IP
PROD_SERVER_USER=$PROD_SERVER_USER
PROD_SERVER_HOST=$PROD_SERVER_HOST
PROD_DEPLOY_PATH=$PROD_DEPLOY_PATH
PROD_BACKUP_DIR=$PROD_BACKUP_DIR

# Legacy variables (backward compatibility)
DEPLOY_SERVER=$DEPLOY_SERVER
DEPLOY_PATH=$DEPLOY_PATH
BACKUP_DIR=$BACKUP_DIR
DEPLOY_CONF
fi)

# ============================================================================
# FRONTEND CONFIGURATION
# ============================================================================
NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
NEXT_TELEMETRY_DISABLED=1

# Feature Flags
NEXT_PUBLIC_FEATURE_WEB_SEARCH=true
NEXT_PUBLIC_FEATURE_DEEP_RESEARCH=true
NEXT_PUBLIC_FEATURE_ADD_FILES=false
NEXT_PUBLIC_FEATURE_GOOGLE_DRIVE=false
NEXT_PUBLIC_FEATURE_CANVAS=false
NEXT_PUBLIC_FEATURE_AGENT_MODE=false
NEXT_PUBLIC_FEATURE_MIC=false

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
MONGODB_USER=$MONGODB_USER
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_DATABASE=copilotos
MONGODB_PORT=27017

REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_PORT=6379

# ============================================================================
# AUTHENTICATION / SECURITY
# ============================================================================
JWT_SECRET_KEY=$JWT_SECRET_KEY
SECRET_KEY=$SECRET_KEY
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=HS256

# ============================================================================
# EXTERNAL APIS
# ============================================================================
SAPTIVA_API_KEY=$SAPTIVA_API_KEY
SAPTIVA_BASE_URL=$SAPTIVA_BASE_URL
SAPTIVA_TIMEOUT=120
SAPTIVA_MAX_RETRIES=3

# Chat Configuration
CHAT_DEFAULT_MODEL=Saptiva Turbo
CHAT_ALLOWED_MODELS=Saptiva Turbo,Saptiva Cortex,Saptiva Ops,Saptiva Coder

# Aletheia (optional)
ALETHEIA_BASE_URL=$ALETHEIA_BASE_URL
ALETHEIA_API_KEY=$ALETHEIA_API_KEY
ALETHEIA_TIMEOUT=120
ALETHEIA_MAX_RETRIES=3

# Deep Research Feature Flags
DEEP_RESEARCH_KILL_SWITCH=true
DEEP_RESEARCH_ENABLED=false
DEEP_RESEARCH_AUTO=false

# ============================================================================
# DEVELOPMENT/PRODUCTION SETTINGS
# ============================================================================
DEBUG=$([ "$ENVIRONMENT" = "development" ] && echo "true" || echo "false")
LOG_LEVEL=$([ "$ENVIRONMENT" = "development" ] && echo "debug" || echo "info")
RATE_LIMIT_REQUESTS_PER_MINUTE=$([ "$ENVIRONMENT" = "development" ] && echo "1000" || echo "100")

# ============================================================================
# CORS & HOSTS
# ============================================================================
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000","http://$DOMAIN:3000"]
ALLOWED_HOSTS=["localhost","127.0.0.1","$DOMAIN","web","api"]

# ============================================================================
# OBSERVABILITY
# ============================================================================
OTEL_SERVICE_NAME=copilotos-bridge-$ENVIRONMENT
OTEL_ENABLED=false
JAEGER_ENDPOINT=http://localhost:14268/api/traces

# ============================================================================
# PERFORMANCE (PRODUCTION)
# ============================================================================
WORKERS=4
MAX_CONNECTIONS=100
POOL_SIZE=20
STREAM_BACKPRESSURE_MAX=2000
STREAM_HEARTBEAT_INTERVAL_MS=3000
SSE_KEEP_ALIVE_TIMEOUT_MS=45000
EOF

# Set restrictive permissions
chmod 600 "$TARGET_FILE"

print_success "Configuration file created: $TARGET_FILE"

# Also create .env symlink for backward compatibility
if [ "$TARGET_FILE" = "$ENV_LOCAL_FILE" ]; then
    ln -sf .env.local "$ENVS_DIR/.env"
    print_success "Symlink created: .env -> .env.local"
fi

# ============================================================================
# SUMMARY
# ============================================================================

print_header "✅ Setup Complete!"

echo -e "${BOLD}Configuration Summary:${NC}"
echo ""
echo -e "  ${CYAN}Environment:${NC}        $ENVIRONMENT"
echo -e "  ${CYAN}Config File:${NC}        $TARGET_FILE"
echo -e "  ${CYAN}Domain:${NC}             $DOMAIN"
echo -e "  ${CYAN}API URL:${NC}            $NEXT_PUBLIC_API_URL"
echo -e "  ${CYAN}MongoDB User:${NC}       $MONGODB_USER"
echo -e "  ${CYAN}SAPTIVA API:${NC}        ${SAPTIVA_API_KEY:0:12}..."
echo ""

print_warning "Security Notes:"
echo "  • Secrets have been auto-generated"
echo "  • File permissions set to 600 (owner read/write only)"
echo "  • NEVER commit this file to version control"
echo "  • Keep these credentials secure"
echo ""

echo -e "${BOLD}Next Steps:${NC}"
echo ""
if [ "$ENVIRONMENT" = "development" ]; then
    echo "  1. Review the configuration:"
    echo -e "     ${GREEN}cat $TARGET_FILE${NC}"
    echo ""
    echo "  2. Start the development environment:"
    echo -e "     ${GREEN}make dev${NC}"
    echo ""
    echo "  3. Create a demo user:"
    echo -e "     ${GREEN}make create-demo-user${NC}"
    echo ""
    echo "  4. Access the application:"
    echo -e "     ${GREEN}http://localhost:3000${NC}"
else
    echo "  1. Review the configuration:"
    echo -e "     ${GREEN}cat $TARGET_FILE${NC}"
    echo ""
    echo "  2. Deploy to production:"
    echo -e "     ${GREEN}make deploy-clean${NC}"
    echo ""
    echo "  3. Verify deployment:"
    echo -e "     ${GREEN}make deploy-status${NC}"
fi

echo ""
print_success "Setup completed successfully!"
echo ""
