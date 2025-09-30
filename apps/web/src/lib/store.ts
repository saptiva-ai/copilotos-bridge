/**
 * Global state management with Zustand
 */

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { ChatMessage, ChatSession, ResearchTask, ChatModel, FeatureFlagsResponse } from './types'
import { apiClient } from './api-client'
import { logDebug, logError, logWarn } from './logger'
import { buildModelList, getDefaultModelSlug, resolveBackendId } from './modelMap'
import { getAllModels } from '../config/modelCatalog'

// App state interfaces
interface AppState {
  // UI state
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  connectionStatus: 'connected' | 'disconnected' | 'connecting'
  
  // Chat state
  currentChatId: string | null
  messages: ChatMessage[]
  isLoading: boolean
  models: ChatModel[]
  modelsLoading: boolean
  selectedModel: string
  toolsEnabled: Record<string, boolean>
  
  // Research state
  activeTasks: ResearchTask[]
  currentTaskId: string | null
  
  // History
  chatSessions: ChatSession[]
  chatSessionsLoading: boolean
  chatNotFound: boolean
  
  // Settings
  settings: {
    maxTokens: number
    temperature: number
    streamEnabled: boolean
  }
  featureFlags: FeatureFlagsResponse | null
  featureFlagsLoading: boolean
}

interface AppActions {
  // UI actions
  setSidebarOpen: (open: boolean) => void
  setTheme: (theme: 'light' | 'dark') => void
  setConnectionStatus: (status: AppState['connectionStatus']) => void
  
  // Chat actions
  setCurrentChatId: (chatId: string | null) => void
  addMessage: (message: ChatMessage) => void
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => void
  clearMessages: () => void
  setLoading: (loading: boolean) => void
  setSelectedModel: (model: string) => void
  toggleTool: (toolName: string) => void
  setToolsEnabled: (tools: Record<string, boolean>) => void
  
  // Research actions
  addTask: (task: ResearchTask) => void
  updateTask: (taskId: string, updates: Partial<ResearchTask>) => void
  removeTask: (taskId: string) => void
  setCurrentTaskId: (taskId: string | null) => void
  
  // History actions
  loadChatSessions: () => Promise<void>
  addChatSession: (session: ChatSession) => void
  removeChatSession: (chatId: string) => void
  renameChatSession: (chatId: string, newTitle: string) => Promise<void>
  pinChatSession: (chatId: string) => Promise<void>
  deleteChatSession: (chatId: string) => Promise<void>
  loadUnifiedHistory: (chatId: string) => Promise<void>
  refreshChatStatus: (chatId: string) => Promise<void>
  loadModels: () => Promise<void>
  loadFeatureFlags: () => Promise<void>
  
  // Settings actions
  updateSettings: (settings: Partial<AppState['settings']>) => void
  
  // API actions
  sendMessage: (content: string) => Promise<void>
  startNewChat: () => void
  checkConnection: () => Promise<void>

  // Cache invalidation helpers
  invalidateOnContextChange: () => void
  clearAllData: () => void
}

// Default settings
const defaultSettings = {
  maxTokens: 2000,
  temperature: 0.7,
  streamEnabled: true,
}

// Default tools configuration
const defaultTools = {
  web_search: true,
  deep_research: false,
}

