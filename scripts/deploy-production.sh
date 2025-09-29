#!/bin/bash

# ============================================================================
# Production Deployment Script with Zero-Downtime
# ============================================================================

set -euo pipefail

# Emojis for logs
RED='🔴'
GREEN='🟢'
YELLOW='🟡'
BLUE='🔵'
NC='' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_PATH="${DEPLOY_PATH:-/home/jf/copilotos-bridge}"
BACKUP_DIR="${BACKUP_DIR:-/home/jf/backups/copilotos-production}"
COMPOSE_FILE="docker-compose.prod.yml"
HEALTH_CHECK_TIMEOUT=300
BACKUP_RETENTION_DAYS=30

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking deployment prerequisites..."

    # Check if running as deployment user
    if [[ $EUID -eq 0 ]]; then
        log_error "Do not run production deployments as root!"
        exit 1
    fi

    # Check required environment variables
    local required_vars=(
        "MONGODB_USER"
        "MONGODB_PASSWORD"
        "REDIS_PASSWORD"
        "JWT_SECRET_KEY"
        "SECRET_KEY"
        "DOMAIN"
    )

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done

    # Check Docker access
    if ! docker info > /dev/null 2>&1; then
        log_error "Cannot access Docker. Check permissions."
        exit 1
    fi

    # Check disk space (minimum 5GB)
    local available_space=$(df "$DEPLOY_PATH" | awk 'NR==2{print $4}')
    if [[ $available_space -lt 5242880 ]]; then # 5GB in KB
        log_error "Insufficient disk space. Need at least 5GB available."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Load environment variables
load_env() {
    local env_file="$PROJECT_ROOT/.env.production"
    if [[ -f "$env_file" ]]; then
        log_info "Loading production environment from $env_file"
        set -a
        source "$env_file"
        set +a
    else
        log_error "Production environment file not found: $env_file"
        exit 1
    fi
}

# Create comprehensive backup
create_backup() {
    log_info "Creating production backup..."

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="production_backup_$timestamp"
    local full_backup_path="$BACKUP_DIR/$backup_name"

    mkdir -p "$full_backup_path"

    # Backup MongoDB
    if docker-compose -f "$COMPOSE_FILE" ps -q mongodb | grep -q .; then
        log_info "Backing up MongoDB..."
        docker exec copilotos-mongodb-prod mongodump \
            --username "$MONGODB_USER" \
            --password "$MONGODB_PASSWORD" \
            --authenticationDatabase admin \
            --out /tmp/dump

        mkdir -p "$full_backup_path/mongodb"
        docker cp copilotos-mongodb-prod:/tmp/dump "$full_backup_path/mongodb/"

        # Verify backup integrity
        if [[ -d "$full_backup_path/mongodb/dump" ]]; then
            log_success "MongoDB backup completed"
        else
            log_error "MongoDB backup failed"
            return 1
        fi
    fi

    # Backup Redis
    if docker-compose -f "$COMPOSE_FILE" ps -q redis | grep -q .; then
        log_info "Backing up Redis..."
        docker exec copilotos-redis-prod redis-cli \
            --rdb /tmp/dump.rdb \
            --a "$REDIS_PASSWORD"

        mkdir -p "$full_backup_path/redis"
        docker cp copilotos-redis-prod:/tmp/dump.rdb "$full_backup_path/redis/"

        if [[ -f "$full_backup_path/redis/dump.rdb" ]]; then
            log_success "Redis backup completed"
        else
            log_error "Redis backup failed"
            return 1
        fi
    fi

    # Backup current compose file and env
    cp "$COMPOSE_FILE" "$full_backup_path/"
    cp ".env.production" "$full_backup_path/" 2>/dev/null || true

    # Create backup metadata
    cat > "$full_backup_path/metadata.json" << EOF
{
    "timestamp": "$timestamp",
    "date": "$(date -Iseconds)",
    "version": "${APP_VERSION:-unknown}",
    "api_image": "${API_IMAGE:-unknown}",
    "web_image": "${WEB_IMAGE:-unknown}",
    "hostname": "$(hostname)",
    "user": "$(whoami)"
}
EOF

    log_success "Backup created: $full_backup_path"
    echo "$full_backup_path" > "$BACKUP_DIR/latest_backup"

    # Cleanup old backups
    cleanup_old_backups
}

