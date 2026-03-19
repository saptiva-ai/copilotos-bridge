#!/bin/bash
# .claude/scripts/phase_gate.sh
# Enforces proper phase transitions in agent workflow
# Exit codes: 0 = pass, 1 = fail

set -euo pipefail

PHASE="${1:-}"
TICKET="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    echo "Usage: $0 <phase> <ticket-id>"
    echo ""
    echo "Phases:"
    echo "  explore  - Check if exploration is complete before plan"
    echo "  plan     - Check if plan is approved before code"
    echo "  code     - Check if code phase is complete before test"
    echo "  test     - Check if tests pass before review"
    echo "  review   - Check if review is complete before docs"
    echo "  done     - Check if all phases complete before marking DONE"
    echo ""
    echo "Example:"
    echo "  $0 test T-20260102-feature"
    exit 1
}

if [ -z "$PHASE" ] || [ -z "$TICKET" ]; then
    usage
fi

KANBAN_DIR="$PROJECT_ROOT/docs/kanban"
TICKET_FILE=""

# Find ticket file in any kanban directory
for dir in doing todo done blocked; do
    if [ -f "$KANBAN_DIR/$dir/$TICKET.md" ]; then
        TICKET_FILE="$KANBAN_DIR/$dir/$TICKET.md"
        break
    fi
done

if [ -z "$TICKET_FILE" ]; then
    echo -e "${RED}ERROR: Ticket not found: $TICKET${NC}"
    echo "  Looked in: $KANBAN_DIR/{doing,todo,done,blocked}/"
    exit 1
fi

echo "=========================================="
echo "Phase Gate: $PHASE"
echo "=========================================="
echo "Ticket: $TICKET"
echo "File: $TICKET_FILE"
echo ""

# Extract value from YAML frontmatter (strips quotes/whitespace)
get_frontmatter_value() {
    local key="$1"
    awk -v key="$key" '
        BEGIN {in_frontmatter=0}
        /^---[[:space:]]*$/ {
            if (in_frontmatter == 0) { in_frontmatter = 1; next }
            exit
        }
        in_frontmatter == 1 && $0 ~ ("^" key ":[[:space:]]*") {
            line = $0
            sub("^[^:]+:[[:space:]]*", "", line)
            gsub(/^[ \t]+|[ \t]+$/, "", line)
            if (line ~ /^".*"$/) { sub(/^"/, "", line); sub(/"$/, "", line) }
            if (line ~ /^'\''.*'\''$/) { sub(/^'\''/, "", line); sub(/'\''$/, "", line) }
            print line
            exit
        }
    ' "$TICKET_FILE"
}

# Extract YAML frontmatter status
get_ticket_status() {
    local status
    status=$(get_frontmatter_value "status")
    if [ -z "$status" ]; then
        echo "UNKNOWN"
        return
    fi
    printf "%s" "$status" | tr '[:lower:]' '[:upper:]'
}

CURRENT_STATUS=$(get_ticket_status)
echo "Current Status: $CURRENT_STATUS"
echo ""

