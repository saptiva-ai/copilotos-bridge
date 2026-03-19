"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import toast from "react-hot-toast";

import { cn } from "@/lib/utils";
import { ChatMessage, ChatSession } from "../../../lib/types";
import {
  ChatInterface,
  ChatWelcomeMessage,
  ChatShell,
  ConversationList,
} from "../../../components/chat";
import { ErrorBoundary } from "../../../components/ErrorBoundary";
import {
  DeepResearchWizard,
  type DeepResearchScope,
} from "../../../components/chat/DeepResearchWizard";
import { DeepResearchProgress } from "../../../components/chat/DeepResearchProgress";
import { IntentNudge } from "../../../components/chat/IntentNudge";
import { AuditProgress } from "../../../components/chat/AuditProgress";
import type { ChatComposerAttachment } from "../../../components/chat/ChatComposer";
import { useChat, useUI, useChatStore } from "../../../lib/store";
import { apiClient, type ChatResponse } from "../../../lib/api-client";
import { getAllModels } from "../../../config/modelCatalog";
import { useRequireAuth } from "../../../hooks/useRequireAuth";
import { useOptimizedChat } from "../../../hooks/useOptimizedChat";
import { useDeepResearch } from "../../../hooks/useDeepResearch";
import type { ToolId } from "../../../types/tools";
import WelcomeBanner from "../../../components/chat/WelcomeBanner";
import { useAuthStore } from "../../../lib/auth-store";
import { logDebug, logError, logWarn } from "../../../lib/logger";
import { researchGate } from "../../../lib/research-gate";
import { logEffect, logAction, logState } from "../../../lib/ux-logger";
import {
  normalizeToolsState,
  legacyKeyToToolId,
  toolIdToLegacyKey,
} from "@/lib/tool-mapping";
import { featureFlags as envFeatureFlags } from "@/lib/feature-flags";
import { CanvasPanel } from "@/components/canvas/canvas-panel";
import { useCanvas } from "@/context/CanvasContext";
import { useCanvasStore } from "@/lib/stores/canvas-store";
// Files V1 imports
import { useFiles } from "../../../hooks/useFiles";
import { useFilesStore } from "../../../lib/stores/files-store";
import type { FileAttachment } from "../../../types/files";
// React Query hooks
import { useChatMessages } from "../../../hooks/useChatMessages";
import { useChatMetadata } from "../../../hooks/useChatMetadata";
import {
  getEffectiveCanvasChatId,
  isTempToRealChatReconciliation,
  shouldResetCanvasForChatTransition,
  shouldResetCanvasForNoActiveChat,
} from "./chat-view-canvas-utils";
// Demo banner intentionally hidden per stakeholder request

interface ChatViewProps {
  initialChatId?: string | null;
}

