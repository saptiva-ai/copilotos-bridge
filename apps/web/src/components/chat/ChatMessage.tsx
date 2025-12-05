"use client";

import * as React from "react";
import { cn, formatRelativeTime, copyToClipboard } from "../../lib/utils";
import { logDebug } from "../../lib/logger";
import { Button, Badge } from "../ui";
import { StreamingMessage } from "./StreamingMessage";
import { FileReviewMessage } from "./FileReviewMessage";
import { MessageAuditCard } from "./MessageAuditCard";
import { BankChartMessage } from "./BankChartMessage";
import { BankAdvisorResponse } from "./BankAdvisorResponse";
import { PreviewAttachment } from "./PreviewAttachment";
import { featureFlags } from "../../lib/feature-flags";
import type {
  ChatMessage as ChatMessageType,
  ChatMessageKind,
  FileReviewData,
  BankChartData,
} from "../../lib/types";
import type { ToolInvocation } from "@/lib/types";
import type { FileAttachment } from "../../types/files";
import { ArtifactCard } from "./artifact-card";
import { parseToolCalls } from "../../lib/tool-parser";
import { AuditSummaryCard } from "./artifacts/AuditSummaryCard";
import { useCanvasStore } from "@/lib/stores/canvas-store";
import {
  ChartBarIcon,
  ArrowsPointingOutIcon,
} from "@heroicons/react/24/outline";

export interface ChatMessageProps {
  id?: string;
  role: "user" | "assistant" | "system";
  kind?: ChatMessageKind;
  content: string;
  timestamp?: Date | string;
  model?: string;
  status?: "sending" | "delivered" | "error" | "streaming";
  tokens?: number;
  latencyMs?: number;
  isStreaming?: boolean;
  task_id?: string;
  metadata?: {
    research_task?: {
      id: string;
      status: string;
      progress?: number;
      created_at: string;
      updated_at: string;
      estimated_completion?: string;
      [key: string]: any;
    };
    tool_invocations?: ToolInvocation[];
    [key: string]: any;
  };
  review?: FileReviewData;
  onCopy?: (text: string) => void;
  onRetry?: (messageId: string) => void;
  onRegenerate?: (messageId: string) => void;
  onStop?: () => void;
  onViewReport?: (taskId: string, taskTitle: string) => void;
  onViewAuditReport?: (
    validationReportId: string,
    documentId: string,
    filename?: string,
  ) => void;
  onReAuditDocument?: (
    documentId: string,
    jobId?: string,
    filename?: string,
  ) => void;
  className?: string;
  // Additional props for UX-005
  isError?: boolean;
  latency?: number;
  artifact?: any;
}

