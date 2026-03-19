# TASK: Regression Test Improvements

**Status**: DONE (Phase 1-3 Complete)
**Created**: 2026-01-14
**Updated**: 2026-01-28
**Priority**: Medium
**Type**: Enhancement

## Summary

Mejoras identificadas en la auditoría de tests de regresión. Este task documenta gaps y mejoras potenciales encontradas por los agentes de exploración.

## Context

Durante la implementación de tests de regresión (2026-01-14), se realizó una auditoría exhaustiva que identificó:
- 133 test files en backend, 49 en frontend, 21+ E2E specs
- Coverage thresholds: 30% backend, 25% frontend (intencional)
- CI solo ejecutaba unit tests, ahora incluye regression

## Gaps Identificados

### Auth Flow Gaps
1. **Token Blacklist Redis Failure** - Sin fallback si Redis está caído
2. **Email Normalization Edge Cases** - `Test@Example.Com` vs `test@example.com`
3. **Password Hash Upgrade Path** - bcrypt → argon2 migration
4. **Session Cookie Attributes** - Verificar Secure, HttpOnly, SameSite
5. **Inactive User Prevention** - Login/refresh con `is_active=false`

### Chat Flow Gaps
1. **Document Stale Read** - MongoDB replica lag en file attachments
2. **Document Readiness Timeout** - Manejo de docs PENDING > 30s
3. **Bank Analytics Detection** - Contextual detection + BUG-13 tracking
4. **Empty Response Handling** - Fallback cuando Saptiva retorna vacío
5. **Streaming Producer Error** - Propagación de errores en SSE

### Bank Advisor Gaps
1. **Intent Classification Edge Cases** - "¿Cuál es mi ICAP?" → DATA, no KNOWLEDGE
2. **Handler Routing Order** - 5+ handlers con prioridad específica
3. **SQL Injection Validation** - SAFE_METRIC_COLUMNS whitelist
4. **Clarification Flow** - Queries ambiguos sin banco/métrica

## Files Reference

### Critical Paths (Auth)
- `src/routers/auth.py` - Endpoints auth
- `src/services/auth_service.py` - Business logic
- `tests/integration/test_auth_flow.py` - Tests existentes

### Critical Paths (Chat)
- `src/routers/chat/endpoints/message_endpoints.py` - Message handling
- `src/routers/chat/handlers/streaming_handler.py` - SSE streaming
- `src/services/chat_service.py` - Chat business logic

### Critical Paths (Bank Advisor)
- `bankadvisor/pipelines/stages/intent_detection.py` - Intent classification
- `bankadvisor/handlers/knowledge_handler.py` - Knowledge queries
- `bankadvisor/services/analytics_service.py` - Data queries

## Proposed Improvements

### Phase 1: Backend Test Fixtures (Immediate) - COMPLETE
- [x] Crear fixtures `client` y `test_user` para tests de regresión
- [x] Fix MongoDB connectivity for Docker/CI/Local environments
- [x] Fix MinIO import-time connection with TEST_MODE
- [x] 11/11 critical path tests passing

### Phase 2: Integration Test Coverage - COMPLETE
- [x] Fix `TestFileDeduplicationRegression` async mocking (3 tests)
- [x] Add `TestDeduplicationEdgeCases` (5 tests: hash determinism, byte diff, sizes)
- [ ] Test de Token Blacklist con Redis failure (deferred)
- [ ] Test de Email normalization (case sensitivity) - covered in REG-AUTH-002
- [ ] Test de Password hash upgrade (deferred)

### Phase 3: E2E Streaming Tests - COMPLETE
- [x] Test de Producer error propagation (BUG-006)
- [x] Test de Empty response handling (BUG-007)
- [x] Test de Artifact persistence (BUG-008)
- [x] Test de Redis blacklist failure (BUG-009)
- [x] Edge cases: unicode, special chars, nested exceptions

## Related

- Plan file: `~/.claude/plans/ticklish-twirling-brooks.md`
- Created tests: `tests/regression/test_critical_paths.py`
- Created tests: `bankadvisor/tests/regression/test_happy_path_regression.py`

## Notes

Los tests de Bank Advisor ya están funcionando (34/34 passing). Los tests de backend requieren fixtures adicionales que actualmente no existen en el proyecto.

## Completion Summary

- **Date Completed**: 2026-01-28
- **Total Regression Tests**: 33
- **Files Created**: 4 (`conftest.py`, `test_critical_paths.py`, `test_file_deduplication.py`, `test_streaming_resilience.py`)
- **CI Integration**: `test-regression` job added to `.github/workflows/ci-cd.yml`
- **Moved to DONE**: 2026-01-29