# Cleanup old backups
cleanup_old_backups() {
    log_info "Cleaning up old backups (retention: $BACKUP_RETENTION_DAYS days)..."
    find "$BACKUP_DIR" -type d -name "production_backup_*" -mtime +$BACKUP_RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
}

# Comprehensive health check
health_check() {
    local service="$1"
    local url="$2"
    local max_attempts=30
    local attempt=1

    log_info "Health checking $service at $url..."

    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s --max-time 10 "$url" > /dev/null; then
            log_success "$service is healthy"
            return 0
        fi

        if [[ $attempt -eq $max_attempts ]]; then
            log_error "$service health check failed after $max_attempts attempts"
            return 1
        fi

        log_info "Attempt $attempt/$max_attempts failed, waiting 10s..."
        sleep 10
        ((attempt++))
    done
}

# Pull and verify images
pull_images() {
    log_info "Pulling latest production images..."

    if [[ -n "${TOKEN:-}" ]]; then
        echo "$TOKEN" | docker login ghcr.io -u "${GITHUB_USER:-$USER}" --password-stdin
        log_success "Logged in to container registry"
    fi

    # Pull images with verification
    local api_image="${API_IMAGE:-ghcr.io/jazielflo/copilotos-bridge/api:latest}"
    local web_image="${WEB_IMAGE:-ghcr.io/jazielflo/copilotos-bridge/web:latest}"

    log_info "Pulling API image: $api_image"
    docker pull "$api_image"

    log_info "Pulling Web image: $web_image"
    docker pull "$web_image"

    # Verify images
    docker inspect "$api_image" > /dev/null
    docker inspect "$web_image" > /dev/null

    log_success "Images pulled and verified successfully"
}

# Zero-downtime deployment
deploy() {
    log_info "Starting zero-downtime production deployment..."

    # Ensure data directories exist
    mkdir -p /opt/copilotos-bridge/data/{mongodb,redis}

    # Step 1: Start new instances with different names
    log_info "Starting new service instances..."

    # Export current images for new deployment
    export API_IMAGE="${API_IMAGE:-ghcr.io/jazielflo/copilotos-bridge/api:latest}"
    export WEB_IMAGE="${WEB_IMAGE:-ghcr.io/jazielflo/copilotos-bridge/web:latest}"

    # Create temporary compose for new instances
    sed 's/-prod/-prod-new/g' "$COMPOSE_FILE" > docker-compose.prod-new.yml
    sed -i 's/:8001/:8002/g' docker-compose.prod-new.yml
    sed -i 's/:3000/:3001/g' docker-compose.prod-new.yml

    # Start new instances
    docker-compose -f docker-compose.prod-new.yml up -d

    # Wait for new services to be ready
    sleep 60

    # Health check new instances
    if ! health_check "New API" "http://localhost:8002/api/health"; then
        log_error "New API instance failed health check"
        docker-compose -f docker-compose.prod-new.yml down
        return 1
    fi

    if ! health_check "New Web" "http://localhost:3001"; then
        log_error "New Web instance failed health check"
        docker-compose -f docker-compose.prod-new.yml down
        return 1
    fi

    log_success "New instances are healthy"

    # Step 2: Switch traffic (if using load balancer)
    log_info "Switching traffic to new instances..."

    # Stop old instances
    docker-compose -f "$COMPOSE_FILE" down

    # Rename new instances to production names
    docker rename copilotos-api-prod-new copilotos-api-prod
    docker rename copilotos-web-prod-new copilotos-web-prod

    # Update port mappings back to original
    docker stop copilotos-api-prod copilotos-web-prod

    # Remove temporary compose file
    rm -f docker-compose.prod-new.yml

    # Start final production deployment
    docker-compose -f "$COMPOSE_FILE" up -d

    # Final health checks
    sleep 30
    health_check "Production API" "http://localhost:8001/api/health"
    health_check "Production Web" "http://localhost:3000"

    log_success "Zero-downtime deployment completed successfully!"
}

