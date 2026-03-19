# Kanban Sync — Manual de operacion

> Sincronizacion de tareas entre 3 almacenes: carpetas locales, MongoDB y GitHub Issues.

---

## 1. Arquitectura

```
 LOCAL (filesystem)          MONGODB (feedback)         GITHUB (Issues)
 docs/kanban/                message_feedback.status    saptiva-ai/octavios-chat-bajaware_invex
 ├── BACKLOG/                ├── Backlog                ├── status:backlog
 ├── DOING/                  ├── In Progress            ├── status:doing
 ├── REVIEW/                 ├── Review                 ├── status:review
 └── DONE/                   └── Done                   └── status:done (closed)
       │                            │                          │
       └────────────────────────────┴──────────────────────────┘
                          MCP kanban-sync v4.0.0
                    (tools/mcp-kanban-sync/src/index.ts)
```

### Mapeo de estados

| Local (carpeta) | MongoDB (`status`) | GitHub (label) | Issue state |
|------------------|--------------------|----------------|-------------|
| BACKLOG          | Backlog            | status:backlog | open |
| DOING            | In Progress        | status:doing   | open |
| REVIEW           | Review             | status:review  | open |
| DONE             | Done               | status:done    | closed |

### Flujo de datos

1. **Local + MongoDB** — el MCP server lo hace en una sola llamada (`kanban_atomic_move`)
2. **GitHub** — el MCP devuelve un bloque `<!-- GITHUB_ACTION -->` que Claude Code ejecuta via `gh` CLI

---

## 2. Prerequisitos

### 2.1 SSH tunnel a produccion

El backend de produccion no expone el puerto 8000 al exterior (firewall GCP).
Se requiere un tunel SSH para que el MCP local alcance la API interna.

```bash
# Abrir tunnel (background, keep-alive)
ssh -L 18000:localhost:8000 jf@$PROD_HOST -N -f -o ServerAliveInterval=30

# Verificar que el tunnel funciona
curl -s http://localhost:18000/health
```

> **Puerto 18000**: se usa para no colisionar con un backend local en 8000.

### 2.2 Variable de entorno

La API interna requiere `BACKEND_INTERNAL_KEY`. Esta variable debe estar:

| Lugar | Variable | Uso |
|-------|----------|-----|
| **PROD** `envs/.env` | `INTERNAL_API_KEY=<key>` | El backend la lee al arrancar |
| **Local** `~/.bashrc` | `export BACKEND_INTERNAL_KEY=<key>` | El MCP la lee via `.mcp.json` |
| **`.mcp.json`** | `"BACKEND_INTERNAL_KEY": "${BACKEND_INTERNAL_KEY}"` | Referencia al env (no hardcodear) |

> La misma key debe coincidir en PROD y local.

### 2.3 GitHub CLI

```bash
# Verificar login
gh auth status

# Si no esta autenticado
gh auth login
```

### 2.4 Configuracion MCP (`.mcp.json`)

```json
{
  "mcpServers": {
    "kanban-sync": {
      "type": "stdio",
      "command": "node",
      "args": ["tools/mcp-kanban-sync/dist/index.js"],
      "env": {
        "KANBAN_PATH": "./docs/kanban",
        "TRIAGE_PATH": "./docs/reports/feedback_triage",
        "BACKEND_URL": "http://localhost:18000",
        "BACKEND_INTERNAL_KEY": "${BACKEND_INTERNAL_KEY}",
        "GITHUB_REPO": "saptiva-ai/octavios-chat-bajaware_invex"
      }
    }
  }
}
```

### 2.5 Build del MCP server

```bash
cd tools/mcp-kanban-sync && npm run build
```

Se debe re-hacer despues de cualquier cambio en `src/`.

---

## 3. Herramientas MCP disponibles

El server expone 22 tools agrupados en 5 categorias.

### 3.1 Lectura

