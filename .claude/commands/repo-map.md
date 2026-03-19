---
name: repo-map
description: Regenerate repo map output and save to .claude/docs/repo_map.md.
argument-hint: ""
allowed-tools: [Bash, Read]
---

!bash
set -euo pipefail

mkdir -p .claude/output
./.claude/skills/project-navigation/scripts/repo_map.sh | tee .claude/docs/repo_map.md
