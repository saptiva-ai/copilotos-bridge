# Code Guardrails

> Safety checks before committing code.

## Automated Checks

### Backend (Python)

```bash
# Run ALL before commit
cd apps/backend

# 1. Lint (catch bugs)
ruff check src/

# 2. Format (style consistency)
ruff format --check .

# 3. Type check (catch type errors)
# mypy src/  # if configured

# 4. Tests (catch regressions)
pytest tests/unit -q

# 5. Security scan
# bandit -r src/  # if configured
```

### Frontend (TypeScript)

```bash
cd apps/web

# 1. Lint
pnpm lint

# 2. Type check
pnpm type-check

# 3. Tests
pnpm test

# 4. Build (catch import/config issues)
pnpm build
```

## Security Checklist

### OWASP Top 10 Prevention

| Vulnerability | Check | Prevention |
|---------------|-------|------------|
| **Injection** | User input in queries? | Parameterized queries, ORMs |
| **Broken Auth** | Token validation? | Verify JWT, check expiration |
| **Sensitive Data** | Secrets in code? | Use env vars, never commit |
| **XXE** | XML parsing? | Disable external entities |
| **Broken Access** | Auth on all endpoints? | Use `Depends(get_current_user)` |
| **Security Misconfig** | Debug mode in prod? | `ENV=production` |
| **XSS** | User input in HTML? | Escape, use React (auto-escapes) |
| **Insecure Deserialize** | `pickle`/`eval`? | Use JSON, validate schema |
| **Vulnerable Components** | Old dependencies? | `pip audit`, `pnpm audit` |
| **Insufficient Logging** | Errors logged? | Structured logging |

### Code Review Security Flags

```python
# 🚨 NEVER allow
eval(user_input)
exec(user_input)
pickle.loads(user_data)
os.system(f"ls {user_path}")
subprocess.run(user_command, shell=True)
f"SELECT * FROM users WHERE id = '{user_id}'"  # SQL injection

# ✅ SAFE alternatives
ast.literal_eval(user_input)  # Only for literals
json.loads(user_data)
shlex.quote(user_path)
subprocess.run(["ls", user_path], shell=False)
User.find(User.id == user_id)  # ORM
```

## Input Validation

### Pydantic Models (Backend)

```python
from pydantic import BaseModel, Field, validator, EmailStr

class CreateUserRequest(BaseModel):
    email: EmailStr  # Validates email format
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=0, le=150)

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

# Usage in router
@router.post("/users")
async def create_user(request: CreateUserRequest):  # Auto-validated
    ...
```

### Zod Schemas (Frontend)

```typescript
import { z } from 'zod';

const createUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
  age: z.number().int().min(0).max(150),
});

type CreateUserInput = z.infer<typeof createUserSchema>;

// Usage
const result = createUserSchema.safeParse(formData);
if (!result.success) {
  setErrors(result.error.flatten().fieldErrors);
  return;
}
```

## Error Handling

### Never Expose Internal Errors

```python
# ❌ Bad - exposes stack trace
@app.exception_handler(Exception)
async def handle_exception(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "trace": traceback.format_exc()}
    )

# ✅ Good - generic message, log internally
@app.exception_handler(Exception)
async def handle_exception(request, exc):
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "code": "INTERNAL_ERROR"}
    )
```

### Domain Exceptions

```python
class DomainError(Exception):
    """Base exception with code and message."""
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code

class UserNotFoundError(DomainError):
    def __init__(self, user_id: str):
        super().__init__(
            message=f"User not found: {user_id}",
            code="USER_NOT_FOUND"
        )

class RateLimitExceededError(DomainError):
    def __init__(self, limit: int, window: str):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window}",
            code="RATE_LIMIT_EXCEEDED"
        )
```

## Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

set -e

echo "Running pre-commit checks..."

# Backend
if git diff --cached --name-only | grep -q "apps/backend/"; then
    echo "Checking backend..."
    cd apps/backend
    ruff check src/
    ruff format --check .
    pytest tests/unit -q --tb=no
    cd ../..
fi

# Frontend
if git diff --cached --name-only | grep -q "apps/web/"; then
    echo "Checking frontend..."
    cd apps/web
    pnpm lint
    pnpm type-check
    cd ../..
fi

echo "✅ All checks passed"
```

## CI/CD Guardrails

```yaml
# .github/workflows/ci.yml
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Lint
        run: ruff check apps/backend/src/
      - name: Format
        run: ruff format --check apps/backend/
      - name: Tests
        run: pytest apps/backend/tests/unit --cov=src --cov-fail-under=70

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Lint
        run: cd apps/web && pnpm lint
      - name: Type Check
        run: cd apps/web && pnpm type-check
      - name: Tests
        run: cd apps/web && pnpm test
```

## Guardrail Failure Response

| Check | Failure | Action |
|-------|---------|--------|
| `ruff check` | Lint errors | Fix before commit |
| `ruff format` | Style issues | Run `ruff format .` |
| `pytest` | Test failures | Fix tests or code |
| `mypy` | Type errors | Add/fix type hints |
| Security scan | Vulnerabilities | Fix immediately (P0) |
