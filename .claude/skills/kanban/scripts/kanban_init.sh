#!/usr/bin/env bash
################################################################################
# kanban_init.sh - Initialize kanban directory structure
#
# Creates the kanban directory structure if it doesn't exist.
# Safe to run multiple times (idempotent).
#
# Usage: kanban_init.sh
################################################################################
set -euo pipefail

root_dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root_dir"

# Load KANBAN_ROOT from env
env_file=".claude/.env.claude"
KANBAN_ROOT="docs/kanban"
if [[ -f "$env_file" ]]; then
  val=$(grep "^KANBAN_ROOT=" "$env_file" | cut -d= -f2 | tr -d '"' || true)
  if [[ -n "$val" ]]; then
    KANBAN_ROOT="$val"
  fi
fi

# Create directories
mkdir -p "$KANBAN_ROOT/BACKLOG"
mkdir -p "$KANBAN_ROOT/DOING"
mkdir -p "$KANBAN_ROOT/DONE"
mkdir -p "$KANBAN_ROOT/logs"

echo "Kanban initialized at: $KANBAN_ROOT"
echo ""
echo "Structure:"
echo "  $KANBAN_ROOT/"
echo "  ├── BACKLOG/"
echo "  ├── DOING/"
echo "  ├── DONE/"
echo "  └── logs/"
