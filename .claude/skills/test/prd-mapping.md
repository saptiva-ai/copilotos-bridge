# PRD to Tests Mapping

## Acceptance Criteria → Test Functions

Los acceptance criteria (CA) del mini-PRD se mapean directamente a funciones de test.

### Naming Convention

```
test_<ca_id>_<descripcion_corta>
```

### Example Mapping

**mini-PRD**:
```markdown
## Acceptance Criteria

### Functional
- [ ] **CA-01**: User can login with valid email and password
- [ ] **CA-02**: Invalid password shows error message
- [ ] **CA-03**: Session expires after 30 minutes of inactivity

### Non-Functional
- [ ] **CA-04**: Login response time < 500ms
- [ ] **CA-05**: Failed attempts are rate-limited (5/minute)
```

**Generated Tests**:
```python
# tests/unit/test_auth.py

class TestAuthCA01to03:
    """Tests for CA-01, CA-02, CA-03: Login functionality."""

    @pytest.mark.asyncio
    async def test_ca01_login_with_valid_credentials_succeeds(self, client):
        """CA-01: User can login with valid email and password."""
        response = await client.post("/api/auth/login", json={
            "email": "user@example.com",
            "password": "valid_password"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    async def test_ca02_invalid_password_shows_error(self, client):
        """CA-02: Invalid password shows error message."""
        response = await client.post("/api/auth/login", json={
            "email": "user@example.com",
            "password": "wrong_password"
        })
        assert response.status_code == 401
        assert "error" in response.json()
        assert "invalid" in response.json()["error"].lower()

    @pytest.mark.asyncio
    async def test_ca03_session_expires_after_inactivity(self, client, freezer):
        """CA-03: Session expires after 30 minutes of inactivity."""
        # Login
        login_response = await client.post("/api/auth/login", json={...})
        token = login_response.json()["access_token"]

        # Advance time 31 minutes
        freezer.tick(timedelta(minutes=31))

        # Try to use token
        response = await client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401


class TestAuthCA04to05:
    """Tests for CA-04, CA-05: Non-functional requirements."""

    @pytest.mark.asyncio
    async def test_ca04_login_response_under_500ms(self, client, benchmark):
        """CA-04: Login response time < 500ms."""
        async def login():
            return await client.post("/api/auth/login", json={...})

        result = await benchmark(login)
        assert result.elapsed < 0.5  # 500ms

    @pytest.mark.asyncio
    async def test_ca05_rate_limits_failed_attempts(self, client):
        """CA-05: Failed attempts are rate-limited (5/minute)."""
        for i in range(5):
            await client.post("/api/auth/login", json={
                "email": "user@example.com",
                "password": "wrong"
            })

        # 6th attempt should be rate limited
        response = await client.post("/api/auth/login", json={
            "email": "user@example.com",
            "password": "wrong"
        })
        assert response.status_code == 429
```

## Test File Organization

```
tests/
├── unit/
│   ├── test_auth.py           # CA-01 to CA-05
│   ├── test_chat.py           # CA-06 to CA-10
│   └── test_documents.py      # CA-11 to CA-15
├── integration/
│   └── test_auth_flow.py      # Full auth integration
└── e2e/
    └── test_login_flow.py     # Browser-based login
```

## Traceability Matrix

| CA ID | Test Function | File | Type |
|-------|---------------|------|------|
| CA-01 | `test_ca01_login_with_valid_credentials_succeeds` | `test_auth.py` | unit |
| CA-02 | `test_ca02_invalid_password_shows_error` | `test_auth.py` | unit |
| CA-03 | `test_ca03_session_expires_after_inactivity` | `test_auth.py` | unit |
| CA-04 | `test_ca04_login_response_under_500ms` | `test_auth.py` | benchmark |
| CA-05 | `test_ca05_rate_limits_failed_attempts` | `test_auth.py` | unit |

## Generating Tests from PRD

### Using Claude Code

```
User: Generate tests for CA-01 to CA-03 from docs/context/product/EPICS/EPIC-HU1.md

Claude: [reads PRD, extracts CA, generates test file]
```

### Test Template

```python
"""
Tests for EPIC-{epic_id}: {epic_name}

Acceptance Criteria covered:
- CA-{id}: {description}
"""

import pytest

class Test{EpicName}:
    """Tests for {epic_name}."""

    @pytest.mark.asyncio
    async def test_ca{id}_{short_description}(self):
        """CA-{id}: {full_description}."""
        # Arrange
        ...

        # Act
        ...

        # Assert
        ...
```

## Validating Coverage

```bash
# Check all CAs have tests
grep -r "CA-" docs/context/product/EPICS/*.md | wc -l  # Count CAs
grep -r "test_ca" tests/ | wc -l              # Count tests

# Should match (or tests > CAs for edge cases)
```
