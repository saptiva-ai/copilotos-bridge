/**
 * HTTP client for CopilotOS Bridge API
 */

import axios, { AxiosInstance, AxiosError, AxiosHeaders } from "axios";

import { logError, logWarn } from "./logger";
import { sha256Hex } from "./hash";

import type {
  AuthTokens,
  RefreshTokenResponse,
  RegisterPayload,
  UserProfile,
  SaptivaKeyStatus,
  UpdateSaptivaKeyPayload,
  FeatureFlagsResponse,
  ArtifactRecord,
  ArtifactType,
  ToolInvocation,
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
  chat_id?: string | null; // Allow explicit null to indicate "create new chat"
  model?: string;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
  tools_enabled?: Record<string, boolean>;
  context?: Array<Record<string, string>>;
  document_ids?: string[]; // Legacy document system
  file_ids?: string[]; // Files V1 system
  // MVP-LOCK: File metadata for persistence (includes file_ids + full file info)
  metadata?: {
    files?: Array<{
      file_id: string;
      filename: string;
      size: number;
      mime_type: string;
    }>;
  };
}

export interface ChatResponse {
  chat_id: string;
  message_id: string;
  content: string;
  artifact?: Record<string, any> | null;
  role: "assistant";
  model: string;
  created_at: string;
  tokens?: number;
  latency_ms?: number;
  finish_reason?: string;
  tools_used?: string[];
  task_id?: string;
  tools_enabled?: Record<string, boolean>;
  decision_metadata?: {
    warnings?: string[];
    docs_used?: number;
    docs_expired?: string[];
  };
  metadata?: {
    tool_invocations?: ToolInvocation[];
    [key: string]: any;
  }; // Include audit metadata (report_pdf_url, etc.)
}

export interface ChatMessageRecord {
  id: string;
  chat_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  status?: string;
  created_at: string;
  updated_at?: string;
  model?: string;
  tokens?: number;
  latency_ms?: number;
  task_id?: string;
  file_ids?: string[];
  files?: Array<Record<string, any>>;
  metadata?: Record<string, any> | null;
  validation_report_id?: string | null;
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
    // CRITICAL: Direct inline check - Next.js replaces process.env.NEXT_PUBLIC_* at build time
    // We MUST use direct access without intermediate variables for replacement to work

    // Check if we're in browser environment
    if (typeof window === "undefined") {
      // Server-side: use environment variable with fallback chain
      return (
        process.env.NEXT_PUBLIC_API_URL ||
        process.env.API_BASE_URL ||
        "http://localhost:8000"
      );
    }

    // Client-side: Direct inline check ensures Next.js static replacement works
    // This pattern MUST NOT use intermediate constants or the bundler will collapse it
    // IMPORTANT: Empty string means use Next.js proxy (relative paths)
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (apiUrl && apiUrl.trim() !== "") {
      return apiUrl;
    }

