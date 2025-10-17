#!/bin/bash
set -e

# ========================================
# Credential Rotation Testing Script
# ========================================
# Tests the complete credential management workflow
# to ensure data persistence and backup functionality
#
# LESSONS LEARNED VALIDATED BY THIS SCRIPT:
# -----------------------------------------
# 1. docker compose restart DOES NOT reload environment variables
#    - This script uses 'down' + 'up' pattern (lines 320-324, 377-381)
#    - Using 'restart' would cause authentication failures
#    - See README.md "Lessons Learned" section for details
#
# 2. Credential rotation preserves data without volume deletion
#    - MongoDB rotation uses db.changeUserPassword() (not volume drop)
#    - Redis rotation uses CONFIG SET requirepass (not volume drop)
#    - Tests validate user count unchanged through rotations
#
# 3. Backups are functional and preserve data correctly
#    - Pre/post-rotation backups created
#    - Restore tested to verify backup integrity
#    - Data count validation after restore
#
# 4. Health checks are essential after configuration changes
#    - wait_for_api() ensures services ready before testing
#    - Prevents false negatives from timing issues
#    - Used after every container recreation
#
# 5. env_file directive in docker-compose.yml is critical
#    - Containers load credentials from .env automatically
#    - Without it, credential sync fails silently
#    - See docs/DOCKER_ENV_FILE_CONFIGURATION.md
# ========================================

# Status symbols
RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "
NC=""

# Test state
TESTS_PASSED=0
TESTS_FAILED=0
TEST_USER="test_rotation_$(date +%s)"  # Unique user per test run
TEST_PASSWORD="TestRotation123!"
TEST_EMAIL="test_rotation_$(date +%s)@example.com"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ  $1${NC}"
}

log_success() {
    echo -e "${GREEN}$1${NC}"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}$1${NC}"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}$1${NC}"
}

wait_for_api() {
    log_info "Waiting for API to be ready..."
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -sf http://localhost:8001/api/health > /dev/null 2>&1; then
            log_success "API is ready"
            return 0
        fi
        ((attempt++))
        sleep 2
    done

    log_error "API did not become ready in time"
    return 1
}

create_test_user() {
    log_info "Creating test user: $TEST_USER"

    RESPONSE=$(curl -s -X POST http://localhost:8001/api/auth/register \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$TEST_USER\",\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}" \
        2>/dev/null)

    if echo "$RESPONSE" | grep -q "access_token"; then
        log_success "Test user created successfully"
        return 0
    else
        log_error "Failed to create test user: $RESPONSE"
        return 1
    fi
}

test_user_login() {
    log_info "Testing user login: $TEST_USER"

    RESPONSE=$(curl -s -X POST http://localhost:8001/api/auth/login \
        -H "Content-Type: application/json" \
        -d "{\"identifier\":\"$TEST_USER\",\"password\":\"$TEST_PASSWORD\"}" \
        2>/dev/null)

    if echo "$RESPONSE" | grep -q "access_token"; then
        log_success "User login successful"
        return 0
    else
        log_error "User login failed: $RESPONSE"
        return 1
    fi
}

count_users() {
    MONGO_PASS=$(grep MONGODB_PASSWORD envs/.env | cut -d= -f2)
    USER_COUNT=$(docker exec copilotos-mongodb mongosh admin \
        -u copilotos_prod_user \
        -p "$MONGO_PASS" \
        --quiet \
        --eval "db.getSiblingDB('copilotos').users.countDocuments({})" 2>/dev/null | tail -1)

    echo "$USER_COUNT"
}

verify_user_exists() {
    log_info "Verifying test user exists in database..."

    MONGO_PASS=$(grep MONGODB_PASSWORD envs/.env | cut -d= -f2)
    USER_COUNT=$(docker exec copilotos-mongodb mongosh admin \
        -u copilotos_prod_user \
        -p "$MONGO_PASS" \
        --quiet \
        --eval "db.getSiblingDB('copilotos').users.countDocuments({username: '$TEST_USER'})" 2>/dev/null | tail -1)

    if [ "$USER_COUNT" -gt 0 ]; then
        log_success "User exists in database"
        return 0
    else
        log_error "User NOT found in database"
        return 1
    fi
}

