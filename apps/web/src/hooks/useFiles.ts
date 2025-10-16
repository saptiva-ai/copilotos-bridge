/**
 * useFiles - Hook for Files V1 unified file ingestion
 *
 * MVP-LOCK: Now persists attachments by chatId to survive page refreshes
 *
 * Simplified hook for uploading files to /api/files/upload
 * Handles validation, upload, error mapping, and idempotency
 *
 * See: VALIDATION_REPORT_V1.md for complete specification
 */

import { useState, useCallback, useRef, useEffect } from "react";
import toast from "react-hot-toast";
import { useApiClient } from "../lib/api-client";
import { sha256Hex } from "../lib/hash";
import { logDebug, logError } from "../lib/logger";
import type {
  FileIngestResponse,
  FileIngestBulkResponse,
  FileError,
  UploadProgress,
  FileAttachment,
} from "../types/files";
import {
  validateFile,
  getErrorMessage,
  MAX_UPLOAD_SIZE,
  RATE_LIMIT_UPLOADS_PER_MINUTE,
} from "../types/files";
import { useFilesStore } from "../lib/stores/files-store";

export interface UseFilesReturn {
  // Upload functions
  uploadFile: (
    file: File,
    conversationId?: string,
  ) => Promise<FileAttachment | null>;
  uploadFiles: (
    files: File[],
    conversationId?: string,
  ) => Promise<FileAttachment[]>;

  // State
  isUploading: boolean;
  uploadProgress: UploadProgress | null;
  error: string | null;
  clearError: () => void;

  // Attachments management
  attachments: FileAttachment[];
  addAttachment: (attachment: FileAttachment) => void;
  removeAttachment: (fileId: string) => void;
  clearAttachments: () => void;
}

/**
 * MVP-LOCK: Hook now accepts optional chatId for persistent storage
 * @param chatId - Optional conversation ID to persist attachments (defaults to "draft")
 */
