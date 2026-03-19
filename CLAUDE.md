# CLAUDE.md - Saptiva OctaviOS Chat

> Monorepo: FastAPI backend (`apps/backend`) + Next.js web (`apps/web`) + plugins (`plugins/*`)
> Orchestration: `Makefile` + `scripts/` | Infra: `infra/docker-compose*.yml`

## Hard Rules
- **No secrets**: never read/print `.env*`, credentials, tokens, keys
- **Compose env**: always `--env-file envs/.env` with docker compose
- **Testing**: preflight must pass; exit code `2` = infra failure
- **File policy**: no new docs outside `docs/kanban/**`
- **Commits**: no `Co-Authored-By`; body in español (`.claude/rules/80_commit_authorship.md`)
- **Flow**: Explore → Plan → Code → Test → Review → Docs
- **Subagents**: parked; only `repo-scout` during Research

## Python Version
**Always `python3.11`** — system `python` (3.8) is too old.

## Commands

```bash
# Dev stack
make dev                    # full stack (Docker)
make health                 # health checks
make logs S=backend         # tail logs

# Testing
make test                   # all suites
make test T=api             # backend
make test T=web             # frontend
make test T=e2e             # Playwright
make test-local TEST_FILE="tests/unit/test_x.py" TEST_ARGS="-k my_case"

# Pre-deploy
make pre-deploy             # lint + unit + regression + integration
make pre-deploy.quick       # regression only
make pre-deploy.lint

# Web
cd apps/web && pnpm lint
cd apps/web && pnpm typecheck
cd apps/web && pnpm test -- -t "pattern"

# Quick checks
RUN_E2E=1 ./.claude/skills/project-navigation/scripts/quick_checks.sh
```

## Key Paths
- Backend: `apps/backend/src/main.py` | routers: `src/routers/` | schemas: `src/schemas/`
- Web: `apps/web/src/app/` | components: `src/components/`
- Tests: `apps/backend/tests/` | `apps/web/src/**/__tests__/`
- Docs: `docs/context/architecture/README.md` | `docs/context/PATTERNS.md`

## Docker
- Entrypoint: `infra/docker-compose.yml` + dev overlay `docker-compose.dev.yml`
- `make dev` handles env-file + overlays automatically
- "bun not found" → rebuild with `--no-cache`, remove stale volumes
