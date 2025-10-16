"use client";

import * as React from "react";
import { cn } from "../../../lib/utils";
import { useAutosizeTextArea } from "./useAutosizeTextArea";
import { TOOL_REGISTRY, type ToolId } from "@/types/tools";
import { featureFlags } from "../../../lib/feature-flags";
import { useSettingsStore } from "../../../lib/stores/settings-store";
import ToolMenu from "../ToolMenu/ToolMenu";

import { FeatureFlagsResponse } from "@/lib/types";
import { legacyKeyToToolId, toolIdToLegacyKey } from "@/lib/tool-mapping";

export interface ChatComposerAttachment {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  progress: number;
  status: "uploading" | "completed" | "error";
  errorMessage?: string;
}

interface ChatComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void | Promise<void>;
  onCancel?: () => void;
  disabled?: boolean;
  loading?: boolean;
  placeholder?: string;
  maxLength?: number;
  showCancel?: boolean;
  className?: string;
  toolsEnabled?: Record<string, boolean>;
  onToggleTool?: (tool: string) => void;
  attachments?: ChatComposerAttachment[];
  onAttachmentsChange?: (attachments: ChatComposerAttachment[]) => void;
  selectedTools?: ToolId[];
  onRemoveTool?: (id: ToolId) => void;
  onAddTool?: (id: ToolId) => void;
  onOpenTools?: () => void;
  featureFlags?: FeatureFlagsResponse | null;
}

interface ComposerAction {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
}

const COMPOSER_ACTION_ORDER = ["deep_research"];

const ALL_COMPOSER_ACTIONS: ComposerAction[] = [
  {
    id: "deep_research",
    name: "Deep research",
    description: "Investigación profunda con fuentes verificadas",
    icon: <SearchIcon />,
  },
  {
    id: "add_files",
    name: "Add files",
    description: "Adjuntar documentos o imágenes",
    icon: <FileIcon />,
  },
  {
    id: "add_google_drive",
    name: "Add from Google Drive",
    description: "Importar desde Google Drive",
    icon: <DriveIcon />,
  },
  {
    id: "code_analysis",
    name: "Code analysis",
    description: "Analizar fragmentos de código",
    icon: <CodeIcon />,
  },
  {
    id: "document_analysis",
    name: "Document analysis",
    description: "Procesar y extraer de documentos",
    icon: <DocumentIcon />,
  },
  {
    id: "use_connectors",
    name: "Use connectors",
    description: "Conectar con APIs externas",
    icon: <ConnectorIcon />,
  },
];

const MAX_VISIBLE_CHIPS = 4;

const ACCEPTED_FILE_TYPES = [
  "pdf",
  "png",
  "jpg",
  "jpeg",
  "docx",
  "txt",
  "md",
  "csv",
  "json",
  "ipynb",
];
const MAX_FILE_SIZE_MB = 20;
const MAX_FILE_COUNT = 5;

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

const validateFile = (file: File): { valid: boolean; error?: string } => {
  const extension = file.name.split(".").pop()?.toLowerCase();

  if (!extension || !ACCEPTED_FILE_TYPES.includes(extension)) {
    return {
      valid: false,
      error: `Tipo de archivo no permitido. Solo se aceptan: ${ACCEPTED_FILE_TYPES.join(", ")}`,
    };
  }

  if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
    return {
      valid: false,
      error: `Archivo muy grande. Máximo ${MAX_FILE_SIZE_MB}MB`,
    };
  }

  return { valid: true };
};

function SearchIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
    >
      <circle cx="11" cy="11" r="6" strokeWidth="1.8" />
      <line
        x1="16.5"
        y1="16.5"
        x2="20"
        y2="20"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
    >
      <rect x="4" y="3" width="16" height="18" rx="2" strokeWidth="1.8" />
      <path d="M8 7h8" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M8 11h8" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function DriveIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
    >
      <path
        d="M7 3h10l4 7-4 7H7l-4-7 4-7Z"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path d="M7 17h10" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
    >
      <path
        d="m9 9-3 3 3 3"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="m15 9 3 3-3 3"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M10 20h4" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function DocumentIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
    >
      <path
        d="M6 3h9l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"
        strokeWidth="1.8"
      />
      <path
        d="M14 3v5h5"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M8 13h8" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M8 17h5" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function ConnectorIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
    >
      <path d="M9 7h6" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M5 12h14" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M9 17h6" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="5" cy="12" r="2" strokeWidth="1.8" />
      <circle cx="19" cy="12" r="2" strokeWidth="1.8" />
    </svg>
  );
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 6v12" />
      <path d="M18 12H6" />
    </svg>
  );
}

function MicIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x={10} y={4} width={4} height={8} rx={2} />
      <path d="M8 11v1a4 4 0 0 0 8 0v-1" />
      <path d="M12 19v2" />
      <path d="M9 21h6" />
    </svg>
  );
}

function StopIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <rect x={7} y={7} width={10} height={10} rx={2} />
    </svg>
  );
}

function SendIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M5 12h14" />
      <path d="M12 5l7 7-7 7" />
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
    >
      <path d="M6 18L18 6" />
      <path d="M6 6l12 12" />
    </svg>
  );
}

