import * as fs from "fs/promises";
import * as path from "path";
import matter from "gray-matter";
import { LocalTask, TaskCard, TaskCardSchema, TaskStatus, TaskType, TaskPriority, CreateTaskInput } from "./types.js";

/**
 * Extract task info from folder name pattern: {YYYY-MM-DD}[-HHMM]__{TYPE}__{descripcion-corta}
 * Example: 2026-02-03__BUG__hallucination-data-validation
 */
function parseTaskFromFolderName(folderName: string, status: TaskStatus): TaskCard | null {
  // Pattern: YYYY-MM-DD[-HHMM]__TYPE__description
  const match = folderName.match(/^(\d{4}-\d{2}-\d{2})(?:-(\d{4}))?__([A-Z]+)__(.+)$/);
  if (!match) {
    // Try legacy pattern: TYPE-DATE__description (e.g., BUG-2026-01-30__desc)
    const legacyMatch = folderName.match(/^([A-Z]+)-(\d{4}-\d{2}-\d{2})__(.+)$/);
    if (legacyMatch) {
      const [, type, date, desc] = legacyMatch;
      const title = desc.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
      return {
        id: folderName,
        title,
        status,
        priority: type === "BUG" || type === "SEC" ? "high" : undefined,
        type: type as TaskType,
      };
    }
    return null;
  }

  const [, date, time, type, desc] = match;
  // Convert kebab-case description to Title Case
  const title = desc.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");

  return {
    id: folderName,
    title,
    status,
    priority: type === "BUG" || type === "SEC" ? "high" : undefined,
    type: type as TaskType,
  };
}

/**
 * Extract title from markdown content (first H1 heading)
 */
function extractTitleFromContent(content: string): string | null {
  const h1Match = content.match(/^#\s+(.+)$/m);
  return h1Match ? h1Match[1].trim() : null;
}

/**
 * Extract priority from markdown content
 */
function extractPriorityFromContent(content: string): string | null {
  const priorityMatch = content.match(/\*\*Prioridad:\*\*\s*(P[0-3])/i);
  return priorityMatch ? priorityMatch[1] : null;
}

async function parseCardFile(
  cardPath: string,
  folderName: string,
  status: TaskStatus
): Promise<{ frontmatter: TaskCard; content: string } | null> {
  try {
    const fileContent = await fs.readFile(cardPath, "utf-8");
    const { data, content } = matter(fileContent);

    // Try frontmatter first
    const parsed = TaskCardSchema.safeParse(data);
    if (parsed.success) {
      return { frontmatter: parsed.data, content: content.trim() };
    }

    // Fallback: extract from folder name
    const fromFolder = parseTaskFromFolderName(folderName, status);
    if (fromFolder) {
      // Try to get better title from H1 heading in content
      const h1Title = extractTitleFromContent(content || fileContent);
      if (h1Title) {
        fromFolder.title = h1Title.replace(/^(BUG|TASK|SEC|REFACTOR|FEEDBACK):\s*/i, "").trim();
      }
      // Try to get priority from content
      const priority = extractPriorityFromContent(content || fileContent);
      if (priority) {
        fromFolder.priority = priority;
      }
      return { frontmatter: fromFolder, content: (content || fileContent).trim() };
    }

    console.error(`Could not parse task: ${cardPath}`);
    return null;
  } catch {
    return null;
  }
}

async function checkAuxiliaryFiles(folderPath: string) {
  const [hasResearch, hasPlan, hasValidate] = await Promise.all([
    fs.access(path.join(folderPath, "research.md")).then(() => true).catch(() => false),
    fs.access(path.join(folderPath, "plan.md")).then(() => true).catch(() => false),
    fs.access(path.join(folderPath, "validate.md")).then(() => true).catch(() => false),
  ]);
  return { hasResearch, hasPlan, hasValidate };
}

async function getFileModifiedTime(filePath: string): Promise<Date | undefined> {
  try {
    const stats = await fs.stat(filePath);
    return stats.mtime;
  } catch {
    return undefined;
  }
}

async function scanStatusDirectory(kanbanPath: string, status: TaskStatus): Promise<LocalTask[]> {
  const statusPath = path.join(kanbanPath, status);
  const tasks: LocalTask[] = [];

  try {
    const entries = await fs.readdir(statusPath, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.name.startsWith(".") || !entry.isDirectory()) continue;
      if (entry.name === "TEMPLATE_TASK_FOLDER") continue;

      const folderPath = path.join(statusPath, entry.name);
      const cardPath = path.join(folderPath, "card.md");

      try { await fs.access(cardPath); } catch { continue; }

      const parsed = await parseCardFile(cardPath, entry.name, status);
      if (!parsed) continue;

      const aux = await checkAuxiliaryFiles(folderPath);
      const modifiedAt = await getFileModifiedTime(cardPath);

      tasks.push({
        id: parsed.frontmatter.id,
        title: parsed.frontmatter.title,
        status,
        type: parsed.frontmatter.type,
        phase: parsed.frontmatter.phase,
        priority: parsed.frontmatter.priority,
        folderPath,
        cardPath,
        frontmatter: parsed.frontmatter,
        content: parsed.content,
        modifiedAt,
        ...aux,
      });
    }
  } catch {}
  return tasks;
}

