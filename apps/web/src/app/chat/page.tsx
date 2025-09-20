'use client'

import * as React from 'react'
import { useSearchParams } from 'next/navigation'
import { ChatLayout } from '../../components/layout'
import { ChatMessage } from '../../lib/types'
import { 
  ChatInterface, 
  ChatWelcomeMessage, 
  ModelSelector, 
  ToolsPanel, 
} from '../../components/chat'
import { Card, CardHeader, CardContent } from '../../components/ui'
import { useChat, useUI } from '../../lib/store'
import { apiClient } from '../../lib/api-client'

function ChatPageContent() {
  const searchParams = useSearchParams()
  const sessionId = searchParams?.get('session')
  
  // Use Zustand store instead of local state
  const {
    messages,
    isLoading,
    selectedModel,
    toolsEnabled,
    sendMessage,
    startNewChat,
    setSelectedModel,
    addMessage,
    clearMessages,
    setLoading,
    toggleTool,
  } = useChat()
  
  const { checkConnection } = useUI()

  // Load session if provided in URL
  React.useEffect(() => {
    if (sessionId && sessionId !== 'new') {
      // Load existing session - implement when API is ready
      console.log('Loading session:', sessionId)
    } else if (!sessionId || sessionId === 'new') {
      startNewChat()
    }
  }, [sessionId, startNewChat])

  // Check API connection on mount
  React.useEffect(() => {
    checkConnection()
  }, [checkConnection])

  // Real API call function
  const sendMessageToAPI = async (userMessage: string, chatId?: string) => {
    try {
      console.log('Making API call to:', apiClient.baseURL)
      console.log('Request data:', { message: userMessage, model: selectedModel })

      const response = await apiClient.sendChatMessage({
        message: userMessage,
        chat_id: chatId,
        model: selectedModel,
        temperature: 0.7,
        max_tokens: 1024,
        stream: false
      })

      console.log('API response:', response)
      return response
    } catch (error) {
      console.error('API call failed:', error)
      throw error
    }
  }

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return

    // Add user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    }

    addMessage(userMessage)
    setLoading(true)

    try {
      // Real API call
      const response = await sendMessageToAPI(message)

      // Add assistant response
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
      // DEBUG: Log the actual error
      console.error('Chat API Error Details:', error)
      console.error('Error message:', error instanceof Error ? error.message : String(error))

      // Add error message
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
    // Find the failed message and the user message before it
    const messageIndex = messages.findIndex(m => m.id === messageId)
    if (messageIndex > 0) {
      const userMessage = messages[messageIndex - 1]
      if (userMessage.role === 'user') {
        // Retry with the user's message
        await handleSendMessage(userMessage.content)
      }
    }
  }

  const handleCopyMessage = (text: string) => {
    // The copyToClipboard function in the component will handle this
    console.log('Message copied:', text.substring(0, 50) + '...')
  }

  return (
    <ChatLayout>
      <div className="h-screen flex">
        {/* Main chat area */}
        <div className="flex-1 flex flex-col">
          <ChatInterface
            messages={messages}
            onSendMessage={handleSendMessage}
            onRetryMessage={handleRetryMessage}
            onCopyMessage={handleCopyMessage}
            loading={isLoading}
            welcomeMessage={<ChatWelcomeMessage />}
            toolsEnabled={toolsEnabled}
            onToggleTool={toggleTool}
          />
        </div>

        
      </div>
    </ChatLayout>
  )
}

export default function ChatPage() {
  return (
    <React.Suspense fallback={<div>Loading...</div>}>
      <ChatPageContent />
    </React.Suspense>
  )
}