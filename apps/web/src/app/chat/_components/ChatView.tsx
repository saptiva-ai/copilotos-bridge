'use client'

import * as React from 'react'
import { useSearchParams } from 'next/navigation'
import toast from 'react-hot-toast'

import { ChatMessage, ChatSession } from '../../../lib/types'
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
import { getAllModels } from '../../../config/modelCatalog'
import { useRequireAuth } from '../../../hooks/useRequireAuth'
import { useSelectedTools } from '../../../hooks/useSelectedTools'
import { useOptimizedChat } from '../../../hooks/useOptimizedChat'
import { useDeepResearch } from '../../../hooks/useDeepResearch'
import type { ToolId } from '../../../types/tools'
import WelcomeBanner from '../../../components/chat/WelcomeBanner'
import { useAuthStore } from '../../../lib/auth-store'
import { logDebug, logError } from '../../../lib/logger'
import { researchGate } from '../../../lib/research-gate'
import { logEffect, logAction, logState } from '../../../lib/ux-logger'
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
    renameChatSession,
    pinChatSession,
    deleteChatSession,
    // P0-UX-HIST-001: Optimistic UI states
    isCreatingConversation,
    optimisticConversations,
    createConversationOptimistic,
    reconcileConversation,
    removeOptimisticConversation,
    // Progressive Commitment: Draft state
    draft,
    openDraft,
    discardDraft,
    isDraftMode,
    // Hydration state (SWR pattern)
    hydratedByChatId,
    isHydratingByChatId,
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

  // CHAT_ROUTE_EFFECT: Blindado con deps mínimas para SWR
  // eslint-disable-next-line react-hooks/exhaustive-deps
  React.useEffect(() => {
    logEffect('CHAT_ROUTE_EFFECT', {
      resolvedChatId,
      isHydrated,
      hydrated: resolvedChatId ? hydratedByChatId[resolvedChatId] : undefined,
      hydrating: resolvedChatId ? isHydratingByChatId[resolvedChatId] : undefined,
    })

    // Guard: Only run when app is ready
    if (!isHydrated) return

    if (resolvedChatId) {
      // If switching away from a temp conversation, cancel its creation
      if (currentChatId?.startsWith('temp-') && currentChatId !== resolvedChatId) {
        logAction('CANCEL_OPTIMISTIC_CHAT', { tempId: currentChatId, switchingTo: resolvedChatId })
        removeOptimisticConversation(currentChatId)
      }

      // Set active chat ID if different
      if (currentChatId !== resolvedChatId) {
        logAction('SET_ACTIVE_CHAT', { chatId: resolvedChatId })
        setCurrentChatId(resolvedChatId)
      }

      // SWR: Only load if NOT hydrated AND NOT currently hydrating
      const hydrated = hydratedByChatId[resolvedChatId]
      const hydrating = isHydratingByChatId[resolvedChatId]

      if (!hydrated && !hydrating) {
        logAction('LOAD_CHAT', { chatId: resolvedChatId })
        loadUnifiedHistory(resolvedChatId)
        refreshChatStatus(resolvedChatId)
      } else {
        logAction('SKIP_LOAD_CHAT', { chatId: resolvedChatId, hydrated, hydrating })
      }
    } else if (currentChatId === null && !isDraftMode()) {
      // Only open draft if we have NO current chat AND we're not already in draft mode
      logAction('ROUTE_TO_NEW_CHAT_INIT', { prevChatId: currentChatId })
      setCurrentChatId(null)
      startNewChat()
    }
  }, [resolvedChatId, isHydrated]) // MINIMAL DEPS: Only route param and app hydration

  const sendStandardMessage = React.useCallback(
    async (message: string, attachments?: ChatComposerAttachment[]) => {
      await sendOptimizedMessage(message, async (msg: string, placeholderId: string, abortController?: AbortController) => {
        try {
          // Resolve UI slug to backend ID
          const selectedModelData = models.find((m) => m.id === selectedModel)
          let backendModelId = selectedModelData?.backendId

          // Fallback: if backendId is null/undefined or equals the slug (not resolved),
          // use display name from catalog
          if (!backendModelId || backendModelId === selectedModel) {
            const catalogModel = getAllModels().find((m) => m.slug === selectedModel)
            backendModelId = catalogModel?.displayName || selectedModel
            console.warn('[ChatView] Using catalog fallback for model:', {
              selectedModelSlug: selectedModel,
              catalogModel: catalogModel?.displayName,
              fallbackValue: backendModelId,
            })
          }

          // Don't send temp IDs to backend - they don't exist there yet
          const wasTempId = currentChatId?.startsWith('temp-')
          const chatIdForBackend = wasTempId ? undefined : (currentChatId || undefined)

          const response = await apiClient.sendChatMessage({
            message: msg,
            chat_id: chatIdForBackend,
            model: backendModelId,
            temperature: 0.3,
            max_tokens: 800,
            stream: false,
            tools_enabled: toolsEnabled,
          })

          // If we had a temp ID and got a real ID back, reconcile the optimistic conversation
          if (!currentChatId && response.chat_id) {
            setCurrentChatId(response.chat_id)
          } else if (wasTempId && response.chat_id && currentChatId) {
            // Reconcile: temp conversation → real conversation
            logDebug('Reconciling optimistic conversation', { tempId: currentChatId, realId: response.chat_id })

            const tempIdToReconcile = currentChatId
            setCurrentChatId(response.chat_id)

            // Create a minimal session object from the response data
            const minimalSession: ChatSession = {
              id: response.chat_id,
              title: 'Nueva conversación', // Will be updated when we reload sessions
              created_at: response.created_at || new Date().toISOString(),
              updated_at: response.created_at || new Date().toISOString(),
              first_message_at: response.created_at || new Date().toISOString(),
              last_message_at: response.created_at || new Date().toISOString(),
              message_count: 2, // User + assistant
              model: response.model || selectedModel,
              preview: message.substring(0, 100),
              pinned: false,
            }

            reconcileConversation(tempIdToReconcile, minimalSession)

            // Reload sessions in background to get the full session data
            loadChatSessions()
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
    [currentChatId, selectedModel, models, toolsEnabled, sendOptimizedMessage, setCurrentChatId, loadChatSessions, chatSessions, reconcileConversation]
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
    // Don't do anything here - let the navigation and useEffect handle it
    // This prevents double loading and race conditions
  }, [])

  const handleStartNewChat = React.useCallback(() => {
    logAction('START_NEW_CHAT_CLICKED', { currentChatId, messagesLen: messages.length })

    // Anti-spam: Check if current chat is empty (including optimistic conversations)
    if (currentChatId && messages.length === 0) {
      const isOptimistic = currentChatId.startsWith('temp-')
      toast('Termina o envía un mensaje antes de iniciar otra conversación', {
        icon: '💡',
        duration: 3000,
      })
      logAction('BLOCKED_NEW_CHAT', { reason: 'current_chat_empty', isOptimistic })
      return
    }

    // Anti-spam: Check if there's already an optimistic conversation being created
    if (optimisticConversations.size > 0) {
      toast('Ya tienes una conversación vacía abierta', {
        icon: '💡',
        duration: 3000,
      })
      logAction('BLOCKED_NEW_CHAT', { reason: 'optimistic_exists', count: optimisticConversations.size })
      return
    }

    // Create optimistic conversation card immediately
    const tempId = createConversationOptimistic()
    logAction('CREATED_OPTIMISTIC_CHAT', { tempId })

    // Set as current chat (DON'T call openDraft - it would reset currentChatId to null!)
    setCurrentChatId(tempId)
    // Clear messages for new conversation
    clearMessages()

    logState('AFTER_NEW_CHAT', { currentChatId: tempId, messagesLength: 0, isDraftMode: false })
  }, [currentChatId, messages.length, optimisticConversations.size, createConversationOptimistic, setCurrentChatId, clearMessages])

  // Chat action handlers - UX-002
  const handleRenameChat = React.useCallback(async (chatId: string, newTitle: string) => {
    try {
      await renameChatSession(chatId, newTitle)
      logDebug('Chat renamed successfully', chatId, newTitle)
    } catch (error) {
      logError('Failed to rename chat:', error)
      // TODO: Show error toast/notification
    }
  }, [renameChatSession])

  const handlePinChat = React.useCallback(async (chatId: string) => {
    try {
      await pinChatSession(chatId)
      logDebug('Chat pin toggled successfully', chatId)
    } catch (error) {
      logError('Failed to toggle pin for chat:', error)
      // TODO: Show error toast/notification
    }
  }, [pinChatSession])

  const handleDeleteChat = React.useCallback(async (chatId: string) => {
    try {
      await deleteChatSession(chatId)
      logDebug('Chat deleted successfully', chatId)
      // If deleting current chat, redirect to new chat
      if (chatId === currentChatId) {
        handleStartNewChat()
      }
    } catch (error) {
      logError('Failed to delete chat:', error)
      // TODO: Show error toast/notification
    }
  }, [deleteChatSession, currentChatId, handleStartNewChat])

  const handleOpenTools = React.useCallback(() => {
    // This callback is now handled by the ChatComposer's menu system
    // The ChatComposer will open its ToolMenu and handle individual tool selection
  }, [])

  const handleRemoveTool = React.useCallback((id: ToolId) => {
    removeTool(id)
  }, [removeTool])

  // Anti-spam: Can only create new chat if:
  // 1. No current chat, OR
  // 2. Current chat has messages (not empty), OR
  // 3. Current chat is NOT an optimistic conversation (tempId) without messages
  const canCreateNewChat = React.useMemo(() => {
    if (!currentChatId) return true
    if (messages.length > 0) return true

    // Block if current is an optimistic conversation without messages
    const isOptimistic = currentChatId.startsWith('temp-')
    const hasOptimistic = optimisticConversations.size > 0

    return !(isOptimistic || hasOptimistic)
  }, [currentChatId, messages.length, optimisticConversations.size])

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
          isCreatingConversation={isCreatingConversation}
          optimisticConversations={optimisticConversations}
          canCreateNew={canCreateNewChat}
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
          currentChatId={currentChatId}
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
