#!/bin/bash
# ========================================
# MONGODB RESTORE SCRIPT
# ========================================
# Restore MongoDB database from mongodump backup
#
# Usage: ./scripts/restore-mongodb.sh <backup-file>
# Example: ./scripts/restore-mongodb.sh /home/jf/backups/mongodb/copilotos_20251009_220000.gz
#
# WARNING: This will replace all existing data in MongoDB!

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}ERROR: No backup file specified${NC}"
    echo ""
    echo "Usage: $0 <backup-file>"
    echo ""
    echo "Available backups:"
    ls -lh /home/jf/backups/mongodb/copilotos_*.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Show backup info
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
BACKUP_DATE=$(stat -f%Sm -t "%Y-%m-%d %H:%M:%S" "$BACKUP_FILE" 2>/dev/null || stat -c%y "$BACKUP_FILE" | cut -d'.' -f1)

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    MONGODB RESTORE                            ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
log_info "Backup file: $BACKUP_FILE"
log_info "Backup size: $BACKUP_SIZE"
log_info "Backup date: $BACKUP_DATE"
echo ""
log_warning "⚠️  WARNING: This will DELETE all existing data in MongoDB!"
log_warning "⚠️  Current data will be PERMANENTLY lost!"
echo ""
read -p "Are you ABSOLUTELY SURE you want to continue? Type 'YES' to proceed: " confirm

if [ "$confirm" != "YES" ]; then
    log_error "Restore cancelled by user"
    exit 1
fi

# Create safety backup of current state
log_info "Creating safety backup of current state..."
SAFETY_BACKUP="/home/jf/backups/mongodb/pre-restore-safety_$(date +%Y%m%d_%H%M%S).gz"
docker exec copilotos-prod-mongodb mongodump \
  --uri="mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin" \
  --gzip \
  --archive > "$SAFETY_BACKUP"

if [ $? -eq 0 ]; then
    SAFETY_SIZE=$(du -h "$SAFETY_BACKUP" | cut -f1)
    log_success "Safety backup created: $SAFETY_BACKUP ($SAFETY_SIZE)"
else
    log_error "Failed to create safety backup!"
    exit 1
fi

# Drop existing database
log_warning "Dropping existing database: ${MONGODB_DATABASE}..."
docker exec copilotos-prod-mongodb mongosh \
  --quiet \
  --eval "db.getSiblingDB('${MONGODB_DATABASE}').dropDatabase()" \
  "mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/admin"

if [ $? -eq 0 ]; then
    log_success "Database dropped"
else
    log_error "Failed to drop database!"
    exit 1
fi

# Restore from backup
log_info "Restoring from backup..."
cat "$BACKUP_FILE" | docker exec -i copilotos-prod-mongodb mongorestore \
  --uri="mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin" \
  --gzip \
  --archive

if [ $? -eq 0 ]; then
    log_success "Restore completed successfully"
else
    log_error "Restore failed!"
    log_error "You can restore from safety backup: $SAFETY_BACKUP"
    exit 1
fi

# Verify restore
log_info "Verifying restore..."
USER_COUNT=$(docker exec copilotos-prod-mongodb mongosh \
  --quiet \
  --eval "db.getSiblingDB('${MONGODB_DATABASE}').users.countDocuments()" \
  "mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/admin")

CHAT_COUNT=$(docker exec copilotos-prod-mongodb mongosh \
  --quiet \
  --eval "db.getSiblingDB('${MONGODB_DATABASE}').chat_sessions.countDocuments()" \
  "mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/admin")

MESSAGE_COUNT=$(docker exec copilotos-prod-mongodb mongosh \
  --quiet \
  --eval "db.getSiblingDB('${MONGODB_DATABASE}').messages.countDocuments()" \
  "mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/admin")

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                   RESTORE COMPLETED                           ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
log_success "Users restored: ${USER_COUNT}"
log_success "Chat sessions restored: ${CHAT_COUNT}"
log_success "Messages restored: ${MESSAGE_COUNT}"
echo ""
log_info "Safety backup kept at: $SAFETY_BACKUP"
log_info "You can delete it manually if restore is successful"
echo ""
