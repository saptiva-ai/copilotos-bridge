# Guía de Workflow: Claude Code para OctaviOS

> Documento para el equipo de desarrollo - 30 dic 2025 (v1.1)
> Nota: estado histórico. Actualmente `/quick-checks` y `/infra-doctor` están deprecados y `plan-architect` está aparcado; ver `CLAUDE.md`.

---

## TL;DR

Claude Code es nuestro copiloto de desarrollo. Esta guía explica:
1. Cómo está organizado el contexto del proyecto
2. Los 6 agentes especializados y cuándo usarlos
3. El flujo desde BRD/PRD hasta código entregado
4. Comandos y herramientas del día a día

---

## 1. Estructura del Proyecto

### 1.1 Namespace `.claude/` (Context Engineering)

```
.claude/
├── agents/           # Subagentes especializados (6 activos)
│   ├── repo-scout.md       # Explore: mapear repo
│   ├── plan-architect.md   # Plan: diseñar solución
│   ├── test-runner.md      # Test: ejecutar y analizar
│   ├── code-reviewer.md    # Review: revisar cambios
│   ├── doc-sync.md         # Docs: sincronizar documentación
│   └── infra-doctor.md     # Ops: diagnosticar servicios
│
├── commands/         # Slash commands (/)
│   ├── quick-checks.md     # /quick-checks - suite mínima
│   ├── repo-map.md         # /repo-map - mapear estructura
│   ├── dev-up.md           # /dev-up - levantar stack
│   ├── api-test.md         # /api-test - tests backend
│   ├── web-test.md         # /web-test - tests frontend
│   └── infra-doctor.md     # /infra-doctor - diagnóstico
│
├── rules/            # Reglas automáticas por contexto
│   ├── 00_security.md      # Siempre activa
│   ├── 10_infra.md         # Al editar infra/
│   ├── 20_testing.md       # Al editar tests
│   ├── 30_backend_python.md # Al editar apps/backend/
│   ├── 40_frontend_web.md  # Al editar apps/web/
│   ├── 50_orchestration.md # Flujo de trabajo
│   └── 60_agent_hygiene.md # Gestión de agentes
│
├── skills/           # Workflows on-demand
│   ├── explore/            # Navegación del codebase
│   ├── plan/               # Planificación de implementación
│   ├── code/               # Convenciones de código
│   ├── test/               # Guía de testing
│   ├── prd-builder/        # Creación de mini-PRDs
│   ├── orchestration-playbooks/
│   └── project-navigation/
│
└── output/           # Outputs transitorios (gitignored)
    ├── quick_checks.md
    ├── repo_map.md
    └── infra_doctor.md
```

### 1.2 Documentación de Negocio (`docs/context/`)

```
docs/context/
├── BRD.md                  # Business Requirements (fuente de verdad)
├── SPRINT_CURRENT.md       # Épicas del sprint actual
├── PATTERNS.md             # Patrones de código del proyecto
│
├── PRD/                    # Mini-PRDs por épica
│   ├── README.md           # Índice con status
│   ├── EPIC-HU1.md         # Query Multi-Banco
│   ├── EPIC-HU2.md         # Comparación Multi-Banco
│   ├── EPIC-HU3.md         # UI Clarificación
│   ├── EPIC-HU4.md         # RAG con Glosario
│   ├── EPIC-HU5.md         # Sistema Feedback
│   └── GAPS.md             # Deuda técnica/funcional
│
└── architecture/           # Arquitectura modular
    ├── README.md           # Índice
    ├── OVERVIEW.md
    ├── AGENTS.md
    ├── DATA.md
    ├── SECURITY.md
    ├── OPERATIONS.md
    ├── ROADMAP.md
    └── COVERAGE.md
```

---

## 2. Agentes Especializados

### 2.1 Tabla de Agentes

| Agent | Fase | Model | Propósito |
|-------|------|-------|-----------|
| `repo-scout` | Explore | haiku | Mapear estructura del repo y entrypoints |
| `plan-architect` | Plan | sonnet | Diseñar planes de implementación |
| `test-runner` | Test | haiku | Ejecutar tests y analizar fallos |
| `code-reviewer` | Review | sonnet | Revisar código para bugs y seguridad |
| `doc-sync` | Docs | haiku | Sincronizar documentación con código |
| `infra-doctor` | Ops | haiku | Diagnosticar problemas de infraestructura |

