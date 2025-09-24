'use client'

import * as React from 'react'
import { cn, formatRelativeTime, copyToClipboard } from '../../lib/utils'
import { Button, Badge } from '../ui'

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
        return <Badge variant="info" size="sm">Sending...</Badge>
      case 'streaming':
        return <Badge variant="info" size="sm">Typing...</Badge>
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
          'flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-2xl text-xs font-bold uppercase shadow-inner backdrop-blur',
          isUser
            ? 'bg-saptiva-mint/25 text-saptiva-mint'
            : 'bg-white/10 text-white',
        )}
      >
        {isUser ? 'Tú' : 'AI'}
      </div>

      {/* Message content */}
      <div className={cn('flex-1 min-w-0', isUser ? 'text-right' : 'text-left')}>
        <div
          className={cn(
            'flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.25em]',
            isUser ? 'justify-end text-saptiva-light/60' : 'justify-start text-saptiva-light/50',
          )}
        >
          <span>{isUser ? 'Usuario' : model || 'Saptiva'}</span>
          {timestamp && <span>{formatRelativeTime(timestamp)}</span>}
          {getStatusBadge()}
        </div>

        <div
          className={cn(
            'mt-2 inline-flex max-w-full rounded-3xl px-5 py-4 text-left text-sm leading-relaxed shadow-[0_18px_35px_rgba(10,12,23,0.45)]',
            isUser
              ? 'bg-saptiva-mint/15 text-saptiva-light'
              : 'border border-white/10 bg-white/10 text-white backdrop-blur',
            isError && 'border-danger/50 bg-danger/5',
          )}
          role="region"
          aria-label="Contenido del mensaje"
        >
          <div className="whitespace-pre-wrap break-words">
            {isStreaming && isAssistant ? (
              <span className="flex items-start gap-1">
                {content}
                {/* Streaming cursor - UX-005 */}
                <span className="inline-block w-2 h-4 bg-primary animate-pulse rounded-sm mt-0.5" />
              </span>
            ) : (
              content
            )}
          </div>
        </div>

        {/* Footer with metadata - UX-005 */}
        {(tokens || latencyMs || latency || model || status === 'error' || isStreaming) && (
          <div className={cn(
            'mt-3 flex items-center gap-2 text-[11px] uppercase tracking-[0.25em] text-saptiva-light/40',
            isUser ? 'justify-end' : 'justify-start'
          )}>
            {/* Show streaming status first */}
            {isStreaming && (
              <span className="flex items-center gap-1 text-primary">
                <span className="w-1 h-1 bg-primary rounded-full animate-pulse" />
                Escribiendo...
              </span>
            )}

            {/* Token count */}
            {tokens && !isStreaming && <span>{tokens} tokens</span>}

            {/* Latency */}
            {(latencyMs || latency) && !isStreaming && (
              <span>{latencyMs || latency}ms</span>
            )}

            {/* Model name */}
            {model && !isStreaming && !isUser && (
              <span>{model}</span>
            )}

            {/* Error with retry */}
            {status === 'error' && onRetry && id && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onRetry(id)}
                className="px-2 text-xs font-bold uppercase tracking-wide text-danger hover:text-danger/80"
              >
                Reintentar
              </Button>
            )}
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
