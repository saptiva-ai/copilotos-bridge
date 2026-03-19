#!/usr/bin/env bash
################################################################################
# post_edit.sh - Post-edit formatting hook with observability
#
# Improvements over original:
#   - Errors are logged to .claude/logs/hook_errors.log instead of being hidden
#   - Each tool failure is captured with exit code and stderr
#   - Summary reported at end
#   - Metrics integration for observability
#
# Environment Variables:
#   CLAUDE_SKIP_FORMAT=1    - Skip all formatting
#   CLAUDE_STRICT_FORMAT=1  - Fail on any formatting error (default: 0)
#   CLAUDE_FORMAT_VERBOSE=1 - Show detailed output (default: 0)
################################################################################
set -euo pipefail

root_dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root_dir"

# Configuration
LOGS_DIR="${root_dir}/.claude/logs"
ERROR_LOG="${LOGS_DIR}/hook_errors.log"
METRICS_SCRIPT="${root_dir}/.claude/scripts/log-metrics.sh"
STRICT_MODE="${CLAUDE_STRICT_FORMAT:-0}"
VERBOSE="${CLAUDE_FORMAT_VERBOSE:-0}"

# Ensure logs directory exists
mkdir -p "$LOGS_DIR"

# Counters
TOOLS_RUN=0
TOOLS_SUCCESS=0
TOOLS_FAILED=0
TOOLS_SKIPPED=0

# Log function
log_error() {
    local tool="$1"
    local message="$2"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "[$timestamp] [post_edit] [$tool] $message" >> "$ERROR_LOG"
    echo "post_edit: $tool failed - $message" >&2
    ((TOOLS_FAILED++))
}

log_success() {
    local tool="$1"
    local count="$2"
    ((TOOLS_SUCCESS++))
    if [[ "$VERBOSE" == "1" ]]; then
        echo "post_edit: $tool processed $count file(s)" >&2
    fi
}

log_skip() {
    local tool="$1"
    local reason="$2"
    ((TOOLS_SKIPPED++))
    echo "post_edit: $tool skipped ($reason)" >&2
}

# Run a formatter tool with error capture
run_formatter() {
    local tool_name="$1"
    local tool_cmd="$2"
    shift 2
    local files=("$@")

    if [[ ${#files[@]} -eq 0 ]]; then
        return 0
    fi

    ((TOOLS_RUN++))

    local stderr_file
    stderr_file=$(mktemp)
    local exit_code=0

    if "$tool_cmd" "${files[@]}" 2>"$stderr_file"; then
        log_success "$tool_name" "${#files[@]}"
    else
        exit_code=$?
        local stderr_content
        stderr_content=$(cat "$stderr_file" 2>/dev/null || echo "No stderr captured")
        log_error "$tool_name" "Exit code $exit_code: $stderr_content"
    fi

    rm -f "$stderr_file"
    return 0  # Don't fail the hook unless strict mode
}

# Skip if formatting disabled
if [[ "${CLAUDE_SKIP_FORMAT:-0}" == "1" ]]; then
    echo "post_edit: formatting skipped (CLAUDE_SKIP_FORMAT=1)" >&2
    exit 0
fi

# Detect changed files
changed_files="${CLAUDE_CHANGED_FILES:-}"
if [[ -z "$changed_files" ]] && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    changed_files=$(git diff --name-only --diff-filter=ACMRT 2>/dev/null || true)
fi

if [[ -z "$changed_files" ]]; then
    echo "post_edit: no changed files detected" >&2
    exit 0
fi

# Categorize files
py_files=()
js_files=()
prettier_files=()

while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    [[ ! -f "$file" ]] && continue  # Skip if file doesn't exist

    case "$file" in
        apps/*|packages/*|plugins/*)
            case "$file" in
                *.py)
                    py_files+=("$file")
                    ;;
                *.ts|*.tsx|*.js|*.jsx)
                    js_files+=("$file")
                    prettier_files+=("$file")
                    ;;
                *.json|*.md|*.css|*.scss|*.yml|*.yaml)
                    prettier_files+=("$file")
                    ;;
            esac
            ;;
        *)
            ;;
    esac
done <<< "$changed_files"

# ============================================================================
# Python formatting (isort + black)
# ============================================================================
if [[ ${#py_files[@]} -gt 0 ]]; then
    # Only use venv binaries to avoid system conflicts
    isort_cmd=""
    black_cmd=""

    if [[ -x "apps/backend/.venv/bin/isort" ]]; then
        isort_cmd="apps/backend/.venv/bin/isort"
    fi
    if [[ -x "apps/backend/.venv/bin/black" ]]; then
        black_cmd="apps/backend/.venv/bin/black"
    fi

    if [[ -n "$isort_cmd" ]]; then
        run_formatter "isort" "$isort_cmd" "${py_files[@]}"
    else
        log_skip "isort" "not in venv"
    fi

    if [[ -n "$black_cmd" ]]; then
        run_formatter "black" "$black_cmd" "${py_files[@]}"
    else
        log_skip "black" "not in venv"
    fi
fi

# ============================================================================
# JavaScript/TypeScript linting (eslint)
# ============================================================================
if [[ ${#js_files[@]} -gt 0 ]]; then
    eslint_bin="apps/web/node_modules/.bin/eslint"
    if [[ -x "$eslint_bin" ]]; then
        run_formatter "eslint" "$eslint_bin" "--fix" "${js_files[@]}"
    else
        log_skip "eslint" "not installed"
    fi
fi

# ============================================================================
# Prettier formatting
# ============================================================================
if [[ ${#prettier_files[@]} -gt 0 ]]; then
    prettier_bin="apps/web/node_modules/.bin/prettier"
    if [[ -x "$prettier_bin" ]]; then
        run_formatter "prettier" "$prettier_bin" "--write" "${prettier_files[@]}"
    else
        log_skip "prettier" "not installed"
    fi
fi

# ============================================================================
# Summary
# ============================================================================
echo "post_edit: completed (success: $TOOLS_SUCCESS, failed: $TOOLS_FAILED, skipped: $TOOLS_SKIPPED)" >&2

# Log metrics if available
if [[ -x "$METRICS_SCRIPT" ]]; then
    "$METRICS_SCRIPT" hook_exec \
        "hook=post_edit" \
        "tools_run=$TOOLS_RUN" \
        "tools_success=$TOOLS_SUCCESS" \
        "tools_failed=$TOOLS_FAILED" \
        "tools_skipped=$TOOLS_SKIPPED" \
        2>/dev/null || true
fi

# Strict mode: fail if any tool failed
if [[ "$STRICT_MODE" == "1" ]] && [[ $TOOLS_FAILED -gt 0 ]]; then
    echo "post_edit: STRICT MODE - failing due to $TOOLS_FAILED error(s)" >&2
    echo "post_edit: See $ERROR_LOG for details" >&2
    exit 1
fi

exit 0
