#!/usr/bin/env bash
################################################################################
# task_list.sh - List kanban tasks (Frontmatter V2)
#
# Lists tasks grouped by status.
#
# Usage: task_list.sh [STATUS_FILTER]
#
################################################################################
set -euo pipefail

root_dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root_dir"

KANBAN_ROOT="docs/kanban"

# Helper to extract YAML field
get_yaml() {
  local file="$1"
  local key="$2"
  # Extract value inside frontmatter
  awk -v key="$key" '
    BEGIN { in_fm=0 }
    /^---$/ { in_fm=!in_fm; next }
    in_fm && $1 == key":" { 
      $1=""; 
      gsub(/^ +| +$|"/, "", $0); 
      print $0; 
      exit 
    }
  ' "$file"
}

# List all tasks in doing/
echo "# Kanban Board (Active)"
echo ""
echo "| ID | Status | Owner | Title |"
echo "|----|--------|-------|-------|"

for file in "$KANBAN_ROOT/doing/"*.md; do
  [[ -e "$file" ]] || continue
  id=$(basename "$file" .md)
  status=$(get_yaml "$file" "status")
  owner=$(get_yaml "$file" "owner")
  title=$(get_yaml "$file" "title")
  
  echo "| $id | $status | ${owner:--} | $title |"
done