export function useFiles(chatId?: string): UseFilesReturn {
  const apiClient = useApiClient();
  const filesStore = useFilesStore();

  // Use "draft" as fallback when no chatId is provided
  const effectiveChatId = chatId || "draft";

  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  // MVP-LOCK: Initialize attachments from persistent store
  const [attachments, setAttachments] = useState<FileAttachment[]>(() => {
    return filesStore.getForChat(effectiveChatId);
  });

  // MVP-LOCK: Sync with persistent store when chatId changes
  useEffect(() => {
    const storedAttachments = filesStore.getForChat(effectiveChatId);

    setAttachments(storedAttachments);
    logDebug("[useFiles] Loaded attachments from store", {
      chatId: effectiveChatId,
      count: storedAttachments.length,
    });
  }, [effectiveChatId, filesStore]);

  // Rate limit tracking (client-side, informational only)
  const uploadTimestamps = useRef<number[]>([]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // MVP-LOCK: Sync with persistent store
  const addAttachment = useCallback(
    (attachment: FileAttachment) => {
      setAttachments((prev) => [...prev, attachment]);
      filesStore.addToChat(effectiveChatId, attachment);
      logDebug("[useFiles] Added attachment to store", {
        chatId: effectiveChatId,
        file_id: attachment.file_id,
      });
    },
    [effectiveChatId, filesStore],
  );

  // MVP-LOCK: Sync with persistent store
  const removeAttachment = useCallback(
    (fileId: string) => {
      setAttachments((prev) => prev.filter((a) => a.file_id !== fileId));
      filesStore.removeFromChat(effectiveChatId, fileId);
      logDebug("[useFiles] Removed attachment from store", {
        chatId: effectiveChatId,
        file_id: fileId,
      });
    },
    [effectiveChatId, filesStore],
  );

  // MVP-LOCK: Sync with persistent store
  const clearAttachments = useCallback(() => {
    setAttachments([]);
    filesStore.clearForChat(effectiveChatId);
    logDebug("[useFiles] Cleared attachments from store", {
      chatId: effectiveChatId,
    });
  }, [effectiveChatId, filesStore]);

  /**
   * Check client-side rate limit (informational, server enforces)
   */
  const checkClientRateLimit = useCallback((): boolean => {
    const now = Date.now();
    const oneMinuteAgo = now - 60 * 1000;

    // Clean old timestamps
    uploadTimestamps.current = uploadTimestamps.current.filter(
      (ts) => ts > oneMinuteAgo,
    );

    // Check if we've hit the limit
    if (uploadTimestamps.current.length >= RATE_LIMIT_UPLOADS_PER_MINUTE) {
      return false; // Rate limited
    }

    return true; // OK to upload
  }, []);

  /**
   * Track upload for client-side rate limiting
   */
  const trackUpload = useCallback(() => {
    uploadTimestamps.current.push(Date.now());
  }, []);

  /**
   * Upload a single file
   */
  const uploadFile = useCallback(
    async (
      file: File,
      conversationId?: string,
    ): Promise<FileAttachment | null> => {
      setError(null);

      // Client-side validation
      const validation = validateFile(file);
      if (!validation.valid) {
        setError(validation.error!);
        logError("[useFiles] Validation failed", {
          filename: file.name,
          error: validation.error,
        });
        return null;
      }

      // Client-side rate limit check (informational)
      if (!checkClientRateLimit()) {
        setError(
          `Demasiados archivos subidos. Espera un minuto. (${RATE_LIMIT_UPLOADS_PER_MINUTE} máximo por minuto)`,
        );
        logError("[useFiles] Client rate limit exceeded", {
          filename: file.name,
        });
        return null;
      }

      setIsUploading(true);
      setUploadProgress({ loaded: 0, total: file.size, percentage: 0 });

      try {
        // Generate idempotency key from file hash
        const buffer = await file.arrayBuffer();
        const digest = await sha256Hex(buffer);
        const idempotencyKey = `${digest}:${conversationId || "no-chat"}`;

        // Generate trace ID for observability
        const traceId = crypto.randomUUID();

        logDebug("[useFiles] Starting upload", {
          filename: file.name,
          size: file.size,
          type: file.type,
          traceId,
          idempotencyKey,
        });

        // Prepare form data
        const formData = new FormData();
        formData.append("files", file);
        if (conversationId) {
          formData.append("conversation_id", conversationId);
        }

        // Upload to backend
        const response = await fetch("/api/files/upload", {
          method: "POST",
          body: formData,
          headers: {
            Authorization: `Bearer ${apiClient.getToken()}`,
            "X-Trace-Id": traceId,
            "Idempotency-Key": idempotencyKey,
          },
          credentials: "include",
        });

        if (!response.ok) {
          // FE-UX-2: Enhanced error handling with actionable messages
          // Parse error response
          const errorData: { detail?: string; error?: FileError } =
            await response.json().catch(() => ({}));

          // Map backend error to user-friendly message
          if (errorData.error) {
            const userMessage = getErrorMessage(errorData.error);
            throw new Error(userMessage);
          }

          // FE-UX-2: Actionable error messages by status code
          if (response.status === 413) {
            throw new Error(
              `❌ El archivo es demasiado grande. Comprime o divide el PDF antes de subir. Máximo: ${MAX_UPLOAD_SIZE / (1024 * 1024)} MB.`,
            );
          } else if (response.status === 415) {
            throw new Error(
              "❌ Formato no soportado. Usa PDF, PNG, JPG, GIF o HEIC. Si tienes un archivo diferente, conviértelo primero.",
            );
          } else if (response.status === 429) {
            throw new Error(
              `⏸️ Demasiados archivos subidos. Espera 60 segundos e intenta de nuevo. Límite: ${RATE_LIMIT_UPLOADS_PER_MINUTE}/minuto.`,
            );
          } else if (response.status === 410) {
            throw new Error(
              "⚠️ El documento expiró (1 hora de TTL). Sube el archivo nuevamente para incluirlo en el chat.",
            );
          } else if (response.status === 500) {
            throw new Error(
              "🔧 Error del servidor al procesar el archivo. Verifica que el archivo no esté corrupto e intenta de nuevo.",
            );
          } else if (response.status === 503) {
            throw new Error(
              "⏳ Servicio temporalmente no disponible. Intenta de nuevo en unos segundos.",
            );
          }

          throw new Error(
            errorData.detail ||
              `⚠️ Error al subir archivo (código ${response.status}). Intenta de nuevo.`,
          );
        }

        const payload: FileIngestBulkResponse = await response.json();

        if (!payload.files || payload.files.length === 0) {
          throw new Error("Invalid response from server");
        }

        const ingestResponse: FileIngestResponse = payload.files[0];

        // Check if processing failed
        if (ingestResponse.status === "FAILED") {
          const userMessage = ingestResponse.error
            ? getErrorMessage(ingestResponse.error)
            : "Processing failed";
          throw new Error(userMessage);
        }

        setUploadProgress({
          loaded: file.size,
          total: file.size,
          percentage: 100,
        });

        // Track successful upload
        trackUpload();

        logDebug("[useFiles] Upload complete", {
          file_id: ingestResponse.file_id,
          status: ingestResponse.status,
        });

        // Create attachment
        const attachment: FileAttachment = {
          file_id: ingestResponse.file_id,
          filename: ingestResponse.filename || file.name,
          status: ingestResponse.status,
          bytes: ingestResponse.bytes,
          pages: ingestResponse.pages,
          mimetype: ingestResponse.mimetype,
        };

        // MVP-LOCK: Persist to store immediately after successful upload
        const targetChatId = conversationId || effectiveChatId;

        filesStore.addToChat(targetChatId, attachment);

        logDebug("[useFiles] Persisted attachment to store after upload", {
          chatId: targetChatId,
          file_id: attachment.file_id,
        });

        // FE-2 MVP: Toast notification when file is ready
        if (attachment.status === "READY") {
          toast.success(
            `✓ ${attachment.filename} listo para analizar en esta conversación`,
            { duration: 2500 },
          );
        }

        return attachment;
      } catch (err: any) {
        const errorMessage = err.message || "Failed to upload file";
        setError(errorMessage);

        logError("[useFiles] Upload failed", {
          filename: file.name,
          error: errorMessage,
        });

        return null;
      } finally {
        setIsUploading(false);
        setUploadProgress(null);
      }
    },
    [apiClient, checkClientRateLimit, trackUpload, filesStore, effectiveChatId],
  );

  /**
   * Upload multiple files
   */
  const uploadFiles = useCallback(
    async (
      files: File[],
      conversationId?: string,
    ): Promise<FileAttachment[]> => {
      setError(null);

      if (files.length === 0) {
        return [];
      }

      setIsUploading(true);

      const attachments: FileAttachment[] = [];
      let failed = 0;

      for (let i = 0; i < files.length; i++) {
        const file = files[i];

        logDebug("[useFiles] Uploading file", {
          index: i + 1,
          total: files.length,
          filename: file.name,
        });

        const attachment = await uploadFile(file, conversationId);

        if (attachment) {
          attachments.push(attachment);
        } else {
          failed++;
        }

        // Small delay between uploads to avoid overwhelming the server
        if (i < files.length - 1) {
          await new Promise((resolve) => setTimeout(resolve, 500));
        }
      }

      if (failed > 0) {
        setError(
          `${failed} de ${files.length} archivos fallaron. Revisa los detalles.`,
        );
      }

      setIsUploading(false);

      return attachments;
    },
    [uploadFile],
  );

  return {
    uploadFile,
    uploadFiles,
    isUploading,
    uploadProgress,
    error,
    clearError,
    attachments,
    addAttachment,
    removeAttachment,
    clearAttachments,
  };
}