### 2.2 Formato TOON (Task-Output-Ownership-Notes)

Cada agente sigue el formato TOON:

```markdown
# Task      → Qué hace (objetivo específico)
# Output    → Qué entrega (formato concreto)
# Ownership → IS/NOT responsible (boundaries claros)
# Notes     → Constraints, edge cases, delegaciones
```

### 2.3 Cuándo Usar Cada Agente

| Situación | Agente | Siguiente Paso |
|-----------|--------|----------------|
| "Necesito entender este codebase" | `repo-scout` | Leer output, luego skill explore |
| "Voy a implementar una feature" | `plan-architect` | Obtener aprobación, luego codificar |
| "Hice cambios, ejecutar tests" | `test-runner` | Si falla, corregir y reintentar |
| "Revisar cambios antes de commit" | `code-reviewer` | Atender feedback |
| "Actualizar docs post-implementación" | `doc-sync` | Revisar cambios |
| "Servicios caídos o unhealthy" | `infra-doctor` | Seguir remediación |

### 2.4 Cadena de Delegación

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FLUJO DE DESARROLLO                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  repo-scout → plan-architect → [code] → test-runner → code-reviewer    │
│       │             │            │           │              │          │
│       │             │            │           │              │          │
│       ▼             ▼            ▼           ▼              ▼          │
│   "Entiendo     "Plan        Skills    "Tests         "Aprobado"       │
│    el repo"    aprobado"      o         pasan"            │            │
│                              externos                      │            │
│                                                            ▼            │
│                                                        doc-sync        │
│                                                            │            │
│                                                            ▼            │
│                                                     "Docs updated"     │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  DELEGACIONES DE ERROR:                                                │
│  • test-runner exit 2 → infra-doctor                                   │
│  • plan-architect gap bloqueante → flag y parar                        │
│  • code-reviewer issue crítico → bloquear merge                        │
│  • doc-sync docs stale → flag only, no fix                             │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.5 Selección de Modelo

| Modelo | Agentes | Razón |
|--------|---------|-------|
| `haiku` | repo-scout, test-runner, doc-sync, infra-doctor | Tareas I/O-bound, determinísticas, velocidad importa |
| `sonnet` | plan-architect, code-reviewer | Requiere razonamiento profundo y juicio |

---

## 3. Flujo de Trabajo: BRD → Código

### Fase 0: Documentos Fuente

```
BRD (negocio)     PRD (producto)
    │                  │
    └────────┬─────────┘
             │
             ▼
      Transformación
```

### Fase 1: Transformación (1 vez por proyecto/release)

**Skill usado:** `prd-builder`

| Paso | Acción | Output |
|------|--------|--------|
| 1 | Cargar BRD.md como contexto | - |
| 2 | Parsear PRD fuente (.tex/.pdf) | - |
| 3 | Para cada épica, extraer: | |
| | - **Por Qué** (cita textual BRD) | Alineación de negocio |
| | - **Cómo** (mapeo arquitectura) | Componentes afectados |
| | - **Qué** (entregables E1, E2...) | Criterios de completado |
| 4 | Generar mini-PRD | `EPIC-HUx.md` |
| 5 | Consolidar gaps | `GAPS.md` |

### Fase 2: Ciclo de Desarrollo (repetir por épica)

```
┌─────────────────────────────────────────────────────────────┐
│  EXPLORE → PLAN → CODE → TEST → REVIEW → DOCS              │
│     │        │      │      │       │       │                │
│   repo-   plan-  skills  test-  code-   doc-                │
│   scout  architect  +    runner reviewer sync               │
│                  external                                    │
│                  agents                                      │
└─────────────────────────────────────────────────────────────┘
```

| Etapa | Agente/Skill | Qué hace |
|-------|--------------|----------|
| **EXPLORE** | `repo-scout` + skill `explore` | Entender código existente, ubicar archivos |
| **PLAN** | `plan-architect` | Diseñar solución, obtener aprobación |
| **CODE** | skill `code` + externos | Implementar siguiendo convenciones |
| **TEST** | `test-runner` | Ejecutar tests, analizar fallos |
| **REVIEW** | `code-reviewer` | Revisar para bugs, seguridad, convenciones |
| **DOCS** | `doc-sync` | Actualizar status en PRDs y GAPS.md |

