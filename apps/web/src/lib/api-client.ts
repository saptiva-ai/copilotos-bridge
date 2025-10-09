/**
 * HTTP client for CopilotOS Bridge API
 */

import axios, { AxiosInstance, AxiosError, AxiosHeaders } from "axios";

import { logError, logWarn } from "./logger";

import type {
  AuthTokens,
  RefreshTokenResponse,
  RegisterPayload,
  UserProfile,
  SaptivaKeyStatus,
  UpdateSaptivaKeyPayload,
  FeatureFlagsResponse,
} from "./types";

export interface LoginRequest {
  identifier: string;
  password: string;
}

type AuthTokenGetter = () => string | null;
type LogoutHandler = (opts?: { reason?: string }) => void;

const UNAUTHENTICATED_PATHS = [
  "/api/auth/login",
  "/api/auth/register",
  "/api/auth/refresh",
];

let authTokenGetter: AuthTokenGetter | null = null;
let logoutHandler: LogoutHandler | null = null;

export function setAuthTokenGetter(getter: AuthTokenGetter) {
  authTokenGetter = getter;
}

export function setLogoutHandler(handler: LogoutHandler) {
  logoutHandler = handler;
}

// Types for API requests/responses
export interface ChatRequest {
  message: string;
  chat_id?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
  tools_enabled?: Record<string, boolean>;
  context?: Array<Record<string, string>>;
  document_ids?: string[];
}

export interface ChatResponse {
  chat_id: string;
  message_id: string;
  content: string;
  role: "assistant";
  model: string;
  created_at: string;
  tokens?: number;
  latency_ms?: number;
  finish_reason?: string;
  tools_used?: string[];
  task_id?: string;
  tools_enabled?: Record<string, boolean>;
}

export interface DeepResearchRequest {
  query: string;
  research_type?: "web_search" | "deep_research";
  chat_id?: string;
  stream?: boolean;
  params?: {
    budget?: number;
    max_iterations?: number;
    scope?: string;
    sources_limit?: number;
    depth_level?: "shallow" | "medium" | "deep";
    focus_areas?: string[];
    language?: string;
    include_citations?: boolean;
  };
  context?: Record<string, any>;
  // P0-DR-001: Explicit flag required to prevent auto-triggering
  explicit?: boolean;
}

export interface DeepResearchResponse {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  message: string;
  result?: any;
  progress?: number;
  estimated_completion?: string;
  created_at: string;
  stream_url?: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  uptime_seconds: number;
  checks: Record<string, any>;
}

export interface DocumentUploadResponse {
  doc_id: string;
  document_id?: string; // Backward compatibility
  filename: string;
  size_bytes: number;
  total_pages: number;
  status:
    | "uploading"
    | "processing"
    | "ready"
    | "failed"
    | "READY"
    | "PROCESSING";
  message?: string;
}

export interface ReviewStartRequest {
  doc_id: string;
  model?: string;
  rewrite_policy?: "conservative" | "moderate" | "aggressive";
  summary?: boolean;
  color_audit?: boolean;
}

export interface ReviewStartResponse {
  job_id: string;
  status: string;
}

export interface ReviewStatusResponse {
  job_id: string;
  status: string;
  progress: number;
  current_stage?: string;
  error_message?: string;
}

export interface ReviewReportResponse {
  doc_id: string;
  job_id: string;
  summary: Array<{ page: number; bullets: string[] }>;
  spelling: Array<{ page: number; span: string; suggestions: string[] }>;
  grammar: Array<{
    page: number;
    span: string;
    rule: string;
    explain: string;
    suggestions: string[];
  }>;
  style_notes: Array<{
    page: number;
    issue: string;
    advice: string;
    span?: string;
  }>;
  suggested_rewrites: Array<{
    page: number;
    block_id: string;
    original: string;
    proposal: string;
    rationale: string;
  }>;
  color_audit: {
    pairs: Array<{
      fg: string;
      bg: string;
      ratio: number;
      wcag: string;
      location?: string;
    }>;
    pass_count: number;
    fail_count: number;
  };
  artifacts: Record<string, any>;
  metrics: {
    lt_findings_count: number;
    llm_calls_count: number;
    tokens_in: number;
    tokens_out: number;
    processing_time_ms: number;
  };
  created_at: string;
  completed_at?: string;
  warnings?: Array<{ stage: string; code: string; message: string }>;
  llm_status?: "ok" | "degraded" | "failed";
}

