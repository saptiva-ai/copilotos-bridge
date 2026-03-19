---
name: web-test
description: Run web tests with WEB_SERVICE=web.
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

WEB_SERVICE=web make test T=web
