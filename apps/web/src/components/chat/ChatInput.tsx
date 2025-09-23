'use client'

import * as React from 'react'
import { Button, Textarea } from '../ui'
import { ModelSelector } from './ModelSelector'
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
  // Model selection
  selectedModel?: string
  onModelChange?: (model: string) => void
  // Tools configuration
  toolsEnabled?: { [key: string]: boolean }
  onToggleTool?: (tool: string) => void
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
  selectedModel,
  onModelChange,
  toolsEnabled,
  onToggleTool,
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
  const hasActiveTools = toolsEnabled && Object.values(toolsEnabled).some(Boolean)

  return (
    <div className={cn('border-t border-gray-200 bg-white', className)}>
      <div className="px-4 py-4">
        {/* Main input container */}
        <div className="flex items-start gap-3">
          {/* Model Selector - Left side */}
          {selectedModel && onModelChange && (
            <div className="flex-shrink-0 pt-1">
              <ModelSelector
                selectedModel={selectedModel}
                onModelChange={onModelChange}
                disabled={disabled || loading}
                className="text-sm"
              />
            </div>
          )}

          {/* Input area with send button - Main area */}
          <div className="flex-1 relative">
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
        </div>

        {/* Tools and actions bar with wrapping behavior */}
        <div className="flex flex-wrap items-center justify-between gap-3 mt-3">
          {/* Tools section - can wrap */}
          <div className="flex flex-wrap items-center gap-3">
            {toolsEnabled && onToggleTool && Object.entries(toolsEnabled).map(([toolName, enabled]) => (
              <div key={toolName} className="flex items-center gap-2">
                <button
                  onClick={() => onToggleTool(toolName)}
                  disabled={disabled || loading}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    enabled ? 'bg-saptiva-blue' : 'bg-gray-200'
                  } ${disabled || loading ? 'opacity-50' : ''}`}
                  aria-label={`Toggle ${toolName.replace('_', ' ')}`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                      enabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
                <label className="text-sm font-medium text-gray-700 capitalize whitespace-nowrap">
                  {toolName.replace('_', ' ')}
                </label>
              </div>
            ))}

            {/* Active tools indicator */}
            {hasActiveTools && (
              <div className="flex items-center gap-1 text-xs text-saptiva-blue bg-saptiva-blue/10 px-2 py-1 rounded-full">
                <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Tools Active
              </div>
            )}
          </div>

          {/* Actions section */}
          <div className="flex items-center gap-2">
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

            {/* Keyboard shortcut hint - hide on small screens */}
            <div className="text-xs text-gray-400 hidden md:block whitespace-nowrap">
              Enter to send • Shift+Enter for new line
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}