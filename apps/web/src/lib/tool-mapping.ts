import type { ToolId } from '@/types/tools'

type ToolKey = 'web_search' | 'deep_research' | 'code_analysis' | 'document_analysis'

const LEGACY_KEY_TO_TOOL_ID_MAP: Record<ToolKey, ToolId> = {
  web_search: 'web-search',
  deep_research: 'deep-research',
  code_analysis: 'agent-mode',
  document_analysis: 'canvas',
}

const TOOL_ID_TO_LEGACY_KEY_MAP: Partial<Record<ToolId, ToolKey>> = {
  'web-search': 'web_search',
  'deep-research': 'deep_research',
  'agent-mode': 'code_analysis',
  canvas: 'document_analysis',
}

export const KNOWN_TOOL_KEYS: ToolKey[] = Object.keys(LEGACY_KEY_TO_TOOL_ID_MAP) as ToolKey[]

export function legacyKeyToToolId(key: string): ToolId | undefined {
  return LEGACY_KEY_TO_TOOL_ID_MAP[key as ToolKey]
}

export function toolIdToLegacyKey(id: ToolId): ToolKey | undefined {
  return TOOL_ID_TO_LEGACY_KEY_MAP[id]
}

export function createDefaultToolsState(
  extraToolKeys: string[] = []
): Record<string, boolean> {
  const baseKeys = [...KNOWN_TOOL_KEYS, ...extraToolKeys]
  return baseKeys.reduce<Record<string, boolean>>((acc, key) => {
    if (!(key in acc)) {
      acc[key] = false
    }
    return acc
  }, {})
}

export function normalizeToolsState(raw?: Record<string, boolean>): Record<string, boolean> {
  const extraKeys = raw ? Object.keys(raw) : []
  const normalized = createDefaultToolsState(extraKeys)
  if (raw) {
    Object.entries(raw).forEach(([key, value]) => {
      normalized[key] = Boolean(value)
    })
  }
  return normalized
}
