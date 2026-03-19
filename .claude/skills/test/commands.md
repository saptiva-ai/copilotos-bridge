# Test Commands Reference

## Make Commands

| Command | Target | Description |
|---------|--------|-------------|
| `make test T=api` | Backend | Run pytest in Docker |
| `make test T=web` | Frontend | Run Jest in Docker |
| `make test T=mcp` | MCP tools | Test MCP integrations |
| `make test T=e2e` | E2E | Run Playwright tests |
| `make test-local FILE="path"` | Local | Run specific test file |

## Project Quick Commands

- Conversación E2E secuencial: `python tests/e2e/conversation/test_multi_turn_context.py`
- Conversación E2E en paralelo: `E2E_MAX_WORKERS=4 python tests/e2e/conversation/test_multi_turn_context.py`

## Slash Commands (Claude Code)

| Command | Action |
|---------|--------|
| `/quick-checks` | Run unit tests only (fast) |
| `/api-test` | Run backend tests |
| `/web-test` | Run frontend tests |
| `/e2e` | Run E2E with Playwright |
| `/dev-up --start` | Start stack before tests |

## Test Targets

| Target | Docker Service | Env Override |
|--------|----------------|--------------|
| `T=api` | `backend` | `API_SERVICE` |
| `T=web` | `web` | `WEB_SERVICE` |

## Preflight Checks

```bash
# Exit codes
# 0 = tests passed
# 1 = tests failed
# 2 = preflight failure (service not running)

make test T=api
echo $?  # Check exit code
```

## Quick Checks Scope

Default excludes integration and e2e:
```bash
# pytest markers
-m "unit and not integration and not e2e"

# Ignored paths
tests/integration
tests/e2e
tests/performance
tests/manual
```

For full suite:
```bash
RUN_E2E=1 ./.claude/skills/project-navigation/scripts/quick_checks.sh
```

## Debugging

```bash
# Verbose output
make test T=api V=1

# Single test
make test T=api TEST_FILE="tests/unit/test_x.py::TestClass::test_method"

# With pdb debugger
cd apps/backend && .venv/bin/python -m pytest tests/unit/test_x.py -s --pdb

# Show print statements
cd apps/backend && .venv/bin/python -m pytest tests/unit/test_x.py -s

# Stop on first failure
cd apps/backend && .venv/bin/python -m pytest tests/unit/test_x.py -x
```

## MCP Commands

```bash
# Add pytest-runner MCP
claude mcp add pytest-runner uvx mcp-pytest-runner

# Add Playwright MCP
claude mcp add playwright npx @playwright/mcp@latest

# List active MCP servers
claude mcp list

# Tidewave MCP (backend SSE)
# Asegúrate de tener backend con TIDEWAVE_ENABLED=true y la red correcta
# Endpoint: POST http://localhost:8000/tidewave/mcp

# Playwright MCP (stdio)
# Config en .mcp.json usa command: npx -y @executeautomation/playwright-mcp-server --stdio
# Alternativa contenedor: puerto 8931 (service agent_playwright)
```

## Docker Test Execution

```bash
# Run tests inside container
docker compose -f infra/docker-compose.yml exec backend pytest tests/unit -v

# Run with coverage
docker compose -f infra/docker-compose.yml exec backend pytest tests/unit --cov=src --cov-report=html
```
