'use client'

import * as React from 'react'
import { ChatMessage, ChatMessageProps } from './ChatMessage'
import { ChatComposer, ChatComposerAttachment } from './ChatComposer'
import { CompactChatComposer } from './ChatComposer/CompactChatComposer'
import { ChatHero } from './ChatHero'
import { LoadingSpinner } from '../ui'
import { ReportPreviewModal } from '../research/ReportPreviewModal'
import { cn } from '../../lib/utils'
import type { ToolId } from '@/types/tools'
import { visibleTools } from '@/lib/feature-flags'
import { useAuthStore } from '@/lib/auth-store'

import { FeatureFlagsResponse } from '@/lib/types'

interface ChatInterfaceProps {
  messages: ChatMessageProps[]
  onSendMessage: (message: string, attachments?: ChatComposerAttachment[]) => void
  onRetryMessage?: (messageId: string) => void
  onRegenerateMessage?: (messageId: string) => void
  onStopStreaming?: () => void
  onCopyMessage?: (text: string) => void
  loading?: boolean
  disabled?: boolean
  className?: string
  welcomeMessage?: React.ReactNode
  toolsEnabled?: { [key: string]: boolean }
  onToggleTool?: (tool: string) => void
  selectedTools?: ToolId[]
  onRemoveTool?: (id: ToolId) => void
  onAddTool?: (id: ToolId) => void
  onOpenTools?: () => void
  featureFlags?: FeatureFlagsResponse | null
}

const LEGACY_KEY_TO_TOOL_ID: Partial<Record<string, ToolId>> = {
  deep_research: 'deep-research',
  web_search: 'web-search',
  code_analysis: 'agent-mode',
  document_analysis: 'canvas',
}

const TOOL_ID_TO_LEGACY_KEY: Partial<Record<ToolId, string>> = {
  'deep-research': 'deep_research',
  'web-search': 'web_search',
  'agent-mode': 'code_analysis',
  canvas: 'document_analysis',
}

