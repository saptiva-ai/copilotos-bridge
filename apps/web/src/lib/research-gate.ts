import { classifyIntent, type Intent as GateIntent } from './intent'

interface GateDependencies {
  deepResearchOn: boolean
  openWizard: (userText: string) => void
  startResearch: (userText: string, scope?: Record<string, any>) => Promise<void>
  showNudge: (message: string) => void
  routeToChat: (userText: string) => Promise<void> | void
  askSplitTopics?: (userText: string) => void
}

export type ResearchGateOutcome =
  | { path: 'nudge'; intent: GateIntent }
  | { path: 'wizard'; intent: GateIntent }
  | { path: 'research'; intent: GateIntent }
  | { path: 'chat'; intent: GateIntent }
  | { path: 'split-topics'; intent: GateIntent }

const NUDGE_NEEDS_CONTEXT =
  '¿Qué te gustaría investigar? Especifica tema, alcance y periodo. Ej.: “Tendencia crédito PyME en MX 2023–2025”.'

const NUDGE_ENABLE_RESEARCH = 'Activa Deep Research para investigar esta consulta con trazabilidad completa.'

/**
 * Unified intent gate that decides whether to run deep research, open the scope wizard or
 * fallback to regular chat based on the user text and whether the Deep Research mode is enabled.
 */
export async function researchGate(text: string, deps: GateDependencies): Promise<ResearchGateOutcome> {
  // CLIENT-SIDE GUARD: Check if Deep Research is enabled
  // This is a UX guard - the real enforcement is server-side
  const deepResearchServerEnabled = process.env.DEEP_RESEARCH_ENABLED !== 'false';

  if (!deepResearchServerEnabled) {
    // Force chat mode when Deep Research is disabled
    await deps.routeToChat(text);
    return { path: 'chat', intent: await classifyIntent(text) };
  }

  const trimmed = text.trim()
  if (!trimmed) {
    return { path: 'nudge', intent: 'Greeting' as GateIntent }
  }

  const intent = await classifyIntent(trimmed)

  if (intent === 'Greeting') {
    if (deps.deepResearchOn) {
      deps.showNudge(NUDGE_NEEDS_CONTEXT)
      return { path: 'nudge', intent }
    }

    await deps.routeToChat(trimmed)
    return { path: 'chat', intent }
  }

  if (intent === 'ChitChat') {
    await deps.routeToChat(trimmed)
    return { path: 'chat', intent }
  }

  if (intent === 'Ambiguous') {
    if (deps.deepResearchOn) {
      deps.openWizard(trimmed)
      return { path: 'wizard', intent }
    }
    await deps.routeToChat(trimmed)
    return { path: 'chat', intent }
  }

  if (intent === 'Researchable') {
    if (deps.deepResearchOn) {
      await deps.startResearch(trimmed)
      return { path: 'research', intent }
    }
    deps.showNudge(NUDGE_ENABLE_RESEARCH)
    return { path: 'nudge', intent }
  }

  if (intent === 'MultiTopic' && deps.askSplitTopics) {
    deps.askSplitTopics(trimmed)
    return { path: 'split-topics', intent }
  }

  await deps.routeToChat(trimmed)
  return { path: 'chat', intent }
}
