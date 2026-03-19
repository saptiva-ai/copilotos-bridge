# Research: Test Infrastructure Audit

**Date**: 2026-01-14
**Source**: Agent exploration (repo-scout)

## Test Infrastructure Inventory

### Backend (FastAPI)
- **Total Test Files**: 133 Python test files
- **Test Assertions**: ~2,025 test functions/methods
- **Directories**:
  - `/tests/unit/` - Unit tests
  - `/tests/integration/` - Integration tests
  - `/tests/regression/` - Regression tests (NEW)
  - `/tests/routers/` - API endpoint tests
  - `/tests/services/` - Service layer tests
  - `/tests/mcp/` - Model Context Protocol tests
  - `/tests/performance/` - Performance tests
  - `/tests/e2e/` - End-to-end tests

### Frontend (Next.js)
- **Total Test Files**: 49 TypeScript/TSX test files
- **Coverage Thresholds**: 25% branches/functions, 30% lines

### E2E (Playwright)
- **Total E2E Test Files**: 21+ Playwright spec files
- **Projects**: setup (auth), no-auth, chromium, firefox

### Bank Advisor
- **Total Test Files**: 25 Python test files
- **Custom Markers**: unit, integration, nl2sql_dirty, ba_null_001, regression

## CI/CD Current State

### Before Changes
- Only ran `pytest tests/unit -q --cov=src --cov-report=xml`
- Integration and regression tests ignored
- No pre-deploy verification

### After Changes
- Added `test-regression` job with MongoDB/Redis services
- Runs `tests/regression -v -m regression`
- Build depends on regression tests passing

## Critical Test Gaps

### Auth Service (`auth_service.py`)
| Function | Line | Risk |
|----------|------|------|
| `authenticate_user()` | 250 | Hash scheme compatibility |
| `register_user()` | 185 | Email normalization |
| `refresh_access_token()` | 328 | Token blacklist bypass |
| `logout_user()` | 398 | Invalid token handling |

### Chat Streaming (`streaming_handler.py`)
| Function | Risk |
|----------|------|
| `handle_stream()` | Document readiness timeout |
| `_stream_chat_response()` | Producer error propagation |
| Bank analytics path | Contextual detection failures |

### Bank Advisor Intent Detection
| Query Type | Current Coverage |
|------------|------------------|
| BANK_KNOWLEDGE | Covered (34 tests) |
| RANKING | Covered |
| COMPARISON | Covered |
| EVOLUTION | Covered |
| Edge cases | Partial |

## Existing Test Fixtures

### Backend (`conftest.py`)
- `initialize_database` - Session-scoped DB init
- `reset_versioned_registry` - MCP tool isolation
- `mock_redis_cache` - Redis mock
- `mock_minio_service` - MinIO mock

### Missing Fixtures
- `client` - AsyncClient for HTTP tests
- `test_user` - Authenticated user for auth tests
- `auth_headers` - Bearer token headers