export const useAppStore = create<AppState & AppActions>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        sidebarOpen: false,
        theme: 'light',
        connectionStatus: 'disconnected',
        currentChatId: null,
        messages: [],
        isLoading: false,
        models: [],
        modelsLoading: false,
        selectedModel: 'turbo', // Default to Saptiva Turbo
        toolsEnabled: defaultTools,
        activeTasks: [],
        currentTaskId: null,
        chatSessions: [],
        chatSessionsLoading: false,
        chatNotFound: false,
        settings: defaultSettings,
        featureFlags: null,
        featureFlagsLoading: false,

        // UI actions
        setSidebarOpen: (open) => set({ sidebarOpen: open }),
        setTheme: (theme) => set({ theme }),
        setConnectionStatus: (status) => set({ connectionStatus: status }),

        // Chat actions
        setCurrentChatId: (chatId) => set({ currentChatId: chatId }),
        
        addMessage: (message) =>
          set((state) => ({
            messages: [...state.messages, message],
          })),
        
        updateMessage: (messageId, updates) =>
          set((state) => ({
            messages: state.messages.map((msg) =>
              msg.id === messageId ? { ...msg, ...updates } : msg
            ),
          })),
        
        clearMessages: () => set({ messages: [] }),
        setLoading: (loading) => set({ isLoading: loading }),
        setSelectedModel: (model) => {
          logDebug('UI model changed', model)
          set({ selectedModel: model })
        },
        
        toggleTool: (toolName) =>
          set((state) => ({
            toolsEnabled: {
              ...state.toolsEnabled,
              [toolName]: !state.toolsEnabled[toolName],
            },
          })),
        
        setToolsEnabled: (tools) => set({ toolsEnabled: tools }),

        // Research actions
        addTask: (task) =>
          set((state) => ({
            activeTasks: [...state.activeTasks, task],
          })),
        
        updateTask: (taskId, updates) =>
          set((state) => ({
            activeTasks: state.activeTasks.map((task) =>
              task.id === taskId ? { ...task, ...updates } : task
            ),
          })),
        
        removeTask: (taskId) =>
          set((state) => ({
            activeTasks: state.activeTasks.filter((task) => task.id !== taskId),
            currentTaskId: state.currentTaskId === taskId ? null : state.currentTaskId,
          })),
        
        setCurrentTaskId: (taskId) => set({ currentTaskId: taskId }),

        // History actions
        loadChatSessions: async () => {
          try {
            set({ chatSessionsLoading: true })
            const response = await apiClient.getChatSessions()
            const sessions = response?.sessions || []
            set({ chatSessions: sessions, chatSessionsLoading: false })
          } catch (error) {
            logError('Failed to load chat sessions:', error)
            set({ chatSessions: [], chatSessionsLoading: false })
          }
        },
        
        addChatSession: (session) =>
          set((state) => ({
            chatSessions: [session, ...state.chatSessions],
          })),
        
        removeChatSession: (chatId) =>
          set((state) => ({
            chatSessions: state.chatSessions.filter((session) => session.id !== chatId),
            currentChatId: state.currentChatId === chatId ? null : state.currentChatId,
            messages: state.currentChatId === chatId ? [] : state.messages,
          })),

        renameChatSession: async (chatId: string, newTitle: string) => {
          try {
            // Optimistic update
            set((state) => ({
              chatSessions: state.chatSessions.map((session) =>
                session.id === chatId ? { ...session, title: newTitle } : session
              ),
            }))

            await apiClient.renameChatSession(chatId, newTitle)
            logDebug('Chat session renamed', { chatId, newTitle })
          } catch (error) {
            logError('Failed to rename chat session:', error)
            // Reload sessions on error to revert optimistic update
            const response = await apiClient.getChatSessions()
            set({ chatSessions: response?.sessions || [] })
            throw error
          }
        },

        pinChatSession: async (chatId: string) => {
          try {
            // Get current pinned state
            const session = get().chatSessions.find((s) => s.id === chatId)
            const newPinnedState = !session?.pinned

            // Optimistic update
            set((state) => ({
              chatSessions: state.chatSessions.map((s) =>
                s.id === chatId ? { ...s, pinned: newPinnedState } : s
              ),
            }))

            await apiClient.pinChatSession(chatId, newPinnedState)
            logDebug('Chat session pin toggled', { chatId, pinned: newPinnedState })
          } catch (error) {
            logError('Failed to pin chat session:', error)
            // Reload sessions on error to revert optimistic update
            const response = await apiClient.getChatSessions()
            set({ chatSessions: response?.sessions || [] })
            throw error
          }
        },

        deleteChatSession: async (chatId: string) => {
          try {
            // Optimistic update
            set((state) => ({
              chatSessions: state.chatSessions.filter((session) => session.id !== chatId),
              currentChatId: state.currentChatId === chatId ? null : state.currentChatId,
              messages: state.currentChatId === chatId ? [] : state.messages,
            }))

            await apiClient.deleteChatSession(chatId)
            logDebug('Chat session deleted', { chatId })
          } catch (error) {
            logError('Failed to delete chat session:', error)
            // Reload sessions on error to revert optimistic update
            const response = await apiClient.getChatSessions()
            set({ chatSessions: response?.sessions || [] })
            throw error
          }
        },

        loadModels: async () => {
          try {
            set({ modelsLoading: true });
            const response = await apiClient.getModels();

            // Build model list with catalog and availability
            const modelList = buildModelList(response.allowed_models);

            // Convert to ChatModel format for UI
            const models: ChatModel[] = modelList.map(({ model, available, backendId }) => ({
              id: model.slug,
              value: backendId || model.slug,
              label: model.displayName,
              description: model.description,
              tags: model.badges,
              available,
              backendId,
            }));

            // Get default model slug from backend default
            const defaultSlug = getDefaultModelSlug(response.default_model);

            logDebug('Models loaded', {
              backendModels: response.allowed_models,
              uiModels: models,
              defaultSlug,
            });

            set({ models, selectedModel: defaultSlug, modelsLoading: false });
          } catch (error) {
            logError('Failed to load models:', error);
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

        loadFeatureFlags: async () => {
          try {
            set({ featureFlagsLoading: true });
            const response = await apiClient.getFeatureFlags();
            set({ featureFlags: response, featureFlagsLoading: false });
          } catch (error) {
            logError('Failed to load feature flags:', error);
            set({ featureFlags: null, featureFlagsLoading: false });
          }
        },

        loadUnifiedHistory: async (chatId) => {
          try {
            set({ chatNotFound: false, messages: [], currentChatId: chatId })
            const historyData = await apiClient.getUnifiedChatHistory(chatId, 50, 0, true, false)

            // Convert history events to chat messages for current UI
            const messages: ChatMessage[] = []

            for (const event of historyData.events) {
              if (event.event_type === 'chat_message' && event.chat_data) {
                messages.push({
                  id: event.message_id || event.id,
                  role: event.chat_data.role,
                  content: event.chat_data.content,
                  timestamp: event.timestamp,
                  model: event.chat_data.model,
                  tokens: event.chat_data.tokens,
                  latency: event.chat_data.latency_ms,
                })
              }
              // TODO: Handle research events in UI
            }

            set({ messages, currentChatId: chatId })

          } catch (error: any) {
            logError('Failed to load unified history:', error)
            // Check if it's a 404 error (chat not found)
            if (error?.response?.status === 404) {
              set({ chatNotFound: true, messages: [], currentChatId: null })
            }
          }
        },

        refreshChatStatus: async (chatId) => {
          try {
            const statusData = await apiClient.getChatStatus(chatId)

            // Update active research tasks
            const researchTasks: ResearchTask[] = statusData.active_research.map((research: any) => ({
              id: research.task_id,
              status: 'running',
              progress: research.progress,
              title: research.current_step || 'Research in progress...',
              query: '', // Not available in status
              created_at: research.started_at,
              updated_at: new Date().toISOString(),
            }))

            set({ activeTasks: researchTasks })

          } catch (error) {
            logError('Failed to refresh chat status:', error)
          }
        },

        // Settings actions
        updateSettings: (newSettings) =>
          set((state) => ({
            settings: { ...state.settings, ...newSettings },
          })),

        // API actions
        sendMessage: async (content) => {
          const state = get()

          try {
            set({ isLoading: true })

            // Add user message immediately
            const userMessage: ChatMessage = {
              id: Date.now().toString(),
              content,
              role: 'user',
              timestamp: new Date().toISOString(),
            }

            get().addMessage(userMessage)

            // Resolve UI slug to backend ID
            const selectedModelData = state.models.find((m) => m.id === state.selectedModel)
            let backendModelId = selectedModelData?.backendId

            // Fallback: if backendId is null/undefined or equals the slug (not resolved),
            // try to get display name from catalog
            if (!backendModelId || backendModelId === state.selectedModel) {
              const catalogModel = getAllModels().find((m) => m.slug === state.selectedModel)
              backendModelId = catalogModel?.displayName || state.selectedModel
              logWarn('Using catalog fallback for model', {
                selectedModelSlug: state.selectedModel,
                originalBackendId: selectedModelData?.backendId,
                catalogModel: catalogModel?.displayName,
                fallbackValue: backendModelId,
                modelsArray: state.models.map(m => ({ id: m.id, backendId: m.backendId })),
              })
            }

            logDebug('Sending message with model', {
              uiSlug: state.selectedModel,
              backendId: backendModelId,
              modelsLoaded: state.models.length,
              selectedModelData: selectedModelData ? {
                id: selectedModelData.id,
                backendId: selectedModelData.backendId,
                available: selectedModelData.available,
              } : null,
            })

            if (!backendModelId) {
              throw new Error('No valid model ID resolved')
            }

            // Send to API
            const response = await apiClient.sendChatMessage({
              message: content,
              chat_id: state.currentChatId || undefined,
              model: backendModelId,
              temperature: state.settings.temperature,
              max_tokens: state.settings.maxTokens,
              stream: state.settings.streamEnabled,
              tools_enabled: state.toolsEnabled,
            })
            
            // Add assistant response
            const assistantMessage: ChatMessage = {
              id: response.message_id,
              content: response.content,
              role: 'assistant',
              timestamp: response.created_at,
              model: response.model,
              tokens: response.tokens,
              latency: response.latency_ms,
              toolsUsed: response.tools_used,
            }
            
            get().addMessage(assistantMessage)
            
            // Update chat ID if it's a new conversation
            if (!state.currentChatId) {
              set({ currentChatId: response.chat_id })
            }
            
          } catch (error) {
            logError('Failed to send message:', error)
            
            // Add error message
            const errorMessage: ChatMessage = {
              id: Date.now().toString(),
              content: 'Sorry, there was an error sending your message. Please try again.',
              role: 'assistant',
              timestamp: new Date().toISOString(),
              isError: true,
            }
            
            get().addMessage(errorMessage)
          } finally {
            set({ isLoading: false })
          }
        },

        startNewChat: () => {
          set({
            currentChatId: null,
            messages: [],
            isLoading: false,
          })
        },

        checkConnection: async () => {
          try {
            set({ connectionStatus: 'connecting' })
            const isConnected = await apiClient.checkConnection()
            set({ connectionStatus: isConnected ? 'connected' : 'disconnected' })
          } catch (error) {
            set({ connectionStatus: 'disconnected' })
          }
        },

        // Cache invalidation helpers
        invalidateOnContextChange: () => {
          // Called on login/logout or when API_BASE/user context changes
          set({
            currentChatId: null,
            messages: [],
            activeTasks: [],
            currentTaskId: null,
            chatSessions: [],
            connectionStatus: 'disconnected',
          })

          // Clear any persistent cache in localStorage that might be stale
          const cacheKeys = ['chat-cache', 'research-cache', 'session-cache']
          cacheKeys.forEach(key => {
            try {
              localStorage.removeItem(key)
            } catch (error) {
              logWarn(`Failed to clear cache key ${key}:`, error)
            }
          })
        },

        clearAllData: () => {
          // Nuclear option: clear all data and reset to initial state
          set({
            sidebarOpen: false,
            connectionStatus: 'disconnected',
            currentChatId: null,
            messages: [],
            isLoading: false,
            selectedModel: 'turbo', // Default to Saptiva Turbo
            toolsEnabled: defaultTools,
            activeTasks: [],
            currentTaskId: null,
            chatSessions: [],
            settings: defaultSettings,
          })

          // Clear all localStorage including our persisted state
          try {
            // Clear our persisted Zustand state
            localStorage.removeItem('copilotos-bridge-store')

            // Clear any additional cache keys
            const allCacheKeys = ['chat-cache', 'research-cache', 'session-cache', 'msw', 'mock-api', 'dev-mode']
            allCacheKeys.forEach(key => {
              localStorage.removeItem(key)
            })
          } catch (error) {
            logWarn('Failed to clear localStorage:', error)
          }
        },
      }),
      {
        name: 'copilotos-bridge-store',
        partialize: (state) => ({
          theme: state.theme,
          selectedModel: state.selectedModel,
          toolsEnabled: state.toolsEnabled,
          settings: state.settings,
        }),
      }
    ),
    {
      name: 'copilotos-bridge-store',
    }
  )
)