export async function loadLocalKanban(kanbanPath: string) {
  const [backlog, doing, review, done] = await Promise.all([
    scanStatusDirectory(kanbanPath, "BACKLOG"),
    scanStatusDirectory(kanbanPath, "DOING"),
    scanStatusDirectory(kanbanPath, "REVIEW"),
    scanStatusDirectory(kanbanPath, "DONE"),
  ]);
  return { backlog, doing, review, done, all: [...backlog, ...doing, ...review, ...done] };
}

export async function getTaskFileContent(folderPath: string, fileName: string): Promise<string | null> {
  try {
    return await fs.readFile(path.join(folderPath, fileName), "utf-8");
  } catch {
    return null;
  }
}

export async function moveTask(task: LocalTask, newStatus: TaskStatus, kanbanPath: string): Promise<boolean> {
  const newFolderPath = path.join(kanbanPath, newStatus, path.basename(task.folderPath));
  try {
    await fs.rename(task.folderPath, newFolderPath);
    const newCardPath = path.join(newFolderPath, "card.md");
    const cardContent = await fs.readFile(newCardPath, "utf-8");
    const { data, content } = matter(cardContent);
    data.status = newStatus;
    await fs.writeFile(newCardPath, matter.stringify(content, data));
    return true;
  } catch {
    return false;
  }
}

export async function createTask(kanbanPath: string, input: CreateTaskInput): Promise<LocalTask | null> {
  const today = new Date().toISOString().split("T")[0];
  const slug = input.title
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .substring(0, 50);

  const folderId = `${today}__${input.type}__${slug}`;
  const status = input.status || "BACKLOG";
  const folderPath = path.join(kanbanPath, status, folderId);
  const cardPath = path.join(folderPath, "card.md");

  try {
    await fs.mkdir(folderPath, { recursive: true });

    const priorityLine = input.priority ? `**Prioridad:** ${input.priority}` : "**Prioridad:** P2 - Medium";
    const cardContent = `# ${input.type}: ${input.title}

${priorityLine}
**Fecha:** ${today}
**Status:** ${status}

---

## Resumen

${input.description}

---

## Criterios de Aceptación

- [ ] TODO

---

## Referencias

- N/A
`;

    await fs.writeFile(cardPath, cardContent);

    return {
      id: folderId,
      title: input.title,
      status,
      type: input.type,
      priority: input.priority,
      folderPath,
      cardPath,
      frontmatter: { id: folderId, title: input.title, status, type: input.type, priority: input.priority },
      content: cardContent,
      hasResearch: false,
      hasPlan: false,
      hasValidate: false,
      modifiedAt: new Date(),
    };
  } catch (e) {
    console.error("Error creating task:", e);
    return null;
  }
}

export async function updateTaskContent(
  task: LocalTask,
  fileType: "card" | "research" | "plan" | "validate",
  content: string
): Promise<boolean> {
  const fileName = fileType === "card" ? "card.md" : `${fileType}.md`;
  const filePath = path.join(task.folderPath, fileName);

  try {
    await fs.writeFile(filePath, content);
    return true;
  } catch {
    return false;
  }
}

export async function appendToTaskFile(
  task: LocalTask,
  fileType: "card" | "research" | "plan" | "validate",
  content: string
): Promise<boolean> {
  const fileName = fileType === "card" ? "card.md" : `${fileType}.md`;
  const filePath = path.join(task.folderPath, fileName);

  try {
    const existing = await fs.readFile(filePath, "utf-8").catch(() => "");
    await fs.writeFile(filePath, existing + "\n\n" + content);
    return true;
  } catch {
    return false;
  }
}

export async function searchTasks(kanbanPath: string, query: string): Promise<LocalTask[]> {
  const kanban = await loadLocalKanban(kanbanPath);
  const queryLower = query.toLowerCase();

  return kanban.all.filter(task =>
    task.title.toLowerCase().includes(queryLower) ||
    task.content.toLowerCase().includes(queryLower) ||
    task.id.toLowerCase().includes(queryLower)
  );
}

export async function getRecentTasks(kanbanPath: string, limit: number = 10): Promise<LocalTask[]> {
  const kanban = await loadLocalKanban(kanbanPath);

  return kanban.all
    .filter(t => t.modifiedAt)
    .sort((a, b) => (b.modifiedAt?.getTime() || 0) - (a.modifiedAt?.getTime() || 0))
    .slice(0, limit);
}

