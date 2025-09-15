'use client'

import * as React from 'react'
import { ChatMessage, ChatMessageProps } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { LoadingSpinner } from '../ui'
import { cn } from '../../lib/utils'

interface ChatInterfaceProps {
  messages: ChatMessageProps[]
  onSendMessage: (message: string) => void
  onRetryMessage?: (messageId: string) => void
  onCopyMessage?: (text: string) => void
  loading?: boolean
  disabled?: boolean
  className?: string
  welcomeMessage?: React.ReactNode
}

export function ChatInterface({
  messages,
  onSendMessage,
  onRetryMessage,
  onCopyMessage,
  loading = false,
  disabled = false,
  className,
  welcomeMessage,
}: ChatInterfaceProps) {
  const [inputValue, setInputValue] = React.useState('')
  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  const messagesContainerRef = React.useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = React.useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  React.useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Handle sending message
  const handleSendMessage = React.useCallback(() => {
    if (inputValue.trim() && !loading && !disabled) {
      onSendMessage(inputValue.trim())
      setInputValue('')
    }
  }, [inputValue, onSendMessage, loading, disabled])

  // Show welcome message when no messages
  const showWelcome = messages.length === 0 && !loading

  return (
    <div className={cn('flex flex-col h-full bg-white', className)}>
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto" ref={messagesContainerRef}>
        {showWelcome && welcomeMessage && (
          <div className="flex items-center justify-center h-full p-8">
            <div className="text-center max-w-md">
              {welcomeMessage}
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="space-y-0">
          {messages.map((message, index) => (
            <ChatMessage
              key={message.id || index}
              {...message}
              onCopy={onCopyMessage}
              onRetry={onRetryMessage}
            />
          ))}
        </div>

        {/* Loading indicator */}
        {loading && messages.length > 0 && (
          <div className="flex justify-center py-4">
            <LoadingSpinner size="sm" text="AI is thinking..." />
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSubmit={handleSendMessage}
        disabled={disabled}
        loading={loading}
        showCancel={loading}
        onCancel={loading ? () => {/* TODO: implement cancel */} : undefined}
      />
    </div>
  )
}

// Welcome message component
export function ChatWelcomeMessage() {
  return (
    <div className="text-center">
      <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </div>
      <h2 className="text-xl font-semibold text-gray-900 mb-2">Welcome to CopilotOS</h2>
      <p className="text-gray-600 mb-6">
        Start a conversation with AI or launch a deep research task. 
        I can help with questions, analysis, and comprehensive research.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        <div className="bg-gray-50 rounded-lg p-3 text-left">
          <div className="font-medium text-gray-900 mb-1">💬 Quick Chat</div>
          <div className="text-gray-600">Ask questions and get instant AI responses</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-left">
          <div className="font-medium text-gray-900 mb-1">🔍 Deep Research</div>
          <div className="text-gray-600">Enable research mode for comprehensive analysis</div>
        </div>
      </div>
    </div>
  )
}