#!/bin/sh
set -eu

usage() {
  echo "Usage: $0 ensure <COLUMN> <TASK_ID> [slug]" >&2
  echo "" >&2
  echo "Examples:" >&2
  echo "  $0 ensure DOING TASK-2026-01-02-1500 short-slug" >&2
  echo "  $0 ensure BACKLOG TASK-2026-01-02-1500__short-slug" >&2
  echo "" >&2
  echo "Optional env: KANBAN_ROOT (defaults to docs/kanban, falls back to docs/agent/kanban)" >&2
  exit 1
}

command=${1:-}
if [ "$command" != "ensure" ]; then
  usage
fi

column=${2:-}
task_id=${3:-}
slug=${4:-}

if [ -z "$column" ] || [ -z "$task_id" ]; then
  usage
fi

# Normalize column to uppercase
column=$(printf "%s" "$column" | tr '[:lower:]' '[:upper:]')

if [ -z "${KANBAN_ROOT:-}" ]; then
  KANBAN_ROOT="docs/kanban"
fi

if [ -z "$slug" ]; then
  case "$task_id" in
    *__*) task_folder_name="$task_id" ;;
    *) usage ;;
  esac
else
  task_folder_name="${task_id}__${slug}"
fi

task_dir="$KANBAN_ROOT/$column/$task_folder_name"

mkdir -p "$KANBAN_ROOT/$column"

if [ ! -d "$task_dir" ]; then
  mkdir -p "$task_dir"
  template_dir="$KANBAN_ROOT/TEMPLATE_TASK_FOLDER"
  if [ ! -d "$template_dir" ]; then
    template_dir="docs/kanban/TEMPLATE_TASK_FOLDER"
  fi
  if [ ! -d "$template_dir" ]; then
    echo "ERROR: template folder not found" >&2
    exit 1
  fi
  cp -R "$template_dir"/. "$task_dir"/
fi

card_file="$task_dir/card.md"
if [ -f "$card_file" ]; then
  tmp_file="$card_file.tmp"
  sed "s/TASK-YYYY-MM-DD-HHMM__slug/$task_folder_name/g" "$card_file" > "$tmp_file"
  mv "$tmp_file" "$card_file"
fi

echo "$task_dir"
