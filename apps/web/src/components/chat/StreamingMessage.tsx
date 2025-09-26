'use client'

import * as React from 'react'
import { cn } from '../../lib/utils'
import { TypingIndicator, StreamingCursor } from '../ui/TypingIndicator'

interface StreamingMessageProps {
  content: string
  isStreaming?: boolean
  isComplete?: boolean
  className?: string
}

export function StreamingMessage({
  content,
  isStreaming = false,
  isComplete = false,
  className
}: StreamingMessageProps) {
  const [displayedContent, setDisplayedContent] = React.useState('')
  const [showCursor, setShowCursor] = React.useState(false)

  // Efecto para mostrar contenido de forma progresiva durante streaming
  React.useEffect(() => {
    if (!isStreaming || isComplete) {
      setDisplayedContent(content)
      setShowCursor(false)
      return
    }

    // Mostrar contenido token por token para efecto natural
    if (content.length > displayedContent.length) {
      const timeoutId = setTimeout(() => {
        setDisplayedContent(content.slice(0, displayedContent.length + 1))
        setShowCursor(true)
      }, 30) // 30ms por carácter para fluidez natural

      return () => clearTimeout(timeoutId)
    }
  }, [content, displayedContent, isStreaming, isComplete])

  // Mostrar typing indicator si no hay contenido aún
  if (isStreaming && displayedContent.length === 0) {
    return (
      <div className={cn('py-2', className)}>
        <TypingIndicator message="Generando respuesta" size="sm" />
      </div>
    )
  }

  return (
    <div className={cn('relative', className)}>
      {/* Contenido renderizado progresivamente */}
      <div className="whitespace-pre-wrap">
        {displayedContent}
        {/* Cursor de streaming */}
        {isStreaming && showCursor && !isComplete && (
          <StreamingCursor />
        )}
      </div>

      {/* Indicador de estado al final del streaming */}
      {isStreaming && !isComplete && displayedContent.length > 0 && (
        <div className="mt-2 text-xs text-text-muted opacity-60">
          <TypingIndicator message="Escribiendo" size="sm" />
        </div>
      )}
    </div>
  )
}

export function MessageSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('animate-pulse space-y-2', className)}>
      <div className="h-4 bg-surface rounded w-3/4"></div>
      <div className="h-4 bg-surface rounded w-1/2"></div>
      <div className="h-4 bg-surface rounded w-2/3"></div>
    </div>
  )
}