# Coverage Metrics

## Targets by Area

| Area | Minimum | Ideal | Notes |
|------|---------|-------|-------|
| Core (auth, chat, routers) | 70% | 85% | Critical code paths |
| Services | 60% | 80% | Business logic |
| Plugins | 30% | 50% | Isolated functionality |
| Frontend components | 60% | 80% | User-facing |
| Utils/helpers | 50% | 70% | Reusable code |

## Quality Metrics (Bank Advisor)

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Query success rate | ≥85% | Tests with valid queries |
| Latency p50 | <2s | Benchmark tests |
| Grounding rate | ≥95% | Response validation tests |

## Checking Coverage

```bash
# Run with coverage
make test T=api

# View HTML report
open apps/backend/htmlcov/index.html

# Coverage in CI
pytest --cov=src --cov-report=xml --cov-fail-under=70
```

## Coverage Configuration

```ini
# apps/backend/.coveragerc
[run]
source = src
omit =
    */tests/*
    */__pycache__/*
    */migrations/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if TYPE_CHECKING:
```

## Improving Coverage

### Finding Uncovered Code

```bash
# Generate detailed report
pytest --cov=src --cov-report=term-missing

# Output shows uncovered lines
src/services/chat.py    85%   42-45, 78-82
```

### Priority Order

1. **Critical paths first**: Auth, payment, data validation
2. **Error handlers**: Exception paths often missed
3. **Edge cases**: Empty inputs, null values, boundaries
4. **Branches**: All if/else paths

## Coverage in PRs

CI should enforce:
```yaml
# .github/workflows/test.yml
- name: Check coverage
  run: pytest --cov-fail-under=70
```

## When to Skip Coverage

```python
# Acceptable to skip:
if TYPE_CHECKING:  # pragma: no cover
    from typing import ...

def __repr__(self):  # pragma: no cover
    return f"<{self.__class__.__name__}>"

# Not acceptable to skip:
# - Business logic
# - Error handling
# - Security checks
```
