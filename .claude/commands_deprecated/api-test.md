---
name: api-test
description: Run API tests with API_SERVICE=backend.
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

API_SERVICE=backend make test T=api