export function ChatMessage({
  id,
  role,
  kind,
  content,
  timestamp,
  model,
  status = "delivered",
  tokens,
  latencyMs,
  isStreaming = false,
  task_id,
  metadata,
  review,
  onCopy,
  onRetry,
  onRegenerate,
  onStop,
  onViewReport,
  onViewAuditReport,
  onReAuditDocument,
  className,
  isError = false,
  latency,
  artifact,
}: ChatMessageProps) {
  const [copied, setCopied] = React.useState(false);

  // 🆕 Canvas highlight synchronization (Phase 2)
  const activeMessageId = useCanvasStore((state) => state.activeMessageId);
  const isActiveInCanvas = activeMessageId === id;

  const isFileReview = kind === "file-review";

  const isUser = role === "user";
  const isSystem = role === "system";
  const isAssistant = role === "assistant";

  // Parse inline tool calls from content
  const { content: displayContent, toolInvocations: inlineToolInvocations } =
    React.useMemo(() => parseToolCalls(content), [content]);

  const toolInvocations = React.useMemo(() => {
    const metadataTools = Array.isArray((metadata as any)?.tool_invocations)
      ? ((metadata as any).tool_invocations as ToolInvocation[])
      : [];
    return [...metadataTools, ...inlineToolInvocations];
  }, [metadata, inlineToolInvocations]);

  const artifactInvocations = toolInvocations.filter(
    (inv) =>
      inv &&
      typeof inv === "object" &&
      inv.tool_name === "create_artifact" &&
      inv.result?.id,
  );

  // State for artifact data (BA-P0-003: Load bank_chart artifacts)
  const [artifactData, setArtifactData] = React.useState<Record<string, any>>(
    {},
  );

  // Fetch artifact content for bank_chart types
  React.useEffect(() => {
    const fetchArtifacts = async () => {
      console.warn(
        "[🎨 ARTIFACTS] Checking artifact invocations:",
        artifactInvocations,
      );
      for (const inv of artifactInvocations) {
        const artifactId = inv.result?.id as string;
        const artifactType = inv.result?.type as string;

        console.warn(
          `[🎨 ARTIFACTS] Found artifact: type=${artifactType}, id=${artifactId}`,
        );

        // Only fetch if it's a bank_chart and we haven't loaded it yet
        if (
          artifactType === "bank_chart" &&
          artifactId &&
          !artifactData[artifactId]
        ) {
          try {
            console.warn(
              `[📊 BANK_CHART] Fetching artifact content for ${artifactId}`,
            );
            const response = await fetch(`/api/artifacts/${artifactId}`);
            if (response.ok) {
              const data = await response.json();
              console.warn(
                `[📊 BANK_CHART] Artifact content loaded:`,
                data.content,
              );
              setArtifactData((prev) => ({
                ...prev,
                [artifactId]: data.content,
              }));
            } else {
              console.error(
                `[📊 BANK_CHART] Failed to fetch artifact: ${response.status} ${response.statusText}`,
              );
            }
          } catch (error) {
            console.error(
              `[📊 BANK_CHART] Error fetching artifact ${artifactId}:`,
              error,
            );
          }
        }
      }
    };

    if (artifactInvocations.length > 0) {
      fetchArtifacts();
    }
  }, [artifactInvocations, artifactData]);

  React.useEffect(() => {
    if (isUser) {
      logDebug("[ChatMessage] Rendering user message", {
        id,
        hasMetadata: !!metadata,
        metadata,
        file_ids: metadata?.file_ids,
        files: metadata?.files,
        shouldShowIndicator: !!(
          metadata?.file_ids && metadata.file_ids.length > 0
        ),
      });
    }
  }, [isUser, metadata, id]);

  // Render file review message if kind === 'file-review'
  if (isFileReview) {
    const message: ChatMessageType = {
      id: id || "",
      role,
      kind,
      content,
      timestamp: timestamp || new Date(),
      review,
    };
    return <FileReviewMessage message={message} />;
  }

  // Check for bank_chart kind (BA-P0-002)
  const isBankChart =
    kind === "bank_chart" || (artifact as any)?.type === "bank_chart";
  const bankChartData: BankChartData | null = isBankChart
    ? (artifact as BankChartData) ||
      (metadata?.artifact as BankChartData) ||
      (metadata?.bank_chart_data as BankChartData)
    : (metadata?.bank_chart_data as BankChartData) || null;

  // Debug logging for bank chart data
  // Log every assistant message render to debug missing button issue
  if (isAssistant) {
    console.warn("[🔍 BANK_CHART DEBUG] Assistant message render:", {
      messageId: id,
      hasMetadata: !!metadata,
      hasBankChartData: !!metadata?.bank_chart_data,
      bankChartDataResolved: !!bankChartData,
      willRenderButton: isAssistant && !!bankChartData,
      metadataKeys: metadata ? Object.keys(metadata) : [],
      isStreaming,
      status,
    });
  }
  if (metadata?.bank_chart_data) {
    console.warn("[🔍 BANK_CHART DEBUG] Found bank_chart_data in metadata:", {
      isBankChart,
      hasData: !!bankChartData,
      isAssistant,
      willRender: isAssistant && !!bankChartData,
      plotlyData: metadata.bank_chart_data.plotly_config?.data,
      plotlyLayout: metadata.bank_chart_data.plotly_config?.layout,
      fullMetadata: metadata.bank_chart_data,
    });
  }

  // Identify audit messages to append inline audit card after content
  const isAuditMessage =
    featureFlags.auditInline &&
    metadata &&
    typeof metadata === "object" &&
    "validation_report_id" in metadata &&
    metadata.validation_report_id;

  // Prefer artifact at message level; fallback to metadata artifact/decision metadata
  const auditArtifact =
    artifact ||
    (metadata as any)?.artifact ||
    (metadata as any)?.decision_metadata?.audit_artifact ||
    (metadata as any)?.audit_artifact;
  const auditDisplayName =
    (auditArtifact as any)?.metadata?.display_name ||
    (auditArtifact as any)?.metadata?.filename ||
    (auditArtifact as any)?.doc_name;

  const handleCopy = async () => {
    const success = await copyToClipboard(displayContent);
    if (success) {
      setCopied(true);
      onCopy?.(displayContent);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getStatusBadge = () => {
    switch (status) {
      case "sending":
        return (
          <Badge variant="info" size="sm">
            Enviando...
          </Badge>
        );
      case "streaming":
        return null; // TypingIndicator already shows this in StreamingMessage
      case "error":
        return (
          <Badge variant="error" size="sm">
            Error
          </Badge>
        );
      default:
        return null;
    }
  };

  if (isSystem) {
    return (
      <div className="flex justify-center my-4">
        <div className="bg-gray-100 text-gray-600 px-3 py-1 rounded-full text-sm">
          {displayContent}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "group flex gap-3 px-4 py-6 transition-colors duration-150",
        isUser ? "flex-row-reverse" : "flex-row",
        "hover:bg-surface-2/50",
        className,
      )}
      role="article"
      aria-label={`${isUser ? "Mensaje del usuario" : "Respuesta del asistente"} - ${formatRelativeTime(timestamp || new Date())}`}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-medium uppercase",
          isUser ? "bg-primary/20 text-primary" : "bg-muted/20 text-muted",
        )}
      >
        {isUser ? "Tú" : "AI"}
      </div>

      {/* Message content */}
      {/*
        LAYOUT FIX: Flex child with min-w-0 to allow shrinking below content size
        This prevents code blocks from pushing the message container wider than available space
      */}
      <div
        className={cn("flex-1 min-w-0", isUser ? "text-right" : "text-left")}
      >
        {/* Removed: Header with "Usuario Just now" and "Saptiva Turbo Just now" for minimal UI */}

        {/* File attachments thumbnails ABOVE user message */}
        {isUser && metadata?.files && metadata.files.length > 0 && (
          <div
            className={cn(
              "mb-3 flex gap-2",
              isUser ? "justify-end" : "justify-start",
            )}
          >
            {metadata.files.map((file: any, index: number) => {
              // Convert file metadata to FileAttachment format
              const attachment: FileAttachment = {
                file_id: file.file_id || `file-${index}`,
                filename: file.filename || `Archivo ${index + 1}`,
                mimetype:
                  file.content_type ||
                  file.mimetype ||
                  "application/octet-stream",
                bytes: file.bytes || file.size || 0,
                pages: file.pages,
                status: "READY",
              };

              return (
                <PreviewAttachment
                  key={attachment.file_id}
                  attachment={attachment}
                  className="w-32 h-48"
                  showAuditButton={false}
                />
              );
            })}
          </div>
        )}

        {/*
          LAYOUT FIX: Message bubble container
          - Changed inline-flex → flex to establish proper block-level flex container
          - Kept max-w-full to respect parent boundaries
          - Added w-full to ensure bubble takes available width and can constrain children
          - This prevents code blocks from escaping the bubble
        */}
        <div
          className={cn(
            "flex w-full max-w-full flex-col rounded-3xl px-5 py-4 text-left text-sm leading-relaxed",
            isUser
              ? "bg-primary/15 text-foreground"
              : "bg-surface text-foreground",
            isError && "bg-danger/5",
          )}
          style={
            isUser
              ? {
                  boxShadow:
                    "inset 0 0 0 0.5px rgba(73, 247, 217, 0.4), 0 0 12px rgba(73, 247, 217, 0.15)",
                }
              : {
                  boxShadow: "inset 0 0 0 0.5px var(--hairline)",
                }
          }
          role="region"
          aria-label="Contenido del mensaje"
        >
          <div
            className={cn(
              "min-w-0 break-words",
              !isAssistant && "whitespace-pre-wrap",
            )}
          >
            {isAssistant ? (
              <StreamingMessage
                content={displayContent}
                isStreaming={isStreaming}
                isComplete={status === "delivered"}
              />
            ) : (
              displayContent
            )}
          </div>
        </div>

        {/* Inline audit card after the assistant's summary */}
        {isAssistant && isAuditMessage && (
          <div className="mt-3">
            <MessageAuditCard
              metadata={metadata as any}
              onViewFull={() =>
                onViewAuditReport?.(
                  metadata?.validation_report_id as string,
                  metadata?.document_id as string,
                  (metadata as any)?.filename as string | undefined,
                )
              }
              onReAudit={() =>
                onReAuditDocument?.(
                  metadata?.document_id as string,
                  metadata?.job_id as string | undefined,
                  (metadata as any)?.filename as string | undefined,
                )
              }
            />
          </div>
        )}

        {/* Structured audit summary card when artifact is present */}
        {isAssistant &&
          auditArtifact &&
          ((auditArtifact as any).type === "audit_report_ui" ||
            !(auditArtifact as any).type) && (
            <div className="mt-3">
              <AuditSummaryCard
                data={{
                  // Use artifact root directly (it now has complete AuditReportResponse structure)
                  doc_name: (auditArtifact as any).doc_name || "",
                  stats: (auditArtifact as any).stats || {
                    critical: 0,
                    high: 0,
                    medium: 0,
                    low: 0,
                    total: 0,
                  },
                  categories: (auditArtifact as any).categories || {},
                  actions: (auditArtifact as any).actions || [],
                  metadata: {
                    ...((auditArtifact as any).metadata || {}),
                    // Surface PDF report URL/attachments from message metadata if artifact lacks them
                    report_pdf_url:
                      (auditArtifact as any)?.metadata?.report_pdf_url ||
                      (metadata as any)?.decision_metadata?.report_pdf_url ||
                      (metadata as any)?.report_pdf_url,
                    attachments:
                      (auditArtifact as any)?.metadata?.attachments ||
                      (metadata as any)?.decision_metadata?.attachments ||
                      (metadata as any)?.attachments,
                    display_name: auditDisplayName,
                  },
                }}
                className={cn(isUser ? "ml-auto max-w-lg" : "max-w-lg")}
              />
            </div>
          )}

        {/* Bank chart visualization - Structured response with SQL and Canvas button */}
        {isAssistant && bankChartData && (
          <BankAdvisorResponse
            bankChartData={bankChartData}
            messageId={id || "unknown"}
            metadata={metadata as any}
            className={isUser ? "ml-auto" : ""}
          />
        )}

        {/* Artifact cards should appear after the assistant's summary (and audit card) */}
        {artifactInvocations.length > 0 && (
          <div
            className={cn(
              "mt-3 flex flex-col gap-2",
              isUser ? "items-end" : "items-start",
            )}
          >
            {artifactInvocations.map((inv) => {
              const artifactId = (inv.result?.id as string) || "";
              const artifactType = (inv.result?.type as any) || "markdown";
              const content = artifactData[artifactId];

              console.warn(
                `[🎨 RENDER] Rendering artifact card: id=${artifactId}, type=${artifactType}, hasContent=${!!content}`,
              );

              return (
                <ArtifactCard
                  key={artifactId || inv.tool_name}
                  id={artifactId}
                  title={(inv.result?.title as string) || "Artefacto"}
                  type={artifactType}
                  content={content}
                />
              );
            })}
          </div>
        )}

        {/* Removed: Footer with "XXX tokens Saptiva Turbo" for minimal UI */}
        {/* Only show error retry button */}
        {status === "error" && onRetry && id && (
          <div
            className={cn(
              "mt-2 flex items-center",
              isUser ? "justify-end" : "justify-start",
            )}
          >
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRetry(id)}
              className="px-2 text-xs font-medium text-danger hover:text-danger/80"
            >
              Reintentar
            </Button>
          </div>
        )}

        {/* Actions (visible on hover or when streaming) - UX-005 */}
        <div
          className={cn(
            "mt-2 flex items-center gap-1 transition-opacity duration-150",
            isStreaming ? "opacity-100" : "opacity-0 group-hover:opacity-100",
            isUser ? "justify-end" : "justify-start",
          )}
        >
          {/* Stop button when streaming */}
          {isStreaming && onStop && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onStop}
              className="px-2 text-xs font-bold uppercase tracking-wide text-danger hover:text-danger/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger/60 focus-visible:ring-offset-1 focus-visible:ring-offset-surface"
              aria-label="Detener generación de respuesta"
            >
              <svg
                className="h-3 w-3 mr-1"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
              Stop
            </Button>
          )}

          {/* Copy button */}
          {!isStreaming && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="px-2 text-xs font-bold uppercase tracking-wide text-saptiva-light/60 hover:text-saptiva-mint focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-1 focus-visible:ring-offset-surface"
              aria-label={
                copied ? "Texto copiado al portapapeles" : "Copiar mensaje"
              }
            >
              {copied ? (
                <>
                  <svg
                    className="h-3 w-3 mr-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  Copiado
                </>
              ) : (
                <>
                  <svg
                    className="h-3 w-3 mr-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                    />
                  </svg>
                  Copy
                </>
              )}
            </Button>
          )}

          {/* Regenerate button for assistant messages */}
          {isAssistant && !isStreaming && onRegenerate && id && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRegenerate(id)}
              className="px-2 text-xs font-bold uppercase tracking-wide text-saptiva-light/60 hover:text-saptiva-mint focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-1 focus-visible:ring-offset-surface"
              aria-label="Regenerar respuesta"
            >
              <svg
                className="h-3 w-3 mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Regenerate
            </Button>
          )}

          {/* Research report button */}
          {task_id &&
            metadata?.research_task &&
            onViewReport &&
            !isStreaming && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  onViewReport(task_id, displayContent.slice(0, 50) + "...")
                }
                className="px-2 text-xs font-bold uppercase tracking-wide text-saptiva-light/60 hover:text-saptiva-mint focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-1 focus-visible:ring-offset-surface"
                aria-label={`Ver reporte de investigación: ${metadata?.research_task?.status}`}
              >
                <svg
                  className="h-3 w-3 mr-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                Report ({metadata.research_task.status})
              </Button>
            )}
        </div>
      </div>
    </div>
  );
}
