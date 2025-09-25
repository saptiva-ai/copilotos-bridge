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
// Demo banner intentionally hidden per stakeholder request

interface ChatViewProps {
  initialChatId?: string | null
}

export function ChatView({ initialChatId = null }: ChatViewProps) {
  const { isAuthenticated, isHydrated } = useRequireAuth()
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
    addMessage,
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

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
      // TODO: Add attachment metadata to message for display
      attachments: attachments?.map(a => ({
        name: a.name,
        size: a.size,
        type: a.type
      })),
    }

    addMessage(userMessage)
    setLoading(true)

    try {
      // TODO: Handle file uploads to backend
      // For now, just send the message without attachments
      const response = await apiClient.sendChatMessage({
        message,
        chat_id: currentChatId || undefined,
        model: selectedModel,
        temperature: 0.7,
        max_tokens: 1024,
        stream: false,
        tools_enabled: toolsEnabled,
        // TODO: Add attachments to API request
        // attachments: attachments?.map(a => a.file),
      })

      const assistantMessage: ChatMessage = {
        id: response.message_id || `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.content,
        timestamp: response.created_at || new Date().toISOString(),
        model: response.model,
        tokens: response.tokens || 0,
        latency: response.latency_ms || 0,
      }

      addMessage(assistantMessage)
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error while processing your message. Please try again.',
        timestamp: new Date().toISOString(),
        model: selectedModel,
        isError: true,
      }

      addMessage(errorMessage)
    } finally {
      setLoading(false)
    }
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
    console.log('Stop streaming requested')
    setLoading(false)
  }, [setLoading])

  const handleCopyMessage = () => {}

  const handleSelectChat = React.useCallback((chatId: string) => {
    setCurrentChatId(chatId)
    loadUnifiedHistory(chatId)
    refreshChatStatus(chatId)
  }, [setCurrentChatId, loadUnifiedHistory, refreshChatStatus])

  const handleStartNewChat = React.useCallback(() => {
    setCurrentChatId(null)
    clearMessages()
    startNewChat()
  }, [setCurrentChatId, clearMessages, startNewChat])

  // Chat action handlers - UX-002
  const handleRenameChat = React.useCallback((chatId: string, newTitle: string) => {
    // TODO: Implement chat rename API call
    console.log('Rename chat:', chatId, 'to:', newTitle)
  }, [])

  const handlePinChat = React.useCallback((chatId: string) => {
    // TODO: Implement chat pin/unpin API call
    console.log('Toggle pin for chat:', chatId)
  }, [])

  const handleDeleteChat = React.useCallback((chatId: string) => {
    // TODO: Implement chat deletion API call
    console.log('Delete chat:', chatId)
    // If deleting current chat, redirect to new chat
    if (chatId === currentChatId) {
      handleStartNewChat()
    }
  }, [currentChatId, handleStartNewChat])

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

  // Chat not found state
  const chatNotFoundComponent = chatNotFound && resolvedChatId ? (
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
    <ChatWelcomeMessage />
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
          welcomeMessage={chatNotFoundComponent}
          toolsEnabled={toolsEnabled}
          onToggleTool={toggleTool}
        />
      </div>
    </ChatShell>
  )
}