create_test_conversation() {
    log_info "Creating test conversation..."

    # First login to get token
    TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
        -H "Content-Type: application/json" \
        -d "{\"identifier\":\"$TEST_USER\",\"password\":\"$TEST_PASSWORD\"}" \
        2>/dev/null | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

    if [ -z "$TOKEN" ]; then
        log_error "Failed to get auth token"
        return 1
    fi

    # Create conversation
    RESPONSE=$(curl -s -X POST http://localhost:8001/api/conversations \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d '{"title":"Test Conversation","model":"SAPTIVA_CORTEX"}' \
        2>/dev/null)

    if echo "$RESPONSE" | grep -q "id"; then
        CONVERSATION_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
        log_success "Conversation created: $CONVERSATION_ID"
        echo "$CONVERSATION_ID"
        return 0
    else
        log_error "Failed to create conversation: $RESPONSE"
        return 1
    fi
}

count_conversations() {
    MONGO_PASS=$(grep MONGODB_PASSWORD envs/.env | cut -d= -f2)
    CONV_COUNT=$(docker exec copilotos-mongodb mongosh admin \
        -u copilotos_prod_user \
        -p "$MONGO_PASS" \
        --quiet \
        --eval "db.getSiblingDB('copilotos').conversations.countDocuments({})" 2>/dev/null | tail -1)

    echo "$CONV_COUNT"
}

check_services_health() {
    log_info "Checking services health..."

    local all_healthy=true

    # Check API
    if curl -sf http://localhost:8001/api/health > /dev/null 2>&1; then
        log_success "API is healthy"
    else
        log_error "API is NOT healthy"
        all_healthy=false
    fi

    # Check MongoDB
    if docker exec copilotos-mongodb mongosh --eval "db.runCommand('ping')" > /dev/null 2>&1; then
        log_success "MongoDB is healthy"
    else
        log_error "MongoDB is NOT healthy"
        all_healthy=false
    fi

    # Check Redis
    if docker exec copilotos-redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis is healthy"
    else
        log_error "Redis is NOT healthy"
        all_healthy=false
    fi

    $all_healthy && return 0 || return 1
}

test_backup_creation() {
    log_info "Testing backup creation..."

    # Create backup directory
    mkdir -p /tmp/copilotos-test-backups

    # Create backup using mongodump
    BACKUP_FILE="/tmp/copilotos-test-backups/test-backup-$(date +%Y%m%d-%H%M%S).archive"

    docker exec copilotos-mongodb mongodump \
        --uri="mongodb://copilotos_prod_user:$(grep MONGODB_PASSWORD envs/.env | cut -d= -f2)@localhost:27017/copilotos?authSource=admin" \
        --archive=/tmp/backup.archive > /dev/null 2>&1

    docker cp copilotos-mongodb:/tmp/backup.archive "$BACKUP_FILE"

    if [ -f "$BACKUP_FILE" ]; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log_success "Backup created: $BACKUP_FILE ($BACKUP_SIZE)"
        echo "$BACKUP_FILE"
        return 0
    else
        log_error "Backup file not created"
        return 1
    fi
}

test_backup_restore() {
    local backup_file="$1"
    log_info "Testing backup restore from: $backup_file"

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi

    # Copy backup to container
    docker cp "$backup_file" copilotos-mongodb:/tmp/restore.archive

    # Restore
    docker exec copilotos-mongodb mongorestore \
        --uri="mongodb://copilotos_prod_user:$(grep MONGODB_PASSWORD envs/.env | cut -d= -f2)@localhost:27017/copilotos?authSource=admin" \
        --archive=/tmp/restore.archive \
        --drop > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        log_success "Backup restored successfully"
        return 0
    else
        log_error "Backup restore failed"
        return 1
    fi
}

