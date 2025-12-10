#!/bin/bash
################################################################################
# Environment Variables Validation Script
#
# Validates critical environment variables required for the application.
# Can run in different modes: strict (all required), warn (show warnings), info
#
# Usage:
#   ./scripts/env-checker.sh [strict|warn|info]
#
# Exit codes:
#   0 - All critical variables are set
#   1 - Missing critical variables (strict mode)
#   2 - Missing optional variables (warn mode, exits 0)
################################################################################

set -eo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

MODE="${1:-warn}"  # strict, warn, info
ENV_FILE="${2:-envs/.env}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Status symbols
CHECK="✓"
CROSS="✗"
WARN="▲"
INFO="ℹ"

# ============================================================================
# CRITICAL VARIABLES (must be set)
# ============================================================================

CRITICAL_VARS=(
    # Core
    "COMPOSE_PROJECT_NAME:Project identifier for Docker Compose"
    "HOST:API server host binding"
    "PORT:API server port"

    # Database
    "MONGODB_URL:MongoDB connection string"
    "MONGODB_DATABASE:MongoDB database name"
    "REDIS_URL:Redis connection string"

    # Security
    "JWT_SECRET_KEY:JWT token signing key (32+ chars)"
    "SECRET_KEY:General encryption key (32+ chars)"

    # External APIs
    "SAPTIVA_API_URL:SAPTIVA LLM API endpoint"
    "SAPTIVA_API_KEY:SAPTIVA API authentication key"

    # Storage
    "MINIO_ENDPOINT:MinIO S3 endpoint"
    "MINIO_ACCESS_KEY:MinIO access credentials"
    "MINIO_SECRET_KEY:MinIO secret credentials"
)

# ============================================================================
# IMPORTANT VARIABLES (recommended but not critical)
# ============================================================================

IMPORTANT_VARS=(
    # Frontend
    "NEXT_PUBLIC_API_URL:Frontend API base URL"
    "CORS_ORIGINS:Allowed CORS origins"

    # Optional APIs
    "ALETHEIA_API_URL:Aletheia research API endpoint"

    # Performance
    "REDIS_PASSWORD:Redis authentication password"
    "MINIO_DEFAULT_PUBLIC_HOST:MinIO public access host"
)

# ============================================================================
# DEVELOPMENT VARIABLES (optional, for dev environment)
# ============================================================================

DEV_VARS=(
    "DEBUG:Enable debug mode"
    "LOG_LEVEL:Logging verbosity level"
    "NEXT_PUBLIC_ENABLE_DEBUG_MODE:Frontend debug mode"
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

check_variable() {
    local var_def="$1"
    local var_name="${var_def%%:*}"
    local var_desc="${var_def#*:}"
    local severity="$2"  # critical, important, dev

    # Load from .env file if exists
    local value=""
    if [ -f "$ENV_FILE" ]; then
        value=$(grep "^${var_name}=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | sed 's/^"//' | sed 's/"$//')
    fi

    # Check if set (either in file or environment)
    if [ -z "$value" ]; then
        value="${!var_name}"
    fi

    # Defaults for internal services
    local note=""
    if [ -z "$value" ] && [ "$var_name" = "ALETHEIA_API_URL" ]; then
        value="http://aletheia:8000"
        note=" (default: aletheia service)"
    fi

    if [ -n "$value" ]; then
        # Variable is set
        if [ "$MODE" = "info" ]; then
            # Mask sensitive values
            local display_value="$value"
            if [[ "$var_name" =~ (KEY|SECRET|PASSWORD|TOKEN) ]]; then
                display_value="********${value: -4}"
            fi
            echo -e "  ${GREEN}${CHECK}${NC} ${var_name}=${display_value}${note}"
        else
            echo -e "  ${GREEN}${CHECK}${NC} ${var_name}${note}"
        fi
        return 0
    else
        # Variable is missing
        case "$severity" in
            critical)
                echo -e "  ${RED}${CROSS}${NC} ${var_name} - ${var_desc}"
                return 1
                ;;
            important)
                echo -e "  ${YELLOW}${WARN}${NC} ${var_name} - ${var_desc}"
                return 2
                ;;
            dev)
                echo -e "  ${CYAN}${INFO}${NC} ${var_name} - ${var_desc}"
                return 3
                ;;
        esac
    fi
}