### Fase 3: Entrega

- Código implementado con tests
- Mini-PRD actualizado (status: DONE)
- Gaps cerrados/documentados
- Commits con Conventional Commits

---

## 4. Comandos del Día a Día

### Desarrollo

```bash
make dev                    # Levantar stack completo
make health                 # Verificar servicios
make logs S=backend         # Ver logs de un servicio
```

### Testing

```bash
make test T=api             # Tests backend (en Docker)
make test T=web             # Tests frontend (en Docker)
make test-local FILE="..."  # Test específico local
```

### Claude Code (Slash Commands)

| Comando | Qué hace |
|---------|----------|
| `/quick-checks` | Suite mínima de tests |
| `/repo-map` | Mapear estructura del repo |
| `/dev-up --start` | Levantar stack si está caído |
| `/infra-doctor` | Diagnosticar problemas de infra |
| `/api-test` | Tests de API backend |
| `/web-test` | Tests de frontend |

### Exit Codes

```
0 = Éxito
1 = Tests fallaron
2 = Infraestructura no disponible (preflight failure)
```

---

## 5. Ejemplo Práctico: Implementar HU3

### Contexto
- **Épica:** UI Clarificación para queries ambiguas
- **Mini-PRD:** `docs/context/PRD/EPIC-HU3.md`
- **Gaps bloqueantes:** P1-1 (Modo Abstención)

### Sesión con Claude Code (usando agentes)

```
Usuario: Implementa HU3: UI Clarificación

Claude: [Invoca agente: repo-scout]

        ## Repo Map
        - Chat UI: apps/web/src/components/chat/
        - Chat service: apps/backend/src/services/chat_service.py
        - Tests: apps/backend/tests/unit/test_chat*.py

Claude: [Invoca agente: plan-architect]

        ## Implementation Plan: HU3 - UI Clarificación

        **Complexity:** MEDIUM
        **Files:** 2 new, 1 modified

        ### Files to Create
        | File | Purpose |
        |------|---------|
        | apps/web/src/components/chat/ClarificationDialog.tsx | UI component |
        | apps/backend/src/services/clarification_service.py | Business logic |

        ### Files to Modify
        | File | Change |
        |------|--------|
        | apps/backend/src/routers/chat.py | Add endpoint |

        ### Dependencies
        | Dependency | Status | Blocking? |
        |------------|--------|-----------|
        | Gap P1-1 | PENDING | Yes |

        ⚠️ Gap P1-1 es bloqueante. Resolver primero.

        ¿Apruebas este plan?

Usuario: Resuelve P1-1 primero, luego continúa

Claude: [Resuelve P1-1, implementa código]
        [Invoca skill: code]

        Implementando ClarificationDialog.tsx...
        Implementando clarification_service.py...
        Agregando endpoint a chat.py...

Claude: [Invoca agente: test-runner]

        ## Test Results
        **Status:** PASS
        **Exit Code:** 0

        ### Summary
        - Passed: 48
        - Failed: 0
        - Skipped: 2

Claude: [Invoca agente: code-reviewer]

        ## Code Review
        **Verdict:** APPROVE
        **Risk Level:** LOW

        ### Suggestions
        - Consider adding rate limiting to /api/clarify endpoint

        ### Test Coverage
        - [x] clarification_service.py has unit tests
        - [x] ClarificationDialog has component tests

Claude: [Invoca agente: doc-sync]

        ## Documentation Sync Report

        ### Updates Made
        | File | Change |
        |------|--------|
        | EPIC-HU3.md | Status: IN PROGRESS → DONE |
        | GAPS.md | P1-1: OPEN → RESOLVED |

        ✅ Documentación sincronizada
```

---

## 6. Principios de Context Engineering

### 6.1 Progressive Disclosure

Claude carga contexto **on-demand**, no todo upfront:

