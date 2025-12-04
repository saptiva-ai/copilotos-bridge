import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { BankChartData, CanvasChartSync } from "@/lib/types";
import { apiClient } from "@/lib/api-client";

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

  // 🆕 Bank chart specific state (Phase 2)
  activeBankChart: BankChartData | null;
  activeMessageId: string | null;
  chartHistory: CanvasChartSync[];

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

  // 🆕 Bank chart methods (Phase 2)
  openBankChart: (
    chartData: BankChartData,
    artifactId: string,
    messageId: string,
    autoOpen?: boolean,
  ) => void;
  setActiveMessage: (messageId: string | null) => void;
  addToChartHistory: (sync: CanvasChartSync) => void;
  clearChartHistory: () => void;

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
      activeBankChart: null,
      activeMessageId: null,
      chartHistory: [],
      currentSessionId: null,
      canvasWidthPercent: DEFAULT_CANVAS_WIDTH, // Default to 40% of viewport width

      setArtifact: (id) =>
        set((state) => ({
          activeArtifactId: id,
          activeArtifactData: null,
          activeBankChart: null, // Clear chart when setting artifact
          isSidebarOpen: id ? true : state.isSidebarOpen,
        })),

      openArtifact: (_type, data) =>
        set(() => ({
          activeArtifactId: null,
          activeArtifactData: data,
          activeBankChart: null, // Clear chart when opening artifact
          isSidebarOpen: true,
        })),

      toggleSidebar: () => {
        set((state) => {
          const newOpenState = !state.isSidebarOpen;

          // If closing, clear active message and deactivate all charts
          if (!newOpenState) {
            return {
              isSidebarOpen: false,
              activeMessageId: null,
              chartHistory: state.chartHistory.map((c) => ({
                ...c,
                isActive: false,
              })),
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
          activeBankChart: null,
          activeMessageId: null,
          chartHistory: [],
        })),

      // Set canvas width (percentage of viewport, constrained to 30-70%)
      setCanvasWidth: (widthPercent) =>
        set(() => ({
          canvasWidthPercent: clampCanvasWidthPercent(widthPercent),
        })),

      // 🆕 Open bank chart in canvas (main method)
      openBankChart: (chartData, artifactId, messageId, autoOpen = false) => {
        const { chartHistory, addToChartHistory } = get();

        set({
          activeBankChart: chartData,
          // Don't set activeArtifactId for temp artifacts or when we have chartData
          // This prevents canvas-panel from trying to fetch the artifact
          activeArtifactId: artifactId !== "temp" ? artifactId : null,
          activeMessageId: messageId,
          isSidebarOpen: true,
          activeArtifactData: null, // Clear audit data if present
        });

        // Add to history if not already present
        if (!chartHistory.find((c) => c.artifactId === artifactId)) {
          addToChartHistory({
            artifactId,
            messageId,
            isActive: true,
          });
        } else {
          // Update existing entry to mark as active
          set((state) => ({
            chartHistory: state.chartHistory.map((c) =>
              c.artifactId === artifactId
                ? { ...c, isActive: true }
                : { ...c, isActive: false },
            ),
          }));
        }

        if (process.env.NODE_ENV === "development") {
          console.warn("[Canvas] Opened bank chart:", {
            artifactId,
            messageId,
            metric: chartData.metric_name,
            autoOpen,
          });
        }

        // Sync to MongoDB after opening chart
        get().syncToMongoDB();
      },

      // 🆕 Set active message (for highlight synchronization)
      setActiveMessage: (messageId) =>
        set((state) => ({
          activeMessageId: messageId,
          chartHistory: state.chartHistory.map((c) => ({
            ...c,
            isActive: c.messageId === messageId,
          })),
        })),

      // 🆕 Add chart to history (with max limit of 20 charts)
      addToChartHistory: (sync) =>
        set((state) => {
          const MAX_CHART_HISTORY = 20;
          const updatedHistory = [
            ...state.chartHistory.map((c) => ({ ...c, isActive: false })),
            sync,
          ];

          // Keep only the last 20 charts
          const limitedHistory =
            updatedHistory.length > MAX_CHART_HISTORY
              ? updatedHistory.slice(-MAX_CHART_HISTORY)
              : updatedHistory;

          return { chartHistory: limitedHistory };
        }),

      // 🆕 Clear chart history (on session change)
      clearChartHistory: () =>
        set(() => ({
          chartHistory: [],
          activeBankChart: null,
          activeMessageId: null,
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
          activeBankChart,
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
            active_bank_chart: activeBankChart,
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
              activeBankChart: canvasState.active_bank_chart || null,
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
      version: 1, // Increment version to migrate old localStorage data
      // Only persist width preference - Canvas state should reset per conversation
      merge: (persistedState, currentState) => {
        const safePersisted = (persistedState as Partial<CanvasState>) || {};
        const canvasWidthPercent = clampCanvasWidthPercent(
          safePersisted.canvasWidthPercent ?? currentState.canvasWidthPercent,
        );

        return {
          ...currentState,
          canvasWidthPercent,
          // DO NOT restore isSidebarOpen - Canvas should start closed per conversation
          isSidebarOpen: false, // Force closed on every hydration
        };
      },
      // Only persist width preference, not open/closed state
      partialize: (state) => ({
        canvasWidthPercent: state.canvasWidthPercent,
        // DO NOT persist isSidebarOpen - causes Canvas to stay open between conversations
      }),
      migrate: (persistedState: any, version: number) => {
        // Migrate from version 0 to version 1: remove old persisted state
        if (version === 0) {
          // Only keep canvasWidthPercent, discard all other persisted fields
          return {
            canvasWidthPercent: clampCanvasWidthPercent(
              persistedState?.canvasWidthPercent,
            ),
          };
        }
        return persistedState;
      },
    },
  ),
);
