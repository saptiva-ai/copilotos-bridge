/**
 * Type definitions for the application
 */

// Chat related types
export interface ChatMessage {
  id: string
  content: string
  role: 'user' | 'assistant' | 'system'
  timestamp: string
  model?: string
  tokens?: number
  latency?: number
  toolsUsed?: string[]
  isError?: boolean
  isStreaming?: boolean
  task_id?: string
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