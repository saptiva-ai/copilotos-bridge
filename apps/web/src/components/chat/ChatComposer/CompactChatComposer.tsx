"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../../../lib/utils";
import type { ToolId } from "@/types/tools";
import { TOOL_REGISTRY } from "@/types/tools";
import ToolMenu from "../ToolMenu/ToolMenu";
import { ChatComposerAttachment } from "./ChatComposer";
import { useChat } from "../../../lib/store";
import { logDebug } from "../../../lib/logger";
import { apiClient } from "../../../lib/api-client";
import { useDocumentReview } from "../../../hooks/useDocumentReview";
// Files V1 imports
import { FileUploadButton, FileAttachmentList, FilesToggle } from "../../files";
import type { FileAttachment } from "../../../types/files";
import type { FeatureFlagsResponse } from "@/lib/types";

interface CompactChatComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void | Promise<void>;
  onCancel?: () => void;
  disabled?: boolean;
  loading?: boolean;
  layout?: "center" | "bottom";
  onActivate?: () => void;
  placeholder?: string;
  maxLength?: number;
  showCancel?: boolean;
  className?: string;
  selectedTools?: ToolId[];
  onRemoveTool?: (id: ToolId) => void;
  onAddTool?: (id: ToolId) => void;
  attachments?: ChatComposerAttachment[];
  onAttachmentsChange?: (attachments: ChatComposerAttachment[]) => void;
  // Files V1 props
  filesV1Attachments?: FileAttachment[];
  onAddFilesV1Attachment?: (attachment: FileAttachment) => void;
  onRemoveFilesV1Attachment?: (fileId: string) => void;
  useFilesInQuestion?: boolean;
  onToggleFilesInQuestion?: (enabled: boolean) => void;
  conversationId?: string;
  featureFlags?: FeatureFlagsResponse | null;
}

// Icons
function PlusIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 6v12" />
      <path d="M18 12H6" />
    </svg>
  );
}

function SendIconArrowUp({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 19V5" />
      <path d="m5 12 7-7 7 7" />
    </svg>
  );
}

function StopIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <rect x={7} y={7} width={10} height={10} rx={2} />
    </svg>
  );
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 18L18 6" />
      <path d="M6 6l12 12" />
    </svg>
  );
}

// Min height: ~44px (min-h-11), Max height: ~192px (max-h-48)
const MIN_HEIGHT = 44;
const MAX_HEIGHT = 192;

// Feature flag: Show tools button (set to true when tools are functional)
const SHOW_TOOLS_BUTTON = true; // V1: Enabled for document upload

