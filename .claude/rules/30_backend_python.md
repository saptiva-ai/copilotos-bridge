---
paths:
  - apps/backend/**/*.py
  - plugins/**/**/*.py
---

# Backend Python Rules

When this applies: editing Python in backend or plugins.

## Style
- **Format**: Black (line 88) + isort `black` profile
- **Typing**: mypy strict; type hints on functions/classes
- **Imports**: stdlib → third-party → local, blank lines between
- **Async**: prefer async endpoints; `await` for IO
- **Pydantic**: `BaseModel` for schemas; `model_dump()`
- **Errors**: `APIError`/`HTTPException`; `structlog` with context fields; Problem Details response
- **Naming**: snake_case functions/vars, PascalCase classes, UPPER_SNAKE constants
- **Exceptions**: no bare `except`; log error, return safe messages
- **Tests**: `apps/backend/tests/**` (legacy: `tests_legacy/`)

## Do
- Follow module structure under `apps/backend/src/` and plugin `src/`
- Keep changes minimal; add/adjust tests when behavior changes

## Don't
- Introduce patterns without checking `docs/context/code/PATTERNS.md`
- Skip test updates when touching service behavior

## Commands
- `make test T=api`
- `make test-local FILE="tests/unit/test_x.py"`
