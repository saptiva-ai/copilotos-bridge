"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChatMessage, ChatMessageProps } from "./ChatMessage";
import { ChatComposer, ChatComposerAttachment } from "./ChatComposer";
import { CompactChatComposer } from "./ChatComposer/CompactChatComposer";
import { ChatHero } from "./ChatHero";
import { ChatSkeleton } from "./ChatSkeleton";
import { LoadingSpinner, Modal } from "../ui";
import { ReportPreviewModal } from "../research/ReportPreviewModal";
import { cn } from "../../lib/utils";
import type { ToolId } from "@/types/tools";
import { useAuthStore } from "@/lib/auth-store";
import { useChatStore } from "@/lib/stores/chat-store";
import { useDocumentReview } from "@/hooks/useDocumentReview";
import { detectReviewCommand } from "@/lib/review-command-detector";
import { logDebug, logError } from "@/lib/logger";
import toast from "react-hot-toast";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { ValidationFindings } from "@/components/validation";
import { apiClient } from "@/lib/api-client";
import type { ValidationReportResponse } from "@/types/validation";
import type {
  ChatMessage as StoreChatMessage,
  ChatMessageStatus,
} from "@/lib/types";

import { FeatureFlagsResponse } from "@/lib/types";
import { logRender, logState, logAction } from "@/lib/ux-logger";
import { legacyKeyToToolId, toolIdToLegacyKey } from "@/lib/tool-mapping";
import {
  HELP_ONBOARDING_PROMPT_EVENT,
  type HelpOnboardingPromptDetail,
} from "@/lib/help-onboarding-events";
// Files V1 imports
import type { FileAttachment } from "@/types/files";
import type { LastReadyFile } from "@/hooks/useFiles";
// React Query hooks
import { useSendMessage } from "@/hooks/useSendMessage";

interface ChatInterfaceProps {
  messages: ChatMessageProps[];
  onSendMessage: (
    message: string,
    attachments?: ChatComposerAttachment[],
  ) => void;
  onRetryMessage?: (messageId: string) => void;
  onRegenerateMessage?: (messageId: string) => void;
  onStopStreaming?: () => void;
  onCopyMessage?: (text: string) => void;
  loading?: boolean;
  disabled?: boolean;
  className?: string;
  welcomeMessage?: React.ReactNode;
  toolsEnabled?: { [key: string]: boolean };
  onToggleTool?: (tool: string) => void;
  selectedTools?: ToolId[];
  onRemoveTool?: (id: ToolId) => void;
  onAddTool?: (id: ToolId) => void;
  onOpenTools?: () => void;
  featureFlags?: FeatureFlagsResponse | null;
  currentChatId?: string | null; // Track conversation ID to reset submitIntent
  isCreating?: boolean; // Optimistic conversation creation
  isHydrating?: boolean; // Loading conversation data
  // Files V1 props - MINIMALISMO FUNCIONAL: Sin toggle
  filesV1Attachments?: FileAttachment[];
  onAddFilesV1Attachment?: (attachment: FileAttachment) => void;
  onRemoveFilesV1Attachment?: (fileId: string) => void;
  onClearFilesV1Attachments?: (overrideChatId?: string) => void;
  lastReadyFile?: LastReadyFile | null;
  // Copiloto 414: Audit progress callback
  onStartAudit?: (fileId: string, filename: string) => void;
  onAuditError?: (fileId: string, reason?: string) => void;
  // HU7: Message feedback
  onFeedback?: (
    messageId: string,
    rating: "up" | "down",
    reason?: string,
  ) => Promise<void>;
}

