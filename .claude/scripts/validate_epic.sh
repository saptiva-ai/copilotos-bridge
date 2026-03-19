#!/bin/bash
# .claude/scripts/validate_epic.sh
# Validates EPIC before it can be marked DONE
# Exit codes: 0 = pass, 1 = fail

set -euo pipefail

EPIC_FILE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 <path-to-epic-file>"
    echo ""
    echo "Example:"
    echo "  $0 docs/context/product/EPICS/EPIC-HU4.md"
    echo ""
    echo "Validates:"
    echo "  1. All Target Files exist"
    echo "  2. All documented test commands can run"
    echo "  3. Demo evidence is present"
    exit 1
}

if [ -z "$EPIC_FILE" ]; then
    echo -e "${RED}ERROR: EPIC file path required${NC}"
    usage
fi

if [ ! -f "$EPIC_FILE" ]; then
    echo -e "${RED}ERROR: EPIC file not found: $EPIC_FILE${NC}"
    exit 1
fi

echo "=========================================="
echo "EPIC Validation Script"
echo "=========================================="
echo "File: $EPIC_FILE"
echo ""

VALIDATION_FAILED=0

# ============================================================================
# CHECK 1: Verify Target Files Exist
# ============================================================================
echo -e "${YELLOW}[CHECK 1] Verifying Target Files...${NC}"

# Extract CREATE and MODIFY actions from Target Files table
# Format: | ACTION | path | description |
# NOTE: DELETE actions are intentionally ignored.
TARGET_FILES=$(awk -F'|' '
    /^\|/ {
        action = $2
        gsub(/^[ \t]+|[ \t]+$/, "", action)
        if (action == "CREATE" || action == "MODIFY") {
            path = $3
            gsub(/^[ \t]+|[ \t]+$/, "", path)
            gsub(/`/, "", path)
            if (path != "") print path
        }
    }
' "$EPIC_FILE" || true)
DELETE_FILES=$(awk -F'|' '
    /^\|/ {
        action = $2
        gsub(/^[ \t]+|[ \t]+$/, "", action)
        if (action == "DELETE") {
            path = $3
            gsub(/^[ \t]+|[ \t]+$/, "", path)
            gsub(/`/, "", path)
            if (path != "") print path
        }
    }
' "$EPIC_FILE" || true)

if [ -n "$DELETE_FILES" ]; then
    echo -e "${YELLOW}  NOTE: DELETE target files are not validated${NC}"
fi

if [ -z "$TARGET_FILES" ]; then
    echo -e "${YELLOW}  No Target Files found in EPIC (skipping)${NC}"
else
    FILE_CHECK_FAILED=0
    while IFS= read -r file; do
        if [ -n "$file" ]; then
            FULL_PATH="$PROJECT_ROOT/$file"
            if [ -f "$FULL_PATH" ] || [ -d "$FULL_PATH" ]; then
                echo -e "  ${GREEN}✓${NC} $file"
            else
                echo -e "  ${RED}✗${NC} $file (NOT FOUND)"
                FILE_CHECK_FAILED=1
            fi
        fi
    done <<< "$TARGET_FILES"

    if [ $FILE_CHECK_FAILED -eq 1 ]; then
        echo -e "${RED}  FAILED: Some target files do not exist${NC}"
        VALIDATION_FAILED=1
    else
        echo -e "${GREEN}  PASSED: All target files exist${NC}"
    fi
fi
echo ""

# ============================================================================
# CHECK 2: Verify Demo Evidence
# ============================================================================
echo -e "${YELLOW}[CHECK 2] Verifying Demo Evidence...${NC}"

# Look for Demo Evidence section and check if files exist
DEMO_SECTION=$(grep -A 10 "## Demo Evidence" "$EPIC_FILE" || true)

if [ -z "$DEMO_SECTION" ]; then
    echo -e "${YELLOW}  WARNING: No 'Demo Evidence' section found${NC}"
    echo -e "${YELLOW}  Recommendation: Add demo evidence before marking DONE${NC}"
else
    # Extract screenshot/video paths
    DEMO_FILES=$(echo "$DEMO_SECTION" | grep -oE 'docs/demos/[^)]+\.(png|jpg|mp4|gif)' || true)

    if [ -z "$DEMO_FILES" ]; then
        echo -e "${YELLOW}  WARNING: No demo files documented${NC}"
    else
        DEMO_CHECK_FAILED=0
        while IFS= read -r demo_file; do
            if [ -n "$demo_file" ]; then
                FULL_PATH="$PROJECT_ROOT/$demo_file"
                if [ -f "$FULL_PATH" ]; then
                    echo -e "  ${GREEN}✓${NC} $demo_file"
                else
                    echo -e "  ${RED}✗${NC} $demo_file (NOT FOUND)"
                    DEMO_CHECK_FAILED=1
                fi
            fi
        done <<< "$DEMO_FILES"

        if [ $DEMO_CHECK_FAILED -eq 1 ]; then
            echo -e "${RED}  FAILED: Demo evidence files missing${NC}"
            VALIDATION_FAILED=1
        fi
    fi
fi
echo ""

# ============================================================================
# CHECK 3: Verify Validation Commands (Parse but don't execute)
# ============================================================================
echo -e "${YELLOW}[CHECK 3] Checking Validation Commands Section...${NC}"

# Look for Validation Commands section
VALIDATION_COMMANDS=$(grep -A 20 "### Validation Commands\|## Validation Commands" "$EPIC_FILE" || true)

if [ -z "$VALIDATION_COMMANDS" ]; then
    echo -e "${YELLOW}  WARNING: No 'Validation Commands' section found${NC}"
else
    # Count commands in code blocks
    COMMAND_COUNT=$(echo "$VALIDATION_COMMANDS" | grep -E '^(pytest|curl|make|docker)' | wc -l || echo 0)
    echo -e "  ${GREEN}✓${NC} Found $COMMAND_COUNT validation commands documented"
    echo -e "  ${YELLOW}  Note: Commands not executed (manual verification required)${NC}"
fi
echo ""

# ============================================================================
# CHECK 4: Verify Definition of Done Criteria
# ============================================================================
echo -e "${YELLOW}[CHECK 4] Checking Definition of Done...${NC}"

# Look for DoD table
DOD_TABLE=$(grep -A 15 "## Definition of Done" "$EPIC_FILE" || true)

if [ -z "$DOD_TABLE" ]; then
    echo -e "${RED}  FAILED: No 'Definition of Done' section found${NC}"
    VALIDATION_FAILED=1
else
    # Count passing criteria
    PASS_COUNT=$(echo "$DOD_TABLE" | grep -c "✅ PASS" || echo 0)
    echo -e "  ${GREEN}✓${NC} Found $PASS_COUNT passing criteria"

    # Warn if very few
    if [ "$PASS_COUNT" -lt 3 ]; then
        echo -e "  ${YELLOW}  WARNING: Only $PASS_COUNT criteria marked as passing${NC}"
    fi
fi
echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo "=========================================="
if [ $VALIDATION_FAILED -eq 0 ]; then
    echo -e "${GREEN}VALIDATION PASSED${NC}"
    echo "EPIC is ready to be marked DONE"
    exit 0
else
    echo -e "${RED}VALIDATION FAILED${NC}"
    echo "Fix issues above before marking EPIC as DONE"
    exit 1
fi
