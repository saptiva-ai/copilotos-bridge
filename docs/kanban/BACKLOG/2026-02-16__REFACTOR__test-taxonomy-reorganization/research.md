# Research

## Questions
- Que suites hoy estan etiquetadas como E2E pero tecnicamente son integration/system?
- Que ejecuta realmente CI en GitHub y que queda fuera?
- Cual deberia ser la taxonomia objetivo (best practices) para este repo?
- Como migrar sin romper flujos actuales (`make test`, `tests.runner`, scripts)?

## Findings

### F1) `tests/e2e/` root es mayormente system/API, no E2E UI
- `tests/utils/helpers.py` autentica y envía HTTP directo a `/api/chat` con SSE parsing.
- `tests/e2e/*` depende de backend URL + token, sin browser automation.
- `tests/e2e/run_all.py` ejecuta scripts Python (`sys.executable file.py`) uno por uno.
- Resultado: estas pruebas validan comportamiento end-to-end de backend (system tests), no journey UI.

### F2) CI actual no ejecuta `tests/e2e/` root
- `.github/workflows/ci.yml` corre:
  - unit backend en `apps/backend/tests/unit` (ignorando integration/e2e en esa etapa),
  - regression backend en `apps/backend/tests/regression`,
  - integration smoke backend (`apps/backend/tests/integration/test_auth_*`),
  - web Playwright smoke.
- No hay job dedicado a `tests/e2e/` root.

### F3) `make test T=e2e` usa significado distinto de E2E
- `scripts/testing/test-runner.sh` target `e2e` ejecuta Playwright (`pnpm --filter web test:e2e`).
- En paralelo, el directorio root `tests/e2e/` usa Python scripts API-first.
- Hay colisión semántica para el mismo término "E2E".

### F4) Playwright en web corre con mocks por default
- `apps/web/e2e/fixtures/index.ts` define `useApiMocks` con `E2E_USE_API_MOCKS !== "0"`.
- `apps/web/e2e/utils/mock-api.ts` intercepta endpoints y evita backend real.
- El job "Web E2E Smoke" de CI usa explícitamente mocks (`E2E_USE_API_MOCKS: '1'`).
- Esto representa "UI integration mocked", no "full e2e live".

### F5) Backend también tiene mezcla de nombres
- Existen archivos en `apps/backend/tests/e2e/` con naming de integration (`test_bank_analytics_integration.py`).
- Técnicamente validan flujos full-stack de API/servicios (sin navegador).

### F6) Conteo actual (snapshot)
- `tests/e2e/`: 61 archivos Python
- `tests/integration/`: 9 archivos Python
- `apps/backend/tests/e2e/`: 7 archivos Python
- `apps/backend/tests/integration/`: 16 archivos Python
- `apps/web/e2e/tests/`: 6 specs Playwright

### F7) Subcarpetas root `tests/e2e/` (snapshot)
- `regression`: 32
- `charts`: 15
- `metrics`: 5
- `conversation`: 4
- `clarification`: 3
- `security`: 2

## Proposed classification matrix

| Actual | Clasificación propuesta | Razon |
|---|---|---|
| `tests/e2e/charts` | `tests/system/chat/charts` | Chat API + chart payload validations |
| `tests/e2e/conversation` | `tests/system/chat/conversation` | Multi-turn via API |
| `tests/e2e/clarification` | `tests/system/chat/clarification` | Clarification NLU via API |
| `tests/e2e/security` | `tests/system/security` | Security behavior black-box API |
| `tests/e2e/regression` | `tests/regression/system` | Regression funcional cross-feature |
| `tests/e2e/metrics` (RPC/API) | `tests/contract/mcp` o `tests/system/mcp` | Mezcla de contrato y flujo real |
| `apps/backend/tests/e2e/*` | `apps/backend/tests/system/*` | Full-stack backend sin browser |
| `apps/web/e2e` con mocks | `apps/web/e2e-mocked` | UI integration con network stubs |
| Web E2E real (nuevo) | `apps/web/e2e-live` | Browser + backend real |

## References
- `tests/utils/helpers.py`
- `tests/e2e/run_all.py`
- `tests/runner/suites.py`
- `scripts/testing/test-runner.sh`
- `.github/workflows/ci.yml`
- `apps/web/e2e/fixtures/index.ts`
- `apps/web/e2e/utils/mock-api.ts`
- `apps/backend/tests/e2e/test_bank_analytics_integration.py`
- `apps/backend/tests/conftest.py`
