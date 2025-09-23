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
    <div
      className={cn(
        'rounded-3xl border border-white/10 bg-white/[0.04] p-4 shadow-[0_25px_60px_rgba(7,10,17,0.45)]',
        'transition-colors duration-200',
        disabled && 'opacity-95',
        className,
      )}
    >
      {/* Main input row */}
      <div className="flex flex-wrap items-end gap-3 mb-3">
        {/* Model selector on the left */}
        {selectedModel && onModelChange && (
          <div className="flex-shrink-0 w-full sm:w-52">
            <ModelSelector
              selectedModel={selectedModel}
              onModelChange={onModelChange}
              disabled={disabled || loading}
              className="w-full"
            />
          </div>
        )}

        {/* Input field with flex-1 and minimum width */}
        <div className="relative flex-1 min-w-[240px]">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || loading}
            autoResize
            rows={1}
            maxLength={maxLength}
            className="min-h-[54px] max-h-40 resize-none border-white/15 bg-black/20 text-white placeholder:text-saptiva-light/50 focus:border-saptiva-mint/60 focus:ring-saptiva-mint/40"
          />

          {maxLength && (
            <div className="pointer-events-none absolute bottom-2 right-14 text-xs text-saptiva-light/60">
              {value.length}/{maxLength}
            </div>
          )}

          <div className="absolute bottom-2 right-2 flex items-center gap-2">
            {showCancel && onCancel && (
              <Button
                size="sm"
                variant="ghost"
                className="h-9 rounded-full border border-white/20 bg-black/30 px-3 text-xs font-semibold uppercase tracking-wide text-white hover:bg-black/40"
                onClick={onCancel}
              >
                Detener
              </Button>
            )}

            <Button
              size="sm"
              disabled={!canSubmit}
              loading={loading}
              onClick={onSubmit}
              className="h-9 w-9 rounded-full bg-saptiva-mint p-0 text-saptiva-dark hover:bg-saptiva-mint/90"
              aria-label="Enviar mensaje"
            >
              {!loading && (
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M5 12h14" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M12 5l7 7-7 7" />
                </svg>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Tool chips row with proper wrapping */}
      {(toolsEnabled || hasActiveTools) && onToggleTool && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {toolsEnabled &&
              Object.entries(toolsEnabled).map(([toolName, enabled]) => (
                <button
                  key={toolName}
                  type="button"
                  onClick={() => onToggleTool(toolName)}
                  disabled={disabled || loading}
                  className={cn(
                    'flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-wide transition',
                    enabled
                      ? 'border-saptiva-mint/70 bg-saptiva-mint/20 text-saptiva-mint'
                      : 'border-white/10 bg-white/5 text-saptiva-light/70 hover:border-white/20 hover:bg-white/10',
                    (disabled || loading) && 'opacity-70',
                  )}
                  aria-pressed={enabled}
                >
                  <span className="inline-flex h-2.5 w-2.5 rounded-full" style={{ backgroundColor: enabled ? '#8AF5D4' : '#5B9BD5' }} />
                  {toolName.replace(/_/g, ' ')}
                </button>
              ))}
          </div>

          <div className="flex items-center gap-2 text-xs text-saptiva-light/60">
            <span className="hidden sm:inline">Enter para enviar</span>
            <span className="hidden sm:inline">•</span>
            <span>Shift + Enter para salto de línea</span>
          </div>
        </div>
      )}
    </div>
  )
}
