import { z } from "zod";

export const TaskStatusSchema = z.enum(["BACKLOG", "DOING", "REVIEW", "DONE"]);
export type TaskStatus = z.infer<typeof TaskStatusSchema>;

export const TaskTypeSchema = z.enum(["BUG", "TASK", "REFACTOR", "SEC", "FEEDBACK"]);
export type TaskType = z.infer<typeof TaskTypeSchema>;

export const TaskPrioritySchema = z.enum(["P0", "P1", "P2", "P3"]);
export type TaskPriority = z.infer<typeof TaskPrioritySchema>;

export const TaskPhaseSchema = z.enum(["research", "plan", "implement", "validate", "done"]);
export type TaskPhase = z.infer<typeof TaskPhaseSchema>;

export const TaskCardSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: TaskStatusSchema,
  phase: z.string().optional(),
  priority: z.string().optional(),
  type: TaskTypeSchema.optional(),
});
export type TaskCard = z.infer<typeof TaskCardSchema>;

export interface LocalTask {
  id: string;
  title: string;
  status: TaskStatus;
  type?: TaskType;
  phase?: string;
  priority?: string;
  folderPath: string;
  cardPath: string;
  frontmatter: TaskCard;
  content: string;
  hasResearch: boolean;
  hasPlan: boolean;
  hasValidate: boolean;
  modifiedAt?: Date;
}

export interface SyncAction {
  id: string;
  type: "create" | "update" | "move" | "delete";
  taskId: string;
  taskTitle: string;
  status: TaskStatus;
  priority?: string;
  content?: string;
  timestamp: string;
}

export interface SyncQueue {
  version: "2.0";
  projectPath: string;
  githubRepo: string;
  lastSync?: string;
  pendingActions: SyncAction[];
}

export interface CreateTaskInput {
  type: TaskType;
  title: string;
  description: string;
  status?: TaskStatus;
  priority?: TaskPriority;
}
