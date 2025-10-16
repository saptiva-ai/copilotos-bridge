/**
 * Chat State Store
 *
 * Manages active chat session state:
 * - Current chat messages
 * - Model selection
 * - Tools configuration
 * - Loading and hydration state
 * - Message sending
 */

import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import toast from "react-hot-toast";
import { ChatMessage, ChatModel } from "../types";
import { apiClient } from "../api-client";
import { logDebug, logError, logWarn } from "../logger";
import { logAction } from "../ux-logger";
import { buildModelList, getDefaultModelSlug } from "../modelMap";
import { getAllModels } from "../../config/modelCatalog";
import { createDefaultToolsState, normalizeToolsState } from "../tool-mapping";

const mergeToolsState = (seed?: Record<string, boolean>) => {
  const extraKeys = seed ? Object.keys(seed) : [];
  const base = createDefaultToolsState(extraKeys);
  return seed ? { ...base, ...seed } : base;
};

interface ChatState {
  // State
  currentChatId: string | null;
  selectionEpoch: number; // Incremented on same-chat re-selection to force re-render
  messages: ChatMessage[];
  isLoading: boolean;
  models: ChatModel[];
  modelsLoading: boolean;
  selectedModel: string;
  toolsEnabled: Record<string, boolean>;
  toolsEnabledByChatId: Record<string, Record<string, boolean>>;
  chatNotFound: boolean;

  // Hydration state (stale-while-revalidate pattern)
  hydratedByChatId: Record<string, boolean>;
  isHydratingByChatId: Record<string, boolean>;

  // Actions
  setCurrentChatId: (chatId: string | null) => void;
  switchChat: (
    nextId: string,
    draftToolsEnabled?: Record<string, boolean>,
  ) => void;
  bumpSelectionEpoch: () => void;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => void;
  clearMessages: () => void;
  setLoading: (loading: boolean) => void;
  setSelectedModel: (model: string) => void;
  toggleTool: (toolName: string) => Promise<void>;
  setToolEnabled: (toolName: string, enabled: boolean) => Promise<void>;
  loadModels: () => Promise<void>;
  loadUnifiedHistory: (chatId: string) => Promise<void>;
  refreshChatStatus: (chatId: string) => Promise<void>;
  updateToolsForChat: (chatId: string, tools: Record<string, boolean>) => void;
  updateCurrentTools: (tools: Record<string, boolean>) => void;
  clearAllData: () => void;

  // Document review actions
  addFileReviewMessage: (message: ChatMessage) => void;
  updateFileReviewMessage: (
    messageId: string,
    reviewData: Partial<ChatMessage["review"]>,
  ) => void;
  findFileReviewMessage: (docId: string) => ChatMessage | undefined;
}

