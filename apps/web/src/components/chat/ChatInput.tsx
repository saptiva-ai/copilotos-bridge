'use client'

import * as React from 'react'
import { Button, Textarea } from '../ui'
import { ModelSelector } from './ModelSelector'
import { cn } from '../../lib/utils'

export interface ChatAttachment {
  id: string
  file: File
  name: string
  size: number
  type: string
  progress: number
  status: 'uploading' | 'completed' | 'error'
  errorMessage?: string
}

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
  // File attachments - UX-004
  attachments?: ChatAttachment[]
  onAttachmentsChange?: (attachments: ChatAttachment[]) => void
}

// Action items for composer menu - UX-003
interface ComposerAction {
  id: string
  name: string
  description: string
  icon: string
  category: 'files' | 'research' | 'analysis' | 'connectors'
  shortcut?: string
}

const COMPOSER_ACTIONS: ComposerAction[] = [
  {
    id: 'add_files',
    name: 'Add files',
    description: 'Adjuntar documentos, imágenes o archivos de código',
    icon: '📄',
    category: 'files'
  },
  {
    id: 'add_google_drive',
    name: 'Add from Google Drive',
    description: 'Importar archivos desde Google Drive',
    icon: '📂',
    category: 'files'
  },
  {
    id: 'deep_research',
    name: 'Deep research',
    description: 'Investigación profunda con fuentes verificadas',
    icon: '🔬',
    category: 'research'
  },
  {
    id: 'code_analysis',
    name: 'Code analysis',
    description: 'Análisis y revisión de código',
    icon: '💻',
    category: 'analysis'
  },
  {
    id: 'document_analysis',
    name: 'Document analysis',
    description: 'Análisis de documentos y extracción de datos',
    icon: '📊',
    category: 'analysis'
  },
  {
    id: 'use_connectors',
    name: 'Use connectors',
    description: 'Conectar con APIs y servicios externos',
    icon: '🔌',
    category: 'connectors'
  }
]

// File attachment configuration - UX-004
const ACCEPTED_FILE_TYPES = ['pdf', 'png', 'jpg', 'jpeg', 'docx', 'txt', 'md', 'csv', 'json', 'ipynb']
const MAX_FILE_SIZE_MB = 20
const MAX_FILE_COUNT = 5

// File validation utility
const validateFile = (file: File): { valid: boolean; error?: string } => {
  const extension = file.name.split('.').pop()?.toLowerCase()

  if (!extension || !ACCEPTED_FILE_TYPES.includes(extension)) {
    return { valid: false, error: `Tipo de archivo no permitido. Solo se aceptan: ${ACCEPTED_FILE_TYPES.join(', ')}` }
  }

  if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
    return { valid: false, error: `Archivo muy grande. Máximo ${MAX_FILE_SIZE_MB}MB` }
  }

  return { valid: true }
}

