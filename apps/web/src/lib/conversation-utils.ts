/**
 * Conversation utilities for title derivation and state management
 *
 * Implements progressive commitment pattern:
 * - Conversations exist only in memory (draft) until first message
 * - Title derived from first user message
 * - Timestamps set only when messages exist
 */

// Stopwords to filter out (low-value words)
const STOPWORDS = new Set([
  'hola', 'buenas', 'ayuda', 'test', 'prueba', 'gracias', 'hi', 'hello',
  'hey', 'thanks', 'please', 'ayúdame', 'ayudame', 'necesito', 'quiero',
  'por favor', 'porfavor'
])

/**
 * Derives a conversation title locally from the first user message.
 *
 * This is a fast heuristic that doesn't require API calls.
 *
 * Rules:
 * - Strip Markdown/HTML formatting and newlines
 * - Normalize whitespace
 * - Filter stopwords
 * - Maximum 70 characters
 * - Capitalize first letter (sentence case)
 * - Remove final punctuation (.:;!?…)
 * - Returns fallback if quality is too low (< 8 chars or all stopwords)
 *
 * @param text - Raw message content
 * @returns Sanitized title (max 70 chars) or fallback
 *
 * @example
 * deriveTitleLocal("hola buenas, cómo configuro el servidor?")
 * // => "Cómo configuro el servidor"
 *
 * @example
 * deriveTitleLocal("**Explicame** sobre machine learning y sus aplicaciones...")
 * // => "Explicame sobre machine learning y sus aplicaciones"
 */
export function deriveTitleLocal(text: string): string {
  if (!text || typeof text !== 'string') {
    return 'Nueva conversación'
  }

  // Take first line only (before any other processing)
  const firstLine = text.split('\n')[0]

  // Clean: strip Markdown, normalize whitespace
  let cleaned = firstLine
    .replace(/[`*_#>\[\]\(\)]/g, '') // Remove Markdown
    .replace(/\s+/g, ' ')             // Normalize whitespace
    .trim()

  // Limit initial length
  if (cleaned.length > 70) {
    cleaned = cleaned.slice(0, 70)
  }

  // Remove final punctuation
  cleaned = cleaned.replace(/[.:;!?…]+$/, '')

  // Filter stopwords at the beginning (preserve original case)
  const words = cleaned.split(' ')
  const lowercaseWords = words.map(w => w.toLowerCase())
  let startIndex = 0

  // Find first non-stopword
  while (startIndex < lowercaseWords.length && STOPWORDS.has(lowercaseWords[startIndex])) {
    startIndex++
  }

  // Get filtered words with original case preserved
  const filteredWords = words.slice(startIndex)

  // If nothing left after filtering, use original (without stopwords if possible)
  let draft = filteredWords.length > 0 ? filteredWords.join(' ') : cleaned

  // Capitalize first letter (sentence case) if not already capitalized
  if (draft && draft.length > 0 && draft[0] !== draft[0].toUpperCase()) {
    draft = draft.charAt(0).toUpperCase() + draft.slice(1)
  }

  // Quality check: if too short or empty, return fallback
  if (!draft || draft.length < 8) {
    return 'Nueva conversación'
  }

  return draft
}

/**
 * Generates a title for a conversation, using local heuristic or API fallback.
 *
 * Strategy:
 * 1. Try local derivation (fast, no API call)
 * 2. If quality is low (< 8 chars or fallback), use API endpoint
 * 3. Returns the best title available
 *
 * @param text - User message text
 * @param apiClient - Optional API client for remote generation
 * @returns Promise<string> - Generated title
 */
export async function generateTitleFromMessage(
  text: string,
  apiClient?: { generateTitle: (text: string) => Promise<{ title: string }> }
): Promise<string> {
  // Try local derivation first
  const localTitle = deriveTitleLocal(text)

  // If local title is good quality, use it
  if (localTitle !== 'Nueva conversación' && localTitle.length >= 8) {
    return localTitle
  }

  // Otherwise, try API if available
  if (apiClient) {
    try {
      const response = await apiClient.generateTitle(text)
      return response.title || localTitle
    } catch (error) {
      console.warn('Title generation via API failed, using local fallback:', error)
      return localTitle
    }
  }

  return localTitle
}

/**
 * Legacy function for backwards compatibility
 * @deprecated Use deriveTitleLocal or generateTitleFromMessage instead
 */
export function deriveTitleFromMessage(text: string): string {
  return deriveTitleLocal(text)
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
