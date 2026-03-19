# Bank Advisor V1.1 - Kanban

> **Source of Truth**: Este directorio (`docs/kanban/`) es la fuente de verdad para el desarrollo. Se sincroniza con GitHub Issues (labels `status:*`) para visibilidad del equipo.

## Estructura de directorios

```
docs/kanban/
├── BACKLOG/               # Tareas pendientes de iniciar
├── DOING/                 # Tareas en progreso (máx 2)
├── REVIEW/                # Listas para revisión/QA antes de cerrar
├── DONE/                  # Tareas completadas
└── TEMPLATE_TASK_FOLDER/  # Plantilla para nuevas tareas
```

## Comandos MCP (Claude Code)

El proyecto incluye un MCP server (`tools/mcp-kanban-sync/` v4.0.0, 22 tools).

### Comandos principales

| Comando | Descripción |
|---------|-------------|
| `kanban_summary` | Resumen del board (conteos y prioridades) |
| `kanban_atomic_move` | Mover tarea en 3 capas: local + MongoDB + GitHub Issue |
| `kanban_create_task` | Crear tarea nueva en BACKLOG |
| `kanban_check_drift` | Verificar sincronización local vs MongoDB |
| `triage_list` | Listar reportes de feedback triage |
| `triage_detail` | Leer contenido completo de un triage por fecha |

Ver `tools/mcp-kanban-sync/README.md` para la referencia completa de los 22 tools.

### Flujo de sincronización

```
kanban_atomic_move ──► LOCAL (filesystem) + MONGODB (feedback) + GITHUB_ACTION
                                                                      │
                                              Claude Code ejecuta ◄───┘
                                              gh issue edit + gh issue close
```

---

## Convenciones de nombrado

### Tareas (carpetas con documentación completa)

```
{YYYY-MM-DD}[-HHMM]__{TYPE}__{descripcion-corta}/
├── card.md      # Descripción principal, estado, actualizaciones
├── plan.md      # Plan de implementación (opcional en quick-fix)
├── research.md  # Investigación y hallazgos (opcional en quick-fix)
└── validate.md  # Criterios de validación y resultados
```

> **Justificación**: La fecha al inicio permite ordenamiento cronológico natural al listar directorios (`ls`, exploradores de archivos).

### Tipos de tareas

| Tipo | Uso | Prioridad visual |
|------|-----|------------------|
| `BUG` | Bugs de producción | 🔴 Critical, 🟠 High, 🟡 Medium |
| `SEC` | Vulnerabilidades de seguridad | 🔴 Critical |
| `TASK` | Features y mejoras | 🔵 Normal |
| `REFACTOR` | Refactorizaciones | 🔵 Normal |

### Ejemplos

```
2026-01-19-1900__TASK__bank-advisor-grpc-migration/
2026-01-28__SEC__nextjs-15-upgrade-cve/
2026-01-30__BUG__wrong-month-data-mapping/
2026-01-30-1415__BUG__icap-decimal-shift/
```

### Nombres legacy

Tareas creadas antes de 2026-02-03 pueden tener el formato antiguo `{TYPE}-{DATE}__desc`. No es necesario renombrarlas, pero nuevas tareas deben usar el formato nuevo.

---

## Ciclo de vida de tareas

```
BACKLOG ──────► DOING ──────► REVIEW ──────► DONE
   │              │
   │   máx 2      │   requiere
   │   tareas     │   validación
   └──────────────┴──────────────
```

---

## Definición de Terminado (DoD)

Para mover cualquier tarea a **DONE**, se deben cumplir los requisitos según el tipo:

### Por tipo de tarea

| Tipo | Requisitos para DONE |
|------|----------------------|
| `BUG-*` | E2E tests en `tests/e2e/` + tests passing contra backend real |
| `SEC-*` | Dependabot 0 alerts + CI verde + no regresiones |
| `TASK-*` | E2E tests en `tests/e2e/` + unit tests + lint passing |
| `REFACTOR-*` | Tests existentes siguen passing + lint passing |

### Bugs de Producción (`BUG-*`)

| Requisito | Descripción | Obligatorio |
|-----------|-------------|-------------|
| **E2E Tests** | Crear tests en `tests/e2e/` que validen el fix | ✅ |
| **Tests Passing** | Ejecutar contra backend real (requiere `make dev`) | ✅ |
| **Test Coverage** | 2-3 test cases cubriendo diferentes escenarios | ✅ |
| **Validators** | Funciones de validación que detecten el bug si reaparece | ✅ |
| **Deploy a Producción** | Fix desplegado en el servidor de producción | ✅ |
| **Confirmación del Usuario** | El usuario reporta que el bug ya no persiste en producción | ✅ |

> **Regla de cierre**: Un bug solo se mueve a DONE cuando el usuario confirma en producción que el problema ya no se reproduce. Hasta entonces, el ticket permanece en DOING con fase `validate`. Esto aplica a todos los bugs sin excepción.
>
> **Flujo**: Fix local → E2E tests pass → Deploy → Usuario prueba → Usuario confirma → DONE