# ========================================
# MAIN TEST SUITE
# ========================================

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Credential Rotation & Data Persistence Test Suite${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 1: Initial setup
echo -e "${YELLOW}═══ Test 1: Initial Environment Check ═══${NC}"
check_services_health || exit 1
echo ""

# Test 2: Create test data
echo -e "${YELLOW}═══ Test 2: Create Test Data ═══${NC}"
INITIAL_USER_COUNT=$(count_users)
log_info "Initial user count: $INITIAL_USER_COUNT"

create_test_user || exit 1
test_user_login || exit 1
verify_user_exists || exit 1

AFTER_USER_COUNT=$(count_users)
log_info "User count after creation: $AFTER_USER_COUNT"

if [ "$AFTER_USER_COUNT" -gt "$INITIAL_USER_COUNT" ]; then
    log_success "User count increased from $INITIAL_USER_COUNT to $AFTER_USER_COUNT"
else
    log_error "User count did not increase"
fi

CONVERSATION_ID=$(create_test_conversation)
INITIAL_CONV_COUNT=$(count_conversations)
log_info "Total conversations: $INITIAL_CONV_COUNT"
echo ""

# Test 3: Create backup before rotation
echo -e "${YELLOW}═══ Test 3: Create Backup (Pre-Rotation) ═══${NC}"
BACKUP_FILE=$(test_backup_creation)
echo ""

# Test 4: Rotate MongoDB password
echo -e "${YELLOW}═══ Test 4: Rotate MongoDB Password ═══${NC}"
log_info "Current MongoDB password from .env:"
OLD_MONGO_PASS=$(grep MONGODB_PASSWORD envs/.env | cut -d= -f2)
echo "  $OLD_MONGO_PASS"

log_info "Generating new password..."
NEW_MONGO_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
echo "  $NEW_MONGO_PASS"

log_info "Rotating password using script..."
echo "$OLD_MONGO_PASS" > /tmp/old_pass.txt
echo "$NEW_MONGO_PASS" > /tmp/new_pass.txt

# Execute rotation script
chmod +x scripts/rotate-mongo-credentials.sh
if ./scripts/rotate-mongo-credentials.sh "$OLD_MONGO_PASS" "$NEW_MONGO_PASS"; then
    log_success "MongoDB password rotation script executed successfully"

    # Update .env file
    sed -i.bak "s|^MONGODB_PASSWORD=.*|MONGODB_PASSWORD=$NEW_MONGO_PASS|" envs/.env
    log_success ".env file updated"

    # ▲  CRITICAL LESSON LEARNED: Use 'down' + 'up' NOT 'restart'
    #
    # WHY: docker compose restart does NOT reload environment variables from .env
    #      It only restarts the process inside the EXISTING container with OLD env vars
    #
    # REAL ISSUE WE HAD:
    # - Updated .env with new password
    # - Ran 'docker compose restart api'
    # - Container still had OLD password → AUTH FAILURES
    # - Symptoms: "Cargando conversaciones..." stuck, Redis WRONGPASS errors
    #
    # CORRECT APPROACH:
    # - 'down' destroys the old container
    # - 'up' creates NEW container with NEW env vars from .env
    # - Container now has credentials matching .env file
    #
    # See: README.md "Lessons Learned" section for full explanation
    log_info "Recreating API container with new credentials (down + up, NOT restart)..."
    docker compose -p copilotos -f infra/docker-compose.yml -f infra/docker-compose.dev.yml down api
    docker compose -p copilotos -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up -d api
    sleep 5

    wait_for_api || exit 1
else
    log_error "MongoDB password rotation failed"
    exit 1
fi
echo ""

# Test 5: Verify data survived rotation
echo -e "${YELLOW}═══ Test 5: Verify Data After MongoDB Rotation ═══${NC}"
check_services_health || exit 1

AFTER_ROTATION_USER_COUNT=$(count_users)
log_info "User count after rotation: $AFTER_ROTATION_USER_COUNT"

if [ "$AFTER_ROTATION_USER_COUNT" -eq "$AFTER_USER_COUNT" ]; then
    log_success "User count unchanged ($AFTER_ROTATION_USER_COUNT) - DATA PRESERVED! ✨"
else
    log_error "User count changed from $AFTER_USER_COUNT to $AFTER_ROTATION_USER_COUNT - DATA LOST!"
    exit 1
fi

verify_user_exists || exit 1
test_user_login || exit 1

AFTER_ROTATION_CONV_COUNT=$(count_conversations)
if [ "$AFTER_ROTATION_CONV_COUNT" -eq "$INITIAL_CONV_COUNT" ]; then
    log_success "Conversation count unchanged ($AFTER_ROTATION_CONV_COUNT) - DATA PRESERVED! ✨"
else
    log_error "Conversation count changed - DATA LOST!"
fi
echo ""

# Test 6: Rotate Redis password
echo -e "${YELLOW}═══ Test 6: Rotate Redis Password ═══${NC}"
log_info "Current Redis password from .env:"
OLD_REDIS_PASS=$(grep REDIS_PASSWORD envs/.env | cut -d= -f2)
echo "  $OLD_REDIS_PASS"

log_info "Generating new password..."
NEW_REDIS_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
echo "  $NEW_REDIS_PASS"

log_info "Rotating password using script..."
chmod +x scripts/rotate-redis-credentials.sh
if ./scripts/rotate-redis-credentials.sh "$NEW_REDIS_PASS"; then
    log_success "Redis password rotation script executed successfully"

    # Update .env file
    sed -i.bak "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=$NEW_REDIS_PASS|" envs/.env
    log_success ".env file updated"

    # ▲  CRITICAL: Same pattern as MongoDB - use down+up, NOT restart
    #
    # Redis AUTH FAILURES WERE OUR FIRST PRODUCTION ISSUE:
    # - Updated REDIS_PASSWORD in .env
    # - Used 'restart' → Container kept old password
    # - API tried to connect with new password from .env
    # - Redis rejected: "WRONGPASS invalid username-password pair"
    # - Result: Conversations wouldn't load, chat hung indefinitely
    #
    # DIAGNOSIS WAS:
    # 1. grep REDIS_PASSWORD envs/.env  → showed NEW password
    # 2. docker inspect copilotos-redis  → showed OLD password
    # 3. Mismatch! → Credential desynchronization
    #
    # FIX: Recreate containers to reload env vars from .env
    log_info "Recreating Redis and API containers with new credentials (down + up, NOT restart)..."
    docker compose -p copilotos -f infra/docker-compose.yml -f infra/docker-compose.dev.yml down redis api
    docker compose -p copilotos -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up -d redis api
    sleep 5

    wait_for_api || exit 1
else
    log_error "Redis password rotation failed"
    exit 1
fi
echo ""

# Test 7: Final verification
echo -e "${YELLOW}═══ Test 7: Final Data Verification ═══${NC}"
check_services_health || exit 1

FINAL_USER_COUNT=$(count_users)
FINAL_CONV_COUNT=$(count_conversations)

log_info "Final user count: $FINAL_USER_COUNT"
log_info "Final conversation count: $FINAL_CONV_COUNT"

if [ "$FINAL_USER_COUNT" -eq "$AFTER_USER_COUNT" ]; then
    log_success "User data fully preserved through both rotations! ✨"
else
    log_error "User data was lost"
fi

if [ "$FINAL_CONV_COUNT" -eq "$INITIAL_CONV_COUNT" ]; then
    log_success "Conversation data fully preserved through both rotations! ✨"
else
    log_error "Conversation data was lost"
fi

verify_user_exists || exit 1
test_user_login || exit 1
echo ""

# Test 8: Create post-rotation backup
echo -e "${YELLOW}═══ Test 8: Create Backup (Post-Rotation) ═══${NC}"
BACKUP_FILE_POST=$(test_backup_creation)
echo ""

# Test 9: Test backup restore
echo -e "${YELLOW}═══ Test 9: Test Backup Restore ═══${NC}"
log_info "Testing restore from pre-rotation backup..."
test_backup_restore "$BACKUP_FILE" || exit 1

# NOTE: Using 'restart' here is OK (not changing credentials)
# After a backup restore, we just need to restart the API to reconnect to MongoDB.
# We're NOT changing environment variables, so 'restart' is fine here.
# If we WERE changing credentials, we'd need 'down' + 'up' like above.
docker compose -p copilotos -f infra/docker-compose.yml -f infra/docker-compose.dev.yml restart api
sleep 5
wait_for_api || exit 1

RESTORED_USER_COUNT=$(count_users)
log_info "User count after restore: $RESTORED_USER_COUNT"

if [ "$RESTORED_USER_COUNT" -gt 0 ]; then
    log_success "Backup restore is functional! ✨"
else
    log_error "Backup restore verification failed"
fi
echo ""

# Final summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Test Results Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
echo ""

echo -e "${YELLOW}Data Journey:${NC}"
echo "  Initial users: $INITIAL_USER_COUNT → After creation: $AFTER_USER_COUNT"
echo "  After MongoDB rotation: $AFTER_ROTATION_USER_COUNT"
echo "  After Redis rotation: $FINAL_USER_COUNT"
echo "  After backup restore: $RESTORED_USER_COUNT"
echo ""

echo -e "${YELLOW}Backups Created:${NC}"
echo "  Pre-rotation: $BACKUP_FILE"
echo "  Post-rotation: $BACKUP_FILE_POST"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}ALL TESTS PASSED! Data persistence and backups work correctly! ◆${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}"
    exit 0
else
    echo -e "${RED}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}SOME TESTS FAILED - Please review the output above${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════════════════${NC}"
    exit 1
fi
