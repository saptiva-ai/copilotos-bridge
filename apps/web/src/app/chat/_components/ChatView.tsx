'use client'

import * as React from 'react'
import { useSearchParams } from 'next/navigation'

import { ChatMessage } from '../../../lib/types'
import {
  ChatInterface,
  ChatWelcomeMessage,
  ChatShell,
  ConversationList,
} from '../../../components/chat'
import { DeepResearchWizard, type DeepResearchScope } from '../../../components/chat/DeepResearchWizard'
import { DeepResearchProgress } from '../../../components/chat/DeepResearchProgress'
import { IntentNudge } from '../../../components/chat/IntentNudge'
import type { ChatComposerAttachment } from '../../../components/chat/ChatComposer'
import { useChat, useUI } from '../../../lib/store'
import { apiClient } from '../../../lib/api-client'
import { useRequireAuth } from '../../../hooks/useRequireAuth'
import { useSelectedTools } from '../../../hooks/useSelectedTools'
import { useOptimizedChat } from '../../../hooks/useOptimizedChat'
import { useDeepResearch } from '../../../hooks/useDeepResearch'
import type { ToolId } from '../../../types/tools'
import WelcomeBanner from '../../../components/chat/WelcomeBanner'
import { useAuthStore } from '../../../lib/auth-store'
import { logDebug, logError } from '../../../lib/logger'
import { researchGate } from '../../../lib/research-gate'
// Demo banner intentionally hidden per stakeholder request

interface ChatViewProps {
  initialChatId?: string | null
}

