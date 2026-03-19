# Plan: Regression Test Improvements

**Status**: Draft
**Last Updated**: 2026-01-14

## Objective

Completar la suite de tests de regresión para prevenir regresiones en deploys.

## Phases

### Phase 1: Fix Backend Regression Test Fixtures (Immediate)

**Goal**: Hacer que `test_critical_paths.py` funcione con fixtures reales.

**Approach**: Crear `conftest.py` en `tests/regression/` que importe fixtures de `tests/integration/`.

**Files**:
- `tests/regression/conftest.py` (CREATE) - Import fixtures from integration

**Validation**:
```bash
cd apps/backend && pytest tests/regression -v -m regression
```

### Phase 2: Integration Test Expansion (Short-term)

**Goal**: Cubrir gaps identificados en auth/chat flows.

**Tests to Add**:
1. `test_auth_redis_failure.py` - Token blacklist with Redis down
2. `test_email_normalization.py` - Case-insensitive email login
3. `test_password_hash_upgrade.py` - bcrypt → argon2 migration

### Phase 3: E2E Streaming Tests (Medium-term)

**Goal**: Cubrir streaming handler edge cases.

**Tests to Add**:
1. Document readiness timeout (> 30s)
2. Bank analytics contextual detection
3. Empty response handling
4. Producer error propagation

## Dependencies

- MongoDB running (port 27018 on host, 27017 in Docker)
- Redis running (port 6380 on host, 6379 in Docker)
- .env loaded from `envs/.env`

## Risks

1. **Flaky tests**: Integration tests depend on real DB state
2. **Port conflicts**: Host vs Docker port mapping
3. **Test isolation**: Need clean_db fixture per test

## Success Criteria

- [ ] `make pre-deploy.regression` passes
- [ ] All 34 Bank Advisor tests pass
- [ ] Backend regression tests pass with real fixtures
- [ ] CI `test-regression` job passes
