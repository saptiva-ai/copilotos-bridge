#!/bin/bash
# Don't use set -e to allow graceful error handling
set +e

# ========================================
# Production Readiness Validation Script
# ========================================
# Valida que el sistema esté configurado correctamente
# para rotación de credenciales sin pérdida de datos
# ========================================

# Status symbols
RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "
NC=""

# Validation state
CHECKS_PASSED=0
CHECKS_FAILED=0
WARNINGS=0

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ  $1${NC}"
}

log_success() {
    echo -e "${GREEN}$1${NC}"
    ((CHECKS_PASSED++))
}

log_error() {
    echo -e "${RED}$1${NC}"
    ((CHECKS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}$1${NC}"
    ((WARNINGS++))
}

section_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ========================================
# VALIDATION CHECKS
# ========================================

check_docker_compose_config() {
    section_header "1. Docker Compose Configuration"

    COMPOSE_FILE="infra/docker-compose.yml"

    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "docker-compose.yml not found at $COMPOSE_FILE"
        return 1
    fi

    log_success "docker-compose.yml found"

    # Check env_file for critical services
    local services=("mongodb" "redis" "api")

    for service in "${services[@]}"; do
        if grep -A 10 "^  $service:" "$COMPOSE_FILE" | grep -q "env_file:"; then
            log_success "Service '$service' has env_file configured"
        else
            log_error "Service '$service' is MISSING env_file directive"
            echo -e "${YELLOW}→ This will cause credential sync issues!${NC}"
        fi
    done
}

check_env_file_exists() {
    section_header "2. Environment File Validation"

    ENV_FILE="envs/.env"

    if [ ! -f "$ENV_FILE" ]; then
        log_error ".env file not found at $ENV_FILE"
        return 1
    fi

    log_success ".env file exists"

    # Check critical variables
    local required_vars=(
        "MONGODB_USER"
        "MONGODB_PASSWORD"
        "MONGODB_DATABASE"
        "REDIS_PASSWORD"
        "JWT_SECRET_KEY"
    )

    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" "$ENV_FILE"; then
            log_success "Variable $var is defined"

            # Check if using default/weak passwords
            local value=$(grep "^${var}=" "$ENV_FILE" | cut -d= -f2)

            if [[ "$value" == *"change_me"* ]] || [[ "$value" == *"password"* ]] || [[ "$value" == "dev-"* ]]; then
                log_warning "Variable $var appears to be using a default/weak value"
                echo -e "${YELLOW}→ Value: $value${NC}"
            fi
        else
            log_error "Variable $var is NOT defined in .env"
        fi
    done
}

check_rotation_scripts() {
    section_header "3. Rotation Scripts Validation"

    local scripts=(
        "scripts/rotate-mongo-credentials.sh"
        "scripts/rotate-redis-credentials.sh"
    )

    for script in "${scripts[@]}"; do
        if [ ! -f "$script" ]; then
            log_error "Script not found: $script"
            continue
        fi

        log_success "Script exists: $script"

        if [ ! -x "$script" ]; then
            log_warning "Script is not executable: $script"
            echo -e "${YELLOW}→ Run: chmod +x $script${NC}"
        else
            log_success "Script is executable: $script"
        fi

        # Check that scripts don't use 'restart' command (but ignore warnings about it)
        if grep "docker compose restart" "$script" 2>/dev/null | grep -v "NO restart" | grep -v "NOTA:" | grep -q "restart"; then
            log_error "Script uses 'docker compose restart' which doesn't reload env vars!"
            echo -e "${YELLOW}→ File: $script${NC}"
            echo -e "${YELLOW}→ Should use 'down' + 'up' instead${NC}"
        else
            log_success "Script doesn't use problematic 'restart' command"
        fi
    done
}

check_documentation() {
    section_header "4. Documentation Validation"

    local docs=(
        "docs/PRODUCTION_CREDENTIAL_ROTATION.md"
        "docs/CREDENTIAL_MANAGEMENT.md"
        "docs/DOCKER_ENV_FILE_CONFIGURATION.md"
    )

    for doc in "${docs[@]}"; do
        if [ -f "$doc" ]; then
            log_success "Documentation exists: $doc"
        else
            log_warning "Documentation missing: $doc"
        fi
    done
}

check_services_running() {
    section_header "5. Services Status"

    local services=("mongodb" "redis" "api")
    local project_name="${COMPOSE_PROJECT_NAME:-copilotos}"

    for service in "${services[@]}"; do
        local container_name="${project_name}-${service}"

        if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
            log_success "Container running: $container_name"
        else
            log_warning "Container NOT running: $container_name"
            echo -e "${YELLOW}→ Run: make dev${NC}"
        fi
    done
}

check_services_health() {
    section_header "6. Services Health Checks"

    # Check API health
    if curl -sf http://localhost:8001/api/health > /dev/null 2>&1; then
        log_success "API health check passed"
    else
        log_warning "API health check failed (may not be running)"
    fi

    # Check MongoDB
    if docker ps --format '{{.Names}}' | grep -q "copilotos-mongodb"; then
        if docker exec copilotos-mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
            log_success "MongoDB is responding"
        else
            log_warning "MongoDB is not responding"
        fi
    fi

    # Check Redis
    if docker ps --format '{{.Names}}' | grep -q "copilotos-redis"; then
        if docker exec copilotos-redis redis-cli ping > /dev/null 2>&1; then
            log_success "Redis is responding"
        else
            log_warning "Redis is not responding"
        fi
    fi
}

check_credential_sync() {
    section_header "7. Credential Synchronization"

    if [ ! -f "envs/.env" ]; then
        log_error "Cannot check credential sync: .env file not found"
        return 1
    fi

    # Check MongoDB credentials
    if docker ps --format '{{.Names}}' | grep -q "copilotos-mongodb"; then
        local env_mongo_pass=$(grep "^MONGODB_PASSWORD=" envs/.env | cut -d= -f2)
        local container_mongo_pass=$(docker inspect copilotos-mongodb --format='{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep "MONGO_INITDB_ROOT_PASSWORD=" | cut -d= -f2)

        if [ -n "$env_mongo_pass" ] && [ -n "$container_mongo_pass" ]; then
            if [ "$env_mongo_pass" == "$container_mongo_pass" ]; then
                log_success "MongoDB password is synchronized between .env and container"
            else
                log_error "MongoDB password MISMATCH between .env and container!"
                echo -e "${YELLOW}→ .env: ${env_mongo_pass:0:10}...${NC}"
                echo -e "${YELLOW}→ Container: ${container_mongo_pass:0:10}...${NC}"
                echo -e "${YELLOW}→ Solution: docker compose down mongodb && docker compose up -d mongodb${NC}"
            fi
        else
            log_warning "Could not verify MongoDB password sync"
        fi
    fi

    # Check Redis credentials
    if docker ps --format '{{.Names}}' | grep -q "copilotos-redis"; then
        local env_redis_pass=$(grep "^REDIS_PASSWORD=" envs/.env | cut -d= -f2)

        if [ -n "$env_redis_pass" ]; then
            if docker exec copilotos-redis redis-cli -a "$env_redis_pass" PING 2>/dev/null | grep -q "PONG"; then
                log_success "Redis password is synchronized between .env and container"
            else
                log_error "Redis password MISMATCH between .env and container!"
                echo -e "${YELLOW}→ Solution: docker compose down redis && docker compose up -d redis${NC}"
            fi
        else
            log_warning "Could not verify Redis password sync"
        fi
    fi
}

check_backup_capability() {
    section_header "8. Backup & Recovery Capability"

    # Check if backups directory exists
    if [ -d "backups" ]; then
        log_success "Backup directory exists"

        # Check for recent backups
        local recent_backups=$(find backups -name "mongodb-*.archive" -mtime -7 2>/dev/null | wc -l)

        if [ "$recent_backups" -gt 0 ]; then
            log_success "Found $recent_backups backup(s) from last 7 days"
        else
            log_warning "No backups found from last 7 days"
            echo -e "${YELLOW}→ Consider running: make backup-mongodb${NC}"
        fi
    else
        log_warning "Backup directory does not exist"
        echo -e "${YELLOW}→ Will be created automatically on first backup${NC}"
    fi

    # Check if mongodump is available in MongoDB container
    if docker ps --format '{{.Names}}' | grep -q "copilotos-mongodb"; then
        if docker exec copilotos-mongodb which mongodump > /dev/null 2>&1; then
            log_success "mongodump tool is available for backups"
        else
            log_error "mongodump tool is NOT available"
        fi
    fi
}

check_makefile_commands() {
    section_header "9. Makefile Commands"

    if [ ! -f "Makefile" ]; then
        log_error "Makefile not found"
        return 1
    fi

    local required_commands=(
        "generate-credentials"
        "rotate-mongo-password"
        "rotate-redis-password"
        "backup-mongodb"
        "reset"
    )

    for cmd in "${required_commands[@]}"; do
        if grep -q "^${cmd}:" Makefile; then
            log_success "Makefile command exists: make $cmd"
        else
            log_warning "Makefile command missing: make $cmd"
        fi
    done
}

check_production_guards() {
    section_header "10. Production Safety Guards"

    # Check if make reset has warnings
    if grep -q "make reset" Makefile; then
        if grep -A 5 "^reset:" Makefile | grep -q "DELETES ALL DATA"; then
            log_success "make reset has clear warnings about data deletion"
        else
            log_warning "make reset should have explicit warnings"
        fi
    fi

    # Check if using restart command anywhere dangerous
    local dangerous_files=(
        "scripts/rotate-mongo-credentials.sh"
        "scripts/rotate-redis-credentials.sh"
        "Makefile"
    )

    local found_restart=false
    for file in "${dangerous_files[@]}"; do
        if [ -f "$file" ]; then
            # Check for restart but ignore warnings about it
            if grep "docker compose restart" "$file" 2>/dev/null | grep -v "NO restart" | grep -v "NOTA:" | grep -v "IMPORTANTE:" | grep -q "restart"; then
                log_warning "File uses 'docker compose restart': $file"
                echo -e "${YELLOW}→ This won't reload env vars, use 'down' + 'up' instead${NC}"
                found_restart=true
            fi
        fi
    done

    if [ "$found_restart" = false ]; then
        log_success "No dangerous 'restart' commands found in rotation scripts"
    fi
}

# ========================================
# MAIN EXECUTION
# ========================================

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Production Readiness Validation${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""

# Run all checks
check_docker_compose_config
check_env_file_exists
check_rotation_scripts
check_documentation
check_services_running
check_services_health
check_credential_sync
check_backup_capability
check_makefile_commands
check_production_guards

# Summary
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Validation Summary${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Checks Passed: $CHECKS_PASSED${NC}"
echo -e "${RED}Checks Failed: $CHECKS_FAILED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}System is READY for production credential rotation!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""

    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}Note: There are $WARNINGS warning(s) that should be reviewed.${NC}"
        echo ""
    fi

    echo "Next steps:"
    echo "  1. Review production guide: docs/PRODUCTION_CREDENTIAL_ROTATION.md"
    echo "  2. Create backup: make backup-mongodb"
    echo "  3. Test rotation in staging first"
    echo "  4. Schedule maintenance window"
    echo ""
    exit 0
else
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}System is NOT ready for production!${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Please fix the failed checks above before proceeding."
    echo ""
    exit 1
fi
