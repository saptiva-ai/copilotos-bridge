/**
 * Global state management with Zustand
 */

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import toast from 'react-hot-toast'
import { ChatMessage, ChatSession, ChatSessionOptimistic, ResearchTask, ChatModel, FeatureFlagsResponse } from './types'
import { apiClient } from './api-client'
import { logDebug, logError, logWarn } from './logger'
import { buildModelList, getDefaultModelSlug, resolveBackendId } from './modelMap'
import { getAllModels } from '../config/modelCatalog'
import { retryWithBackoff, defaultShouldRetry } from './retry'
import { getSyncInstance } from './sync'
import { DraftConversation, INITIAL_DRAFT_STATE, deriveTitleFromMessage } from './conversation-utils'

// App state interfaces
interface AppState {
  // UI state
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  connectionStatus: 'connected' | 'disconnected' | 'connecting'

  // Chat state
  currentChatId: string | null
  selectionEpoch: number  // Incremented on same-chat re-selection to force re-render
  messages: ChatMessage[]
  isLoading: boolean
  models: ChatModel[]
  modelsLoading: boolean
  selectedModel: string
  toolsEnabled: Record<string, boolean>

  // Hydration state (stale-while-revalidate pattern)
  hydratedByChatId: Record<string, boolean>
  isHydratingByChatId: Record<string, boolean>
  
  // Research state
  activeTasks: ResearchTask[]
  currentTaskId: string | null
  
  // History
  chatSessions: ChatSession[]
  chatSessionsLoading: boolean
  chatNotFound: boolean

  // P0-UX-HIST-001: Optimistic conversation creation
  isCreatingConversation: boolean
  optimisticConversations: Map<string, ChatSessionOptimistic>

  // Pending operations counter for global loader
  pendingOps: number

  // Timeout refs for creation lifecycle (to ensure cleanup)
  createTimeoutById: Record<string, number | undefined>

  // Draft conversation state (memory-only, no backend persistence)
  draft: DraftConversation

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
  switchChat: (nextId: string) => void  // Handles re-selection with epoch bumping
  bumpSelectionEpoch: () => void
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

  // P0-UX-HIST-001: Optimistic conversation actions
  createConversationOptimistic: () => string
  reconcileConversation: (tempId: string, realSession: ChatSession) => void
  removeOptimisticConversation: (tempId: string) => void
  finalizeCreation: (tempId: string) => void
  cancelCreation: (tempId: string) => void

  // Draft conversation actions (progressive commitment pattern)
  openDraft: () => void
  discardDraft: () => void
  setDraftText: (text: string) => void
  isDraftMode: () => boolean

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
        selectionEpoch: 0,
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
        isCreatingConversation: false,
        optimisticConversations: new Map(),
        pendingOps: 0,
        createTimeoutById: {},
        draft: INITIAL_DRAFT_STATE,
        settings: defaultSettings,
        featureFlags: null,
        featureFlagsLoading: false,
        hydratedByChatId: {},
        isHydratingByChatId: {},

        // UI actions
        setSidebarOpen: (open) => set({ sidebarOpen: open }),
        setTheme: (theme) => set({ theme }),
        setConnectionStatus: (status) => set({ connectionStatus: status }),

        // Chat actions
        setCurrentChatId: (chatId) => set({ currentChatId: chatId }),

        // Switch chat with re-selection support (A→B→C→A pattern)
        switchChat: (nextId: string) => {
          const { currentChatId, selectionEpoch } = get()

          // Always set the activeId AND bump epoch
          // This ensures every chat selection triggers a fresh mount, preventing "memoria fantasma"
          const isReselection = currentChatId === nextId
          const newEpoch = selectionEpoch + 1

          logDebug('SWITCH_CHAT', {
            from: currentChatId,
            to: nextId,
            reselection: isReselection,
            epochBefore: selectionEpoch,
            epochAfter: newEpoch
          })

          set({
            currentChatId: nextId,
            selectionEpoch: newEpoch
          })
        },