export interface ApiError {
  detail: string;
  error?: string;
  code?: string;
}

class ApiClient {
  private client!: AxiosInstance;
  private baseURL: string;

  constructor() {
    // Smart API URL detection for different environments
    this.baseURL = this.getApiBaseUrl();
    this.initializeClient();
  }

  private getApiBaseUrl(): string {
    // Check if we're in browser environment
    if (typeof window === "undefined") {
      // Server-side: use environment variable
      return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
    }

    // Client-side: determine based on environment
    const isLocal =
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1" ||
      window.location.hostname.startsWith("192.168.") ||
      window.location.hostname.endsWith(".local");

    if (isLocal) {
      // Development: use Next.js proxy (rewrites in next.config.js)
      // This avoids CORS issues by making requests to same origin
      return window.location.origin;
    } else {
      // Production: use current origin (nginx proxy handles /api routes)
      return window.location.origin;
    }
  }

  private initializeClient() {
    // Create base config
    const config: any = {
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control":
          "no-store, no-cache, must-revalidate, proxy-revalidate",
        Pragma: "no-cache",
        Expires: "0",
        "X-Requested-With": "XMLHttpRequest",
        "X-Client-Version":
          typeof window !== "undefined" ? Date.now().toString() : "server",
      },
    };

    // Only explicitly set adapter if we're in Node.js environment
    if (typeof window === "undefined") {
      // Server-side: use http adapter
      config.adapter = "http";
    }
    // Browser will automatically use XMLHttpRequest adapter

    this.client = axios.create(config);

