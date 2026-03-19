/**
 * Backend API client for kanban ↔ MongoDB feedback sync.
 *
 * Calls the internal API endpoints on the FastAPI backend to
 * update/query feedback statuses linked to kanban ticket_ids.
 */

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const INTERNAL_KEY = process.env.BACKEND_INTERNAL_KEY;

/** Maps local kanban folder names to MongoDB FeedbackStatus values. */
const STATUS_MAP: Record<string, string> = {
  BACKLOG: "Backlog",
  DOING: "In Progress",
  REVIEW: "Review",
  DONE: "Done",
};

export interface TicketStatusResult {
  ticket_id: string;
  status: string;
  modified_count: number;
}

export interface TicketStatusInfo {
  ticket_id: string;
  status: string;
  count: number;
}

/**
 * Update all feedbacks linked to a ticket_id to the corresponding MongoDB status.
 * Returns null if INTERNAL_KEY is not configured (graceful degradation).
 */
export async function updateFeedbackStatus(
  ticketId: string,
  kanbanStatus: "BACKLOG" | "DOING" | "REVIEW" | "DONE"
): Promise<{ modified: number } | null> {
  if (!INTERNAL_KEY) {
    console.error("[backend-client] BACKEND_INTERNAL_KEY not set — skipping MongoDB update");
    return null;
  }

  const mongoStatus = STATUS_MAP[kanbanStatus];
  const res = await fetch(`${BACKEND_URL}/api/internal/feedback/ticket-status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Key": INTERNAL_KEY,
    },
    body: JSON.stringify({ ticket_id: ticketId, status: mongoStatus }),
  });

  if (!res.ok) {
    const text = await res.text();
    console.error(`[backend-client] PATCH failed (${res.status}): ${text}`);
    return null;
  }

  const data = (await res.json()) as TicketStatusResult;
  return { modified: data.modified_count };
}

/**
 * Query feedback statuses for multiple ticket_ids.
 * Returns empty array if INTERNAL_KEY is not configured.
 */
export async function getTicketStatuses(
  ticketIds: string[]
): Promise<TicketStatusInfo[]> {
  if (!INTERNAL_KEY) {
    console.error("[backend-client] BACKEND_INTERNAL_KEY not set — skipping MongoDB query");
    return [];
  }

  if (ticketIds.length === 0) return [];

  const res = await fetch(`${BACKEND_URL}/api/internal/feedback/ticket-status/batch`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Key": INTERNAL_KEY,
    },
    body: JSON.stringify({ ticket_ids: ticketIds }),
  });

  if (!res.ok) {
    const text = await res.text();
    console.error(`[backend-client] POST batch failed (${res.status}): ${text}`);
    return [];
  }

  return (await res.json()) as TicketStatusInfo[];
}

/** Connectivity + data diagnostic. Distinguishes "no config" / "no connection" / "empty" / "has data". */
export type BackendHealth =
  | { status: "no_config" }
  | { status: "unreachable"; error: string }
  | { status: "ok"; total: number; withTicket: number };

export async function getBackendHealth(): Promise<BackendHealth> {
  if (!INTERNAL_KEY) return { status: "no_config" };

  try {
    const res = await fetch(`${BACKEND_URL}/api/internal/feedback/stats`, {
      headers: { "X-Internal-Key": INTERNAL_KEY },
    });
    if (!res.ok) {
      return { status: "unreachable", error: `HTTP ${res.status}` };
    }
    const data = (await res.json()) as { total_feedbacks: number; with_ticket_id: number };
    return { status: "ok", total: data.total_feedbacks, withTicket: data.with_ticket_id };
  } catch (e) {
    return { status: "unreachable", error: String(e) };
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// Triage API methods
// ══════════════════════════════════════════════════════════════════════════════

export interface FeedbackRecord {
  feedback_id: string | null;
  rating: string;
  reason: string | null;
  created_at: string;
  conversation_id: string;
  message_id: string;
  user_id: string;
  context: Record<string, any> | null;
  ticket_id: string | null;
  status: string;
}

export interface ConversationData {
  messages: Array<{
    id: string;
    role: string;
    content: string;
    created_at: string;
    metadata: Record<string, any> | null;
  }>;
  artifacts?: Array<{
    id: string;
    type: string;
    title: string;
    content: any;
    created_at: string;
    expires_at: string | null;
  }>;
}

/**
 * Query feedback records with filters.
 */
export async function queryFeedback(
  params: {
    date_from?: string;
    date_to?: string;
    rating?: string;
    feedback_ids?: string[];
    limit?: number;
  }
): Promise<FeedbackRecord[]> {
  if (!INTERNAL_KEY) {
    console.error("[backend-client] BACKEND_INTERNAL_KEY not set");
    return [];
  }

  const res = await fetch(`${BACKEND_URL}/api/internal/feedback/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Key": INTERNAL_KEY,
    },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const text = await res.text();
    console.error(`[backend-client] feedback query failed (${res.status}): ${text}`);
    return [];
  }

  return (await res.json()) as FeedbackRecord[];
}

/**
 * Fetch full conversation threads with messages and artifacts.
 */
export async function getConversations(
  conversationIds: string[]
): Promise<Record<string, ConversationData>> {
  if (!INTERNAL_KEY || conversationIds.length === 0) return {};

  const res = await fetch(`${BACKEND_URL}/api/internal/feedback/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Key": INTERNAL_KEY,
    },
    body: JSON.stringify({
      conversation_ids: conversationIds,
      include_artifacts: true,
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    console.error(`[backend-client] conversations failed (${res.status}): ${text}`);
    return {};
  }

  return (await res.json()) as Record<string, ConversationData>;
}

export { STATUS_MAP };
