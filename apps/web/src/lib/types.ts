/**
 * Type definitions for the application
 */

// User/auth related types
export interface UserPreferencesProfile {
  theme: string
  language: string
  defaultModel: string
  chatSettings: Record<string, unknown>
}

export interface UserProfile {
  id: string
  username: string
  email: string
  isActive: boolean
  createdAt: string
  updatedAt: string
  lastLogin?: string | null
  preferences: UserPreferencesProfile
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
  expiresIn: number
  user: UserProfile
}

export interface RefreshTokenResponse {
  accessToken: string
  expiresIn: number
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
}

// Chat related types
export type ChatMessageStatus = 'sending' | 'streaming' | 'delivered' | 'error'

export interface ChatMessage {
  id: string
  content: string
  role: 'user' | 'assistant' | 'system'
  timestamp: string | Date
  status?: ChatMessageStatus
  model?: string
  tokens?: number
  latency?: number
  toolsUsed?: string[]
  isError?: boolean
  isStreaming?: boolean
  task_id?: string
  // UX-004 file attachments metadata
  attachments?: {
    name: string
    size: number
    type: string
  }[]
  metadata?: {
    research_task?: ResearchTask
    [key: string]: any
  }
}

export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
  model: string
  preview?: string
  pinned?: boolean
}

// Research related types
export interface ResearchTask {
  id: string
  query: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress?: number
  result?: any
  created_at: string
  updated_at: string
  estimated_completion?: string
  stream_url?: string
  research_type?: 'web_search' | 'deep_research'
  params?: {
    budget?: number
    max_iterations?: number
    scope?: string
    sources_limit?: number
    depth_level?: 'shallow' | 'medium' | 'deep'
    focus_areas?: string[]
    language?: string
    include_citations?: boolean
  }
}

// Model related types
export interface ModelInfo {
  id: string
  name: string
  description: string
  maxTokens: number
  supportsStreaming: boolean
  supportsTools: boolean
  category: 'general' | 'coding' | 'research' | 'creative'
  status: 'available' | 'unavailable' | 'maintenance'
}

// Tool related types
export interface ToolConfig {
  id: string
  name: string
  description: string
  enabled: boolean
  category: 'search' | 'analysis' | 'generation' | 'processing'
  parameters?: Record<string, any>
}

// API response types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pages: number
  limit: number
}

// Streaming event types (from streaming.ts)
export interface StreamEvent {
  event_type: string
  task_id: string
  timestamp: string
  data: Record<string, any>
  progress?: number
}

// Settings types
export interface UserSettings {
  theme: 'light' | 'dark' | 'system'
  language: string
  notifications: {
    enabled: boolean
    taskCompletion: boolean
    errors: boolean
  }
  chat: {
    defaultModel: string
    maxTokens: number
    temperature: number
    streamEnabled: boolean
    autoScroll: boolean
  }
  research: {
    defaultDepthLevel: 'shallow' | 'medium' | 'deep'
    maxSources: number
    includeCitations: boolean
    autoExport: boolean
  }
}

export type SaptivaKeySource = 'unset' | 'environment' | 'database'

export interface SaptivaKeyStatus {
  configured: boolean
  mode: 'demo' | 'live'
  source: SaptivaKeySource
  hint?: string | null
  statusMessage?: string | null
  lastValidatedAt?: string | null
  updatedAt?: string | null
  updatedBy?: string | null
}

export interface UpdateSaptivaKeyPayload {
  apiKey: string
  validate?: boolean
}

// Error types
export interface AppError {
  code: string
  message: string
  details?: any
  timestamp: string
  context?: Record<string, any>
}

// Navigation types
export interface NavItem {
  id: string
  label: string
  href: string
  icon?: React.ComponentType
  badge?: string | number
  children?: NavItem[]
}

// File/Report types
export interface ReportMetadata {
  id: string
  title: string
  format: 'md' | 'pdf' | 'docx' | 'html'
  size: number
  created_at: string
  sources_count: number
  pages?: number
}

export interface ExportOptions {
  format: 'md' | 'pdf' | 'docx' | 'html'
  includeSources: boolean
  includeMetadata: boolean
  template?: string
}