export function ChatComposer({
  value,
  onChange,
  onSubmit,
  onCancel,
  disabled = false,
  loading = false,
  placeholder = "Escribe tu mensaje…",
  maxLength = 10000,
  showCancel = false,
  className,
  toolsEnabled,
  onToggleTool,
  attachments = [],
  onAttachmentsChange,
  selectedTools,
  onRemoveTool,
  onAddTool,
  onOpenTools,
  featureFlags: featureFlagsProp,
}: ChatComposerProps) {
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
  }, [toolVisibilityLoaded, loadToolVisibility]);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const [showToolsMenu, setShowToolsMenu] = React.useState(false);
  const [dragCounter, setDragCounter] = React.useState(0);
  const [isDragOver, setIsDragOver] = React.useState(false);

  useAutosizeTextArea(textareaRef.current, value, 176);

  const composerActions = React.useMemo(() => {
    const flags = featureFlagsProp || featureFlags;
    // Handle both API response (snake_case) and local feature flags (camelCase)
    const isApiResponse = (f: any): f is FeatureFlagsResponse =>
      "deep_research_enabled" in f;

    return ALL_COMPOSER_ACTIONS.filter((action) => {
      if (isApiResponse(flags)) {
        // API response uses snake_case
        switch (action.id) {
          case "deep_research":
            return flags.deep_research_enabled;
          default:
            return false; // API only returns deep research flags
        }
      } else {
        // Local feature flags use camelCase
        switch (action.id) {
          case "deep_research":
            return flags.deepResearch;
          case "add_files":
            return flags.files;
          case "add_google_drive":
            return flags.googleDrive;
          case "code_analysis":
            return flags.agentMode;
          case "document_analysis":
            return flags.canvas;
          case "use_connectors":
            return false;
          default:
            return true;
        }
      }
    });
  }, [featureFlagsProp]);

  const orderedActions = React.useMemo(() => {
    const remainder = composerActions.filter(
      (action) => !COMPOSER_ACTION_ORDER.includes(action.id),
    );
    const prioritized = COMPOSER_ACTION_ORDER.map((id) =>
      composerActions.find((action) => action.id === id),
    ).filter(Boolean) as ComposerAction[];
    return [...prioritized, ...remainder];
  }, [composerActions]);

  const allowAttachments = toolVisibility.files ?? featureFlags.files;
  const showMicButton = featureFlags.mic;

  const canSubmit = value.trim().length > 0 && !disabled && !loading;

  const chipToolIds = React.useMemo<ToolId[]>(() => {
    // Prefer the new selectedTools prop if available (including empty arrays)
    if (selectedTools !== undefined) {
      return selectedTools;
    }

    // Fallback to legacy toolsEnabled only if selectedTools is not passed
    if (toolsEnabled) {
      return Object.entries(toolsEnabled)
        .filter(([, enabled]) => enabled)
        .map(([legacyKey]) => legacyKeyToToolId(legacyKey))
        .filter((id): id is ToolId => {
          if (!id) return false;
          return Boolean(toolVisibility[id]);
        });
    }

    return [];
  }, [selectedTools, toolsEnabled, toolVisibility]);

  const hasActiveTools = chipToolIds.length > 0;
  const visibleToolIds = React.useMemo(
    () => chipToolIds.slice(0, MAX_VISIBLE_CHIPS),
    [chipToolIds],
  );
  const hiddenToolCount =
    chipToolIds.length > MAX_VISIBLE_CHIPS
      ? chipToolIds.length - MAX_VISIBLE_CHIPS
      : 0;

  const handleToggleToolsMenu = React.useCallback(() => {
    setShowToolsMenu((prev) => !prev);
  }, []);

  const handleMicClick = React.useCallback(() => {
    if (disabled || loading) return;
    if (typeof window !== "undefined" && typeof window.alert === "function") {
      window.alert("Funcionalidad aún no disponible");
    }
  }, [disabled, loading]);

  const handleSendClick = React.useCallback(() => {
    if (!canSubmit) return;
    onSubmit();
  }, [canSubmit, onSubmit]);

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (value.trim()) {
          onSubmit();
        }
      }

      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        if (value.trim()) {
          onSubmit();
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
    [onSubmit, value, showToolsMenu, showCancel, onCancel],
  );

  const handleRemoveToolChip = React.useCallback(
    (id: ToolId) => {
      if (onRemoveTool) {
        onRemoveTool(id);
        return;
      }

      if (onToggleTool) {
        const legacyKey = toolIdToLegacyKey(id);
        if (legacyKey) {
          onToggleTool(legacyKey);
        }
      }
    },
    [onRemoveTool, onToggleTool],
  );

  const handlePlusClick = React.useCallback(() => {
    // Siempre abrir el menú local primero
    handleToggleToolsMenu();

    // También llamar el callback externo si existe (para logging, etc.)
    if (onOpenTools) {
      onOpenTools();
    }
  }, [handleToggleToolsMenu, onOpenTools]);

  const handleToolSelect = React.useCallback(
    (id: ToolId) => {
      if (onAddTool) {
        onAddTool(id);
      }
      setShowToolsMenu(false);
    },
    [onAddTool],
  );

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

  const handleDragEnter = React.useCallback(
    (e: React.DragEvent) => {
      if (!allowAttachments) return;
      e.preventDefault();
      setDragCounter((prev) => prev + 1);
      if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
        setIsDragOver(true);
      }
    },
    [allowAttachments],
  );

  const handleDragLeave = React.useCallback(
    (e: React.DragEvent) => {
      if (!allowAttachments) return;
      e.preventDefault();
      setDragCounter((prev) => {
        const next = prev - 1;
        if (next <= 0) {
          setIsDragOver(false);
          return 0;
        }
        return next;
      });
    },
    [allowAttachments],
  );

  const handleDragOver = React.useCallback(
    (e: React.DragEvent) => {
      if (!allowAttachments) return;
      e.preventDefault();
    },
    [allowAttachments],
  );

  const handleFileSelect = React.useCallback(
    (files: FileList) => {
      if (!allowAttachments) return;
      if (!onAttachmentsChange) return;

      const current = [...attachments];

      Array.from(files).forEach((file, index) => {
        if (current.length >= MAX_FILE_COUNT) {
          return;
        }

        const { valid, error } = validateFile(file);

        current.push({
          id: `${file.name}-${file.size}-${Date.now()}-${index}`,
          file,
          name: file.name,
          size: file.size,
          type: file.type,
          progress: valid ? 0 : 100,
          status: valid ? "uploading" : "error",
          errorMessage: valid ? undefined : error,
        });
      });

      onAttachmentsChange(current);
    },
    [allowAttachments, attachments, onAttachmentsChange],
  );

  const handleDrop = React.useCallback(
    (e: React.DragEvent) => {
      if (!allowAttachments) return;
      e.preventDefault();
      setDragCounter(0);
      setIsDragOver(false);

      if (e.dataTransfer.files) {
        handleFileSelect(e.dataTransfer.files);
      }
    },
    [allowAttachments, handleFileSelect],
  );

  const handleFileInputChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      if (!allowAttachments) return;
      if (event.target.files && event.target.files.length > 0) {
        handleFileSelect(event.target.files);
        event.target.value = "";
      }
    },
    [allowAttachments, handleFileSelect],
  );

  const composerRef = React.useRef<HTMLDivElement>(null);

  return (
    <div
      className={cn("w-full px-3 pb-3 pt-2 sm:px-4 md:pb-4", className)}
      aria-label="Chat composer"
    >
      <div className="relative max-w-4xl mx-auto">
        {showToolsMenu && (
          <div className="absolute bottom-full left-0 z-[9999] mb-2 pointer-events-auto">
            <ToolMenu
              onSelect={handleToolSelect}
              onClose={() => setShowToolsMenu(false)}
            />
          </div>
        )}

        <div
          ref={composerRef}
          className={cn(
            "grid grid-rows-[auto_auto] gap-2 rounded-2xl border border-zinc-700/50 bg-zinc-900/70 p-2 shadow-sm transition-all duration-200 backdrop-blur supports-[backdrop-filter]:bg-zinc-900/60 sm:p-3",
            "hover:shadow-md focus-within:shadow-md",
          )}
        >
          <div
            className={cn(
              "flex items-center gap-3 rounded-xl border border-transparent px-1 py-1 transition-colors",
              isDragOver && "border-emerald-500/40 bg-emerald-500/5",
            )}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          >
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(event) => onChange(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isDragOver ? "Suelta los archivos aquí…" : placeholder
              }
              disabled={disabled || loading}
              maxLength={maxLength}
              rows={1}
              className="peer h-full w-full max-h-[176px] resize-none overflow-y-auto rounded-xl bg-transparent px-2 py-1.5 text-sm leading-relaxed text-zinc-100 placeholder:text-zinc-400 focus:outline-none"
            />
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-2 px-1">
              {/* IZQUIERDA: [+] y luego chips a la DERECHA del + */}
              <div className="flex items-center gap-2 min-w-0">
                <button
                  type="button"
                  aria-label="Tools"
                  onClick={handlePlusClick}
                  disabled={disabled || loading}
                  className={cn(
                    "flex-shrink-0 grid min-h-[36px] min-w-[36px] place-items-center rounded-xl text-zinc-300 hover:bg-zinc-800/70 transition-colors",
                    (disabled || loading) && "cursor-not-allowed opacity-50",
                  )}
                >
                  <PlusIcon className="h-5 w-5" />
                </button>

                <div className="flex items-center gap-2 overflow-hidden">
                  {visibleToolIds.map((id) => {
                    const tool = TOOL_REGISTRY[id];
                    if (!tool) return null;
                    const Icon = tool.Icon;
                    return (
                      <div
                        key={id}
                        className="group flex h-9 items-center gap-2 rounded-xl border border-[#49F7D9]/60 bg-[#49F7D9]/15 pl-2 pr-1 text-[#49F7D9] transition-colors hover:bg-[#49F7D9]/25"
                        title={tool.label}
                      >
                        <Icon className="h-4 w-4" />
                        <span className="text-sm font-medium">
                          {tool.label}
                        </span>
                        <button
                          type="button"
                          aria-label={`Remove ${tool.label}`}
                          onClick={() => handleRemoveToolChip(id)}
                          className="grid place-items-center rounded-lg p-1 text-[#49F7D9] hover:bg-[#49F7D9]/20"
                        >
                          <CloseIcon className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {showMicButton && (
                  <button
                    type="button"
                    onClick={handleMicClick}
                    disabled={disabled || loading}
                    aria-label="Funcionalidad aún no disponible"
                    className={cn(
                      "grid min-h-[36px] min-w-[36px] place-items-center rounded-xl border border-zinc-700/70 text-zinc-300 transition-colors",
                      "hover:bg-zinc-800/70 hover:text-zinc-50",
                      (disabled || loading) && "cursor-not-allowed opacity-50",
                    )}
                  >
                    <MicIcon className="h-5 w-5" />
                  </button>
                )}

                {showCancel && onCancel ? (
                  <button
                    type="button"
                    onClick={onCancel}
                    className="grid min-h-[36px] min-w-[36px] place-items-center rounded-xl border border-red-500/60 bg-red-500/15 text-red-300 transition-colors hover:bg-red-500/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400/60 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-900"
                    aria-label="Detener"
                  >
                    <StopIcon className="h-5 w-5" />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleSendClick}
                    disabled={!canSubmit}
                    aria-label="Enviar mensaje"
                    className={cn(
                      "grid min-h-[36px] min-w-[40px] place-items-center rounded-xl bg-emerald-600 text-white transition-colors",
                      "hover:bg-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300/80 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-900",
                      !canSubmit && "cursor-not-allowed opacity-50",
                    )}
                  >
                    <SendIcon className="h-5 w-5" />
                  </button>
                )}
              </div>
            </div>

            {allowAttachments && attachments.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 px-1">
                {attachments.map((attachment) => (
                  <div
                    key={attachment.id}
                    className={cn(
                      "flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs transition-colors",
                      attachment.status === "completed"
                        ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-200"
                        : attachment.status === "error"
                          ? "border-red-500/60 bg-red-500/10 text-red-300"
                          : "border-zinc-700/70 bg-zinc-900/80 text-zinc-200",
                    )}
                  >
                    <span className="text-sm">
                      {attachment.name.endsWith(".pdf")
                        ? "📄"
                        : attachment.name.match(/\.(png|jpg|jpeg)$/i)
                          ? "🖼️"
                          : attachment.name.endsWith(".docx")
                            ? "📝"
                            : attachment.name.match(/\.(txt|md)$/i)
                              ? "📝"
                              : attachment.name.match(/\.(csv|json)$/i)
                                ? "📊"
                                : attachment.name.endsWith(".ipynb")
                                  ? "📓"
                                  : "📎"}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1">
                        <span className="truncate font-medium">
                          {attachment.name}
                        </span>
                        <span className="text-zinc-400">
                          ({formatFileSize(attachment.size)})
                        </span>
                      </div>
                      {attachment.status === "uploading" && (
                        <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-zinc-800">
                          <div
                            className="h-full bg-emerald-500 transition-all duration-300 ease-out"
                            style={{ width: `${attachment.progress}%` }}
                          />
                        </div>
                      )}
                      {attachment.status === "error" &&
                        attachment.errorMessage && (
                          <p className="mt-1 text-xs text-red-300">
                            {attachment.errorMessage}
                          </p>
                        )}
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        onAttachmentsChange?.(
                          attachments.filter(
                            (item) => item.id !== attachment.id,
                          ),
                        )
                      }
                      disabled={disabled || loading}
                      className="grid h-4 w-4 place-items-center rounded-full text-zinc-400 hover:bg-zinc-800"
                      aria-label="Eliminar archivo"
                    >
                      <svg
                        className="h-3 w-3"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_FILE_TYPES.map((type) => `.${type}`).join(",")}
          onChange={handleFileInputChange}
          className="hidden"
        />
      </div>
    </div>
  );
}
