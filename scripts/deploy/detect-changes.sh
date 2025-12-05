#!/bin/bash
# ============================================================================
# CHANGE DETECTION SCRIPT
# ============================================================================
# Detects which services have changed since last deploy
# Usage: ./scripts/deploy/detect-changes.sh [base-ref]
# ============================================================================

set -e

BASE_REF="${1:-HEAD~1}"  # Default: compare with previous commit
CHANGED_SERVICES=()

# Service to directory mapping
declare -A SERVICE_PATHS=(
    ["backend"]="apps/backend"
    ["web"]="apps/web packages"
    ["file-manager"]="plugins/public/file-manager"
    ["bank-advisor"]="plugins/bank-advisor-private"
)

echo "🔍 Detecting changes since $BASE_REF..."
echo ""

# Get list of changed files
CHANGED_FILES=$(git diff --name-only "$BASE_REF" HEAD)

if [ -z "$CHANGED_FILES" ]; then
    echo "ℹ️  No changes detected"
    exit 0
fi

# Check each service
for service in "${!SERVICE_PATHS[@]}"; do
    paths="${SERVICE_PATHS[$service]}"

    # Check if any changed file matches this service's paths
    for path in $paths; do
        if echo "$CHANGED_FILES" | grep -q "^$path/"; then
            CHANGED_SERVICES+=("$service")
            echo "✓ $service (changes in $path/)"
            break
        fi
    done
done

# Check for infrastructure changes (affects all services)
if echo "$CHANGED_FILES" | grep -q "^infra/"; then
    echo "⚠️  Infrastructure changes detected - recommend full redeploy"
    CHANGED_SERVICES=("backend" "web" "file-manager" "bank-advisor")
fi

echo ""
if [ ${#CHANGED_SERVICES[@]} -eq 0 ]; then
    echo "ℹ️  No service changes detected"
else
    echo "📦 Changed services: ${CHANGED_SERVICES[*]}"
fi

# Output services as space-separated list for scripting
echo "${CHANGED_SERVICES[*]}"
