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
  onViewReport?: (taskId: string, taskTitle: string) => void
  className?: string
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
  onViewReport,
  className,
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
        'group flex gap-3 px-4 py-6 hover:bg-gray-50',
        isUser ? 'flex-row-reverse' : 'flex-row',
        className
      )}
    >
      {/* Avatar */}
      <div className={cn(
        'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
        isUser 
          ? 'bg-primary-600 text-white' 
          : 'bg-gray-200 text-gray-700'
      )}>
        {isUser ? 'U' : 'AI'}
      </div>

      {/* Message content */}
      <div className={cn(
        'flex-1 min-w-0',
        isUser ? 'text-right' : 'text-left'
      )}>
        {/* Header */}
        <div className={cn(
          'flex items-center gap-2 mb-1',
          isUser ? 'justify-end' : 'justify-start'
        )}>
          <span className="text-sm font-medium text-gray-900">
            {isUser ? 'You' : (model || 'Assistant')}
          </span>
          {timestamp && (
            <span className="text-xs text-gray-500">
              {formatRelativeTime(timestamp)}
            </span>
          )}
          {getStatusBadge()}
        </div>

        {/* Message text */}
        <div className={cn(
          'prose prose-sm max-w-none',
          isUser 
            ? 'bg-primary-600 text-white rounded-lg px-4 py-2 inline-block' 
            : 'text-gray-900'
        )}>
          {isStreaming && isAssistant ? (
            <div className="flex items-center">
              <span>{content}</span>
              <span className="ml-1 animate-typing">|</span>
            </div>
          ) : (
            <div className="whitespace-pre-wrap break-words">
              {content}
            </div>
          )}
        </div>

        {/* Footer with metadata and actions */}
        {(tokens || latencyMs || status === 'error') && (
          <div className={cn(
            'flex items-center gap-2 mt-2 text-xs text-gray-500',
            isUser ? 'justify-end' : 'justify-start'
          )}>
            {tokens && <span>{tokens} tokens</span>}
            {latencyMs && <span>{latencyMs}ms</span>}
            {status === 'error' && onRetry && id && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => onRetry(id)}
              >
                Retry
              </Button>
            )}
          </div>
        )}

        {/* Actions (visible on hover) */}
        <div className={cn(
          'opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 mt-2',
          isUser ? 'justify-end' : 'justify-start'
        )}>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="text-xs"
          >
            {copied ? (
              <>
                <svg className="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                Copied
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

          {/* Research report button */}
          {task_id && metadata?.research_task && onViewReport && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onViewReport(task_id, content.slice(0, 50) + '...')}
              className="text-xs"
            >
              <svg className="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Report ({metadata.research_task.status})
            </Button>
          )}

          {isAssistant && (
            <Button variant="ghost" size="sm" className="text-xs">
              <svg className="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              Like
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}