    // Empty or undefined: use relative paths for Next.js proxy
    // In dev: /api/* -> next.config.js proxy -> http://api:8001/api/*
    return "";
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
      async (error: AxiosError<ApiError>) => {
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
              logoutHandler?.({ reason });
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

  async get<T = any>(
    url: string,
    config?: import("axios").AxiosRequestConfig,
  ): Promise<{ data: T }> {
    const response = await this.client.get<T>(url, config);
    return { data: response.data };
  }

  async post<T = any>(
    url: string,
    body?: any,
    config?: import("axios").AxiosRequestConfig,
  ): Promise<{ data: T }> {
    const response = await this.client.post<T>(url, body, config);
    return { data: response.data };
  }

  async delete<T = any>(
    url: string,
    config?: import("axios").AxiosRequestConfig,
  ): Promise<{ data: T }> {
    const response = await this.client.delete<T>(url, config);
    return { data: response.data };
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
  async sendChatMessage(
    request: ChatRequest,
    retries: number = 2,
  ): Promise<ChatResponse> {
    // FE-3 MVP: Force 'Saptiva Turbo' default if model not specified
    const payload = { model: "Saptiva Turbo", ...request };

    // Detect if request involves file analysis
    const hasFiles =
      (request.file_ids && request.file_ids.length > 0) ||
      (request.metadata?.files &&
        Array.isArray(request.metadata.files) &&
        request.metadata.files.length > 0);

    // Increase timeout for file analysis (3 minutes vs 30s default)
    const timeout = hasFiles ? 180000 : 30000;

    // ISSUE-026: Retry logic with exponential backoff
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const response = await this.client.post<ChatResponse>(
          "/api/chat",
          payload,
          { timeout },
        );
        return response.data;
      } catch (e: any) {
        // Determine if we should retry
        const shouldRetry =
          !e.response || // Network error
          (e.response.status >= 500 && e.response.status < 600); // Server error

        // Don't retry if it was a timeout on a file request (it might still be processing)
        // But wait, if it's a network timeout, e.code might be 'ECONNABORTED'
        const isTimeout = e.code === "ECONNABORTED";
        if (isTimeout && hasFiles) {
          // If it timed out after 3 minutes, retrying probably won't help and will cause duplicates
          // Better to let it fail so user knows it's taking too long
          console.warn(
            "File analysis timed out after 3m, not retrying to avoid duplicates",
          );
          throw e;
        }

        const isLastAttempt = attempt === retries;

        if (!shouldRetry || isLastAttempt) {
          // Fix Pack: Defensive logging for debugging file_ids issues
          console.error("POST /api/chat failed", {
            status: e?.response?.status,
            data: e?.response?.data,
            payload,
            attempt: attempt + 1,
            totalAttempts: retries + 1,
            isTimeout: e.code === "ECONNABORTED",
          });
          throw e;
        }

        // Exponential backoff: 1s, 2s, max 5s
        const delay = Math.min(1000 * Math.pow(2, attempt), 5000);
        console.warn(`POST /api/chat failed, retrying in ${delay}ms`, {
          attempt: attempt + 1,
          status: e?.response?.status,
        });
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }

    // This should never be reached, but TypeScript requires it
    throw new Error("Unexpected: retry loop exited without return");
  }

  /**
   * Send chat message with streaming support via SSE.
   * Returns an async generator that yields content chunks.
   */
  async *sendChatMessageStream(
    request: ChatRequest,
    abortSignal?: AbortSignal,
  ): AsyncGenerator<
    | {
        type: "meta";
        data: { chat_id: string; user_message_id: string; model: string };
      }
    | { type: "bank_chart"; data: any }
    | { type: "bank_clarification"; data: any }
    | {
        type: "artifact_created";
        data: {
          artifact_id: string;
          type: string;
          title: string;
          created_at: string;
        };
      }
    | { type: "chunk"; data: { content: string } }
    | { type: "done"; data: ChatResponse }
    | { type: "error"; data: { error: string } },
    void,
    unknown
  > {
    const payload = { model: "Saptiva Turbo", ...request, stream: true };
    // console.log("[🔍 PAYLOAD DEBUG] Request payload:", JSON.stringify(payload, null, 2));
    const token = authTokenGetter?.();

    // Build query params
    const params = new URLSearchParams();

    // Build URL
    const baseURL = this.client.defaults.baseURL || "";
    const url = `${baseURL}/api/chat`;

    try {
      // Use fetch with SSE
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream", // CRITICAL: Tell backend we want SSE format
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
        signal: abortSignal,
      });

      if (!response.ok) {
        if (
          (response.status === 401 || response.status === 403) &&
          logoutHandler
        ) {
          const reason =
            response.status === 401 ? "token_expired" : "token_invalid";
          logWarn("Streaming request unauthorized, forcing logout", {
            status: response.status,
            reason,
            url,
          });
          setTimeout(() => {
            logoutHandler?.({ reason });
          }, 100);
        }
        // 🚨 ENHANCED ERROR LOGGING: Capture full error details from backend
        const errorText = await response.text();

        // Try to parse as JSON for structured errors (e.g., Pydantic validation errors)
        let errorBody: any = errorText;
        try {
          errorBody = JSON.parse(errorText);
        } catch {
          // Not JSON, use raw text
        }

        console.error("🚨 API CHAT ERROR:", {
          status: response.status,
          statusText: response.statusText,
          url: url,
          body: errorBody,
          payload: payload, // Include payload for debugging
        });

        // Throw with detailed message
        const errorMessage =
          typeof errorBody === "object"
            ? errorBody.detail || errorBody.message || JSON.stringify(errorBody)
            : errorBody;

        throw new Error(
          `Failed to send message (${response.status} ${response.statusText}): ${errorMessage}`,
        );
      }

      if (!response.body) {
        throw new Error("Response body is null");
      }

      // Parse SSE stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "";
      let chunkCount = 0;
      const extractJsonCandidate = (raw: string) => {
        const firstBrace = raw.indexOf("{");
        if (firstBrace === -1) return null;
        let depth = 0;
        for (let i = firstBrace; i < raw.length; i++) {
          const char = raw[i];
          if (char === "{") {
            depth++;
          } else if (char === "}") {
            depth--;
            if (depth === 0) {
              return raw.slice(firstBrace, i + 1);
            }
          }
        }
        return null;
      };

      // console.log("[🔍 SSE DEBUG] Starting to read SSE stream");

      try {
        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            // If stream ends and we have buffered JSON with no events, try to parse it
            const candidate =
              extractJsonCandidate(buffer.trim()) || buffer.trim();
            if (candidate && candidate.startsWith("{")) {
              try {
                const parsed = JSON.parse(candidate);
                yield { type: "done", data: parsed as ChatResponse };
                return;
              } catch (finalErr) {
                console.error(
                  "[🔍 NON-STREAMING END] Failed to parse buffered JSON:",
                  finalErr,
                );
              }
            }
            // console.log("[🔍 SSE DEBUG] Stream done - total chunks received:", chunkCount);
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          // console.log("[🔍 SSE DEBUG] Raw chunk received (length:", chunk.length, "):", chunk.substring(0, 200));
          chunkCount++;
          buffer += chunk;

          // WORKAROUND: Detect if backend sent JSON response (non-streaming mode)
          // When documents are attached, backend forces non-streaming and returns plain JSON
          if (
            chunkCount === 1 &&
            chunk.trim().startsWith("{") &&
            !chunk.includes("event:") &&
            !chunk.includes("data:")
          ) {
            // console.log("[🔍 NON-STREAMING DETECTED] Backend sent JSON response, parsing as ChatResponse");
            try {
              const candidate = extractJsonCandidate(buffer) || buffer;
              const jsonResponse = JSON.parse(candidate);
              // console.log("[🔍 NON-STREAMING] Parsed response:", jsonResponse);
              yield { type: "done", data: jsonResponse as ChatResponse };
              return; // Exit early - no more chunks expected
            } catch (jsonError) {
              console.error(
                "[🔍 NON-STREAMING] Failed to parse JSON response:",
                jsonError,
              );
              // Fallback: treat buffer as plain content to avoid breaking the flow
              yield {
                type: "done",
                data: {
                  chat_id: "",
                  message_id: "",
                  content: buffer,
                  role: "assistant",
                  model: "",
                  created_at: new Date().toISOString(),
                } as ChatResponse,
              };
              return;
            }
          }

          const lines = buffer.split("\n");
          buffer = lines.pop() || ""; // Keep incomplete line in buffer

          for (const line of lines) {
            if (!line.trim() || line.startsWith(":")) continue;

            // Parse SSE format: "event: chunk\ndata: {...}"
            if (line.startsWith("event:")) {
              currentEvent = line.slice(6).trim();
              // console.log("[🔍 SSE DEBUG] Event type:", currentEvent);
              continue;
            }

            if (line.startsWith("data:")) {
              const dataStr = line.slice(5).trim();
              // console.log("[🔍 SSE DEBUG] Data received for event:", currentEvent, "data length:", dataStr.length);

              if (dataStr === "[DONE]") {
                return;
              }

              try {
                const parsed = JSON.parse(dataStr);

                // Use the event type from the "event:" line
                if (currentEvent === "meta") {
                  console.warn("[🔍 SSE] Meta event received:", parsed);
                  yield { type: "meta", data: parsed };
                } else if (currentEvent === "bank_chart") {
                  console.warn(
                    "[📊 BANK_CHART] Event received from SSE:",
                    parsed,
                  );
                  yield { type: "bank_chart", data: parsed };
                } else if (currentEvent === "bank_clarification") {
                  console.warn(
                    "[❓ BANK_CLARIFICATION] Event received from SSE:",
                    parsed,
                  );
                  yield { type: "bank_clarification", data: parsed };
                } else if (currentEvent === "chunk") {
                  // Chunk logging disabled to avoid spam
                  yield { type: "chunk", data: parsed };
                } else if (currentEvent === "done") {
                  console.warn("[🔍 SSE] Done event received");
                  yield { type: "done", data: parsed as ChatResponse };
                } else if (currentEvent === "error") {
                  console.warn("[❌ SSE] Error event received:", parsed);
                  yield { type: "error", data: parsed };
                } else if (currentEvent === "artifact_created") {
                  console.warn("[🎨 ARTIFACT_CREATED] Event received:", parsed);
                  yield { type: "artifact_created", data: parsed };
                }

                // Reset current event after processing
                currentEvent = "";
              } catch (parseError) {
                console.error(
                  "[🔍 SSE DEBUG] Failed to parse SSE data:",
                  parseError,
                  "data:",
                  dataStr.substring(0, 100),
                );
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (networkError: any) {
      // 🚨 CRITICAL NETWORK ERROR: Capture fetch failures (connection refused, timeout, etc.)
      // This catches errors that happen BEFORE response.ok can be checked
      console.error("🚨 CRITICAL NETWORK ERROR:", {
        message: networkError?.message || "Unknown network error",
        name: networkError?.name,
        cause: networkError?.cause,
        stack: networkError?.stack,
        url: url,
        payload: payload,
      });

      // Re-throw with more context
      throw new Error(
        `Network error during chat request: ${networkError?.message || "Connection failed"}. ` +
          `Check if backend is running at ${url}`,
      );
    }
  }

  // Artifact endpoints
  async getArtifact(artifactId: string): Promise<ArtifactRecord> {
    const response = await this.client.get<ArtifactRecord>(
      `/api/artifacts/${artifactId}`,
    );
    return response.data;
  }

  async updateArtifact(
    artifactId: string,
    payload: { title?: string; content: string | Record<string, any> },
  ): Promise<ArtifactRecord> {
    const response = await this.client.put<ArtifactRecord>(
      `/api/artifacts/${artifactId}`,
      payload,
    );
    return response.data;
  }

  // Document endpoints
  async uploadDocument(
    file: File,
    options: {
      onProgress?: (progress: number) => void;
      conversationId?: string;
    } = {},
  ): Promise<DocumentUploadResponse> {
    const { onProgress, conversationId } = options;
    const formData = new FormData();
    formData.append("files", file);

    const traceId = crypto.randomUUID();
    const fileBuffer = await file.arrayBuffer();
    const digest = await sha256Hex(fileBuffer);
    const idempotencyKey = `${digest}:${conversationId ?? "no-chat"}`;

    const axiosConfig: import("axios").AxiosRequestConfig<FormData> = {
      headers: {
        "Content-Type": "multipart/form-data",
        "X-Trace-Id": traceId,
        "Idempotency-Key": idempotencyKey,
      },
      withCredentials: true,
      timeout: 180000, // 3 minutes for file upload with OCR processing
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total,
          );
          onProgress(percentCompleted);
        }
      },
    };

    try {
      const response = await this.client.post(
        "/api/files/upload",
        formData,
        axiosConfig,
      );

      const payload = response.data as { files: Array<Record<string, any>> };
      const fileEntry = payload.files?.[0];
      if (!fileEntry) {
        throw new Error("Upload response missing file entry");
      }

      return {
        doc_id: fileEntry.file_id,
        document_id: fileEntry.file_id,
        filename: fileEntry.filename || file.name,
        size_bytes: fileEntry.bytes ?? file.size,
        total_pages: fileEntry.pages ?? 0,
        status: (fileEntry.status || "READY").toLowerCase(),
      };
    } catch (error: any) {
      if (!axios.isAxiosError(error) || error.response?.status !== 404) {
        throw error;
      }

      // Fallback to legacy endpoint for compatibility
      const legacyFormData = new FormData();
      legacyFormData.append("file", file);

      const response = await this.client.post<DocumentUploadResponse>(
        "/api/documents/upload",
        legacyFormData,
        axiosConfig,
      );
      return response.data;
    }
  }

  // Copiloto 414 - Document Audit endpoints
  async auditDocument(
    documentId: string,
    options: {
      clientName?: string;
      policyId?: string;
      enableDisclaimer?: boolean;
      enableFormat?: boolean;
      enableGrammar?: boolean;
      enableLogo?: boolean;
    } = {},
  ): Promise<import("@/types/validation").ValidationReportResponse> {
    const {
      clientName,
      policyId = "auto",
      enableDisclaimer = true,
      enableFormat = true,
      enableGrammar = true,
      enableLogo = true,
    } = options;

    const params = new URLSearchParams({
      doc_id: documentId,
      policy_id: policyId, // NEW: Use policy_id instead of client_name
      ...(clientName && { client_name: clientName }), // DEPRECATED: backward compat
      enable_disclaimer: String(enableDisclaimer),
      enable_format: String(enableFormat),
      enable_grammar: String(enableGrammar),
      enable_logo: String(enableLogo),
    });

    try {
      const response = await this.client.post(
        `/api/review/validate?${params.toString()}`,
        {},
        {
          withCredentials: true,
        },
      );

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const errorMessage = error.response?.data?.detail || error.message;
        throw new Error(`Audit failed: ${errorMessage}`);
      }
      throw error;
    }
  }

