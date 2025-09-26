export type Intent =
  | 'Greeting'
  | 'ChitChat'
  | 'Command'
  | 'Researchable'
  | 'Ambiguous'
  | 'MultiTopic'

const RE_QUESTION = /(\?|\b(qué|como|cómo|por qué|por que|cuando|cuándo|donde|dónde|cuál|cual)\b)/i
const RE_EMPTY = /^\s*([hH]ola|buenas|buenos días|buenas tardes|hey|qué tal|:wave:)?\s*$/
const RE_COMMAND = /(configura|establece|crea|actualiza|ejecuta|borra|elimina)/i
const RE_GREETING_PREFIX = /^\s*(hola|buen[oa]s|buenos días|buenas tardes|hey|qué tal)([,!\s]|$)/i

function countConstraintMatches(text: string): number {
  const constraints = [
    /\b20\d{2}\b/g, // años explícitos
    /\b(latam|méxico|mx|europa|ee\.?uu\.?|usa|apac|emea)\b/gi,
    /https?:\/\//gi,
    /\b(impacto|comparativa|tendencia|riesgo|mercado|benchmark|pronóstico|forecast)\b/gi,
  ]

  return constraints.reduce((acc, re) => acc + ((text.match(re) || []).length), 0)
}

export function classifyLocally(rawText: string): Intent {
  const text = rawText.trim()

  if (!text || RE_EMPTY.test(text)) {
    return 'Greeting'
  }

  const greetingMatch = text.match(RE_GREETING_PREFIX)
  if (greetingMatch) {
    const remainder = text.slice(greetingMatch[0].length).trim()
    if (!remainder || remainder.split(/\s+/).length <= 4) {
      return 'Greeting'
    }
  }

  if (RE_COMMAND.test(text)) {
    return 'Command'
  }

  const constraintMatches = countConstraintMatches(text)

  if (RE_QUESTION.test(text)) {
    const wordCount = text.split(/\s+/).length

    if (constraintMatches >= 2) {
      return 'Researchable'
    }

    if (constraintMatches === 0 && wordCount <= 4) {
      return 'ChitChat'
    }

    return 'Ambiguous'
  }

  if (constraintMatches >= 2) {
    return 'Researchable'
  }

  if (constraintMatches === 1) {
    return 'Ambiguous'
  }

  return 'ChitChat'
}

interface IntentResponse {
  intent?: Intent
}

export async function classifyIntent(text: string): Promise<Intent> {
  const localIntent = classifyLocally(text)
  if (localIntent !== 'Ambiguous') {
    return localIntent
  }

  try {
    const response = await fetch('/api/intent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })

    if (!response.ok) {
      return localIntent
    }

    const payload = (await response.json()) as IntentResponse
    return payload.intent ?? localIntent
  } catch (error) {
    if (process.env.NODE_ENV !== 'production') {
      // eslint-disable-next-line no-console
      console.warn('[classifyIntent] fallback error', error)
    }
    return localIntent
  }
}
