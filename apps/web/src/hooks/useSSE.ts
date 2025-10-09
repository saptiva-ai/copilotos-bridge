/**
 * useSSE - Hook for Server-Sent Events (SSE) connection
 *
 * Manages EventSource connection for real-time review progress updates
 * Integrates with chat store to update file review messages
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { useApiClient } from "../lib/api-client";
import { useChatStore } from "../lib/stores/chat-store";
import { logDebug } from "../lib/logger";
import type { ReviewStage } from "../lib/types";

export interface SSEEvent {
  jobId: string;
  status: string;
  progress: number;
  currentStage?: string;
  message?: string;
  timestamp: string;
}

export interface UseSSEReturn {
  isConnected: boolean;
  lastEvent: SSEEvent | null;
  error: string | null;
  reconnect: () => void;
  disconnect: () => void;
}

export function useSSE(
  jobId: string | null,
  docId: string | null,
  enabled: boolean = true,
): UseSSEReturn {
  const apiClient = useApiClient();
  const { findFileReviewMessage, updateFileReviewMessage } = useChatStore();
  const eventSourceRef = useRef<EventSource | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const [error, setError] = useState<string | null>(null);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  const connect = useCallback(() => {
    if (!jobId || !enabled) return;

    // Close existing connection
    disconnect();

    const token = apiClient.getToken();
    if (!token) {
      setError("No authentication token");
      return;
    }

    try {
      // Create EventSource with auth token in URL (EventSource doesn't support custom headers)
      const url = `/api/review/events/${jobId}?token=${encodeURIComponent(token)}`;
      const eventSource = new EventSource(url);

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
        logDebug("[SSE] Connected", { jobId });
      };

      eventSource.addEventListener("status", (event) => {
        try {
          const data = JSON.parse(event.data) as SSEEvent;
          setLastEvent(data);
          logDebug("[SSE] Status update", data);

          // Update file review message in store
          if (docId) {
            const message = findFileReviewMessage(docId);
            if (message) {
              const newStages = [...(message.review?.stages || [])];

              // Add new stage if not already present
              if (!newStages.includes(data.status as ReviewStage)) {
                newStages.push(data.status as ReviewStage);
              }

              // Map SSE status to FileReviewStatus
              let fileStatus:
                | "uploading"
                | "uploaded"
                | "processing"
                | "ready"
                | "reviewing"
                | "completed"
                | "error";
              if (data.status === "READY") {
                fileStatus = "completed";
              } else if (data.status === "FAILED") {
                fileStatus = "error";
              } else if (
                ["QUEUED", "RECEIVED", "EXTRACT"].includes(data.status)
              ) {
                fileStatus = "processing";
              } else {
                fileStatus = "reviewing";
              }

              updateFileReviewMessage(message.id, {
                jobId: data.jobId,
                stages: newStages,
                status: fileStatus,
                progress: data.progress,
                currentStage: data.currentStage,
                errors: data.message ? [data.message] : undefined,
              });
            }
          }

          // Auto-disconnect when review is complete
          if (
            data.status === "READY" ||
            data.status === "FAILED" ||
            data.status === "CANCELLED"
          ) {
            setTimeout(() => {
              disconnect();
            }, 1000);
          }
        } catch (err) {
          console.error("[SSE] Failed to parse event data", err);
        }
      });

      eventSource.onerror = (err) => {
        console.error("[SSE] Connection error", err);
        setError("Connection lost");
        setIsConnected(false);

        // Don't auto-reconnect, let user decide
        disconnect();
      };

      eventSourceRef.current = eventSource;
    } catch (err: any) {
      setError(err.message || "Failed to connect");
      console.error("[SSE] Failed to create EventSource", err);
    }
  }, [
    jobId,
    enabled,
    apiClient,
    disconnect,
    docId,
    findFileReviewMessage,
    updateFileReviewMessage,
  ]);

  const reconnect = useCallback(() => {
    disconnect();
    setTimeout(connect, 100);
  }, [disconnect, connect]);

  // Connect/disconnect based on jobId and enabled
  useEffect(() => {
    if (jobId && enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [jobId, enabled, connect, disconnect]);

  return {
    isConnected,
    lastEvent,
    error,
    reconnect,
    disconnect,
  };
}
