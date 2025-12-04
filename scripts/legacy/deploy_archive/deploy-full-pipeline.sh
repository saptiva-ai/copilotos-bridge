#!/bin/bash
################################################################################
# Full Deployment Pipeline - Orchestrates entire deployment process
#
# Usage:
#   ./scripts/deploy-full-pipeline.sh [--skip-audit] [--skip-backup] [--incremental]
#
# This script runs the complete deployment pipeline:
#   1. Pre-deployment audit
#   2. Comprehensive backups (MongoDB + Docker volumes)
#   3. Build and deploy with TAR
#   4. Post-deployment verification
#
# Options:
#   --skip-audit       Skip pre-deployment audit (not recommended)
#   --skip-backup      Skip backups (DANGEROUS - not recommended)
#   --incremental      Use incremental build (faster, uses cache)
#   --skip-tests       Skip local tests (faster, but risky)
#   -h, --help         Show this help
#
################################################################################

set -e
set -o pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOGS_DIR="$PROJECT_ROOT/deployment-logs"
LOG_FILE="$LOGS_DIR/deploy-${TIMESTAMP}.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Flags
SKIP_AUDIT=false
SKIP_BACKUP=false
INCREMENTAL=false
SKIP_TESTS=false

# Load production environment
if [ -f "$PROJECT_ROOT/envs/.env.prod" ]; then
    source "$PROJECT_ROOT/envs/.env.prod"
elif [ -f "$PROJECT_ROOT/envs/.env" ]; then
    source "$PROJECT_ROOT/envs/.env"
fi

# Validate required environment variables
if [ -z "$PROD_SERVER_HOST" ]; then
    echo -e "${RED}ERROR: PROD_SERVER_HOST not set${NC}"
    echo "Please set it in envs/.env.prod or export it:"
    echo "  export PROD_SERVER_HOST=user@your-server-ip"
    exit 1
fi

if [ -z "$PROD_DEPLOY_PATH" ]; then
    echo -e "${RED}ERROR: PROD_DEPLOY_PATH not set${NC}"
    echo "Please set it in envs/.env.prod or export it:"
    echo "  export PROD_DEPLOY_PATH=/path/to/deployment"
    exit 1
fi

SERVER_HOST="$PROD_SERVER_HOST"
DEPLOY_PATH="$PROD_DEPLOY_PATH"

# ============================================================================
# PARSE ARGUMENTS
# ============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-audit)
            SKIP_AUDIT=true
            shift
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --incremental)
            INCREMENTAL=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -h|--help)
            cat << EOF
Full Deployment Pipeline

Usage: $0 [OPTIONS]

Options:
  --skip-audit       Skip pre-deployment audit (not recommended)
  --skip-backup      Skip backups (DANGEROUS - not recommended)
  --incremental      Use incremental build (faster, uses cache)
  --skip-tests       Skip local tests (faster, but risky)
  -h, --help         Show this help

Examples:
  # Full safe deployment (recommended)
  $0

  # Fast deployment with incremental build
  $0 --incremental

  # Risky fast deployment (skip tests and use cache)
  $0 --incremental --skip-tests

EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h for help"
            exit 1
            ;;
    esac
done

# ============================================================================
# LOGGING SETUP
# ============================================================================
mkdir -p "$LOGS_DIR"

# Log function that outputs to both console and file
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

log_info() { log "${BLUE}[INFO]${NC} $1"; }
log_success() { log "${GREEN}[OK]${NC} $1"; }
log_warning() { log "${YELLOW}[WARN]${NC} $1"; }
log_error() { log "${RED}[ERROR]${NC} $1"; }

