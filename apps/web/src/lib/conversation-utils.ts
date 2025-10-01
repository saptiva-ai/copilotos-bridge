/**
 * Conversation utilities for title derivation and state management
 *
 * Implements progressive commitment pattern:
 * - Conversations exist only in memory (draft) until first message
 * - Title derived from first user message
 * - Timestamps set only when messages exist
 */

/**
 * Derives a conversation title from the first user message
 *
 * Rules:
 * - Strip Markdown/HTML formatting
 * - Normalize whitespace
 * - Maximum 40 characters with ellipsis
 * - Returns sanitized plain text
 *
 * @param text - Raw message content
 * @returns Sanitized title (max 40 chars)
 *
 * @example
 * deriveTitleFromMessage("**How** do I deploy this?")
 * // => "How do I deploy this?"
 *
 * @example
 * deriveTitleFromMessage("A very long question about something complex...")
 * // => "A very long question about something…"
 */
export function deriveTitleFromMessage(text: string): string {
  if (!text || typeof text !== 'string') {
    return 'Nueva conversación'
  }

  // Strip Markdown: **, *, _, `, #, >, [], ()
  let plain = text.replace(/[`*_#>\[\]\(\)]/g, '')

  // Normalize whitespace
  plain = plain.replace(/\s+/g, ' ').trim()

  // If empty after sanitization
  if (!plain) {
    return 'Nueva conversación'
  }

  // Truncate to 40 chars with ellipsis
  const maxLength = 40
  if (plain.length <= maxLength) {
    return plain
  }

  return plain.slice(0, maxLength - 1) + '…'
}

/**
 * Checks if a conversation is empty (no messages)
 */
export function isConversationEmpty(messageCount: number, firstMessageAt: string | null): boolean {
  return messageCount === 0 || !firstMessageAt
}

/**
 * Formats a conversation title for display
 * Falls back to placeholder if title is generic
 */
export function formatConversationTitle(title: string, messageCount: number): string {
  if (!title || title.trim() === '') {
    return messageCount > 0 ? 'Conversación' : 'Nueva conversación'
  }

  // If title is still the default and there are messages, show first message indicator
  if (title === 'Nueva conversación' && messageCount > 0) {
    return 'Conversación'
  }

  return title
}

/**
 * Draft state type for memory-only conversations
 */
export interface DraftConversation {
  isDraftMode: boolean
  draftText: string
  draftModel?: string
}

/**
 * Initial draft state
 */
export const INITIAL_DRAFT_STATE: DraftConversation = {
  isDraftMode: false,
  draftText: '',
  draftModel: undefined,
}

/**
 * Validates a conversation for persistence
 * Only conversations with messages should be persisted
 */
export function shouldPersistConversation(
  messageCount: number,
  firstMessageAt: string | null
): boolean {
  return messageCount > 0 && firstMessageAt !== null
}
