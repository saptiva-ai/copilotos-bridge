#!/bin/bash

# ============================================================================
# Staging Deployment Script
# ============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_PATH="${DEPLOY_PATH:-/home/jf/copilotos-bridge}"
BACKUP_DIR="${BACKUP_DIR:-/home/jf/backups/copilotos-staging}"
COMPOSE_FILE="docker-compose.staging.yml"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root or with sudo
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. Consider using a dedicated deployment user."
    fi
}

# Load environment variables
load_env() {
    local env_file="$PROJECT_ROOT/.env.staging"
    if [[ -f "$env_file" ]]; then
        log_info "Loading environment from $env_file"
        set -a
        source "$env_file"
        set +a
    else
        log_warning "No .env.staging file found. Using defaults."
    fi
}

# Create backup
create_backup() {
    log_info "Creating backup..."

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="staging_backup_$timestamp"

    mkdir -p "$BACKUP_DIR"

    # Backup volumes
    if docker-compose -f "$COMPOSE_FILE" ps -q mongodb | grep -q .; then
        log_info "Backing up MongoDB..."
        docker exec copilotos-mongodb-staging mongodump --out /tmp/dump
        docker cp copilotos-mongodb-staging:/tmp/dump "$BACKUP_DIR/$backup_name/mongodb"
    fi

    if docker-compose -f "$COMPOSE_FILE" ps -q redis | grep -q .; then
        log_info "Backing up Redis..."
        docker exec copilotos-redis-staging redis-cli --rdb /tmp/dump.rdb
        docker cp copilotos-redis-staging:/tmp/dump.rdb "$BACKUP_DIR/$backup_name/redis/"
    fi

    log_success "Backup created: $BACKUP_DIR/$backup_name"
}

# Health check
health_check() {
    local service="$1"
    local url="$2"
    local max_attempts=30
    local attempt=1

    log_info "Health checking $service..."

    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$url" > /dev/null; then
            log_success "$service is healthy"
            return 0
        fi

        log_info "Attempt $attempt/$max_attempts failed, waiting..."
        sleep 10
        ((attempt++))
    done

    log_error "$service health check failed after $max_attempts attempts"
    return 1
}

# Pull latest images
pull_images() {
    log_info "Pulling latest images..."

    if [[ -n "${TOKEN:-}" ]]; then
        echo "$TOKEN" | docker login ghcr.io -u "${GITHUB_USER:-$USER}" --password-stdin
    fi

    docker-compose -f "$COMPOSE_FILE" pull
    log_success "Images pulled successfully"
}

# Deploy services
deploy() {
    log_info "Deploying to staging..."

    # Stop existing services
    docker-compose -f "$COMPOSE_FILE" down

    # Start services
    docker-compose -f "$COMPOSE_FILE" up -d

    # Wait for services to be ready
    sleep 30

    # Health checks
    health_check "API" "http://localhost:8001/api/health"
    health_check "Web" "http://localhost:3000"

    log_success "Staging deployment completed successfully!"
}

# Rollback function
rollback() {
    log_warning "Rolling back staging deployment..."

    # Stop current deployment
    docker-compose -f "$COMPOSE_FILE" down

    # Find latest backup
    local latest_backup=$(ls -t "$BACKUP_DIR" | head -n1)

    if [[ -n "$latest_backup" ]]; then
        log_info "Restoring from backup: $latest_backup"

        # Restore MongoDB
        if [[ -d "$BACKUP_DIR/$latest_backup/mongodb" ]]; then
            docker-compose -f "$COMPOSE_FILE" up -d mongodb
            sleep 10
            docker exec copilotos-mongodb-staging mongorestore /tmp/restore
        fi

        # Restore Redis
        if [[ -f "$BACKUP_DIR/$latest_backup/redis/dump.rdb" ]]; then
            docker-compose -f "$COMPOSE_FILE" up -d redis
            sleep 10
            docker cp "$BACKUP_DIR/$latest_backup/redis/dump.rdb" copilotos-redis-staging:/data/dump.rdb
            docker restart copilotos-redis-staging
        fi

        log_success "Rollback completed"
    else
        log_error "No backup found for rollback"
        return 1
    fi
}

# Cleanup old images and containers
cleanup() {
    log_info "Cleaning up old Docker resources..."
    docker system prune -f
    docker volume prune -f
    log_success "Cleanup completed"
}

# Main deployment flow
main() {
    log_info "Starting staging deployment..."

    check_permissions
    load_env

    case "${1:-deploy}" in
        "deploy")
            create_backup
            pull_images
            deploy
            cleanup
            ;;
        "rollback")
            rollback
            ;;
        "backup")
            create_backup
            ;;
        "health")
            health_check "API" "http://localhost:8001/api/health"
            health_check "Web" "http://localhost:3000"
            ;;
        *)
            echo "Usage: $0 {deploy|rollback|backup|health}"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"