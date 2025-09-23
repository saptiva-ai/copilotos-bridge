/**
 * HTTP client for CopilotOS Bridge API
 */

import axios, { AxiosInstance, AxiosError, AxiosHeaders } from 'axios'

import type {
  AuthTokens,
  RefreshTokenResponse,
  RegisterPayload,
  UserProfile,
  SaptivaKeyStatus,
  UpdateSaptivaKeyPayload,
} from './types'

export interface LoginRequest {
  identifier: string
  password: string
}

type AuthTokenGetter = () => string | null

const UNAUTHENTICATED_PATHS = ['/api/auth/login', '/api/auth/register', '/api/auth/refresh']

let authTokenGetter: AuthTokenGetter | null = null

export function setAuthTokenGetter(getter: AuthTokenGetter) {
  authTokenGetter = getter
}

// Types for API requests/responses
export interface ChatRequest {
  message: string
  chat_id?: string
  model?: string
  temperature?: number
  max_tokens?: number
  stream?: boolean
  tools_enabled?: Record<string, boolean>
  context?: Array<Record<string, string>>
}

export interface ChatResponse {
  chat_id: string
  message_id: string
  content: string
  role: 'assistant'
  model: string
  created_at: string
  tokens?: number
  latency_ms?: number
  finish_reason?: string
  tools_used?: string[]
  task_id?: string
}

export interface DeepResearchRequest {
  query: string
  research_type?: 'web_search' | 'deep_research'
  chat_id?: string
  stream?: boolean
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
  context?: Record<string, any>
}

export interface DeepResearchResponse {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  message: string
  result?: any
  progress?: number
  estimated_completion?: string
  created_at: string
  stream_url?: string
}

export interface HealthResponse {
  status: string
  timestamp: string
  version: string
  uptime_seconds: number
  checks: Record<string, any>
}

export interface ApiError {
  detail: string
  error?: string
  code?: string
}

class ApiClient {
  private client!: AxiosInstance
  private baseURL: string

  constructor() {
    // Smart API URL detection for different environments
    this.baseURL = this.getApiBaseUrl()
    this.initializeClient()
  }

  private getApiBaseUrl(): string {
    // Check if we're in browser environment
    if (typeof window === 'undefined') {
      // Server-side: use environment variable
      return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
    }

    // Client-side: determine based on environment
    const isLocal = window.location.hostname === 'localhost' ||
                   window.location.hostname === '127.0.0.1' ||
                   window.location.hostname.startsWith('192.168.') ||
                   window.location.hostname.endsWith('.local')

    if (isLocal) {
      // Development: use explicit API URL
      return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
    } else {
      // Production: use current origin (nginx proxy handles /api routes)
      return window.location.origin
    }
  }

