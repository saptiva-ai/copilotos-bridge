'use client'

import * as React from 'react'
import { Button, Textarea } from '../ui'
import { cn } from '../../lib/utils'

interface ChatInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  onCancel?: () => void
  disabled?: boolean
  loading?: boolean
  placeholder?: string
  maxLength?: number
  showCancel?: boolean
  className?: string
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  onCancel,
  disabled = false,
  loading = false,
  placeholder = "Type your message... (Press Enter to send, Shift+Enter for new line)",
  maxLength = 10000,
  showCancel = false,
  className,
}: ChatInputProps) {
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value.trim() && !disabled && !loading) {
        onSubmit()
      }
    }
    
    // Escape to cancel
    if (e.key === 'Escape' && showCancel && onCancel) {
      onCancel()
    }
  }

  // Auto-focus when not disabled
  React.useEffect(() => {
    if (!disabled && !loading && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [disabled, loading])

  const canSubmit = value.trim().length > 0 && !disabled && !loading

  return (
    <div className={cn('border-t border-gray-200 bg-white', className)}>
      <div className="px-4 py-4">
        <div className="flex flex-col space-y-3">
          {/* Input area */}
          <div className="relative">
            <Textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled || loading}
              autoResize
              rows={1}
              className="min-h-[44px] max-h-32 pr-12 resize-none"
              maxLength={maxLength}
            />
            
            {/* Character count */}
            {maxLength && (
              <div className="absolute bottom-2 right-12 text-xs text-gray-400">
                {value.length}/{maxLength}
              </div>
            )}

            {/* Send button */}
            <div className="absolute bottom-2 right-2">
              <Button
                size="sm"
                disabled={!canSubmit}
                loading={loading}
                onClick={onSubmit}
                className="h-8 w-8 p-0"
              >
                {!loading && (
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                )}
              </Button>
            </div>
          </div>

          {/* Bottom bar with tools and actions */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {/* File upload button */}
              <Button variant="ghost" size="sm" disabled={disabled || loading}>
                <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
                Attach
              </Button>

              {/* Tools toggle */}
              <Button variant="ghost" size="sm" disabled={disabled || loading}>
                <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Tools
              </Button>
            </div>

            <div className="flex items-center space-x-2">
              {/* Cancel button (when editing/regenerating) */}
              {showCancel && onCancel && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={onCancel}
                  disabled={loading}
                >
                  Cancel
                </Button>
              )}

              {/* Keyboard shortcut hint */}
              <div className="text-xs text-gray-400 hidden sm:block">
                Enter to send • Shift+Enter for new line
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}