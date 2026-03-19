# Plan

## Objective
- Unificar taxonomia de pruebas para que carpeta, runner y CI reflejen el nivel real de test: `unit`, `integration`, `contract`, `system`, `e2e-live`.

## Scope
### In
- Definir y adoptar estructura target en root, backend y web.
- Reclasificar suites mal nombradas (`tests/e2e` root y web e2e mocked).
- Actualizar CI para ejecutar/categorizar por capa real.
- Mantener compatibilidad temporal en comandos existentes (`make`, `tests.runner`).

### Out
- Reescritura masiva de asserts/logica de tests.
- Replantear cobertura funcional de producto.
- Cambios de infraestructura ajenos a pipeline de tests.

## Phases
### Phase 1 - Taxonomia y convenciones (documental + wiring inicial)
- [ ] Acordar definiciones operativas:
  - `unit`: sin IO externo real.
  - `integration`: integra componentes internos (DB/cache/service).
  - `contract`: valida schemas/contratos API-RPC.
  - `system`: flujo black-box backend sin browser.
  - `e2e-live`: browser + backend real.
- [ ] Agregar convencion de naming para jobs CI y suites runner.
- [ ] Definir tags/markers para separar `e2e-mocked` vs `e2e-live`.

#### Phase 1 Files
- `docs/kanban/README.md` (si se decide actualizar definiciones formales)
- `apps/backend/pytest.ini`
- `apps/backend/tests/conftest.py`
- `tests/runner/suites.py`

### Phase 2 - CI realignment (sin movimiento masivo de archivos aun)
- [ ] Renombrar jobs CI para evitar ambiguedad:
  - `test-web-e2e-smoke` -> `test-web-ui-mocked-smoke`
  - nuevo `test-web-e2e-live-smoke` (opt-in/manual/nightly)
- [ ] Añadir job para `tests/system` (inicialmente manual/nightly).
- [ ] Mantener gating de PR en suites rápidas (`unit + integration smoke + ui-mocked smoke`).
- [ ] Ejecutar `system` y `e2e-live` en horarios/dispatch para costo-control.

#### Phase 2 Files
- `.github/workflows/ci.yml`
- `.github/workflows/cd.yml` (si aplica smoke taxonomy en deploy)

### Phase 3 - Reorganizacion de paths (migracion progresiva)
- [ ] Crear nuevos directorios objetivo:
  - `tests/system/**`, `tests/contract/**`, `tests/regression/system/**`
  - `apps/web/e2e-mocked/**`, `apps/web/e2e-live/**`
  - `apps/backend/tests/system/**`
- [ ] Mover suites por bloques, empezando por root:
  - `tests/e2e/charts` -> `tests/system/chat/charts`
  - `tests/e2e/conversation` -> `tests/system/chat/conversation`
  - `tests/e2e/clarification` -> `tests/system/chat/clarification`
  - `tests/e2e/security` -> `tests/system/security`
  - `tests/e2e/regression` -> `tests/regression/system`
- [ ] Separar `tests/e2e/metrics` en:
  - `tests/contract/mcp` (shape/versioning/list tools)
  - `tests/system/mcp` (flows reales RPC/API)
  - unit/service tests movidos a `apps/backend/tests/unit/**` donde aplique.

#### Phase 3 Files
- `tests/e2e/**` (moves)
- `tests/system/**` (new)
- `tests/contract/**` (new)
- `apps/backend/tests/e2e/**` (moves)
- `apps/backend/tests/system/**` (new)
- `apps/web/e2e/**` (split into mocked/live)

### Phase 4 - Compatibilidad y deprecaciones controladas
- [ ] Actualizar `tests.runner` para nuevas suites:
  - `system_chat`, `system_regression`, `contract_mcp`, `web_e2e_live`, `web_ui_mocked`.
- [ ] Mantener alias legacy por una ventana definida:
  - `e2e_all` -> apunta temporalmente a `system + e2e-live`.
- [ ] Emitir warning de deprecacion al invocar nombres legacy.

#### Phase 4 Files
- `tests/runner/suites.py`
- `tests/runner/__main__.py`
- `Makefile`
- `scripts/testing/test-runner.sh`
- `tests/README.md`

### Phase 5 - Cierre operativo
- [ ] Ejecutar smoke matrix final y documentar resultados.
- [ ] Confirmar que PR gating no se degrada en tiempo.
- [ ] Congelar fecha de retiro de aliases legacy.

#### Phase 5 Files
- `docs/kanban/<ticket>/validate.md`
- `.github/workflows/ci.yml`
- `tests/README.md`

## Validation Commands
- `python3.11 -m pytest -q apps/backend/tests/unit --maxfail=1`
- `python3.11 -m pytest -q apps/backend/tests/integration -m integration --maxfail=1`
- `python3.11 -m pytest -q tests/system --maxfail=1`
- `python3.11 -m pytest -q tests/contract --maxfail=1`
- `cd apps/web && pnpm test`
- `cd apps/web && E2E_USE_API_MOCKS=1 pnpm test:e2e -- --project=chromium`
- `cd apps/web && E2E_USE_API_MOCKS=0 pnpm test:e2e -- --project=chromium --grep @live`
- `python3.11 -m tests.runner --list`

## Success Criteria
- [ ] Toda suite tiene clasificacion unica y consistente por nivel.
- [ ] `E2E` queda reservado para browser + backend real (`e2e-live`).
- [ ] Las suites API black-box quedan bajo `system`.
- [ ] CI muestra cobertura por capa (unit/integration/system/ui-mocked/e2e-live) sin ambigüedad.
- [ ] `make test` y `tests.runner` siguen funcionando durante y despues de la migracion.
