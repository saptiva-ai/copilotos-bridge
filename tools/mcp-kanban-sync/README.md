# MCP Kanban Sync Server v4.0.0

Servidor MCP para sincronizar el kanban local (`docs/kanban/`) con MongoDB y GitHub Issues en una sola operación.

> **Manual completo**: [`docs/manuals/dev/kanban_sync.md`](../../docs/manuals/dev/kanban_sync.md)
> — prerequisitos, SSH tunnel, API interna, solución de problemas y referencia de las 22 herramientas.

## Arquitectura de sincronización

```
 LOCAL (filesystem)          MONGODB (feedback)         GITHUB (Issues)
 docs/kanban/                message_feedback.status    saptiva-ai/octavios-chat-bajaware_invex
 ├── BACKLOG/                ├── Backlog                ├── status:backlog
 ├── DOING/                  ├── In Progress            ├── status:doing
 ├── REVIEW/                 ├── Review                 ├── status:review
 └── DONE/                   └── Done                   └── status:done (closed)
       │                            │                          │
       └────── kanban_atomic_move ──┴───── GITHUB_ACTION ──────┘
```

- **Local + MongoDB**: el MCP server lo resuelve en una llamada
- **GitHub**: devuelve un bloque `<!-- GITHUB_ACTION -->` que Claude Code ejecuta via `gh` CLI

## Inicio rápido

```bash
# 1. Build
cd tools/mcp-kanban-sync && npm install && npm run build

# 2. SSH tunnel a PROD (puerto 18000 local → 8000 remoto)
ssh -L 18000:localhost:8000 jf@$PROD_HOST -N -f

# 3. Verificar que BACKEND_INTERNAL_KEY esta exportado
echo $BACKEND_INTERNAL_KEY

# 4. Verificar gh auth
gh auth status
```

## Configuración (`.mcp.json`)

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

## Herramientas (22)

### Lectura

| Herramienta | Descripción |
|-------------|-------------|
| `kanban_summary` | Resumen con conteo por status y prioridad |
| `kanban_list` | Listar tareas de un status |
| `kanban_task_detail` | Card completa + research/plan/validate |
| `kanban_search` | Buscar por keyword |
| `kanban_recent` | Tareas recientes por fecha |
| `kanban_by_priority` | Filtrar por P0-P3 |
| `kanban_workflow_status` | Estado de archivos auxiliares |

### Escritura

| Herramienta | Descripción |
|-------------|-------------|
| `kanban_create_task` | Crear tarea nueva |
| `kanban_update_content` | Reemplazar contenido de archivo |
| `kanban_append_content` | Agregar al final de un archivo |
| `kanban_move_task` | Mover entre estados (solo local) |
| `kanban_set_priority` | Cambiar prioridad |
| `kanban_delete_task` | Eliminar tarea (irreversible) |

### Sync atómico

| Herramienta | Descripción |
|-------------|-------------|
| **`kanban_atomic_move`** | Mover en 3 capas: local + MongoDB + GitHub Issue |
| **`kanban_check_drift`** | Comparar estado local vs MongoDB |

### Feedback Triage

| Herramienta | Descripción |
|-------------|-------------|
| `triage_list` | Listar reportes de triage con fecha y tamaño |
| `triage_detail` | Leer contenido completo de un reporte por fecha |
| `triage_generate` | Ejecutar script Python para generar reporte |
| `triage_extract_conversation` | Extraer thread de conversación como markdown |

### Cola legacy

| Herramienta | Descripción |
|-------------|-------------|
| `kanban_queue_status` | Ver acciones pendientes |
| `kanban_queue_task` | Agregar a cola |
| `kanban_generate_sync_instructions` | Instrucciones para sync manual via gh CLI |
| `kanban_clear_queue` | Limpiar cola |

## Uso

```bash
# Mover tarea (3 capas)
kanban_atomic_move task_id="entity-alias-gfnorte" new_status="DONE" user_confirmed=true

# Detectar desincronizacion
kanban_check_drift scope="doing"

# Ver resumen
kanban_summary

# Listar triages recientes
triage_list limit=5

# Leer triage de hoy
triage_detail date="2026-02-10"
```

## Archivos fuente del servidor

```
src/
├── index.ts            # Servidor MCP, 22 definiciones de herramientas + handlers
├── kanban-parser.ts    # Parser de carpetas y card.md
├── backend-client.ts   # Cliente HTTP para API interna de MongoDB
├── sync-queue.ts       # Cola de sync legacy
└── types.ts            # Tipos y schemas Zod
```

## Solución de problemas: Variables de entorno y MCP

### Problema: `kanban_check_drift` retorna HTTP 401

El sintoma tipico es:

```
⚠️ Backend no alcanzable: HTTP 401
```

Pero `curl` con la misma key funciona perfectamente via tunnel.

### Causa raíz

La interpolacion `${VAR}` en `.mcp.json` se resuelve desde el **proceso padre** (Claude Code), no desde una shell fresca. Si Claude Code se inicio antes de que la variable estuviera exportada en `~/.bashrc`, el proceso MCP recibe el string literal `${BACKEND_INTERNAL_KEY}` en lugar del valor real.

### Diagnóstico

```bash
# 1. Encontrar el PID del proceso MCP
ps aux | grep mcp-kanban-sync | grep -v grep

# 2. Verificar que valor recibio el proceso
cat /proc/<PID>/environ | tr '\0' '\n' | grep BACKEND_INTERNAL_KEY

# Si muestra BACKEND_INTERNAL_KEY=${BACKEND_INTERNAL_KEY} (literal), ese es el problema
```

### Solución

```bash
# Opcion A: Reiniciar Claude Code (recomendado)
# Salir con /exit, verificar que la variable esta exportada, volver a entrar
echo $BACKEND_INTERNAL_KEY   # debe mostrar el valor real
claude

# Opcion B: Matar el proceso MCP y reconectar
kill <PID>
# Luego en Claude Code: /mcp → Reconnect kanban-sync
```

### Buenas prácticas

1. **Exportar variables ANTES de iniciar Claude Code.** Las variables agregadas a `~/.bashrc` despues de que Claude Code ya esta corriendo no estaran disponibles para interpolacion en `.mcp.json`.

2. **`/mcp` Reconnect no reinicia el proceso.** Solo reconecta el pipe stdio. Para forzar un respawn del proceso Node.js, hay que matar el PID original y luego reconectar.

3. **Verificar siempre con `/proc/<PID>/environ`.** Es la unica forma confiable de saber que valor recibio el proceso MCP. `echo $VAR` en la shell de Claude Code (Bash tool) muestra el valor de una subshell que SI tiene el bashrc cargado, no el del proceso padre.

4. **No hardcodear secrets en `.mcp.json`.** Este archivo esta versionado en git. La interpolacion `${VAR}` es el patron correcto — solo hay que asegurar que el proceso padre tenga la variable disponible al momento de iniciar.

5. **SSH tunnel: verificar antes de operar.** El tunnel `ssh -L 18000:localhost:8000` debe estar activo para que `BACKEND_URL=http://localhost:18000` funcione:
   ```bash
   ps aux | grep "ssh -L 18000" | grep -v grep
   # Si no hay resultado, recrear:
   ssh -L 18000:localhost:8000 jf@$PROD_HOST -N -f
   ```

## Desarrollo

```bash
npm run dev     # Watch mode (tsc --watch)
npm run build   # Build once
npm start       # Run server
```
