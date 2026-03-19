#!/usr/bin/env bash
################################################################################
# task_new.sh - Create a new kanban task (Frontmatter V2)
#
# Creates a task YAML file in 'doing/' with unique timestamp-based ID.
#
# Usage: task_new.sh "Task title" [P0|P1|P2|P3]
#
# Arguments:
#   $1 - Task title (required)
#   $2 - Priority: P0 (critical), P1 (high), P2 (medium), P3 (low) [default: P2]
#
# Output: Task ID to stdout
################################################################################
set -euo pipefail

root_dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root_dir"

# Load env
env_file=".claude/.env.claude"
KANBAN_ROOT="docs/kanban"
if [[ -f "$env_file" ]]; then
  val=$(grep "^KANBAN_ROOT=" "$env_file" | cut -d= -f2 | tr -d '"' || true)
  if [[ -n "$val" ]]; then
    KANBAN_ROOT="$val"
  fi
fi

# Validate arguments
if [[ $# -lt 1 ]]; then
  echo "Usage: task_new.sh \"Task title\" [P0|P1|P2|P3]" >&2
  exit 1
fi

title="$1"
priority="${2:-P2}"

# Validate priority
case "$priority" in
  P0|P1|P2|P3) ;;
  *)
    echo "Invalid priority: $priority (use P0, P1, P2, or P3)" >&2
    exit 1
    ;;
esac

# Generate unique task ID
# Format: T-YYYYMMDDTHHMMSS-###
timestamp=$(date -u +"%Y%m%dT%H%M%S")
timestamp_iso=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Find next counter for this second
counter=1
while [[ -f "$KANBAN_ROOT/doing/T-${timestamp}-$(printf '%03d' $counter).md" ]] || \
      [[ -f "$KANBAN_ROOT/done/T-${timestamp}-$(printf '%03d' $counter).md" ]]; do
  counter=$((counter + 1))
  if [[ $counter -gt 999 ]]; then
    echo "Too many tasks created in the same second" >&2
    exit 1
  fi
done

task_id="T-${timestamp}-$(printf '%03d' $counter)"
task_file="$KANBAN_ROOT/doing/${task_id}.md"

# Ensure directories exist
mkdir -p "$KANBAN_ROOT/doing"
mkdir -p "$KANBAN_ROOT/done"

# Create task YAML Frontmatter + Body
cat > "$task_file" <<EOF
---
id: "$task_id"
title: "$title"
priority: "$priority"
status: "TODO"
owner: "unassigned"
created: "$timestamp_iso"
epic: ""
cas: []
pr_files: []
test_status: "PENDING"
---

# Description
$title

# Plan
- [ ] Analyze requirements
- [ ] Implement changes
- [ ] Verify tests

# Notes
EOF

# Output task ID (for scripting)
echo "$task_id"