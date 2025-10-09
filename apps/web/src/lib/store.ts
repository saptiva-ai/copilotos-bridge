/**
 * Global state management with Zustand
 */

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import toast from 'react-hot-toast'
import { ChatMessage, ChatSession, ChatSessionOptimistic, ResearchTask, ChatModel, FeatureFlagsResponse } from './types'
import { apiClient } from './api-client'
import { logDebug, logError, logWarn } from './logger'
import { logAction } from './ux-logger'
import { buildModelList, getDefaultModelSlug, resolveBackendId } from './modelMap'
import { getAllModels } from '../config/modelCatalog'
import { retryWithBackoff, defaultShouldRetry } from './retry'
import { getSyncInstance } from './sync'
import { DraftConversation, INITIAL_DRAFT_STATE, deriveTitleFromMessage, generateTitleFromMessage, computeTitleFromText } from './conversation-utils'
import { hasFirstMessage } from './types'
import { createDefaultToolsState, normalizeToolsState } from './tool-mapping'

const mergeToolsState = (seed?: Record<string, boolean>) => {
  const extraKeys = seed ? Object.keys(seed) : []
  const base = createDefaultToolsState(extraKeys)
  return seed ? { ...base, ...seed } : base
}

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
  toolsEnabledByChatId: Record<string, Record<string, boolean>>
  draftToolsEnabled: Record<string, boolean>

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
  pendingCreationId: string | null

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
  toggleTool: (toolName: string) => Promise<void>
  setToolEnabled: (toolName: string, enabled: boolean) => Promise<void>
  
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
  updateSessionTitle: (chatId: string, newTitle: string) => void  // Optimistic title update
  loadUnifiedHistory: (chatId: string) => Promise<void>
  refreshChatStatus: (chatId: string) => Promise<void>
  loadModels: () => Promise<void>
  loadFeatureFlags: () => Promise<void>

  // P0-UX-HIST-001: Optimistic conversation actions
  createConversationOptimistic: (tempId?: string, createdAt?: string, idempotencyKey?: string) => string
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
        toolsEnabled: mergeToolsState(),
        toolsEnabledByChatId: {},
        draftToolsEnabled: mergeToolsState(),
        activeTasks: [],
        currentTaskId: null,
        chatSessions: [],
        chatSessionsLoading: false,
        chatNotFound: false,
        isCreatingConversation: false,
        pendingCreationId: null,
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
        setCurrentChatId: (chatId) => {
          const state = get()
          const nextToolsByChat = { ...state.toolsEnabledByChatId }
          let resolvedTools: Record<string, boolean>

          if (chatId) {
            if (!nextToolsByChat[chatId]) {
              nextToolsByChat[chatId] = mergeToolsState()
            }
            resolvedTools = mergeToolsState(nextToolsByChat[chatId])
          } else {
            resolvedTools = mergeToolsState(state.draftToolsEnabled)
          }

          set({
            currentChatId: chatId,
            toolsEnabled: resolvedTools,
            toolsEnabledByChatId: nextToolsByChat,
          })
        },

        // Switch chat with re-selection support (A→B→C→A pattern)
        switchChat: (nextId: string) => {
          const {
            currentChatId,
            selectionEpoch,
            hydratedByChatId,
            isHydratingByChatId,
            toolsEnabledByChatId,
            draftToolsEnabled,
          } = get()

          // Always set the activeId AND bump epoch
          // This ensures every chat selection triggers a fresh mount, preventing "memoria fantasma"
          const isReselection = currentChatId === nextId
          const newEpoch = selectionEpoch + 1

          // CRITICAL: Invalidate hydration for the target chat to force reload
          // This prevents showing stale messages when returning to a chat (A→B→A)
          const newHydratedByChatId = { ...hydratedByChatId }
          delete newHydratedByChatId[nextId]

          // CRITICAL: Also clear isHydratingByChatId flag to allow loadUnifiedHistory to execute
          // If we don't clear this, loadUnifiedHistory will see the flag and early return,
          // leaving messages=[] and showing Hero instead of loading new data
          const newIsHydratingByChatId = { ...isHydratingByChatId }
          delete newIsHydratingByChatId[nextId]

          const nextToolsByChat = { ...toolsEnabledByChatId }
          if (!nextToolsByChat[nextId]) {
            nextToolsByChat[nextId] = mergeToolsState()
          }

          const resolvedTools = mergeToolsState(nextToolsByChat[nextId] || draftToolsEnabled)

          logDebug('SWITCH_CHAT', {
            from: currentChatId,
            to: nextId,
            reselection: isReselection,
            epochBefore: selectionEpoch,
            epochAfter: newEpoch,
            invalidateHydration: true,
            clearingMessages: true,
            clearingHydratingFlag: true,
            settingLoading: true
          })

          set({
            currentChatId: nextId,
            selectionEpoch: newEpoch,
            hydratedByChatId: newHydratedByChatId,
            isHydratingByChatId: newIsHydratingByChatId,
            messages: [],  // CRITICAL: Clear messages immediately to prevent showing B's messages when switching to A
            isLoading: true,  // CRITICAL: Set loading to prevent Hero from showing during async data load
            toolsEnabledByChatId: nextToolsByChat,
            toolsEnabled: resolvedTools,
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
        
        toggleTool: async (toolName) => {
          const state = get()
          const currentValue = state.toolsEnabled[toolName] ?? false
          await get().setToolEnabled(toolName, !currentValue)
        },

        setToolEnabled: async (toolName, enabled) => {
          const state = get()
          const currentValue = state.toolsEnabled[toolName] ?? false
          if (currentValue === enabled) {
            return
          }

          const nextTools = mergeToolsState({
            ...state.toolsEnabled,
            [toolName]: enabled,
          })

          const currentChatId = state.currentChatId
          const nextToolsByChat = { ...state.toolsEnabledByChatId }

          if (currentChatId) {
            nextToolsByChat[currentChatId] = nextTools
          }

          set({
            toolsEnabled: nextTools,
            toolsEnabledByChatId: nextToolsByChat,
            draftToolsEnabled: currentChatId ? state.draftToolsEnabled : nextTools,
          })

          logAction('tool.toggle.changed', { tool: toolName, enabled })

          if (currentChatId && !currentChatId.startsWith('temp-')) {
            try {
              await apiClient.updateChatSession(currentChatId, { tools_enabled: nextTools })
            } catch (error) {
              logError('Failed to update tools-enabled state', error)
              toast.error('No se pudo actualizar la configuración de herramientas.')

              const rollbackTools = mergeToolsState({
                ...state.toolsEnabled,
                [toolName]: currentValue,
              })

              set((prevState) => {
                const rollbackMap = { ...prevState.toolsEnabledByChatId }
                if (currentChatId) {
                  rollbackMap[currentChatId] = rollbackTools
                }
                return {
                  toolsEnabled: rollbackTools,
                  toolsEnabledByChatId: rollbackMap,
                }
              })
            }
          }
        },

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
            const sessions: ChatSession[] = response?.sessions || []

            const state = get()
            const nextToolsByChat: Record<string, Record<string, boolean>> = {}

            sessions.forEach((session: ChatSession) => {
              nextToolsByChat[session.id] = mergeToolsState(session.tools_enabled)
            })

            // Preserve optimistic conversations (temp IDs)
            Object.entries(state.toolsEnabledByChatId).forEach(([chatId, tools]) => {
              if (chatId.startsWith('temp-')) {
                nextToolsByChat[chatId] = mergeToolsState(tools)
              }
            })

            let mergedSessions: ChatSession[] = sessions
            let pendingCreationId = state.pendingCreationId
            let isCreatingConversation = state.isCreatingConversation

            if (pendingCreationId) {
              const pendingSession = state.chatSessions.find(
                (session) => session.id === pendingCreationId && (session as ChatSessionOptimistic).isOptimistic
              )

              if (pendingSession) {
                mergedSessions = [
                  pendingSession,
                  ...sessions.filter((session) => session.id !== pendingCreationId),
                ]

                nextToolsByChat[pendingCreationId] = mergeToolsState(
                  state.toolsEnabledByChatId[pendingCreationId] || state.toolsEnabled
                )
              } else {
                pendingCreationId = null
                isCreatingConversation = false
              }
            }

            const activeChatId = state.currentChatId
            const nextTools = activeChatId
              ? mergeToolsState(nextToolsByChat[activeChatId])
              : mergeToolsState(state.draftToolsEnabled)

            set({
              chatSessions: mergedSessions,
              chatSessionsLoading: false,
              toolsEnabledByChatId: nextToolsByChat,
              toolsEnabled: nextTools,
              pendingCreationId,
              isCreatingConversation,
            })

            // Note: No broadcast here - only individual mutations broadcast
            // This prevents infinite loops from sync listeners calling loadChatSessions
          } catch (error) {
            logError('Failed to load chat sessions:', error)
            set({ chatSessions: [], chatSessionsLoading: false })
          }
        },
        
        addChatSession: (session) => {
          set((state) => {
            const existing = state.chatSessions.filter((s) => s.id !== session.id)
            const sessionTools = mergeToolsState(session.tools_enabled)
            const nextToolsByChat = {
              ...state.toolsEnabledByChatId,
              [session.id]: sessionTools,
            }

            const isCurrent = state.currentChatId === session.id

            return {
              chatSessions: [session, ...existing],
              pendingCreationId: state.pendingCreationId === session.id ? null : state.pendingCreationId,
              isCreatingConversation: state.pendingCreationId === session.id ? false : state.isCreatingConversation,
              toolsEnabledByChatId: nextToolsByChat,
              toolsEnabled: isCurrent ? sessionTools : state.toolsEnabled,
            }
          })

          // Broadcast to other tabs
          getSyncInstance().broadcast('session_created', { session })
        },

        removeChatSession: (chatId) =>
          set((state) => {
            const filteredSessions = state.chatSessions.filter((session) => session.id !== chatId)
            const nextMap = { ...state.toolsEnabledByChatId }
            delete nextMap[chatId]

            const isCurrent = state.currentChatId === chatId
            return {
              chatSessions: filteredSessions,
              currentChatId: isCurrent ? null : state.currentChatId,
              messages: isCurrent ? [] : state.messages,
              toolsEnabledByChatId: nextMap,
              toolsEnabled: isCurrent ? mergeToolsState(state.draftToolsEnabled) : state.toolsEnabled,
            }
          }),

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

            // Wait briefly for MongoDB to persist the change
            // This prevents race conditions with other loadChatSessions() calls
            await new Promise(resolve => setTimeout(resolve, 200))

            // Reload sessions from backend to ensure consistency
            await get().loadChatSessions()

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

            // Wait briefly for MongoDB to persist the change
            await new Promise(resolve => setTimeout(resolve, 200))

            // Reload sessions from backend to ensure consistency
            await get().loadChatSessions()

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

        // Optimistic title update - Used by auto-titling to avoid race conditions
        updateSessionTitle: (chatId: string, newTitle: string) => {
          set((state) => ({
            chatSessions: state.chatSessions.map((session) =>
              session.id === chatId
                ? { ...session, title: newTitle, updated_at: new Date().toISOString() }
                : session
            )
          }))

          logDebug('Optimistically updated session title', { chatId, newTitle })
        },

        // P0-UX-HIST-001: Optimistic conversation creation with single-flight guard
        createConversationOptimistic: (providedTempId?: string, providedCreatedAt?: string, providedIdempotencyKey?: string) => {
          const generatedKey =
            typeof crypto !== 'undefined' && 'randomUUID' in crypto
              ? crypto.randomUUID()
              : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
          const idempotencyKey = providedIdempotencyKey || generatedKey
          const tempId = providedTempId || `temp-${idempotencyKey}`
          const now = providedCreatedAt || new Date().toISOString()

          const draftTools = mergeToolsState(get().draftToolsEnabled)

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
            pending: true,
            state: 'creating',
            idempotency_key: idempotencyKey,
            tools_enabled: draftTools,
          }

          set((state) => {
            const withoutDuplicate = state.chatSessions.filter((session) => session.id !== tempId)
            const sessionTools = draftTools
            return {
              chatSessions: [optimisticSession, ...withoutDuplicate],
              isCreatingConversation: true,
              pendingCreationId: tempId,
              toolsEnabledByChatId: {
                ...state.toolsEnabledByChatId,
                [tempId]: sessionTools,
              },
              toolsEnabled: sessionTools,
            }
          })

          logDebug('Created optimistic conversation', { tempId })
          return tempId
        },

        finalizeCreation: (tempId: string) => {
          set((state) => {
            const idx = state.chatSessions.findIndex((session) => session.id === tempId)
            if (idx === -1) {
              return state
            }

            const session = state.chatSessions[idx] as ChatSessionOptimistic
            if (!session.isOptimistic || session.pending === false) {
              return state
            }

            const updatedSession: ChatSessionOptimistic = {
              ...session,
              pending: false,
              state: session.state === 'creating' ? 'draft' : session.state,
              isNew: session.isNew ?? true,
            }

            const nextSessions = [...state.chatSessions]
            nextSessions[idx] = updatedSession

            return {
              chatSessions: nextSessions,
            }
          })

          logDebug('Finalized optimistic conversation', { tempId })
        },

        cancelCreation: (tempId: string) => {
          logWarn('Cancelling optimistic conversation', { tempId })
          get().removeOptimisticConversation(tempId)
        },

        reconcileConversation: (tempId: string, realSession: ChatSession) => {
          set((state) => {
            const filteredSessions = state.chatSessions.filter(
              (session) => session.id !== tempId && session.id !== realSession.id
            )

            const hydratedSession: ChatSessionOptimistic = {
              ...realSession,
              isOptimistic: false,
              isNew: true,
              pending: false,
            }

            const tempTools = state.toolsEnabledByChatId[tempId] || state.toolsEnabled
            const resolvedTools = mergeToolsState(realSession.tools_enabled || tempTools)
            const nextToolsByChat = { ...state.toolsEnabledByChatId }
            delete nextToolsByChat[tempId]
            nextToolsByChat[realSession.id] = resolvedTools

            const isCurrentTemp = state.currentChatId === tempId

            return {
              chatSessions: [hydratedSession, ...filteredSessions],
              isCreatingConversation: state.pendingCreationId === tempId ? false : state.isCreatingConversation,
              pendingCreationId: state.pendingCreationId === tempId ? null : state.pendingCreationId,
              toolsEnabledByChatId: nextToolsByChat,
              toolsEnabled: isCurrentTemp ? resolvedTools : state.toolsEnabled,
            }
          })

          // Broadcast to other tabs so they can refresh history state
          getSyncInstance().broadcast('session_created', { session: realSession })

          logDebug('Reconciled optimistic conversation', { tempId, realId: realSession.id })

          // Clear highlight after subtle delay
          setTimeout(() => {
            set((state) => ({
              chatSessions: state.chatSessions.map((session) =>
                session.id === realSession.id ? { ...session, isNew: false } : session
              ),
            }))
          }, 2000)
        },

        removeOptimisticConversation: (tempId: string) => {
          set((state) => {
            const filteredSessions = state.chatSessions.filter((session) => session.id !== tempId)
            const wasPending = state.pendingCreationId === tempId
            const nextMap = { ...state.toolsEnabledByChatId }
            delete nextMap[tempId]
            const isCurrent = state.currentChatId === tempId
            return {
              chatSessions: filteredSessions,
              isCreatingConversation: wasPending ? false : state.isCreatingConversation,
              pendingCreationId: wasPending ? null : state.pendingCreationId,
              toolsEnabledByChatId: nextMap,
              toolsEnabled: isCurrent ? mergeToolsState(state.draftToolsEnabled) : state.toolsEnabled,
              currentChatId: isCurrent ? null : state.currentChatId,
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
          const state = get()

          // Clear any existing cleanup timer
          if (state.draft.cleanupTimerId) {
            clearTimeout(state.draft.cleanupTimerId)
          }

          // Generate client ID for idempotency
          const cid = typeof crypto !== 'undefined' && 'randomUUID' in crypto
            ? crypto.randomUUID()
            : `draft-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`

          const startedAt = Date.now()

          // Auto-cleanup after 2.5s if no message is sent
          const DRAFT_TIMEOUT_MS = 2500
          const cleanupTimerId = window.setTimeout(() => {
            const currentState = get()
            // Only cleanup if still in draft mode and no messages sent
            if (currentState.draft.isDraftMode &&
                currentState.draft.cid === cid &&
                currentState.messages.length === 0) {
              logAction('chat.draft.cleaned', {
                cid,
                durationMs: Date.now() - startedAt,
                reason: 'timeout'
              })
              get().discardDraft()
            }
          }, DRAFT_TIMEOUT_MS)

          set({
            draft: {
              isDraftMode: true,
              draftText: '',
              draftModel: state.selectedModel,
              cid,
              startedAt,
              cleanupTimerId,
            },
            currentChatId: null,
            messages: [],
            chatNotFound: false,
            isLoading: false, // Clear loading state to show hero mode
            toolsEnabled: mergeToolsState(state.draftToolsEnabled),
          })

          logAction('chat.draft.created', {
            cid,
            model: state.selectedModel,
            timeoutMs: DRAFT_TIMEOUT_MS
          })
          logDebug('Draft mode activated with auto-cleanup', {
            model: state.selectedModel,
            cid,
            timeoutMs: DRAFT_TIMEOUT_MS
          })
        },

        discardDraft: () => {
          const state = get()
          const hadText = state.draft.draftText.length > 0
          const cid = state.draft.cid

          // Clear cleanup timer if exists
          if (state.draft.cleanupTimerId) {
            clearTimeout(state.draft.cleanupTimerId)
          }

          set({
            draft: INITIAL_DRAFT_STATE,
            isLoading: false, // Clear loading state when discarding draft
          })

          if (cid) {
            logAction('chat.draft.discarded', {
              cid,
              hadText,
              durationMs: state.draft.startedAt ? Date.now() - state.draft.startedAt : 0
            })
          }
          logDebug('Draft discarded', { hadText, cid })
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
            // CRITICAL: Clear isLoading even on early return to prevent stuck loading state
            set({ isLoading: false })
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
          } finally {
            // CRITICAL: Always clear isLoading in finally block to prevent stuck state
            // This ensures cleanup happens regardless of success, error, or early return
            logDebug('loadUnifiedHistory cleanup', { chatId, clearingLoading: true })
            set({ isLoading: false })
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

            // console.log('[AUTOTITLE-DEBUG] sendMessage - isDraftMode:', state.draft.isDraftMode, 'currentChatId:', state.currentChatId)

            // Message-First: If in draft mode, create conversation with first message
            if (state.draft.isDraftMode) {
              const draftCid = state.draft.cid
              const draftStartedAt = state.draft.startedAt || Date.now()

              // Clear auto-cleanup timer since user is sending message
              if (state.draft.cleanupTimerId) {
                clearTimeout(state.draft.cleanupTimerId)
              }

              // Generate title from first message (fast, no API call)
              const title = computeTitleFromText(content)

              logAction('chat.message.first', {
                cid: draftCid,
                titleLength: title.length,
                messageLength: content.length,
                draftDurationMs: Date.now() - draftStartedAt
              })

              logDebug('Creating conversation from draft (message-first)', {
                title,
                cid: draftCid
              })

              try {
                // Create conversation with derived title
                // Use draft cid as idempotency key
                const conversation = await apiClient.createConversation(
                  {
                    title,
                    model: state.draft.draftModel || state.selectedModel,
                    tools_enabled: state.toolsEnabled,
                  },
                  { idempotencyKey: draftCid }
                )

                // Exit draft mode and set the new chat ID
                set({
                  draft: INITIAL_DRAFT_STATE,
                  currentChatId: conversation.id,
                })

                // Commit to history ONLY after backend confirms creation
                const newSession: ChatSession = {
                  id: conversation.id,
                  title: conversation.title || title,
                  created_at: conversation.created_at,
                  updated_at: conversation.updated_at,
                  first_message_at: null, // Will be set after message sent
                  last_message_at: null,
                  message_count: 0, // Will be updated after message sent
                  model: conversation.model,
                  preview: content.substring(0, 100),
                  pinned: false,
                  state: 'draft',
                  tools_enabled: normalizeToolsState(conversation.tools_enabled),
                }

                // Add to history at index 0 (newest first)
                set((s) => ({
                  chatSessions: [newSession, ...s.chatSessions]
                }))

                logAction('chat.history.committed', {
                  chatId: conversation.id,
                  cid: draftCid,
                  title,
                  latencyMs: Date.now() - draftStartedAt
                })

                logDebug('Conversation created and committed to history', {
                  chatId: conversation.id,
                  title,
                  messageLength: content.length,
                })

                // Message-first: Auto-title with AI after creation (non-blocking)
                // This improves the temporary title with an AI-generated one
                // console.log('[AUTOTITLE-DEBUG] Starting autotitle for conversation:', conversation.id, 'content:', content.substring(0, 50))
                generateTitleFromMessage(content, apiClient)
                  .then(async (aiTitle) => {
                    // console.log('[AUTOTITLE-DEBUG] Generated title:', aiTitle, 'original:', title, 'will update:', aiTitle && aiTitle !== title)
                    if (aiTitle && aiTitle !== title) {
                      // Update conversation title with AI-generated title
                      await apiClient.updateChatSession(conversation.id, {
                        title: aiTitle,
                        auto_title: true  // Mark as automatic to avoid setting title_override
                      })

                      // Update local state immediately (faster than reloading all sessions)
                      set((state) => ({
                        chatSessions: state.chatSessions.map((session) =>
                          session.id === conversation.id
                            ? { ...session, title: aiTitle, updated_at: new Date().toISOString() }
                            : session
                        ),
                      }))

                      // Broadcast to other tabs
                      getSyncInstance().broadcast('session_renamed', { chatId: conversation.id })

                      logDebug('Auto-titled message-first conversation', {
                        chatId: conversation.id,
                        originalTitle: title,
                        aiTitle,
                      })
                    }
                  })
                  .catch((error) => {
                    logWarn('Failed to auto-title message-first conversation', { error })
                    // Non-critical, conversation already created with temp title
                  })

              } catch (error) {
                logError('Failed to create conversation from draft', error)
                logAction('chat.create.failed', {
                  cid: draftCid,
                  error: error instanceof Error ? error.message : 'Unknown error'
                })

                // Re-enable draft mode on failure
                set({
                  draft: {
                    ...state.draft,
                    cleanupTimerId: undefined, // Don't restart timer
                  }
                })

                throw error // Re-throw to show error toast
              }
            } else if (state.currentChatId && !state.currentChatId.startsWith('temp-')) {
              // Auto-title existing conversations on first message (if not overridden)
              const currentSession = state.chatSessions.find(s => s.id === state.currentChatId)
              // console.log('[AUTOTITLE-DEBUG] Existing conversation path - currentSession:', currentSession?.id, 'hasFirstMessage:', currentSession && hasFirstMessage(currentSession), 'title_override:', currentSession?.title_override)

              if (currentSession && !hasFirstMessage(currentSession) && !currentSession.title_override) {
                // This is the first message, generate and update title
                try {
                  // console.log('[AUTOTITLE-DEBUG] Generating title for existing conversation:', currentSession.id)
                  const newTitle = await generateTitleFromMessage(content, apiClient)

                  // Update conversation title with auto_title flag (won't set override)
                  await apiClient.updateChatSession(state.currentChatId, {
                    title: newTitle,
                    auto_title: true  // Mark as automatic to avoid setting title_override
                  })

                  // Update local state optimistically
                  set((state) => ({
                    chatSessions: state.chatSessions.map((session) =>
                      session.id === state.currentChatId
                        ? { ...session, title: newTitle, title_override: false }
                        : session
                    ),
                  }))

                  logDebug('Auto-titled conversation on first message', {
                    chatId: state.currentChatId,
                    title: newTitle,
                  })
                } catch (error) {
                  logWarn('Failed to auto-title conversation', { error })
                  // Non-critical, continue with message send
                }
              }
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

            const responseTools = normalizeToolsState(response.tools_enabled)

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

            set((prevState) => {
              const nextMap = { ...prevState.toolsEnabledByChatId, [response.chat_id]: responseTools }
              const shouldUpdateActive =
                prevState.currentChatId === response.chat_id || (!prevState.currentChatId && !wasTempId)

              return {
                toolsEnabledByChatId: nextMap,
                toolsEnabled: shouldUpdateActive ? responseTools : prevState.toolsEnabled,
              }
            })

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
            toolsEnabled: mergeToolsState(),
            toolsEnabledByChatId: {},
            draftToolsEnabled: mergeToolsState(),
            activeTasks: [],
            currentTaskId: null,
            chatSessions: [],
            settings: defaultSettings,
            pendingCreationId: null,
            isCreatingConversation: false,
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
    setToolEnabled: store.setToolEnabled,
    setLoading: store.setLoading,
    loadChatSessions: store.loadChatSessions,
    loadModels: store.loadModels,
    loadFeatureFlags: store.loadFeatureFlags,
    addChatSession: store.addChatSession,
    removeChatSession: store.removeChatSession,
    renameChatSession: store.renameChatSession,
    pinChatSession: store.pinChatSession,
    deleteChatSession: store.deleteChatSession,
    updateSessionTitle: store.updateSessionTitle,
    setCurrentChatId: store.setCurrentChatId,
    switchChat: store.switchChat,
    bumpSelectionEpoch: store.bumpSelectionEpoch,
    loadUnifiedHistory: store.loadUnifiedHistory,
    refreshChatStatus: store.refreshChatStatus,
    // P0-UX-HIST-001: Optimistic UI
    isCreatingConversation: store.isCreatingConversation,
    pendingCreationId: store.pendingCreationId,
    createConversationOptimistic: store.createConversationOptimistic,
    reconcileConversation: store.reconcileConversation,
    removeOptimisticConversation: store.removeOptimisticConversation,
    finalizeCreation: store.finalizeCreation,
    cancelCreation: store.cancelCreation,
    // Progressive Commitment: Draft state
    draft: store.draft,
    draftToolsEnabled: store.draftToolsEnabled,
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
