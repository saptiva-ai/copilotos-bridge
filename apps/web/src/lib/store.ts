/**
 * Global state management with Zustand
 */

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { ChatMessage, ChatSession, ResearchTask } from './types'
import { apiClient } from './api-client'

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
  selectedModel: string
  toolsEnabled: Record<string, boolean>
  
  // Research state
  activeTasks: ResearchTask[]
  currentTaskId: string | null
  
  // History
  chatSessions: ChatSession[]
  
  // Settings
  settings: {
    maxTokens: number
    temperature: number
    streamEnabled: boolean
  }
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
  
  // Settings actions
  updateSettings: (settings: Partial<AppState['settings']>) => void
  
  // API actions
  sendMessage: (content: string) => Promise<void>
  startNewChat: () => void
  checkConnection: () => Promise<void>
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
  code_analysis: true,
  document_analysis: false,
  image_generation: false,
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
        selectedModel: 'SAPTIVA_CORTEX',
        toolsEnabled: defaultTools,
        activeTasks: [],
        currentTaskId: null,
        chatSessions: [],
        settings: defaultSettings,

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
        setSelectedModel: (model) => set({ selectedModel: model }),
        
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
            const sessions = await apiClient.getChatSessions()
            set({ chatSessions: sessions })
          } catch (error) {
            console.error('Failed to load chat sessions:', error)
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
            
            // Send to API
            const response = await apiClient.sendChatMessage({
              message: content,
              chat_id: state.currentChatId || undefined,
              model: state.selectedModel,
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
            console.error('Failed to send message:', error)
            
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
    selectedModel: store.selectedModel,
    toolsEnabled: store.toolsEnabled,
    sendMessage: store.sendMessage,
    startNewChat: store.startNewChat,
    addMessage: store.addMessage,
    updateMessage: store.updateMessage,
    clearMessages: store.clearMessages,
    setSelectedModel: store.setSelectedModel,
    toggleTool: store.toggleTool,
    setLoading: store.setLoading,
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
  }
}

export const useSettings = () => {
  const store = useAppStore()
  return {
    settings: store.settings,
    updateSettings: store.updateSettings,
  }
}