export function ChatView({ initialChatId = null }: ChatViewProps) {
  const { isAuthenticated, isHydrated } = useRequireAuth()
  const user = useAuthStore((state) => state.user)
  const searchParams = useSearchParams()
  const queryChatId = searchParams?.get('session') ?? null

  const resolvedChatId = React.useMemo(() => {
    if (initialChatId && initialChatId !== 'new') return initialChatId
    if (queryChatId && queryChatId !== 'new') return queryChatId
    return null
  }, [initialChatId, queryChatId])

  const {
    currentChatId,
    messages,
    isLoading,
    models,
    modelsLoading,
    featureFlags,
    featureFlagsLoading,
    selectedModel,
    toolsEnabled,
    startNewChat,
    setSelectedModel,
    clearMessages,
    setLoading,
    toggleTool,
    chatSessions,
    chatSessionsLoading,
    chatNotFound,
    loadChatSessions,
    loadModels,
    loadFeatureFlags,
    setCurrentChatId,
    loadUnifiedHistory,
    refreshChatStatus,
  } = useChat()

  const { checkConnection } = useUI()
  const { selected: selectedTools, addTool, removeTool } = useSelectedTools()
  const { sendOptimizedMessage, cancelCurrentRequest } = useOptimizedChat({
    enablePredictiveLoading: true,
    enableResponseCache: true,
    streamingChunkSize: 3
  })

  const [nudgeMessage, setNudgeMessage] = React.useState<string | null>(null)
  const [pendingWizard, setPendingWizard] = React.useState<{ query: string; attachments?: ChatComposerAttachment[] } | null>(null)
  const [activeResearch, setActiveResearch] = React.useState<{ taskId: string; streamUrl?: string | null; query: string } | null>(null)
  const [isStartingResearch, setIsStartingResearch] = React.useState(false)
  const [researchError, setResearchError] = React.useState<string | null>(null)

  const deepResearchEnabled = React.useMemo(() => {
    if (featureFlags?.deep_research_kill_switch) {
      return false;
    }
    return selectedTools.includes('deep-research');
  }, [selectedTools, featureFlags])

  const researchState = useDeepResearch(activeResearch?.streamUrl ?? undefined)
  const {
    phase: researchPhase,
    progress: researchProgress,
    sources: researchSources,
    evidences: researchEvidences,
    report: researchReport,
    error: researchHookError,
    isStreaming: researchIsStreaming,
    stop: stopResearchStream,
    reset: resetResearchState,
  } = researchState

  const startDeepResearchFlow = React.useCallback(
    async (
      text: string,
      scope?: Partial<DeepResearchScope>,
      _attachments?: ChatComposerAttachment[],
    ) => {
      if (researchIsStreaming) {
        setNudgeMessage('Ya hay una investigación en curso. Cancela o espera a que finalice antes de iniciar otra.')
        return
      }

      resetResearchState()
      setPendingWizard(null)
      setResearchError(null)
      setNudgeMessage(null)
      setActiveResearch(null)
      setIsStartingResearch(true)

      try {
        await sendOptimizedMessage(text, async (msg: string, placeholderId: string, abortController?: AbortController) => {
          try {
            const request = {
              query: msg,
              chat_id: currentChatId || undefined,
              research_type: 'deep_research' as const,
              stream: true,
              params: {
                depth_level: scope?.depth ?? 'medium',
                scope: scope?.objective ?? msg,
              },
              context: {
                time_window: scope?.timeWindow,
                origin: 'chat',
              },
            }

            const response = await apiClient.startDeepResearch(request)

            if (!currentChatId && (response as any)?.chat_id) {
              setCurrentChatId((response as any).chat_id)
            }

            setActiveResearch({
              taskId: response.task_id,
              streamUrl: response.stream_url,
              query: msg,
            })

            return {
              id: placeholderId,
              role: 'assistant' as const,
              content:
                'Iniciando investigación profunda. Te compartiré avances conforme encontremos evidencia relevante.',
              timestamp: new Date().toISOString(),
              status: 'delivered' as const,
            }
          } catch (error) {
            setResearchError('No se pudo iniciar la investigación. Intenta nuevamente o ajusta el alcance.')
            setNudgeMessage('No se pudo iniciar la investigación. Intenta nuevamente o ajusta el alcance.')
            setActiveResearch(null)
            return {
              id: placeholderId,
              role: 'assistant' as const,
              content: 'Lo siento, no se pudo iniciar la investigación en este momento.',
              timestamp: new Date().toISOString(),
              status: 'error' as const,
            }
          } finally {
            setIsStartingResearch(false)
          }
        })
      } finally {
        setIsStartingResearch(false)
      }
    },
    [
      researchIsStreaming,
      resetResearchState,
      sendOptimizedMessage,
      currentChatId,
      setPendingWizard,
      setResearchError,
      setNudgeMessage,
      setActiveResearch,
      setIsStartingResearch,
      setCurrentChatId,
      apiClient,
    ]
  )

  React.useEffect(() => {
    checkConnection()
  }, [checkConnection])

  React.useEffect(() => {
    if (isAuthenticated && isHydrated) {
      loadChatSessions()
      loadModels()
      loadFeatureFlags()
    }
  }, [isAuthenticated, isHydrated, loadChatSessions, loadModels, loadFeatureFlags])

  React.useEffect(() => {
    if (!isHydrated) return

    if (resolvedChatId) {
      setCurrentChatId(resolvedChatId)
      loadUnifiedHistory(resolvedChatId)
      refreshChatStatus(resolvedChatId)
    } else {
      setCurrentChatId(null)
      startNewChat()
    }
  }, [resolvedChatId, isHydrated, setCurrentChatId, loadUnifiedHistory, refreshChatStatus, startNewChat])

  const sendStandardMessage = React.useCallback(
    async (message: string, attachments?: ChatComposerAttachment[]) => {
      await sendOptimizedMessage(message, async (msg: string, placeholderId: string, abortController?: AbortController) => {
        try {
          const response = await apiClient.sendChatMessage({
            message: msg,
            chat_id: currentChatId || undefined,
            model: selectedModel,
            temperature: 0.3,
            max_tokens: 800,
            stream: false,
            tools_enabled: toolsEnabled,
          })

          if (!currentChatId && response.chat_id) {
            setCurrentChatId(response.chat_id)
          }

          const assistantMessage: ChatMessage = {
            id: response.message_id || placeholderId,
            role: 'assistant',
            content: response.content,
            timestamp: response.created_at || new Date().toISOString(),
            model: response.model,
            tokens: response.tokens || 0,
            latency: response.latency_ms || 0,
            status: 'delivered',
            isStreaming: false,
            task_id: response.task_id,
          }

          return assistantMessage
        } catch (error) {
          logError('Failed to send chat message', error)
          return {
            id: placeholderId,
            role: 'assistant',
            content:
              'Lo siento, no pude conectar con el servidor de chat en este momento. Intenta nuevamente en unos segundos.',
            timestamp: new Date().toISOString(),
            status: 'error' as const,
            isStreaming: false,
          }
        }
      })
    },
    [currentChatId, selectedModel, toolsEnabled, sendOptimizedMessage, setCurrentChatId]
  )

  const handleSendMessage = React.useCallback(
    async (message: string, attachments?: ChatComposerAttachment[]) => {
      const trimmed = message.trim()
      if (!trimmed) return

      setNudgeMessage(null)
      setResearchError(null)

      try {
        await researchGate(trimmed, {
          deepResearchOn: deepResearchEnabled,
          openWizard: (userText) => setPendingWizard({ query: userText, attachments }),
          startResearch: async (userText, scope) => {
            await startDeepResearchFlow(userText, scope, attachments)
          },
          showNudge: (msg) => setNudgeMessage(msg),
          routeToChat: (userText) => sendStandardMessage(userText, attachments),
        })
      } catch (error) {
        logDebug('researchGate fallback', error)
        await sendStandardMessage(trimmed, attachments)
      }
    },
    [
      deepResearchEnabled,
      sendStandardMessage,
      setPendingWizard,
      startDeepResearchFlow,
      setNudgeMessage,
      setResearchError,
    ]
  )

  const handleRetryMessage = async (messageId: string) => {
    const messageIndex = messages.findIndex((m) => m.id === messageId)
    if (messageIndex > 0) {
      const userMessage = messages[messageIndex - 1]
      if (userMessage.role === 'user') {
        await handleSendMessage(userMessage.content)
      }
    }
  }

  // UX-005 handlers
  const handleRegenerateMessage = async (messageId: string) => {
    const messageIndex = messages.findIndex((m) => m.id === messageId)
    if (messageIndex <= 0) {
      logDebug('Cannot regenerate: no previous user message found')
      return
    }

    const userMessage = messages[messageIndex - 1]
    if (userMessage.role !== 'user') {
      logDebug('Cannot regenerate: previous message is not from user')
      return
    }

    try {
      // Remove the assistant message that we're regenerating
      const updatedMessages = messages.filter((m) => m.id !== messageId)
      // Update messages state to remove the old response
      // Note: In a real app, this would be handled by a proper state management system

      logDebug('Regenerating message', {
        messageId,
        userContent: userMessage.content,
        messageIndex
      })

      // Resend the user message to generate a new response
      await handleSendMessage(userMessage.content, userMessage.attachments as any)
    } catch (error) {
      logDebug('Failed to regenerate message', error)
      // In a real app, you'd show an error toast/notification
    }
  }

  const handleStopStreaming = React.useCallback(() => {
    logDebug('Stop streaming requested')
    // Cancel the current chat request
    cancelCurrentRequest()
    // Also stop research streaming if active
    if (researchIsStreaming) {
      stopResearchStream()
    }
    setLoading(false)
  }, [cancelCurrentRequest, researchIsStreaming, stopResearchStream, setLoading])

  const handleCancelResearch = React.useCallback(async () => {
    if (!activeResearch) return

    try {
      stopResearchStream()
      await apiClient.cancelResearchTask(activeResearch.taskId, 'user_cancelled')
    } catch (error) {
      logDebug('Cancel research error', error)
      setNudgeMessage('No se pudo cancelar la investigación. Inténtalo nuevamente.')
    } finally {
      resetResearchState()
      setActiveResearch(null)
    }
  }, [activeResearch, stopResearchStream, resetResearchState, apiClient, setNudgeMessage, setActiveResearch])

  const handleCloseResearchCard = React.useCallback(() => {
    resetResearchState()
    setActiveResearch(null)
    setResearchError(null)
  }, [resetResearchState, setActiveResearch, setResearchError])

  const handleCopyMessage = () => {}

  const handleSelectChat = React.useCallback((chatId: string) => {
    if (chatId === currentChatId) return
    setCurrentChatId(chatId)
    clearMessages()
    loadUnifiedHistory(chatId)
    refreshChatStatus(chatId)
  }, [clearMessages, currentChatId, setCurrentChatId, loadUnifiedHistory, refreshChatStatus])

  const handleStartNewChat = React.useCallback(() => {
    setCurrentChatId(null)
    clearMessages()
    startNewChat()
  }, [setCurrentChatId, clearMessages, startNewChat])

  // Chat action handlers - UX-002
  const handleRenameChat = React.useCallback(async (chatId: string, newTitle: string) => {
    try {
      await apiClient.renameChatSession(chatId, newTitle)
      // Refresh chat sessions to reflect the change
      // Note: In a real app, you'd update the store directly or use optimistic updates
      logDebug('Chat renamed successfully', chatId, newTitle)
    } catch (error) {
      logDebug('Failed to rename chat', error)
      // In a real app, you'd show an error toast/notification
    }
  }, [apiClient])

  const handlePinChat = React.useCallback(async (chatId: string, currentlyPinned?: boolean) => {
    try {
      // Toggle the pinned state - if currentlyPinned is undefined, default to pin
      const newPinnedState = currentlyPinned !== undefined ? !currentlyPinned : true
      await apiClient.pinChatSession(chatId, newPinnedState)
      logDebug('Chat pin toggled successfully', chatId, newPinnedState)
    } catch (error) {
      logDebug('Failed to toggle pin for chat', error)
      // In a real app, you'd show an error toast/notification
    }
  }, [apiClient])

  const handleDeleteChat = React.useCallback(async (chatId: string) => {
    try {
      await apiClient.deleteChatSession(chatId)
      logDebug('Chat deleted successfully', chatId)
      // If deleting current chat, redirect to new chat
      if (chatId === currentChatId) {
        handleStartNewChat()
      }
      // Note: In a real app, you'd update the chat list in the store/state
    } catch (error) {
      logDebug('Failed to delete chat', error)
      // In a real app, you'd show an error toast/notification
    }
  }, [currentChatId, handleStartNewChat, apiClient])

  const handleOpenTools = React.useCallback(() => {
    // This callback is now handled by the ChatComposer's menu system
    // The ChatComposer will open its ToolMenu and handle individual tool selection
  }, [])

  const handleRemoveTool = React.useCallback((id: ToolId) => {
    removeTool(id)
  }, [removeTool])

  if (!isHydrated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-saptiva-slate">Cargando sesión...</p>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  // Chat not found state or welcome banner
  const welcomeComponent = chatNotFound && resolvedChatId ? (
    <div className="flex h-full items-center justify-center">
      <div className="text-center max-w-md mx-auto px-6">
        <h3 className="text-xl font-semibold text-white mb-3">
          Conversación no encontrada
        </h3>
        <p className="text-saptiva-light/70 mb-6">
          La conversación <code className="px-2 py-1 bg-white/10 rounded text-sm">{resolvedChatId}</code> no existe
          o no tienes acceso a ella.
        </p>
        <button
          onClick={() => {
            handleStartNewChat()
            window.history.replaceState({}, '', '/chat')
          }}
          className="inline-flex items-center justify-center rounded-full bg-saptiva-blue px-6 py-3 text-sm font-semibold text-white hover:bg-saptiva-lightBlue/90 transition-colors"
        >
          Iniciar nueva conversación
        </button>
      </div>
    </div>
  ) : (
    <WelcomeBanner user={user || undefined} />
  )

  return (
    <ChatShell
      sidebar={(
        <ConversationList
          sessions={chatSessions}
          onNewChat={handleStartNewChat}
          onSelectChat={handleSelectChat}
          activeChatId={currentChatId}
          isLoading={chatSessionsLoading}
          onRenameChat={handleRenameChat}
          onPinChat={handlePinChat}
          onDeleteChat={handleDeleteChat}
        />
      )}
      models={models}
      selectedModel={selectedModel}
      onModelChange={setSelectedModel}
    >
      <div className="flex h-full flex-col">
        {(nudgeMessage || pendingWizard || activeResearch) && (
          <div className="flex flex-col items-center gap-4 px-4 pt-4">
            {nudgeMessage && (
              <IntentNudge message={nudgeMessage} onDismiss={() => setNudgeMessage(null)} />
            )}

            {pendingWizard && (
              <DeepResearchWizard
                query={pendingWizard.query}
                onConfirm={(scope) => startDeepResearchFlow(pendingWizard.query, scope)}
                onCancel={() => setPendingWizard(null)}
                loading={isStartingResearch}
              />
            )}

            {activeResearch && (
              <DeepResearchProgress
                query={activeResearch.query}
                phase={researchPhase}
                progress={researchProgress}
                sources={researchSources}
                evidences={researchEvidences}
                report={researchReport}
                errorMessage={researchError ?? researchHookError?.error ?? null}
                isStreaming={researchIsStreaming}
                onCancel={handleCancelResearch}
                onClose={handleCloseResearchCard}
              />
            )}
          </div>
        )}

        <ChatInterface
          className="flex-1"
          messages={messages}
          onSendMessage={handleSendMessage}
          onRetryMessage={handleRetryMessage}
          onRegenerateMessage={handleRegenerateMessage}
          onStopStreaming={handleStopStreaming}
          onCopyMessage={handleCopyMessage}
          loading={isLoading}
          welcomeMessage={welcomeComponent}
          featureFlags={featureFlags}
          toolsEnabled={toolsEnabled}
          onToggleTool={toggleTool}
          selectedTools={selectedTools}
          onRemoveTool={handleRemoveTool}
          onAddTool={addTool}
          onOpenTools={handleOpenTools}
        />
      </div>
    </ChatShell>
  )
}
