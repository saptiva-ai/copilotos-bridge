'use client'

import * as React from 'react'
import { cn } from '../../../lib/utils'
import type { ToolId } from '@/types/tools'
import { TOOL_REGISTRY } from '@/types/tools'
import ToolMenu from '../ToolMenu/ToolMenu'
import { ChatComposerAttachment } from './ChatComposer'

interface ChatComposerV2Props {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void | Promise<void>
  onCancel?: () => void
  disabled?: boolean
  loading?: boolean
  layout?: 'center' | 'bottom'
  onActivate?: () => void
  placeholder?: string
  maxLength?: number
  showCancel?: boolean
  className?: string
  selectedTools?: ToolId[]
  onRemoveTool?: (id: ToolId) => void
  onAddTool?: (id: ToolId) => void
  attachments?: ChatComposerAttachment[]
  onAttachmentsChange?: (attachments: ChatComposerAttachment[]) => void
}

const MIN_ROWS = 1
const MAX_ROWS = 8

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 6v12" />
      <path d="M18 12H6" />
    </svg>
  )
}

function SendIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14" />
      <path d="M12 5l7 7-7 7" />
    </svg>
  )
}

function StopIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <rect x={7} y={7} width={10} height={10} rx={2} />
    </svg>
  )
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 18L18 6" />
      <path d="M6 6l12 12" />
    </svg>
  )
}

