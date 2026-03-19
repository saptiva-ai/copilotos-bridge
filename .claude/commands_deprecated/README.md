# Deprecated Commands

These commands are kept for reference but are not active.

## Replacements (Pareto)

| Old Command | Replacement |
|-------------|-------------|
| `/api-test` | `make test T=api` |
| `/web-test` | `make test T=web` |
| `/e2e` | `make test T=e2e` |
| `/test` | `make test T=api` or `make test T=web` |
| `/quick-checks` | `/dev-up` + manual `make test` |
| `/infra-doctor` | `/dev-up` + manual `docker compose ps` |
| `/health` | `/dev-up` |
| `/dev-loop` | `/plan` + `/implement` + `/review` + `/validate` |
| `/do` | `/plan` + `/implement` + `/review` + `/validate` |
| `/commit` | `git commit` |
| `/doc-sync` | manual doc edits |
| `/metrics` | `.claude/scripts/report-metrics.sh` |
| `/prd` | edit `docs/context/PRD/*` manually |

## Migration

```bash
# Tests
make test T=api
make test T=web
make test T=e2e

# Stack status
/dev-up
```