export function ChatInterface({
  messages,
  onSendMessage,
  onRetryMessage,
  onRegenerateMessage,
  onStopStreaming,
  onCopyMessage,
  loading = false,
  disabled = false,
  className,
  welcomeMessage,
  toolsEnabled,
  onToggleTool,
  selectedTools,
  onRemoveTool,
  onAddTool,
  onOpenTools,
  featureFlags,
}: ChatInterfaceProps) {
  const [inputValue, setInputValue] = React.useState('')
  const [attachments, setAttachments] = React.useState<ChatComposerAttachment[]>([])
  const [reportModal, setReportModal] = React.useState({ isOpen: false, taskId: '', taskTitle: '' })
  const [heroMode, setHeroMode] = React.useState(true)
  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  const messagesContainerRef = React.useRef<HTMLDivElement>(null)
  const user = useAuthStore((state) => state.user)

  const scrollToBottom = React.useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
      }
    }, 100)
  }, [])

  React.useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  React.useEffect(() => {
    if (!loading && messages.length > 0) {
      scrollToBottom()
    }
  }, [loading, scrollToBottom, messages.length])

  const handleSend = React.useCallback(async () => {
    const trimmed = inputValue.trim()
    if (!trimmed || disabled || loading) return

    onSendMessage(trimmed, attachments.length ? attachments : undefined)
    setInputValue('')
    setAttachments([])
  }, [inputValue, disabled, loading, onSendMessage, attachments])

  const handleFileAttachmentChange = React.useCallback((next: ChatComposerAttachment[]) => {
    setAttachments(next)
  }, [])

  const selectedToolIds = React.useMemo<ToolId[]>(() => {
    // Prefer the new selectedTools prop if available (including empty arrays)
    if (selectedTools !== undefined) {
      return selectedTools
    }

    // Fallback to legacy toolsEnabled only if selectedTools is not passed
    if (!toolsEnabled) return []

    return Object.entries(toolsEnabled)
      .filter(([, enabled]) => enabled)
      .map(([legacyKey]) => LEGACY_KEY_TO_TOOL_ID[legacyKey])
      .filter((id): id is ToolId => {
        if (!id) return false
        return Boolean(visibleTools[id])
      })
  }, [selectedTools, toolsEnabled])

  const handleRemoveToolInternal = React.useCallback(
    (id: ToolId) => {
      // Prefer the new onRemoveTool prop if available
      if (onRemoveTool) {
        onRemoveTool(id)
        return
      }

      // Fallback to legacy onToggleTool
      if (onToggleTool) {
        const legacyKey = TOOL_ID_TO_LEGACY_KEY[id]
        if (legacyKey) {
          onToggleTool(legacyKey)
        }
      }
    },
    [onRemoveTool, onToggleTool],
  )

  const showWelcome = messages.length === 0 && !loading

  // Switch to expanded mode when messages exist or on first interaction
  React.useEffect(() => {
    if (messages.length > 0) {
      setHeroMode(false)
    }
  }, [messages.length])

  // Auto-scroll to bottom on new messages
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  const handleActivate = React.useCallback(() => {
    setHeroMode(false)
  }, [])

  return (
    <div className={cn('flex h-full flex-col relative', className)}>
      {showWelcome && heroMode ? (
        /* Hero Mode: Centered container with greeting + composer */
        <section className="flex-1 flex items-center justify-center px-4">
          <div className="w-full max-w-[640px] space-y-6 text-center">
            <h1 className="text-3xl font-semibold text-white/95">
              ¿Cómo puedo ayudarte, {user?.username || 'Usuario'}?
            </h1>

            {/* Composer in hero mode - part of the same centered container */}
            <CompactChatComposer
              value={inputValue}
              onChange={setInputValue}
              onSubmit={handleSend}
              onCancel={loading ? onStopStreaming : undefined}
              disabled={disabled}
              loading={loading}
              layout="center"
              onActivate={handleActivate}
              showCancel={loading}
              selectedTools={selectedToolIds}
              onRemoveTool={handleRemoveToolInternal}
              onAddTool={onAddTool}
              attachments={attachments}
              onAttachmentsChange={handleFileAttachmentChange}
            />
          </div>
        </section>
      ) : (
        /* Chat Mode: Messages + bottom composer */
        <>
          <section
            id="message-list"
            ref={messagesContainerRef}
            className="relative flex-1 min-h-0 overflow-y-auto overscroll-contain thin-scroll main-has-composer"
            style={{ scrollBehavior: 'smooth' }}
          >
            <div className="relative mx-auto max-w-3xl px-4 min-h-full pb-6 pt-16">
              <div className="space-y-0">
                {messages.map((message, index) => (
                  <ChatMessage
                    key={message.id || index}
                    {...message}
                    onCopy={onCopyMessage}
                    onRetry={onRetryMessage}
                    onRegenerate={onRegenerateMessage}
                    onStop={onStopStreaming}
                    onViewReport={(taskId, taskTitle) =>
                      setReportModal({ isOpen: true, taskId: taskId ?? '', taskTitle: taskTitle ?? '' })
                    }
                  />
                ))}
              </div>
              <div ref={messagesEndRef} />
            </div>
          </section>

          {/* Composer at bottom in chat mode */}
          <CompactChatComposer
            value={inputValue}
            onChange={setInputValue}
            onSubmit={handleSend}
            onCancel={loading ? onStopStreaming : undefined}
            disabled={disabled}
            loading={loading}
            layout="bottom"
            showCancel={loading}
            selectedTools={selectedToolIds}
            onRemoveTool={handleRemoveToolInternal}
            onAddTool={onAddTool}
            attachments={attachments}
            onAttachmentsChange={handleFileAttachmentChange}
          />
        </>
      )}

      <ReportPreviewModal
        isOpen={reportModal.isOpen}
        taskId={reportModal.taskId}
        taskTitle={reportModal.taskTitle}
        onClose={() => setReportModal({ isOpen: false, taskId: '', taskTitle: '' })}
      />
    </div>
  )
}

export function ChatWelcomeMessage() {
  return (
    <div className="mx-auto max-w-xl text-center text-white">
      <div className="inline-flex items-center rounded-full border border-white/20 bg-white/5 px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-saptiva-light/70">
        Saptiva Copilot OS
      </div>
      <h2 className="mt-4 text-3xl font-semibold text-white">Conversaciones con enfoque, evidencia y control</h2>
      <p className="mt-3 text-sm text-saptiva-light/70">
        Inicia tu consulta o activa Deep Research para investigar con trazabilidad completa.
      </p>
    </div>
  )
}