| Tool | Descripcion | Parametros |
|------|-------------|------------|
| `kanban_summary` | Resumen con conteo por status y prioridad | — |
| `kanban_list` | Listar tareas de un status | `status`: BACKLOG, DOING, REVIEW, DONE |
| `kanban_task_detail` | Card completa + research/plan/validate | `task_id` (parcial OK) |
| `kanban_search` | Buscar por keyword en titulo/contenido/ID | `query` |
| `kanban_recent` | Tareas mas recientes por fecha de modificacion | `limit` (default: 10) |
| `kanban_by_priority` | Filtrar por prioridad | `priority`: P0, P1, P2, P3 |
| `kanban_workflow_status` | Estado de archivos auxiliares por tarea activa | — |

### 3.2 Escritura (solo local)

| Tool | Descripcion | Parametros |
|------|-------------|------------|
| `kanban_create_task` | Crear tarea nueva | `type`, `title`, `description`, `status?`, `priority?` |
| `kanban_update_content` | Reemplazar contenido de archivo | `task_id`, `file_type` (card/research/plan/validate), `content` |
| `kanban_append_content` | Agregar al final de un archivo | `task_id`, `file_type`, `content` |
| `kanban_move_task` | Mover entre estados (solo local) | `task_id`, `new_status`, `user_confirmed?` |
| `kanban_set_priority` | Cambiar prioridad | `task_id`, `priority` |
| `kanban_delete_task` | Eliminar tarea (irreversible) | `task_id` |

### 3.3 Cola de sync (legacy)

| Tool | Descripcion |
|------|-------------|
| `kanban_queue_status` | Ver acciones pendientes de sync |
| `kanban_queue_task` | Agregar tarea a la cola |
| `kanban_generate_sync_instructions` | Generar instrucciones para sync via gh CLI |
| `kanban_clear_queue` | Limpiar cola |

### 3.4 Sync atomico (recomendado)

| Tool | Descripcion | Parametros |
|------|-------------|------------|
| **`kanban_atomic_move`** | Mover en 3 capas: local + MongoDB + GitHub Issue | `task_id`, `new_status`, `user_confirmed?` |
| **`kanban_check_drift`** | Comparar estado local vs MongoDB | `scope`: doing (default), all |

### 3.5 Feedback Triage

| Tool | Descripcion | Parametros |
|------|-------------|------------|
| `triage_list` | Listar reportes disponibles | `limit` (default: 10) |
| `triage_detail` | Leer reporte completo por fecha | `date` (YYYY-MM-DD) |
| `triage_generate` | Ejecutar script Python para generar reporte | `date`, `dry_run?` |
| `triage_extract_conversation` | Extraer thread de conversacion como markdown | `feedback_id` o `conversation_id` |

---

## 4. Operaciones comunes

### 4.1 Mover una tarea (3 capas)

```
kanban_atomic_move task_id="entity-alias-gfnorte" new_status="DONE" user_confirmed=true
```

**Que hace internamente:**
1. Mueve la carpeta local de `DOING/` a `DONE/`
2. Actualiza `message_feedback.status` en MongoDB via `PATCH /api/internal/feedback/ticket-status`
3. Devuelve un bloque `<!-- GITHUB_ACTION -->` con instrucciones para GitHub

**Respuesta tipica:**
```
✅ LOCAL: DOING → DONE
✅ MONGODB: 5 feedbacks → Done
⏳ GITHUB: Ejecutar github_action (Claude Code lo hará automáticamente)

<!-- GITHUB_ACTION -->
{"action":"update_issue_status","repo":"saptiva-ai/octavios-chat-bajaware_invex","search_title":"...","new_status":"DONE","add_label":"status:done","remove_labels":["status:backlog","status:doing","status:review"],"close_issue":true}
```

### 4.2 Ejecutar la GITHUB_ACTION

Cuando `kanban_atomic_move` devuelve `<!-- GITHUB_ACTION -->`, Claude Code debe:

1. Parsear el JSON
2. Buscar el issue: `gh issue list --repo <repo> --search "<search_title>" --json number`
3. Actualizar labels: `gh issue edit <number> --add-label <add_label> --remove-label <remove_labels>`
4. Si `close_issue=true`: `gh issue close <number>`

### 4.3 DoD Gate para bugs

Los bugs requieren `user_confirmed=true` para moverse a DONE.
Sin esta flag, el tool devuelve un checklist:

