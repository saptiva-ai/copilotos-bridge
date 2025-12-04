#!/bin/bash
################################################################################
# Production State Auditor - Generate comprehensive state report
#
# Usage:
#   # From local machine:
#   ssh jf@34.172.67.93 'bash -s' < scripts/audit-production-state.sh
#
#   # Or on server:
#   ./scripts/audit-production-state.sh
#
# Output: audit-report-TIMESTAMP.json
################################################################################

set -e
set -o pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="audit-report-${TIMESTAMP}.json"
REPORT_MD="audit-report-${TIMESTAMP}.md"
PROJECT_ROOT="${PROJECT_ROOT:-/home/jf/capital414-chat}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-octavios-chat-capital414}"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================
log_info() { echo -e "${BLUE}[INFO]${NC} $1" >&2; }
log_success() { echo -e "${GREEN}[OK]${NC} $1" >&2; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1" >&2; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# ============================================================================
# ENVIRONMENT DETECTION
# ============================================================================
detect_environment() {
    log_info "Detecting environment..."

    # Load environment if available (using set -a to handle spaces in values)
    if [ -f "$PROJECT_ROOT/envs/.env" ]; then
        set -a
        source "$PROJECT_ROOT/envs/.env" 2>/dev/null || true
        set +a
        log_success "Loaded .env"
    else
        log_warning "No environment file found"
    fi

    # Export variables for MongoDB access
    export MONGODB_USER="${MONGODB_USER:-octavios_user}"
    export MONGODB_PASSWORD="${MONGODB_PASSWORD:-secure_password_change_me}"
    export MONGODB_DATABASE="${MONGODB_DATABASE:-octavios}"
    export MONGODB_CONTAINER="${COMPOSE_PROJECT_NAME}-mongodb"
}

# ============================================================================
# MONGODB STATS
# ============================================================================
get_mongodb_stats() {
    log_info "Collecting MongoDB statistics..."

    local stats_json=""

    if docker ps --filter "name=$MONGODB_CONTAINER" --format '{{.Names}}' | grep -q "$MONGODB_CONTAINER"; then
        # MongoDB is running - collect detailed stats
        # Using --norc to avoid "switched to db" messages
        stats_json=$(docker exec "$MONGODB_CONTAINER" mongosh \
            --username "$MONGODB_USER" \
            --password "$MONGODB_PASSWORD" \
            --authenticationDatabase admin \
            --quiet \
            --norc \
            "$MONGODB_DATABASE" \
            --eval "
                // Count documents in each collection
                const collections = db.getCollectionNames();
                const collectionStats = {};

                collections.forEach(function(col) {
                    try {
                        const stats = db[col].stats();
                        collectionStats[col] = {
                            count: stats.count,
                            size_mb: parseFloat((stats.size / 1024 / 1024).toFixed(2)),
                            avg_obj_size: stats.avgObjSize || 0
                        };
                    } catch(e) {
                        collectionStats[col] = { error: e.message };
                    }
                });

                // Database-level stats
                const dbStats = db.stats();

                print(JSON.stringify({
                    database: '$MONGODB_DATABASE',
                    collections: collectionStats,
                    total_size_mb: parseFloat((dbStats.dataSize / 1024 / 1024).toFixed(2)),
                    index_size_mb: parseFloat((dbStats.indexSize / 1024 / 1024).toFixed(2)),
                    storage_size_mb: parseFloat((dbStats.storageSize / 1024 / 1024).toFixed(2))
                }));
            " 2>/dev/null | grep -v "switched to db" | tr -d '\n' || echo '{"error": "Failed to collect MongoDB stats"}')

        log_success "MongoDB stats collected"
    else
        stats_json='{"error": "MongoDB container not running"}'
        log_warning "MongoDB container not running"
    fi

    echo "$stats_json"
}

# ============================================================================
# DOCKER CONTAINERS
# ============================================================================
get_docker_containers() {
    log_info "Collecting Docker container information..."

    local containers_json="["
    local first=true

    while IFS= read -r line; do
        if [ "$first" = true ]; then
            first=false
        else
            containers_json+=","
        fi

        IFS='|' read -r name status created image <<< "$line"

        containers_json+=$(cat <<EOF
{
    "name": "$name",
    "status": "$status",
    "created": "$created",
    "image": "$image"
}
EOF
)
    done < <(docker ps -a --filter "name=${COMPOSE_PROJECT_NAME}" --format "{{.Names}}|{{.Status}}|{{.CreatedAt}}|{{.Image}}")

    containers_json+="]"

    log_success "Container info collected"
    echo "$containers_json"
}

# ============================================================================
# DOCKER VOLUMES
# ============================================================================
get_docker_volumes() {
    log_info "Collecting Docker volume information..."

    local volumes_json="{"
    local first=true

    # Common volume patterns for this project
    local volume_patterns=(
        "${COMPOSE_PROJECT_NAME}_mongodb_data"
        "${COMPOSE_PROJECT_NAME}_redis_data"
        "${COMPOSE_PROJECT_NAME}_minio_data"
        "${COMPOSE_PROJECT_NAME}_qdrant_data"
        "${COMPOSE_PROJECT_NAME}_qdrant_snapshots"
    )

    for volume_name in "${volume_patterns[@]}"; do
        if docker volume inspect "$volume_name" &>/dev/null; then
            local size=$(docker system df -v 2>/dev/null | grep "$volume_name" | awk '{print $3}' || echo "unknown")

            if [ "$first" = true ]; then
                first=false
            else
                volumes_json+=","
            fi

            volumes_json+="\"$volume_name\": {\"size\": \"$size\", \"exists\": true}"
        fi
    done

    volumes_json+="}"

    log_success "Volume info collected"
    echo "$volumes_json"
}

# ============================================================================
# GIT INFORMATION
# ============================================================================
get_git_info() {
    log_info "Collecting Git information..."

    cd "$PROJECT_ROOT"

    local git_json="{}"

    if [ -d ".git" ]; then
        local current_commit=$(git log -1 --format='%H' 2>/dev/null || echo "unknown")
        local current_commit_short=$(git log -1 --format='%h' 2>/dev/null || echo "unknown")
        local current_message=$(git log -1 --format='%s' 2>/dev/null || echo "unknown")
        local current_author=$(git log -1 --format='%an' 2>/dev/null || echo "unknown")
        local current_date=$(git log -1 --format='%ai' 2>/dev/null || echo "unknown")
        local current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
        local has_uncommitted=$(git diff-index --quiet HEAD -- 2>/dev/null && echo "false" || echo "true")

        git_json=$(cat <<EOF
{
    "commit": "$current_commit",
    "commit_short": "$current_commit_short",
    "message": "$current_message",
    "author": "$current_author",
    "date": "$current_date",
    "branch": "$current_branch",
    "has_uncommitted_changes": $has_uncommitted
}
EOF
)
        log_success "Git info collected"
    else
        git_json='{"error": "Not a git repository"}'
        log_warning "Not a git repository"
    fi

    echo "$git_json"
}

# ============================================================================
# SYSTEM RESOURCES
# ============================================================================
get_system_resources() {
    log_info "Collecting system resource information..."

    local disk_usage=$(df -h / | tail -1 | awk '{print "{\"total\": \"" $2 "\", \"used\": \"" $3 "\", \"available\": \"" $4 "\", \"percent\": \"" $5 "\"}"}')
    local memory_usage=$(free -h | grep Mem | awk '{print "{\"total\": \"" $2 "\", \"used\": \"" $3 "\", \"available\": \"" $7 "\"}"}')

    local resources_json=$(cat <<EOF
{
    "disk": $disk_usage,
    "memory": $memory_usage,
    "docker_disk_usage": $(docker system df --format json 2>/dev/null || echo '{}')
}
EOF
)

    log_success "System resources collected"
    echo "$resources_json"
}

# ============================================================================
# USER ANALYSIS
# ============================================================================
get_user_analysis() {
    log_info "Analyzing user activity..."

    local user_stats=""

    if docker ps --filter "name=$MONGODB_CONTAINER" --format '{{.Names}}' | grep -q "$MONGODB_CONTAINER"; then
        user_stats=$(docker exec "$MONGODB_CONTAINER" mongosh \
            --username "$MONGODB_USER" \
            --password "$MONGODB_PASSWORD" \
            --authenticationDatabase admin \
            --quiet \
            --norc \
            "$MONGODB_DATABASE" \
            --eval "
                const totalUsers = db.users.countDocuments();
                const activeUsers = db.chat_sessions.distinct('user_id').length;
                const totalSessions = db.chat_sessions.countDocuments();
                const totalMessages = db.chat_messages.countDocuments();
                const totalDocuments = db.documents ? db.documents.countDocuments() : 0;

                // Get recent activity (last 7 days)
                const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
                const recentSessions = db.chat_sessions.countDocuments({ created_at: { \$gte: sevenDaysAgo } });

                print(JSON.stringify({
                    total_users: totalUsers,
                    active_users: activeUsers,
                    total_sessions: totalSessions,
                    total_messages: totalMessages,
                    total_documents: totalDocuments,
                    recent_sessions_7d: recentSessions
                }));
            " 2>/dev/null | grep -v "switched to db" | tr -d '\n' || echo '{"error": "Failed to analyze users"}')

        log_success "User analysis collected"
    else
        user_stats='{"error": "MongoDB container not running"}'
        log_warning "Cannot analyze users - MongoDB not running"
    fi

    echo "$user_stats"
}

# ============================================================================
# GENERATE REPORT
# ============================================================================
generate_report() {
    log_info "Generating comprehensive audit report..."

    detect_environment

    local mongodb_stats=$(get_mongodb_stats)
    local docker_containers=$(get_docker_containers)
    local docker_volumes=$(get_docker_volumes)
    local git_info=$(get_git_info)
    local system_resources=$(get_system_resources)
    local user_analysis=$(get_user_analysis)

    # Generate final JSON report
    cat > "$REPORT_FILE" <<EOF
{
    "audit_timestamp": "$(date -Iseconds)",
    "hostname": "$(hostname)",
    "project_root": "$PROJECT_ROOT",
    "compose_project_name": "$COMPOSE_PROJECT_NAME",
    "git": $git_info,
    "mongodb": $mongodb_stats,
    "user_activity": $user_analysis,
    "containers": $docker_containers,
    "volumes": $docker_volumes,
    "system_resources": $system_resources
}
EOF

    log_success "Report generated: $REPORT_FILE"

    # Pretty print summary to console
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  PRODUCTION STATE AUDIT REPORT                                 ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if command -v jq &>/dev/null; then
        echo -e "${BLUE}Summary:${NC}"
        jq -r '
            "  Git Commit: \(.git.commit_short) - \(.git.message)",
            "  Branch: \(.git.branch)",
            "  Total Users: \(.user_activity.total_users // "N/A")",
            "  Active Users: \(.user_activity.active_users // "N/A")",
            "  Total Sessions: \(.user_activity.total_sessions // "N/A")",
            "  Total Messages: \(.user_activity.total_messages // "N/A")",
            "  Total Documents: \(.user_activity.total_documents // "N/A")",
            "  Recent Activity (7d): \(.user_activity.recent_sessions_7d // "N/A") sessions",
            "",
            "  Running Containers: \(.containers | length)",
            "  MongoDB Size: \(.mongodb.total_size_mb // "N/A") MB",
            "  Disk Usage: \(.system_resources.disk.percent)"
        ' "$REPORT_FILE"
    else
        log_warning "jq not installed - skipping pretty summary"
        echo "  Full report available in: $REPORT_FILE"
    fi

    echo ""
    echo -e "${BLUE}Full report saved to:${NC} $REPORT_FILE"
    echo ""
    echo -e "${YELLOW}Download report to local machine:${NC}"
    echo "  scp jf@34.172.67.93:$PROJECT_ROOT/$REPORT_FILE ./"
    echo ""

    # Generate Markdown report
    generate_markdown_report
}

# ============================================================================
# GENERATE MARKDOWN REPORT
# ============================================================================
generate_markdown_report() {
    log_info "Generating Markdown report..."

    if [ ! -f "$REPORT_FILE" ]; then
        log_error "JSON report not found: $REPORT_FILE"
        return 1
    fi

    # Generate Markdown report
    cat > "$REPORT_MD" <<'MDEOF'
# Production State Audit Report

**Generated:** $(date -Iseconds)
**Hostname:** $(hostname)
**Project Root:** $PROJECT_ROOT
**Compose Project:** $COMPOSE_PROJECT_NAME

---

## 📊 Summary

MDEOF

    # Add summary using jq if available
    if command -v jq &>/dev/null; then
        cat >> "$REPORT_MD" <<MDEOF
$(jq -r '
"### User Activity\n",
"- **Total Users:** \(.user_activity.total_users // "N/A")",
"- **Active Users:** \(.user_activity.active_users // "N/A")",
"- **Total Sessions:** \(.user_activity.total_sessions // "N/A")",
"- **Total Messages:** \(.user_activity.total_messages // "N/A")",
"- **Total Documents:** \(.user_activity.total_documents // "N/A")",
"- **Recent Activity (7d):** \(.user_activity.recent_sessions_7d // "N/A") sessions\n",
"### Infrastructure\n",
"- **Running Containers:** \(.containers | length)",
"- **MongoDB Size:** \(.mongodb.total_size_mb // "N/A") MB",
"- **Disk Usage:** \(.system_resources.disk.used) / \(.system_resources.disk.total) (\(.system_resources.disk.percent))",
"- **Memory Usage:** \(.system_resources.memory.used) / \(.system_resources.memory.total)\n"
' "$REPORT_FILE")

---

## 🐳 Docker Containers

| Container | Status | Image | Created |
|-----------|--------|-------|---------|
$(jq -r '.containers[] | "| \(.name) | \(.status) | \(.image) | \(.created) |"' "$REPORT_FILE")

---

## 💾 MongoDB Collections

$(jq -r '
if .mongodb.collections then
    "| Collection | Documents | Size (MB) |\n|------------|-----------|-----------|",
    (.mongodb.collections | to_entries[] | "| \(.key) | \(.value.count // 0) | \(.value.size_mb // 0) |")
else
    "_MongoDB stats not available_"
end
' "$REPORT_FILE")

**Total Database Size:** $(jq -r '.mongodb.total_size_mb // "N/A"' "$REPORT_FILE") MB
**Index Size:** $(jq -r '.mongodb.index_size_mb // "N/A"' "$REPORT_FILE") MB
**Storage Size:** $(jq -r '.mongodb.storage_size_mb // "N/A"' "$REPORT_FILE") MB

---

## 💻 System Resources

### Disk
- **Total:** $(jq -r '.system_resources.disk.total' "$REPORT_FILE")
- **Used:** $(jq -r '.system_resources.disk.used' "$REPORT_FILE")
- **Available:** $(jq -r '.system_resources.disk.available' "$REPORT_FILE")
- **Usage:** $(jq -r '.system_resources.disk.percent' "$REPORT_FILE")

### Memory
- **Total:** $(jq -r '.system_resources.memory.total' "$REPORT_FILE")
- **Used:** $(jq -r '.system_resources.memory.used' "$REPORT_FILE")
- **Available:** $(jq -r '.system_resources.memory.available' "$REPORT_FILE")

---

## 🔧 Git Repository

$(jq -r '
if .git.error then
    "⚠️ **" + .git.error + "**"
else
    "- **Branch:** \(.git.branch)\n" +
    "- **Commit:** \(.git.commit_short) - \(.git.message)\n" +
    "- **Author:** \(.git.author)\n" +
    "- **Date:** \(.git.date)\n" +
    "- **Uncommitted Changes:** \(.git.has_uncommitted_changes)"
end
' "$REPORT_FILE")

---

## 📝 Next Steps

### Pre-Deploy Checklist
- [ ] Review this audit report
- [ ] Backup MongoDB data
- [ ] Backup Docker volumes
- [ ] Verify sufficient disk space (need ~10GB free)
- [ ] Review deployment plan

### Recommended Actions
1. **If deploying:** Follow `docs/deployment/MIGRATION_PLAN_QDRANT.md`
2. **Download reports:**
   \`\`\`bash
   scp jf@34.172.67.93:$PROJECT_ROOT/$REPORT_FILE ./
   scp jf@34.172.67.93:$PROJECT_ROOT/$REPORT_MD ./
   \`\`\`

---

**Report Files:**
- JSON: \`$REPORT_FILE\`
- Markdown: \`$REPORT_MD\`
MDEOF
    else
        # Fallback if jq is not available
        cat >> "$REPORT_MD" <<MDEOF
_jq not available - detailed report in JSON format: $REPORT_FILE_

### Basic Info
- Audit Timestamp: $(date -Iseconds)
- Hostname: $(hostname)
- Project Root: $PROJECT_ROOT

Please install jq for detailed Markdown reports.
MDEOF
    fi

    log_success "Markdown report generated: $REPORT_MD"
    echo -e "${BLUE}Markdown report saved to:${NC} $REPORT_MD" >&2
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================
main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Production State Auditor                                     ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Change to project directory if provided
    if [ -d "$PROJECT_ROOT" ]; then
        cd "$PROJECT_ROOT"
    fi

    generate_report

    exit 0
}

# Run
main "$@"