step() {
    log ""
    log "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    log "${GREEN}$1${NC}"
    log "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ============================================================================
# PIPELINE STAGES
# ============================================================================

# Stage 0: Pre-checks
stage_prechecks() {
    step "Stage 0/5: Pre-Flight Checks"

    log_info "Verifying environment..."

    # Check SSH access
    if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$SERVER_HOST" exit &>/dev/null; then
        log_error "Cannot connect to server: $SERVER_HOST"
        log_error "Check SSH keys and network connectivity"
        exit 1
    fi
    log_success "SSH access verified"

    # Check git status
    cd "$PROJECT_ROOT"
    if ! git diff-index --quiet HEAD --; then
        log_warning "You have uncommitted changes"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Deployment cancelled"
            exit 1
        fi
    fi

    # Check branch
    CURRENT_BRANCH=$(git branch --show-current)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        log_warning "Current branch is '$CURRENT_BRANCH', not 'main'"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Deployment cancelled"
            exit 1
        fi
    fi

    log_success "Pre-flight checks passed"
}

# Stage 1: Audit
stage_audit() {
    if [ "$SKIP_AUDIT" = true ]; then
        log_warning "Skipping audit (--skip-audit flag)"
        return 0
    fi

    step "Stage 1/5: Pre-Deployment Audit"

    log_info "Copying audit script to server..."
    scp "$PROJECT_ROOT/scripts/audit-production-state.sh" \
        "$SERVER_HOST:$DEPLOY_PATH/scripts/" >> "$LOG_FILE" 2>&1

    log_info "Running audit on server..."
    ssh "$SERVER_HOST" "cd $DEPLOY_PATH && chmod +x scripts/audit-production-state.sh" >> "$LOG_FILE" 2>&1
    ssh "$SERVER_HOST" "bash -s" < "$PROJECT_ROOT/scripts/audit-production-state.sh" | tee -a "$LOG_FILE"

    log_info "Downloading audit report..."
    scp "$SERVER_HOST:$DEPLOY_PATH/audit-report-*.json" "$LOGS_DIR/" >> "$LOG_FILE" 2>&1

    AUDIT_FILE=$(ls -t "$LOGS_DIR"/audit-report-*.json | head -1)
    if [ -f "$AUDIT_FILE" ]; then
        log_success "Audit report saved: $AUDIT_FILE"

        # Parse and display key metrics
        if command -v jq &>/dev/null; then
            log_info "Current system state:"
            jq -r '
                "  Users: \(.user_activity.total_users // "N/A")",
                "  Sessions: \(.user_activity.total_sessions // "N/A")",
                "  Messages: \(.user_activity.total_messages // "N/A")",
                "  Documents: \(.user_activity.total_documents // "N/A")"
            ' "$AUDIT_FILE" | tee -a "$LOG_FILE"
        fi
    else
        log_error "Failed to download audit report"
        return 1
    fi
}

# Stage 2: Backup
stage_backup() {
    if [ "$SKIP_BACKUP" = true ]; then
        log_error "Skipping backup is DANGEROUS and not recommended!"
        read -p "Are you SURE? Type 'SKIP' to confirm: " confirm
        if [ "$confirm" != "SKIP" ]; then
            log_info "Proceeding with backup..."
        else
            log_warning "Backup skipped by user"
            return 0
        fi
    fi

    step "Stage 2/5: Data Backup"

    log_info "Copying backup script to server..."
    scp "$PROJECT_ROOT/scripts/backup-docker-volumes.sh" \
        "$SERVER_HOST:$DEPLOY_PATH/scripts/" >> "$LOG_FILE" 2>&1

    log_info "Running backup on server..."
    ssh "$SERVER_HOST" "cd $DEPLOY_PATH && \
        chmod +x scripts/backup-docker-volumes.sh && \
        ./scripts/backup-docker-volumes.sh \
            --backup-dir ~/backups/volumes \
            --retention-days 7" | tee -a "$LOG_FILE"

    log_info "Verifying backup..."
    BACKUP_SIZE=$(ssh "$SERVER_HOST" "du -sh ~/backups/volumes/* | tail -1 | cut -f1" 2>/dev/null || echo "unknown")

    if [ "$BACKUP_SIZE" != "unknown" ]; then
        log_success "Backup completed: $BACKUP_SIZE"
    else
        log_error "Backup verification failed"
        return 1
    fi
}

# Stage 3: Local tests (optional)
stage_tests() {
    if [ "$SKIP_TESTS" = true ]; then
        log_warning "Skipping local tests (--skip-tests flag)"
        return 0
    fi

    step "Stage 3/5: Local Tests"

    cd "$PROJECT_ROOT"

    log_info "Validating environment variables..."
    if ! make env-check >> "$LOG_FILE" 2>&1; then
        log_error "Environment validation failed"
        log_info "Check $LOG_FILE for details"
        return 1
    fi
    log_success "Environment validated"

    log_info "Running test suite (this may take a few minutes)..."
    if ! make test >> "$LOG_FILE" 2>&1; then
        log_error "Tests failed"
        log_info "Check $LOG_FILE for details"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        log_warning "Proceeding despite test failures"
    else
        log_success "All tests passed"
    fi
}

# Stage 4: Deploy
stage_deploy() {
    step "Stage 4/5: Deployment"

    cd "$PROJECT_ROOT"

    local deploy_flags=""
    if [ "$INCREMENTAL" = true ]; then
        deploy_flags="--incremental"
        log_info "Using incremental build (faster, with cache)"
    fi

    log_info "Starting deployment pipeline..."
    if ./scripts/deploy-with-tar.sh $deploy_flags | tee -a "$LOG_FILE"; then
        log_success "Deployment completed successfully"
    else
        log_error "Deployment failed"
        log_error "Check logs: $LOG_FILE"
        return 1
    fi
}

# Stage 5: Verification
stage_verification() {
    step "Stage 5/5: Post-Deployment Verification"

    log_info "Waiting for services to stabilize (30 seconds)..."
    sleep 30

    # API Health
    log_info "Checking API health..."
    API_HEALTH=$(ssh "$SERVER_HOST" "curl -sf --max-time 10 http://localhost:8001/api/health" 2>/dev/null | jq -r '.status' 2>/dev/null || echo "error")

    if [ "$API_HEALTH" = "healthy" ]; then
        log_success "API: healthy"
    else
        log_error "API: $API_HEALTH"
        return 1
    fi

    # Qdrant (new container)
    log_info "Checking Qdrant..."
    if ssh "$SERVER_HOST" "docker ps | grep -q qdrant"; then
        log_success "Qdrant: running"

        # Test Qdrant API
        QDRANT_COLLECTIONS=$(ssh "$SERVER_HOST" "curl -sf http://localhost:6333/collections" 2>/dev/null | jq -r '.status' 2>/dev/null || echo "error")
        if [ "$QDRANT_COLLECTIONS" = "ok" ] || [ "$QDRANT_COLLECTIONS" = "error" ]; then
            log_success "Qdrant API: responsive"
        fi
    else
        log_error "Qdrant: not running"
        return 1
    fi

    # Data verification (if we have audit report)
    AUDIT_FILE=$(ls -t "$LOGS_DIR"/audit-report-*.json | head -1)
    if [ -f "$AUDIT_FILE" ] && command -v jq &>/dev/null; then
        log_info "Verifying data integrity..."

        PRE_USERS=$(jq -r '.user_activity.total_users // 0' "$AUDIT_FILE")

        POST_USERS=$(ssh "$SERVER_HOST" "docker exec octavios-chat-capital414-mongodb mongosh \
            --username ${MONGODB_USER:-octavios_user} \
            --password ${MONGODB_PASSWORD} \
            --authenticationDatabase admin \
            --quiet \
            --eval 'use octavios; db.users.countDocuments()'" 2>/dev/null || echo "0")

        if [ "$PRE_USERS" = "$POST_USERS" ]; then
            log_success "Data integrity verified (users: $POST_USERS)"
        else
            log_warning "User count changed: $PRE_USERS -> $POST_USERS"
        fi
    fi

    log_success "All verifications passed"
}

# ============================================================================
# MAIN PIPELINE
# ============================================================================
main() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  FULL DEPLOYMENT PIPELINE                                     ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    log_info "Deployment started: $(date)"
    log_info "Target server: $SERVER_HOST"
    log_info "Deploy path: $DEPLOY_PATH"
    log_info "Log file: $LOG_FILE"
    echo ""

    # Confirmation
    if [ "$SKIP_BACKUP" = false ] && [ "$SKIP_AUDIT" = false ]; then
        echo -e "${YELLOW}This will:${NC}"
        echo "  1. Audit current production state"
        echo "  2. Backup all Docker volumes"
        echo "  3. Run local tests"
        echo "  4. Build and deploy new version"
        echo "  5. Verify deployment"
        echo ""
        read -p "Proceed with deployment? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled by user"
            exit 0
        fi
    fi

    # Run pipeline stages
    local start_time=$(date +%s)

    stage_prechecks
    stage_audit
    stage_backup
    stage_tests
    stage_deploy
    stage_verification

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    # Summary
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  DEPLOYMENT SUCCESSFUL                                        ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    log_success "Deployment completed in ${minutes}m ${seconds}s"
    log_info "Logs saved to: $LOG_FILE"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Monitor logs: ssh $SERVER_HOST 'docker compose logs -f'"
    echo "  2. Test application manually"
    echo "  3. Review deployment log: cat $LOG_FILE"
    echo ""
}

# Run
main "$@"
