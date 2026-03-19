---
name: test
description: Run tests (api, web, e2e, or specific file).
argument-hint: "[api|web|e2e|FILE=path/to/test.py]"
allowed-tools: [Bash]
disable-model-invocation: true
---

!bash
set -euo pipefail

target="${1:-api}"

# Preflight check
if ! ./.claude/hooks/preflight.sh; then
  echo "preflight failed; start services with make dev or /dev-up --start" >&2
  exit 2
fi

# Load env for compose file
COMPOSE_FILE=$(grep "^COMPOSE_FILE=" .claude/.env.claude | cut -d= -f2 | tr -d '"') || echo "infra/docker-compose.yml"
BACKEND_SVC="backend"
WEB_SVC="web"

case "$target" in
  api)
    echo "Running API tests..."
    make test T=api
    ;;
  web)
    echo "Running Web tests..."
    make test T=web
    ;;
  e2e)
    echo "Running E2E tests..."
    RUN_E2E=1 ./.claude/skills/project-navigation/scripts/quick_checks.sh
    ;;
  FILE=*)
    file="${target#FILE=}"
    echo "Running tests for: $file"
    if [[ "$file" == *.py ]]; then
      echo "Detected Backend Python test"
      # Run inside backend container
      docker compose -f $COMPOSE_FILE exec -T $BACKEND_SVC pytest "$file" -v
    elif [[ "$file" == *.ts || "$file" == *.tsx || "$file" == *.js ]]; then
      echo "Detected Frontend Web test"
      # Run inside web container
      docker compose -f $COMPOSE_FILE exec -T $WEB_SVC npm test -- "$file"
    else
      echo "Unknown file type: $file" >&2
      exit 1
    fi
    ;;
  *)
    echo "Usage: /test [api|web|e2e|FILE=path/to/test]"
    echo ""
    echo "Examples:"
    echo "  /test api                    - Run all backend tests"
    echo "  /test web                    - Run all frontend tests"
    echo "  /test e2e                    - Run E2E tests"
    echo "  /test FILE=tests/unit/test_chat.py - Run specific test file (in Docker)"
    exit 1
    ;;
esac