// Selectors for performance
export const useChat = () => {
  const store = useAppStore()
  return {
    currentChatId: store.currentChatId,
    messages: store.messages,
    isLoading: store.isLoading,
    models: store.models,
    modelsLoading: store.modelsLoading,
    featureFlags: store.featureFlags,
    featureFlagsLoading: store.featureFlagsLoading,
    selectedModel: store.selectedModel,
    toolsEnabled: store.toolsEnabled,
    chatSessions: store.chatSessions,
    chatSessionsLoading: store.chatSessionsLoading,
    chatNotFound: store.chatNotFound,
    sendMessage: store.sendMessage,
    startNewChat: store.startNewChat,
    addMessage: store.addMessage,
    updateMessage: store.updateMessage,
    clearMessages: store.clearMessages,
    setSelectedModel: store.setSelectedModel,
    toggleTool: store.toggleTool,
    setLoading: store.setLoading,
    loadChatSessions: store.loadChatSessions,
    loadModels: store.loadModels,
    loadFeatureFlags: store.loadFeatureFlags,
    addChatSession: store.addChatSession,
    removeChatSession: store.removeChatSession,
    renameChatSession: store.renameChatSession,
    pinChatSession: store.pinChatSession,
    deleteChatSession: store.deleteChatSession,
    setCurrentChatId: store.setCurrentChatId,
    loadUnifiedHistory: store.loadUnifiedHistory,
    refreshChatStatus: store.refreshChatStatus,
  }
}

export const useResearch = () => {
  const store = useAppStore()
  return {
    activeTasks: store.activeTasks,
    currentTaskId: store.currentTaskId,
    addTask: store.addTask,
    updateTask: store.updateTask,
    removeTask: store.removeTask,
    setCurrentTaskId: store.setCurrentTaskId,
  }
}

export const useUI = () => {
  const store = useAppStore()
  return {
    sidebarOpen: store.sidebarOpen,
    theme: store.theme,
    connectionStatus: store.connectionStatus,
    setSidebarOpen: store.setSidebarOpen,
    setTheme: store.setTheme,
    checkConnection: store.checkConnection,
    invalidateOnContextChange: store.invalidateOnContextChange,
    clearAllData: store.clearAllData,
  }
}

export const useSettings = () => {
  const store = useAppStore()
  return {
    settings: store.settings,
    updateSettings: store.updateSettings,
  }
}