export function ChatInterface({
  messages,
  onSendMessage,
  onRetryMessage,
  onRegenerateMessage,
  onStopStreaming,
  onCopyMessage,
  loading = false,
  disabled = false,
  className,
  welcomeMessage,
  toolsEnabled,
  onToggleTool,
  selectedTools,
  onRemoveTool,
  onAddTool,
  onOpenTools,
  featureFlags,
  currentChatId,
  isCreating = false,
  isHydrating = false,
  // Files V1 props - MINIMALISMO FUNCIONAL: Sin toggle
  filesV1Attachments = [],
  onAddFilesV1Attachment,
  onRemoveFilesV1Attachment,
  lastReadyFile,
  // Copiloto 414: Audit progress callback
  onStartAudit,
  onAuditError,
  // HU7: Message feedback
  onFeedback,
}: ChatInterfaceProps) {
  const [inputValue, setInputValue] = React.useState("");
  const [attachments, setAttachments] = React.useState<
    ChatComposerAttachment[]
  >([]);
  const [reportModal, setReportModal] = React.useState({
    isOpen: false,
    taskId: "",
    taskTitle: "",
  });
  const [auditModal, setAuditModal] = React.useState({
    isOpen: false,
    loading: false,
    documentId: "",
    filename: "",
    report: null as ValidationReportResponse | null,
    error: null as string | null,
  });
  const [submitIntent, setSubmitIntent] = React.useState(false); // Only true after first submit
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const messagesContainerRef = React.useRef<HTMLDivElement>(null);
  const user = useAuthStore((state) => state.user);
  const prevChatIdRef = React.useRef(currentChatId);
  const mountChatIdRef = React.useRef(currentChatId);

  // Log component mount/unmount for debugging re-selection
  React.useEffect(() => {
    const mountChatId = mountChatIdRef.current;
    logAction("MOUNT_BODY", { chatId: mountChatId });

    return () => {
      logAction("UNMOUNT_BODY", { chatId: mountChatId });
    };
  }, []); // Empty deps = mount/unmount only

  // Reset submitIntent when switching to a different conversation
  React.useEffect(() => {
    if (prevChatIdRef.current !== currentChatId) {
      logState("CHAT_SWITCHED", {
        currentChatId: currentChatId || null,
        messagesLength: messages.length,
        isDraftMode: false,
        submitIntent: submitIntent,
        showHero: undefined,
      });
      setSubmitIntent(false);
      prevChatIdRef.current = currentChatId;
    }
  }, [currentChatId, messages.length, submitIntent]);

  const scrollToBottom = React.useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop =
          messagesContainerRef.current.scrollHeight;
      }
    }, 100);
  }, []);

  React.useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  React.useEffect(() => {
    if (!loading && messages.length > 0) {
      scrollToBottom();
    }
  }, [loading, scrollToBottom, messages.length]);

  // Review hooks
  const addMessage = useChatStore((state) => state.addMessage);
  const { startReview } = useDocumentReview();
  const toolVisibility = useSettingsStore((state) => state.toolVisibility);
  const loadToolVisibility = useSettingsStore(
    (state) => state.loadToolVisibility,
  );
  const toolVisibilityLoaded = useSettingsStore(
    (state) => state.toolVisibilityLoaded,
  );

  // React Query: Optimistic updates for message sending
  const sendMessage = useSendMessage(currentChatId ?? null);

  React.useEffect(() => {
    if (!toolVisibilityLoaded) {
      loadToolVisibility();
    }
  }, [loadToolVisibility, toolVisibilityLoaded]);

  const handleCloseAuditModal = React.useCallback(() => {
    setAuditModal({
      isOpen: false,
      loading: false,
      documentId: "",
      filename: "",
      report: null,
      error: null,
    });
  }, []);

  const handleViewAuditReport = React.useCallback(
    async (
      _validationReportId: string,
      documentId: string,
      filename?: string,
    ) => {
      if (!documentId) {
        return;
      }

      setAuditModal({
        isOpen: true,
        loading: true,
        documentId,
        filename: filename ?? "Reporte de auditoría",
        report: null,
        error: null,
      });

      try {
        const report = await apiClient.getDocumentValidation(documentId);
        setAuditModal((prev) => ({
          ...prev,
          loading: false,
          report,
        }));
      } catch (error) {
        logError("[ChatInterface] Failed to load audit report", error);
        const message =
          error instanceof Error
            ? error.message
            : "No se pudo cargar el reporte de auditoría.";
        toast.error("No se pudo cargar el reporte de auditoría.");
        setAuditModal((prev) => ({
          ...prev,
          loading: false,
          error: message,
        }));
      }
    },
    [],
  );

  const handleReAuditDocument = React.useCallback(
    async (documentId: string, _jobId?: string, filename?: string) => {
      if (!documentId) {
        return;
      }

      if (!currentChatId) {
        toast.error("Necesitas una conversación activa para re-auditar.");
        return;
      }

      const displayName = filename ?? "Documento auditado";
      onStartAudit?.(documentId, displayName);

      try {
        const response = await apiClient.auditFileInChat(
          documentId,
          currentChatId,
          "auto",
        );

        if (response) {
          const newMessage: StoreChatMessage = {
            id: response.id,
            content: response.content,
            role: response.role,
            timestamp: response.created_at,
            status:
              (response.status as ChatMessageStatus | undefined) || "delivered",
            model: response.model,
            tokens: response.tokens,
            latency: response.latency_ms,
            task_id: response.task_id,
            metadata: {
              ...(response.metadata ?? {}),
              validation_report_id: response.validation_report_id,
              document_id: documentId,
              filename: displayName,
            },
          };

          addMessage(newMessage);
        }

        toast.success(
          "Re-auditoría solicitada. Recibirás un nuevo reporte en unos momentos.",
        );
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "Error desconocido al re-auditar.";
        logError("[ChatInterface] Failed to re-audit document", {
          documentId,
          error,
        });
        onAuditError?.(documentId, message);
        toast.error("No se pudo re-auditar el documento. Inténtalo de nuevo.");
      }
    },
    [addMessage, currentChatId, onAuditError, onStartAudit],
  );

  // Handle message feedback (thumbs up/down)
  const handleMessageFeedback = React.useCallback(
    async (messageId: string, rating: "up" | "down", reason?: string) => {
      // Prioritize the onFeedback prop if provided (Architectural Layering)
      if (onFeedback) {
        return onFeedback(messageId, rating, reason);
      }

      const resolvedChatId =
        currentChatId ??
        (typeof window !== "undefined"
          ? (window.location.pathname.match(/\/chat\/([^/]+)/)?.[1] ?? null)
          : null);

      if (!resolvedChatId) {
        logError("[ChatInterface] No chat ID for feedback");
        return;
      }

      try {
        await apiClient.submitMessageFeedback({
          messageId,
          conversationId: resolvedChatId,
          rating,
          reason,
        });
        logDebug("[ChatInterface] Feedback submitted (fallback)", {
          messageId,
          conversationId: resolvedChatId,
          rating,
          reason,
        });
      } catch (error) {
        logError("[ChatInterface] Failed to submit feedback (fallback)", error);
        toast.error("No se pudo enviar el feedback. Inténtalo de nuevo.");
        throw error; // Re-throw so MessageFeedback can handle the error state
      }
    },
    [currentChatId, onFeedback],
  );

  // Calculate selected tools BEFORE handleSend (needed for optimistic updates)
  const selectedToolIds = React.useMemo<ToolId[]>(() => {
    // Prefer the new selectedTools prop if available (including empty arrays)
    if (selectedTools !== undefined) {
      return selectedTools;
    }

    // Fallback to legacy toolsEnabled only if selectedTools is not passed
    if (!toolsEnabled) return [];

    return Object.entries(toolsEnabled)
      .filter(([, enabled]) => enabled)
      .map(([legacyKey]) => legacyKeyToToolId(legacyKey))
      .filter((id): id is ToolId => {
        if (!id) return false;
        return Boolean(toolVisibility[id]);
      });
  }, [selectedTools, toolsEnabled, toolVisibility]);

  const handleSend = React.useCallback(async () => {
    const trimmed = inputValue.trim();

    // MVP-LOCK: Desactivar detección de comandos de revisión
    // El flujo de Review está deshabilitado para el MVP
    const REVIEW_FLOW_DISABLED = true;

    // MINIMALISMO FUNCIONAL: Permitir envío si hay archivos listos o texto
    const hasReadyFiles = filesV1Attachments.some((a) => a.status === "READY");
    const allowFilesOnlySend =
      process.env.NEXT_PUBLIC_ALLOW_FILES_ONLY_SEND !== "false";
    const canSend = trimmed.length > 0 || (hasReadyFiles && allowFilesOnlySend);

    if (!canSend || disabled || loading) return;

    // Mark submit intent (triggers hero → chat transition)
    setSubmitIntent(true);

    // MVP-LOCK: Skip review command detection, go straight to chat
    if (!REVIEW_FLOW_DISABLED) {
      // Legacy review flow code (now disabled)
      const reviewCommand = detectReviewCommand(trimmed);
      if (reviewCommand.isReviewCommand) {
        logDebug(
          "[MVP-LOCK] Review command detected but ignored",
          reviewCommand,
        );
      }
    }

    // Always route to chat with file_ids
    // Optimistic update: Add user message to UI instantly
    const readyFiles = filesV1Attachments.filter((a) => a.status === "READY");
    const fileIds = readyFiles.map((a) => a.file_id);

    // Build tools configuration
    const toolsConfig = selectedToolIds.reduce(
      (acc, toolId) => {
        acc[toolId] = true;
        return acc;
      },
      {} as Record<string, boolean>,
    );

    if (currentChatId && (trimmed || fileIds.length > 0)) {
      sendMessage.mutate({
        content: trimmed,
        fileIds: fileIds.length > 0 ? fileIds : undefined,
        files: readyFiles.length > 0 ? readyFiles : undefined,
        toolsEnabled:
          Object.keys(toolsConfig).length > 0 ? toolsConfig : undefined,
      });
    }

    // Continue with existing streaming flow
    onSendMessage(trimmed, attachments.length ? attachments : undefined);
    setInputValue("");
    setAttachments([]);
  }, [
    inputValue,
    disabled,
    loading,
    onSendMessage,
    attachments,
    filesV1Attachments,
    currentChatId,
    sendMessage,
    selectedToolIds,
  ]);

  const handleFileAttachmentChange = React.useCallback(
    (next: ChatComposerAttachment[]) => {
      setAttachments(next);
    },
    [],
  );

  React.useEffect(() => {
    const handleHelpPrompt = (event: Event) => {
      const customEvent = event as CustomEvent<HelpOnboardingPromptDetail>;
      const prompt = customEvent.detail?.prompt;
      if (!prompt || typeof prompt !== "string") return;
      setInputValue(prompt);
    };

    window.addEventListener(
      HELP_ONBOARDING_PROMPT_EVENT,
      handleHelpPrompt as EventListener,
    );
    return () => {
      window.removeEventListener(
        HELP_ONBOARDING_PROMPT_EVENT,
        handleHelpPrompt as EventListener,
      );
    };
  }, []);

  const handleRemoveToolInternal = React.useCallback(
    (id: ToolId) => {
      // Prefer the new onRemoveTool prop if available
      if (onRemoveTool) {
        onRemoveTool(id);
        return;
      }

      // Fallback to legacy onToggleTool
      if (onToggleTool) {
        const legacyKey = toolIdToLegacyKey(id);
        if (legacyKey) {
          onToggleTool(legacyKey);
        }
      }
    },
    [onRemoveTool, onToggleTool],
  );

  // Robust showHero/showSkeleton selector: Check all conditions including hydration state
  const showSkeleton = React.useMemo(() => {
    // Show skeleton during optimistic creation or hydration
    if (isCreating || isHydrating) return true;

    // Show skeleton if loading and no messages yet (legacy behavior)
    if (loading && messages.length === 0 && !submitIntent) return true;

    return false;
  }, [loading, messages.length, submitIntent, isCreating, isHydrating]);

  const showHero = React.useMemo(() => {
    // Never show hero if we have messages
    if (messages.length > 0) return false;

    // Never show hero if showing skeleton
    if (showSkeleton) return false;

    // Never show hero if loading (prevents flicker during hydration)
    if (loading) return false;

    // Never show hero if user has submitted (progressive commitment)
    if (submitIntent) return false;

    // All conditions met: Show hero
    return true;
  }, [messages.length, loading, submitIntent, showSkeleton]);

  // Log render state
  React.useEffect(() => {
    logRender("ChatInterface", {
      messagesLen: messages.length,
      submitIntent,
      showHero,
      loading,
    });
  });

  // Auto-scroll to bottom on new messages
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages]);

  return (
    <div className={cn("flex h-full flex-col relative", className)}>
      <AnimatePresence mode="wait">
        {showSkeleton ? (
          /* Skeleton Mode: Show during creation/hydration to prevent flash */
          <motion.section
            key={`skeleton-${currentChatId || "loading"}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="flex-1"
          >
            <ChatSkeleton />
          </motion.section>
        ) : showHero ? (
          /* Hero Mode: Centered container with greeting + composer */
          <motion.section
            key={`hero-${currentChatId || "new"}`}
            initial={{ opacity: 1 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.16, ease: "easeOut" }}
            className="flex-1 flex items-center justify-center px-4"
          >
            <div className="w-full max-w-[640px] space-y-6 text-center">
              <h1 className="text-3xl font-semibold text-foreground">
                ¿Cómo puedo ayudarte, {user?.username || "Usuario"}?
              </h1>

              {/* Composer in hero mode - NO onActivate, NO focus triggers */}
              <CompactChatComposer
                value={inputValue}
                onChange={setInputValue}
                onSubmit={handleSend}
                onSendMessageDirect={onSendMessage}
                onCancel={loading ? onStopStreaming : undefined}
                disabled={disabled}
                loading={loading}
                layout="center"
                showCancel={loading}
                selectedTools={selectedToolIds}
                onRemoveTool={handleRemoveToolInternal}
                onAddTool={onAddTool}
                attachments={attachments}
                onAttachmentsChange={handleFileAttachmentChange}
                // Files V1 props - MINIMALISMO FUNCIONAL: Sin toggle
                filesV1Attachments={filesV1Attachments}
                onAddFilesV1Attachment={onAddFilesV1Attachment}
                onRemoveFilesV1Attachment={onRemoveFilesV1Attachment}
                lastReadyFile={lastReadyFile}
                conversationId={currentChatId || undefined}
                featureFlags={featureFlags}
                // Copiloto 414: Audit progress callback
                onStartAudit={onStartAudit}
                onAuditError={onAuditError}
              />
            </div>
          </motion.section>
        ) : (
          /* Chat Mode: Messages + bottom composer */
          <motion.div
            key={`body-${currentChatId || "new"}`}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
            className="flex h-full flex-col"
          >
            <section
              id="message-list"
              ref={messagesContainerRef}
              className="relative flex-1 min-h-0 overflow-y-auto overscroll-contain thin-scroll main-has-composer"
              style={{ scrollBehavior: "smooth" }}
            >
              <div className="relative mx-auto max-w-3xl px-4 min-h-full pb-6 pt-16">
                <div className="space-y-0">
                  {messages.map((message, index) => (
                    <ChatMessage
                      key={message.id || index}
                      {...message}
                      onCopy={onCopyMessage}
                      onRetry={onRetryMessage}
                      onRegenerate={onRegenerateMessage}
                      onStop={onStopStreaming}
                      onViewReport={(taskId, taskTitle) =>
                        setReportModal({
                          isOpen: true,
                          taskId: taskId ?? "",
                          taskTitle: taskTitle ?? "",
                        })
                      }
                      onViewAuditReport={handleViewAuditReport}
                      onReAuditDocument={handleReAuditDocument}
                      conversationId={currentChatId ?? undefined}
                      onFeedback={handleMessageFeedback}
                      onSendMessage={onSendMessage}
                    />
                  ))}
                </div>
                <div ref={messagesEndRef} />
              </div>
            </section>

            {/* Composer at bottom in chat mode */}
            <CompactChatComposer
              value={inputValue}
              onChange={setInputValue}
              onSubmit={handleSend}
              onSendMessageDirect={onSendMessage}
              onCancel={loading ? onStopStreaming : undefined}
              disabled={disabled}
              loading={loading}
              layout="bottom"
              showCancel={loading}
              selectedTools={selectedToolIds}
              onRemoveTool={handleRemoveToolInternal}
              onAddTool={onAddTool}
              attachments={attachments}
              onAttachmentsChange={handleFileAttachmentChange}
              // Files V1 props - MINIMALISMO FUNCIONAL: Sin toggle
              filesV1Attachments={filesV1Attachments}
              onAddFilesV1Attachment={onAddFilesV1Attachment}
              onRemoveFilesV1Attachment={onRemoveFilesV1Attachment}
              lastReadyFile={lastReadyFile}
              conversationId={currentChatId || undefined}
              featureFlags={featureFlags}
              // Copiloto 414: Audit progress callback
              onStartAudit={onStartAudit}
              onAuditError={onAuditError}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <ReportPreviewModal
        isOpen={reportModal.isOpen}
        taskId={reportModal.taskId}
        taskTitle={reportModal.taskTitle}
        onClose={() =>
          setReportModal({ isOpen: false, taskId: "", taskTitle: "" })
        }
      />

      <Modal
        isOpen={auditModal.isOpen}
        onClose={handleCloseAuditModal}
        title={auditModal.filename || "Reporte de auditoría"}
        size="xl"
        className="bg-surface text-foreground border border-border"
      >
        {auditModal.loading ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : auditModal.error ? (
          <p className="text-sm text-red-400">{auditModal.error}</p>
        ) : auditModal.report ? (
          <div className="max-h-[70vh] overflow-y-auto pr-2">
            <ValidationFindings report={auditModal.report} />
          </div>
        ) : (
          <p className="text-sm text-muted">
            Selecciona un reporte de auditoría para ver los detalles.
          </p>
        )}
      </Modal>
    </div>
  );
}

export function ChatWelcomeMessage() {
  return (
    <div className="mx-auto max-w-xl text-center text-foreground">
      <div className="inline-flex items-center rounded-full border border-border bg-surface px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-muted">
        Saptiva Copilot OS
      </div>
      <h2 className="mt-4 text-3xl font-semibold text-foreground">
        Conversaciones con enfoque, evidencia y control
      </h2>
      <p className="mt-3 text-sm text-muted">
        Inicia tu consulta o activa Deep Research para investigar con
        trazabilidad completa.
      </p>
    </div>
  );
}