  private initializeClient() {
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Client-Version': typeof window !== 'undefined' ? Date.now().toString() : 'server',
      },
      // Prevent axios from caching responses
      adapter: 'http'
    })

    // Request interceptor for auth tokens
    this.client.interceptors.request.use(
      (config) => {
        const requestUrl = config.url || ''
        const shouldSkipAuth = UNAUTHENTICATED_PATHS.some((path) => requestUrl.endsWith(path))

        if (!shouldSkipAuth) {
          const token = this.getAuthToken()
          if (token) {
            if (!config.headers) {
              config.headers = new AxiosHeaders()
            }
            config.headers.set('Authorization', `Bearer ${token}`)
          }
        }

        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        console.error('API Error:', {
          status: error.response?.status,
          data: error.response?.data,
          url: error.config?.url,
          method: error.config?.method,
        })
        return Promise.reject(error)
      }
    )
  }

  private getAuthToken(): string | null {
    try {
      if (authTokenGetter) {
        return authTokenGetter()
      }
    } catch (error) {
      console.warn('Failed to retrieve auth token', error)
    }
    return null
  }

  // Public method for components that need to access the token
  public getToken(): string | null {
    return this.getAuthToken()
  }

  // Auth endpoints
  async login(request: LoginRequest): Promise<AuthTokens> {
    const response = await this.client.post('/api/auth/login', {
      identifier: request.identifier,
      password: request.password,
    })

    return this.transformAuthResponse(response.data)
  }

  async register(payload: RegisterPayload): Promise<AuthTokens> {
    const response = await this.client.post('/api/auth/register', payload)
    return this.transformAuthResponse(response.data)
  }

  async refreshAccessToken(refreshToken: string): Promise<RefreshTokenResponse> {
    const response = await this.client.post('/api/auth/refresh', {
      refresh_token: refreshToken,
    })

    const data = response.data
    return {
      accessToken: data.access_token,
      expiresIn: data.expires_in,
    }
  }

  async getCurrentUser(): Promise<UserProfile> {
    const response = await this.client.get('/api/auth/me')
    return this.transformUserProfile(response.data)
  }

  private transformUserProfile(payload: any): UserProfile {
    if (!payload) {
      throw new Error('Invalid user payload')
    }

    return {
      id: payload.id,
      username: payload.username,
      email: payload.email,
      isActive: payload.is_active,
      createdAt: payload.created_at,
      updatedAt: payload.updated_at,
      lastLogin: payload.last_login ?? null,
      preferences: {
        theme: payload.preferences?.theme ?? 'auto',
        language: payload.preferences?.language ?? 'en',
        defaultModel: payload.preferences?.default_model ?? 'SAPTIVA_CORTEX',
        chatSettings: payload.preferences?.chat_settings ?? {},
      },
    }
  }

  private transformAuthResponse(payload: any): AuthTokens {
    return {
      accessToken: payload.access_token,
      refreshToken: payload.refresh_token,
      expiresIn: payload.expires_in,
      user: this.transformUserProfile(payload.user),
    }
  }

  private transformSaptivaKeyStatus(payload: any): SaptivaKeyStatus {
    return {
      configured: Boolean(payload?.configured),
      mode: payload?.mode === 'live' ? 'live' : 'demo',
      source: (payload?.source ?? 'unset') as SaptivaKeyStatus['source'],
      hint: payload?.hint ?? null,
      statusMessage: payload?.status_message ?? null,
      lastValidatedAt: payload?.last_validated_at ?? null,
      updatedAt: payload?.updated_at ?? null,
      updatedBy: payload?.updated_by ?? null,
    }
  }

  // Health check
  async healthCheck(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/api/health')
    return response.data
  }

  // Chat endpoints
  async sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>('/api/chat', request)
    return response.data
  }

  async getChatHistory(chatId: string, limit = 50, offset = 0): Promise<any> {
    const response = await this.client.get(`/api/history/${chatId}`, {
      params: { limit, offset }
    })
    return response.data
  }

  // Unified history endpoints
  async getUnifiedChatHistory(
    chatId: string,
    limit = 50,
    offset = 0,
    includeResearch = true,
    includeSources = false
  ): Promise<any> {
    const response = await this.client.get(`/api/history/${chatId}/unified`, {
      params: {
        limit,
        offset,
        include_research: includeResearch,
        include_sources: includeSources
      }
    })
    return response.data
  }

  async getChatStatus(chatId: string): Promise<any> {
    const response = await this.client.get(`/api/history/${chatId}/status`)
    return response.data
  }

  async getResearchTimeline(chatId: string, taskId: string): Promise<any> {
    const response = await this.client.get(`/api/history/${chatId}/research/${taskId}`)
    return response.data
  }

  async getChatSessions(limit = 20, offset = 0): Promise<any> {
    const response = await this.client.get('/api/sessions', {
      params: { limit, offset }
    })
    return response.data
  }

  async deleteChatSession(chatId: string): Promise<void> {
    await this.client.delete(`/api/sessions/${chatId}`)
  }

  // Deep research endpoints
  async startDeepResearch(request: DeepResearchRequest): Promise<DeepResearchResponse> {
    const response = await this.client.post<DeepResearchResponse>('/api/deep-research', request)
    return response.data
  }

  async getResearchStatus(taskId: string): Promise<DeepResearchResponse> {
    const response = await this.client.get<DeepResearchResponse>(`/api/deep-research/${taskId}`)
    return response.data
  }

  async cancelResearchTask(taskId: string, reason?: string): Promise<void> {
    await this.client.post(`/api/deep-research/${taskId}/cancel`, { 
      task_id: taskId, 
      reason 
    })
  }

  async getUserTasks(limit = 20, offset = 0, statusFilter?: string): Promise<any> {
    const response = await this.client.get('/api/tasks', {
      params: { limit, offset, status_filter: statusFilter }
    })
    return response.data
  }

  // Report endpoints
  async downloadReport(taskId: string, format = 'md', includeSources = true): Promise<Blob> {
    const response = await this.client.get(`/api/report/${taskId}`, {
      params: { format, include_sources: includeSources },
      responseType: 'blob'
    })
    return response.data
  }

  async getReportMetadata(taskId: string): Promise<any> {
    const response = await this.client.get(`/api/report/${taskId}/metadata`)
    return response.data
  }

  // Settings endpoints
  async getSaptivaKeyStatus(): Promise<SaptivaKeyStatus> {
    const response = await this.client.get('/api/settings/saptiva-key')
    return this.transformSaptivaKeyStatus(response.data)
  }

  async updateSaptivaKey(payload: UpdateSaptivaKeyPayload): Promise<SaptivaKeyStatus> {
    const response = await this.client.post('/api/settings/saptiva-key', {
      api_key: payload.apiKey,
      validate: payload.validate ?? true,
    })
    return this.transformSaptivaKeyStatus(response.data)
  }

  async deleteSaptivaKey(): Promise<SaptivaKeyStatus> {
    const response = await this.client.delete('/api/settings/saptiva-key')
    return this.transformSaptivaKeyStatus(response.data)
  }

  // Streaming utilities
  createEventSource(url: string): EventSource {
    const fullUrl = `${this.baseURL}${url}`
    return new EventSource(fullUrl)
  }

  // Helper method to handle API errors
  handleError(error: AxiosError<ApiError>): string {
    if (error.response?.data?.detail) {
      return error.response.data.detail
    }
    if (error.response?.data?.error) {
      return error.response.data.error
    }
    if (error.message) {
      return error.message
    }
    return 'An unknown error occurred'
  }

  // Connection status
  async checkConnection(): Promise<boolean> {
    try {
      await this.healthCheck()
      return true
    } catch (error) {
      return false
    }
  }
}

// Singleton instance
export const apiClient = new ApiClient()

// Hook for React components
export function useApiClient() {
  return apiClient
}
