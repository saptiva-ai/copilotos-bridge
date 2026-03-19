# Project Navigation Reference

## Ownership and entrypoints
- Entry points:
  - Backend: `apps/backend/src/main.py`
  - Frontend: `apps/web/src/app/layout.tsx`
  - File manager plugin: `plugins/public/file-manager/src/main.py`
  - Bank advisor plugin: `plugins/bank-advisor-private/src/main.py`
- Locate entrypoints quickly:
  - `rg --files -g 'apps/backend/src/main.py' -g 'apps/web/src/app/layout.tsx'`
  - `rg --files -g 'plugins/**/src/main.py'`
- Check ownership (if needed):
  - `rg --files -g 'CODEOWNERS' -g 'CODEOWNERS*'`
  - `git blame <file>` for recent authorship

## Configs and environment
- Environment files live under `envs/` and per-app `.env*` files.
- Docker-compose files live in `infra/`.
- Infra subdirs for ops/config: `infra/nginx/`, `infra/monitoring/`, `infra/observability/`.
- Claude Code settings live in `.claude/settings.json`.
- Session-safe env is written to `.claude/.env.claude` by `.claude/hooks/session_start.sh`.

## APIs, contracts, schema
- API routers and services:
  - `apps/backend/src/routers/` and `apps/backend/src/services/`
- Frontend UI contracts:
  - `apps/web/src/app/`, `apps/web/src/components/`, `apps/web/src/lib/`
- Data/schema artifacts:
  - `plugins/bank-advisor-private/schemas/`
- Test references:
  - `apps/backend/tests/`, `apps/web/__tests__/`, `packages/tests-e2e/tests/`

## Testing

### Docker Compose Location
- Compose file: `infra/docker-compose.yml`
- Project name: `octavios-chat-bajaware_invex`

### Service Name Mapping
The test runner maps test targets to compose services:
- `T=api` → `backend` service (override: `API_SERVICE=<name>`)
- `T=web` → `web` service (override: `WEB_SERVICE=<name>`)

### Running Tests
```bash
# Ensure services are running first
make dev

# Run API tests (uses 'backend' container)
make test T=api

# Run web tests
make test T=web

# Quick checks with auto-start
START=1 ./.claude/skills/project-navigation/scripts/quick_checks.sh

# Slash command (writes output to .claude/docs/quick_checks.md)
/quick-checks
```

### Preflight Checks
The test runner validates services before executing tests:
- Uses docker labels (`com.docker.compose.service`, `com.docker.compose.project`) for robust detection
- Exit code 2 = preflight failure (service not running)
- Exit code 1 = test failure
- Preflight hook script: `.claude/hooks/preflight.sh`

## Docs index
- Primary index: `CLAUDE.md` "Index" section linking into docs.
- Domain docs: `docs/context/` and architecture docs in `docs/architecture/`.
