#!/usr/bin/env bash
################################################################################
# pre_push_checks.sh - Run ruff lint + unit tests before git push / gh pr create
#
# Called as a PreToolUse hook. Receives JSON on stdin with tool_input.
# Exit 0 = allow, Exit 2 = block with message on stderr.
################################################################################
set -euo pipefail

root_dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root_dir"

# ============================================================================
# 1. Ruff check (lint only, no format — format is checked separately by CI)
# ============================================================================
echo "🔍 Running ruff check on backend..." >&2

if ! python3.11 -m ruff check apps/backend/src/ 2>&1; then
  echo "" >&2
  echo "❌ ruff check failed. Fix lint errors before pushing." >&2
  exit 2
fi

if ! python3.11 -m ruff format --check apps/backend/src/ 2>&1; then
  echo "" >&2
  echo "❌ ruff format check failed. Run: cd apps/backend && python3.11 -m ruff format src/" >&2
  exit 2
fi

echo "✅ Ruff checks passed" >&2

# ============================================================================
# 2. Backend unit tests (fast subset — exclude e2e/benchmarks/integration)
# ============================================================================
echo "🧪 Running backend unit tests..." >&2

if ! python3.11 -m pytest apps/backend/tests/unit/ \
    -x --timeout=60 -q --no-header --tb=short 2>&1; then
  echo "" >&2
  echo "❌ Unit tests failed. Fix failing tests before pushing." >&2
  exit 2
fi

echo "✅ Unit tests passed" >&2

# ============================================================================
# 3. Plugin unit tests
# ============================================================================
echo "🧪 Running plugin unit tests..." >&2

if ! python3.11 -m pytest plugins/bank-advisor-private/tests/unit/ \
    -x --timeout=60 -q --no-header --tb=short 2>&1; then
  echo "" >&2
  echo "❌ Plugin unit tests failed. Fix failing tests before pushing." >&2
  exit 2
fi

echo "✅ Plugin unit tests passed" >&2

echo "" >&2
echo "✅ All pre-push checks passed — proceeding." >&2
exit 0