case $PHASE in
    "explore")
        echo -e "${YELLOW}[GATE] Checking exploration prerequisites...${NC}"

        # Check if ticket has epic linked
        if ! grep -q "^epic:" "$TICKET_FILE"; then
            echo -e "${RED}  ✗ No epic linked in ticket${NC}"
            echo "  Add 'epic: EPIC-HUx' to YAML frontmatter"
            exit 1
        fi

        echo -e "${GREEN}  ✓ Epic linked${NC}"
        echo -e "${GREEN}GATE PASSED: Ready for exploration${NC}"
        ;;

    "plan")
        echo -e "${YELLOW}[GATE] Checking plan prerequisites...${NC}"

        # Check if exploration was done (should have repo_map or context)
        if [ ! -f "$PROJECT_ROOT/.claude/docs/repo_map.md" ]; then
            echo -e "${YELLOW}  ⚠ No repo_map found (exploration may not have run)${NC}"
        else
            echo -e "${GREEN}  ✓ Exploration context exists${NC}"
        fi

        # Status should be TODO or EXPLORATION
        if [ "$CURRENT_STATUS" != "TODO" ] && [ "$CURRENT_STATUS" != "EXPLORATION" ]; then
            echo -e "${YELLOW}  ⚠ Status is $CURRENT_STATUS (expected TODO or EXPLORATION)${NC}"
        fi

        echo -e "${GREEN}GATE PASSED: Ready for planning${NC}"
        ;;

    "code")
        echo -e "${YELLOW}[GATE] Checking code prerequisites...${NC}"

        # Check if plan exists (linked in ticket or as file)
        if ! grep -q "plan:" "$TICKET_FILE"; then
            echo -e "${YELLOW}  ⚠ No plan linked in ticket${NC}"
            echo "  Recommended: Link plan file in YAML frontmatter"
        else
            echo -e "${GREEN}  ✓ Plan linked${NC}"
        fi

        # Status should indicate planning is complete
        if [ "$CURRENT_STATUS" == "TODO" ]; then
            echo -e "${RED}  ✗ Status is still TODO (plan not approved)${NC}"
            exit 1
        fi

        echo -e "${GREEN}GATE PASSED: Ready for implementation${NC}"
        ;;

    "test")
        echo -e "${YELLOW}[GATE] Checking test prerequisites...${NC}"

        # Status must be TESTING or IN_PROGRESS
        if [ "$CURRENT_STATUS" != "TESTING" ] && [ "$CURRENT_STATUS" != "IN_PROGRESS" ]; then
            echo -e "${RED}  ✗ Status is $CURRENT_STATUS (expected TESTING or IN_PROGRESS)${NC}"
            echo "  Update status to TESTING before running tests"
            exit 1
        fi

        # Check if pr_files are listed (code was written)
        if ! grep -q "pr_files:" "$TICKET_FILE"; then
            echo -e "${RED}  ✗ No pr_files listed in ticket${NC}"
            echo "  Add 'pr_files: [list]' to YAML frontmatter"
            exit 1
        fi

        echo -e "${GREEN}  ✓ Code phase complete${NC}"
        echo -e "${GREEN}GATE PASSED: Ready for testing${NC}"
        ;;

    "review")
        echo -e "${YELLOW}[GATE] Checking review prerequisites...${NC}"

        # Status must be TESTING (tests passed)
        if [ "$CURRENT_STATUS" != "TESTING" ]; then
            echo -e "${RED}  ✗ Status is $CURRENT_STATUS (expected TESTING)${NC}"
            echo "  Tests must pass before review"
            exit 1
        fi

        # Check if test evidence exists (could be test output file)
        echo -e "${GREEN}  ✓ Test phase complete${NC}"
        echo -e "${GREEN}GATE PASSED: Ready for review${NC}"
        ;;

    "done")
        echo -e "${YELLOW}[GATE] Checking completion prerequisites...${NC}"

        GATE_FAILED=0

        # Must have pr_files
        if ! grep -q "pr_files:" "$TICKET_FILE"; then
            echo -e "${RED}  ✗ No pr_files listed${NC}"
            GATE_FAILED=1
        else
            echo -e "${GREEN}  ✓ Code changes documented${NC}"
        fi

        # Status must be REVIEW or TESTING
        if [ "$CURRENT_STATUS" != "REVIEW" ] && [ "$CURRENT_STATUS" != "TESTING" ]; then
            echo -e "${RED}  ✗ Status is $CURRENT_STATUS (expected REVIEW or TESTING)${NC}"
            GATE_FAILED=1
        else
            echo -e "${GREEN}  ✓ Review/Test phase complete${NC}"
        fi

        # Check if linked to EPIC
        EPIC=$(get_frontmatter_value "epic")
        if [ -n "$EPIC" ]; then
            EPIC_FILE="$PROJECT_ROOT/docs/context/product/EPICS/$EPIC.md"
            if [ -f "$EPIC_FILE" ]; then
                echo -e "${GREEN}  ✓ EPIC exists: $EPIC${NC}"

                # Run EPIC validation if it exists
                if [ -x "$SCRIPT_DIR/validate_epic.sh" ]; then
                    echo ""
                    echo -e "${YELLOW}  Running EPIC validation...${NC}"
                    if "$SCRIPT_DIR/validate_epic.sh" "$EPIC_FILE"; then
                        echo -e "${GREEN}  ✓ EPIC validation passed${NC}"
                    else
                        echo -e "${RED}  ✗ EPIC validation failed${NC}"
                        GATE_FAILED=1
                    fi
                fi
            else
                echo -e "${YELLOW}  ⚠ EPIC file not found: $EPIC_FILE${NC}"
            fi
        fi

        if [ $GATE_FAILED -eq 1 ]; then
            echo ""
            echo -e "${RED}GATE FAILED: Cannot mark as DONE${NC}"
            exit 1
        fi

        echo ""
        echo -e "${GREEN}GATE PASSED: Ready to mark as DONE${NC}"
        ;;

    *)
        echo -e "${RED}ERROR: Unknown phase: $PHASE${NC}"
        usage
        ;;
esac

exit 0
