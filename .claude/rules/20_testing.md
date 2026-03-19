---
paths:
  - scripts/testing/**
  - apps/backend/**
  - apps/web/**
---

# Testing Rules

When this applies: running or editing tests and test tooling.

Do:
- Run preflight (stack up) before tests.
- Use `make test T=api` (backend) and `make test T=web` (web).
- Use quick checks for minimal coverage.
- Treat missing Python test deps (e.g., `mongomock_motor`) as preflight failures.
- Keep legacy Qdrant tests archived under `apps/backend/tests_legacy/`.
- Default quick checks run `tests/unit` with `-m "unit and not integration and not e2e"`; opt in with `RUN_E2E=1`.
- With `RUN_E2E=1`, quick checks requires Weaviate health.

Don't:
- Bypass preflight errors; exit code 2 means infra failure.
- Rename test targets without updating Makefile + scripts.
- Reintroduce Qdrant tests into `apps/backend/tests/`.

Parallel Execution:
- Always run E2E tests in background with `run_in_background=true` when possible.
- System has 24 cores and 7.5GB RAM available.
- Workers recommendations:
  - E2E HTTP tests: `E2E_MAX_WORKERS=4-8` (limited by backend capacity)
  - Unit tests: 12-16 workers
  - Multi-turn context: 4-6 workers (each scenario is a full session)
- Example: `E2E_MAX_WORKERS=6 python tests/e2e/conversation/test_multi_turn_context.py`
- Check output with `TaskOutput` tool or `tail -f` on output file.

Commands:
- `make test T=api`
- `make test T=web`
- `RUN_E2E=1 ./.claude/skills/project-navigation/scripts/quick_checks.sh`
- `QUICK_CHECKS_TIMEOUT=180 ./.claude/skills/project-navigation/scripts/quick_checks.sh`

Exit codes:
- `2` infra/preflight failure
- `1` tests failed
- `0` success

Refs:
- `.claude/skills/test/SKILL.md`
- `.claude/commands/quick-checks.md`
