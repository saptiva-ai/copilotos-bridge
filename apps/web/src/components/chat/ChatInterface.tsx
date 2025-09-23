'use client'

import * as React from 'react'
import { ChatMessage, ChatMessageProps } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { QuickPrompts } from './QuickPrompts'
import { LoadingSpinner } from '../ui'
import { ReportPreviewModal } from '../research/ReportPreviewModal'
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
  toolsEnabled?: { [key: string]: boolean }
  onToggleTool?: (tool: string) => void
  selectedModel?: string
  onModelChange?: (model: string) => void
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
  toolsEnabled,
  onToggleTool,
  selectedModel,
  onModelChange,
}: ChatInterfaceProps) {
  const [inputValue, setInputValue] = React.useState('')
  const [reportModal, setReportModal] = React.useState<{
    isOpen: boolean
    taskId: string
    taskTitle: string
  }>({ isOpen: false, taskId: '', taskTitle: '' })
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
  const handleSendMessage = React.useCallback((message?: string) => {
    const messageToSend = message || inputValue.trim()
    if (messageToSend && !loading && !disabled) {
      onSendMessage(messageToSend)
      if (!message) setInputValue('') // Only clear if using input value
    }
  }, [inputValue, onSendMessage, loading, disabled])

  // Handle quick prompt selection - send immediately
  const handleQuickPromptSelect = React.useCallback((prompt: string) => {
    handleSendMessage(prompt) // Send directly without setting input value
  }, [handleSendMessage])

  // Handle viewing report
  const handleViewReport = React.useCallback((taskId: string, taskTitle: string) => {
    setReportModal({ isOpen: true, taskId, taskTitle })
  }, [])

  // Show welcome message when no messages
  const showWelcome = messages.length === 0 && !loading

  return (
    <div className={cn('flex flex-col h-full bg-white', className)}>
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto" ref={messagesContainerRef}>
        {showWelcome && (
          <div className="flex items-center justify-center min-h-full p-8">
            <div className="w-full">
              {/* Welcome message */}
              {welcomeMessage && (
                <div className="text-center max-w-md mx-auto mb-12">
                  {welcomeMessage}
                </div>
              )}

              {/* Quick prompts */}
              <QuickPrompts
                onPromptSelect={handleQuickPromptSelect}
                className="animate-fade-in"
              />
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
              onViewReport={handleViewReport}
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
        toolsEnabled={toolsEnabled}
        onToggleTool={onToggleTool}
        selectedModel={selectedModel}
        onModelChange={onModelChange}
      />

      {/* Report Preview Modal */}
      <ReportPreviewModal
        isOpen={reportModal.isOpen}
        taskId={reportModal.taskId}
        taskTitle={reportModal.taskTitle}
        onClose={() => setReportModal({ isOpen: false, taskId: '', taskTitle: '' })}
      />
    </div>
  )
}

// Welcome message component
export function ChatWelcomeMessage() {
  return (
    <div className="text-center">
      <h2 className="text-2xl font-semibold text-gray-800 mb-4">CopilotOS</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm max-w-md mx-auto">
        <div className="bg-gray-50 rounded-lg p-3 text-left cursor-pointer hover:bg-gray-100">
          <div className="font-medium text-gray-800">"Explain quantum computing in simple terms"</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-left cursor-pointer hover:bg-gray-100">
          <div className="font-medium text-gray-800">"What are the latest trends in AI?"</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-left cursor-pointer hover:bg-gray-100">
          <div className="font-medium text-gray-800">"Summarize the plot of 'Dune'"</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-left cursor-pointer hover:bg-gray-100">
          <div className="font-medium text-gray-800">"Write a python script to scrape a website"</div>
        </div>
      </div>
    </div>
  )
}