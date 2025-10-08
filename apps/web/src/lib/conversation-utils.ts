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
  // Spanish
  'hola', 'buenas', 'ayuda', 'test', 'prueba', 'gracias', 'ayúdame', 'ayudame',
  'necesito', 'quiero', 'por', 'favor', 'porfavor', 'puedes', 'podrias', 'podrías',
  'me', 'como', 'cómo', 'que', 'qué', 'cual', 'cuál', 'cuando', 'cuándo',
  'donde', 'dónde', 'dame', 'dime', 'explicame', 'explícame', 'muestra', 'muestrame',
  'hazme', 'haz', 'hacer', 'tengo', 'hay', 'está', 'esta', 'es', 'son',
  // English
  'hi', 'hello', 'hey', 'thanks', 'please', 'help', 'can', 'could', 'would',
  'what', 'how', 'when', 'where', 'why', 'who', 'which', 'tell', 'show',
  'give', 'make', 'do', 'does', 'is', 'are', 'was', 'were', 'the', 'a', 'an'
])

/**
 * Derives a conversation title locally from the first user message.
 *
 * This is a fast heuristic that doesn't require API calls.
 *
 * Rules:
 * - Strip Markdown/HTML formatting and newlines
 * - Normalize whitespace
 * - Filter stopwords from beginning and middle
 * - Maximum 40 characters (optimized for sidebar UI)
 * - Limit to 5-6 most important words
 * - Smart truncation at word boundaries with ellipsis
 * - Capitalize first letter (sentence case)
 * - Remove final punctuation (.:;!?…)
 * - Returns fallback if quality is too low (< 8 chars or all stopwords)
 *
 * @param text - Raw message content
 * @returns Sanitized title (max 40 chars) or fallback
 *
 * @example
 * deriveTitleLocal("hola buenas, cómo configuro el servidor?")
 * // => "Configuro el servidor"
 *
 * @example
 * deriveTitleLocal("**Explicame** sobre machine learning y sus aplicaciones principales...")
 * // => "Machine learning aplicaciones..."
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

  // Remove final punctuation
  cleaned = cleaned.replace(/[.:;!?…]+$/, '')

  // Split into words and filter stopwords
  const words = cleaned.split(' ')
  const filteredWords = words.filter((word) => {
    const lower = word.toLowerCase()
    return !STOPWORDS.has(lower) && word.length > 0
  })

  // If nothing left after filtering, use first few words of original
  if (filteredWords.length === 0) {
    const fallbackWords = words.slice(0, 5).filter(w => w.length > 0)
    if (fallbackWords.length === 0) {
      return 'Nueva conversación'
    }
    filteredWords.push(...fallbackWords)
  }

  // Limit to first 5-6 most important words
  const maxWords = 6
  const importantWords = filteredWords.slice(0, maxWords)

  // Build title progressively, respecting character limit
  const maxLength = 40
  let draft = ''
  let addedWords = 0

  for (const word of importantWords) {
    const testDraft = draft ? `${draft} ${word}` : word

    // If adding this word exceeds limit, stop
    if (testDraft.length > maxLength) {
      break
    }

    draft = testDraft
    addedWords++
  }

  // Add ellipsis if we truncated
  const wasTruncated = addedWords < importantWords.length || filteredWords.length > maxWords
  if (wasTruncated && draft.length > 0) {
    // Only add ellipsis if it fits within limit
    if (draft.length + 3 <= maxLength) {
      draft += '...'
    }
  }

  // Capitalize first letter (sentence case) if not already capitalized
  if (draft && draft.length > 0 && draft[0] !== draft[0].toUpperCase()) {
    draft = draft.charAt(0).toUpperCase() + draft.slice(1)
  }

  // Quality check: if too short or empty, return fallback
  if (!draft || draft.length < 5) {
    return 'Nueva conversación'
  }

  return draft
}

/**
 * Generates a title for a conversation, using local heuristic or API fallback.
 *
 * Strategy:
 * 1. Try local derivation (fast, no API call)
 * 2. If quality is low (< 5 chars or fallback), use API endpoint
 * 3. Returns the best title available
 *
 * Note: With the new 40-char limit, local titles are now more concise
 * and suitable for sidebar display. API fallback is used less frequently.
 *
 * @param text - User message text
 * @param apiClient - Optional API client for remote generation
 * @returns Promise<string> - Generated title
 */
export async function generateTitleFromMessage(
  text: string,
  apiClient?: { generateTitle: (text: string) => Promise<{ title: string }> }
): Promise<string> {
  // Calculate local title as fallback
  const localTitle = deriveTitleLocal(text)

  // If API client is available, ALWAYS try AI generation first
  if (apiClient) {
    try {
      const response = await apiClient.generateTitle(text)
      // Ensure API title also respects length limit
      const apiTitle = response.title || localTitle
      if (apiTitle.length > 40) {
        // Truncate API title intelligently
        const truncated = apiTitle.slice(0, 37).trim()
        return truncated + '...'
      }
      return apiTitle
    } catch (error) {
      console.warn('Title generation via API failed, using local fallback:', error)
      return localTitle
    }
  }

  // No API client available, use local derivation
  return localTitle
}

/**
 * Computes a title from the first line of text (message-first pattern)
 * Optimized for immediate display, no API call required
 *
 * Rules:
 * - First line only
 * - Strip markdown (* _ # [] ())
 * - Trim and collapse whitespace
 * - Truncate to 70 chars with "…"
 * - Returns "Sin título" if empty
 *
 * @param text - Raw message text
 * @returns Sanitized title (max 70 chars)
 */
export function computeTitleFromText(text: string): string {
  if (!text || typeof text !== 'string') {
    return 'Sin título'
  }

  // Take first line only
  const firstLine = text.split('\n')[0]

  // Strip markdown and normalize whitespace
  let cleaned = firstLine
    .replace(/[`*_#>\[\]\(\)]/g, '') // Remove Markdown symbols
    .replace(/\s+/g, ' ')             // Normalize whitespace
    .trim()

  // Remove final punctuation
  cleaned = cleaned.replace(/[.:;!?…]+$/, '')

  // Check if empty after cleaning
  if (!cleaned || cleaned.length === 0) {
    return 'Sin título'
  }

  // Truncate to 70 chars with ellipsis
  const maxLength = 70
  if (cleaned.length > maxLength) {
    cleaned = cleaned.slice(0, maxLength - 1).trim() + '…'
  }

  return cleaned
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
 * Draft state type for memory-only conversations (message-first pattern)
 */
export interface DraftConversation {
  isDraftMode: boolean
  draftText: string
  draftModel?: string
  // Message-first fields
  cid?: string              // Client-generated ID for idempotency
  startedAt?: number        // Timestamp when draft was created
  cleanupTimerId?: number   // Timer ID for auto-cleanup
}

/**
 * Initial draft state
 */
export const INITIAL_DRAFT_STATE: DraftConversation = {
  isDraftMode: false,
  draftText: '',
  draftModel: undefined,
  cid: undefined,
  startedAt: undefined,
  cleanupTimerId: undefined,
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
