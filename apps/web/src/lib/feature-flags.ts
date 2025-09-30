import type { ToolId } from '@/types/tools'

const toBool = (value: string | undefined, defaultValue = false) => {
  if (value === undefined) return defaultValue
  return value.toLowerCase() === 'true'
}

export const featureFlags = {
  webSearch: toBool(process.env.NEXT_PUBLIC_FEATURE_WEB_SEARCH, true),
  deepResearch: toBool(process.env.NEXT_PUBLIC_FEATURE_DEEP_RESEARCH, true),
  addFiles: toBool(process.env.NEXT_PUBLIC_FEATURE_ADD_FILES, false),
  googleDrive: toBool(process.env.NEXT_PUBLIC_FEATURE_GOOGLE_DRIVE, false),
  canvas: toBool(process.env.NEXT_PUBLIC_FEATURE_CANVAS, false),
  agentMode: toBool(process.env.NEXT_PUBLIC_FEATURE_AGENT_MODE, false),
  mic: toBool(process.env.NEXT_PUBLIC_FEATURE_MIC, false),
  // Model selector production-style UI (default: true)
  useProdStyleModels: toBool(process.env.NEXT_PUBLIC_FEATURE_PROD_STYLE_MODELS, true),
}

export const visibleTools: Record<ToolId, boolean> = {
  'web-search': featureFlags.webSearch,
  'deep-research': featureFlags.deepResearch,
  'add-files': featureFlags.addFiles,
  'google-drive': featureFlags.googleDrive,
  canvas: featureFlags.canvas,
  'agent-mode': featureFlags.agentMode,
}