validate_secret_length() {
    local var_name="$1"
    local min_length="${2:-32}"

    local value=""
    if [ -f "$ENV_FILE" ]; then
        value=$(grep "^${var_name}=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | sed 's/^"//' | sed 's/"$//')
    fi

    if [ -z "$value" ]; then
        value="${!var_name}"
    fi

    if [ -n "$value" ] && [ "${#value}" -lt "$min_length" ]; then
        echo -e "  ${YELLOW}${WARN}${NC} ${var_name} should be at least ${min_length} characters (current: ${#value})"
        return 1
    fi
    return 0
}

# ============================================================================
# MAIN VALIDATION
# ============================================================================

main() {
    print_header "Environment Variables Check"

    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}${CROSS} Environment file not found: ${ENV_FILE}${NC}"
        echo -e "${YELLOW}${WARN} Run 'make setup' to create it${NC}"
        echo ""
        exit 1
    fi

    echo -e "${CYAN}${INFO} Checking environment file: ${ENV_FILE}${NC}"
    echo ""

    # Track results
    local missing_critical=0
    local missing_important=0
    local missing_dev=0

    # Check critical variables
    print_header "Critical Variables (Required)"
    for var in "${CRITICAL_VARS[@]}"; do
        if ! check_variable "$var" "critical"; then
            missing_critical=$((missing_critical + 1))
        fi
    done

    # Check important variables
    if [ "$MODE" != "strict" ]; then
        print_header "Important Variables (Recommended)"
        for var in "${IMPORTANT_VARS[@]}"; do
            if ! check_variable "$var" "important"; then
                missing_important=$((missing_important + 1))
            fi
        done
    fi

    # Check development variables
    if [ "$MODE" = "info" ]; then
        print_header "Development Variables (Optional)"
        for var in "${DEV_VARS[@]}"; do
            if ! check_variable "$var" "dev"; then
                missing_dev=$((missing_dev + 1))
            fi
        done
    fi

    # Validate secret lengths
    if [ "$MODE" = "info" ] || [ "$MODE" = "warn" ]; then
        echo ""
        print_header "Security Validation"
        validate_secret_length "JWT_SECRET_KEY" 32
        validate_secret_length "SECRET_KEY" 32
    fi

    # Summary
    echo ""
    print_header "Summary"

    if [ $missing_critical -eq 0 ]; then
        echo -e "${GREEN}${CHECK} All critical variables are set${NC}"
    else
        echo -e "${RED}${CROSS} Missing ${missing_critical} critical variable(s)${NC}"
    fi

    if [ $missing_important -gt 0 ] && [ "$MODE" != "strict" ]; then
        echo -e "${YELLOW}${WARN} Missing ${missing_important} important variable(s)${NC}"
    fi

    if [ $missing_dev -gt 0 ] && [ "$MODE" = "info" ]; then
        echo -e "${CYAN}${INFO} Missing ${missing_dev} development variable(s)${NC}"
    fi

    echo ""

    # Exit codes
    if [ $missing_critical -gt 0 ]; then
        echo -e "${RED}${CROSS} Environment check failed${NC}"
        echo -e "${YELLOW}${WARN} Run 'make setup' to configure missing variables${NC}"
        echo ""
        exit 1
    fi

    if [ $missing_important -gt 0 ] && [ "$MODE" = "strict" ]; then
        echo -e "${YELLOW}${WARN} Environment check passed with warnings${NC}"
        echo ""
        exit 0
    fi

    echo -e "${GREEN}${CHECK} Environment check passed${NC}"
    echo ""
    exit 0
}

# ============================================================================
# ENTRYPOINT
# ============================================================================

main "$@"