# Standard deployment (with brief downtime)
deploy_standard() {
    log_info "Starting standard production deployment..."

    # Stop services
    docker-compose -f "$COMPOSE_FILE" down

    # Start services
    docker-compose -f "$COMPOSE_FILE" up -d

    # Wait for services
    sleep 60

    # Health checks
    health_check "API" "http://localhost:8001/api/health"
    health_check "Web" "http://localhost:3000"

    log_success "Standard deployment completed successfully!"
}

# Rollback function
rollback() {
    log_warning "Initiating production rollback..."

    local latest_backup_file="$BACKUP_DIR/latest_backup"

    if [[ ! -f "$latest_backup_file" ]]; then
        log_error "No backup reference found"
        return 1
    fi

    local latest_backup=$(cat "$latest_backup_file")

    if [[ ! -d "$latest_backup" ]]; then
        log_error "Backup directory not found: $latest_backup"
        return 1
    fi

    log_info "Rolling back to: $latest_backup"

    # Stop current deployment
    docker-compose -f "$COMPOSE_FILE" down

    # Restore MongoDB
    if [[ -d "$latest_backup/mongodb/dump" ]]; then
        log_info "Restoring MongoDB..."
        docker-compose -f "$COMPOSE_FILE" up -d mongodb
        sleep 20

        docker cp "$latest_backup/mongodb/dump" copilotos-mongodb-prod:/tmp/restore
        docker exec copilotos-mongodb-prod mongorestore \
            --username "$MONGODB_USER" \
            --password "$MONGODB_PASSWORD" \
            --authenticationDatabase admin \
            --drop /tmp/restore
    fi

    # Restore Redis
    if [[ -f "$latest_backup/redis/dump.rdb" ]]; then
        log_info "Restoring Redis..."
        docker-compose -f "$COMPOSE_FILE" up -d redis
        sleep 10

        docker cp "$latest_backup/redis/dump.rdb" copilotos-redis-prod:/data/dump.rdb
        docker restart copilotos-redis-prod
    fi

    # Start all services
    docker-compose -f "$COMPOSE_FILE" up -d

    # Health checks
    sleep 30
    health_check "API" "http://localhost:8001/api/health"
    health_check "Web" "http://localhost:3000"

    log_success "Rollback completed successfully"
}

# Monitor deployment
monitor() {
    log_info "Monitoring production services..."

    while true; do
        if health_check "API" "http://localhost:8001/api/health" && \
           health_check "Web" "http://localhost:3000"; then
            log_success "All services healthy at $(date)"
        else
            log_error "Health check failed at $(date)"
        fi
        sleep 60
    done
}

# Main function
main() {
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            load_env
            create_backup
            pull_images
            deploy_standard
            ;;
        "deploy-zero-downtime")
            check_prerequisites
            load_env
            create_backup
            pull_images
            deploy
            ;;
        "rollback")
            check_prerequisites
            load_env
            rollback
            ;;
        "backup")
            load_env
            create_backup
            ;;
        "health")
            health_check "API" "http://localhost:8001/api/health"
            health_check "Web" "http://localhost:3000"
            ;;
        "monitor")
            monitor
            ;;
        *)
            echo "Usage: $0 {deploy|deploy-zero-downtime|rollback|backup|health|monitor}"
            echo ""
            echo "Commands:"
            echo "  deploy                - Standard deployment with brief downtime"
            echo "  deploy-zero-downtime  - Zero-downtime deployment (experimental)"
            echo "  rollback              - Rollback to latest backup"
            echo "  backup                - Create backup only"
            echo "  health                - Check service health"
            echo "  monitor               - Continuous health monitoring"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"