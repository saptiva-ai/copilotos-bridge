"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChatMessage, ChatMessageProps } from "./ChatMessage";
import { ChatComposer, ChatComposerAttachment } from "./ChatComposer";
import { CompactChatComposer } from "./ChatComposer/CompactChatComposer";
import { ChatHero } from "./ChatHero";
import { LoadingSpinner } from "../ui";
import { ReportPreviewModal } from "../research/ReportPreviewModal";
import { cn } from "../../lib/utils";
import type { ToolId } from "@/types/tools";
import { useAuthStore } from "@/lib/auth-store";
import { useChatStore } from "@/lib/stores/chat-store";
import { useDocumentReview } from "@/hooks/useDocumentReview";
import { detectReviewCommand } from "@/lib/review-command-detector";
import { logDebug } from "@/lib/logger";
import toast from "react-hot-toast";
import { useSettingsStore } from "@/lib/stores/settings-store";

import { FeatureFlagsResponse } from "@/lib/types";
import { logRender, logState, logAction } from "@/lib/ux-logger";
import { legacyKeyToToolId, toolIdToLegacyKey } from "@/lib/tool-mapping";

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
  const { messages: chatMessages } = useChatStore();
  const { startReview } = useDocumentReview();
  const toolVisibility = useSettingsStore((state) => state.toolVisibility);
  const loadToolVisibility = useSettingsStore(
    (state) => state.loadToolVisibility,
  );
  const toolVisibilityLoaded = useSettingsStore(
    (state) => state.toolVisibilityLoaded,
  );

  React.useEffect(() => {
    if (!toolVisibilityLoaded) {
      loadToolVisibility();
    }
  }, [loadToolVisibility, toolVisibilityLoaded]);

  const handleSend = React.useCallback(async () => {
    const trimmed = inputValue.trim();
    if (!trimmed || disabled || loading) return;

    // Mark submit intent (triggers hero → chat transition)
    setSubmitIntent(true);

    // 1. Detectar comandos de revisión ANTES de enviar al LLM
    const reviewCommand = detectReviewCommand(trimmed);

    if (reviewCommand.isReviewCommand) {
      logDebug("[ChatInterface] Review command detected", reviewCommand);

      // 2. Buscar el último documento subido
      const fileMessages = chatMessages.filter(
        (msg) => msg.kind === "file-review",
      );
      const latestDoc = fileMessages
        .filter((msg) => msg.review?.status === "uploaded" && msg.review?.docId)
        .sort((a, b) => {
          const aTime = new Date(a.timestamp).getTime();
          const bTime = new Date(b.timestamp).getTime();
          return bTime - aTime;
        })[0];

      if (!latestDoc?.review?.docId) {
        toast.error("No hay ningún documento subido para revisar");
        setInputValue("");
        return;
      }

      // 3. Iniciar revisión sin enviar al chat LLM
      logDebug("[ChatInterface] Starting review", {
        docId: latestDoc.review.docId,
      });

      const jobId = await startReview(latestDoc.review.docId, {
        model: "Saptiva Turbo",
        rewritePolicy: "conservative",
        summary: reviewCommand.action === "summarize",
        colorAudit: true,
      });

      if (jobId) {
        toast.success(
          reviewCommand.action === "summarize"
            ? "Generando resumen del documento..."
            : "Iniciando revisión del documento...",
        );
      }

      setInputValue("");
      setAttachments([]);
      return; // ← NO enviar al chat LLM
    }

    // 4. Si no es comando de revisión, continuar flujo normal
    onSendMessage(trimmed, attachments.length ? attachments : undefined);
    setInputValue("");
    setAttachments([]);
  }, [
    inputValue,
    disabled,
    loading,
    onSendMessage,
    attachments,
    chatMessages,
    startReview,
  ]);

  const handleFileAttachmentChange = React.useCallback(
    (next: ChatComposerAttachment[]) => {
      setAttachments(next);
    },
    [],
  );

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
  }, [selectedTools, toolsEnabled]);

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

  // Robust showHero selector: Check all conditions including hydration state
  const showHero = React.useMemo(() => {
    // Never show hero if we have messages
    if (messages.length > 0) return false;

    // Never show hero if loading (prevents flicker during hydration)
    if (loading) return false;

    // Never show hero if user has submitted (progressive commitment)
    if (submitIntent) return false;

    // All conditions met: Show hero
    return true;
  }, [messages.length, loading, submitIntent]);

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
        {showHero ? (
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
              <h1 className="text-3xl font-semibold text-white/95">
                ¿Cómo puedo ayudarte, {user?.username || "Usuario"}?
              </h1>

              {/* Composer in hero mode - NO onActivate, NO focus triggers */}
              <CompactChatComposer
                value={inputValue}
                onChange={setInputValue}
                onSubmit={handleSend}
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
    </div>
  );
}

export function ChatWelcomeMessage() {
  return (
    <div className="mx-auto max-w-xl text-center text-white">
      <div className="inline-flex items-center rounded-full border border-white/20 bg-white/5 px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-saptiva-light/70">
        Saptiva Copilot OS
      </div>
      <h2 className="mt-4 text-3xl font-semibold text-white">
        Conversaciones con enfoque, evidencia y control
      </h2>
      <p className="mt-3 text-sm text-saptiva-light/70">
        Inicia tu consulta o activa Deep Research para investigar con
        trazabilidad completa.
      </p>
    </div>
  );
}
