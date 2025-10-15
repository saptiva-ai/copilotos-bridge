"use client";

import * as React from "react";
import { Badge } from "../ui/Badge";
import { type FileAttachment, type FileStatus } from "../../types/files";
import { cn } from "../../lib/utils";

export interface FileAttachmentListProps {
  attachments: FileAttachment[];
  onRemove?: (fileId: string) => void;
  className?: string;
}

/**
 * FileAttachmentList - Display list of file attachments
 *
 * Features:
 * - Status indicators (READY, PROCESSING, FAILED)
 * - File metadata (size, pages)
 * - Remove action
 *
 * Usage:
 * ```tsx
 * <FileAttachmentList
 *   attachments={attachments}
 *   onRemove={removeAttachment}
 * />
 * ```
 */
export function FileAttachmentList({
  attachments,
  onRemove,
  className,
}: FileAttachmentListProps) {
  if (attachments.length === 0) {
    return null;
  }

  const formatBytes = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusBadge = (status: FileStatus) => {
    switch (status) {
      case "READY":
        return (
          <Badge variant="success" size="sm" icon={<CheckCircleIcon />}>
            Listo
          </Badge>
        );
      case "PROCESSING":
        return (
          <Badge variant="info" size="sm" icon={<SpinnerIcon />}>
            Procesando
          </Badge>
        );
      case "FAILED":
        return (
          <Badge variant="error" size="sm" icon={<AlertCircleIcon />}>
            Error
          </Badge>
        );
      case "RECEIVED":
        return (
          <Badge variant="secondary" size="sm">
            Recibido
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <div className={cn("space-y-2", className)}>
      {attachments.map((attachment) => (
        <div
          key={attachment.file_id}
          className={cn(
            "flex items-center gap-3 rounded-lg border p-3 transition-colors",
            attachment.status === "READY"
              ? "border-green-200 bg-green-50/50"
              : attachment.status === "FAILED"
                ? "border-red-200 bg-red-50/50"
                : "border-gray-200 bg-gray-50/50",
          )}
        >
          {/* File Icon */}
          <div className="flex-shrink-0">
            <FileIcon mimetype={attachment.mimetype} />
          </div>

          {/* File Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <p className="text-sm font-medium text-gray-900 truncate">
                {attachment.filename}
              </p>
              {getStatusBadge(attachment.status)}
            </div>

            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>{formatBytes(attachment.bytes)}</span>
              {attachment.pages && (
                <>
                  <span>•</span>
                  <span>
                    {attachment.pages} página{attachment.pages !== 1 ? "s" : ""}
                  </span>
                </>
              )}
              {attachment.mimetype && (
                <>
                  <span>•</span>
                  <span className="uppercase">
                    {getMimeLabel(attachment.mimetype)}
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Remove Button */}
          {onRemove && (
            <button
              onClick={() => onRemove(attachment.file_id)}
              className="flex-shrink-0 p-1 rounded-md hover:bg-gray-200 text-gray-500 hover:text-gray-700 transition-colors"
              aria-label={`Eliminar ${attachment.filename}`}
            >
              <XIcon />
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

// Helper Icons
function CheckCircleIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}

function AlertCircleIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg
      className="animate-spin"
      xmlns="http://www.w3.org/2000/svg"
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

interface FileIconProps {
  mimetype?: string;
}

function FileIcon({ mimetype }: FileIconProps) {
  const isPdf = mimetype === "application/pdf";
  const isImage = mimetype?.startsWith("image/");

  if (isPdf) {
    return (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-red-500"
      >
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
        <polyline points="14 2 14 8 20 8" />
      </svg>
    );
  }

  if (isImage) {
    return (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-blue-500"
      >
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <circle cx="8.5" cy="8.5" r="1.5" />
        <polyline points="21 15 16 10 5 21" />
      </svg>
    );
  }

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-gray-500"
    >
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function getMimeLabel(mimetype: string): string {
  if (mimetype === "application/pdf") return "PDF";
  if (mimetype.startsWith("image/")) {
    const ext = mimetype.split("/")[1];
    return ext.toUpperCase();
  }
  return "Archivo";
}
