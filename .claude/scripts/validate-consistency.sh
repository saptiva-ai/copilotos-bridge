#!/usr/bin/env bash
#
# validate-consistency.sh - Validate Claude Code configuration consistency
#
# Checks:
#   1. Agents in delegation-matrix.md exist in .claude/agents/
#   2. Skills referenced in agents exist in .claude/skills/
#   3. Commands referenced in do.md exist in .claude/commands/
#   4. Hooks referenced in settings.json exist in .claude/hooks/
#   5. Agent definitions have required fields
#
# Usage:
#   validate-consistency.sh [--fix] [--quiet]
#
# Options:
#   --fix     Attempt to fix issues (move missing to parking, etc.)
#   --quiet   Only output errors, no info messages
#   --json    Output results as JSON
#
# Exit codes:
#   0 - All validations passed
#   1 - Validation errors found
#   2 - Script error (missing files, etc.)
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_ROOT="${SCRIPT_DIR}/.."
AGENTS_DIR="${CLAUDE_ROOT}/agents"
SKILLS_DIR="${CLAUDE_ROOT}/skills"
COMMANDS_DIR="${CLAUDE_ROOT}/commands"
HOOKS_DIR="${CLAUDE_ROOT}/hooks"
PARKING_DIR="${CLAUDE_ROOT}/agents_parking"
DELEGATION_MATRIX="${CLAUDE_ROOT}/skills/orchestration-playbooks/delegation-matrix.md"
DO_COMMAND="${CLAUDE_ROOT}/commands/do.md"
SETTINGS_FILE="${CLAUDE_ROOT}/settings.json"

# Options
FIX_MODE=false
QUIET_MODE=false
JSON_MODE=false

# Counters
ERRORS=0
WARNINGS=0
PASSED=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
for arg in "$@"; do
    case $arg in
        --fix)
            FIX_MODE=true
            ;;
        --quiet|-q)
            QUIET_MODE=true
            ;;
        --json)
            JSON_MODE=true
            QUIET_MODE=true
            ;;
        --help|-h)
            head -30 "$0" | tail -25
            exit 0
            ;;
    esac
done

