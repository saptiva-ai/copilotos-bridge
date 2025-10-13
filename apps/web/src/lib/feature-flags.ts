import type { ToolId } from "@/types/tools";

const toBool = (value: string | undefined, defaultValue = false) => {
  if (value === undefined) return defaultValue;
  return value.toLowerCase() === "true";
};

export const featureFlags = {
  webSearch: toBool(process.env.NEXT_PUBLIC_FEATURE_WEB_SEARCH, false), // V1: Disabled
  deepResearch: toBool(process.env.NEXT_PUBLIC_FEATURE_DEEP_RESEARCH, false), // V1: Disabled
  addFiles: toBool(process.env.NEXT_PUBLIC_FEATURE_ADD_FILES, true), // V1: ENABLED for document upload
  googleDrive: toBool(process.env.NEXT_PUBLIC_FEATURE_GOOGLE_DRIVE, false),
  canvas: toBool(process.env.NEXT_PUBLIC_FEATURE_CANVAS, false),
  agentMode: toBool(process.env.NEXT_PUBLIC_FEATURE_AGENT_MODE, false),
  mic: toBool(process.env.NEXT_PUBLIC_FEATURE_MIC, false),
  // Model selector production-style UI (default: true)
  useProdStyleModels: toBool(
    process.env.NEXT_PUBLIC_FEATURE_PROD_STYLE_MODELS,
    true,
  ),
};

const defaultToolVisibility: Record<ToolId, boolean> = {
  "web-search": featureFlags.webSearch,
  "deep-research": featureFlags.deepResearch,
  "add-files": featureFlags.addFiles,
  "google-drive": featureFlags.googleDrive,
  canvas: featureFlags.canvas,
  "agent-mode": featureFlags.agentMode,
  "document-review": toBool(
    process.env.NEXT_PUBLIC_FEATURE_DOCUMENT_REVIEW,
    true,
  ),
  files: toBool(
    process.env.NEXT_PUBLIC_TOOL_FILES ??
      process.env.NEXT_PUBLIC_FEATURE_ADD_FILES,
    true,
  ),
};

export const getDefaultToolVisibility = (): Record<ToolId, boolean> => ({
  ...defaultToolVisibility,
});

export const fetchToolVisibility = async (): Promise<
  Record<ToolId, boolean>
> => {
  try {
    const response = await fetch("/api/features/tools", {
      credentials: "include",
    });
    if (!response.ok) throw new Error("Failed to fetch tool visibility");

    const payload = await response.json();
    if (!payload?.tools) {
      return getDefaultToolVisibility();
    }

    const next: Record<ToolId, boolean> = getDefaultToolVisibility();
    for (const entry of payload.tools as Array<{
      key: ToolId;
      enabled: boolean;
    }>) {
      if (entry?.key in next) {
        next[entry.key] = Boolean(entry.enabled);
      }
    }
    if (next.files) {
      next["add-files"] = false;
      next["document-review"] = false;
    }
    return next;
  } catch (error) {
    console.warn("[feature-flags] Falling back to env-based visibility", error);
    return getDefaultToolVisibility();
  }
};