export const useChatStore = create<ChatState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        currentChatId: null,
        selectionEpoch: 0,
        messages: [],
        isLoading: false,
        models: [],
        modelsLoading: false,
        selectedModel: "turbo", // Default to Saptiva Turbo
        toolsEnabled: mergeToolsState(),
        toolsEnabledByChatId: {},
        chatNotFound: false,
        hydratedByChatId: {},
        isHydratingByChatId: {},

        // Actions
        setCurrentChatId: (chatId) => {
          const state = get();
          const nextToolsByChat = { ...state.toolsEnabledByChatId };
          let resolvedTools: Record<string, boolean>;

          if (chatId) {
            if (!nextToolsByChat[chatId]) {
              nextToolsByChat[chatId] = mergeToolsState();
            }
            resolvedTools = mergeToolsState(nextToolsByChat[chatId]);
          } else {
            resolvedTools = mergeToolsState();
          }

          set({
            currentChatId: chatId,
            toolsEnabled: resolvedTools,
            toolsEnabledByChatId: nextToolsByChat,
          });
        },

        // Switch chat with re-selection support (A→B→C→A pattern)
        switchChat: (
          nextId: string,
          draftToolsEnabled?: Record<string, boolean>,
        ) => {
          const {
            currentChatId,
            selectionEpoch,
            hydratedByChatId,
            isHydratingByChatId,
            toolsEnabledByChatId,
          } = get();

          // Always set the activeId AND bump epoch
          const isReselection = currentChatId === nextId;
          const newEpoch = selectionEpoch + 1;

          // CRITICAL: Invalidate hydration for the target chat to force reload
          const newHydratedByChatId = { ...hydratedByChatId };
          delete newHydratedByChatId[nextId];

          // CRITICAL: Also clear isHydratingByChatId flag
          const newIsHydratingByChatId = { ...isHydratingByChatId };
          delete newIsHydratingByChatId[nextId];

          const nextToolsByChat = { ...toolsEnabledByChatId };
          if (!nextToolsByChat[nextId]) {
            nextToolsByChat[nextId] = mergeToolsState();
          }

          const resolvedTools = mergeToolsState(
            nextToolsByChat[nextId] || draftToolsEnabled,
          );

          logDebug("SWITCH_CHAT", {
            from: currentChatId,
            to: nextId,
            reselection: isReselection,
            epochBefore: selectionEpoch,
            epochAfter: newEpoch,
            invalidateHydration: true,
            clearingMessages: true,
            clearingHydratingFlag: true,
            settingLoading: true,
          });

          set({
            currentChatId: nextId,
            selectionEpoch: newEpoch,
            hydratedByChatId: newHydratedByChatId,
            isHydratingByChatId: newIsHydratingByChatId,
            messages: [], // CRITICAL: Clear messages immediately
            isLoading: true, // CRITICAL: Set loading to prevent Hero from showing
            toolsEnabledByChatId: nextToolsByChat,
            toolsEnabled: resolvedTools,
          });
        },

        bumpSelectionEpoch: () => {
          const epoch = get().selectionEpoch;
          logDebug("BUMP_EPOCH", { from: epoch, to: epoch + 1 });
          set({ selectionEpoch: epoch + 1 });
        },

        addMessage: (message) =>
          set((state) => ({
            messages: [...state.messages, message],
          })),

        updateMessage: (messageId, updates) =>
          set((state) => ({
            messages: state.messages.map((msg) =>
              msg.id === messageId ? { ...msg, ...updates } : msg,
            ),
          })),

        clearMessages: () => set({ messages: [] }),
        setLoading: (loading) => set({ isLoading: loading }),
        setSelectedModel: (model) => {
          logDebug("UI model changed", model);
          set({ selectedModel: model });
        },

        toggleTool: async (toolName) => {
          const state = get();
          const currentValue = state.toolsEnabled[toolName] ?? false;
          await get().setToolEnabled(toolName, !currentValue);
        },

        setToolEnabled: async (toolName, enabled) => {
          const state = get();
          const currentValue = state.toolsEnabled[toolName] ?? false;
          if (currentValue === enabled) {
            return;
          }

          const nextTools = mergeToolsState({
            ...state.toolsEnabled,
            [toolName]: enabled,
          });

          const currentChatId = state.currentChatId;
          const nextToolsByChat = { ...state.toolsEnabledByChatId };

          if (currentChatId) {
            nextToolsByChat[currentChatId] = nextTools;
          }

          set({
            toolsEnabled: nextTools,
            toolsEnabledByChatId: nextToolsByChat,
          });

          logAction("tool.toggle.changed", { tool: toolName, enabled });

          if (currentChatId && !currentChatId.startsWith("temp-")) {
            try {
              await apiClient.updateChatSession(currentChatId, {
                tools_enabled: nextTools,
              });
            } catch (error) {
              logError("Failed to update tools-enabled state", error);
              toast.error(
                "No se pudo actualizar la configuración de herramientas.",
              );

              const rollbackTools = mergeToolsState({
                ...state.toolsEnabled,
                [toolName]: currentValue,
              });

              set((prevState) => {
                const rollbackMap = { ...prevState.toolsEnabledByChatId };
                if (currentChatId) {
                  rollbackMap[currentChatId] = rollbackTools;
                }
                return {
                  toolsEnabled: rollbackTools,
                  toolsEnabledByChatId: rollbackMap,
                };
              });
            }
          }
        },

        loadModels: async () => {
          try {
            set({ modelsLoading: true });
            const response = await apiClient.getModels();

            // Build model list with catalog and availability
            const modelList = buildModelList(response.allowed_models);

            // Convert to ChatModel format for UI
            const models: ChatModel[] = modelList.map(
              ({ model, available, backendId }) => ({
                id: model.slug,
                value: backendId || model.slug,
                label: model.displayName,
                description: model.description,
                tags: model.badges,
                available,
                backendId,
              }),
            );

            // Get default model slug from backend default
            const defaultSlug = getDefaultModelSlug(response.default_model);

            logDebug("Models loaded", {
              backendModels: response.allowed_models,
              uiModels: models,
              defaultSlug,
            });

            set({ models, selectedModel: defaultSlug, modelsLoading: false });
          } catch (error) {
            logError("Failed to load models:", error);
            // Fallback to catalog models all marked unavailable
            const fallbackModels: ChatModel[] = getAllModels().map((model) => ({
              id: model.slug,
              value: model.slug,
              label: model.displayName,
              description: model.description,
              tags: model.badges,
              available: false,
              backendId: null,
            }));
            set({ models: fallbackModels, modelsLoading: false });
          }
        },

        loadUnifiedHistory: async (chatId) => {
          const state = get();

          // SWR deduplication: Don't load if already hydrated or currently hydrating
          if (
            state.hydratedByChatId[chatId] ||
            state.isHydratingByChatId[chatId]
          ) {
            logDebug("Skipping load - already hydrated/hydrating", { chatId });
            // CRITICAL: Clear isLoading even on early return
            set({ isLoading: false });
            return;
          }

          try {
            // Mark as hydrating (prevents duplicate calls)
            set((s) => ({
              isHydratingByChatId: { ...s.isHydratingByChatId, [chatId]: true },
              chatNotFound: false,
              currentChatId: chatId,
            }));

            const historyData = await apiClient.getUnifiedChatHistory(
              chatId,
              50,
              0,
              true,
              false,
            );

            // Convert history events to chat messages
            const messages: ChatMessage[] = [];

            for (const event of historyData.events) {
              if (event.event_type === "chat_message" && event.chat_data) {
                // DEBUG: Log metadata from backend
                if (event.chat_data.role === "user") {
                  logDebug("[ChatStore] Loading user message from history", {
                    message_id: event.message_id,
                    role: event.chat_data.role,
                    hasMetadata: !!event.chat_data.metadata,
                    metadata: event.chat_data.metadata,
                    metadataKeys: event.chat_data.metadata
                      ? Object.keys(event.chat_data.metadata)
                      : [],
                  });
                }

                messages.push({
                  id: event.message_id || event.id,
                  role: event.chat_data.role,
                  content: event.chat_data.content,
                  timestamp: event.timestamp,
                  model: event.chat_data.model,
                  tokens: event.chat_data.tokens,
                  latency: event.chat_data.latency_ms,
                  // MVP-LOCK: Include metadata if present (for file_ids indicator)
                  ...(event.chat_data.metadata && {
                    metadata: event.chat_data.metadata,
                  }),
                });
              }
            }

            // Atomic replacement: set messages only when data arrives
            set((s) => ({
              messages,
              currentChatId: chatId,
              hydratedByChatId: { ...s.hydratedByChatId, [chatId]: true },
              isHydratingByChatId: {
                ...s.isHydratingByChatId,
                [chatId]: false,
              },
            }));

            logDebug("Chat hydrated", {
              chatId,
              messageCount: messages.length,
            });
          } catch (error: any) {
            logError("Failed to load unified history:", error);

            // Mark hydration as failed
            set((s) => ({
              isHydratingByChatId: {
                ...s.isHydratingByChatId,
                [chatId]: false,
              },
            }));

            // Check if it's a 404 error (chat not found)
            if (error?.response?.status === 404) {
              set({ chatNotFound: true, messages: [], currentChatId: null });
            }
          } finally {
            // CRITICAL: Always clear isLoading in finally block
            logDebug("loadUnifiedHistory cleanup", {
              chatId,
              clearingLoading: true,
            });
            set({ isLoading: false });
          }
        },

        refreshChatStatus: async (chatId) => {
          // This is now handled by research store, kept for compatibility
          try {
            await apiClient.getChatStatus(chatId);
          } catch (error) {
            logError("Failed to refresh chat status:", error);
          }
        },

        updateToolsForChat: (
          chatId: string,
          tools: Record<string, boolean>,
        ) => {
          set((state) => ({
            toolsEnabledByChatId: {
              ...state.toolsEnabledByChatId,
              [chatId]: mergeToolsState(tools),
            },
          }));
        },

        updateCurrentTools: (tools: Record<string, boolean>) => {
          set({ toolsEnabled: mergeToolsState(tools) });
        },

        clearAllData: () => {
          set({
            currentChatId: null,
            selectionEpoch: 0,
            messages: [],
            isLoading: false,
            selectedModel: "turbo",
            toolsEnabled: mergeToolsState(),
            toolsEnabledByChatId: {},
            chatNotFound: false,
            hydratedByChatId: {},
            isHydratingByChatId: {},
          });
        },

        // Document review message actions
        addFileReviewMessage: (message: ChatMessage) => {
          logDebug("Adding file review message", {
            messageId: message.id,
            filename: message.review?.filename,
          });
          set((state) => ({
            messages: [...state.messages, message],
          }));
        },

        updateFileReviewMessage: (
          messageId: string,
          reviewData: Partial<ChatMessage["review"]>,
        ) => {
          logDebug("Updating file review message", { messageId, reviewData });
          set((state) => ({
            messages: state.messages.map((msg) =>
              msg.id === messageId && msg.kind === "file-review"
                ? {
                    ...msg,
                    review: {
                      ...msg.review!,
                      ...reviewData,
                    },
                  }
                : msg,
            ),
          }));
        },

        findFileReviewMessage: (docId: string) => {
          const state = get();
          return state.messages.find(
            (msg) => msg.kind === "file-review" && msg.review?.docId === docId,
          );
        },
      }),
      {
        name: "chat-store",
        partialize: (state) => ({
          selectedModel: state.selectedModel,
          toolsEnabled: state.toolsEnabled,
        }),
      },
    ),
    {
      name: "chat-store",
    },
  ),
);

// Note: For backward compatibility, import draft methods from draft-store
// The full backward-compatible useChat selector is in stores/index.ts
