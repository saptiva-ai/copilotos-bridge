import { create } from "zustand";
import { persist } from "zustand/middleware";
import { apiClient } from "@/lib/api-client";
import type {
  ResearchReportEvent,
  ResearchSourceEvent,
  ResearchEvidenceEvent,
} from "@/hooks/useDeepResearch";

// Deep Research report data for canvas display
export interface ResearchReportData {
  taskId: string;
  query: string;
  report: ResearchReportEvent;
  sources: ResearchSourceEvent[];
  evidences: ResearchEvidenceEvent[];
  completedAt: string;
}

const DEFAULT_CANVAS_WIDTH = 40;

export const clampCanvasWidthPercent = (width?: number | null): number => {
  const numericWidth =
    typeof width === "number" ? width : Number(width ?? DEFAULT_CANVAS_WIDTH);

  if (!Number.isFinite(numericWidth)) {
    return DEFAULT_CANVAS_WIDTH;
  }

  return Math.min(Math.max(numericWidth, 30), 70);
};

interface CanvasState {
  isSidebarOpen: boolean;
  activeArtifactId: string | null;
  activeArtifactData: any | null;

  // Active message ID for highlight synchronization
  activeMessageId: string | null;

  // 🆕 Deep Research report state
  activeResearchReport: ResearchReportData | null;

  // Current session ID for persistence
  currentSessionId: string | null;

  // Canvas width as percentage of viewport (30-70%, default 40%)
  canvasWidthPercent: number;

  // Existing methods
  setArtifact: (id: string | null) => void;
  openArtifact: (type: string, data: any) => void;
  toggleSidebar: () => void;
  reset: () => void;
  setCanvasWidth: (widthPercent: number) => void;

  // 🆕 Deep Research methods
  openResearchReport: (reportData: ResearchReportData) => void;
  clearResearchReport: () => void;

  // MongoDB persistence
  setCurrentSessionId: (sessionId: string | null) => void;
  syncToMongoDB: () => Promise<void>;
  loadFromMongoDB: (sessionId: string) => Promise<void>;
}

export const useCanvasStore = create<CanvasState>()(
  persist(
    (set, get) => ({
      isSidebarOpen: false,
      activeArtifactId: null,
      activeArtifactData: null,
      activeMessageId: null,
      activeResearchReport: null,
      currentSessionId: null,
      canvasWidthPercent: DEFAULT_CANVAS_WIDTH, // Default to 40% of viewport width

      setArtifact: (id) =>
        set((state) => ({
          activeArtifactId: id,
          activeArtifactData: null,
          activeResearchReport: null, // Clear research report
          isSidebarOpen: id ? true : state.isSidebarOpen,
        })),

      openArtifact: (_type, data) =>
        set(() => ({
          activeArtifactId: null,
          activeArtifactData: data,
          activeResearchReport: null, // Clear research report
          isSidebarOpen: true,
        })),

      toggleSidebar: () => {
        set((state) => {
          const newOpenState = !state.isSidebarOpen;

          // If closing, clear active message
          if (!newOpenState) {
            return {
              isSidebarOpen: false,
              activeMessageId: null,
            };
          }

          return { isSidebarOpen: true };
        });

        // Sync to MongoDB after state change
        get().syncToMongoDB();
      },

      reset: () =>
        set(() => ({
          isSidebarOpen: false,
          activeArtifactId: null,
          activeArtifactData: null,
          activeMessageId: null,
          activeResearchReport: null,
        })),

      // Set canvas width (percentage of viewport, constrained to 30-70%)
      setCanvasWidth: (widthPercent) =>
        set(() => ({
          canvasWidthPercent: clampCanvasWidthPercent(widthPercent),
        })),

      // 🆕 Open research report in canvas
      openResearchReport: (reportData) => {
        set({
          activeResearchReport: reportData,
          activeArtifactId: null,
          activeArtifactData: null,
          isSidebarOpen: true,
        });

        if (process.env.NODE_ENV === "development") {
          console.warn("[Canvas] Opened research report:", {
            taskId: reportData.taskId,
            query: reportData.query,
            sourcesCount: reportData.sources.length,
          });
        }
      },

      // 🆕 Clear research report
      clearResearchReport: () =>
        set(() => ({
          activeResearchReport: null,
        })),

      // Set current session ID for persistence
      setCurrentSessionId: (sessionId) => set({ currentSessionId: sessionId }),

      // Sync canvas state to MongoDB
      syncToMongoDB: async () => {
        const state = get();
        const {
          currentSessionId,
          isSidebarOpen,
          activeArtifactId,
          activeMessageId,
        } = state;

        if (!currentSessionId) {
          // No session ID set, skip sync
          return;
        }

        try {
          await apiClient.saveCanvasState(currentSessionId, {
            is_sidebar_open: isSidebarOpen,
            active_artifact_id: activeArtifactId,
            active_message_id: activeMessageId,
          });
        } catch (_error) {
          // Silently fail - sync will retry on next change
        }
      },

      // Load canvas state from MongoDB
      loadFromMongoDB: async (sessionId) => {
        try {
          const canvasState = await apiClient.getCanvasState(sessionId);

          if (canvasState) {
            set({
              isSidebarOpen: canvasState.is_sidebar_open || false,
              activeArtifactId: canvasState.active_artifact_id || null,
              activeMessageId: canvasState.active_message_id || null,
              currentSessionId: sessionId,
            });
          } else {
            // No saved state, just set the session ID
            set({ currentSessionId: sessionId });
          }
        } catch (_error) {
          // Set session ID anyway so we can save later
          set({ currentSessionId: sessionId });
        }
      },
    }),
    {
      name: "canvas-store",
      version: 2, // Bump to v2 to force full localStorage reset
      // Only persist width preference - Canvas state should reset per conversation
      partialize: (state) => ({
        canvasWidthPercent: state.canvasWidthPercent,
        // DO NOT persist isSidebarOpen - causes Canvas to stay open between conversations
      }),
    },
  ),
);
