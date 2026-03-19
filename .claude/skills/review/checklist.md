# Review Checklists

## By File Type

### Python Backend (`*.py`)

#### Router Files (`routers/*.py`)
- [ ] All endpoints have auth (`Depends(get_current_user)`)
- [ ] Request validation with Pydantic models
- [ ] Response models defined
- [ ] Error responses documented
- [ ] No business logic (delegated to service)
- [ ] Proper HTTP status codes

#### Service Files (`services/*.py`)
- [ ] Single responsibility
- [ ] Dependencies injected (not constructed)
- [ ] Async methods where appropriate
- [ ] Error handling with domain exceptions
- [ ] No direct HTTP/request handling
- [ ] Testable (mockable dependencies)

#### Model Files (`models/*.py`)
- [ ] Type hints on all fields
- [ ] Validators where needed
- [ ] Indexes defined for query fields
- [ ] No business logic (pure data)
- [ ] Proper Settings class (collection name)

#### Test Files (`tests/*.py`)
- [ ] Follows `test_<ca>_<description>` naming
- [ ] Mocks external dependencies
- [ ] Tests happy path AND error cases
- [ ] No hardcoded test data (use fixtures)
- [ ] Async tests use `@pytest.mark.asyncio`

### TypeScript Frontend (`*.tsx`, `*.ts`)

#### Component Files (`*.tsx`)
- [ ] Props interface defined
- [ ] No `any` types
- [ ] Loading state handled
- [ ] Error state handled
- [ ] Accessible (aria labels, semantic HTML)
- [ ] No inline styles (use Tailwind/CSS modules)

#### Hook Files (`hooks/*.ts`)
- [ ] Returns object (not array) for named access
- [ ] Handles loading/error states
- [ ] Cleanup in useEffect if needed
- [ ] Memoization where beneficial
- [ ] Typed return value

#### API Files (`lib/api/*.ts`)
- [ ] Error handling
- [ ] Typed request/response
- [ ] No hardcoded URLs
- [ ] Timeout configured

## By Change Type

### New Feature
- [ ] PRD/mini-PRD exists
- [ ] Architecture discussed/approved
- [ ] Tests written first (TDD)
- [ ] Documentation updated
- [ ] No breaking changes (or migration path)

### Bug Fix
- [ ] Root cause identified
- [ ] Test added that fails without fix
- [ ] Fix is minimal
- [ ] No side effects
- [ ] Related code checked for same bug

### Refactor
- [ ] Behavior unchanged (tests still pass)
- [ ] No new features sneaked in
- [ ] Code is cleaner
- [ ] Performance not degraded

### Dependency Update
- [ ] Changelog reviewed
- [ ] Breaking changes addressed
- [ ] Security advisories checked
- [ ] Tests pass with new version

## Quick Scan Commands

```bash
# Security quick scan
grep -rn "eval\|exec\|pickle\|shell=True" apps/backend/src/

# Type issues (Python)
grep -rn ": Any" apps/backend/src/

# Missing tests
find apps/backend/src -name "*.py" | while read f; do
  base=$(basename "$f" .py)
  if ! find apps/backend/tests -name "test_${base}.py" | grep -q .; then
    echo "Missing test: $f"
  fi
done

# Console.log in production
grep -rn "console.log" apps/web/src/

# TODO/FIXME
grep -rn "TODO\|FIXME\|HACK" apps/
```

## Severity Decision Tree

```
Is it a security vulnerability?
├─ Yes → CRITICAL
└─ No
   └─ Will it cause runtime errors?
      ├─ Yes → HIGH
      └─ No
         └─ Does it violate project conventions?
            ├─ Yes → MEDIUM
            └─ No
               └─ Is it a style/preference issue?
                  ├─ Yes → LOW (or skip)
                  └─ No → Don't flag
```

## Review Time Budget

| Change Size | Max Review Time | Focus |
|-------------|-----------------|-------|
| Small (<50 lines) | 10 min | Security, correctness |
| Medium (50-200 lines) | 20 min | + conventions, tests |
| Large (200-500 lines) | 30 min | + architecture |
| XL (>500 lines) | Request split | Too risky to review |