        bumpSelectionEpoch: () => {
          const epoch = get().selectionEpoch
          logDebug('BUMP_EPOCH', { from: epoch, to: epoch + 1 })
          set({ selectionEpoch: epoch + 1 })
        },

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

            // Note: No broadcast here - only individual mutations broadcast
            // This prevents infinite loops from sync listeners calling loadChatSessions
          } catch (error) {
            logError('Failed to load chat sessions:', error)
            set({ chatSessions: [], chatSessionsLoading: false })
          }
        },
        
        addChatSession: (session) => {
          set((state) => ({
            chatSessions: [session, ...state.chatSessions],
          }))

          // Broadcast to other tabs
          getSyncInstance().broadcast('session_created', { session })
        },
        
        removeChatSession: (chatId) =>
          set((state) => ({
            chatSessions: state.chatSessions.filter((session) => session.id !== chatId),
            currentChatId: state.currentChatId === chatId ? null : state.currentChatId,
            messages: state.currentChatId === chatId ? [] : state.messages,
          })),

        renameChatSession: async (chatId: string, newTitle: string) => {
          const previousSessions = get().chatSessions

          try {
            // Optimistic update
            set((state) => ({
              chatSessions: state.chatSessions.map((session) =>
                session.id === chatId ? { ...session, title: newTitle } : session
              ),
            }))

            // Retry with exponential backoff
            await retryWithBackoff(
              () => apiClient.renameChatSession(chatId, newTitle),
              {
                maxRetries: 3,
                baseDelay: 1000,
                shouldRetry: defaultShouldRetry,
                onRetry: (error, attempt, delay) => {
                  logWarn(`Retrying rename (attempt ${attempt})`, { chatId, delay, error: error.message })
                  toast.loading(`Reintentando renombrar... (${attempt}/3)`, {
                    id: `rename-retry-${chatId}`,
                    duration: delay
                  })
                },
              }
            )

            // Success toast
            toast.success('Conversación renombrada', { id: `rename-retry-${chatId}` })
            logDebug('Chat session renamed', { chatId, newTitle })

            // Broadcast to other tabs
            getSyncInstance().broadcast('session_renamed', { chatId })
          } catch (error) {
            logError('Failed to rename chat session:', error)

            // Rollback optimistic update
            set({ chatSessions: previousSessions })

            // Error toast with retry action
            toast.error('Error al renombrar la conversación', {
              id: `rename-retry-${chatId}`,
              duration: 5000,
            })

            throw error
          }
        },

        pinChatSession: async (chatId: string) => {
          const previousSessions = get().chatSessions
          const session = previousSessions.find((s) => s.id === chatId)
          const newPinnedState = !session?.pinned

          try {
            // Optimistic update
            set((state) => ({
              chatSessions: state.chatSessions.map((s) =>
                s.id === chatId ? { ...s, pinned: newPinnedState } : s
              ),
            }))

            // Retry with exponential backoff
            await retryWithBackoff(
              () => apiClient.pinChatSession(chatId, newPinnedState),
              {
                maxRetries: 3,
                baseDelay: 1000,
                shouldRetry: defaultShouldRetry,
                onRetry: (error, attempt, delay) => {
                  logWarn(`Retrying pin (attempt ${attempt})`, { chatId, delay, error: error.message })
                  toast.loading(`Reintentando... (${attempt}/3)`, {
                    id: `pin-retry-${chatId}`,
                    duration: delay
                  })
                },
              }
            )

            // Success toast (subtle, short duration)
            toast.success(newPinnedState ? 'Conversación fijada' : 'Conversación desfijada', {
              id: `pin-retry-${chatId}`,
              duration: 2000,
            })
            logDebug('Chat session pin toggled', { chatId, pinned: newPinnedState })

            // Broadcast to other tabs
            getSyncInstance().broadcast('session_pinned', { chatId })
          } catch (error) {
            logError('Failed to pin chat session:', error)

            // Rollback optimistic update
            set({ chatSessions: previousSessions })

            // Error toast
            toast.error('Error al fijar la conversación', {
              id: `pin-retry-${chatId}`,
              duration: 4000,
            })

            throw error
          }
        },

        deleteChatSession: async (chatId: string) => {
          const previousSessions = get().chatSessions
          const previousChatId = get().currentChatId
          const previousMessages = get().messages

          try {
            // Optimistic update
            set((state) => ({
              chatSessions: state.chatSessions.filter((session) => session.id !== chatId),
              currentChatId: state.currentChatId === chatId ? null : state.currentChatId,
              messages: state.currentChatId === chatId ? [] : state.messages,
            }))

            // Retry with exponential backoff
            await retryWithBackoff(
              () => apiClient.deleteChatSession(chatId),
              {
                maxRetries: 3,
                baseDelay: 1000,
                shouldRetry: defaultShouldRetry,
                onRetry: (error, attempt, delay) => {
                  logWarn(`Retrying delete (attempt ${attempt})`, { chatId, delay, error: error.message })
                  toast.loading(`Reintentando eliminar... (${attempt}/3)`, {
                    id: `delete-retry-${chatId}`,
                    duration: delay
                  })
                },
              }
            )

            // Success toast
            toast.success('Conversación eliminada', {
              id: `delete-retry-${chatId}`,
              duration: 3000,
            })
            logDebug('Chat session deleted', { chatId })

            // Broadcast to other tabs
            getSyncInstance().broadcast('session_deleted', { chatId })
          } catch (error) {
            logError('Failed to delete chat session:', error)

            // Rollback optimistic update
            set({
              chatSessions: previousSessions,
              currentChatId: previousChatId,
              messages: previousMessages,
            })

            // Error toast
            toast.error('Error al eliminar la conversación', {
              id: `delete-retry-${chatId}`,
              duration: 5000,
            })

            throw error
          }
        },

        // P0-UX-HIST-001: Optimistic conversation creation with lifecycle state machine
        createConversationOptimistic: () => {
          // Anti-spam: limit concurrent creating conversations
          const state = get()
          if (state.pendingOps > 10) {
            logWarn('Too many pending operations, blocking new conversation creation')
            return ''
          }

          const tempId = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
          const now = new Date().toISOString()

          const optimisticSession: ChatSessionOptimistic = {
            id: tempId,
            tempId,
            title: 'Nueva conversación',
            created_at: now,
            updated_at: now,
            first_message_at: null,
            last_message_at: null,
            message_count: 0,
            model: get().selectedModel,
            preview: '',
            isOptimistic: true,
            isNew: true,
            state: 'creating', // Lifecycle: empieza en 'creating'
          }

          set((state) => {
            const newOptimisticConversations = new Map(state.optimisticConversations)
            newOptimisticConversations.set(tempId, optimisticSession)
            return {
              isCreatingConversation: true,
              optimisticConversations: newOptimisticConversations,
              pendingOps: state.pendingOps + 1, // Increment global loader counter
            }
          })

          logDebug('Created optimistic conversation', { tempId, state: 'creating', pendingOps: get().pendingOps })

          // IMPORTANTE: No podemos usar get().finalizeCreation dentro de setTimeout porque Zustand
          // puede no tener la función actualizada. Debemos definir finalizeCreation inline aquí.

          // Función inline para finalizar (se reutiliza en timeout y watchdog)
          const finalize = () => {
            logDebug('🔵 Timeout/Watchdog triggering finalization', { tempId })
            const currentState = get()

            // Clear timeout if exists
            const timeout = currentState.createTimeoutById[tempId]
            if (timeout) {
              clearTimeout(timeout)
            }

            // Transition: creating → draft
            set((state) => {
              const newOptimisticConversations = new Map(state.optimisticConversations)
              const session = newOptimisticConversations.get(tempId)

              if (!session) {
                logWarn('🔵 Finalize: session not found', { tempId })
                return state
              }

              if (session.state !== 'creating') {
                logDebug('🔵 Finalize: already finalized', { tempId, currentState: session.state })
                return state
              }

              newOptimisticConversations.set(tempId, {
                ...session,
                state: 'draft',
                isNew: false,
              })

              const newTimeoutById = { ...state.createTimeoutById }
              delete newTimeoutById[tempId]

              const newPendingOps = Math.max(0, state.pendingOps - 1)
              logDebug('🔵 Finalize: success (inline)', {
                tempId,
                from: 'creating',
                to: 'draft',
                pendingOps: `${state.pendingOps} → ${newPendingOps}`,
              })

              return {
                optimisticConversations: newOptimisticConversations,
                isCreatingConversation: newOptimisticConversations.size > 0,
                pendingOps: newPendingOps,
                createTimeoutById: newTimeoutById,
              }
            })
          }

          // Lifecycle: Finalizar creación tras 1s (creating → draft)
          const transitionTimeout = window.setTimeout(finalize, 1000)

          // Store timeout ref for cleanup
          set((state) => ({
            createTimeoutById: { ...state.createTimeoutById, [tempId]: transitionTimeout },
          }))

          // Watchdog: Garantizar finalización tras 5s (última barrera)
          window.setTimeout(() => {
            const session = get().optimisticConversations.get(tempId)
            if (session && session.state === 'creating') {
              logWarn('🔴 Watchdog triggered: forcing finalization', { tempId })
              finalize()
            } else {
              logDebug('🟢 Watchdog checked: already finalized', { tempId, state: session?.state })
            }
          }, 5000)

          return tempId
        },

        finalizeCreation: (tempId: string) => {
          logDebug('🔵 FINALIZE_CREATION called', { tempId })
          const state = get()

          // Clear timeout if exists
          const timeout = state.createTimeoutById[tempId]
          if (timeout) {
            logDebug('🔵 Clearing timeout', { tempId, timeoutId: timeout })
            clearTimeout(timeout)
          }

          // Idempotent: only transition if still in 'creating' state
          set((state) => {
            const newOptimisticConversations = new Map(state.optimisticConversations)
            const session = newOptimisticConversations.get(tempId)

            if (!session) {
              // Session already removed (reconciled or cancelled)
              logWarn('🔵 FINALIZE_CREATION: session not found', { tempId })
              return state
            }

            if (session.state !== 'creating') {
              // Already finalized
              logDebug('🔵 FINALIZE_CREATION: already finalized', { tempId, currentState: session.state })
              return state
            }

            // Transition: creating → draft
            newOptimisticConversations.set(tempId, {
              ...session,
              state: 'draft',
              isNew: false, // Remove highlight after animation
            })

            const newTimeoutById = { ...state.createTimeoutById }
            delete newTimeoutById[tempId]

            const newPendingOps = Math.max(0, state.pendingOps - 1)
            logDebug('🔵 FINALIZE_CREATION: success', {
              tempId,
              from: 'creating',
              to: 'draft',
              pendingOps: `${state.pendingOps} → ${newPendingOps}`,
            })

            return {
              optimisticConversations: newOptimisticConversations,
              isCreatingConversation: newOptimisticConversations.size > 0,
              pendingOps: newPendingOps, // Decrement global loader
              createTimeoutById: newTimeoutById,
            }
          })
        },

        cancelCreation: (tempId: string) => {
          const state = get()

          // Clear timeout if exists
          const timeout = state.createTimeoutById[tempId]
          if (timeout) {
            clearTimeout(timeout)
          }

          set((state) => {
            const newOptimisticConversations = new Map(state.optimisticConversations)
            const session = newOptimisticConversations.get(tempId)

            // Decrement pendingOps if session was in 'creating' state
            const wasPending = session && session.state === 'creating'

            newOptimisticConversations.delete(tempId)

            const newTimeoutById = { ...state.createTimeoutById }
            delete newTimeoutById[tempId]

            logDebug('Cancelled conversation creation', { tempId })

            return {
              optimisticConversations: newOptimisticConversations,
              isCreatingConversation: newOptimisticConversations.size > 0,
              pendingOps: wasPending ? Math.max(0, state.pendingOps - 1) : state.pendingOps,
              createTimeoutById: newTimeoutById,
            }
          })
        },

        reconcileConversation: (tempId: string, realSession: ChatSession) => {
          const state = get()

          // Clear timeout if exists (cleanup)
          const timeout = state.createTimeoutById[tempId]
          if (timeout) {
            clearTimeout(timeout)
          }

          set((state) => {
            const newOptimisticConversations = new Map(state.optimisticConversations)
            const optimisticSession = newOptimisticConversations.get(tempId)

            // Decrement pendingOps if session was still in 'creating' state
            const wasPending = optimisticSession && optimisticSession.state === 'creating'

            // Remove from optimistic map
            newOptimisticConversations.delete(tempId)

            // Add real session to chatSessions if not already there
            const sessionExists = state.chatSessions.some((s) => s.id === realSession.id)
            const newChatSessions = sessionExists
              ? state.chatSessions
              : [{ ...realSession, isNew: true } as ChatSessionOptimistic, ...state.chatSessions]

            const newTimeoutById = { ...state.createTimeoutById }
            delete newTimeoutById[tempId]

            return {
              optimisticConversations: newOptimisticConversations,
              chatSessions: newChatSessions,
              isCreatingConversation: newOptimisticConversations.size > 0,
              pendingOps: wasPending ? Math.max(0, state.pendingOps - 1) : state.pendingOps,
              createTimeoutById: newTimeoutById,
            }
          })

          // Broadcast to other tabs
          getSyncInstance().broadcast('session_created', { session: realSession })

          logDebug('Reconciled optimistic conversation', { tempId, realId: realSession.id })

          // Clear isNew flag after highlight duration (2 seconds)
          setTimeout(() => {
            set((state) => ({
              chatSessions: state.chatSessions.map((s) =>
                s.id === realSession.id ? { ...s, isNew: false } as ChatSession : s
              ),
            }))
          }, 2000)
        },

        removeOptimisticConversation: (tempId: string) => {
          const state = get()

          // Clear timeout if exists
          const timeout = state.createTimeoutById[tempId]
          if (timeout) {
            clearTimeout(timeout)
          }

          set((state) => {
            const newOptimisticConversations = new Map(state.optimisticConversations)
            const session = newOptimisticConversations.get(tempId)

            // Decrement pendingOps if session was in 'creating' state
            const wasPending = session && session.state === 'creating'

            newOptimisticConversations.delete(tempId)

            const newTimeoutById = { ...state.createTimeoutById }
            delete newTimeoutById[tempId]

            return {
              optimisticConversations: newOptimisticConversations,
              isCreatingConversation: newOptimisticConversations.size > 0,
              pendingOps: wasPending ? Math.max(0, state.pendingOps - 1) : state.pendingOps,
              createTimeoutById: newTimeoutById,
            }
          })

          logDebug('Removed optimistic conversation', { tempId })
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

        // Draft conversation actions - Progressive Commitment Pattern
        openDraft: () => {
          set({
            draft: {
              isDraftMode: true,
              draftText: '',
              draftModel: get().selectedModel,
            },
            currentChatId: null,
            messages: [],
            chatNotFound: false,
            isLoading: false, // Clear loading state to show hero mode
          })
          logDebug('Draft mode activated', { model: get().selectedModel })
        },

        discardDraft: () => {
          const hadText = get().draft.draftText.length > 0
          set({
            draft: INITIAL_DRAFT_STATE,
            isLoading: false, // Clear loading state when discarding draft
          })
          logDebug('Draft discarded', { hadText })
        },

        setDraftText: (text: string) => {
          set((state) => ({
            draft: { ...state.draft, draftText: text }
          }))
        },

        isDraftMode: () => {
          return get().draft.isDraftMode
        },

        loadUnifiedHistory: async (chatId) => {
          const state = get()

          // SWR deduplication: Don't load if already hydrated or currently hydrating
          if (state.hydratedByChatId[chatId] || state.isHydratingByChatId[chatId]) {
            logDebug('Skipping load - already hydrated/hydrating', { chatId })
            return
          }

          try {
            // Mark as hydrating (prevents duplicate calls)
            set((s) => ({
              isHydratingByChatId: { ...s.isHydratingByChatId, [chatId]: true },
              chatNotFound: false,
              currentChatId: chatId,
              // SWR: DON'T clear messages here - keep stale data visible
            }))

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

            // Atomic replacement: set messages only when data arrives
            set((s) => ({
              messages,
              currentChatId: chatId,
              hydratedByChatId: { ...s.hydratedByChatId, [chatId]: true },
              isHydratingByChatId: { ...s.isHydratingByChatId, [chatId]: false },
            }))

            logDebug('Chat hydrated', { chatId, messageCount: messages.length })

          } catch (error: any) {
            logError('Failed to load unified history:', error)

            // Mark hydration as failed
            set((s) => ({
              isHydratingByChatId: { ...s.isHydratingByChatId, [chatId]: false },
            }))

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

            // Progressive Commitment: If in draft mode, create conversation FIRST
            if (state.draft.isDraftMode) {
              const title = deriveTitleFromMessage(content)
              const now = new Date().toISOString()

              logDebug('Creating conversation from draft (first message)', { title })

              // Create conversation with derived title
              const conversation = await apiClient.createConversation({
                title,
                model: state.draft.draftModel || state.selectedModel,
              })

              // Exit draft mode and set the new chat ID
              set({
                draft: INITIAL_DRAFT_STATE,
                currentChatId: conversation.id,
              })

              logDebug('Conversation created from first message', {
                chatId: conversation.id,
                title,
                messageLength: content.length,
              })
            }

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
            
            // P0-UX-HIST-001: Reconcile optimistic conversation if tempId was used
            const wasTempId = state.currentChatId && state.currentChatId.startsWith('temp-')

            // Update chat ID to real ID from response
            if (!state.currentChatId || wasTempId) {
              set({ currentChatId: response.chat_id })
            }

            // Reconcile optimistic conversation with real session
            if (wasTempId && state.currentChatId) {
              const tempId = state.currentChatId

              // Fetch the real session data
              try {
                const sessionsResponse = await apiClient.getChatSessions()
                const realSession = sessionsResponse?.sessions?.find((s: ChatSession) => s.id === response.chat_id)

                if (realSession) {
                  get().reconcileConversation(tempId, realSession)
                  logDebug('Optimistic conversation reconciled', { tempId, realId: response.chat_id })
                }
              } catch (reconcileError) {
                logError('Failed to reconcile optimistic conversation:', reconcileError)
                // Just remove the optimistic one if reconciliation fails
                get().removeOptimisticConversation(tempId)
              }
            } else {
              // If no optimistic ID was used, still reload sessions to get the new one
              get().loadChatSessions()
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
          // Progressive Commitment: Use draft mode instead of creating empty conversation
          get().openDraft()
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
    selectionEpoch: store.selectionEpoch,
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
    switchChat: store.switchChat,
    bumpSelectionEpoch: store.bumpSelectionEpoch,
    loadUnifiedHistory: store.loadUnifiedHistory,
    refreshChatStatus: store.refreshChatStatus,
    // P0-UX-HIST-001: Optimistic UI
    isCreatingConversation: store.isCreatingConversation,
    optimisticConversations: store.optimisticConversations,
    createConversationOptimistic: store.createConversationOptimistic,
    reconcileConversation: store.reconcileConversation,
    removeOptimisticConversation: store.removeOptimisticConversation,
    finalizeCreation: store.finalizeCreation,
    cancelCreation: store.cancelCreation,
    // Progressive Commitment: Draft state
    draft: store.draft,
    openDraft: store.openDraft,
    discardDraft: store.discardDraft,
    setDraftText: store.setDraftText,
    isDraftMode: store.isDraftMode,
    // Hydration state (SWR pattern)
    hydratedByChatId: store.hydratedByChatId,
    isHydratingByChatId: store.isHydratingByChatId,
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
