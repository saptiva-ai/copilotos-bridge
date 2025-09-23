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
    // Try multiple approaches to ensure scroll works
    setTimeout(() => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
      }

      // Fallback: scroll the container directly
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
      }
    }, 100) // Small delay to ensure DOM is updated
  }, [])

  React.useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Also scroll when loading changes (when response comes in)
  React.useEffect(() => {
    if (!loading && messages.length > 0) {
      scrollToBottom()
    }
  }, [loading, scrollToBottom, messages.length])

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
    <div className={cn('flex h-full flex-col', className)}>
      {/* Messages area with dedicated scroll container */}
      <section
        id="message-list"
        className="relative flex-1 min-h-0 overflow-y-auto overscroll-contain"
        ref={messagesContainerRef}
        style={{ scrollBehavior: 'smooth' }}
      >
        <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-white/10 to-transparent" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-black/20 to-transparent" />

        <div className="relative container-saptiva pt-16 pb-6 min-h-full">
          {showWelcome ? (
            <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
              {welcomeMessage && (
                <div className="mx-auto mb-12 max-w-xl text-white/90">
                  {welcomeMessage}
                </div>
              )}
              <QuickPrompts
                onPromptSelect={handleQuickPromptSelect}
                className="w-full animate-fade-in"
              />
            </div>
          ) : (
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

              {loading && (
                <div className="flex justify-center py-6">
                  <LoadingSpinner size="sm" text="Saptiva está pensando..." />
                </div>
              )}
            </div>
          )}

          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </div>
      </section>

      {/* Input area as footer */}
      <footer className="shrink-0 border-t border-white/10 bg-black/20 px-4 pb-8 pt-4 backdrop-blur-md sm:px-6 lg:px-10">
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
      </footer>

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
    <div className="mx-auto max-w-xl text-center text-white">
      <div className="inline-flex items-center rounded-full border border-white/20 bg-white/5 px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-saptiva-light/70">
        Saptiva Copilot OS
      </div>
      <h2 className="mt-4 text-3xl font-semibold text-white">
        Conversaciones con enfoque, evidencia y control
      </h2>
      <p className="mt-3 text-sm text-saptiva-light/70">
        Inicia tu consulta o activa Deep Research para investigar con trazabilidad completa.
      </p>
    </div>
  )
}
