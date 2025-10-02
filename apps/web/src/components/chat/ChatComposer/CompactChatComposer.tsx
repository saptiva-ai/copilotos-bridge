'use client'

import * as React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../../lib/utils'
import type { ToolId } from '@/types/tools'
import { TOOL_REGISTRY } from '@/types/tools'
import ToolMenu from '../ToolMenu/ToolMenu'
import { ChatComposerAttachment } from './ChatComposer'

interface CompactChatComposerProps {
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

// Icons
function PlusIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 6v12" />
      <path d="M18 12H6" />
    </svg>
  )
}

function SendIconArrowUp({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 19V5" />
      <path d="m5 12 7-7 7 7" />
    </svg>
  )
}

function StopIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <rect x={7} y={7} width={10} height={10} rx={2} />
    </svg>
  )
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 18L18 6" />
      <path d="M6 6l12 12" />
    </svg>
  )
}

// Min height: ~44px (min-h-11), Max height: ~192px (max-h-48)
const MIN_HEIGHT = 44
const MAX_HEIGHT = 192

// Feature flag: Show tools button (set to true when tools are functional)
const SHOW_TOOLS_BUTTON = false

export function CompactChatComposer({
  value,
  onChange,
  onSubmit,
  onCancel,
  disabled = false,
  loading = false,
  layout = 'bottom',
  onActivate,
  placeholder = 'Pregúntame algo...',
  maxLength = 10000,
  showCancel = false,
  className,
  selectedTools = [],
  onRemoveTool,
  onAddTool,
  attachments = [],
  onAttachmentsChange,
}: CompactChatComposerProps) {
  const [showToolsMenu, setShowToolsMenu] = React.useState(false)
  const [textareaHeight, setTextareaHeight] = React.useState(MIN_HEIGHT)
  const [isSubmitting, setIsSubmitting] = React.useState(false)

  const taRef = React.useRef<HTMLTextAreaElement>(null)
  const composerRef = React.useRef<HTMLDivElement>(null)

  // Auto-resize textarea (grows downward only)
  const handleAutoResize = React.useCallback(() => {
    const ta = taRef.current
    if (!ta) return

    // Reset height to recalculate
    ta.style.height = 'auto'
    const scrollHeight = ta.scrollHeight

    // Calculate new height (clamped between MIN and MAX)
    const newHeight = Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, scrollHeight))
    setTextareaHeight(newHeight)
    ta.style.height = `${newHeight}px`
  }, [])

  // Auto-resize on value change
  React.useEffect(() => {
    handleAutoResize()
  }, [value, handleAutoResize])

  // Transition to chat mode on focus or when typing
  React.useEffect(() => {
    if (layout === 'center' && value.trim() && onActivate) {
      onActivate()
    }
  }, [layout, value, onActivate])

  // Submit with animation (must be defined before handleKeyDown)
  const handleSendClick = React.useCallback(async () => {
    if (!value.trim() || disabled || loading || isSubmitting) return

    setIsSubmitting(true)

    // Brief animation before submit (120ms)
    await new Promise((resolve) => setTimeout(resolve, 120))

    await onSubmit()

    // Reset state after submit
    setIsSubmitting(false)
    setTextareaHeight(MIN_HEIGHT)

    // Re-focus textarea after brief delay
    setTimeout(() => {
      taRef.current?.focus()
    }, 80)
  }, [value, disabled, loading, isSubmitting, onSubmit])

  // Handle Enter key (submit) and Shift+Enter (newline)
  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        if (value.trim() && !disabled && !loading && !isSubmitting) {
          handleSendClick()
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
    [value, disabled, loading, isSubmitting, showToolsMenu, showCancel, onCancel, handleSendClick]
  )

  const canSubmit = value.trim().length > 0 && !disabled && !loading && !isSubmitting

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
      className={cn(isCenter ? 'w-full' : 'sticky bottom-0 w-full', className)}
      onFocusCapture={() => isCenter && onActivate?.()}
    >
      {/* Outer wrapper: horizontal centering + responsive padding */}
      <div
        className={cn(
          'mx-auto w-full',
          isCenter ? 'max-w-[640px]' : 'max-w-3xl px-4 pb-4'
        )}
      >
        <div ref={composerRef} className="relative">
          {/* Tool Menu */}
          <AnimatePresence>
            {showToolsMenu && (
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 4, scale: 0.98 }}
                transition={{ duration: 0.14, ease: [0.16, 1, 0.3, 1] }}
                className="absolute bottom-full left-0 z-[9999] mb-2 pointer-events-auto"
              >
                <ToolMenu
                  onSelect={handleToolSelect}
                  onClose={() => setShowToolsMenu(false)}
                />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Main Composer Container - Minimalist ChatGPT style */}
          <motion.div
            role="form"
            aria-label="Compositor de mensajes"
            className={cn(
              'grid items-end gap-2',
              'rounded-2xl p-2',
              'bg-[var(--surface)]',
              'shadow-sm',
              // Dynamic grid: smaller space when tools hidden, full 44px when shown
              SHOW_TOOLS_BUTTON ? 'grid-cols-[44px,1fr,44px]' : 'grid-cols-[8px,1fr,44px]'
            )}
            style={{
              boxShadow: 'inset 0 0 0 0.5px var(--hairline)',
            }}
            animate={{
              height: isSubmitting ? MIN_HEIGHT + 16 : 'auto', // +16 for padding
            }}
            transition={{ duration: 0.12, ease: 'easeOut' }}
          >
            {/* Plus Button (Tools) - Minimal space when hidden (8px), full when shown (44px) */}
            <div
              className={cn(
                'shrink-0',
                SHOW_TOOLS_BUTTON ? 'w-11' : 'w-2', // 44px when shown, 8px when hidden
                !SHOW_TOOLS_BUTTON && 'pointer-events-none'
              )}
            >
              {SHOW_TOOLS_BUTTON && (
                <button
                  type="button"
                  onClick={() => setShowToolsMenu(!showToolsMenu)}
                  disabled={disabled || loading}
                  className={cn(
                    'h-11 w-11 rounded-xl',
                    'grid place-items-center',
                    'text-neutral-300 bg-transparent',
                    'hover:bg-[var(--surface-strong)] active:bg-[var(--surface-strong)]',
                    'transition-colors duration-150',
                    'outline-none ring-0 focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0',
                    (disabled || loading) && 'cursor-not-allowed opacity-40'
                  )}
                  aria-label="Abrir herramientas"
                  aria-expanded={showToolsMenu}
                  aria-haspopup="menu"
                >
                  <PlusIcon className="h-5 w-5 opacity-80" />
                </button>
              )}
            </div>

            {/* Auto-grow Textarea - No borders, no focus color change */}
            <div className="min-w-0 flex-1">
              <motion.textarea
                ref={taRef}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={disabled || loading}
                maxLength={maxLength}
                rows={1}
                className={cn(
                  'w-full resize-none bg-transparent',
                  'text-[15px] leading-6 text-neutral-100 placeholder:text-neutral-400',
                  'outline-none ring-0 border-0',
                  'focus:outline-none focus:ring-0 focus:border-0 focus:border-transparent',
                  'focus-visible:outline-none focus-visible:ring-0',
                  'overflow-y-auto thin-scroll',
                  'transition-[height] duration-150 ease-out'
                )}
                style={{
                  minHeight: `${MIN_HEIGHT}px`,
                  maxHeight: `${MAX_HEIGHT}px`,
                  height: `${textareaHeight}px`,
                }}
                aria-label="Escribe tu mensaje"
                aria-multiline="true"
                animate={{
                  opacity: isSubmitting ? 0.6 : 1,
                }}
                transition={{ duration: 0.12 }}
              />
            </div>

            {/* Send Button (Arrow Up) or Stop Button - No visible rings */}
            {showCancel && onCancel ? (
              <button
                type="button"
                onClick={onCancel}
                className={cn(
                  'h-11 w-11 shrink-0 rounded-xl',
                  'grid place-items-center',
                  'bg-red-500/20 text-red-300',
                  'hover:bg-red-500/30 active:bg-red-500/40',
                  'transition-colors duration-150',
                  'outline-none ring-0 focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0'
                )}
                aria-label="Detener generación"
              >
                <StopIcon className="h-5 w-5" />
              </button>
            ) : (
              <motion.button
                type="submit"
                onClick={handleSendClick}
                disabled={!canSubmit}
                className={cn(
                  'h-11 w-11 shrink-0 rounded-xl',
                  'grid place-items-center',
                  'transition-all duration-150',
                  'outline-none ring-0 focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0',
                  canSubmit
                    ? 'bg-primary text-neutral-900 hover:bg-primary/90 active:scale-95'
                    : 'bg-neutral-700/40 text-neutral-500 cursor-not-allowed'
                )}
                aria-label="Enviar mensaje"
                whileTap={canSubmit ? { scale: 0.92 } : {}}
                transition={{ duration: 0.1 }}
              >
                <SendIconArrowUp className="h-5 w-5" />
              </motion.button>
            )}
          </motion.div>

          {/* Tool Chips (below main bar) */}
          <AnimatePresence>
            {selectedTools.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.16, ease: 'easeOut' }}
                className="mt-2 overflow-hidden"
              >
                <div className="flex items-center gap-2 overflow-x-auto thin-scroll px-1">
                  {selectedTools.slice(0, 4).map((id) => {
                    const tool = TOOL_REGISTRY[id]
                    if (!tool) return null
                    const Icon = tool.Icon
                    return (
                      <motion.div
                        key={id}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        transition={{ duration: 0.12 }}
                        className={cn(
                          'group flex h-9 items-center gap-2 shrink-0',
                          'rounded-xl border border-primary/60 bg-primary/15 pl-2 pr-1',
                          'text-primary',
                          'transition-colors hover:bg-primary/25'
                        )}
                        title={tool.label}
                      >
                        <Icon className="h-4 w-4" />
                        <span className="text-sm font-medium">{tool.label}</span>
                        <button
                          type="button"
                          aria-label={`Quitar ${tool.label}`}
                          onClick={() => onRemoveTool?.(id)}
                          className={cn(
                            'grid place-items-center rounded-lg p-1',
                            'text-primary hover:bg-primary/20',
                            'transition-colors'
                          )}
                        >
                          <CloseIcon className="h-3.5 w-3.5" />
                        </button>
                      </motion.div>
                    )
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
