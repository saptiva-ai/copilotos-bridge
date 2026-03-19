# docs/reports/

Directorio de reportes efímeros generados por CI, Playwright y triages de feedback.

## Estructura

```
docs/reports/
├── README.md               ← este archivo (tracked en git)
├── .gitignore              ← reglas locales
├── feedback_triage/        ← reportes diarios de triage (gitignored)
│   ├── YYYY-MM-DD.md       ← reporte diario consolidado (estándar)
│   └── YYYY-MM-DD-tracker.md ← inventario histórico (excepcional)
└── playwright/             ← outputs de Playwright E2E (gitignored)
    ├── *.json              ← resultados de test runner
    └── *.pdf               ← screenshots/traces
```

## Reglas

### 1. Nada se trackea en git excepto este README y `.gitignore`
Todos los reportes son **efímeros** y gitignored. Si un reporte necesita
persistir (ej. post-mortem, audit), va en `docs/context/` o en el kanban task.

### 2. Convenciones de nombrado

| Directorio | Formato | Ejemplo | Cuándo |
|---|---|---|---|
| `feedback_triage/` | `YYYY-MM-DD.md` | `2026-02-10.md` | Siempre (1 por día) |
| `feedback_triage/` | `YYYY-MM-DD-tracker.md` | `2026-02-05-tracker.md` | Solo inventarios históricos |
| `playwright/` | `playwright-e2e__{suite}__{ts}.{json,pdf}` | `playwright-e2e__chat__20260209T054221Z.json` | Cada corrida E2E |

**Regla de naming para feedback_triage**:
- Un archivo por día: `YYYY-MM-DD.md`
- Sin sufijos (`-triage`, `-raw`, etc.) — el formato consolidado ya incluye todo
- Excepción: `-tracker` para inventarios de mapeo feedback→ticket (legacy)

### 3. Retención
- **feedback_triage/**: conservar últimos 30 días. Borrar manualmente o con script.
- **playwright/**: conservar última semana. CI puede limpiar automáticamente.
- No hay limpieza automática configurada — es responsabilidad del desarrollador.

### 4. Generación
- **Playwright**: generado por `pnpm test:e2e` en `apps/web/`. El script
  `run-e2e-with-pdf-report.sh` deposita en `docs/reports/playwright/`.
- **Feedback triage**: generado manualmente vía Claude Code usando datos de
  MongoDB production (requiere SSH tunnel activo).

### 5. No crear subdirectorios adicionales
Si aparece una nueva categoría de reporte, agregarla a este README y al
`.gitignore` antes de generar archivos. Máximo 3 subdirectorios de primer nivel.

---

## Integración Kanban / GitHub Issues

Los reportes de `feedback_triage/` alimentan el pipeline de tickets del kanban.

### Flujo

```
MongoDB (feedback) ──→ feedback_triage/YYYY-MM-DD.md ──→ Kanban tasks ──→ GitHub Issues
```

1. **Triage diario**: se consulta MongoDB vía SSH tunnel, se genera `YYYY-MM-DD.md`
2. **Creación de tickets**: los bugs identificados en el triage se crean como tasks
   en `docs/kanban/BACKLOG/` usando `kanban_create_task` (MCP kanban-sync)
3. **Sync a GitHub**: `kanban_atomic_move` dispara `<!-- GITHUB_ACTION -->` que
   actualiza labels en el GitHub Issue correspondiente

### MCP Tools involucrados

| Paso | Herramienta MCP | Acción |
|---|---|---|
| Consultar feedback | API interna o Bash (mongo) | Query thumbs-down del día |
| Listar triages | `triage_list` | Ver reportes disponibles con métricas |
| Leer triage | `triage_detail` | Contenido completo de un reporte por fecha |
| Crear ticket | `kanban_create_task` | Task en BACKLOG con link al feedback ID |
| Mover ticket | `kanban_atomic_move` | BACKLOG → DOING → REVIEW → DONE |
| Sync GitHub | `gh issue edit` + `gh issue close` | Actualizar labels en GitHub Issue |

### Convención de ticket desde triage

Cuando un triage identifica un bug, el ticket se crea con:
- **Nombre**: `YYYY-MM-DD__BUG__<slug-descriptivo>`
- **Contenido**: link al feedback ID + descripción del issue
- **Prioridad**: basada en frecuencia de ocurrencia en el triage
