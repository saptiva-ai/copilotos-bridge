#!/bin/bash
# ============================================================================
# GRANULAR CHANGE DETECTION SCRIPT v2
# ============================================================================
# Detects which services have changed and outputs JSON for CI/CD integration.
#
# Usage:
#   ./detect-changes-v2.sh [base-ref]           # Compare with ref
#   ./detect-changes-v2.sh --since-tag v1.4.1   # Compare with tag
#   ./detect-changes-v2.sh --json               # Output JSON only
#   ./detect-changes-v2.sh --github-output      # Set GitHub Actions outputs
#
# Output:
#   - Human-readable summary
#   - JSON: {"services": ["backend", "web"], "all": false}
#   - Exit codes: 0=changes, 1=no changes, 2=error
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service to path mapping
# Format: service_name:path1,path2,path3
SERVICE_MAPPINGS=(
    "backend:apps/backend"
    "web:apps/web,packages"
    "file-manager:plugins/public/file-manager"
)

# Shared paths that affect ALL services
SHARED_PATHS=(
    "infra/"
    "docker-compose"
    ".env"
    "Makefile"
)

# Parse arguments
BASE_REF="HEAD~1"
JSON_ONLY=false
GITHUB_OUTPUT=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --since-tag)
            BASE_REF="$2"
            shift 2
            ;;
        --json)
            JSON_ONLY=true
            shift
            ;;
        --github-output)
            GITHUB_OUTPUT=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options] [base-ref]"
            echo ""
            echo "Options:"
            echo "  --since-tag TAG    Compare with a specific tag"
            echo "  --json             Output JSON only (for scripting)"
            echo "  --github-output    Set GitHub Actions outputs"
            echo "  --verbose, -v      Show detailed output"
            echo "  --help, -h         Show this help"
            echo ""
            echo "Examples:"
            echo "  $0                    # Compare with HEAD~1"
            echo "  $0 origin/main        # Compare with main branch"
            echo "  $0 --since-tag v1.4.1 # Compare with tag"
            exit 0
            ;;
        *)
            BASE_REF="$1"
            shift
            ;;
    esac
done

# Functions
log_info() {
    if [ "$JSON_ONLY" = false ]; then
        echo -e "${BLUE}ℹ️  $1${NC}"
    fi
}

log_success() {
    if [ "$JSON_ONLY" = false ]; then
        echo -e "${GREEN}✓ $1${NC}"
    fi
}

log_warning() {
    if [ "$JSON_ONLY" = false ]; then
        echo -e "${YELLOW}⚠️  $1${NC}"
    fi
}

log_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

# Verify git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log_error "Not a git repository"
    exit 2
fi

# Verify base ref exists
if ! git rev-parse "$BASE_REF" > /dev/null 2>&1; then
    log_error "Invalid ref: $BASE_REF"
    exit 2
fi

# Get changed files
if [ "$JSON_ONLY" = false ]; then
    echo ""
    log_info "Detecting changes since $BASE_REF..."
    echo ""
fi

CHANGED_FILES=$(git diff --name-only "$BASE_REF" HEAD 2>/dev/null || git diff --name-only "$BASE_REF" 2>/dev/null)

if [ -z "$CHANGED_FILES" ]; then
    if [ "$JSON_ONLY" = true ]; then
        echo '{"services": [], "all": false, "changes": 0}'
    else
        log_info "No changes detected"
    fi
    exit 1
fi

CHANGE_COUNT=$(echo "$CHANGED_FILES" | wc -l)

# Check for shared path changes (affects all services)
ALL_SERVICES=false
for shared_path in "${SHARED_PATHS[@]}"; do
    if echo "$CHANGED_FILES" | grep -q "^$shared_path"; then
        ALL_SERVICES=true
        if [ "$JSON_ONLY" = false ]; then
            log_warning "Shared path changed: $shared_path (affects all services)"
        fi
        break
    fi
done

# Detect changed services
declare -a CHANGED_SERVICES=()

for mapping in "${SERVICE_MAPPINGS[@]}"; do
    service="${mapping%%:*}"
    paths="${mapping#*:}"

    # Split paths by comma
    IFS=',' read -ra path_array <<< "$paths"

    service_changed=false
    changed_path=""

    for path in "${path_array[@]}"; do
        if echo "$CHANGED_FILES" | grep -q "^$path"; then
            service_changed=true
            changed_path="$path"
            break
        fi
    done

    if [ "$service_changed" = true ] || [ "$ALL_SERVICES" = true ]; then
        CHANGED_SERVICES+=("$service")
        if [ "$JSON_ONLY" = false ]; then
            if [ "$ALL_SERVICES" = true ] && [ "$service_changed" = false ]; then
                log_success "$service (via shared path)"
            else
                log_success "$service (changes in $changed_path/)"
            fi
        fi
    fi
done

# Generate output
if [ "$JSON_ONLY" = true ]; then
    # JSON output for CI/CD
    services_json=$(printf '%s\n' "${CHANGED_SERVICES[@]}" | jq -R . | jq -s .)
    echo "{\"services\": $services_json, \"all\": $ALL_SERVICES, \"changes\": $CHANGE_COUNT}"
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}📊 Summary${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "   Files changed: $CHANGE_COUNT"
    echo "   Services affected: ${#CHANGED_SERVICES[@]}"

    if [ ${#CHANGED_SERVICES[@]} -gt 0 ]; then
        echo ""
        echo -e "   ${GREEN}Build/Deploy:${NC} ${CHANGED_SERVICES[*]}"
    fi

    if [ "$ALL_SERVICES" = true ]; then
        echo ""
        log_warning "Full redeploy recommended due to shared path changes"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

# GitHub Actions output
if [ "$GITHUB_OUTPUT" = true ] && [ -n "$GITHUB_OUTPUT" ]; then
    # Set outputs for GitHub Actions
    services_json=$(printf '%s\n' "${CHANGED_SERVICES[@]}" | jq -R . | jq -s -c .)

    echo "services=$services_json" >> "$GITHUB_OUTPUT"
    echo "services_csv=${CHANGED_SERVICES[*]}" >> "$GITHUB_OUTPUT"
    echo "all=$ALL_SERVICES" >> "$GITHUB_OUTPUT"
    echo "has_changes=true" >> "$GITHUB_OUTPUT"
    echo "change_count=$CHANGE_COUNT" >> "$GITHUB_OUTPUT"

    # Individual service flags
    for mapping in "${SERVICE_MAPPINGS[@]}"; do
        service="${mapping%%:*}"
        service_var="${service//-/_}"  # Replace hyphens with underscores

        if [[ " ${CHANGED_SERVICES[*]} " =~ " $service " ]]; then
            echo "${service_var}_changed=true" >> "$GITHUB_OUTPUT"
        else
            echo "${service_var}_changed=false" >> "$GITHUB_OUTPUT"
        fi
    done
fi

# Verbose output
if [ "$VERBOSE" = true ] && [ "$JSON_ONLY" = false ]; then
    echo ""
    echo "Changed files:"
    echo "$CHANGED_FILES" | head -20
    if [ "$CHANGE_COUNT" -gt 20 ]; then
        echo "... and $((CHANGE_COUNT - 20)) more"
    fi
fi

# Exit with appropriate code
if [ ${#CHANGED_SERVICES[@]} -eq 0 ]; then
    exit 1  # No service changes
else
    exit 0  # Has changes
fi