# Logging functions
log_info() {
    if [[ "$QUIET_MODE" == "false" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_pass() {
    PASSED=$((PASSED + 1))
    if [[ "$QUIET_MODE" == "false" ]]; then
        echo -e "${GREEN}[PASS]${NC} $1"
    fi
}

log_warn() {
    WARNINGS=$((WARNINGS + 1))
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_error() {
    ERRORS=$((ERRORS + 1))
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_section() {
    if [[ "$QUIET_MODE" == "false" ]]; then
        echo ""
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}  $1${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    fi
}

# ============================================================================
# VALIDATION 1: Agents in delegation-matrix exist
# ============================================================================
validate_delegation_matrix_agents() {
    log_section "Validating Delegation Matrix Agents"

    if [[ ! -f "$DELEGATION_MATRIX" ]]; then
        log_warn "Delegation matrix not found: $DELEGATION_MATRIX"
        return
    fi

    # Extract agent names from delegation-matrix.md (looking for patterns like `agent-name`)
    local agents_referenced
    agents_referenced=$(grep -o '`[a-z-]*`' "$DELEGATION_MATRIX" 2>/dev/null | tr -d '`' | grep -E '^[a-z]+-[a-z]+' | sort -u || true)

    if [[ -z "$agents_referenced" ]]; then
        log_info "No agents found in delegation matrix"
        return
    fi

    for agent in $agents_referenced; do
        local agent_file="${AGENTS_DIR}/${agent}.md"
        local parked_file="${PARKING_DIR}/${agent}.md"

        if [[ -f "$agent_file" ]]; then
            log_pass "Agent exists: $agent"
        elif [[ -f "$parked_file" ]]; then
            log_warn "Agent is parked but still referenced: $agent"
        else
            log_error "Agent missing: $agent (referenced in delegation-matrix.md)"
        fi
    done
}

# ============================================================================
# VALIDATION 2: Skills referenced in agents exist
# ============================================================================
validate_agent_skills() {
    log_section "Validating Agent Skills References"

    if [[ ! -d "$AGENTS_DIR" ]]; then
        log_warn "Agents directory not found: $AGENTS_DIR"
        return
    fi

    for agent_file in "$AGENTS_DIR"/*.md; do
        [[ -f "$agent_file" ]] || continue

        local agent_name
        agent_name=$(basename "$agent_file" .md)

        # Extract skills from YAML frontmatter (skills: [skill1, skill2])
        local skills_line
        skills_line=$(grep -E '^skills:' "$agent_file" 2>/dev/null | head -1 || true)

        if [[ -z "$skills_line" ]]; then
            continue
        fi

        # Parse skills list (handle both [skill1, skill2] and - skill formats)
        local skills
        skills=$(echo "$skills_line" | sed 's/skills:\s*\[//; s/\]//; s/,/ /g; s/"//g; s/'"'"'//g' | tr -s ' ')

        for skill in $skills; do
            [[ -z "$skill" ]] && continue
            [[ "$skill" == "[]" ]] && continue

            local skill_dir="${SKILLS_DIR}/${skill}"
            local skill_file="${skill_dir}/SKILL.md"

            if [[ -d "$skill_dir" ]] && [[ -f "$skill_file" ]]; then
                log_pass "Skill exists: $skill (used by $agent_name)"
            elif [[ -d "$skill_dir" ]]; then
                log_warn "Skill directory exists but missing SKILL.md: $skill"
            else
                log_error "Skill missing: $skill (referenced by $agent_name)"
            fi
        done
    done
}

# ============================================================================
# VALIDATION 3: Commands in do.md exist
# ============================================================================
validate_do_commands() {
    log_section "Validating /do Command References"

    if [[ ! -f "$DO_COMMAND" ]]; then
        log_warn "do.md not found: $DO_COMMAND"
        return
    fi

    # Extract command references like /plan, /test, /review, etc.
    local commands_referenced
    commands_referenced=$(grep -oE '/[a-z]+-?[a-z]*' "$DO_COMMAND" 2>/dev/null | tr -d '/' | sort -u || true)

    for cmd in $commands_referenced; do
        [[ -z "$cmd" ]] && continue
        [[ "$cmd" == "do" ]] && continue  # Skip self-reference

        local cmd_file="${COMMANDS_DIR}/${cmd}.md"

        if [[ -f "$cmd_file" ]]; then
            log_pass "Command exists: /$cmd"
        else
            # Check if it's a built-in command or known non-command reference
            case "$cmd" in
                # Built-in CLI commands
                help|clear|config|model|compact|memory|doctor|permissions|mcp)
                    log_info "Built-in command: /$cmd"
                    ;;
                # File/directory path fragments (not commands)
                skills|rules|agents|commands|hooks|scripts|orchestration-playbooks|delegation-matrix)
                    # These are path references, not commands - skip silently
                    ;;
                # Text fragments from documentation
                fails|claude|prd|docs)
                    # Common words that appear after / in docs - skip silently
                    ;;
                *)
                    log_error "Command missing: /$cmd (referenced in do.md)"
                    ;;
            esac
        fi
    done
}

# ============================================================================
# VALIDATION 4: Hooks in settings.json exist
# ============================================================================
validate_hooks() {
    log_section "Validating Hook Files"

    if [[ ! -f "$SETTINGS_FILE" ]]; then
        log_warn "Settings file not found: $SETTINGS_FILE"
        return
    fi

    # Extract hook commands from settings.json
    local hooks
    hooks=$(grep -oE '"command":\s*"[^"]+\.sh"' "$SETTINGS_FILE" 2>/dev/null | sed 's/"command":\s*"//; s/"$//' || true)

    for hook in $hooks; do
        [[ -z "$hook" ]] && continue

        # Resolve relative path
        local hook_path
        if [[ "$hook" == ./* ]]; then
            hook_path="${CLAUDE_ROOT}/../${hook#./}"
        else
            hook_path="${CLAUDE_ROOT}/../${hook}"
        fi

        if [[ -f "$hook_path" ]]; then
            if [[ -x "$hook_path" ]]; then
                log_pass "Hook exists and executable: $hook"
            else
                log_warn "Hook exists but not executable: $hook"
            fi
        else
            log_error "Hook missing: $hook"
        fi
    done
}

# ============================================================================
# VALIDATION 5: Agent YAML frontmatter has required fields
# ============================================================================
validate_agent_structure() {
    log_section "Validating Agent Structure"

    local required_fields=("name" "description" "model" "tools")

    for agent_file in "$AGENTS_DIR"/*.md; do
        [[ -f "$agent_file" ]] || continue

        local agent_name
        agent_name=$(basename "$agent_file" .md)
        local missing_fields=()

        for field in "${required_fields[@]}"; do
            if ! grep -qE "^${field}:" "$agent_file" 2>/dev/null; then
                missing_fields+=("$field")
            fi
        done

        if [[ ${#missing_fields[@]} -eq 0 ]]; then
            log_pass "Agent structure valid: $agent_name"
        else
            log_error "Agent missing fields: $agent_name (missing: ${missing_fields[*]})"
        fi
    done
}

# ============================================================================
# VALIDATION 6: Check for orphaned agents (in agents/ but not in delegation-matrix)
# ============================================================================
validate_orphaned_agents() {
    log_section "Checking for Orphaned Agents"

    if [[ ! -f "$DELEGATION_MATRIX" ]]; then
        log_info "Skipping orphan check (no delegation matrix)"
        return
    fi

    for agent_file in "$AGENTS_DIR"/*.md; do
        [[ -f "$agent_file" ]] || continue

        local agent_name
        agent_name=$(basename "$agent_file" .md)

        if grep -q "\`${agent_name}\`" "$DELEGATION_MATRIX" 2>/dev/null; then
            log_pass "Agent in matrix: $agent_name"
        else
            log_warn "Orphaned agent (not in delegation-matrix): $agent_name"
        fi
    done
}

# ============================================================================
# MAIN
# ============================================================================

log_info "Claude Code Configuration Validator"
log_info "Root: $CLAUDE_ROOT"

# Run all validations
validate_delegation_matrix_agents
validate_agent_skills
validate_do_commands
validate_hooks
validate_agent_structure
validate_orphaned_agents

# Summary
log_section "Validation Summary"

echo ""
echo -e "  ${GREEN}Passed:${NC}   $PASSED"
echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "  ${RED}Errors:${NC}   $ERRORS"
echo ""

# JSON output
if [[ "$JSON_MODE" == "true" ]]; then
    cat << EOF
{
  "passed": $PASSED,
  "warnings": $WARNINGS,
  "errors": $ERRORS,
  "status": "$([ $ERRORS -eq 0 ] && echo "pass" || echo "fail")"
}
EOF
fi

# Exit with appropriate code
if [[ $ERRORS -gt 0 ]]; then
    log_error "Validation failed with $ERRORS error(s)"
    exit 1
else
    log_pass "All validations passed!"
    exit 0
fi
