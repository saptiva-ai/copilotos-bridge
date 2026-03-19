---
id: "REFACTOR-2026-02-16__test-taxonomy-reorganization"
title: "Reorganizar taxonomia de tests (unit/integration/system/e2e) y alinear CI"
status: "BACKLOG"
phase: "Research"
scope_in:
  - "Inventariar las suites actuales en tests/ (root), apps/backend/tests y apps/web/e2e"
  - "Definir taxonomia objetivo siguiendo best practices (testing pyramid)"
  - "Proponer mapeo carpeta-a-carpeta para corregir nomenclatura e2e vs integration/system"
  - "Alinear GitHub CI para que los jobs representen el tipo real de test"
  - "Definir plan de migracion por fases sin romper comandos existentes (Makefile/scripts)"
scope_out:
  - "Reescritura de asserts o logica de producto en tests existentes"
  - "Cambios funcionales en backend/web fuera de testing tooling y estructura"
  - "Limpieza historica de artifacts *.json de resultados legacy"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "python3.11 -m pytest -q apps/backend/tests/unit --maxfail=1"
  - "python3.11 -m pytest -q apps/backend/tests/integration -m integration --maxfail=1"
  - "python3.11 -m pytest -q tests/system --maxfail=1"
  - "cd apps/web && pnpm test"
  - "cd apps/web && E2E_USE_API_MOCKS=1 pnpm test:e2e -- --project=chromium"
  - "cd apps/web && E2E_USE_API_MOCKS=0 pnpm test:e2e -- --project=chromium --grep @live"
  - "python3.11 -m tests.runner --list"
pr_files: []
test_status: "research-only"
---

# Summary
- Objective: corregir la taxonomia de testing para que `unit`, `integration`, `system` y `e2e` signifiquen lo mismo en carpeta, runner, Makefile y CI.
- Constraint: mantener continuidad operativa (sin romper comandos existentes en una sola iteracion), ejecutando migracion por fases con compatibilidad.

# Problema
Hoy existe desalineacion entre nombre y comportamiento real de varias suites:

1. `tests/e2e/` (root) contiene mayormente pruebas black-box contra API/SSE (backend real), no flujo UI de usuario final.
2. `make test T=e2e` ejecuta Playwright (web), lo cual usa otro significado de E2E distinto a `tests/e2e/` root.
3. CI de GitHub no ejecuta actualmente `tests/e2e/` root, pero el nombre "E2E" sugiere criticidad alta para release.
4. `apps/web/e2e` corre con mocks por default (`E2E_USE_API_MOCKS=1`), por lo que son mas "UI integration mocked" que E2E live.
5. En backend hay archivos `*_integration.py` bajo `apps/backend/tests/e2e/`, mezclando dos taxonomias en la misma carpeta.

Esto dificulta:
- priorizacion de fallas en CI,
- lectura de cobertura real por nivel,
- decision de que tests deben bloquear merge/deploy.

# Evidencia (inventario actual)

| Capa | Ruta | Cantidad | Comportamiento dominante |
|---|---|---:|---|
| Root | `tests/e2e/` | 61 files | API/SSE black-box, runners Python por script |
| Root | `tests/integration/` | 9 files | Integracion entre servicios (backend/file-manager/embedding) |
| Backend | `apps/backend/tests/e2e/` | 7 files | Full-stack API/service (sin browser) |
| Backend | `apps/backend/tests/integration/` | 16 files | Integracion FastAPI + DB + componentes |
| Web | `apps/web/e2e/tests/*.spec.ts` | 6 specs | UI con Playwright; mocks API por default |

# Estructura objetivo propuesta (taxonomia canonica)

```text
tests/
├── unit/                      # Lógica aislada (sin red/DB real)
├── contract/                  # Contratos API/RPC (shape/versioning)
│   ├── mcp/
│   └── api/
├── integration/               # Integración entre componentes/servicios
│   ├── services/
│   └── backend-adapters/
├── system/                    # Flujo end-to-end backend (sin browser)
│   ├── chat/
│   │   ├── charts/
│   │   ├── clarification/
│   │   ├── conversation/
│   │   └── security/
│   ├── mcp/
│   └── regression/
├── smoke/
├── fixtures/
└── runner/

apps/backend/tests/
├── unit/
├── integration/
├── system/                    # antes apps/backend/tests/e2e
├── regression/
├── mcp/
└── smoke/

apps/web/
├── src/**/__tests__/          # unit/component/integration
├── e2e-mocked/                # Playwright con mocks (actual e2e)
└── e2e-live/                  # Playwright con backend real
```

# Causa raiz
- La taxonomia crecio de forma organica: se uso "e2e" para cualquier test de alto nivel, incluso cuando no habia browser.
- La separacion "por comportamiento tecnico" (mocked UI vs live UI, contract vs integration vs system) nunca se formalizo en CI.
- Se mantuvieron runners legacy por script (`python test_*.py`) junto con suites pytest marcadas, sin una capa unica de orquestacion.

# Solucion propuesta
1. Adoptar taxonomia canonica por nivel de prueba (piramide + system tests).
2. Reservar `E2E` para flujo UI real (browser + backend real + infraestructura minima).
3. Reclasificar `tests/e2e/` root como `tests/system/` y/o `tests/contract` segun caso.
4. Separar Playwright mocked de Playwright live en carpetas/proyectos distintos.
5. Alinear CI con jobs nombrados por taxonomia real y una politica clara de bloqueo (PR vs nightly).

# Criterios de aceptacion
- [ ] Existe un mapeo 1:1 de suites actuales a la taxonomia objetivo.
- [ ] CI usa nombres de jobs consistentes con la capa (`unit`, `integration`, `system`, `e2e-live`).
- [ ] `tests/e2e` deja de usarse para pruebas sin browser.
- [ ] Playwright mocked y live se ejecutan por separado y con etiquetado explicito.
- [ ] Se mantiene backward compatibility temporal en `make test`/`tests.runner` durante la migracion.

# Updates
- 2026-02-16 12:16 - Ticket creado con inventario completo, diagnostico de nomenclatura y propuesta de reorganizacion por fases.