```
⛔ DoD Gate: "Chart Year Mismatch" es un BUG.
1. ✅ E2E tests passing
2. ✅ Desplegado en producción
3. ⬜ Usuario confirma que el bug no se reproduce
```

### 4.4 Detectar desincronizacion

```
kanban_check_drift scope="doing"
```

---

## 5. API interna del backend

El backend expone endpoints protegidos por `X-Internal-Key` header.

### Endpoints

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `PATCH` | `/api/internal/feedback/ticket-status` | Actualizar status de feedbacks por ticket_id |
| `POST` | `/api/internal/feedback/ticket-status/batch` | Consultar status de multiples tickets |
| `GET` | `/api/internal/feedback/stats` | Estadisticas de feedbacks (total, con ticket) |
| `POST` | `/api/internal/feedback/query` | Query feedbacks con filtros (fecha, rating, status) |
| `POST` | `/api/internal/feedback/conversations` | Thread completo de conversacion |
| `GET` | `/api/internal/feedback/stale-charts` | Detectar charts con datos desactualizados |

---

## 6. GitHub Issue Labels

Para la integracion con GitHub, crear estos labels en el repositorio:

| Label | Color | Descripcion |
|-------|-------|-------------|
| `status:backlog` | `#FBCA04` | Tarea en backlog |
| `status:doing` | `#0E8A16` | Tarea en progreso |
| `status:review` | `#1D76DB` | Tarea en review |
| `status:done` | `#6F42C1` | Tarea completada |
| `type:bug` | `#D73A4A` | Bug report |
| `type:task` | `#0075CA` | Task |
| `type:refactor` | `#E4E669` | Refactor |
| `type:security` | `#B60205` | Security issue |
| `triage:feedback` | `#F9D0C4` | Generado desde feedback triage |

---

## 7. Estructura de carpetas local

```
docs/kanban/
├── BACKLOG/
│   └── YYYY-MM-DD__TYPE__descripcion-corta/
│       └── card.md
├── DOING/
│   └── YYYY-MM-DD__TYPE__descripcion-corta/
│       ├── card.md
│       ├── research.md   (opcional)
│       ├── plan.md       (opcional)
│       └── validate.md   (opcional)
├── REVIEW/
│   └── ...
└── DONE/
    └── ...
```

---

## 8. Degradacion controlada

El sistema esta disenado para funcionar parcialmente si alguna capa falla:

| Escenario | LOCAL | MONGODB | GITHUB |
|-----------|-------|---------|--------|
| Sin `BACKEND_INTERNAL_KEY` | Funciona | Skip con warning | Manual |
| Sin SSH tunnel | Funciona | Skip (unreachable) | Manual |
| Sin `gh` auth | Funciona | Funciona | Manual |
| Todo configurado | Funciona | Funciona | Via `GITHUB_ACTION` |

---

## 9. Troubleshooting

### "Internal API not configured"

```bash
docker exec $CONTAINER env | grep INTERNAL
# Si no aparece: recrear (NO restart)
docker compose ... up -d backend
```

### "Backend no alcanzable"

```bash
ss -tlnp | grep 18000
# Si no aparece, reabrir tunnel
ssh -L 18000:localhost:8000 jf@$PROD_HOST -N -f
```

### MCP no arranca

```bash
cd tools/mcp-kanban-sync && npm run build
KANBAN_PATH=./docs/kanban node tools/mcp-kanban-sync/dist/index.js
```

---

## 10. Referencia de archivos

| Archivo | Descripcion |
|---------|-------------|
| `tools/mcp-kanban-sync/src/index.ts` | MCP server: definicion de 22 tools |
| `tools/mcp-kanban-sync/src/kanban-parser.ts` | Parser de carpetas y card.md |
| `tools/mcp-kanban-sync/src/backend-client.ts` | Cliente HTTP para API interna |
| `tools/mcp-kanban-sync/src/sync-queue.ts` | Cola de sync legacy |
| `tools/mcp-kanban-sync/src/types.ts` | Tipos y schemas Zod |
| `apps/backend/src/routers/internal.py` | Endpoints internos (FastAPI) |
| `.mcp.json` | Configuracion del MCP para Claude Code |
