---
name: e2e
description: Run E2E tests via quick checks (RUN_E2E=1), ensuring the stack is up.
argument-hint: ""
allowed-tools: [Bash]
disable-model-invocation: true
---

!bash
set -euo pipefail

if ! ./.claude/hooks/preflight.sh; then
  echo "preflight failed; start services with make dev or /dev-up --start" >&2
  exit 2
fi

RUN_E2E=1 ./.claude/skills/project-navigation/scripts/quick_checks.sh
