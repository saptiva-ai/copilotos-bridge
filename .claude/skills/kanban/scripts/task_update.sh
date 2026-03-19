#!/usr/bin/env bash
################################################################################
# task_update.sh - Update task status/owner (Frontmatter V2)
#
# Updates YAML frontmatter. Moves file to 'done/' ONLY if status becomes DONE.
#
# Usage: task_update.sh <TASK_ID> <STATUS> [OWNER]
#
# Arguments:
#   $1 - Task ID (e.g., T-20251231T142305-001)
#   $2 - New status: TODO, IN_PROGRESS, TESTING, DOCS, DONE
#   $3 - Owner (optional, e.g., "software-developer")
#
################################################################################
set -euo pipefail

root_dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root_dir"

KANBAN_ROOT="docs/kanban"

# Validate arguments
if [[ $# -lt 2 ]]; then
  echo "Usage: task_update.sh <TASK_ID> <STATUS> [OWNER]" >&2
  exit 1
fi

task_id="$1"
new_status="$2"
owner="${3:-}"

# Validate status
case "$new_status" in
  TODO|IN_PROGRESS|TESTING|DOCS|DONE) ;;
  *) 
    echo "Invalid status: $new_status (use TODO, IN_PROGRESS, TESTING, DOCS, DONE)" >&2
    exit 1
    ;;
esac

# Find current task file
current_file=""
if [[ -f "$KANBAN_ROOT/doing/${task_id}.md" ]]; then
  current_file="$KANBAN_ROOT/doing/${task_id}.md"
elif [[ -f "$KANBAN_ROOT/done/${task_id}.md" ]]; then
  current_file="$KANBAN_ROOT/done/${task_id}.md"
fi

if [[ -z "$current_file" ]]; then
  echo "Task not found: $task_id" >&2
  exit 2
fi

# Update YAML Frontmatter using a temporary file
tmp_file=$(mktemp)
awk -v status="$new_status" -v owner="$owner" '
  BEGIN { in_frontmatter=0 }
  /^---$/ {
    in_frontmatter = !in_frontmatter;
    print;
    next;
  }
  in_frontmatter && /^status:/ {
    print "status: \"" status "\"";
    next;
  }
  in_frontmatter && /^owner:/ {
    if (owner != "") {
      print "owner: \"" owner "\"";
    } else {
      print;
    }
    next;
  }
  { print }
' "$current_file" > "$tmp_file"

mv "$tmp_file" "$current_file"

# Handle File Movement
if [[ "$new_status" == "DONE" ]] && [[ "$current_file" == *"/doing/"* ]]; then
  mv "$current_file" "$KANBAN_ROOT/done/${task_id}.md"
  echo "Moved $task_id to done/"
elif [[ "$new_status" != "DONE" ]] && [[ "$current_file" == *"/done/"* ]]; then
  mv "$current_file" "$KANBAN_ROOT/doing/${task_id}.md"
  echo "Reopened $task_id to doing/"
else
  echo "Updated $task_id status to $new_status"
fi
