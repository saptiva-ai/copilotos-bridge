/**
 * HTTP client for CopilotOS Bridge API
 */

import axios, { AxiosInstance, AxiosError } from 'axios'

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
  private client: AxiosInstance
  private baseURL: string

  constructor() {
    // Use environment variables or defaults
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor for auth tokens
    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = this.getAuthToken()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
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
    // In a real app, get from localStorage, cookies, or auth store
    return null
  }

  // Public method for components that need to access the token
  public getToken(): string | null {
    return this.getAuthToken()
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