export function ChatView({ initialChatId = null }: ChatViewProps) {
  const { isAuthenticated, isHydrated } = useRequireAuth();
  const user = useAuthStore((state) => state.user);
  const searchParams = useSearchParams();
  const queryChatId = searchParams?.get("session") ?? null;

  const resolvedChatId = React.useMemo(() => {
    if (initialChatId && initialChatId !== "new") return initialChatId;
    if (queryChatId && queryChatId !== "new") return queryChatId;
    return null;
  }, [initialChatId, queryChatId]);

  // CRITICAL: Use direct selector for messages to ensure re-renders on content changes
  // This fixes streaming text not appearing word-by-word
  const messages = useChatStore((state) => state.messages);

  const {
    currentChatId,
    selectionEpoch,
    isLoading,
    models,
    modelsLoading,
    featureFlags,
    featureFlagsLoading,
    selectedModel,
    toolsEnabled,
    startNewChat,
    setSelectedModel,
    clearMessages,
    setLoading,
    toggleTool,
    setToolEnabled,
    chatSessions,
    chatSessionsLoading,
    chatNotFound,
    loadChatSessions,
    loadModels,
    loadFeatureFlags,
    setCurrentChatId,
    switchChat,
    loadUnifiedHistory,
    renameChatSession,
    pinChatSession,
    deleteChatSession,
    updateSessionTitle,
    // P0-UX-HIST-001: Optimistic UI states
    isCreatingConversation,
    pendingCreationId,
    createConversationOptimistic,
    reconcileConversation,
    removeOptimisticConversation,
    // Progressive Commitment: Draft state
    draft,
    draftToolsEnabled,
    openDraft,
    discardDraft,
    isDraftMode,
    // Hydration state (SWR pattern)
    hydratedByChatId,
    isHydratingByChatId,
  } = useChat();

  // Prefer route conversation when available; otherwise fallback to store state.
  // This prevents transient `/chat` route states from being treated as "no conversation".
  const effectiveChatId = React.useMemo(
    () => getEffectiveCanvasChatId(resolvedChatId, currentChatId),
    [resolvedChatId, currentChatId],
  );

  // React Query: Load messages with automatic caching and deduplication
  const { isLoading: isLoadingMessages } = useChatMessages(resolvedChatId);

  // Centralized metadata for file restoration policies
  const { hasMessages, isReady } = useChatMetadata(resolvedChatId);

  const { checkConnection } = useUI();
  const {
    sendOptimizedMessage,
    cancelCurrentRequest,
    updateStreamingContent,
    completeStreaming,
    submitFeedback,
  } = useOptimizedChat({
    chatId: resolvedChatId,
    enablePredictiveLoading: true,
    enableResponseCache: true,
    streamingChunkSize: 3,
  });
  const isCanvasOpen = useCanvasStore((state) => state.isSidebarOpen);
  const toggleCanvas = useCanvasStore((state) => state.toggleSidebar);
  const resetCanvas = useCanvasStore((state) => state.reset);
  const setCurrentSessionId = useCanvasStore(
    (state) => state.setCurrentSessionId,
  );
  const loadFromMongoDB = useCanvasStore((state) => state.loadFromMongoDB);
  const openResearchReport = useCanvasStore(
    (state) => state.openResearchReport,
  );
  const { closeCanvas } = useCanvas();

  // DEBUG: Log canvas state in ChatView
  React.useEffect(() => {
    logDebug("🏠 [ChatView] isCanvasOpen changed", { isCanvasOpen });
  }, [isCanvasOpen]);

  // Track previous chatId to detect conversation changes
  const prevChatIdRef = React.useRef<string | null>(null);

  // Reset and close canvas when switching conversations
  React.useEffect(() => {
    const previousChatId = prevChatIdRef.current;
    const nextChatId = effectiveChatId;
    const hasChanged = previousChatId !== nextChatId;
    const isTempToRealReconciliation = isTempToRealChatReconciliation(
      previousChatId,
      nextChatId,
    );
    const wasOpen = useCanvasStore.getState().isSidebarOpen;

    if (shouldResetCanvasForChatTransition(previousChatId, nextChatId)) {
      // Conversation changed - FORCE close canvas immediately
      // Close using all available methods to ensure it closes
      if (wasOpen) {
        closeCanvas(); // Close via context
      }
      resetCanvas(); // Reset store state
      logDebug(
        "🎨 [ChatView] Canvas forced closed due to conversation change",
        {
          from: previousChatId,
          to: nextChatId,
          wasOpen,
        },
      );
    } else if (hasChanged && isTempToRealReconciliation) {
      // Preserve canvas while optimistic conversation ID is reconciled with real ID.
      logDebug(
        "🎨 [ChatView] Preserving canvas during temp→real reconciliation",
        {
          from: previousChatId,
          to: nextChatId,
          wasOpen,
        },
      );
    }

    prevChatIdRef.current = nextChatId;

    if (nextChatId) {
      // Set session ID for future syncs
      setCurrentSessionId(nextChatId);
      logDebug("🎨 [ChatView] Canvas session ID set", {
        chatId: nextChatId,
      });
    } else if (shouldResetCanvasForNoActiveChat(previousChatId, nextChatId)) {
      // Transitioned to no active chat, reset canvas state.
      if (wasOpen) {
        closeCanvas(); // Close via context
      }
      resetCanvas();
      setCurrentSessionId(null);
    }
  }, [
    effectiveChatId,
    resetCanvas,
    setCurrentSessionId,
    closeCanvas,
  ]);

  // Files V1 state - MVP-LOCK: Use effective chat ID to avoid route/store transient races.
  const {
    attachments: filesV1Attachments,
    addAttachment: addFilesV1Attachment,
    removeAttachment: removeFilesV1Attachment,
    clearAttachments: clearFilesV1Attachments,
    lastReadyFile: lastReadyAuditFile,
  } = useFiles(effectiveChatId || undefined, messages.length > 0);

  // BUG-FIX: Selectors for aggressive attachment cleanup
  // Used after successful message send to clear all orphaned attachments
  const clearAllTempAttachments = useFilesStore(
    (state) => state.clearAllTempAttachments,
  );
  const clearForChat = useFilesStore((state) => state.clearForChat);

  const [nudgeMessage, setNudgeMessage] = React.useState<string | null>(null);
  const [pendingWizard, setPendingWizard] = React.useState<{
    query: string;
    attachments?: ChatComposerAttachment[];
  } | null>(null);
  const [activeResearch, setActiveResearch] = React.useState<{
    taskId: string;
    streamUrl?: string | null;
    query: string;
  } | null>(null);
  const [isStartingResearch, setIsStartingResearch] = React.useState(false);
  const [researchError, setResearchError] = React.useState<string | null>(null);
  const [isSending, setIsSending] = React.useState(false); // ISSUE-009: Rate limiting

  // Audit progress state (Copiloto 414)
  const [activeAudit, setActiveAudit] = React.useState<{
    fileId: string;
    filename: string;
  } | null>(null);

  // 🔍 DEBUG: Log on every render to verify code is loaded
  logDebug("🔍 [ChatView] RENDER - Code version check", {
    messagesLen: messages.length,
    filesV1AttachmentsLen: filesV1Attachments.length,
    activeAudit,
    currentChatId,
  });

  // State for current audit report PDF URL
  const [currentReportPdfUrl, setCurrentReportPdfUrl] = React.useState<
    string | null
  >(null);

  const selectedTools = React.useMemo<ToolId[]>(() => {
    return Object.entries(toolsEnabled)
      .filter(([, enabled]) => enabled)
      .map(([key]) => legacyKeyToToolId(key))
      .filter((id): id is ToolId => Boolean(id));
  }, [toolsEnabled]);

  const deepResearchEnabled = React.useMemo(() => {
    if (featureFlags?.deep_research_kill_switch) {
      return false;
    }
    // Allow env flag to force-enable even if toggle persisted as off
    return (
      selectedTools.includes("deep-research") || envFeatureFlags.deepResearch
    );
  }, [selectedTools, featureFlags]);

  // Ensure research/search tools are enabled when feature flags allow it
  React.useEffect(() => {
    if (envFeatureFlags.webSearch && !toolsEnabled.web_search) {
      void setToolEnabled("web_search", true);
    }
    if (
      envFeatureFlags.deepResearch &&
      !featureFlags?.deep_research_kill_switch &&
      !toolsEnabled.deep_research
    ) {
      void setToolEnabled("deep_research", true);
    }
  }, [toolsEnabled, setToolEnabled, featureFlags]);

  const handleAddTool = React.useCallback(
    (id: ToolId) => {
      const legacyKey = toolIdToLegacyKey(id);
      if (!legacyKey) return;
      void setToolEnabled(legacyKey, true);
    },
    [setToolEnabled],
  );

  const handleRemoveTool = React.useCallback(
    (id: ToolId) => {
      const legacyKey = toolIdToLegacyKey(id);
      if (!legacyKey) return;
      void setToolEnabled(legacyKey, false);
    },
    [setToolEnabled],
  );

  const researchState = useDeepResearch(activeResearch?.streamUrl ?? undefined);
  const {
    phase: researchPhase,
    progress: researchProgress,
    sources: researchSources,
    evidences: researchEvidences,
    report: researchReport,
    error: researchHookError,
    isStreaming: researchIsStreaming,
    stop: stopResearchStream,
    reset: resetResearchState,
  } = researchState;

  // 🆕 Auto-open Canvas with research report when completed
  React.useEffect(() => {
    if (
      researchPhase === "COMPLETED" &&
      researchReport &&
      activeResearch?.taskId
    ) {
      openResearchReport({
        taskId: activeResearch.taskId,
        query: activeResearch.query,
        report: researchReport,
        sources: researchSources,
        evidences: researchEvidences,
        completedAt: new Date().toISOString(),
      });

      logDebug("[ChatView] Deep Research completed, opening Canvas", {
        taskId: activeResearch.taskId,
        sourcesCount: researchSources.length,
        evidencesCount: researchEvidences.length,
      });
    }
  }, [
    researchPhase,
    researchReport,
    activeResearch,
    researchSources,
    researchEvidences,
    openResearchReport,
  ]);

  const startDeepResearchFlow = React.useCallback(
    async (
      text: string,
      scope?: Partial<DeepResearchScope>,
      _attachments?: ChatComposerAttachment[],
    ) => {
      if (researchIsStreaming) {
        setNudgeMessage(
          "Ya hay una investigación en curso. Cancela o espera a que finalice antes de iniciar otra.",
        );
        return;
      }

      resetResearchState();
      setPendingWizard(null);
      setResearchError(null);
      setNudgeMessage(null);
      setActiveResearch(null);
      setIsStartingResearch(true);

      try {
        await sendOptimizedMessage(
          text,
          async (
            msg: string,
            placeholderId: string,
            abortController?: AbortController,
          ) => {
            try {
              const request = {
                query: msg,
                chat_id: currentChatId || undefined,
                research_type: "deep_research" as const,
                stream: true,
                params: {
                  depth_level: scope?.depth ?? "medium",
                  scope: scope?.objective ?? msg,
                },
                context: {
                  time_window: scope?.timeWindow,
                  origin: "chat",
                },
              };

              const response = await apiClient.startDeepResearch(request);

              if (!currentChatId && (response as any)?.chat_id) {
                setCurrentChatId((response as any).chat_id);
              }

              setActiveResearch({
                taskId: response.task_id,
                streamUrl: response.stream_url,
                query: msg,
              });

              return {
                id: placeholderId,
                role: "assistant" as const,
                content:
                  "Iniciando investigación profunda. Te compartiré avances conforme encontremos evidencia relevante.",
                timestamp: new Date().toISOString(),
                status: "delivered" as const,
              };
            } catch (error) {
              setResearchError(
                "No se pudo iniciar la investigación. Intenta nuevamente o ajusta el alcance.",
              );
              setNudgeMessage(
                "No se pudo iniciar la investigación. Intenta nuevamente o ajusta el alcance.",
              );
              setActiveResearch(null);
              return {
                id: placeholderId,
                role: "assistant" as const,
                content:
                  "Lo siento, no se pudo iniciar la investigación en este momento.",
                timestamp: new Date().toISOString(),
                status: "error" as const,
              };
            } finally {
              setIsStartingResearch(false);
            }
          },
        );
      } finally {
        setIsStartingResearch(false);
      }
    },
    [
      researchIsStreaming,
      resetResearchState,
      sendOptimizedMessage,
      currentChatId,
      setPendingWizard,
      setResearchError,
      setNudgeMessage,
      setActiveResearch,
      setIsStartingResearch,
      setCurrentChatId,
    ],
  );

  React.useEffect(() => {
    checkConnection();
  }, [checkConnection]);

  // Message-first: Cleanup draft on navigation or beforeunload
  React.useEffect(() => {
    const handleBeforeUnload = () => {
      if (isDraftMode() && messages.length === 0) {
        discardDraft();
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDraftMode, messages.length, discardDraft]);

  // Message-first: Cleanup draft when navigating away from /chat or /chat/new
  React.useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (isDraftMode() && messages.length === 0) {
        discardDraft();
      }
    };
  }, [isDraftMode, messages.length, discardDraft]);

  React.useEffect(() => {
    if (isAuthenticated && isHydrated) {
      loadChatSessions();
      loadModels();
      loadFeatureFlags();
    }
  }, [
    isAuthenticated,
    isHydrated,
    loadChatSessions,
    loadModels,
    loadFeatureFlags,
  ]);

  // CHAT_ROUTE_EFFECT: Blindado con deps mínimas para SWR
  /* eslint-disable react-hooks/exhaustive-deps */
  React.useEffect(() => {
    logEffect("CHAT_ROUTE_EFFECT", {
      resolvedChatId,
      isHydrated,
      hydrated: resolvedChatId ? hydratedByChatId[resolvedChatId] : undefined,
      hydrating: resolvedChatId
        ? isHydratingByChatId[resolvedChatId]
        : undefined,
    });

    // Guard: Only run when app is ready
    if (!isHydrated) return;

    if (resolvedChatId) {
      // ANTI-FLASH GUARD: Skip navigation for temp IDs during creation
      // When creating a conversation, handleStartNewChat already sets currentChatId(tempId)
      // and we don't want to trigger switchChat/load until backend reconciles
      const isTempId = resolvedChatId.startsWith("temp-");
      const isCurrentlyCreating =
        isCreatingConversation && pendingCreationId === resolvedChatId;

      if (isTempId && isCurrentlyCreating) {
        logAction("SKIP_SWITCH_DURING_CREATE", {
          tempId: resolvedChatId,
          reason: "optimistic_creation_in_progress",
        });
        return;
      }

      // If switching away from a temp conversation, cancel its creation
      if (
        currentChatId?.startsWith("temp-") &&
        currentChatId !== resolvedChatId
      ) {
        logAction("CANCEL_OPTIMISTIC_CHAT", {
          tempId: currentChatId,
          switchingTo: resolvedChatId,
        });
        removeOptimisticConversation(currentChatId);
      }

      // Use switchChat to handle re-selection with epoch bumping
      // No guard needed - switchChat handles A→A pattern by bumping epoch
      logAction("SWITCH_CHAT", { from: currentChatId, to: resolvedChatId });
      switchChat(resolvedChatId);

      // CRITICAL: Always call loadUnifiedHistory after switchChat
      // switchChat invalidates cache by clearing hydratedByChatId and isHydratingByChatId
      // We can't check those flags here because Zustand updates are async - we'd read stale values
      // loadUnifiedHistory has its own deduplication logic to prevent duplicate loads
      logAction("LOAD_CHAT", { chatId: resolvedChatId });
      loadUnifiedHistory(resolvedChatId);
    } else if (currentChatId === null && !isDraftMode()) {
      // Only open draft if we have NO current chat AND we're not already in draft mode
      logAction("ROUTE_TO_NEW_CHAT_INIT", { prevChatId: currentChatId });
      setCurrentChatId(null);
      startNewChat();
    }
  }, [resolvedChatId, isHydrated]); // MINIMAL DEPS: Only route param and app hydration
  /* eslint-enable react-hooks/exhaustive-deps */

  // Track which chats have already loaded documents (prevent duplicate loads)
  const loadedChatsRef = React.useRef<Set<string>>(new Set());

  // ISSUE-010: Track active streaming AbortController for cleanup
  const streamAbortControllerRef = React.useRef<AbortController | null>(null);

  // ISSUE-010: Cleanup streaming on unmount to prevent orphaned SSE connections
  React.useEffect(() => {
    return () => {
      if (streamAbortControllerRef.current) {
        streamAbortControllerRef.current.abort();
        streamAbortControllerRef.current = null;
        logDebug("[ChatView] Aborted streaming on unmount");
      }
    };
  }, []);

  // Load documents from backend when chat changes (fixes file persistence after refresh)
  React.useEffect(() => {
    const loadChatDocuments = async () => {
      if (!resolvedChatId || resolvedChatId.startsWith("temp-")) return;

      // Skip if already loaded for this chat
      if (loadedChatsRef.current.has(resolvedChatId)) {
        logDebug(
          "[ChatView] Documents already loaded for this chat, skipping",
          {
            chatId: resolvedChatId,
          },
        );
        return;
      }

      try {
        // 🛡️ FIREWALL DE HISTORIAL: NO cargar documentos para chats existentes CON mensajes
        // Los documentos históricos deben verse en los mensajes, NO en el input
        const isExistingChat =
          resolvedChatId &&
          !resolvedChatId.startsWith("temp-") &&
          !resolvedChatId.startsWith("creating") &&
          resolvedChatId !== "draft" &&
          messages.length > 0; // ← CLAVE: solo bloquear si tiene mensajes

        if (isExistingChat) {
          logDebug(
            "[ChatView] 🛡️ FIREWALL: Skipping document restoration for existing chat with messages",
            {
              chatId: resolvedChatId,
              messagesLen: messages.length,
              reason:
                "Historical documents should not be loaded into input composer",
              hint: "Documents are visible in message history, not in the input area",
            },
          );

          // Mark as loaded to prevent re-loading
          loadedChatsRef.current.add(resolvedChatId);
          return;
        }

        logDebug(
          "[ChatView] Loading documents from backend (draft/temp chat)",
          {
            chatId: resolvedChatId,
          },
        );

        const documents = await apiClient.listDocuments(resolvedChatId);

        // Re-populate filesStore with documents from backend
        // This ensures files persist after page refresh for DRAFT chats
        // Get fresh state from store to avoid stale closure issues
        const currentAttachments = filesV1Attachments;

        logDebug("[ChatView] Current attachments in store", {
          count: currentAttachments.length,
          fileIds: currentAttachments.map((f) => f.file_id),
        });

        logDebug("[ChatView] Documents from backend", {
          count: documents.length,
          fileIds: documents.map((d) => d.file_id),
        });

        documents.forEach((doc) => {
          // Only add if not already in store (avoid duplicates)
          const existing = currentAttachments.find(
            (f) => f.file_id === doc.file_id,
          );
          if (!existing) {
            logDebug("[ChatView] Adding document from backend", {
              file_id: doc.file_id,
              filename: doc.filename,
            });
            addFilesV1Attachment(doc);
          } else {
            logDebug("[ChatView] Skipping duplicate document", {
              file_id: doc.file_id,
              filename: doc.filename,
            });
          }
        });

        // Mark this chat as loaded
        loadedChatsRef.current.add(resolvedChatId);

        logDebug("[ChatView] Documents loaded from backend", {
          chatId: resolvedChatId,
          count: documents.length,
        });
      } catch (error) {
        // Non-blocking error - chat can still function without file list
        logError("[ChatView] Failed to load documents from backend", error);
      }
    };

    loadChatDocuments();
    // CRITICAL: Don't include filesV1Attachments in deps - causes infinite loop!
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolvedChatId]);

  const sendStandardMessage = React.useCallback(
    async (message: string, attachments?: ChatComposerAttachment[]) => {
      // MVP-LOCK: Prepare metadata with file_ids for user message bubble
      let userMessageMetadata: Record<string, any> | undefined;

      // Files V1: Collect file metadata for visual indicator
      // BUG FIX: Always collect file metadata when files are present,
      // regardless of toggle state. The toggle only controls backend processing.
      let fileIds: string[] | undefined;
      let readyFiles: typeof filesV1Attachments = [];
      if (filesV1Attachments.length > 0) {
        readyFiles = filesV1Attachments.filter((a) => a.status === "READY");

        if (readyFiles.length > 0) {
          fileIds = readyFiles.map((a) => a.file_id);

          // MVP-LOCK: Store full file information in metadata (not just IDs)
          // This allows the UI to display filenames without additional lookups
          userMessageMetadata = {
            file_ids: fileIds,
            files: readyFiles.map((f) => ({
              file_id: f.file_id,
              filename: f.filename,
              bytes: f.bytes,
              pages: f.pages,
              mimetype: f.mimetype,
            })),
          };

          logDebug("[ChatView] File metadata prepared", {
            fileIds,
            fileCount: readyFiles.length,
          });
        }
      }

      // MINIMALISMO FUNCIONAL: Archivos siempre se usan cuando están listos
      const fileIdsForBackend = fileIds;

      // 🔧 FIX: Auto-enable document_analysis when files are attached
      // If file_ids are present in payload, the LLM MUST have permission to read them
      const hasFiles = fileIdsForBackend && fileIdsForBackend.length > 0;

      // Always expose create_artifact to the LLM even if not toggled explicitly
      // Auto-enable document_analysis when files are attached (prevents "📄 Documentos no encontrados")
      const toolsForPayload = {
        ...toolsEnabled,
        create_artifact: true,
        document_analysis: hasFiles || toolsEnabled.document_analysis || false,
      };

      await sendOptimizedMessage(
        message,
        async (
          msg: string,
          placeholderId: string,
          abortController?: AbortController,
        ) => {
          try {
            // Upload attachments first if provided (legacy system)
            let documentIds: string[] = [];
            if (attachments && attachments.length > 0) {
              const uploadPromises = attachments
                .filter((att) => att.status !== "error")
                .map(async (attachment) => {
                  try {
                    const response = await apiClient.uploadDocument(
                      attachment.file,
                      {
                        conversationId: currentChatId || undefined,
                      },
                    );
                    return response.document_id;
                  } catch (error) {
                    logError("Failed to upload document", {
                      name: attachment.name,
                      error,
                    });
                    return null;
                  }
                });

              const results = await Promise.all(uploadPromises);
              documentIds = results.filter((id): id is string => id !== null);

              logDebug("[ChatView] Uploaded documents", { documentIds });
            }

            // Resolve UI slug to backend ID
            const selectedModelData = models.find(
              (m) => m.id === selectedModel,
            );
            let backendModelId = selectedModelData?.backendId;

            // Fallback: if backendId is null/undefined or equals the slug (not resolved),
            // use display name from catalog
            if (!backendModelId || backendModelId === selectedModel) {
              const catalogModel = getAllModels().find(
                (m) => m.slug === selectedModel,
              );
              backendModelId = catalogModel?.displayName || selectedModel;
              logWarn("[ChatView] Using catalog fallback for model", {
                selectedModelSlug: selectedModel,
                catalogModel: catalogModel?.displayName,
                fallbackValue: backendModelId,
              });
            }

            // Don't send temp IDs to backend - they don't exist there yet
            const wasTempId = currentChatId?.startsWith("temp-");

            // CRITICAL FIX: Don't treat valid chat IDs as "phantom" just because messages haven't loaded yet
            // Previous logic: isPhantomChat = currentChatId && messages.length === 0 && !wasTempId
            // Problem: This caused follow-up messages to create new conversations because messages
            // hadn't loaded yet from the backend (race condition)
            //
            // New logic: If we have a valid (non-temp) chat_id, ALWAYS use it
            // The backend will handle whether the chat exists or needs to be created
            //
            // Send chat_id to backend only if it's NOT a temp ID
            // CRITICAL: Use `null` instead of `undefined`
            // - `null` serializes as "chat_id": null (backend knows to create new chat)
            // - `undefined` removes the key entirely (causes backend validation errors)
            const chatIdForBackend = wasTempId ? null : currentChatId || null;

            // OBS-1: Log payload before sending to backend
            logDebug("[ChatView] payload_outbound", {
              text_len: msg.length,
              file_ids: fileIdsForBackend || [],
              nonce: placeholderId.slice(-8),
              metadata_present: !!userMessageMetadata,
            });

            // Enable streaming to properly render audit progress and responses
            // (Previously disabled due to JSON blobs, now fixed in streaming handler)
            const enableStreaming = documentIds.length === 0;

            let response: ChatResponse | undefined;

            if (enableStreaming) {
              // Streaming path: consume SSE chunks
              let accumulatedContent = "";
              // console.log("[DEBUG] Entering streaming path");

              try {
                const streamGenerator = apiClient.sendChatMessageStream(
                  {
                    message: msg,
                    chat_id: chatIdForBackend,
                    model: backendModelId,
                    temperature: 0.3,
                    max_tokens: 800,
                    stream: true,
                    tools_enabled: toolsForPayload,
                    document_ids:
                      documentIds.length > 0 ? documentIds : undefined,
                    file_ids:
                      fileIdsForBackend && fileIdsForBackend.length > 0
                        ? fileIdsForBackend
                        : undefined,
                    metadata: userMessageMetadata,
                  },
                  abortController?.signal,
                );

                let metaData: any = null;
                // console.log("[🔍 STREAMING DEBUG] Starting to consume events");

                for await (const event of streamGenerator) {
                  // console.log("[🔍 STREAMING DEBUG] Event received:", event.type, event.data ? "with data" : "no data");

                  if (event.type === "meta") {
                    metaData = event.data;
                    // console.log("[🔍 STREAMING DEBUG] Meta event:", metaData);
                    // Update chat_id if we got a new one
                    if (!currentChatId && event.data.chat_id) {
                      setCurrentChatId(event.data.chat_id);
                    }
                  } else if (event.type === "artifact_created") {
                    // Handle artifact_created event
                    if (!metaData) metaData = {};
                    metaData.artifact_id = event.data.artifact_id;

                    // Update streaming message metadata in real-time
                    updateStreamingContent(placeholderId, accumulatedContent, {
                      ...metaData,
                      artifact_id: event.data.artifact_id,
                    });
                  } else if (event.type === "chunk") {
                    accumulatedContent += event.data.content;
                    // console.log("[🔍 STREAMING DEBUG] Chunk received - content length:", event.data.content?.length, "accumulated:", accumulatedContent.length);
                    // Update streaming content (flushSync is handled in useOptimizedChat hook)
                    updateStreamingContent(placeholderId, accumulatedContent);
                  } else if (event.type === "done") {
                    // console.log("[🔍 STREAMING DEBUG] Done event - has content:", !!event.data.content, "accumulated:", accumulatedContent.length);
                    response = {
                      ...event.data,
                      // Merge accumulated metaData with event metadata
                      metadata: {
                        ...(event.data?.metadata ||
                          (response as any)?.metadata ||
                          {}),
                        ...(metaData || {}),
                      },
                    } as ChatResponse;
                  } else if (event.type === "error") {
                    // Handle both string and object error formats
                    const errorMsg =
                      typeof event.data === "string"
                        ? event.data
                        : event.data?.error ||
                          (event.data && "message" in event.data
                            ? (event.data as any).message
                            : JSON.stringify(event.data));
                    throw new Error(errorMsg);
                  }
                }
                // console.log("[🔍 STREAMING DEBUG] Stream finished - response exists:", !!response, "accumulated:", accumulatedContent.length);

                // If we didn't get a done event, construct response from accumulated data
                if (!response) {
                  // console.log("[🔍 STREAMING DEBUG] No done event - constructing from accumulated");
                  response = {
                    chat_id: metaData?.chat_id || chatIdForBackend || "",
                    message_id: metaData?.user_message_id || placeholderId,
                    content: accumulatedContent,
                    role: "assistant" as const,
                    model: metaData?.model || backendModelId,
                    created_at: new Date().toISOString(),
                    metadata: {
                      ...((response as any)?.metadata || {}),
                      ...(metaData || {}),
                    },
                  };
                }

                // Override content with accumulated content (in case done event has incomplete data)
                if (accumulatedContent && response) {
                  // console.log("[🔍 STREAMING DEBUG] Overriding response.content with accumulated (length:", accumulatedContent.length, ")");
                  response.content = accumulatedContent;
                } else {
                  // console.log("[🔍 STREAMING DEBUG] Not overriding - accumulated empty or no response");
                }
              } catch (streamError) {
                // Backend may use non-streaming for RAG automatically
                // Only log as warning if it's a real error, not a strategy change
                const isAttributeError =
                  streamError instanceof Error &&
                  streamError.message?.includes("AttributeError");

                const isPdfMaterializationError =
                  streamError instanceof Error &&
                  streamError.message?.includes("pdf_materialization_failed");

                const isStorageUnavailable =
                  streamError instanceof Error &&
                  streamError.message?.includes("storage_unavailable");

                // Don't log expected strategy changes or known issues
                if (
                  !isAttributeError &&
                  !isPdfMaterializationError &&
                  !isStorageUnavailable
                ) {
                  console.warn(
                    "Stream processing encountered issue, using fallback:",
                    streamError,
                  );
                }

                // Fallback to non-streaming if streaming fails
                response = await apiClient.sendChatMessage({
                  message: msg,
                  chat_id: chatIdForBackend,
                  model: backendModelId,
                  temperature: 0.3,
                  max_tokens: 800,
                  stream: false,
                  tools_enabled: toolsForPayload,
                  document_ids:
                    documentIds.length > 0 ? documentIds : undefined,
                  file_ids:
                    fileIdsForBackend && fileIdsForBackend.length > 0
                      ? fileIdsForBackend
                      : undefined,
                  metadata: userMessageMetadata,
                });
              }
            } else {
              // Non-streaming path (fallback)
              response = await apiClient.sendChatMessage({
                message: msg,
                chat_id: chatIdForBackend,
                model: backendModelId,
                temperature: 0.3,
                max_tokens: 800,
                stream: false,
                tools_enabled: toolsForPayload,
                document_ids: documentIds.length > 0 ? documentIds : undefined,
                file_ids:
                  fileIdsForBackend && fileIdsForBackend.length > 0
                    ? fileIdsForBackend
                    : undefined,
                metadata: userMessageMetadata,
              });
            }

            // Ensure response was set (should always be the case after streaming or non-streaming)
            logDebug("[ChatView] 🔍 About to check response", {
              hasResponse: !!response,
              responseKeys: response ? Object.keys(response) : [],
            });

            if (!response) {
              throw new Error("Failed to get response from API");
            }

            logDebug(
              "[ChatView] 🔍 Response exists, proceeding to file cleanup",
            );

            // 🔧 FIX: Clear file attachments IMMEDIATELY after successful response
            // This must happen BEFORE any other processing (auto-title, reconciliation, etc.)
            // to prevent files from persisting if subsequent operations fail
            logDebug(
              "[ChatView] ✅ Response received, clearing files immediately",
              {
                readyFilesLength: readyFiles.length,
                responseChatId: response.chat_id,
                currentChatId,
                wasTempId,
              },
            );

            if (readyFiles.length > 0) {
              // BUG-FIX: NUCLEAR CLEANUP - Clear attachments from ALL possible locations
              // Files can be stored under: resolvedChatId, currentChatId, response.chat_id, "draft", or temp-*
              // We must clear ALL of them to prevent orphaned thumbnails

              // 1. Clear all temp/draft attachments (handles temp-*, creating-*, draft)
              clearAllTempAttachments();

              // 2. Clear for the response chat_id (the real UUID from backend)
              if (response.chat_id) {
                clearForChat(response.chat_id);
              }

              // 3. Clear for resolvedChatId (the ID from URL when file was uploaded)
              // This is CRITICAL: files are stored under this ID, not response.chat_id
              if (resolvedChatId && resolvedChatId !== response.chat_id) {
                clearForChat(resolvedChatId);
              }

              // 4. Clear for currentChatId (in case it differs from resolvedChatId)
              if (
                currentChatId &&
                currentChatId !== response.chat_id &&
                currentChatId !== resolvedChatId
              ) {
                clearForChat(currentChatId);
              }

              logDebug(
                "[ChatView] ✅ Cleared file attachments after successful response (Nuclear Clean)",
                {
                  clearedCount: readyFiles.length,
                  clearedIds: [
                    "temp/*",
                    response.chat_id,
                    resolvedChatId,
                    currentChatId,
                  ].filter(Boolean),
                  method: "clearForChat + clearAllTempAttachments",
                },
              );
            }

            // Parche A: Show warnings from decision_metadata (expired docs, etc.)
            if (response?.decision_metadata?.warnings?.length) {
              toast.error(response.decision_metadata.warnings.join(" • "), {
                duration: 4000,
              });
              logDebug("[ChatView] Backend warnings displayed", {
                warnings: response.decision_metadata.warnings,
              });
            }

            // Auto-title logic: Detect if this is a new conversation
            // A conversation is "new" if:
            // 1. We didn't have a currentChatId before, OR
            // 2. The ID was temporary (optimistic), OR
            // 3. This is the first message (messages.length === 0 before adding response)
            const isFirstMessage = messages.length === 0;
            const wasNewConversation =
              !currentChatId ||
              currentChatId.startsWith("temp-") ||
              isFirstMessage;

            // If we had a temp ID and got a real ID back, reconcile the optimistic conversation
            if (!currentChatId && response.chat_id) {
              setCurrentChatId(response.chat_id);
            } else if (wasTempId && response.chat_id && currentChatId) {
              // Reconcile: temp conversation → real conversation
              logDebug("Reconciling optimistic conversation", {
                tempId: currentChatId,
                realId: response.chat_id,
              });

              const tempIdToReconcile = currentChatId;
              setCurrentChatId(response.chat_id);

              // Create a minimal session object from the response data
              const minimalSession: ChatSession = {
                id: response.chat_id,
                title: "Nueva conversación", // Will be updated by auto-titling
                created_at: response.created_at || new Date().toISOString(),
                updated_at: response.created_at || new Date().toISOString(),
                first_message_at:
                  response.created_at || new Date().toISOString(),
                last_message_at:
                  response.created_at || new Date().toISOString(),
                message_count: 2, // User + assistant
                model: response.model || selectedModel,
                preview: message.substring(0, 100),
                pinned: false,
                tools_enabled: normalizeToolsState(response.tools_enabled),
              };

              reconcileConversation(tempIdToReconcile, minimalSession);
            }

            // Auto-title logic: Execute for all new conversations (unified)
            if (wasNewConversation && response.chat_id) {
              (async () => {
                try {
                  const { generateTitleFromMessage } =
                    await import("@/lib/conversation-utils");
                  const aiTitle = await generateTitleFromMessage(
                    msg,
                    apiClient,
                  );

                  if (aiTitle && aiTitle !== "Nueva conversación") {
                    // Load sessions first to ensure conversation exists in store
                    await loadChatSessions();

                    // Optimistic update - show title immediately
                    updateSessionTitle(response.chat_id, aiTitle);

                    // Update backend in background
                    await apiClient.updateChatSession(response.chat_id, {
                      title: aiTitle,
                      auto_title: true,
                    });

                    logDebug("Auto-titled conversation successfully", {
                      chatId: response.chat_id,
                      title: aiTitle,
                    });
                  }
                } catch (error) {
                  logWarn("Failed to auto-title conversation", { error });
                }
              })();
            }

            // DEBUG: Log response from backend
            logDebug("[ChatView] Response from backend", {
              has_content: !!response.content,
              content_length: response.content?.length || 0,
              response_keys: Object.keys(response),
              response,
            });

            // Defensive parsing: sometimes backend may return the whole ChatResponse as JSON string in content
            let safeContent = response.content || "";
            let parsedContent: any = null;
            if (
              typeof safeContent === "string" &&
              safeContent.trim().startsWith("{")
            ) {
              try {
                parsedContent = JSON.parse(safeContent);
                if (parsedContent && parsedContent.content) {
                  safeContent = parsedContent.content;
                  // Hydrate artifacts/metadata if present in embedded payload
                  response = {
                    ...response,
                    artifact: response.artifact || parsedContent.artifact,
                    metadata: response.metadata || parsedContent.metadata,
                  } as any; // Cast to any to allow decision property
                  // Add decision if present (not in type but exists in runtime)
                  if (parsedContent.decision) {
                    (response as any).decision = parsedContent.decision;
                  }
                  const decisionArtifact = (parsedContent.decision || {})
                    .audit_artifact;
                  if (!(response as any).artifact && decisionArtifact) {
                    response = {
                      ...response,
                      artifact: decisionArtifact,
                    } as any;
                  }
                }
              } catch {
                // keep original safeContent
              }
            }

            // At this point response is guaranteed to exist from the try-catch above
            const safeResponse = response!;

            const assistantMessage: ChatMessage = {
              id: safeResponse.message_id || placeholderId,
              role: "assistant",
              content: safeContent,
              artifact:
                safeResponse.artifact ||
                (safeResponse as any)?.decision_metadata?.audit_artifact ||
                (safeResponse.metadata as any)?.decision_metadata
                  ?.audit_artifact ||
                null,
              timestamp: safeResponse.created_at || new Date().toISOString(),
              model: safeResponse.model,
              tokens: safeResponse.tokens || 0,
              latency: safeResponse.latency_ms || 0,
              status: "delivered",
              isStreaming: false,
              task_id: safeResponse.task_id,
              metadata: safeResponse.metadata, // Include audit metadata (report_pdf_url, etc.)
            };

            // Extract report PDF URL from audit metadata
            if (safeResponse.metadata?.decision_metadata?.report_pdf_url) {
              setCurrentReportPdfUrl(
                safeResponse.metadata.decision_metadata.report_pdf_url,
              );
              logDebug("[ChatView] Audit report PDF URL extracted", {
                url: safeResponse.metadata.decision_metadata.report_pdf_url,
              });
            }

            // NOTE: Files were already cleared earlier (see line ~790)
            return assistantMessage;
          } catch (error) {
            logError("❌ [ChatView] Failed to send chat message", {
              error,
              errorMessage:
                error instanceof Error ? error.message : String(error),
              errorStack: error instanceof Error ? error.stack : undefined,
              readyFilesLength: readyFiles.length,
            });

            // Even on error, try to clear files to avoid stuck state
            if (readyFiles.length > 0) {
              clearFilesV1Attachments();
              logDebug("[ChatView] ✅ Cleared files after error (cleanup)", {
                clearedCount: readyFiles.length,
              });
            }

            return {
              id: placeholderId,
              role: "assistant",
              content:
                "Lo siento, no pude conectar con el servidor de chat en este momento. Intenta nuevamente en unos segundos.",
              timestamp: new Date().toISOString(),
              status: "error" as const,
              isStreaming: false,
            };
          }
        },
        userMessageMetadata, // MVP-LOCK: Pass file_ids metadata for user message bubble
      );
    },
    [
      currentChatId,
      selectedModel,
      models,
      toolsEnabled,
      sendOptimizedMessage,
      updateStreamingContent,
      setCurrentChatId,
      loadChatSessions,
      reconcileConversation,
      updateSessionTitle,
      messages.length,
      filesV1Attachments,
      clearFilesV1Attachments,
    ],
  );

  // Copiloto 414: Audit progress handlers
  const handleStartAudit = React.useCallback(
    (fileId: string, filename: string) => {
      setActiveAudit({ fileId, filename });
      logDebug("[ChatView] Audit started", { fileId, filename });
    },
    [],
  );

  const handleAuditError = React.useCallback(
    (fileId: string, reason?: string) => {
      setActiveAudit(null);
      logError("[ChatView] Audit failed", { fileId, reason });
    },
    [],
  );

  const handleAuditComplete = React.useCallback(() => {
    setActiveAudit(null);

    // 🔧 FIX: Clear file attachments after audit completes
    // This ensures audit files don't persist after the audit report is received
    if (filesV1Attachments.length > 0) {
      clearFilesV1Attachments();
      logDebug("[ChatView] Cleared file attachments after audit completion", {
        clearedCount: filesV1Attachments.length,
      });
    }

    logDebug("[ChatView] Audit completed");
  }, [filesV1Attachments, clearFilesV1Attachments]);

  // Auto-clear audit progress when new message with validation arrives
  React.useEffect(() => {
    logDebug("[ChatView] Audit cleanup useEffect triggered", {
      activeAudit,
      messagesLen: messages.length,
      hasLatestMessage: messages.length > 0,
    });

    if (!activeAudit) {
      logDebug("[ChatView] No active audit, skipping cleanup");
      return;
    }

    const latestMessage = messages[messages.length - 1];
    logDebug("[ChatView] Checking latest message for validation_report_id", {
      hasMetadata: !!latestMessage?.metadata,
      metadataKeys: latestMessage?.metadata
        ? Object.keys(latestMessage.metadata)
        : [],
      hasValidationReportId:
        latestMessage?.metadata &&
        "validation_report_id" in latestMessage.metadata,
    });

    if (
      latestMessage?.metadata &&
      "validation_report_id" in latestMessage.metadata
    ) {
      logDebug("[ChatView] Calling handleAuditComplete");
      handleAuditComplete();
    }
  }, [messages, activeAudit, handleAuditComplete]);

  const handleSendMessage = React.useCallback(
    async (message: string, attachments?: ChatComposerAttachment[]) => {
      // ISSUE-009: Rate limiting - Prevent spam by checking if already sending
      if (isSending) {
        logDebug("Message send blocked - already sending");
        return;
      }

      const trimmed = message.trim();

      // Rollback feature flag: Allow disabling files-only send
      const allowFilesOnlySend =
        process.env.NEXT_PUBLIC_ALLOW_FILES_ONLY_SEND !== "false";

      // Fix Pack: Allow sending with empty message if files are ready (and flag enabled)
      const readyFileList = filesV1Attachments.filter(
        (a) => a.status === "READY",
      );
      const defaultAuditTarget =
        readyFileList.find(
          (file) => file.file_id === lastReadyAuditFile?.file_id,
        ) ?? readyFileList[readyFileList.length - 1];
      // MINIMALISMO FUNCIONAL: Usar archivos automáticamente cuando están listos
      const shouldAutoAudit =
        !trimmed && allowFilesOnlySend && Boolean(defaultAuditTarget);

      if (!trimmed && !shouldAutoAudit) return;

      setNudgeMessage(null);
      setResearchError(null);

      // Copiloto 414: Auto-trigger audit command when files están listos
      const effectiveMessage =
        shouldAutoAudit && defaultAuditTarget
          ? `Auditar archivo: ${defaultAuditTarget.filename}`
          : trimmed;

      if (shouldAutoAudit && defaultAuditTarget) {
        handleStartAudit(
          defaultAuditTarget.file_id,
          defaultAuditTarget.filename,
        );
      }

      const pendingAttachments = filesV1Attachments.filter(
        (a) => a.status !== "READY",
      );
      if (pendingAttachments.length > 0) {
        toast(
          `⏳ Procesando ${pendingAttachments.length} archivo${
            pendingAttachments.length === 1 ? "" : "s"
          }… Intenta de nuevo en unos segundos.`,
        );
        return;
      }

      // ISSUE-009: Set sending flag to prevent concurrent sends
      setIsSending(true);

      try {
        // Hard preference: if Deep Research tool is enabled, route directly to research
        // to avoid falling back to plain chat when intent classifier is ambiguous.
        if (deepResearchEnabled) {
          await startDeepResearchFlow(effectiveMessage, undefined, attachments);
          return;
        }

        await researchGate(effectiveMessage, {
          deepResearchOn: deepResearchEnabled,
          openWizard: (userText) =>
            setPendingWizard({ query: userText, attachments }),
          startResearch: async (userText, scope) => {
            await startDeepResearchFlow(userText, scope, attachments);
          },
          showNudge: (msg) => setNudgeMessage(msg),
          routeToChat: (userText) => sendStandardMessage(userText, attachments),
          onSuggestTool: (tool) =>
            logAction("planner.suggested.tool", { tool }),
        });
      } catch (error) {
        logDebug("researchGate fallback", error);
        try {
          await sendStandardMessage(effectiveMessage, attachments);
        } catch (sendError) {
          throw sendError;
        }
      } finally {
        // ISSUE-009: Always clear sending flag
        setIsSending(false);
      }
    },
    [
      isSending,
      deepResearchEnabled,
      sendStandardMessage,
      setPendingWizard,
      startDeepResearchFlow,
      setNudgeMessage,
      setResearchError,
      filesV1Attachments,
      lastReadyAuditFile,
      handleStartAudit,
    ],
  );

  const handleRetryMessage = async (messageId: string) => {
    const messageIndex = messages.findIndex((m) => m.id === messageId);
    if (messageIndex > 0) {
      const userMessage = messages[messageIndex - 1];
      if (userMessage.role === "user") {
        await handleSendMessage(userMessage.content);
      }
    }
  };

  // UX-005 handlers
  const handleRegenerateMessage = async (messageId: string) => {
    const messageIndex = messages.findIndex((m) => m.id === messageId);
    if (messageIndex <= 0) {
      logDebug("Cannot regenerate: no previous user message found");
      return;
    }

    const userMessage = messages[messageIndex - 1];
    if (userMessage.role !== "user") {
      logDebug("Cannot regenerate: previous message is not from user");
      return;
    }

    try {
      // Remove the assistant message that we're regenerating
      const updatedMessages = messages.filter((m) => m.id !== messageId);
      // Update messages state to remove the old response
      // Note: In a real app, this would be handled by a proper state management system

      logDebug("Regenerating message", {
        messageId,
        userContent: userMessage.content,
        messageIndex,
      });

      // Resend the user message to generate a new response
      await handleSendMessage(
        userMessage.content,
        userMessage.attachments as any,
      );
    } catch (error) {
      logDebug("Failed to regenerate message", error);
      // In a real app, you'd show an error toast/notification
    }
  };

  const handleStopStreaming = React.useCallback(() => {
    logDebug("Stop streaming requested");
    // Cancel the current chat request
    cancelCurrentRequest();
    // Also stop research streaming if active
    if (researchIsStreaming) {
      stopResearchStream();
    }
    setLoading(false);
  }, [
    cancelCurrentRequest,
    researchIsStreaming,
    stopResearchStream,
    setLoading,
  ]);

  const handleCancelResearch = React.useCallback(async () => {
    if (!activeResearch) return;

    try {
      stopResearchStream();
      await apiClient.cancelResearchTask(
        activeResearch.taskId,
        "user_cancelled",
      );
    } catch (error) {
      logDebug("Cancel research error", error);
      setNudgeMessage(
        "No se pudo cancelar la investigación. Inténtalo nuevamente.",
      );
    } finally {
      resetResearchState();
      setActiveResearch(null);
    }
  }, [
    activeResearch,
    stopResearchStream,
    resetResearchState,
    setNudgeMessage,
    setActiveResearch,
  ]);

  const handleCloseResearchCard = React.useCallback(() => {
    resetResearchState();
    setActiveResearch(null);
    setResearchError(null);
  }, [resetResearchState, setActiveResearch, setResearchError]);

  const handleCopyMessage = () => {};

  const router = useRouter();

  const latestChatIdRef = React.useRef(currentChatId);
  React.useEffect(() => {
    latestChatIdRef.current = currentChatId;
  }, [currentChatId]);

  const handleSelectChat = React.useCallback((chatId: string) => {
    // Don't do anything here - let the navigation and useEffect handle it
    // This prevents double loading and race conditions
  }, []);

  const optimisticCreationEnabled =
    featureFlags?.create_chat_optimistic !== false;

  const handleStartNewChat = React.useCallback(async (): Promise<
    string | null
  > => {
    if (!optimisticCreationEnabled) {
      logAction("START_NEW_CHAT_FALLBACK_FLOW", {
        reason: "feature_flag_disabled",
      });
      startNewChat();
      router.push("/chat", { scroll: false });
      return null;
    }

    logAction("START_NEW_CHAT_CLICKED", {
      currentChatId,
      messagesLen: messages.length,
      pendingCreationId,
      isCreatingConversation,
    });

    if (isCreatingConversation || pendingCreationId) {
      logAction("BLOCKED_NEW_CHAT", {
        reason: "pending_creation",
        pendingCreationId,
      });
      return pendingCreationId;
    }

    if (currentChatId && messages.length === 0) {
      const isOptimistic = currentChatId.startsWith("temp-");
      // Silent feedback: prevent action without showing toast
      logAction("BLOCKED_NEW_CHAT", {
        reason: "current_chat_empty",
        isOptimistic,
      });
      return null;
    }

    const idempotencyKey =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `temp-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    const createdAt = new Date().toISOString();

    const tempId = `temp-${idempotencyKey}`;
    const optimisticId = createConversationOptimistic(
      tempId,
      createdAt,
      idempotencyKey,
    );
    logAction("CREATED_OPTIMISTIC_CHAT", {
      tempId: optimisticId,
      idempotencyKey,
    });

    setCurrentChatId(optimisticId);
    clearMessages();

    logState("AFTER_NEW_CHAT", {
      currentChatId: optimisticId,
      messagesLength: 0,
      isDraftMode: false,
    });

    void (async () => {
      try {
        const response = await apiClient.createConversation(
          { model: selectedModel, tools_enabled: draftToolsEnabled },
          { idempotencyKey },
        );

        const realSession: ChatSession = {
          id: response.id,
          title: response.title,
          created_at: response.created_at,
          updated_at: response.updated_at,
          first_message_at: null,
          last_message_at: null,
          message_count: response.message_count,
          model: response.model,
          preview: "",
          pinned: false,
          state: "draft",
          idempotency_key: idempotencyKey,
          tools_enabled: normalizeToolsState(response.tools_enabled),
        };

        reconcileConversation(optimisticId, realSession);

        const latestChatId = latestChatIdRef.current;
        const shouldFocusNewChat =
          latestChatId === optimisticId || latestChatId === null;

        if (shouldFocusNewChat) {
          setCurrentChatId(realSession.id);
          router.replace(`/chat/${realSession.id}`, { scroll: false });
        }
      } catch (error: any) {
        logError("Failed to create conversation", {
          error,
          tempId: optimisticId,
        });
        removeOptimisticConversation(optimisticId);
        toast.error("No se pudo crear la conversación.");
      }
    })();

    return optimisticId;
  }, [
    optimisticCreationEnabled,
    clearMessages,
    createConversationOptimistic,
    currentChatId,
    isCreatingConversation,
    messages.length,
    pendingCreationId,
    reconcileConversation,
    removeOptimisticConversation,
    router,
    selectedModel,
    setCurrentChatId,
    startNewChat,
    draftToolsEnabled,
  ]);

  // Chat action handlers - UX-002
  const handleRenameChat = React.useCallback(
    async (chatId: string, newTitle: string) => {
      try {
        await renameChatSession(chatId, newTitle);
        logDebug("Chat renamed successfully", chatId, newTitle);
      } catch (error) {
        logError("Failed to rename chat:", error);
        toast.error("No se pudo renombrar la conversación");
      }
    },
    [renameChatSession],
  );

  const handlePinChat = React.useCallback(
    async (chatId: string) => {
      try {
        await pinChatSession(chatId);
        logDebug("Chat pin toggled successfully", chatId);
      } catch (error) {
        logError("Failed to toggle pin for chat:", error);
        toast.error("No se pudo fijar la conversación");
      }
    },
    [pinChatSession],
  );

  const handleDeleteChat = React.useCallback(
    async (chatId: string) => {
      try {
        await deleteChatSession(chatId);
        logDebug("Chat deleted successfully", chatId);
        // If deleting current chat, open draft mode (no optimistic conversation)
        if (chatId === currentChatId) {
          startNewChat(); // Uses draft mode instead of creating optimistic conversation
        }
      } catch (error) {
        logError("Failed to delete chat:", error);
        toast.error("No se pudo eliminar la conversación");
      }
    },
    [deleteChatSession, currentChatId, startNewChat],
  );

  const handleOpenTools = React.useCallback(() => {
    // This callback is now handled by the ChatComposer's menu system
    // The ChatComposer will open its ToolMenu and handle individual tool selection
  }, []);

  // Anti-spam: Can only create new chat if:
  // 1. No current chat selected, OR
  // 2. Current chat has messages, OR
  // 3. There's no pending optimistic conversation in-flight
  const canCreateNewChat = React.useMemo(() => {
    if (!optimisticCreationEnabled) {
      return true;
    }

    if (pendingCreationId) {
      return false;
    }

    if (!currentChatId) return true;
    if (messages.length > 0) return true;

    // Block if current is an optimistic conversation without messages
    return !currentChatId.startsWith("temp-");
  }, [
    currentChatId,
    messages.length,
    optimisticCreationEnabled,
    pendingCreationId,
  ]);

  if (!isHydrated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-saptiva-slate">Cargando sesión...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  // BUG-FIX: Guard against showing "not found" during transitions
  // Only show error when:
  // 1. chatNotFound is true (404 from backend)
  // 2. We have a resolvedChatId (not navigating to /chat)
  // 3. NOT creating a new conversation (optimistic creation in progress)
  // 4. NOT in draft mode (user clicked "new chat")
  // 5. NOT a temp ID (temporary during creation)
  const shouldShowNotFound =
    chatNotFound &&
    resolvedChatId &&
    !isCreatingConversation &&
    !isDraftMode() &&
    !resolvedChatId.startsWith("temp-");

  // Chat not found state or welcome banner
  const welcomeComponent = shouldShowNotFound ? (
    <div className="flex h-full items-center justify-center">
      <div className="text-center max-w-md mx-auto px-6">
        <h3 className="text-xl font-semibold text-white mb-3">
          Conversación no encontrada
        </h3>
        <p className="text-saptiva-light/70 mb-6">
          La conversación{" "}
          <code className="px-2 py-1 bg-white/10 rounded text-sm">
            {resolvedChatId}
          </code>{" "}
          no existe o no tienes acceso a ella.
        </p>
        <button
          onClick={async () => {
            const nextId = await handleStartNewChat();
            if (nextId) {
              router.replace(`/chat/${nextId}`, { scroll: false });
            } else {
              router.replace("/chat", { scroll: false });
            }
          }}
          className="inline-flex items-center justify-center rounded-full bg-saptiva-blue px-6 py-3 text-sm font-semibold text-white hover:bg-saptiva-lightBlue/90 transition-colors"
        >
          Iniciar nueva conversación
        </button>
      </div>
    </div>
  ) : (
    <WelcomeBanner user={user || undefined} />
  );

  return (
    <ChatShell
      sidebar={
        <ConversationList
          sessions={chatSessions}
          onNewChat={handleStartNewChat}
          onSelectChat={handleSelectChat}
          activeChatId={currentChatId}
          isLoading={chatSessionsLoading}
          onRenameChat={handleRenameChat}
          onPinChat={handlePinChat}
          onDeleteChat={handleDeleteChat}
          isCreatingConversation={isCreatingConversation}
          canCreateNew={canCreateNewChat}
        />
      }
      models={models}
      selectedModel={selectedModel}
      onModelChange={setSelectedModel}
    >
      <div className="relative flex h-full flex-col">
        {(nudgeMessage || pendingWizard || activeResearch) && (
          <div className="flex flex-col items-center gap-4 px-4 pt-4">
            {nudgeMessage && (
              <IntentNudge
                message={nudgeMessage}
                onDismiss={() => setNudgeMessage(null)}
              />
            )}

            {pendingWizard && (
              <DeepResearchWizard
                query={pendingWizard.query}
                onConfirm={(scope) =>
                  startDeepResearchFlow(pendingWizard.query, scope)
                }
                onCancel={() => setPendingWizard(null)}
                loading={isStartingResearch}
              />
            )}

            {activeResearch && (
              <DeepResearchProgress
                query={activeResearch.query}
                phase={researchPhase}
                progress={researchProgress}
                sources={researchSources}
                evidences={researchEvidences}
                report={researchReport}
                errorMessage={researchError ?? researchHookError?.error ?? null}
                isStreaming={researchIsStreaming}
                onCancel={handleCancelResearch}
                onClose={handleCloseResearchCard}
              />
            )}

            {/* Copiloto 414: Audit progress indicator */}
            {activeAudit && <AuditProgress filename={activeAudit.filename} />}
          </div>
        )}

        {/* ISSUE-015: Wrap ChatInterface in ErrorBoundary to prevent full UI crash */}
        <ErrorBoundary
          fallback={
            <div className="flex flex-1 flex-col items-center justify-center rounded-2xl border border-red-500/20 bg-red-500/5 p-8 text-center">
              <div className="mb-4 text-6xl">💬</div>
              <h2 className="mb-2 text-xl font-semibold text-white">
                Error en el chat
              </h2>
              <p className="mb-6 max-w-md text-sm text-saptiva-light/70">
                Ocurrió un error al renderizar el chat. Intenta recargar la
                página.
              </p>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="rounded-full bg-[#49F7D9] px-6 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90"
              >
                Recargar página
              </button>
            </div>
          }
        >
          <div className="flex h-full min-h-0 gap-0">
            <div
              className={cn(
                "transition-all duration-300",
                isCanvasOpen ? "flex-1 min-w-0" : "w-full",
              )}
            >
              <ChatInterface
                key={`chat-${currentChatId}-${selectionEpoch}`}
                className="flex-1"
                currentChatId={currentChatId}
                messages={messages}
                onSendMessage={handleSendMessage}
                onRetryMessage={handleRetryMessage}
                onRegenerateMessage={handleRegenerateMessage}
                onStopStreaming={handleStopStreaming}
                onCopyMessage={handleCopyMessage}
                loading={isLoading}
                welcomeMessage={welcomeComponent}
                featureFlags={featureFlags}
                toolsEnabled={toolsEnabled}
                onToggleTool={toggleTool}
                selectedTools={selectedTools}
                onRemoveTool={handleRemoveTool}
                onAddTool={handleAddTool}
                onOpenTools={handleOpenTools}
                onFeedback={submitFeedback}
                isCreating={isCreatingConversation}
                isHydrating={
                  currentChatId ? isHydratingByChatId[currentChatId] : false
                }
                // Files V1 props - MINIMALISMO FUNCIONAL: Sin toggle
                filesV1Attachments={filesV1Attachments}
                onAddFilesV1Attachment={addFilesV1Attachment}
                onRemoveFilesV1Attachment={removeFilesV1Attachment}
                onClearFilesV1Attachments={clearFilesV1Attachments}
                lastReadyFile={lastReadyAuditFile}
                // Copiloto 414: Audit progress callback
                onStartAudit={handleStartAudit}
                onAuditError={handleAuditError}
              />
            </div>
            {/* Canvas: Unified for both desktop and mobile, side by side with chat */}
            <CanvasPanel
              key={effectiveChatId || "no-chat"}
              className="h-full"
              reportPdfUrl={currentReportPdfUrl || undefined}
            />
          </div>
        </ErrorBoundary>
      </div>
    </ChatShell>
  );
}
