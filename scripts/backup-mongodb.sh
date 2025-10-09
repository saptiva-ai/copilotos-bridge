#!/bin/bash
# ========================================
# MONGODB BACKUP SCRIPT
# ========================================
# Automated backup of MongoDB database using mongodump
#
# Usage: ./scripts/backup-mongodb.sh
#
# Features:
# - Creates compressed backups using mongodump
# - Maintains backup history with timestamps
# - Automatic cleanup of old backups (30 days retention)
# - Logging of all backup operations
#
# Requirements:
# - Docker and docker-compose installed
# - MongoDB container running
# - Credentials in envs/.env.prod

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="/home/jf/backups/mongodb"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Load production environment
if [ -f "$PROJECT_ROOT/envs/.env.prod" ]; then
    source "$PROJECT_ROOT/envs/.env.prod"
else
    echo -e "${RED}ERROR: envs/.env.prod not found${NC}"
    exit 1
fi

# Functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> ${BACKUP_DIR}/backup.log
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [SUCCESS] $1" >> ${BACKUP_DIR}/backup.log
}

log_error() {
    echo -e "${RED}✗${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> ${BACKUP_DIR}/backup.log
}

# Create backup directory if it doesn't exist
mkdir -p ${BACKUP_DIR}

log_info "Starting MongoDB backup: copilotos_${DATE}"

# Create backup using mongodump
log_info "Running mongodump..."
docker exec copilotos-prod-mongodb mongodump \
  --uri="mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin" \
  --gzip \
  --archive > ${BACKUP_DIR}/copilotos_${DATE}.gz

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h ${BACKUP_DIR}/copilotos_${DATE}.gz | cut -f1)
    log_success "Backup completed: copilotos_${DATE}.gz (${BACKUP_SIZE})"
else
    log_error "Backup failed!"
    exit 1
fi

# Verify backup is not empty
BACKUP_SIZE_BYTES=$(stat -f%z ${BACKUP_DIR}/copilotos_${DATE}.gz 2>/dev/null || stat -c%s ${BACKUP_DIR}/copilotos_${DATE}.gz)
if [ ${BACKUP_SIZE_BYTES} -lt 1000 ]; then
    log_error "Backup file is suspiciously small (${BACKUP_SIZE_BYTES} bytes). Possible corruption!"
    exit 1
fi

# Clean up old backups
log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."
find ${BACKUP_DIR} -name "copilotos_*.gz" -mtime +${RETENTION_DAYS} -delete
log_success "Cleanup completed"

# List recent backups
log_info "Recent backups:"
ls -lh ${BACKUP_DIR}/copilotos_*.gz 2>/dev/null | tail -5 || echo "No backups found"

log_success "Backup process completed successfully"