  /**
   * Invoke audit_file tool in chat (P2.BE.3)
   *
   * Audits a document and posts the result as an assistant message in the chat.
   *
   * @param documentId - Document ID to audit
   * @param chatId - Chat session ID where result will be posted
   * @param policyId - Policy to apply (default: "auto")
   * @returns ChatMessageRecord with the created audit message
   */
  async auditFileInChat(
    documentId: string,
    chatId: string,
    policyId: string = "auto",
  ): Promise<ChatMessageRecord> {
    try {
      const params = new URLSearchParams({
        doc_id: documentId,
        chat_id: chatId,
        policy_id: policyId,
      });

      const response = await this.client.post(
        `/api/chat/tools/audit-file?${params.toString()}`,
        {},
        {
          withCredentials: true,
          timeout: 180000,
        },
      );

      return response.data as ChatMessageRecord;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const errorMessage = error.response?.data?.detail || error.message;
        throw new Error(`Audit tool failed: ${errorMessage}`);
      }
      throw error;
    }
  }

  /**
   * List documents for the current user
   *
   * Optionally filter by conversation ID to get documents for a specific chat.
   *
   * @param conversationId - Optional chat/conversation ID to filter by
   * @returns Array of document metadata
   */
  async listDocuments(
    conversationId?: string,
    limit: number = 50,
    offset: number = 0,
  ): Promise<Array<import("@/types/files").FileAttachment>> {
    try {
      // ISSUE-012: Add pagination parameters
      const params = new URLSearchParams();
      if (conversationId) {
        params.set("conversation_id", conversationId);
      }
      params.set("limit", limit.toString());
      params.set("offset", offset.toString());

      const url = `/api/documents?${params.toString()}`;

      const response = await this.client.get(url, {
        withCredentials: true,
      });

      // Convert backend DocumentMetadata to frontend FileAttachment format
      const documents = response.data.map((doc: any) => ({
        file_id: doc.doc_id,
        filename: doc.filename,
        status: doc.status === "ready" ? "READY" : doc.status.toUpperCase(),
        bytes: doc.size_bytes,
        pages: doc.total_pages,
        mimetype: doc.content_type,
      }));

      return documents;
    } catch (error: any) {
      // 🔧 GRACEFUL FALLBACK: Handle 404 for "Chat Fantasma" (UUID not yet persisted)
      // When refreshing a new chat URL, the backend may not have the chat yet
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        console.warn(
          `[ApiClient] Chat not found on server (404), returning empty documents list.`,
          { conversationId },
        );
        return []; // ✅ Safe fallback - chat exists locally but not on server yet
      }

      // For other errors, throw as usual
      console.error("API Error Details:", error);
      throw new Error(
        `Failed to list documents: ${error.response?.data?.detail || error.message}`,
      );
    }
  }

  /**
   * Get validation report for a document (Copiloto 414)
   *
   * Fetches the most recent validation report if the document has been audited.
   *
   * @param documentId - Document ID
   * @returns ValidationReportResponse with findings and summary
   * @throws Error if document not found or no validation report exists (404)
   */
  async getDocumentValidation(
    documentId: string,
  ): Promise<import("@/types/validation").ValidationReportResponse> {
    try {
      const response = await this.client.get(
        `/api/documents/${documentId}/validation`,
        {
          withCredentials: true,
        },
      );

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const errorMessage = error.response?.data?.detail || error.message;
        throw new Error(`Failed to fetch validation report: ${errorMessage}`);
      }
      throw error;
    }
  }

  // Document review endpoints
  // MVP-LOCK: Kill-switch for Review flow
  async startDocumentReview(
    request: ReviewStartRequest,
  ): Promise<ReviewStartResponse> {
    console.error(
      "[MVP-LOCK] startDocumentReview fue invocado pero está deshabilitado en el MVP.",
      { request },
    );
    throw new Error(
      "Review flow is disabled for MVP. Use chat with file_ids instead.",
    );

    // Legacy code (now disabled):
    // const response = await this.client.post<ReviewStartResponse>(
    //   "/api/review/start",
    //   request,
    // );
    // return response.data;
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
    try {
      const response = await this.client.get(`/api/history/${chatId}`, {
        params: { limit, offset },
      });
      return response.data;
    } catch (error: any) {
      // 🔧 GRACEFUL FALLBACK: Handle 404 for "Chat Fantasma"
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        console.warn(
          `[ApiClient] Chat not found on server (404), returning empty history.`,
          { chatId },
        );
        return {
          chat_id: chatId,
          messages: [],
          total: 0,
        };
      }
      throw error;
    }
  }

  // Unified history endpoints
  async getUnifiedChatHistory(
    chatId: string,
    limit = 50,
    offset = 0,
    includeResearch = true,
    includeSources = false,
  ): Promise<any> {
    try {
      const response = await this.client.get(`/api/history/${chatId}/unified`, {
        params: {
          limit,
          offset,
          include_research: includeResearch,
          include_sources: includeSources,
        },
      });
      return response.data;
    } catch (error: any) {
      // 🔧 GRACEFUL FALLBACK: Handle 404 for "Chat Fantasma" (UUID not yet persisted)
      // When refreshing a new chat URL, the backend may not have the chat yet
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        console.warn(
          `[ApiClient] Chat not found on server (404), returning empty history.`,
          { chatId },
        );
        // Return empty history structure matching backend response format
        return {
          chat_id: chatId,
          events: [],
          total: 0,
          limit,
          offset,
        };
      }

      // For other errors, throw as usual
      throw error;
    }
  }

  async getChatStatus(chatId: string): Promise<any> {
    try {
      const response = await this.client.get(`/api/history/${chatId}/status`);
      return response.data;
    } catch (error: any) {
      // 🛡️ GRACEFUL FALLBACK: Handle 404 (Not Found) AND 500 (Server Error on lookup)
      // When refreshing a new chat URL, the backend may crash (500) or return 404
      // if the chat isn't initialized yet. Assume it's a draft to avoid blocking the UI.
      if (
        axios.isAxiosError(error) &&
        (error.response?.status === 404 || error.response?.status === 500)
      ) {
        const statusCode = error.response?.status;
        console.warn(
          `[ApiClient] Chat status check failed (${statusCode}), assuming new draft.`,
          { chatId, statusCode },
        );
        // Return default status for non-existent or uninitialized chat
        return {
          chat_id: chatId,
          state: "draft", // New chats start as draft
          message_count: 0,
        };
      }
      // For other errors (e.g., network issues, auth errors), throw as usual
      throw error;
    }
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

  // Canvas state persistence
  async saveCanvasState(
    sessionId: string,
    canvasState: {
      is_sidebar_open?: boolean;
      active_artifact_id?: string | null;
      active_message_id?: string | null;
      active_bank_chart?: any | null;
    },
  ): Promise<void> {
    await this.client.patch(`/api/sessions/${sessionId}/canvas`, canvasState);
  }

  async getCanvasState(sessionId: string): Promise<any> {
    const response = await this.client.get(`/api/sessions/${sessionId}/canvas`);
    return response.data?.data;
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