#### Patrón de E2E Test para Bugs

```python
# tests/e2e/regression/test_{YYYY_MM_DD}_{tipo}_{descripcion}.py
# Ejemplo: test_2026_01_30_bug_icap_decimal.py

BugTestCase(
    bug_id="{YYYY-MM-DD}__{TYPE}__{desc}",  # ID único del bug
    description="...",                     # Qué valida este test
    query="...",                           # Query que reproduce el bug
    expected_behavior="...",               # Comportamiento esperado
    validation_fn="validate_xxx",          # Función validadora
    expected_keywords=["..."],             # Keywords que DEBEN aparecer
    forbidden_keywords=["..."]             # Keywords que NO deben aparecer
)
```

#### Ejecutar Tests

```bash
# Requisito: backend corriendo
make dev

# Ejecutar tests E2E del bug
python tests/e2e/regression/test_{YYYY_MM_DD}_{tipo}_{descripcion}.py

# Resultado requerido: "✅ All tests PASSED!"
```

### Tareas de Seguridad (`SEC-*`)

| Requisito | Descripción | Obligatorio |
|-----------|-------------|-------------|
| **Dependabot Clear** | 0 alerts en GitHub Dependabot | ✅ |
| **CI Verde** | Pipeline de CI pasa | ✅ |
| **No Regressions** | Tests existentes siguen pasando | ✅ |

### Tareas de Feature (`TASK-*`)

| Requisito | Descripción | Obligatorio |
|-----------|-------------|-------------|
| **E2E Tests** | Crear tests en `tests/e2e/` que validen la feature | ✅ |
| **Unit Tests** | Unit tests para código nuevo/modificado | ✅ |
| **Tests Passing** | Ejecutar contra backend real (requiere `make dev`) | ✅ |
| **Lint Passing** | `make pre-deploy.lint` | ✅ |
| **CI Verde** | Pipeline de CI pasa | ✅ |

#### Ejecutar Tests para TASK-*

```bash
# Requisito: backend corriendo
make dev

# Ejecutar tests E2E de la feature
python tests/e2e/{categoria}/test_{YYYY_MM_DD}_{tipo}_{descripcion}.py

# Resultado requerido: "✅ All tests PASSED!"
```

### Refactorizaciones (`REFACTOR-*`)

| Requisito | Descripción | Obligatorio |
|-----------|-------------|-------------|
| **No Regressions** | Tests existentes siguen pasando | ✅ |
| **Lint Passing** | `make pre-deploy.lint` | ✅ |
| **CI Verde** | Pipeline de CI pasa | ✅ |

---

### Fases dentro de DOING

Cada tarea en progreso pasa por fases documentadas en `card.md`:

1. **Research** - Investigación y análisis de causa raíz
2. **Plan** - Definición de la solución
3. **Implement** - Desarrollo y tests
4. **Validate** - Verificación de criterios de aceptación

---

## Guía de documentación

Cada tarea debe incluir documentación completa:

| Sección | Descripción | Obligatorio |
|---------|-------------|-------------|
| **Problema** | Descripción clara del problema + feedback del usuario | ✅ |
| **Causa raíz** | Causa raíz técnica identificada | ✅ |
| **Solución** | Descripción de la solución implementada | ✅ |
| **Verificación** | Checklist de criterios validados | ✅ |
| **Feedback del usuario** | Citas textuales si viene de producción | Si aplica |

### Tareas Quick-Fix

Tareas con solo `card.md` cuando son:
- Hotfixes urgentes sin tiempo para documentación completa
- Cambios pequeños de configuración
- Bug fixes de una línea

Se identifican con el sufijo `(quick-fix)` en el card.md.

---

## GitHub Issue Labels

| Label | Descripción |
|-------|-------------|
| `status:backlog` | Tarea en backlog |
| `status:doing` | Tarea en progreso |
| `status:review` | Tarea en review |
| `status:done` | Tarea completada (issue cerrado) |
| `type:bug` | Bug report |
| `type:task` | Feature/task |
| `type:refactor` | Refactorización |
| `type:security` | Seguridad |
| `triage:feedback` | Generado desde feedback triage |

Usar `kanban_summary` para datos en tiempo real.

---

## Enlaces del proyecto

- **GitHub Issues**: [saptiva-ai/octavios-chat-bajaware_invex](https://github.com/saptiva-ai/octavios-chat-bajaware_invex/issues)
- **GitHub Wiki**: [Documentación](https://github.com/saptiva-ai/octavios-chat-bajaware_invex/wiki)
- **Repo**: `octavios-chat-bajaware_invex`
- **Proyecto padre**: CopilotOS - Bank Advisor Invex
- **Producción**: https://bankadvisor.saptiva.com/dashboard

---

## Documentación relacionada

- `.claude/rules/70_workflow_rails.md` — Reglas de workflow y fases
- `tools/mcp-kanban-sync/README.md` — Documentación técnica del servidor MCP (22 herramientas)
- `docs/reports/README.md` — Reportes efímeros (Playwright, feedback triage)