// File size formatter
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
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
  attachments = [],
  onAttachmentsChange,
}: ChatInputProps) {
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)
  const toolsButtonRef = React.useRef<HTMLButtonElement>(null)
  const fileInputRef = React.useRef<HTMLInputElement>(null)
  const [showToolsMenu, setShowToolsMenu] = React.useState(false)
  const [isDragOver, setIsDragOver] = React.useState(false)
  const [dragCounter, setDragCounter] = React.useState(0)

  // Handle keyboard shortcuts - UX-006
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter to send (regular), Shift+Enter for new line
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value.trim() && !disabled && !loading) {
        onSubmit()
      }
    }

    // Cmd/Ctrl+Enter to send (alternative)
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      if (value.trim() && !disabled && !loading) {
        onSubmit()
      }
    }

    // Escape to cancel/stop
    if (e.key === 'Escape') {
      e.preventDefault()
      if (showCancel && onCancel) {
        onCancel() // Stop streaming
      } else if (showToolsMenu) {
        setShowToolsMenu(false) // Close tools menu
      }
    }
  }

  // Auto-focus when not disabled
  React.useEffect(() => {
    if (!disabled && !loading && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [disabled, loading])

  // Handle click outside to close tools menu
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        showToolsMenu &&
        toolsButtonRef.current &&
        !toolsButtonRef.current.contains(event.target as Node)
      ) {
        setShowToolsMenu(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showToolsMenu])

  // Handle tools menu toggle
  const handleToggleToolsMenu = React.useCallback(() => {
    setShowToolsMenu(prev => !prev)
  }, [])

  // File attachment handlers - UX-004
  const handleFileSelect = React.useCallback((files: FileList | File[]) => {
    if (!onAttachmentsChange) return

    const fileArray = Array.from(files)
    const newAttachments: ChatAttachment[] = []

    for (const file of fileArray) {
      // Check file count limit
      if (attachments.length + newAttachments.length >= MAX_FILE_COUNT) {
        console.error(`Máximo ${MAX_FILE_COUNT} archivos permitidos`)
        break
      }

      const validation = validateFile(file)
      if (!validation.valid) {
        console.error(validation.error)
        continue
      }

      const attachment: ChatAttachment = {
        id: `attachment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        file,
        name: file.name,
        size: file.size,
        type: file.type || 'application/octet-stream',
        progress: 0,
        status: 'uploading'
      }

      newAttachments.push(attachment)
    }

    if (newAttachments.length > 0) {
      onAttachmentsChange([...attachments, ...newAttachments])
      // Simulate upload progress
      newAttachments.forEach(attachment => {
        let progress = 0
        const interval = setInterval(() => {
          progress += 10 + Math.random() * 20
          if (progress >= 100) {
            progress = 100
            clearInterval(interval)
            onAttachmentsChange(
              attachments.map(a =>
                a.id === attachment.id
                  ? { ...a, progress: 100, status: 'completed' as const }
                  : a
              )
            )
          } else {
            onAttachmentsChange(
              attachments.map(a =>
                a.id === attachment.id
                  ? { ...a, progress }
                  : a
              )
            )
          }
        }, 100)
      })
    }
  }, [attachments, onAttachmentsChange])

  const handleRemoveAttachment = React.useCallback((attachmentId: string) => {
    if (!onAttachmentsChange) return
    onAttachmentsChange(attachments.filter(a => a.id !== attachmentId))
  }, [attachments, onAttachmentsChange])

  // Drag and drop handlers
  const handleDragEnter = React.useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragCounter(prev => prev + 1)
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragOver(true)
    }
  }, [])

  const handleDragLeave = React.useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragCounter(prev => {
      const newCounter = prev - 1
      if (newCounter === 0) {
        setIsDragOver(false)
      }
      return newCounter
    })
  }, [])

  const handleDragOver = React.useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = React.useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
    setDragCounter(0)

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files)
    }
  }, [handleFileSelect])

  // File input handler
  const handleFileInputChange = React.useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelect(e.target.files)
      // Reset input
      e.target.value = ''
    }
  }, [handleFileSelect])

  const handleAddFilesClick = React.useCallback(() => {
    fileInputRef.current?.click()
    setShowToolsMenu(false)
  }, [])

  // Handle global keyboard shortcuts - UX-006
  React.useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // Alt+N opens actions menu - UX-003
      if (e.altKey && e.key === 'n') {
        e.preventDefault()
        setShowToolsMenu(prev => !prev)
      }

      // Cmd/Ctrl+K for command palette (future implementation)
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        // TODO: Implement command palette
        console.log('Command palette shortcut (Cmd/Ctrl+K) - not implemented yet')
      }
    }

    document.addEventListener('keydown', handleGlobalKeyDown)
    return () => document.removeEventListener('keydown', handleGlobalKeyDown)
  }, [])

  const canSubmit = value.trim().length > 0 && !disabled && !loading
  const hasActiveTools = toolsEnabled && Object.values(toolsEnabled).some(Boolean)

  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-surface p-3 shadow-card',
        'transition-colors duration-200',
        disabled && 'opacity-95',
        className,
      )}
    >
      {/* Model Picker movido al header-left según UX-001 */}
      {/* Composer minimalista: mic + input + enviar según CHT-02 */}
      <div className="flex items-end gap-3 mb-3">
        {/* Botón de micrófono - UX-006 accessibility */}
        <button
          type="button"
          disabled={disabled || loading}
          className={cn(
            'flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-white/5 text-white/70 transition-all hover:bg-white/10 hover:text-white',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
            (disabled || loading) && 'opacity-50 cursor-not-allowed'
          )}
          aria-label="Activar micrófono (no implementado)"
          tabIndex={0}
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
        </button>

        {/* Botón + para tools con menu hacia arriba - CHT-03 */}
        <div className="relative">
          <button
            ref={toolsButtonRef}
            type="button"
            onClick={handleToggleToolsMenu}
            disabled={disabled || loading}
            className={cn(
              'flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-white/5 text-white/70 transition-all hover:bg-white/10 hover:text-white',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
              hasActiveTools && 'border-primary/70 bg-primary/20 text-primary',
              showToolsMenu && 'border-primary bg-primary/10 text-primary',
              (disabled || loading) && 'opacity-50 cursor-not-allowed'
            )}
            aria-label="Herramientas"
            aria-expanded={showToolsMenu}
          >
            <svg
              className={cn("h-5 w-5 transition-transform", showToolsMenu && "rotate-45")}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </button>

          {/* Popover de acciones - UX-003 */}
          {showToolsMenu && (
            <div className="absolute bottom-full left-0 mb-2 w-72 overflow-hidden rounded-lg border border-border bg-surface shadow-card">
              <div className="border-b border-border p-3">
                <h3 className="text-sm font-bold text-text">Actions</h3>
                <p className="text-xs text-text-muted">Agregar contenido y herramientas a tu mensaje</p>
              </div>

              <div className="max-h-64 overflow-y-auto p-2">
                <div className="space-y-1">
                  {COMPOSER_ACTIONS.map((action) => (
                    <button
                      key={action.id}
                      type="button"
                      onClick={() => {
                        // Handle specific actions - UX-004
                        if (action.id === 'add_files') {
                          handleAddFilesClick()
                        } else {
                          // TODO: Implementar lógica específica para cada acción
                          console.log('Action selected:', action.id)
                          setShowToolsMenu(false) // close-on-select
                        }
                      }}
                      className={cn(
                        'flex w-full items-start gap-3 rounded-lg p-3 text-left transition-all',
                        'hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:ring-offset-1 focus-visible:ring-offset-surface'
                      )}
                      tabIndex={0}
                    >
                      <span className="text-lg">{action.icon}</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-text">{action.name}</div>
                        <p className="text-xs text-text-muted line-clamp-2">
                          {action.description}
                        </p>
                      </div>
                      <svg className="h-4 w-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  ))}
                </div>

                {/* More actions */}
                <div className="border-t border-border mt-2 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      console.log('More actions')
                      setShowToolsMenu(false)
                    }}
                    className="flex w-full items-center gap-3 rounded-lg p-3 text-left transition-all hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:ring-offset-1 focus-visible:ring-offset-surface"
                    tabIndex={0}
                  >
                    <span className="text-lg">⋯</span>
                    <span className="font-medium text-text">More…</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input expandible con drag & drop - UX-004 */}
        <div
          className={cn(
            "relative flex-1",
            isDragOver && "ring-2 ring-primary/50 ring-offset-2 ring-offset-surface rounded-lg"
          )}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isDragOver ? "Suelta los archivos aquí..." : placeholder}
            disabled={disabled || loading}
            autoResize
            rows={1}
            maxLength={maxLength}
            className="min-h-[48px] max-h-32 resize-none border-0 bg-transparent text-white placeholder:text-text-muted focus:border-0 focus:ring-0 focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-surface pr-12"
          />

          {maxLength && (
            <div className="pointer-events-none absolute bottom-2 right-14 text-xs text-saptiva-light/60">
              {value.length}/{maxLength}
            </div>
          )}

          {/* Botón enviar en esquina del input */}
          <div className="absolute bottom-2 right-2">
            {showCancel && onCancel ? (
              <Button
                size="sm"
                variant="ghost"
                className="h-8 w-8 rounded-full border border-danger/50 bg-danger/20 p-0 text-danger hover:bg-danger/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger/60 focus-visible:ring-offset-1 focus-visible:ring-offset-surface"
                onClick={onCancel}
                aria-label="Detener"
              >
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="6" y="6" width="12" height="12" rx="2" />
                </svg>
              </Button>
            ) : (

              <Button
                size="sm"
                disabled={!canSubmit}
                loading={loading}
                onClick={onSubmit}
                className="h-8 w-8 rounded-full bg-primary p-0 text-bg hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-1 focus-visible:ring-offset-surface"
                aria-label="Enviar mensaje"
              >
                {!loading && (
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 12h14" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 5l7 7-7 7" />
                  </svg>
                )}
              </Button>
            )}
          </div>
          {/* Drag overlay */}
          {isDragOver && (
            <div className="absolute inset-0 bg-primary/10 border-2 border-dashed border-primary/50 rounded-lg flex items-center justify-center backdrop-blur-sm">
              <div className="text-center">
                <svg className="h-8 w-8 text-primary mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p className="text-sm font-medium text-primary">Suelta los archivos aquí</p>
                <p className="text-xs text-text-muted mt-1">
                  Máximo {MAX_FILE_COUNT} archivos, {MAX_FILE_SIZE_MB}MB cada uno
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={ACCEPTED_FILE_TYPES.map(type => `.${type}`).join(',')}
        onChange={handleFileInputChange}
        className="hidden"
      />

      {/* Attachment chips - UX-004 */}
      {attachments.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {attachments.map((attachment) => (
            <div
              key={attachment.id}
              className={cn(
                "flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs transition-all",
                attachment.status === 'completed' ? "border-primary/50 bg-primary/10 text-primary" :
                attachment.status === 'error' ? "border-danger/50 bg-danger/10 text-danger" :
                "border-border bg-surface-2 text-text"
              )}
            >
              {/* File type icon */}
              <span className="text-sm">
                {attachment.name.endsWith('.pdf') ? '📄' :
                 attachment.name.match(/\.(png|jpg|jpeg)$/i) ? '🖼️' :
                 attachment.name.endsWith('.docx') ? '📝' :
                 attachment.name.match(/\.(txt|md)$/i) ? '📝' :
                 attachment.name.match(/\.(csv|json)$/i) ? '📊' :
                 attachment.name.endsWith('.ipynb') ? '📓' : '📎'}
              </span>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1">
                  <span className="truncate font-medium">{attachment.name}</span>
                  <span className="text-text-muted">({formatFileSize(attachment.size)})</span>
                </div>

                {/* Progress bar */}
                {attachment.status === 'uploading' && (
                  <div className="mt-1 h-1 w-full bg-surface-2 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300 ease-out"
                      style={{ width: `${attachment.progress}%` }}
                    />
                  </div>
                )}

                {attachment.status === 'error' && attachment.errorMessage && (
                  <div className="text-xs text-danger mt-1">{attachment.errorMessage}</div>
                )}
              </div>

              {/* Remove button */}
              <button
                type="button"
                onClick={() => handleRemoveAttachment(attachment.id)}
                disabled={disabled || loading}
                className="ml-1 h-4 w-4 rounded-full hover:bg-surface-2 flex items-center justify-center transition-colors"
                aria-label="Eliminar archivo"
              >
                <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Chips de tools activas sobre el input - CHT-02 */}
      {hasActiveTools && onToggleTool && (
        <div className="mb-2 flex flex-wrap items-center gap-2">
          {toolsEnabled &&
            Object.entries(toolsEnabled)
              .filter(([, enabled]) => enabled)
              .map(([toolName]) => (
                <button
                  key={toolName}
                  type="button"
                  onClick={() => onToggleTool(toolName)}
                  disabled={disabled || loading}
                  className={cn(
                    'flex items-center gap-1.5 rounded-full border border-primary/50 bg-primary/10 px-3 py-1 text-xs font-medium text-primary transition hover:bg-primary/20',
                    (disabled || loading) && 'opacity-50',
                  )}
                  aria-pressed="true"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-current" />
                  {toolName.replace(/_/g, ' ')}
                  <svg className="ml-1 h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              ))}
        </div>
      )}

      {/* Atajos de teclado - UX-006 */}
      <div className="mt-2 text-center">
        <p className="text-xs text-text-muted">
          <span>Enter envía</span>
          <span className="mx-2">•</span>
          <span>⌘/Ctrl+Enter envía</span>
          <span className="mx-2">•</span>
          <span>Shift+Enter nueva línea</span>
          <span className="mx-2">•</span>
          <span>Esc cancela</span>
          <span className="mx-2">•</span>
          <span>Alt+N herramientas</span>
        </p>
      </div>
    </div>
  )
}
