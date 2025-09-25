'use client'

import * as React from 'react'
import { Button } from '../ui'
import { cn } from '../../lib/utils'

type ChatModel = {
  id: string
  value: string
  label: string
  description: string
  tags: string[]
}

const CHAT_MODELS: ChatModel[] = [
  {
    id: 'saptiva-turbo',
    value: 'SAPTIVA_TURBO',
    label: 'Saptiva Turbo',
    description: 'Chats simples, asistentes de alta concurrencia (rápido y barato).',
    tags: ['Core', 'Chat'],
  },
  {
    id: 'saptiva-cortex',
    value: 'SAPTIVA_CORTEX',
    label: 'Saptiva Cortex',
    description: 'Razonamiento y comprensión profunda; ideal para agentes con lógica.',
    tags: ['Core', 'Reasoning', 'Chat'],
  },
  {
    id: 'saptiva-ops',
    value: 'SAPTIVA_OPS',
    label: 'Saptiva Ops',
    description: 'Casos complejos con tools/SDK; agentes autónomos, RAG, websearch.',
    tags: ['Pro', 'Tools', 'Chat'],
  },
  {
    id: 'saptiva-legacy',
    value: 'SAPTIVA_LEGACY',
    label: 'Saptiva Legacy',
    description: 'Compatibilidad con SDKs/flows heredados y pruebas.',
    tags: ['Legacy', 'Chat'],
  },
  {
    id: 'saptiva-coder',
    value: 'SAPTIVA_CODER',
    label: 'Saptiva Coder',
    description: 'Asistente de programación/codegen en contexto conversacional.',
    tags: ['Coding', 'Chat'],
  },
  {
    id: 'saptiva-multimodal',
    value: 'SAPTIVA_MULTIMODAL',
    label: 'Saptiva Multimodal',
    description: 'Chat con comprensión de texto + imágenes (p. ej., documentos).',
    tags: ['Multimodal', 'Chat'],
  },
]

interface ModelSelectorProps {
  selectedModel: string
  onModelChange: (modelId: string) => void
  className?: string
  disabled?: boolean
}

export function ModelSelector({ selectedModel, onModelChange, className, disabled = false }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const dropdownRef = React.useRef<HTMLDivElement>(null)
  const buttonRef = React.useRef<HTMLButtonElement>(null)
  const popoverId = React.useId()
  const buttonId = React.useId()

  const currentModel = React.useMemo(() => {
    return CHAT_MODELS.find((model) => model.value === selectedModel) ?? CHAT_MODELS[0]
  }, [selectedModel])

  const handleToggle = React.useCallback(() => {
    setIsOpen((prev) => !prev)
  }, [])

  const handleSelect = React.useCallback(
    (value: string) => {
      onModelChange(value)
      setIsOpen(false)
    },
    [onModelChange],
  )

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!dropdownRef.current?.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  return (
    <div ref={dropdownRef} className={cn('relative inline-block', className)}>
      <Button
        ref={buttonRef}
        type="button"
        variant="ghost"
        disabled={disabled}
        id={buttonId}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={isOpen ? popoverId : undefined}
        onClick={handleToggle}
        className={cn(
          'flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 text-sm font-medium text-text transition-all',
          'hover:border-primary/60 hover:bg-surface-2',
          isOpen && 'border-primary/60 bg-surface-2',
          disabled && 'cursor-not-allowed opacity-60',
        )}
      >
        <span className="text-text-muted">Saptiva</span>
        <span className="text-text">/</span>
        <span className="font-semibold text-text">{currentModel.label}</span>
      </Button>

      {isOpen && (
        <div
          id={popoverId}
          role="listbox"
          aria-labelledby={buttonId}
          className="absolute left-0 top-full z-50 mt-2 w-[22rem] overflow-hidden rounded-xl border border-border bg-surface shadow-card"
        >
          <div className="max-h-[60vh] overflow-y-auto p-2">
            <div className="px-2 pb-2">
              <h3 className="text-sm font-semibold text-text">Modelos de chat</h3>
              <p className="text-xs text-text-muted">Selecciona un modelo orientado a conversación.</p>
            </div>
            <div className="space-y-1">
              {CHAT_MODELS.map((model) => {
                const isActive = model.value === currentModel.value
                return (
                  <button
                    key={model.id}
                    type="button"
                    onClick={() => handleSelect(model.value)}
                    className={cn(
                      'flex w-full items-start gap-3 rounded-lg border border-transparent bg-surface-2/40 px-3 py-3 text-left transition-colors',
                      'hover:border-border hover:bg-surface-2',
                      isActive && 'border-primary/60 bg-primary/10 text-text',
                    )}
                  >
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-surface-2 text-text">
                      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <circle cx="12" cy="12" r="5" strokeWidth="1.6" />
                        <path d="M12 7v10" strokeWidth="1.6" strokeLinecap="round" />
                      </svg>
                    </span>
                    <div className="flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-semibold text-text">{model.label}</p>
                        {isActive && <span className="h-1.5 w-1.5 rounded-full bg-primary" />}
                      </div>
                      <p className="mt-1 text-xs text-text-muted leading-relaxed">{model.description}</p>
                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        {model.tags.map((tag) => (
                          <span
                            key={`${model.id}-${tag}`}
                            className="rounded-full border border-border px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.08em] text-text-muted"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