    // Request interceptor for auth tokens
    this.client.interceptors.request.use(
      (config) => {
        const requestUrl = config.url || "";
        const shouldSkipAuth = UNAUTHENTICATED_PATHS.some((path) =>
          requestUrl.endsWith(path),
        );

        if (!shouldSkipAuth) {
          const token = this.getAuthToken();
          if (token) {
            if (!config.headers) {
              config.headers = new AxiosHeaders();
            }
            config.headers.set("Authorization", `Bearer ${token}`);
          }
        }

        return config;
      },
      (error) => Promise.reject(error),
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        const errorInfo = {
          status: error.response?.status || "N/A",
          data: error.response?.data || "No response data",
          url: error.config?.url || "Unknown URL",
          method: (error.config?.method || "UNKNOWN").toUpperCase(),
          message: error.message || "Network error",
        };
        logError("API Error Details:", errorInfo);

        // Auto-logout on 401/403 (token expired/invalid)
        const status = error.response?.status;
        if (status === 401 || status === 403) {
          const requestUrl = error.config?.url || "";
          const isAuthEndpoint = UNAUTHENTICATED_PATHS.some((path) =>
            requestUrl.endsWith(path),
          );

          // Don't logout if error is from login/register (those are expected)
          if (!isAuthEndpoint && logoutHandler) {
            const errorCode = error.response?.data?.code || "token_expired";
            const reason = status === 401 ? "token_expired" : "token_invalid";

            logWarn("Auto-logout triggered", {
              status,
              reason,
              errorCode,
              url: requestUrl,
            });

            // Call logout handler (async, don't await)
            setTimeout(() => {
              logoutHandler({ reason });
            }, 100);
          }
        }

        return Promise.reject(error);
      },
    );
  }

  private getAuthToken(): string | null {
    try {
      if (authTokenGetter) {
        return authTokenGetter();
      }
    } catch (error) {
      logWarn("Failed to retrieve auth token", error);
    }
    return null;
  }

  // Public method for components that need to access the token
  public getToken(): string | null {
    return this.getAuthToken();
  }

  // Auth endpoints
  async login(request: LoginRequest): Promise<AuthTokens> {
    const response = await this.client.post("/api/auth/login", {
      identifier: request.identifier,
      password: request.password,
    });

    return this.transformAuthResponse(response.data);
  }

  async register(payload: RegisterPayload): Promise<AuthTokens> {
    const response = await this.client.post("/api/auth/register", payload);
    return this.transformAuthResponse(response.data);
  }

  async refreshAccessToken(
    refreshToken: string,
  ): Promise<RefreshTokenResponse> {
    const response = await this.client.post("/api/auth/refresh", {
      refresh_token: refreshToken,
    });

    const data = response.data;
    return {
      accessToken: data.access_token,
      expiresIn: data.expires_in,
    };
  }

  async getCurrentUser(): Promise<UserProfile> {
    const response = await this.client.get("/api/auth/me");
    return this.transformUserProfile(response.data);
  }

  async logout(): Promise<void> {
    await this.client.post("/api/auth/logout");
  }

  private transformUserProfile(payload: any): UserProfile {
    if (!payload) {
      throw new Error("Invalid user payload");
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
        theme: payload.preferences?.theme ?? "auto",
        language: payload.preferences?.language ?? "en",
        defaultModel: payload.preferences?.default_model ?? "SAPTIVA_CORTEX",
        chatSettings: payload.preferences?.chat_settings ?? {},
      },
    };
  }

  private transformAuthResponse(payload: any): AuthTokens {
    return {
      accessToken: payload.access_token,
      refreshToken: payload.refresh_token,
      expiresIn: payload.expires_in,
      user: this.transformUserProfile(payload.user),
    };
  }

  private transformSaptivaKeyStatus(payload: any): SaptivaKeyStatus {
    return {
      configured: Boolean(payload?.configured),
      mode: payload?.mode === "live" ? "live" : "demo",
      source: (payload?.source ?? "unset") as SaptivaKeyStatus["source"],
      hint: payload?.hint ?? null,
      statusMessage: payload?.status_message ?? null,
      lastValidatedAt: payload?.last_validated_at ?? null,
      updatedAt: payload?.updated_at ?? null,
      updatedBy: payload?.updated_by ?? null,
    };
  }

  // Health check
  async healthCheck(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>("/api/health");
    return response.data;
  }

  // Chat endpoints
  async sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>("/api/chat", request);
    return response.data;
  }

  // Document endpoints
  async uploadDocument(
    file: File,
    onProgress?: (progress: number) => void,
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await this.client.post<DocumentUploadResponse>(
      "/api/documents/upload",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total,
            );
            onProgress(percentCompleted);
          }
        },
      },
    );
    return response.data;
  }

  // Document review endpoints
  async startDocumentReview(
    request: ReviewStartRequest,
  ): Promise<ReviewStartResponse> {
    const response = await this.client.post<ReviewStartResponse>(
      "/api/review/start",
      request,
    );
    return response.data;
  }

  async getReviewStatus(jobId: string): Promise<ReviewStatusResponse> {
    const response = await this.client.get<ReviewStatusResponse>(
      `/api/review/status/${jobId}`,
    );
    return response.data;
  }

  async getReviewReport(docId: string): Promise<ReviewReportResponse> {
    const response = await this.client.get<ReviewReportResponse>(
      `/api/review/report/${docId}`,
    );
    return response.data;
  }

  async getChatHistory(chatId: string, limit = 50, offset = 0): Promise<any> {
    const response = await this.client.get(`/api/history/${chatId}`, {
      params: { limit, offset },
    });
    return response.data;
  }

  // Unified history endpoints
  async getUnifiedChatHistory(
    chatId: string,
    limit = 50,
    offset = 0,
    includeResearch = true,
    includeSources = false,
  ): Promise<any> {
    const response = await this.client.get(`/api/history/${chatId}/unified`, {
      params: {
        limit,
        offset,
        include_research: includeResearch,
        include_sources: includeSources,
      },
    });
    return response.data;
  }

  async getChatStatus(chatId: string): Promise<any> {
    const response = await this.client.get(`/api/history/${chatId}/status`);
    return response.data;
  }

  async getResearchTimeline(chatId: string, taskId: string): Promise<any> {
    const response = await this.client.get(
      `/api/history/${chatId}/research/${taskId}`,
    );
    return response.data;
  }

  async getChatSessions(limit = 20, offset = 0): Promise<any> {
    const response = await this.client.get("/api/sessions", {
      params: { limit, offset },
    });
    return response.data;
  }

  async updateChatSession(
    chatId: string,
    updates: {
      title?: string;
      pinned?: boolean;
      tools_enabled?: Record<string, boolean>;
      auto_title?: boolean;
    },
  ): Promise<void> {
    await this.client.patch(`/api/sessions/${chatId}`, updates);
  }

  async renameChatSession(chatId: string, title: string): Promise<void> {
    await this.updateChatSession(chatId, { title });
  }

  async pinChatSession(chatId: string, pinned: boolean): Promise<void> {
    await this.updateChatSession(chatId, { pinned });
  }

  async deleteChatSession(chatId: string): Promise<void> {
    await this.client.delete(`/api/sessions/${chatId}`);
  }

  // P0-FLUJO-NEW-POST: Create conversation first (before any messages)
  async createConversation(
    params?: {
      title?: string;
      model?: string;
      tools_enabled?: Record<string, boolean>;
    },
    options?: { idempotencyKey?: string },
  ): Promise<any> {
    const requestConfig = options?.idempotencyKey
      ? { headers: { "Idempotency-Key": options.idempotencyKey } }
      : undefined;

    const response = await this.client.post(
      "/api/conversations",
      {
        title: params?.title,
        model: params?.model || "SAPTIVA_CORTEX",
        tools_enabled: params?.tools_enabled,
      },
      requestConfig,
    );
    return response.data;
  }

  // Deep research endpoints
  async startDeepResearch(
    request: DeepResearchRequest,
  ): Promise<DeepResearchResponse> {
    // P0-DR-001: Always set explicit=true when called from frontend
    // This ensures Deep Research is only triggered by explicit user action
    const requestWithExplicit: DeepResearchRequest = {
      ...request,
      explicit: true,
    };
    const response = await this.client.post<DeepResearchResponse>(
      "/api/deep-research",
      requestWithExplicit,
    );
    return response.data;
  }

  async getResearchStatus(taskId: string): Promise<DeepResearchResponse> {
    const response = await this.client.get<DeepResearchResponse>(
      `/api/deep-research/${taskId}`,
    );
    return response.data;
  }

  async cancelResearchTask(taskId: string, reason?: string): Promise<void> {
    await this.client.post(`/api/deep-research/${taskId}/cancel`, {
      task_id: taskId,
      reason,
    });
  }

  async getUserTasks(
    limit = 20,
    offset = 0,
    statusFilter?: string,
  ): Promise<any> {
    const response = await this.client.get("/api/tasks", {
      params: { limit, offset, status_filter: statusFilter },
    });
    return response.data;
  }

  // Report endpoints
  async downloadReport(
    taskId: string,
    format = "md",
    includeSources = true,
  ): Promise<Blob> {
    const response = await this.client.get(`/api/report/${taskId}`, {
      params: { format, include_sources: includeSources },
      responseType: "blob",
    });
    return response.data;
  }

  async getReportMetadata(taskId: string): Promise<any> {
    const response = await this.client.get(`/api/report/${taskId}/metadata`);
    return response.data;
  }

  // Settings endpoints
  async getSaptivaKeyStatus(): Promise<SaptivaKeyStatus> {
    const response = await this.client.get("/api/settings/saptiva-key");
    return this.transformSaptivaKeyStatus(response.data);
  }

  async updateSaptivaKey(
    payload: UpdateSaptivaKeyPayload,
  ): Promise<SaptivaKeyStatus> {
    const response = await this.client.post("/api/settings/saptiva-key", {
      api_key: payload.apiKey,
      validate: payload.validate ?? true,
    });
    return this.transformSaptivaKeyStatus(response.data);
  }

  async deleteSaptivaKey(): Promise<SaptivaKeyStatus> {
    const response = await this.client.delete("/api/settings/saptiva-key");
    return this.transformSaptivaKeyStatus(response.data);
  }

  // Feature flags endpoints
  async getFeatureFlags(): Promise<FeatureFlagsResponse> {
    const response =
      await this.client.get<FeatureFlagsResponse>("/api/feature-flags");
    return response.data;
  }

  // Model endpoints
  async getModels(): Promise<{
    default_model: string;
    allowed_models: string[];
  }> {
    const response = await this.client.get("/api/models");
    return response.data;
  }

  // Title generation endpoint
  async generateTitle(text: string): Promise<{ title: string }> {
    const response = await this.client.post("/api/title", { text });
    return response.data;
  }

  // Streaming utilities
  createEventSource(url: string): EventSource {
    const fullUrl = `${this.baseURL}${url}`;
    return new EventSource(fullUrl);
  }

  // Helper method to handle API errors
  handleError(error: AxiosError<ApiError>): string {
    if (error.response?.data?.detail) {
      return error.response.data.detail;
    }
    if (error.response?.data?.error) {
      return error.response.data.error;
    }
    if (error.message) {
      return error.message;
    }
    return "An unknown error occurred";
  }

  // Connection status
  async checkConnection(): Promise<boolean> {
    try {
      await this.healthCheck();
      return true;
    } catch (error) {
      return false;
    }
  }
}

// Singleton instance
export const apiClient = new ApiClient();

// Hook for React components
export function useApiClient() {
  return apiClient;
}
