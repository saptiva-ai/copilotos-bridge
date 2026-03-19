# MCP Testing Guide

Complete guide to testing MCP (Model Context Protocol) implementation with diff-coverage, markers, and CI/CD integration.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Test Markers](#test-markers)
3. [Diff-Coverage](#diff-coverage)
4. [Makefile Commands](#makefile-commands)
5. [CI/CD Integration](#cicd-integration)
6. [Writing MCP Tests](#writing-mcp-tests)
7. [Best Practices](#best-practices)

---

## Quick Start

### Run all MCP tests

```bash
make test-mcp
```

### Run specific MCP test category

```bash
make test-mcp-marker MARKER=mcp_security
```

### Run only tests for changed files

```bash
make test-diff
```

### Run MCP tests for changed files only

```bash
make test-mcp-diff
```

---

## Test Markers

MCP tests use pytest markers for categorization:

### Available Markers

| Marker | Description | Example |
|--------|-------------|---------|
| `mcp` | General MCP tests | All MCP-related tests |
| `mcp_tools` | Tool implementation tests | Schema discovery, tool invocation |
| `mcp_security` | Security layer tests | Rate limiting, validation, AuthZ |
| `mcp_tasks` | Task management tests | 202 Accepted pattern, polling |
| `mcp_versioning` | Version management tests | Semver, constraint resolution |
| `unit` | Unit tests | Fast, isolated tests |
| `integration` | Integration tests | Tests with dependencies |

### Usage Examples

**Run all MCP tests:**
```bash
pytest tests/mcp/ -m mcp
```

**Run only security tests:**
```bash
pytest tests/ -m mcp_security
```

**Run MCP unit tests only:**
```bash
pytest tests/ -m "mcp and unit"
```

**Run MCP integration tests only:**
```bash
pytest tests/ -m "mcp and integration"
```

**Exclude slow tests:**
```bash
pytest tests/ -m "mcp and not slow"
```

### Adding Markers to Tests

**File-level markers (all tests in file):**
```python
# tests/mcp/test_security.py
import pytest

pytestmark = [pytest.mark.mcp, pytest.mark.mcp_security, pytest.mark.unit]

class TestRateLimiter:
    def test_rate_limit_allows_within_limit(self):
        # Test code...
```

**Function-level markers (single test):**
```python
@pytest.mark.mcp
@pytest.mark.mcp_security
@pytest.mark.slow
async def test_rate_limit_stress_test():
    # Long-running test...
```

---

## Diff-Coverage

Diff-coverage runs only tests for files that changed in your git diff. This dramatically speeds up test runs during development.

### How It Works

The diff-coverage plugin:
1. Runs `git diff BASE_BRANCH...HEAD` to find changed files
2. Maps test files to source files (e.g., `test_security.py` → `security.py`)
3. Selects only tests related to changed files
4. Runs selected tests with full coverage reporting

### Usage

**Basic diff-coverage:**
```bash
# Compare against main branch (default)
pytest tests/ --diff-coverage

# Compare against specific branch
pytest tests/ --diff-coverage --diff-base=develop
```

**With Makefile:**
```bash
# Compare against main
make test-diff

# Compare against develop
make test-diff BASE=develop

# MCP tests only
make test-mcp-diff

# MCP tests against develop
make test-mcp-diff BASE=develop
```

### Examples

**Scenario 1: Changed security.py**
```bash
# You modified: apps/api/src/mcp/security.py
make test-diff

# Runs:
# - tests/mcp/test_security.py (direct mapping)
# - Any other tests importing security.py
```

**Scenario 2: Changed task management**
```bash
# You modified: apps/api/src/mcp/tasks.py
make test-mcp-diff

# Runs only MCP tests:
# - tests/mcp/test_task_routes.py
# - tests/mcp/test_metrics.py (if it tests task metrics)
```

**Scenario 3: Changed test file**
```bash
# You modified: tests/mcp/test_versioning.py
make test-diff

# Runs:
# - tests/mcp/test_versioning.py (self)
```

### Diff-Coverage with CI

In pull requests, CI automatically runs diff-coverage:
- Only tests related to changed files run
- Provides fast feedback on PRs
- Full test suite still runs on main branch

---

## Makefile Commands

### MCP Testing

| Command | Description |
|---------|-------------|
| `make test-mcp` | Run all MCP tests |
| `make test-mcp-marker MARKER=<marker>` | Run tests with specific marker |
| `make test-diff` | Run diff-coverage tests (all) |
| `make test-mcp-diff` | Run MCP diff-coverage tests |
| `make test-mcp-diff BASE=develop` | Run MCP diff-coverage against develop |

### General Testing

| Command | Description |
|---------|-------------|
| `make test-api` | Run all API tests |
| `make test-api-coverage` | Run API tests with coverage report |
| `make test-api-file FILE=test_security.py` | Run specific test file |
| `make test-api-parallel` | Run tests in parallel |

### Examples

**Development workflow:**
```bash
# 1. Make changes to src/mcp/security.py
# 2. Run related tests only
make test-diff

# 3. If tests pass, run all MCP tests
make test-mcp

# 4. If all pass, commit changes
git add .
git commit -m "feat(mcp): improve rate limiting"
```

**Pre-commit check:**
```bash
# Run all MCP tests with coverage
make test-mcp ARGS="--cov=src/mcp --cov-report=html"

# Open coverage report
open apps/api/htmlcov/index.html
```

---

## CI/CD Integration

### MCP-Specific CI Workflow

The `.github/workflows/mcp-ci.yml` workflow runs on:
- Push to `main` or `develop` (if MCP files changed)
- Pull requests (if MCP files changed)
- Manual workflow dispatch

### CI Jobs

**1. mcp-backend**
- Runs all MCP backend tests
- Separated by marker:
  - Unit tests (fast, isolated)
  - Integration tests (with dependencies)
  - Security tests (80% coverage required)
  - Task management tests
  - Versioning tests
- Uploads coverage to Codecov

**2. mcp-diff-coverage** (PRs only)
- Runs only tests for changed files
- Provides fast feedback
- Comments on PR with coverage diff

**3. mcp-frontend**
- Type checks TypeScript SDK
- Lints MCP SDK code
- Runs frontend tests (if available)

**4. mcp-health**
- Aggregates results from all jobs
- Provides final pass/fail status

### Viewing CI Results

**GitHub UI:**
1. Go to Pull Request
2. Click "Checks" tab
3. Expand "MCP (Model Context Protocol) CI"
4. View individual job results

**Command line:**
```bash
# View CI status
make ci-status

# View CI logs
make ci-logs

# Watch CI in real-time
make ci-watch
```

### CI Badge

Add to README:
```markdown
[![MCP CI](https://github.com/your-org/your-repo/actions/workflows/mcp-ci.yml/badge.svg)](https://github.com/your-org/your-repo/actions/workflows/mcp-ci.yml)
```

---

## Writing MCP Tests

### Test Structure

```python
"""
Module docstring explaining what this test file covers.
"""

import pytest

# Add file-level markers
pytestmark = [pytest.mark.mcp, pytest.mark.mcp_security, pytest.mark.unit]

from src.mcp.security import RateLimiter, RateLimitConfig


class TestRateLimiter:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_within_limit(self):
        """Test requests within limit are allowed."""
        limiter = RateLimiter()
        config = RateLimitConfig(calls_per_minute=10, calls_per_hour=100)

        allowed, retry_after = await limiter.check_rate_limit("user_123:test_tool", config)

        assert allowed is True
        assert retry_after is None

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_after_limit(self):
        """Test requests are blocked after exceeding limit."""
        limiter = RateLimiter()
        config = RateLimitConfig(calls_per_minute=3, calls_per_hour=100)

        # Make 3 requests (at limit)
        for _ in range(3):
            allowed, _ = await limiter.check_rate_limit("user_123:test_tool", config)
            assert allowed is True

        # 4th request should be blocked
        allowed, retry_after = await limiter.check_rate_limit("user_123:test_tool", config)
        assert allowed is False
        assert retry_after is not None
```

### Using Fixtures

MCP tests have access to shared fixtures from `conftest.py`:

```python
def test_tool_invocation_with_mock_user(mock_user, sample_tool_payload):
    """Test tool invocation with authenticated user."""
    assert mock_user.id == "test_user_123"
    assert "doc_id" in sample_tool_payload
```

### Assertions

Use helper functions from `conftest.py`:

```python
from conftest import assert_valid_error_response, assert_valid_success_response

def test_validation_error():
    response = invoke_tool_with_invalid_payload()
    assert_valid_error_response(response, expected_code="VALIDATION_ERROR")

def test_successful_invocation():
    response = invoke_tool()
    assert_valid_success_response(response, expected_tool="audit_file")
```

---

## Best Practices

### 1. Use Appropriate Markers

```python
# Unit test: Fast, isolated
pytestmark = [pytest.mark.mcp, pytest.mark.mcp_security, pytest.mark.unit]

# Integration test: With dependencies
pytestmark = [pytest.mark.mcp, pytest.mark.mcp_tasks, pytest.mark.integration]

# Slow test: Mark explicitly
@pytest.mark.slow
def test_stress_test():
    # Long-running test
```

### 2. Write Descriptive Test Names

```python
# Good
def test_rate_limit_blocks_after_exceeding_minute_limit():
    pass

# Bad
def test_rate_limit():
    pass
```

### 3. Use Docstrings

```python
def test_rate_limit_blocks_after_limit(self):
    """
    Test that rate limiter blocks requests after exceeding the minute limit.

    Given: RateLimiter with 3 calls/minute limit
    When: User makes 4 requests
    Then: First 3 succeed, 4th is blocked with retry_after
    """
```

### 4. Test Both Success and Failure Paths

```python
class TestPayloadValidator:
    def test_validate_size_within_limit(self):
        """Test payload within size limit passes."""
        assert PayloadValidator.validate_size(small_payload, max_size_kb=1) is True

    def test_validate_size_exceeds_limit(self):
        """Test oversized payload is rejected."""
        with pytest.raises(ValueError, match="Payload too large"):
            PayloadValidator.validate_size(huge_payload, max_size_kb=1)
```

### 5. Use Diff-Coverage During Development

```bash
# Fast iteration cycle
while developing:
    make_changes()
    make test-diff  # Only run related tests
    if tests_pass:
        break

# Before commit: full test suite
make test-mcp
```

### 6. Coverage Requirements

- **Security tests:** 90% minimum
- **Task management:** 85% minimum
- **Other MCP tests:** 80% minimum
- **Overall MCP:** 80% minimum

### 7. Keep Tests Independent

```python
# Good: Each test creates its own data
def test_rate_limit_1():
    limiter = RateLimiter()  # Fresh instance
    # Test...

def test_rate_limit_2():
    limiter = RateLimiter()  # Fresh instance
    # Test...

# Bad: Tests share state
limiter = RateLimiter()  # Module-level

def test_rate_limit_1():
    # Uses shared limiter
    pass

def test_rate_limit_2():
    # Affected by test_rate_limit_1
    pass
```

---

## Troubleshooting

### Tests Not Selected by Diff-Coverage

**Problem:** Changed file but no tests run

**Solution:** Check file mapping:
```bash
# Test file should match source file name
src/mcp/security.py → tests/mcp/test_security.py
src/mcp/tasks.py → tests/mcp/test_task_routes.py
```

### Marker Not Found

**Problem:** `pytest: error: Unknown marker: mcp_security`

**Solution:** Markers must be registered in `pytest.ini`:
```ini
[pytest]
markers =
    mcp_security: MCP security layer tests
```

### Import Errors in Tests

**Problem:** `ModuleNotFoundError: No module named 'src'`

**Solution:** Ensure PYTHONPATH is set:
```bash
# In pytest.ini
pythonpath = ["src", "../.."]

# Or in command
PYTHONPATH=apps/api/src pytest tests/
```

### Slow Test Suite

**Solution:** Use diff-coverage or parallel execution:
```bash
# Diff-coverage (fast)
make test-diff

# Parallel execution
make test-api-parallel

# Exclude slow tests
pytest tests/ -m "not slow"
```

---

## Summary

### Key Commands

```bash
# Development
make test-diff              # Fast: only changed files
make test-mcp               # All MCP tests
make test-mcp-diff          # MCP tests for changed files

# Specific categories
make test-mcp-marker MARKER=mcp_security
make test-mcp-marker MARKER=mcp_tasks

# Coverage reports
make test-api-coverage      # With HTML report
```

### CI Workflow

1. **Push changes** → CI runs diff-coverage (fast feedback)
2. **PR approved** → Full MCP test suite runs
3. **Merge to main** → Full integration tests + coverage upload

### Coverage Requirements

- Security: 90%+
- Tasks: 85%+
- Other: 80%+
- Overall MCP: 80%+

---

For questions or issues with the MCP test infrastructure, check:
- `apps/api/conftest.py` - Pytest configuration and fixtures
- `apps/api/pytest.ini` - Test markers and options
- `.github/workflows/mcp-ci.yml` - CI workflow
- `Makefile` - Test commands
