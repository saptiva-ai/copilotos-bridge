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
import type { ChatComposerAttachment } from '../../../components/chat/ChatComposer'
import { useChat, useUI } from '../../../lib/store'
import { apiClient } from '../../../lib/api-client'
import { useRequireAuth } from '../../../hooks/useRequireAuth'
import { useSelectedTools } from '../../../hooks/useSelectedTools'
import { useOptimizedChat } from '../../../hooks/useOptimizedChat'
import type { ToolId } from '../../../types/tools'
import WelcomeBanner from '../../../components/chat/WelcomeBanner'
import { useAuthStore } from '../../../lib/auth-store'
import { logDebug } from '../../../lib/logger'
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
    setCurrentChatId,
    loadUnifiedHistory,
    refreshChatStatus,
  } = useChat()

  const { checkConnection } = useUI()
  const { selected: selectedTools, addTool, removeTool } = useSelectedTools()
  const { sendOptimizedMessage, isTyping, getCachedResponse } = useOptimizedChat({
    enablePredictiveLoading: true,
    enableResponseCache: true,
    streamingChunkSize: 3
  })

  React.useEffect(() => {
    checkConnection()
  }, [checkConnection])

  React.useEffect(() => {
    if (isAuthenticated && isHydrated) {
      loadChatSessions()
    }
  }, [isAuthenticated, isHydrated, loadChatSessions])

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

  const handleSendMessage = async (message: string, attachments?: ChatComposerAttachment[]) => {
    if (!message.trim()) return

    // Use the optimized send message function for better UX
    await sendOptimizedMessage(message, async (msg: string, placeholderId: string) => {
      // Original API call logic
      const response = await apiClient.sendChatMessage({
        message: msg,
        chat_id: currentChatId || undefined,
        model: selectedModel,
        temperature: 0.3, // Reduced for faster responses
        max_tokens: 800,  // Reduced for more concise responses
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
    })
  }

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
    if (messageIndex > 0) {
      const userMessage = messages[messageIndex - 1]
      if (userMessage.role === 'user') {
        // TODO: Add API support for regeneration with same parameters
        await handleSendMessage(userMessage.content, userMessage.attachments as any)
      }
    }
  }

  const handleStopStreaming = React.useCallback(() => {
    // TODO: Implement streaming cancellation
    logDebug('Stop streaming requested')
    setLoading(false)
  }, [setLoading])

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
  const handleRenameChat = React.useCallback((chatId: string, newTitle: string) => {
    // TODO: Implement chat rename API call
    logDebug('Rename chat request', chatId, newTitle)
  }, [])

  const handlePinChat = React.useCallback((chatId: string) => {
    // TODO: Implement chat pin/unpin API call
    logDebug('Toggle pin for chat', chatId)
  }, [])

  const handleDeleteChat = React.useCallback((chatId: string) => {
    // TODO: Implement chat deletion API call
    logDebug('Delete chat request', chatId)
    // If deleting current chat, redirect to new chat
    if (chatId === currentChatId) {
      handleStartNewChat()
    }
  }, [currentChatId, handleStartNewChat])

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
      selectedModel={selectedModel}
      onModelChange={setSelectedModel}
    >
      <div className="flex h-full flex-col">
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
