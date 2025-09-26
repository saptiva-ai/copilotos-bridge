'use client'

import * as React from 'react'
import { cn } from '../../lib/utils'

interface TypingIndicatorProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
  message?: string
}

export function TypingIndicator({
  className,
  size = 'md',
  message = "Escribiendo..."
}: TypingIndicatorProps) {
  const [dots, setDots] = React.useState('.')

  React.useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => {
        if (prev === '...') return '.'
        return prev + '.'
      })
    }, 500)

    return () => clearInterval(interval)
  }, [])

  const sizeClasses = {
    sm: 'h-1 w-1',
    md: 'h-1.5 w-1.5',
    lg: 'h-2 w-2'
  }

  const containerSizes = {
    sm: 'gap-1 text-xs',
    md: 'gap-1.5 text-sm',
    lg: 'gap-2 text-base'
  }

  return (
    <div className={cn(
      'flex items-center text-text-muted',
      containerSizes[size],
      className
    )}>
      <div className="flex items-center gap-1">
        <div
          className={cn(
            'bg-current rounded-full animate-pulse',
            sizeClasses[size]
          )}
          style={{ animationDelay: '0ms' }}
        />
        <div
          className={cn(
            'bg-current rounded-full animate-pulse',
            sizeClasses[size]
          )}
          style={{ animationDelay: '200ms' }}
        />
        <div
          className={cn(
            'bg-current rounded-full animate-pulse',
            sizeClasses[size]
          )}
          style={{ animationDelay: '400ms' }}
        />
      </div>
      <span className="ml-2 font-medium">
        {message}{dots}
      </span>
    </div>
  )
}

export function StreamingCursor({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        'inline-block w-0.5 h-4 bg-primary animate-pulse ml-0.5',
        className
      )}
      style={{ animationDuration: '1s' }}
    />
  )
}