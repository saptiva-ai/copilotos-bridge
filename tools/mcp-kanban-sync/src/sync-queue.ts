import * as fs from "fs/promises";
import * as path from "path";
import { LocalTask, SyncAction, SyncQueue } from "./types.js";

const SYNC_QUEUE_FILENAME = ".kanban-sync-queue.json";

export async function loadSyncQueue(kanbanPath: string): Promise<SyncQueue> {
  const queuePath = path.join(path.dirname(kanbanPath), SYNC_QUEUE_FILENAME);
  try {
    const content = await fs.readFile(queuePath, "utf-8");
    return JSON.parse(content);
  } catch {
    return {
      version: "2.0",
      projectPath: kanbanPath,
      githubRepo: process.env.GITHUB_REPO || "",
      pendingActions: [],
    };
  }
}

export async function saveSyncQueue(kanbanPath: string, queue: SyncQueue): Promise<void> {
  const queuePath = path.join(path.dirname(kanbanPath), SYNC_QUEUE_FILENAME);
  await fs.writeFile(queuePath, JSON.stringify(queue, null, 2));
}

export async function queueTaskForSync(
  kanbanPath: string,
  task: LocalTask,
  actionType: "create" | "update" | "move" | "delete"
): Promise<SyncAction> {
  const queue = await loadSyncQueue(kanbanPath);
  const newAction: SyncAction = {
    id: `sync-${Date.now()}`,
    type: actionType,
    taskId: task.id,
    taskTitle: task.title,
    status: task.status,
    priority: task.priority,
    content: actionType === "create" ? task.content : undefined,
    timestamp: new Date().toISOString(),
  };
  
  const idx = queue.pendingActions.findIndex(a => a.taskId === task.id);
  if (idx >= 0) queue.pendingActions[idx] = newAction;
  else queue.pendingActions.push(newAction);
  
  await saveSyncQueue(kanbanPath, queue);
  return newAction;
}

export async function clearSyncQueue(kanbanPath: string): Promise<void> {
  const queue = await loadSyncQueue(kanbanPath);
  queue.pendingActions = [];
  queue.lastSync = new Date().toISOString();
  await saveSyncQueue(kanbanPath, queue);
}

export async function generateSyncInstructions(kanbanPath: string): Promise<string> {
  const queue = await loadSyncQueue(kanbanPath);
  
  if (queue.pendingActions.length === 0) {
    return "✅ No hay acciones pendientes de sincronización.";
  }

  const repo = queue.githubRepo || process.env.GITHUB_REPO || "saptiva-ai/octavios-chat-bajaware_invex";
  const lines = [
    "# 📋 Instrucciones de Sync a GitHub",
    "",
    `**Acciones pendientes**: ${queue.pendingActions.length}`,
    `**Repo**: https://github.com/${repo}`,
    "",
    "---",
    "",
    "## Ejecutar con gh CLI:",
    "",
    "```bash",
    `# Repo: ${repo}`,
    "",
  ];

  for (const action of queue.pendingActions) {
    if (action.type === "create") {
      const labels = action.priority ? `--label "${action.priority}"` : "";
      lines.push(`# CREAR: ${action.taskTitle}`);
      lines.push(`gh issue create --repo ${repo} --title "${action.taskTitle}" ${labels} --body "Status: ${action.status}"`);
    } else if (action.type === "move") {
      lines.push(`# MOVER: ${action.taskTitle} → ${action.status}`);
      lines.push(`# (actualizar label de status en el issue correspondiente)`);
    } else if (action.type === "delete") {
      lines.push(`# ELIMINAR: ${action.taskTitle}`);
      lines.push(`# (cerrar issue en GitHub)`);
    } else {
      lines.push(`# ACTUALIZAR: ${action.taskTitle}`);
      lines.push(`# Status: ${action.status}`);
    }
    lines.push("");
  }

  lines.push("```");
  lines.push("");
  lines.push("Después ejecuta: `kanban_clear_queue`");

  return lines.join("\n");
}
