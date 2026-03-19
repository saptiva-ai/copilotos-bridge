---
name: test
description: Write and run tests with MCP-enhanced diagnostics (pytest, Jest, Playwright). Use PROACTIVELY after implementing code changes to validate behavior. (project)
allowed-tools: [Read, Write, Edit, Grep, Glob, Bash]
---

# Testing Skill

> Write, run, and debug tests with AI-assisted diagnostics.

## MCP Testing Stack

El proyecto usa tres servidores MCP para testing inteligente:

| Server | Tipo | Capacidad |
|--------|------|-----------|
| `pytest-runner` | Test execution | Discover/run tests, resultados estructurados |
| `tidewave-backend` | Runtime analysis | Logs, source location, project eval |
| `playwright` | E2E browser | Screenshots, clicks, form fills |

### Flujo de Testing con MCP

```
┌─────────────────┐
│   mini-PRD      │  Acceptance Criteria (CA-01, CA-02...)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Tidewave     │  get_source_location → encontrar código
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  pytest-runner  │  discover_tests → tests existentes
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   test skill    │  Generar tests desde CA
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  pytest-runner  │  run_tests → ejecutar
└────────┬────────┘
         │ ¿failures?
         ▼
┌─────────────────┐
│    Tidewave     │  get_logs → diagnóstico runtime
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Playwright    │  E2E + screenshots
└─────────────────┘
```

## Quick Start

```bash
# Backend tests
make test T=api

# Frontend tests
make test T=web

# E2E tests
make test T=e2e

# Quick checks (unit only)
/quick-checks
```

## Test Structure

```
apps/backend/tests/
├── unit/              # Isolated tests with mocks
├── integration/       # Multi-service tests
├── e2e/               # Full flow tests
└── mcp/               # MCP tools tests

apps/web/src/
└── components/**/__tests__/   # Component tests

tests/playwright/      # E2E browser tests
```

## From PRD to Tests

Los acceptance criteria del mini-PRD se mapean directamente a tests:

```markdown
# mini-PRD
- CA-01: User can login with valid email
- CA-02: Invalid password shows error message
```

```python
# tests/unit/test_auth.py
def test_ca01_user_can_login_with_valid_email():
    """CA-01: User can login with valid email."""
    ...

def test_ca02_invalid_password_shows_error():
    """CA-02: Invalid password shows error message."""
    ...
```

## Reference Files

| File | Content |
|------|---------|
| `commands.md` | Make commands, slash commands, debugging |
| `patterns.md` | pytest/Jest code examples |
| `coverage.md` | Coverage metrics and targets |
| `prd-mapping.md` | Detailed CA → Test mapping |

## Test Checklist

- [ ] Tests nombrados con patrón `test_<ca>_<descripcion>`
- [ ] Mocks para dependencias externas
- [ ] Edge cases cubiertos (null, empty, invalid)
- [ ] Tests pasan localmente antes de commit
- [ ] Coverage meets targets (see `coverage.md`)