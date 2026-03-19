#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";

import {
  loadLocalKanban,
  getKanbanSummary,
  getTaskFileContent,
  moveTask,
  createTask,
  updateTaskContent,
  appendToTaskFile,
  searchTasks,
  getRecentTasks,
  getTasksByPriority,
  updateTaskPriority,
  deleteTask,
  getWorkflowStatus,
} from "./kanban-parser.js";
import { loadSyncQueue, generateSyncInstructions, queueTaskForSync, clearSyncQueue } from "./sync-queue.js";
import { updateFeedbackStatus, getTicketStatuses, getBackendHealth, STATUS_MAP, queryFeedback, getConversations } from "./backend-client.js";
import { TaskStatus, TaskType, TaskPriority } from "./types.js";

const KANBAN_PATH = process.env.KANBAN_PATH || "./docs/kanban";
const TRIAGE_PATH = process.env.TRIAGE_PATH || "./docs/reports/feedback_triage";

const GITHUB_REPO = process.env.GITHUB_REPO || "saptiva-ai/octavios-chat-bajaware_invex";

const server = new Server(
  { name: "mcp-kanban-sync", version: "4.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    // === READ OPERATIONS ===
    {
      name: "kanban_summary",
      description: "Resumen del kanban local con conteo por status y prioridad",
      inputSchema: { type: "object", properties: {} }
    },
    {
      name: "kanban_list",
      description: "Listar tareas por status (BACKLOG, DOING, REVIEW, DONE)",
      inputSchema: {
        type: "object",
        properties: {
          status: { type: "string", enum: ["BACKLOG", "DOING", "REVIEW", "DONE"], description: "Status de las tareas a listar" }
        },
        required: ["status"]
      }
    },
    {
      name: "kanban_task_detail",
      description: "Ver detalles completos de una tarea incluyendo research.md si existe",
      inputSchema: {
        type: "object",
        properties: {
          task_id: { type: "string", description: "ID de la tarea (puede ser parcial)" }
        },
        required: ["task_id"]
      }
    },
    {
      name: "kanban_search",
      description: "Buscar tareas por keyword en título, contenido o ID",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string", description: "Término de búsqueda" }
        },
        required: ["query"]
      }
    },
    {
      name: "kanban_recent",
      description: "Obtener las tareas más recientemente modificadas",
      inputSchema: {
        type: "object",
        properties: {
          limit: { type: "number", description: "Número máximo de tareas (default: 10)" }
        }
      }
    },
    {
      name: "kanban_by_priority",
      description: "Listar tareas por prioridad (P0, P1, P2, P3)",
      inputSchema: {
        type: "object",
        properties: {
          priority: { type: "string", enum: ["P0", "P1", "P2", "P3"], description: "Nivel de prioridad" }
        },
        required: ["priority"]
      }
    },
    {
      name: "kanban_workflow_status",
      description: "Ver estado del workflow de cada tarea activa (research, plan, validate)",
      inputSchema: { type: "object", properties: {} }
    },

    // === WRITE OPERATIONS ===
    {
      name: "kanban_create_task",
      description: "Crear una nueva tarea en el kanban",
      inputSchema: {
        type: "object",
        properties: {
          type: { type: "string", enum: ["BUG", "TASK", "REFACTOR", "SEC", "FEEDBACK"], description: "Tipo de tarea" },
          title: { type: "string", description: "Título descriptivo de la tarea" },
          description: { type: "string", description: "Descripción detallada del problema o tarea" },
          status: { type: "string", enum: ["BACKLOG", "DOING", "DONE"], description: "Status inicial (default: BACKLOG)" },
          priority: { type: "string", enum: ["P0", "P1", "P2", "P3"], description: "Prioridad (default: P2)" }
        },
        required: ["type", "title", "description"]
      }
    },
    {
      name: "kanban_update_content",
      description: "Actualizar el contenido de un archivo de tarea (card, research, plan, validate)",
      inputSchema: {
        type: "object",
        properties: {
          task_id: { type: "string", description: "ID de la tarea" },
          file_type: { type: "string", enum: ["card", "research", "plan", "validate"], description: "Tipo de archivo" },
          content: { type: "string", description: "Nuevo contenido completo" }
        },
        required: ["task_id", "file_type", "content"]
      }
    },
    {
      name: "kanban_append_content",
      description: "Agregar contenido al final de un archivo de tarea",
      inputSchema: {
        type: "object",
        properties: {
          task_id: { type: "string", description: "ID de la tarea" },
          file_type: { type: "string", enum: ["card", "research", "plan", "validate"], description: "Tipo de archivo" },
          content: { type: "string", description: "Contenido a agregar" }
        },
        required: ["task_id", "file_type", "content"]
      }
    },
    {
      name: "kanban_move_task",
      description: "Mover tarea entre estados (BACKLOG → DOING → REVIEW → DONE). Para bugs: requiere user_confirmed=true para mover a DONE (el usuario debe confirmar en producción que el bug no persiste).",
      inputSchema: {
        type: "object",
        properties: {
          task_id: { type: "string", description: "ID de la tarea" },
          new_status: { type: "string", enum: ["BACKLOG", "DOING", "REVIEW", "DONE"], description: "Nuevo status" },
          user_confirmed: { type: "boolean", description: "Para BUG→DONE: confirmar que el usuario validó el fix en producción (requerido para bugs)" }
        },
        required: ["task_id", "new_status"]
      }
    },
    {
      name: "kanban_set_priority",
      description: "Cambiar la prioridad de una tarea",
      inputSchema: {
        type: "object",
        properties: {
          task_id: { type: "string", description: "ID de la tarea" },
          priority: { type: "string", enum: ["P0 - Critical", "P1 - High", "P2 - Medium", "P3 - Low"], description: "Nueva prioridad" }
        },
        required: ["task_id", "priority"]
      }
    },
    {
      name: "kanban_delete_task",
      description: "Eliminar una tarea del kanban (irreversible)",
      inputSchema: {
        type: "object",
        properties: {
          task_id: { type: "string", description: "ID de la tarea a eliminar" }
        },
        required: ["task_id"]
      }
    },

    // === SYNC OPERATIONS ===
    {
      name: "kanban_queue_status",
      description: "Ver cola de sync pendiente para GitHub",
      inputSchema: { type: "object", properties: {} }
    },
    {
      name: "kanban_queue_task",
      description: "Agregar tarea a la cola de sync",
      inputSchema: {
        type: "object",
        properties: {
          task_id: { type: "string", description: "ID de la tarea" },
          action: { type: "string", enum: ["create", "update", "move", "delete"], description: "Tipo de acción" }
        },
        required: ["task_id"]
      }
    },
    {
      name: "kanban_generate_sync_instructions",
      description: "Generar instrucciones para sincronizar con GitHub Issues via gh CLI",
      inputSchema: { type: "object", properties: {} }
    },
    {
      name: "kanban_clear_queue",
      description: "Limpiar cola de sync despues de sincronizar con GitHub",
      inputSchema: { type: "object", properties: {} }
    },

    // === ATOMIC SYNC OPERATIONS ===
    {
      name: "kanban_atomic_move",
      description: "Mover ticket: local + MongoDB + GitHub Issue update. Retorna github_action para que Claude ejecute via gh CLI.",
      inputSchema: {
        type: "object",
        properties: {
          task_id: { type: "string", description: "ID de la tarea (parcial OK)" },
          new_status: { type: "string", enum: ["BACKLOG", "DOING", "REVIEW", "DONE"], description: "Nuevo status" },
          user_confirmed: { type: "boolean", description: "Para BUG→DONE: usuario confirmó fix" }
        },
        required: ["task_id", "new_status"]
      }
    },
    {
      name: "kanban_check_drift",
      description: "Verificar sincronización entre local y MongoDB",
      inputSchema: {
        type: "object",
        properties: {
          scope: { type: "string", enum: ["doing", "all"], description: "default: doing" }
        }
      }
    },

    // === FEEDBACK TRIAGE OPERATIONS ===
    {
      name: "triage_list",
      description: "Listar reportes de feedback triage disponibles con métricas extraídas del encabezado",
      inputSchema: {
        type: "object",
        properties: {
          limit: { type: "number", description: "Número máximo de reportes (default: 10, más recientes primero)" }
        }
      }
    },
    {
      name: "triage_detail",
      description: "Leer el contenido completo de un reporte de feedback triage por fecha",
      inputSchema: {
        type: "object",
        properties: {
          date: { type: "string", description: "Fecha del reporte en formato YYYY-MM-DD" }
        },
        required: ["date"]
      }
    },
    {
      name: "triage_generate",
      description: "Generar reporte de triage ejecutando el script Python. Requiere SSH tunnel activo y BACKEND_INTERNAL_KEY.",
      inputSchema: {
        type: "object",
        properties: {
          date: { type: "string", description: "Fecha del reporte en formato YYYY-MM-DD" },
          dry_run: { type: "boolean", description: "Solo mostrar output sin guardar archivo (default: false)" }
        },
        required: ["date"]
      }
    },
    {
      name: "triage_extract_conversation",
      description: "Extraer thread completo de una conversación desde el backend (mensajes + artefactos) formateado como markdown",
      inputSchema: {
        type: "object",
        properties: {
          feedback_id: { type: "string", description: "Feedback ID (e.g., FDBK-0109) para buscar la conversación" },
          conversation_id: { type: "string", description: "Conversation ID directo (alternativa a feedback_id)" }
        }
      }
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      // === READ OPERATIONS ===
      case "kanban_summary": {
        const summary = await getKanbanSummary(KANBAN_PATH);
        const queue = await loadSyncQueue(KANBAN_PATH);
        const pending = queue.pendingActions.length > 0 ? `\n\n⚠️ ${queue.pendingActions.length} cambios pendientes de sync` : "";
        return { content: [{ type: "text", text: summary + pending }] };
      }

      case "kanban_list": {
        const status = (args as any).status as TaskStatus;
        const kanban = await loadLocalKanban(KANBAN_PATH);
        const tasks = status === "BACKLOG" ? kanban.backlog : status === "DOING" ? kanban.doing : status === "REVIEW" ? kanban.review : kanban.done;
        const lines = [`# ${status} (${tasks.length})`, ""];
        for (const t of tasks) {
          const priority = t.priority ? ` [${t.priority}]` : "";
          const files = [];
          if (t.hasResearch) files.push("📋");
          if (t.hasPlan) files.push("📝");
          if (t.hasValidate) files.push("✅");
          const filesStr = files.length > 0 ? ` ${files.join("")}` : "";
          lines.push(`- **${t.title}**${priority}${filesStr}`);
          lines.push(`  \`${t.id}\``);
        }
        return { content: [{ type: "text", text: lines.join("\n") }] };
      }

      case "kanban_task_detail": {
        const taskId = (args as any).task_id;
        const kanban = await loadLocalKanban(KANBAN_PATH);
        const task = kanban.all.find(t => t.id === taskId || t.id.includes(taskId));
        if (!task) return { content: [{ type: "text", text: `❌ Tarea no encontrada: ${taskId}` }], isError: true };

        let text = `# ${task.title}\n\n**ID**: \`${task.id}\`\n**Status**: ${task.status}\n**Priority**: ${task.priority || "N/A"}\n**Type**: ${task.type || "N/A"}\n**Path**: ${task.folderPath}\n\n---\n## card.md\n\n${task.content}`;
        if (task.hasResearch) {
          const r = await getTaskFileContent(task.folderPath, "research.md");
          if (r) text += `\n\n---\n## research.md\n\n${r}`;
        }
        if (task.hasPlan) {
          const p = await getTaskFileContent(task.folderPath, "plan.md");
          if (p) text += `\n\n---\n## plan.md\n\n${p}`;
        }
        if (task.hasValidate) {
          const v = await getTaskFileContent(task.folderPath, "validate.md");
          if (v) text += `\n\n---\n## validate.md\n\n${v}`;
        }
        return { content: [{ type: "text", text }] };
      }

      case "kanban_search": {
        const query = (args as any).query;
        const results = await searchTasks(KANBAN_PATH, query);
        if (results.length === 0) {
          return { content: [{ type: "text", text: `No se encontraron tareas para: "${query}"` }] };
        }
        const lines = [`# Resultados para "${query}" (${results.length})`, ""];
        for (const t of results) {
          lines.push(`- **${t.title}** [${t.status}]`);
          lines.push(`  \`${t.id}\``);
        }
        return { content: [{ type: "text", text: lines.join("\n") }] };
      }

      case "kanban_recent": {
        const limit = (args as any).limit || 10;
        const tasks = await getRecentTasks(KANBAN_PATH, limit);
        const lines = [`# Tareas Recientes (${tasks.length})`, ""];
        for (const t of tasks) {
          const date = t.modifiedAt?.toISOString().split("T")[0] || "N/A";
          lines.push(`- **${t.title}** [${t.status}] - ${date}`);
          lines.push(`  \`${t.id}\``);
        }
        return { content: [{ type: "text", text: lines.join("\n") }] };
      }

      case "kanban_by_priority": {
        const priority = (args as any).priority;
        const tasks = await getTasksByPriority(KANBAN_PATH, priority);
        const lines = [`# Tareas ${priority} (${tasks.length})`, ""];
        for (const t of tasks) {
          lines.push(`- **${t.title}** [${t.status}]`);
          lines.push(`  \`${t.id}\``);
        }
        return { content: [{ type: "text", text: lines.join("\n") }] };
      }

      case "kanban_workflow_status": {
        const status = await getWorkflowStatus(KANBAN_PATH);
        return { content: [{ type: "text", text: status }] };
      }

      // === WRITE OPERATIONS ===
      case "kanban_create_task": {
        const { type, title, description, status, priority } = args as any;
        const task = await createTask(KANBAN_PATH, {
          type: type as TaskType,
          title,
          description,
          status: status as TaskStatus,
          priority: priority as TaskPriority,
        });
        if (!task) {
          return { content: [{ type: "text", text: "❌ Error al crear la tarea" }], isError: true };
        }
        await queueTaskForSync(KANBAN_PATH, task, "create");
        return {
          content: [{
            type: "text",
            text: `✅ Tarea creada:\n\n**${task.title}**\n- ID: \`${task.id}\`\n- Status: ${task.status}\n- Path: ${task.folderPath}`
          }]
        };
      }

      case "kanban_update_content": {
        const { task_id, file_type, content } = args as any;
        const kanban = await loadLocalKanban(KANBAN_PATH);
        const task = kanban.all.find(t => t.id === task_id || t.id.includes(task_id));
        if (!task) return { content: [{ type: "text", text: `❌ Tarea no encontrada: ${task_id}` }], isError: true };

        if (await updateTaskContent(task, file_type, content)) {
          await queueTaskForSync(KANBAN_PATH, task, "update");
          return { content: [{ type: "text", text: `✅ Actualizado ${file_type}.md de "${task.title}"` }] };
        }
        return { content: [{ type: "text", text: "❌ Error al actualizar" }], isError: true };
      }

      case "kanban_append_content": {
        const { task_id, file_type, content } = args as any;
        const kanban = await loadLocalKanban(KANBAN_PATH);
        const task = kanban.all.find(t => t.id === task_id || t.id.includes(task_id));
        if (!task) return { content: [{ type: "text", text: `❌ Tarea no encontrada: ${task_id}` }], isError: true };

        if (await appendToTaskFile(task, file_type, content)) {
          await queueTaskForSync(KANBAN_PATH, task, "update");
          return { content: [{ type: "text", text: `✅ Contenido agregado a ${file_type}.md de "${task.title}"` }] };
        }
        return { content: [{ type: "text", text: "❌ Error al agregar contenido" }], isError: true };
      }

      case "kanban_move_task": {
        const { task_id, new_status, user_confirmed } = args as any;
        const kanban = await loadLocalKanban(KANBAN_PATH);
        const task = kanban.all.find(t => t.id === task_id || t.id.includes(task_id));
        if (!task) return { content: [{ type: "text", text: `❌ Tarea no encontrada: ${task_id}` }], isError: true };

        const old = task.status;
        if (old === new_status) {
          return { content: [{ type: "text", text: `ℹ️ La tarea ya está en ${new_status}` }] };
        }

        // DoD gate: BUG tasks require user confirmation to move to DONE
        const isBug = task.type === "BUG" || task.id.includes("__BUG__");
        if (isBug && new_status === "DONE" && !user_confirmed) {
          return {
            content: [{
              type: "text",
              text: [
                `⛔ **DoD Gate**: "${task.title}" es un BUG.`,
                "",
                "Los bugs solo se mueven a DONE cuando el usuario confirma en producción que el problema ya no persiste.",
                "",
                "**Checklist antes de cerrar:**",
                "1. ✅ E2E tests passing",
                "2. ✅ Desplegado en producción",
                "3. ⬜ **Usuario confirma que el bug no se reproduce**",
                "",
                "Para forzar el cierre, usa `user_confirmed: true`.",
              ].join("\n"),
            }],
          };
        }

        if (await moveTask(task, new_status, KANBAN_PATH)) {
          task.status = new_status;
          await queueTaskForSync(KANBAN_PATH, task, "move");
          const confirmed = isBug && new_status === "DONE" ? " (usuario confirmó fix)" : "";
          return { content: [{ type: "text", text: `✅ **${task.title}**\n\n${old} → ${new_status}${confirmed}` }] };
        }
        return { content: [{ type: "text", text: "❌ Error al mover la tarea" }], isError: true };
      }

      case "kanban_set_priority": {
        const { task_id, priority } = args as any;
        const kanban = await loadLocalKanban(KANBAN_PATH);
        const task = kanban.all.find(t => t.id === task_id || t.id.includes(task_id));
        if (!task) return { content: [{ type: "text", text: `❌ Tarea no encontrada: ${task_id}` }], isError: true };

        if (await updateTaskPriority(task, priority)) {
          task.priority = priority;
          await queueTaskForSync(KANBAN_PATH, task, "update");
          return { content: [{ type: "text", text: `✅ Prioridad de "${task.title}" actualizada a ${priority}` }] };
        }
        return { content: [{ type: "text", text: "❌ Error al actualizar prioridad" }], isError: true };
      }

      case "kanban_delete_task": {
        const { task_id } = args as any;
        const kanban = await loadLocalKanban(KANBAN_PATH);
        const task = kanban.all.find(t => t.id === task_id || t.id.includes(task_id));
        if (!task) return { content: [{ type: "text", text: `❌ Tarea no encontrada: ${task_id}` }], isError: true };

        if (await deleteTask(task)) {
          await queueTaskForSync(KANBAN_PATH, { ...task, status: "DONE" } as any, "delete");
          return { content: [{ type: "text", text: `🗑️ Tarea eliminada: "${task.title}"` }] };
        }
        return { content: [{ type: "text", text: "❌ Error al eliminar la tarea" }], isError: true };
      }

      // === SYNC OPERATIONS ===
      case "kanban_queue_status": {
        const queue = await loadSyncQueue(KANBAN_PATH);
        if (queue.pendingActions.length === 0) {
          const lastSync = queue.lastSync ? `\nÚltima sync: ${queue.lastSync}` : "";
          return { content: [{ type: "text", text: `✅ Cola vacía - todo sincronizado${lastSync}` }] };
        }
        const lines = [
          "# Cola de Sync Pendiente",
          "",
          `**Acciones**: ${queue.pendingActions.length}`,
          "",
          ...queue.pendingActions.map(a => `- **${a.type.toUpperCase()}**: ${a.taskTitle} → ${a.status}`)
        ];
        return { content: [{ type: "text", text: lines.join("\n") }] };
      }

      case "kanban_queue_task": {
        const { task_id, action = "update" } = args as any;
        const kanban = await loadLocalKanban(KANBAN_PATH);
        const task = kanban.all.find(t => t.id === task_id || t.id.includes(task_id));
        if (!task) return { content: [{ type: "text", text: `❌ Tarea no encontrada: ${task_id}` }], isError: true };
        await queueTaskForSync(KANBAN_PATH, task, action);
        return { content: [{ type: "text", text: `✅ Agregado a cola: ${task.title} (${action})` }] };
      }

      case "kanban_generate_sync_instructions": {
        return { content: [{ type: "text", text: await generateSyncInstructions(KANBAN_PATH) }] };
      }

      case "kanban_clear_queue": {
        await clearSyncQueue(KANBAN_PATH);
        return { content: [{ type: "text", text: "✅ Cola limpiada - sync completa" }] };
      }

      // === ATOMIC SYNC OPERATIONS ===
      case "kanban_atomic_move": {
        const { task_id, new_status, user_confirmed } = args as any;
        const kanban = await loadLocalKanban(KANBAN_PATH);
        const task = kanban.all.find(t => t.id === task_id || t.id.includes(task_id));
        if (!task) return { content: [{ type: "text", text: `❌ Tarea no encontrada: ${task_id}` }], isError: true };

        const old = task.status;
        if (old === new_status) {
          return { content: [{ type: "text", text: `ℹ️ La tarea ya está en ${new_status}` }] };
        }

        // DoD gate: BUG tasks require user confirmation to move to DONE
        const isBug = task.type === "BUG" || task.id.includes("__BUG__");
        if (isBug && new_status === "DONE" && !user_confirmed) {
          return {
            content: [{
              type: "text",
              text: [
                `⛔ **DoD Gate**: "${task.title}" es un BUG.`,
                "",
                "Los bugs solo se mueven a DONE cuando el usuario confirma que el fix está verificado.",
                "",
                "Para forzar el cierre, usa `user_confirmed: true`.",
              ].join("\n"),
            }],
          };
        }

        const lines: string[] = [];

        // Step 1: LOCAL move
        if (await moveTask(task, new_status, KANBAN_PATH)) {
          lines.push(`✅ LOCAL: ${old} → ${new_status}`);
        } else {
          return { content: [{ type: "text", text: "❌ Error al mover la tarea localmente" }], isError: true };
        }

        // Step 2: MONGODB update
        const health = await getBackendHealth();
        if (health.status === "no_config") {
          lines.push(`⏭️ MONGODB: sin BACKEND_INTERNAL_KEY — solo sync local`);
        } else if (health.status === "unreachable") {
          lines.push(`⚠️ MONGODB: backend no alcanzable (${health.error})`);
        } else if (health.total === 0) {
          lines.push(`ℹ️ MONGODB: 0 feedbacks en BD — sync solo disponible en producción`);
        } else {
          const mongoResult = await updateFeedbackStatus(task.id, new_status as "BACKLOG" | "DOING" | "REVIEW" | "DONE");
          if (mongoResult && mongoResult.modified > 0) {
            lines.push(`✅ MONGODB: ${mongoResult.modified} feedbacks → ${STATUS_MAP[new_status]}`);
          } else {
            lines.push(`ℹ️ MONGODB: 0 feedbacks vinculados a este ticket (${health.total} totales en BD)`);
          }
        }

        // Step 3: Build github_action for Claude to execute via gh CLI
        const labelMap: Record<string, string> = {
          BACKLOG: "status:backlog",
          DOING: "status:doing",
          REVIEW: "status:review",
          DONE: "status:done",
        };
        const githubAction = {
          action: "update_issue_status",
          repo: GITHUB_REPO,
          search_title: task.id,
          new_status: new_status,
          add_label: labelMap[new_status] || "",
          remove_labels: Object.values(labelMap).filter(l => l !== labelMap[new_status]),
          close_issue: new_status === "DONE",
        };
        lines.push(`⏳ GITHUB: Ejecutar github_action (Claude Code lo hará automáticamente)`);
        lines.push("");
        lines.push("<!-- GITHUB_ACTION -->");
        lines.push(JSON.stringify(githubAction));

        task.status = new_status as TaskStatus;
        return { content: [{ type: "text", text: lines.join("\n") }] };
      }

      case "kanban_check_drift": {
        const scope = ((args as any).scope || "doing") as string;
        const kanban = await loadLocalKanban(KANBAN_PATH);

        let tasks = scope === "all"
          ? kanban.all
          : kanban.doing;

        if (tasks.length === 0) {
          return { content: [{ type: "text", text: `# Drift Check (${scope.toUpperCase()})\n\nNo hay tareas en ${scope}.` }] };
        }

        // Pre-flight: check backend connectivity and data
        const health = await getBackendHealth();
        if (health.status === "no_config") {
          const lines = [
            `# Drift Check (${scope.toUpperCase()})`,
            "",
            `**${tasks.length} tareas locales** en ${scope}`,
            "",
            `⏭️ BACKEND_INTERNAL_KEY no configurado — no se puede comparar con MongoDB.`,
            `Solo se verificó el estado local.`,
          ];
          return { content: [{ type: "text", text: lines.join("\n") }] };
        }
        if (health.status === "unreachable") {
          const lines = [
            `# Drift Check (${scope.toUpperCase()})`,
            "",
            `**${tasks.length} tareas locales** en ${scope}`,
            "",
            `⚠️ Backend no alcanzable: ${health.error}`,
            `Verificar que BACKEND_URL (${process.env.BACKEND_URL || "http://localhost:8000"}) esté corriendo.`,
          ];
          return { content: [{ type: "text", text: lines.join("\n") }] };
        }
        if (health.total === 0) {
          const lines = [
            `# Drift Check (${scope.toUpperCase()})`,
            "",
            `**${tasks.length} tareas locales** en ${scope}`,
            "",
            `ℹ️ MongoDB tiene 0 feedbacks — la data de feedback solo existe en producción.`,
            `Para drift check real, apuntar BACKEND_URL al backend de prod.`,
          ];
          return { content: [{ type: "text", text: lines.join("\n") }] };
        }

        // MongoDB has data — do the full comparison
        const ticketIds = tasks.map(t => t.id);
        const mongoStatuses = await getTicketStatuses(ticketIds);

        const mongoMap = new Map<string, string>();
        for (const info of mongoStatuses) {
          mongoMap.set(info.ticket_id, info.status);
        }

        const rows: string[] = [];
        let driftCount = 0;
        let linkedCount = 0;

        for (const task of tasks) {
          const mongoStatus = mongoMap.get(task.id);
          const expectedMongo = STATUS_MAP[task.status];

          if (!mongoStatus) {
            rows.push(`| ${task.id} | ${task.status} | — | ➖ |`);
          } else {
            linkedCount++;
            if (mongoStatus === expectedMongo) {
              rows.push(`| ${task.id} | ${task.status} | ${mongoStatus} | ✅ |`);
            } else {
              rows.push(`| ${task.id} | ${task.status} | ${mongoStatus} | ❌ |`);
              driftCount++;
            }
          }
        }

        const lines = [
          `# Drift Check (${scope.toUpperCase()})`,
          "",
          `**Backend**: ${health.total} feedbacks (${health.withTicket} con ticket vinculado)`,
          "",
          "| Ticket | Local | MongoDB | Sync? |",
          "|--------|-------|---------|-------|",
          ...rows,
        ];

        if (driftCount > 0) {
          lines.push("", `⚠️ ${driftCount} discrepancia(s) de ${linkedCount} tickets vinculados`);
        } else if (linkedCount > 0) {
          lines.push("", `✅ ${linkedCount} tickets vinculados — todo sincronizado`);
        } else {
          lines.push("", `ℹ️ Ninguna tarea de ${scope} tiene feedbacks vinculados en MongoDB`);
        }

        return { content: [{ type: "text", text: lines.join("\n") }] };
      }

      // === FEEDBACK TRIAGE OPERATIONS ===
      case "triage_list": {
        const limit = (args as any).limit || 10;
        const fs = await import("node:fs/promises");
        const path = await import("node:path");

        let files: string[];
        try {
          const entries = await fs.readdir(TRIAGE_PATH);
          files = entries
            .filter((f: string) => f.endsWith(".md"))
            .sort()
            .reverse()
            .slice(0, limit);
        } catch {
          return { content: [{ type: "text", text: `❌ No se pudo leer ${TRIAGE_PATH}` }], isError: true };
        }

        if (files.length === 0) {
          return { content: [{ type: "text", text: "ℹ️ No hay reportes de triage disponibles" }] };
        }

        const lines = [`# Feedback Triage Reports (${files.length})`, "", "| Fecha | Archivo | Tamaño |", "|-------|---------|--------|"];
        for (const f of files) {
          const stat = await fs.stat(path.join(TRIAGE_PATH, f));
          const sizeKb = (stat.size / 1024).toFixed(1);
          const date = f.replace(".md", "");
          lines.push(`| ${date} | \`${f}\` | ${sizeKb} KB |`);
        }
        lines.push("", `📁 Path: \`${TRIAGE_PATH}\``);
        return { content: [{ type: "text", text: lines.join("\n") }] };
      }

      case "triage_detail": {
        const date = (args as any).date;
        const fs = await import("node:fs/promises");
        const path = await import("node:path");

        // Try exact match first, then with common suffixes
        const candidates = [`${date}.md`, `${date}-tracker.md`];
        let content: string | null = null;
        let matchedFile = "";

        for (const candidate of candidates) {
          try {
            content = await fs.readFile(path.join(TRIAGE_PATH, candidate), "utf-8");
            matchedFile = candidate;
            break;
          } catch {
            continue;
          }
        }

        if (!content) {
          // List available files as hint
          try {
            const entries = await fs.readdir(TRIAGE_PATH);
            const available = entries.filter((f: string) => f.startsWith(date));
            if (available.length > 0) {
              return { content: [{ type: "text", text: `❌ No encontrado para ${date}. Archivos similares: ${available.join(", ")}` }], isError: true };
            }
          } catch { /* ignore */ }
          return { content: [{ type: "text", text: `❌ No existe reporte para ${date} en ${TRIAGE_PATH}` }], isError: true };
        }

        return { content: [{ type: "text", text: `📄 \`${matchedFile}\`\n\n${content}` }] };
      }

      case "triage_generate": {
        const date = (args as any).date;
        const dryRun = (args as any).dry_run || false;
        const { execSync } = await import("node:child_process");
        const path = await import("node:path");

        const scriptPath = "scripts/triage/generate_report.py";
        const outputPath = path.join(TRIAGE_PATH, `${date}.md`);
        const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
        const apiKey = process.env.BACKEND_INTERNAL_KEY || "";

        if (!apiKey) {
          return { content: [{ type: "text", text: "❌ BACKEND_INTERNAL_KEY no configurado" }], isError: true };
        }

        const cmdArgs = [
          "python", scriptPath,
          "--date", date,
          "--backend-url", backendUrl,
          "--api-key", apiKey,
        ];

        if (dryRun) {
          cmdArgs.push("--dry-run");
        } else {
          cmdArgs.push("--output", outputPath);
        }

        try {
          const output = execSync(cmdArgs.join(" "), {
            timeout: 120_000,
            encoding: "utf-8",
            cwd: process.cwd(),
          });

          if (dryRun) {
            return { content: [{ type: "text", text: `📋 DRY RUN\n\n${output}` }] };
          }

          // Read the generated file
          const fs = await import("node:fs/promises");
          let reportContent = "";
          try {
            reportContent = await fs.readFile(outputPath, "utf-8");
          } catch {
            reportContent = "(archivo no encontrado después de generación)";
          }

          const preview = reportContent.length > 2000
            ? reportContent.substring(0, 2000) + "\n\n... (truncado)"
            : reportContent;

          return {
            content: [{
              type: "text",
              text: [
                `✅ Reporte generado: \`${outputPath}\``,
                "",
                output,
                "",
                "---",
                "",
                preview,
              ].join("\n"),
            }],
          };
        } catch (e: any) {
          return {
            content: [{
              type: "text",
              text: `❌ Error ejecutando script:\n\n${e.stderr || e.message || String(e)}`,
            }],
            isError: true,
          };
        }
      }

      case "triage_extract_conversation": {
        const feedbackId = (args as any).feedback_id;
        let conversationId = (args as any).conversation_id;

        // If feedback_id provided, resolve to conversation_id
        if (feedbackId && !conversationId) {
          const feedbacks = await queryFeedback({ feedback_ids: [feedbackId], limit: 1 });
          if (feedbacks.length === 0) {
            return { content: [{ type: "text", text: `❌ Feedback no encontrado: ${feedbackId}` }], isError: true };
          }
          conversationId = feedbacks[0].conversation_id;
        }

        if (!conversationId) {
          return { content: [{ type: "text", text: "❌ Se requiere feedback_id o conversation_id" }], isError: true };
        }

        // Fetch conversation thread
        const convData = await getConversations([conversationId]);
        const conv = convData[conversationId];

        if (!conv) {
          return { content: [{ type: "text", text: `❌ Conversación no encontrada: ${conversationId}` }], isError: true };
        }

        // Format as markdown
        const lines: string[] = [
          `# Conversación \`${conversationId}\``,
          "",
          `**Mensajes**: ${conv.messages.length}`,
          `**Artefactos**: ${conv.artifacts?.length || 0}`,
          "",
          "---",
          "",
        ];

        for (const msg of conv.messages) {
          lines.push(`### ${msg.role.toUpperCase()} (${msg.created_at})`);
          lines.push("");
          lines.push(msg.content);
          lines.push("");

          if (msg.metadata) {
            const meta = msg.metadata;
            const interesting = ["intent", "handler_name", "confidence", "bank_chart_data"];
            const metaLines = interesting
              .filter(k => meta[k] !== undefined && meta[k] !== null)
              .map(k => {
                const val = typeof meta[k] === "object" ? JSON.stringify(meta[k]).substring(0, 200) : String(meta[k]);
                return `- **${k}**: ${val}`;
              });
            if (metaLines.length > 0) {
              lines.push("**Metadata**:");
              lines.push(...metaLines);
              lines.push("");
            }
          }
        }

        if (conv.artifacts && conv.artifacts.length > 0) {
          lines.push("---");
          lines.push("");
          lines.push("## Artefactos");
          lines.push("");

          for (const art of conv.artifacts) {
            lines.push(`### ${art.title} (\`${art.type}\`, ${art.created_at})`);
            if (art.expires_at) {
              lines.push(`**Expires**: ${art.expires_at}`);
            }
            if (art.type === "bank_chart" && art.content && typeof art.content === "object") {
              const c = art.content;
              lines.push(`- **chart_status**: ${c.chart_status || "?"}`);
              lines.push(`- **metric_name**: ${c.metric_name || "?"}`);
              lines.push(`- **bank_names**: ${JSON.stringify(c.bank_names || [])}`);

              const plotly = c.plotly_config;
              if (plotly?.data?.[0]?.x) {
                const x = plotly.data[0].x;
                lines.push(`- **x_range**: [${x[0]}, ${x[x.length - 1]}] (${x.length} points)`);
              }
              if (plotly?.data) {
                lines.push(`- **traces**: ${plotly.data.length}`);
              }
            }
            lines.push("");
          }
        }

        // Also fetch feedback for this conversation
        const feedbacks = await queryFeedback({ limit: 20 });
        const convFeedbacks = feedbacks.filter(f => f.conversation_id === conversationId);

        if (convFeedbacks.length > 0) {
          lines.push("---");
          lines.push("");
          lines.push("## Feedback en esta conversación");
          lines.push("");
          for (const fb of convFeedbacks) {
            lines.push(`- **${fb.feedback_id || "N/A"}** (${fb.rating}) — ${fb.reason || "sin razón"}`);
            lines.push(`  msg_id: \`${fb.message_id}\`, status: ${fb.status}`);
          }
        }

        return { content: [{ type: "text", text: lines.join("\n") }] };
      }

      default:
        return { content: [{ type: "text", text: `❌ Herramienta desconocida: ${name}` }], isError: true };
    }
  } catch (e) {
    return { content: [{ type: "text", text: `❌ Error: ${e}` }], isError: true };
  }
});

const transport = new StdioServerTransport();
server.connect(transport);
console.error("MCP Kanban Sync v4.0.0 running (GitHub sync)");
