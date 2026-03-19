# Validation

## Commands
- `python3.11 -m pytest -q apps/backend/tests/unit --maxfail=1`
- `python3.11 -m pytest -q apps/backend/tests/integration -m integration --maxfail=1`
- `python3.11 -m pytest -q tests/system --maxfail=1`
- `python3.11 -m pytest -q tests/contract --maxfail=1`
- `cd apps/web && pnpm test`
- `cd apps/web && E2E_USE_API_MOCKS=1 pnpm test:e2e -- --project=chromium`
- `cd apps/web && E2E_USE_API_MOCKS=0 pnpm test:e2e -- --project=chromium --grep @live`
- `python3.11 -m tests.runner --list`

## Results
### Automated tests
- NOT RUN (research/plan only): este ticket documenta propuesta de reorganizacion y plan de ejecucion, sin cambios implementados de codigo o paths de tests.

### Verification checklist
- PASS: se definio taxonomia objetivo por capas.
- PASS: se documento mapeo de rutas actuales a rutas objetivo.
- PASS: se documento plan incremental para CI + runner + compatibilidad legacy.
- PASS: se incluyeron comandos de validacion para la fase de implementacion.

## Notes
- Este ticket permanece en BACKLOG hasta aprobacion de la estrategia de migracion.
- Recomendado ejecutar primero un spike pequeño (1 categoria, por ejemplo `tests/e2e/charts` -> `tests/system/chat/charts`) antes de migracion completa.
