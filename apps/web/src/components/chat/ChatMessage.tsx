'use client'

import * as React from 'react'
import { cn, formatRelativeTime, copyToClipboard } from '../../lib/utils'
import { Button, Badge } from '../ui'
import { StreamingMessage } from './StreamingMessage'

export interface ChatMessageProps {
  id?: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: Date | string
  model?: string
  status?: 'sending' | 'delivered' | 'error' | 'streaming'
  tokens?: number
  latencyMs?: number
  isStreaming?: boolean
  task_id?: string
  metadata?: {
    research_task?: {
      id: string
      status: string
      progress?: number
      created_at: string
      updated_at: string
      estimated_completion?: string
      [key: string]: any
    }
    [key: string]: any
  }
  onCopy?: (text: string) => void
  onRetry?: (messageId: string) => void
  onRegenerate?: (messageId: string) => void
  onStop?: () => void
  onViewReport?: (taskId: string, taskTitle: string) => void
  className?: string
  // Additional props for UX-005
  isError?: boolean
  latency?: number
}

export function ChatMessage({
  id,
  role,
  content,
  timestamp,
  model,
  status = 'delivered',
  tokens,
  latencyMs,
  isStreaming = false,
  task_id,
  metadata,
  onCopy,
  onRetry,
  onRegenerate,
  onStop,
  onViewReport,
  className,
  isError = false,
  latency,
}: ChatMessageProps) {
  const [copied, setCopied] = React.useState(false)

  const isUser = role === 'user'
  const isSystem = role === 'system'
  const isAssistant = role === 'assistant'

  const handleCopy = async () => {
    const success = await copyToClipboard(content)
    if (success) {
      setCopied(true)
      onCopy?.(content)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const getStatusBadge = () => {
    switch (status) {
      case 'sending':
        return <Badge variant="info" size="sm">Enviando...</Badge>
      case 'streaming':
        return null // TypingIndicator already shows this in StreamingMessage
      case 'error':
        return <Badge variant="error" size="sm">Error</Badge>
      default:
        return null
    }
  }

  if (isSystem) {
    return (
      <div className="flex justify-center my-4">
        <div className="bg-gray-100 text-gray-600 px-3 py-1 rounded-full text-sm">
          {content}
        </div>
      </div>
    )
  }

  return (
    <div
      className={cn(
        'group flex gap-3 px-4 py-6 transition-colors duration-150',
        isUser ? 'flex-row-reverse' : 'flex-row',
        'hover:bg-white/5',
        className,
      )}
      role="article"
      aria-label={`${isUser ? 'Mensaje del usuario' : 'Respuesta del asistente'} - ${formatRelativeTime(timestamp || new Date())}`}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-medium uppercase',
          isUser
            ? 'bg-primary/20 text-primary'
            : 'bg-white/10 text-white opacity-60',
        )}
      >
        {isUser ? 'Tú' : 'AI'}
      </div>

      {/* Message content */}
      <div className={cn('flex-1 min-w-0', isUser ? 'text-right' : 'text-left')}>
        {/* Removed: Header with "Usuario Just now" and "Saptiva Turbo Just now" for minimal UI */}

        <div
          className={cn(
            'inline-flex max-w-full rounded-3xl px-5 py-4 text-left text-sm leading-relaxed',
            isUser
              ? 'bg-primary/15 text-white'
              : 'bg-[var(--surface)] text-white',
            isError && 'bg-danger/5',
          )}
          style={
            isUser
              ? {
                  boxShadow: 'inset 0 0 0 0.5px rgba(73, 247, 217, 0.4), 0 0 12px rgba(73, 247, 217, 0.15)',
                }
              : {
                  boxShadow: 'inset 0 0 0 0.5px var(--hairline)',
                }
          }
          role="region"
          aria-label="Contenido del mensaje"
        >
          <div className="whitespace-pre-wrap break-words">
            {isAssistant ? (
              <StreamingMessage
                content={content}
                isStreaming={isStreaming}
                isComplete={status === 'delivered'}
              />
            ) : (
              content
            )}
          </div>
        </div>

        {/* Removed: Footer with "XXX tokens Saptiva Turbo" for minimal UI */}
        {/* Only show error retry button */}
        {status === 'error' && onRetry && id && (
          <div className={cn(
            'mt-2 flex items-center',
            isUser ? 'justify-end' : 'justify-start'
          )}>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRetry(id)}
              className="px-2 text-xs font-medium text-danger hover:text-danger/80"
            >
              Reintentar
            </Button>
          </div>
        )}

        {/* Actions (visible on hover or when streaming) - UX-005 */}
        <div className={cn(
          'mt-2 flex items-center gap-1 transition-opacity duration-150',
          isStreaming ? 'opacity-100' : 'opacity-0 group-hover:opacity-100',
          isUser ? 'justify-end' : 'justify-start'
        )}>
          {/* Stop button when streaming */}
          {isStreaming && onStop && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onStop}
              className="px-2 text-xs font-bold uppercase tracking-wide text-danger hover:text-danger/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger/60 focus-visible:ring-offset-1 focus-visible:ring-offset-surface"
              aria-label="Detener generación de respuesta"
            >
              <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
              Stop
            </Button>
          )}

          {/* Copy button */}
          {!isStreaming && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="px-2 text-xs font-bold uppercase tracking-wide text-saptiva-light/60 hover:text-saptiva-mint focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-1 focus-visible:ring-offset-surface"
              aria-label={copied ? "Texto copiado al portapapeles" : "Copiar mensaje"}
            >
              {copied ? (
                <>
                  <svg className="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                  Copiado
                </>
              ) : (
                <>
                  <svg className="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copy
                </>
              )}
            </Button>
          )}

          {/* Regenerate button for assistant messages */}
          {isAssistant && !isStreaming && onRegenerate && id && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRegenerate(id)}
              className="px-2 text-xs font-bold uppercase tracking-wide text-saptiva-light/60 hover:text-saptiva-mint focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-1 focus-visible:ring-offset-surface"
              aria-label="Regenerar respuesta"
            >
              <svg className="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Regenerate
            </Button>
          )}

          {/* Research report button */}
          {task_id && metadata?.research_task && onViewReport && !isStreaming && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onViewReport(task_id, content.slice(0, 50) + '...')}
              className="px-2 text-xs font-bold uppercase tracking-wide text-saptiva-light/60 hover:text-saptiva-mint focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-1 focus-visible:ring-offset-surface"
              aria-label={`Ver reporte de investigación: ${metadata?.research_task?.status}`}
            >
              <svg className="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Report ({metadata.research_task.status})
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
