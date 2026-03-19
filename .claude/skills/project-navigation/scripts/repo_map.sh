#!/usr/bin/env bash
################################################################################
# repo_map.sh - Generate repository structure map
#
# Creates a quick overview of the repository structure for Claude Code.
# Reads configuration from .claude/.env.claude for compose detection.
#
# Usage: repo_map.sh
# Output: Markdown to stdout (redirect to file as needed)
################################################################################
set -euo pipefail

root_dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root_dir"

# Load env
env_file=".claude/.env.claude"
COMPOSE_FILE=""
if [[ -f "$env_file" ]]; then
  COMPOSE_FILE=$(grep "^COMPOSE_FILE=" "$env_file" | cut -d= -f2 | tr -d '"' || true)
fi

search_cmd="rg -n"
if ! command -v rg >/dev/null 2>&1; then
  search_cmd="grep -n"
fi

echo "== Repo tree (depth 3, dirs only) =="
if command -v tree >/dev/null 2>&1; then
  tree -L 3 -d 2>/dev/null || find . -maxdepth 3 -type d -print
else
  find . -maxdepth 3 -type d -print 2>/dev/null | head -100
fi

echo
echo "== Doc index entrypoint (CLAUDE.md) =="
$search_cmd "Index:" CLAUDE.md 2>/dev/null || echo "(no Index section found)"

echo
echo "== Key entrypoints (presence check) =="
for path in \
  "CLAUDE.md" \
  ".claude/skills/explore/SKILL.md" \
  ".claude/skills/plan/SKILL.md" \
  ".claude/skills/code/SKILL.md" \
  ".claude/skills/test/SKILL.md" \
  ".claude/skills/kanban/SKILL.md" \
  "docs/context/project/SPRINT_CURRENT.md" \
  "docs/context/code/PATTERNS.md" \
  "docs/kanban/TEMPLATE_TASK_FOLDER/card.md" \
  "Makefile" \
  "package.json"
do
  if [[ -f "$path" ]]; then
    echo "$path"
  else
    echo "MISSING: $path"
  fi
done

echo
echo "== Claude Code config =="
for path in \
  ".claude/settings.json" \
  ".claude/commands" \
  ".claude/agents" \
  ".claude/rules" \
  ".claude/skills"
do
  if [[ -e "$path" ]]; then
    echo "$path"
  else
    echo "MISSING: $path"
  fi
done

if [[ -d ".claude/commands" ]]; then
  echo ""
  echo "Commands:"
  find .claude/commands -maxdepth 1 -type f -name "*.md" 2>/dev/null | sort
fi

if [[ -d ".claude/agents" ]]; then
  echo ""
  echo "Agents:"
  find .claude/agents -maxdepth 1 -type f -name "*.md" 2>/dev/null | sort
fi

if [[ -d ".claude/skills" ]]; then
  echo ""
  echo "Skills:"
  find .claude/skills -maxdepth 2 -name "SKILL.md" 2>/dev/null | sort
fi

echo
echo "== Tooling files =="
if command -v rg >/dev/null 2>&1; then
  rg --files -g 'Makefile' -g 'package.json' -g 'pnpm-lock.yaml' -g 'pnpm-workspace.yaml' -g 'pyproject.toml' -g 'requirements*.txt' 2>/dev/null | head -30
else
  find . -maxdepth 4 -type f \( -name "Makefile" -o -name "package.json" -o -name "pyproject.toml" -o -name "requirements*.txt" \) 2>/dev/null | head -30
fi

echo
echo "== Compose services =="
if [[ -n "$COMPOSE_FILE" ]] && [[ -f "$COMPOSE_FILE" ]]; then
  echo "Compose file: $COMPOSE_FILE"
  docker compose -f "$COMPOSE_FILE" config --services 2>/dev/null || echo "(docker compose unavailable)"
else
  echo "(no compose file detected)"
fi
