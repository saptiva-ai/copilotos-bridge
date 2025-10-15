/**
 * Feature Flags
 *
 * Centralized feature flag management for the application
 */

export interface ToolsFeatures {
  files?: { enabled: boolean };
  addFiles?: { enabled: boolean };
  documentReview?: { enabled: boolean };
  deepResearch?: { enabled: boolean };
}

export interface FeaturesResponse {
  tools: ToolsFeatures;
}

/**
 * Fetch feature flags from backend
 */
export async function getToolsFeatures(): Promise<ToolsFeatures> {
  try {
    const response = await fetch("/api/features/tools", {
      cache: "no-store", // Always fetch fresh
    });

    if (!response.ok) {
      console.warn("Failed to fetch feature flags, using defaults");
      return getDefaultFeatures();
    }

    const data: FeaturesResponse = await response.json();
    return data.tools || getDefaultFeatures();
  } catch (error) {
    console.error("Error fetching feature flags:", error);
    return getDefaultFeatures();
  }
}

/**
 * Default features (fallback)
 */
function getDefaultFeatures(): ToolsFeatures {
  return {
    files: {
      enabled: process.env.NEXT_PUBLIC_TOOL_FILES === "true",
    },
    addFiles: {
      enabled: process.env.NEXT_PUBLIC_TOOL_ADD_FILES === "true",
    },
    documentReview: {
      enabled: process.env.NEXT_PUBLIC_TOOL_DOCUMENT_REVIEW === "true",
    },
    deepResearch: {
      enabled: false, // Kill switch active by default
    },
  };
}

/**
 * Check if Files V1 is enabled
 */
export async function isFilesV1Enabled(): Promise<boolean> {
  const features = await getToolsFeatures();
  return features.files?.enabled ?? false;
}

/**
 * Client-side feature flag hook
 * Use this in React components
 */
export function useFeatureFlags() {
  const [features, setFeatures] =
    React.useState<ToolsFeatures>(getDefaultFeatures());
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    getToolsFeatures()
      .then(setFeatures)
      .finally(() => setLoading(false));
  }, []);

  return { features, loading };
}

// Add React import for the hook
import * as React from "react";