export async function getTasksByPriority(kanbanPath: string, priority: string): Promise<LocalTask[]> {
  const kanban = await loadLocalKanban(kanbanPath);
  const priorityLower = priority.toLowerCase();

  return kanban.all.filter(task =>
    task.priority?.toLowerCase() === priorityLower ||
    task.priority?.toLowerCase().includes(priorityLower)
  );
}

export async function updateTaskPriority(task: LocalTask, newPriority: string): Promise<boolean> {
  try {
    let content = await fs.readFile(task.cardPath, "utf-8");

    // Try to update existing priority line
    const priorityRegex = /\*\*Prioridad:\*\*\s*[^\n]+/i;
    if (priorityRegex.test(content)) {
      content = content.replace(priorityRegex, `**Prioridad:** ${newPriority}`);
    } else {
      // Add priority after the first heading
      content = content.replace(/^(#[^\n]+\n)/m, `$1\n**Prioridad:** ${newPriority}\n`);
    }

    await fs.writeFile(task.cardPath, content);
    return true;
  } catch {
    return false;
  }
}

export async function deleteTask(task: LocalTask): Promise<boolean> {
  try {
    await fs.rm(task.folderPath, { recursive: true });
    return true;
  } catch {
    return false;
  }
}

export async function getKanbanSummary(kanbanPath: string): Promise<string> {
  const kanban = await loadLocalKanban(kanbanPath);
  const lines = [
    "# Local Kanban Summary",
    "",
    `| Status | Count |`,
    `|--------|-------|`,
    `| BACKLOG | ${kanban.backlog.length} |`,
    `| DOING | ${kanban.doing.length} |`,
    `| REVIEW | ${kanban.review.length} |`,
    `| DONE | ${kanban.done.length} |`,
    "",
  ];

  // Group DOING tasks by priority
  const doingByPriority = {
    P0: kanban.doing.filter(t => t.priority?.includes("P0")),
    P1: kanban.doing.filter(t => t.priority?.includes("P1")),
    P2: kanban.doing.filter(t => t.priority?.includes("P2") || !t.priority),
    P3: kanban.doing.filter(t => t.priority?.includes("P3")),
  };

  if (kanban.doing.length > 0) {
    lines.push("## DOING");
    lines.push("");

    for (const [priority, tasks] of Object.entries(doingByPriority)) {
      if (tasks.length === 0) continue;
      lines.push(`### ${priority}`);
      for (const task of tasks) {
        const files = [];
        if (task.hasResearch) files.push("📋");
        if (task.hasPlan) files.push("📝");
        if (task.hasValidate) files.push("✅");
        const filesStr = files.length > 0 ? ` ${files.join("")}` : "";
        lines.push(`- **${task.title}**${filesStr}`);
        lines.push(`  - ID: \`${task.id}\``);
      }
      lines.push("");
    }
  }

  if (kanban.review.length > 0) {
    lines.push("## REVIEW");
    lines.push("");
    for (const task of kanban.review) {
      const files = [];
      if (task.hasResearch) files.push("📋");
      if (task.hasPlan) files.push("📝");
      if (task.hasValidate) files.push("✅");
      const filesStr = files.length > 0 ? ` ${files.join("")}` : "";
      lines.push(`- **${task.title}**${filesStr}`);
      lines.push(`  - ID: \`${task.id}\``);
    }
    lines.push("");
  }

  if (kanban.backlog.length > 0) {
    lines.push("## BACKLOG");
    lines.push("");
    for (const task of kanban.backlog.slice(0, 10)) {
      lines.push(`- **${task.title}**${task.priority ? ` (${task.priority})` : ""}`);
    }
    if (kanban.backlog.length > 10) {
      lines.push(`- ... and ${kanban.backlog.length - 10} more`);
    }
  }
  return lines.join("\n");
}

export async function getWorkflowStatus(kanbanPath: string): Promise<string> {
  const kanban = await loadLocalKanban(kanbanPath);
  const lines = [
    "# Workflow Status",
    "",
    "## Active Tasks (DOING)",
    "",
  ];

  for (const task of kanban.doing) {
    const phase = task.phase || "unknown";
    const files = {
      research: task.hasResearch ? "✅" : "❌",
      plan: task.hasPlan ? "✅" : "❌",
      validate: task.hasValidate ? "✅" : "❌",
    };

    lines.push(`### ${task.title}`);
    lines.push(`- Phase: ${phase}`);
    lines.push(`- Files: research ${files.research} | plan ${files.plan} | validate ${files.validate}`);
    lines.push(`- Priority: ${task.priority || "N/A"}`);
    lines.push("");
  }

  return lines.join("\n");
}