export function ChatComposerV2({
  value,
  onChange,
  onSubmit,
  onCancel,
  disabled = false,
  loading = false,
  layout = 'bottom',
  onActivate,
  placeholder = 'Escribe tu mensaje…',
  maxLength = 10000,
  showCancel = false,
  className,
  selectedTools = [],
  onRemoveTool,
  onAddTool,
  attachments = [],
  onAttachmentsChange,
}: ChatComposerV2Props) {
  const [rows, setRows] = React.useState(MIN_ROWS)
  const [showToolsMenu, setShowToolsMenu] = React.useState(false)
  const taRef = React.useRef<HTMLTextAreaElement>(null)
  const composerRef = React.useRef<HTMLDivElement>(null)

  // Auto-resize textarea
  React.useLayoutEffect(() => {
    const ta = taRef.current
    if (!ta) return

    ta.rows = MIN_ROWS
    const lineHeight = parseInt(getComputedStyle(ta).lineHeight || '24', 10)
    const nextRows = Math.min(MAX_ROWS, Math.ceil(ta.scrollHeight / lineHeight))
    setRows(nextRows)

    // Update CSS variable for CLS prevention
    if (composerRef.current) {
      const height = composerRef.current.offsetHeight
      document.documentElement.style.setProperty('--composer-h', `${height}px`)
    }
  }, [value])

  // Transition to chat mode on focus or when typing
  React.useEffect(() => {
    if (layout === 'center' && value.trim() && onActivate) {
      onActivate()
    }
  }, [layout, value, onActivate])

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        if (value.trim()) {
          onSubmit()
        }
      }

      if (e.key === 'Escape') {
        if (showToolsMenu) {
          setShowToolsMenu(false)
          return
        }
        if (showCancel && onCancel) {
          onCancel()
        }
      }
    },
    [onSubmit, value, showToolsMenu, showCancel, onCancel]
  )

  const handleSendClick = React.useCallback(() => {
    if (!value.trim() || disabled || loading) return
    onSubmit()
  }, [value, disabled, loading, onSubmit])

  const canSubmit = value.trim().length > 0 && !disabled && !loading

  // Close menu on click outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!composerRef.current?.contains(event.target as Node)) {
        setShowToolsMenu(false)
      }
    }

    if (showToolsMenu) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showToolsMenu])

  const handleToolSelect = React.useCallback(
    (id: ToolId) => {
      if (onAddTool) {
        onAddTool(id)
      }
      setShowToolsMenu(false)
    },
    [onAddTool]
  )

  const isCenter = layout === 'center'

  return (
    <div
      className={cn(
        isCenter ? 'w-full' : 'sticky bottom-0 w-full',
        className
      )}
      onFocusCapture={() => isCenter && onActivate?.()}
    >
      <div
        ref={composerRef}
        className={cn(
          'relative rounded-2xl bg-neutral-900/70 backdrop-blur transition-all duration-200',
          'border border-white/10 focus-within:ring-2 focus-within:ring-white/20',
          isCenter
            ? 'w-full max-w-[640px] mx-auto'
            : 'mx-auto w-full max-w-[840px] px-4 pb-3'
        )}
      >
        {/* Tool Menu */}
        {showToolsMenu && (
          <div className="absolute bottom-full left-0 z-[9999] mb-2 pointer-events-auto">
            <ToolMenu
              onSelect={handleToolSelect}
              onClose={() => setShowToolsMenu(false)}
            />
          </div>
        )}

        <div className="flex flex-col gap-2 p-3">
          {/* Textarea */}
          <div className="flex items-end gap-2">
            {/* Tools button */}
            <button
              type="button"
              onClick={() => setShowToolsMenu(!showToolsMenu)}
              disabled={disabled || loading}
              className={cn(
                'shrink-0 h-10 w-10 rounded-xl border border-white/10 hover:bg-white/5 transition-colors',
                'grid place-items-center text-zinc-300',
                (disabled || loading) && 'cursor-not-allowed opacity-50'
              )}
              aria-label="Herramientas"
            >
              <PlusIcon className="h-5 w-5" />
            </button>

            {/* Textarea */}
            <div className="flex-1 min-w-0">
              <textarea
                ref={taRef}
                rows={rows}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={disabled || loading}
                maxLength={maxLength}
                className={cn(
                  'w-full resize-none bg-transparent focus:outline-none',
                  'text-[15px] leading-6 text-white placeholder:text-white/40',
                  'max-h-[calc(1.5rem*8)] overflow-y-auto thin-scroll',
                  'transition-[height] duration-150 ease-out'
                )}
              />
            </div>

            {/* Send/Stop button */}
            {showCancel && onCancel ? (
              <button
                type="button"
                onClick={onCancel}
                className="shrink-0 h-10 px-4 rounded-xl bg-red-500/15 hover:bg-red-500/25 border border-red-500/60 text-red-300 transition-colors"
                aria-label="Detener"
              >
                <StopIcon className="h-5 w-5" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSendClick}
                disabled={!canSubmit}
                className={cn(
                  'shrink-0 h-10 px-4 rounded-xl bg-white/10 hover:bg-white/20 border border-white/10 text-white transition-colors',
                  !canSubmit && 'cursor-not-allowed opacity-50'
                )}
                aria-label="Enviar"
              >
                <SendIcon className="h-5 w-5" />
              </button>
            )}
          </div>

          {/* Tool chips */}
          {selectedTools.length > 0 && (
            <div className="flex items-center gap-2 overflow-x-auto thin-scroll px-1">
              {selectedTools.slice(0, 4).map((id) => {
                const tool = TOOL_REGISTRY[id]
                if (!tool) return null
                const Icon = tool.Icon
                return (
                  <div
                    key={id}
                    className="group flex h-9 items-center gap-2 rounded-xl border border-[#49F7D9]/60 bg-[#49F7D9]/15 pl-2 pr-1 text-[#49F7D9] transition-colors hover:bg-[#49F7D9]/25 shrink-0"
                    title={tool.label}
                  >
                    <Icon className="h-4 w-4" />
                    <span className="text-sm font-medium">{tool.label}</span>
                    <button
                      type="button"
                      aria-label={`Remove ${tool.label}`}
                      onClick={() => onRemoveTool?.(id)}
                      className="grid place-items-center rounded-lg p-1 text-[#49F7D9] hover:bg-[#49F7D9]/20"
                    >
                      <CloseIcon className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
