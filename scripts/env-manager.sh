#!/bin/bash

# ==============================================
# Environment Manager Script
# Handles global variables and environment switching
# ==============================================

set -e

# Status symbols for logs
GREEN="✔ "
YELLOW="▲ "
RED="✖ "
BLUE="▸ "
CYAN="◆ "
NC=""

# Global configuration
ENVS_DIR="envs"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Available environments
ENVIRONMENTS=("local" "staging" "prod")

show_help() {
    echo -e "${GREEN}Environment Manager${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC}"
    echo "  $0 [command] [environment]"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  check [env]          - Check environment variables"
    echo "  switch [env]         - Switch active environment"
    echo "  validate [env]       - Validate environment configuration"
    echo "  backup [env]         - Backup environment file"
    echo "  restore [env]        - Restore environment from backup"
    echo "  diff [env1] [env2]   - Compare two environments"
    echo "  list                 - List all environments"
    echo "  template [env]       - Create template from existing env"
    echo ""
    echo -e "${YELLOW}Environments:${NC} ${ENVIRONMENTS[*]}"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 check local"
    echo "  $0 switch prod"
    echo "  $0 validate staging"
    echo "  $0 diff local prod"
}

check_environment() {
    local env="$1"
    local env_file="$ENVS_DIR/.env.$env"

    echo -e "${CYAN}Checking environment: $env${NC}"
    echo ""

    if [[ ! -f "$env_file" ]]; then
        echo -e "${RED}Environment file not found: $env_file${NC}"
        return 1
    fi

    # Critical variables check
    local critical_vars=(
        "SAPTIVA_API_KEY"
        "JWT_SECRET_KEY"
        "MONGODB_URL"
        "REDIS_URL"
        "NODE_ENV"
    )

    local missing_vars=()
    local demo_mode=false

    echo -e "${YELLOW}Critical Variables:${NC}"
    for var in "${critical_vars[@]}"; do
        if grep -q "^${var}=" "$env_file"; then
            local value=$(grep "^${var}=" "$env_file" | cut -d'=' -f2- | tr -d '"')
            if [[ -n "$value" && "$value" != "" ]]; then
                if [[ "$var" == "SAPTIVA_API_KEY" ]]; then
                    echo -e "  ${GREEN}$var: ${value:0:10}...${NC}"
                elif [[ "$var" == "JWT_SECRET_KEY" ]]; then
                    echo -e "  ${GREEN}$var: ***hidden***${NC}"
                else
                    echo -e "  ${GREEN}$var: $value${NC}"
                fi
            else
                echo -e "  ${RED}$var: empty${NC}"
                missing_vars+=("$var")
                if [[ "$var" == "SAPTIVA_API_KEY" ]]; then
                    demo_mode=true
                fi
            fi
        else
            echo -e "  ${RED}$var: not found${NC}"
            missing_vars+=("$var")
        fi
    done

    echo ""

    if [[ $demo_mode == true ]]; then
        echo -e "${YELLOW}Demo Mode Active: SAPTIVA_API_KEY not configured${NC}"
    fi

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        echo -e "${RED}▲  Missing variables: ${missing_vars[*]}${NC}"
        return 1
    else
        echo -e "${GREEN}All critical variables configured${NC}"
        return 0
    fi
}

switch_environment() {
    local target_env="$1"
    local target_file="$ENVS_DIR/.env.$target_env"
    local current_file=".env"

    if [[ ! -f "$target_file" ]]; then
        echo -e "${RED}Environment file not found: $target_file${NC}"
        return 1
    fi

    echo -e "${CYAN}Switching to environment: $target_env${NC}"

    # Backup current .env if exists
    if [[ -f "$current_file" ]]; then
        cp "$current_file" "${current_file}.backup.$(date +%Y%m%d_%H%M%S)"
        echo -e "${YELLOW}Current .env backed up${NC}"
    fi

    # Copy target environment
    cp "$target_file" "$current_file"
    echo -e "${GREEN}Switched to $target_env environment${NC}"

    # Restart services if they're running
    if docker ps | grep -q "copilotos-"; then
        echo -e "${YELLOW}Restarting services...${NC}"
        make restart > /dev/null 2>&1 || echo -e "${YELLOW}Could not restart services automatically${NC}"
    fi
}

validate_environment() {
    local env="$1"
    local env_file="$ENVS_DIR/.env.$env"

    echo -e "${CYAN}Validating environment: $env${NC}"
    echo ""

    if ! check_environment "$env"; then
        echo -e "${RED}Environment validation failed${NC}"
        return 1
    fi

    # Additional validation for production
    if [[ "$env" == "prod" ]]; then
        echo -e "${YELLOW}⛨ Production-specific checks:${NC}"

        # Check for demo/test values
        if grep -q "ChangeMe123" "$env_file"; then
            echo -e "${RED}Found demo passwords in production${NC}"
            return 1
        fi

        if grep -q "localhost" "$env_file"; then
            echo -e "${YELLOW}Found localhost URLs in production${NC}"
        fi

        echo -e "${GREEN}Production validation passed${NC}"
    fi

    return 0
}

list_environments() {
    echo -e "${CYAN}Available Environments:${NC}"
    echo ""

    for env in "${ENVIRONMENTS[@]}"; do
        local env_file="$ENVS_DIR/.env.$env"
        if [[ -f "$env_file" ]]; then
            local size=$(du -h "$env_file" | cut -f1)
            local modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$env_file" 2>/dev/null || stat -c "%y" "$env_file" | cut -d' ' -f1,2 | cut -d'.' -f1)
            echo -e "  ${GREEN}$env${NC} ($size, modified: $modified)"
        else
            echo -e "  ${RED}$env${NC} (file missing)"
        fi
    done
}

diff_environments() {
    local env1="$1"
    local env2="$2"
    local file1="$ENVS_DIR/.env.$env1"
    local file2="$ENVS_DIR/.env.$env2"

    echo -e "${CYAN}Comparing $env1 vs $env2:${NC}"
    echo ""

    if [[ ! -f "$file1" ]]; then
        echo -e "${RED}Environment file not found: $file1${NC}"
        return 1
    fi

    if [[ ! -f "$file2" ]]; then
        echo -e "${RED}Environment file not found: $file2${NC}"
        return 1
    fi

    diff -u "$file1" "$file2" || echo -e "${YELLOW}Environments differ${NC}"
}

# Main command dispatcher
case "${1:-help}" in
    "check")
        if [[ -z "$2" ]]; then
            echo -e "${RED}Environment name required${NC}"
            show_help
            exit 1
        fi
        check_environment "$2"
        ;;
    "switch")
        if [[ -z "$2" ]]; then
            echo -e "${RED}Environment name required${NC}"
            show_help
            exit 1
        fi
        switch_environment "$2"
        ;;
    "validate")
        if [[ -z "$2" ]]; then
            echo -e "${RED}Environment name required${NC}"
            show_help
            exit 1
        fi
        validate_environment "$2"
        ;;
    "list")
        list_environments
        ;;
    "diff")
        if [[ -z "$2" || -z "$3" ]]; then
            echo -e "${RED}Two environment names required${NC}"
            show_help
            exit 1
        fi
        diff_environments "$2" "$3"
        ;;
    "help"|*)
        show_help
        ;;
esac