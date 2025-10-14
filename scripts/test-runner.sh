#!/usr/bin/env bash
# Unified runner for shell-based tests

set -euo pipefail
IFS=$'\n\t'
shopt -s nullglob

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$ROOT_DIR/scripts:$PATH"

: "${TEST_GLOB:=scripts/tests/**/*test*.sh}"
: "${STOP_ON_FAIL:=true}"

echo "[runner] collecting tests from: $TEST_GLOB"

passed=0
failed=0

for test_script in $TEST_GLOB; do
  if [[ -f "$test_script" && -x "$test_script" ]]; then
    echo "──▶ $test_script"
    if bash "$test_script"; then
      ((passed++)) || true
    else
      ((failed++)) || true
      echo "✗ FAILED: $test_script"
      if [[ "$STOP_ON_FAIL" == "true" ]]; then
        exit 1
      fi
    fi
  fi
done

echo "[runner] passed=$passed failed=$failed"

if [[ $failed -ne 0 ]]; then
  exit 1
fi