```
CLAUDE.md (53 líneas)     ← Siempre cargado
    │
    ├── agents/*.md           ← Solo cuando se invoca
    ├── @docs/context/BRD.md  ← Solo cuando se necesita
    ├── @docs/context/PRD/... ← Solo cuando se necesita
    └── skills/*.md           ← Solo cuando se invoca
```

**Beneficio:** Maximiza tokens disponibles para la tarea actual.

### 6.2 Context Before Action

Cada mini-PRD responde **antes de codificar**:

1. **Por Qué** → Cita textual del BRD que justifica la épica
2. **Cómo** → Componentes de arquitectura involucrados
3. **Qué** → Entregables concretos con criterios de completado

### 6.3 Single Source of Truth

| Documento | Es fuente de verdad para |
|-----------|-------------------------|
| `BRD.md` | Requisitos de negocio, métricas |
| `architecture/` | Decisiones técnicas |
| `GAPS.md` | Deuda técnica priorizada |
| `SPRINT_CURRENT.md` | Épicas del sprint |

### 6.4 Gap Management

```
P0 = Blocker (no se puede continuar)
P1 = Crítico (afecta entrega)
P2 = Mejora (nice to have)
```

---

## 7. Roles y Responsabilidades

| Rol | Responsabilidad |
|-----|-----------------|
| **PM** | Mantener BRD.md, SPRINT_CURRENT.md, priorizar GAPS.md |
| **Tech Lead** | Mantener architecture/*.md, aprobar planes de plan-architect |
| **Dev** | Ejecutar ciclo EXPLORE→DOCS, actualizar mini-PRDs |
| **Claude Code** | Asistir con agentes en cada etapa, revisar código |

---

## 8. Checklist de Onboarding

Para nuevos miembros del equipo:

- [ ] Leer `CLAUDE.md` (índice principal, 53 líneas)
- [ ] Ejecutar `make dev` y `make health`
- [ ] Ejecutar `/repo-map` para entender la estructura (usa `repo-scout`)
- [ ] Leer el mini-PRD de la épica asignada (`docs/context/PRD/EPIC-HUx.md`)
- [ ] Revisar `GAPS.md` para contexto de deuda técnica
- [ ] Ejecutar `/quick-checks` para validar setup (usa `test-runner`)
- [ ] Familiarizarse con los 6 agentes en `.claude/agents/`

---

## 9. FAQ

### ¿Cuáles son los 6 agentes disponibles?
`repo-scout`, `plan-architect`, `test-runner`, `code-reviewer`, `doc-sync`, `infra-doctor`

### ¿Dónde encuentro las convenciones de código?
Invoca el skill `code` o lee `.claude/skills/code/SKILL.md`

### ¿Cómo sé qué tests ejecutar?
Invoca `test-runner` o ejecuta `/quick-checks` para la suite mínima

### ¿Qué hago si falla el preflight (exit code 2)?
`test-runner` delegará automáticamente a `infra-doctor`. También puedes ejecutar `/infra-doctor` directamente.

### ¿Cómo agrego un nuevo gap?
Edita `docs/context/PRD/GAPS.md` siguiendo el formato existente con prioridad P0/P1/P2

### ¿Dónde van los outputs de Claude?
En `.claude/output/` (gitignored). No se commitean.

### ¿Qué modelo usa cada agente?
- **haiku** (rápido): repo-scout, test-runner, doc-sync, infra-doctor
- **sonnet** (profundo): plan-architect, code-reviewer

### ¿Cómo sé cuándo usar un agente vs un skill?
- **Agentes**: Tareas autónomas con output estructurado (mapear, testear, revisar)
- **Skills**: Conocimiento on-demand para aplicar durante desarrollo (convenciones, patrones)

---

## Referencias

- [CLAUDE.md](../../CLAUDE.md) - Índice principal
- [BRD.md](../context/BRD.md) - Requisitos de negocio
- [PRD/README.md](../context/PRD/README.md) - Índice de mini-PRDs
- [architecture/README.md](../context/architecture/README.md) - Índice de arquitectura
- [60_agent_hygiene.md](../../.claude/rules/60_agent_hygiene.md) - Gestión de agentes
- [Anthropic Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Context Engineering Guide](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

*Generado: 30 dic 2025 | Versión: 1.1*
*Changelog: Agregados 6 agentes con formato TOON, cadena de delegación, selección de modelos*