export function CompactChatComposer({
  value,
  onChange,
  onSubmit,
  onCancel,
  disabled = false,
  loading = false,
  layout = "bottom",
  onActivate,
  placeholder = "Pregúntame algo...",
  maxLength = 10000,
  showCancel = false,
  className,
  selectedTools = [],
  onRemoveTool,
  onAddTool,
  attachments = [],
  onAttachmentsChange,
  // Files V1 props
  filesV1Attachments = [],
  onAddFilesV1Attachment,
  onRemoveFilesV1Attachment,
  useFilesInQuestion = false,
  onToggleFilesInQuestion,
  conversationId,
  featureFlags,
}: CompactChatComposerProps) {
  const [showToolsMenu, setShowToolsMenu] = React.useState(false);
  const [textareaHeight, setTextareaHeight] = React.useState(MIN_HEIGHT);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [uploadingFiles, setUploadingFiles] = React.useState<
    Map<string, number>
  >(new Map()); // filename -> progress%

  const taRef = React.useRef<HTMLTextAreaElement>(null);
  const composerRef = React.useRef<HTMLDivElement>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  // Get current chat ID and finalize function from store
  const { currentChatId, finalizeCreation } = useChat();

  // Get document review hook for file upload
  const { uploadFile } = useDocumentReview();

  // Finalize creation when user starts typing (guarantee transition creating → draft)
  const handleFirstInput = React.useCallback(() => {
    logDebug("[chat.composer] handleFirstInput", { currentChatId });
    if (currentChatId && currentChatId.startsWith("temp-")) {
      logDebug("[chat.composer] finalizeCreation trigger", { currentChatId });
      finalizeCreation(currentChatId);
    }
  }, [currentChatId, finalizeCreation]);

  // Auto-resize textarea (grows downward only)
  const handleAutoResize = React.useCallback(() => {
    const ta = taRef.current;
    if (!ta) return;

    // Reset height to recalculate
    ta.style.height = "auto";
    const scrollHeight = ta.scrollHeight;

    // Calculate new height (clamped between MIN and MAX)
    const newHeight = Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, scrollHeight));
    setTextareaHeight(newHeight);
    ta.style.height = `${newHeight}px`;
  }, []);

  // Auto-resize on value change
  React.useEffect(() => {
    handleAutoResize();
  }, [value, handleAutoResize]);

  // Finalize creation on mount if current chat is optimistic
  React.useEffect(() => {
    if (currentChatId && currentChatId.startsWith("temp-")) {
      finalizeCreation(currentChatId);
    }
  }, [currentChatId, finalizeCreation]);

  // Reset isSubmitting when currentChatId changes (switching conversations)
  React.useEffect(() => {
    setIsSubmitting(false);
  }, [currentChatId]);

  // Reset isSubmitting when value is cleared from parent (after successful submit)
  React.useEffect(() => {
    if (value === "") {
      setIsSubmitting(false);
    }
  }, [value]);

  // Reset isSubmitting when loading completes (backend finished processing)
  const prevLoadingRef = React.useRef(loading);
  React.useEffect(() => {
    if (prevLoadingRef.current === true && loading === false) {
      setIsSubmitting(false);
    }
    prevLoadingRef.current = loading;
  }, [loading]);

  // Submit with animation (must be defined before handleKeyDown)
  const handleSendClick = React.useCallback(async () => {
    if (!value.trim() || disabled || loading || isSubmitting) return;

    setIsSubmitting(true);

    try {
      // Brief animation before submit (120ms)
      await new Promise((resolve) => setTimeout(resolve, 120));

      await onSubmit();

      // Reset state after submit
      setTextareaHeight(MIN_HEIGHT);

      // Re-focus textarea after brief delay
      setTimeout(() => {
        taRef.current?.focus();
      }, 80);
    } catch (error) {
      // If submit fails, ensure we reset isSubmitting
      setIsSubmitting(false);
    }
    // Note: Don't reset isSubmitting here on success - let useEffects handle it
    // This prevents race conditions with parent state updates
  }, [value, disabled, loading, isSubmitting, onSubmit]);

  // Handle Enter key (submit) and Shift+Enter (newline)
  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (value.trim() && !disabled && !loading && !isSubmitting) {
          handleSendClick();
        }
      }

      if (e.key === "Escape") {
        if (showToolsMenu) {
          setShowToolsMenu(false);
          return;
        }
        if (showCancel && onCancel) {
          onCancel();
        }
      }
    },
    [
      value,
      disabled,
      loading,
      isSubmitting,
      showToolsMenu,
      showCancel,
      onCancel,
      handleSendClick,
    ],
  );

  const canSubmit =
    value.trim().length > 0 && !disabled && !loading && !isSubmitting;

  // Close menu on click outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!composerRef.current?.contains(event.target as Node)) {
        setShowToolsMenu(false);
      }
    };

    if (showToolsMenu) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showToolsMenu]);

  const handleToolSelect = React.useCallback(
    (id: ToolId) => {
      // Special handling for 'add-files': Open file picker
      if (id === "add-files" || id === "files") {
        fileInputRef.current?.click();
        setShowToolsMenu(false);
        return;
      }

      // For other tools, call onAddTool if provided
      if (onAddTool) {
        onAddTool(id);
      }
      setShowToolsMenu(false);
    },
    [onAddTool],
  );

  // Handle file selection
  const handleFileChange = React.useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const files = event.target.files;
      if (!files || files.length === 0) return;

      logDebug("[chat.composer] Files selected", { count: files.length });

      // Process files
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const filename = file.name;

        // Validate file type (PDF, PNG, JPG only)
        const allowedTypes = [
          "application/pdf",
          "image/png",
          "image/jpeg",
          "image/jpg",
        ];
        if (!allowedTypes.includes(file.type)) {
          alert(
            `Archivo no soportado: ${filename}. Solo se permiten PDF, PNG, JPG.`,
          );
          continue;
        }

        // Validate file size (max 30MB)
        const maxSize = 30 * 1024 * 1024; // 30MB
        if (file.size > maxSize) {
          alert(`Archivo muy grande: ${filename}. Máximo 30MB.`);
          continue;
        }

        // Start upload with progress
        setUploadingFiles((prev) => new Map(prev).set(filename, 0));

        try {
          // For PDFs, use document review flow (creates persistent message in chat)
          if (file.type === "application/pdf") {
            logDebug("[chat.composer] Uploading PDF via document review", {
              filename,
            });

            const metadata = await uploadFile(file, currentChatId || undefined);

            if (metadata) {
              logDebug("[chat.composer] PDF uploaded and message created", {
                filename,
                docId: metadata.docId,
              });
            }
          } else {
            // For images, use regular attachment flow
            const response = await apiClient.uploadDocument(file, {
              conversationId: currentChatId || undefined,
              onProgress: (progress) => {
                setUploadingFiles((prev) =>
                  new Map(prev).set(filename, progress),
                );
              },
            });

            // Add to attachments using document_id from response
            if (onAttachmentsChange) {
              const newAttachment: ChatComposerAttachment = {
                id: response.document_id ?? response.doc_id,
                file,
                name: response.filename,
                size: response.size_bytes,
                type: file.type,
                progress: 100,
                status: "completed",
              };
              onAttachmentsChange([...(attachments || []), newAttachment]);
            }

            logDebug("[chat.composer] Image uploaded successfully", {
              filename,
              doc_id: response.document_id,
            });
          }

          // Remove from uploading
          setUploadingFiles((prev) => {
            const next = new Map(prev);
            next.delete(filename);
            return next;
          });
        } catch (error: any) {
          console.error("Upload failed:", error);
          const errorMsg =
            error?.response?.data?.detail ||
            error?.message ||
            "Error desconocido";
          alert(`Error al subir ${filename}: ${errorMsg}`);
          setUploadingFiles((prev) => {
            const next = new Map(prev);
            next.delete(filename);
            return next;
          });
        }
      }

      // Reset file input
      event.target.value = "";
    },
    [attachments, onAttachmentsChange, currentChatId, uploadFile],
  );

  const isCenter = layout === "center";

  return (
    <div
      className={cn(isCenter ? "w-full" : "sticky bottom-0 w-full", className)}
    >
      {/* Outer wrapper: horizontal centering + responsive padding */}
      <div
        className={cn(
          "mx-auto w-full",
          isCenter ? "max-w-[640px]" : "max-w-3xl px-4 pb-4",
        )}
      >
        <div ref={composerRef} className="relative">
          {/* Tool Menu */}
          <AnimatePresence>
            {showToolsMenu && (
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 4, scale: 0.98 }}
                transition={{ duration: 0.14, ease: [0.16, 1, 0.3, 1] }}
                className="absolute bottom-full left-0 z-[9999] mb-2 pointer-events-auto"
              >
                <ToolMenu
                  onSelect={handleToolSelect}
                  onClose={() => setShowToolsMenu(false)}
                />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Main Composer Container - Minimalist ChatGPT style */}
          <motion.div
            role="form"
            aria-label="Compositor de mensajes"
            className={cn(
              "grid items-end gap-2",
              "rounded-2xl p-2",
              "bg-[var(--surface)]",
              "shadow-sm",
              // Dynamic grid: smaller space when tools hidden, full 44px when shown
              SHOW_TOOLS_BUTTON
                ? "grid-cols-[44px,1fr,44px]"
                : "grid-cols-[8px,1fr,44px]",
            )}
            style={{
              boxShadow: "inset 0 0 0 0.5px var(--hairline)",
            }}
            animate={{
              height: isSubmitting ? MIN_HEIGHT + 16 : "auto", // +16 for padding
            }}
            transition={{ duration: 0.12, ease: "easeOut" }}
          >
            {/* Plus Button (Tools) - Minimal space when hidden (8px), full when shown (44px) */}
            <div
              className={cn(
                "shrink-0",
                SHOW_TOOLS_BUTTON ? "w-11" : "w-2", // 44px when shown, 8px when hidden
                !SHOW_TOOLS_BUTTON && "pointer-events-none",
              )}
            >
              {SHOW_TOOLS_BUTTON && (
                <button
                  type="button"
                  onClick={() => setShowToolsMenu(!showToolsMenu)}
                  disabled={disabled || loading}
                  className={cn(
                    "h-11 w-11 rounded-xl",
                    "grid place-items-center",
                    "text-neutral-300 bg-transparent",
                    "hover:bg-[var(--surface-strong)] active:bg-[var(--surface-strong)]",
                    "transition-colors duration-150",
                    "outline-none ring-0 focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0",
                    (disabled || loading) && "cursor-not-allowed opacity-40",
                  )}
                  aria-label="Abrir herramientas"
                  aria-expanded={showToolsMenu}
                  aria-haspopup="menu"
                >
                  <PlusIcon className="h-5 w-5 opacity-80" />
                </button>
              )}
            </div>

            {/* Auto-grow Textarea - No borders, no focus color change */}
            <div className="min-w-0 flex-1">
              <motion.textarea
                ref={taRef}
                value={value}
                onChange={(e) => {
                  onChange(e.target.value);
                  handleFirstInput(); // Finalize creation on first input
                }}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={disabled || loading}
                maxLength={maxLength}
                rows={1}
                className={cn(
                  "w-full resize-none bg-transparent",
                  "text-[15px] leading-6 text-neutral-100 placeholder:text-neutral-400",
                  "outline-none ring-0 border-0",
                  "focus:outline-none focus:ring-0 focus:border-0 focus:border-transparent",
                  "focus-visible:outline-none focus-visible:ring-0",
                  "overflow-y-auto thin-scroll",
                  "transition-[height] duration-150 ease-out",
                )}
                style={{
                  minHeight: `${MIN_HEIGHT}px`,
                  maxHeight: `${MAX_HEIGHT}px`,
                  height: `${textareaHeight}px`,
                }}
                aria-label="Escribe tu mensaje"
                aria-multiline="true"
                animate={{
                  opacity: isSubmitting ? 0.6 : 1,
                }}
                transition={{ duration: 0.12 }}
              />
            </div>

            {/* Send Button (Arrow Up) or Stop Button - No visible rings */}
            {showCancel && onCancel ? (
              <button
                type="button"
                onClick={onCancel}
                className={cn(
                  "h-11 w-11 shrink-0 rounded-xl",
                  "grid place-items-center",
                  "bg-red-500/20 text-red-300",
                  "hover:bg-red-500/30 active:bg-red-500/40",
                  "transition-colors duration-150",
                  "outline-none ring-0 focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0",
                )}
                aria-label="Detener generación"
              >
                <StopIcon className="h-5 w-5" />
              </button>
            ) : (
              <motion.button
                type="submit"
                onClick={handleSendClick}
                disabled={!canSubmit}
                className={cn(
                  "h-11 w-11 shrink-0 rounded-xl",
                  "grid place-items-center",
                  "transition-all duration-150",
                  "outline-none ring-0 focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0",
                  canSubmit
                    ? "bg-primary text-neutral-900 hover:bg-primary/90 active:scale-95"
                    : "bg-neutral-700/40 text-neutral-500 cursor-not-allowed",
                )}
                aria-label="Enviar mensaje"
                whileTap={canSubmit ? { scale: 0.92 } : {}}
                transition={{ duration: 0.1 }}
              >
                <SendIconArrowUp className="h-5 w-5" />
              </motion.button>
            )}
          </motion.div>

          {/* Tool Chips (below main bar) */}
          <AnimatePresence>
            {selectedTools.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.16, ease: "easeOut" }}
                className="mt-2 overflow-hidden"
              >
                <div className="flex items-center gap-2 overflow-x-auto thin-scroll px-1">
                  {selectedTools.slice(0, 4).map((id) => {
                    const tool = TOOL_REGISTRY[id];
                    if (!tool) return null;
                    const Icon = tool.Icon;
                    return (
                      <motion.div
                        key={id}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        transition={{ duration: 0.12 }}
                        className={cn(
                          "group flex h-9 items-center gap-2 shrink-0",
                          "rounded-xl border border-primary/60 bg-primary/15 pl-2 pr-1",
                          "text-primary",
                          "transition-colors hover:bg-primary/25",
                        )}
                        title={tool.label}
                      >
                        <Icon className="h-4 w-4" />
                        <span className="text-sm font-medium">
                          {tool.label}
                        </span>
                        <button
                          type="button"
                          aria-label={`Quitar ${tool.label}`}
                          onClick={() => onRemoveTool?.(id)}
                          className={cn(
                            "grid place-items-center rounded-lg p-1",
                            "text-primary hover:bg-primary/20",
                            "transition-colors",
                          )}
                        >
                          <CloseIcon className="h-3.5 w-3.5" />
                        </button>
                      </motion.div>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* File Upload Cards with Progress */}
          <AnimatePresence>
            {(uploadingFiles.size > 0 ||
              (attachments && attachments.length > 0)) && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.16, ease: "easeOut" }}
                className="mt-2 overflow-hidden"
              >
                <div className="space-y-2">
                  {/* Uploading files */}
                  {Array.from(uploadingFiles.entries()).map(
                    ([filename, progress]) => (
                      <motion.div
                        key={`uploading-${filename}`}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -8 }}
                        transition={{ duration: 0.2 }}
                        className="rounded-lg border border-zinc-700/60 bg-zinc-800/60 p-3"
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-zinc-700/60">
                            <svg
                              className="h-5 w-5 text-zinc-400"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                              />
                            </svg>
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-zinc-200 truncate">
                              {filename}
                            </p>
                            <div className="mt-1 flex items-center gap-2">
                              <div className="flex-1 h-1.5 bg-zinc-700/60 rounded-full overflow-hidden">
                                <motion.div
                                  className="h-full bg-primary"
                                  initial={{ width: 0 }}
                                  animate={{ width: `${progress}%` }}
                                  transition={{ duration: 0.2 }}
                                />
                              </div>
                              <span className="text-xs text-zinc-400">
                                {progress}%
                              </span>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    ),
                  )}

                  {/* Uploaded files */}
                  {attachments?.map((attachment) => (
                    <motion.div
                      key={attachment.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.2 }}
                      className="rounded-lg border border-green-500/30 bg-green-500/10 p-3"
                    >
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/20">
                          <svg
                            className="h-5 w-5 text-green-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                            />
                          </svg>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-zinc-200 truncate">
                            {attachment.name}
                          </p>
                          <p className="text-xs text-zinc-400">
                            {(attachment.size / 1024).toFixed(0)} KB · Listo
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            const filtered = attachments.filter(
                              (a) => a.id !== attachment.id,
                            );
                            onAttachmentsChange?.(filtered);
                          }}
                          className="grid place-items-center rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-700/60 transition-colors"
                          aria-label="Eliminar archivo"
                        >
                          <CloseIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Files V1 Section */}
          {onAddFilesV1Attachment && (
            <AnimatePresence>
              {(filesV1Attachments.length > 0 || useFilesInQuestion) && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.16, ease: "easeOut" }}
                  className="mt-3 space-y-3"
                >
                  {/* Upload Button and Toggle */}
                  <div className="flex items-center gap-3">
                    {onAddFilesV1Attachment && (
                      <FileUploadButton
                        conversationId={conversationId}
                        onUploadComplete={(newAttachments) => {
                          newAttachments.forEach(onAddFilesV1Attachment);
                          // Auto-enable toggle when files are uploaded
                          if (
                            newAttachments.length > 0 &&
                            onToggleFilesInQuestion
                          ) {
                            onToggleFilesInQuestion(true);
                          }
                        }}
                        maxFiles={5}
                        variant="outline"
                        size="sm"
                      />
                    )}

                    {filesV1Attachments.length > 0 &&
                      onToggleFilesInQuestion && (
                        <FilesToggle
                          enabled={useFilesInQuestion}
                          onChange={onToggleFilesInQuestion}
                          fileCount={filesV1Attachments.length}
                        />
                      )}
                  </div>

                  {/* File Attachments List */}
                  {filesV1Attachments.length > 0 &&
                    onRemoveFilesV1Attachment && (
                      <FileAttachmentList
                        attachments={filesV1Attachments}
                        onRemove={onRemoveFilesV1Attachment}
                      />
                    )}
                </motion.div>
              )}
            </AnimatePresence>
          )}

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            multiple
            onChange={handleFileChange}
            className="hidden"
            aria-label="Seleccionar archivos"
          />
        </div>
      </div>
    </div>
  );
}
