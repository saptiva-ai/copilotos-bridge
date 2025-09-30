'use client'

import * as React from 'react'
import { Button } from '../ui'
import { cn } from '../../lib/utils'
import { BADGE_STYLES, type UiModel, type ModelBadge } from '../../config/modelCatalog'
import { featureFlags } from '../../lib/feature-flags'

export type ChatModel = {
  id: string
  value: string
  label: string
  description: string
  tags: string[]
  available?: boolean
  backendId?: string | null
}

interface ModelSelectorProps {
  models: ChatModel[]
  selectedModel: string
  onModelChange: (modelId: string) => void
  className?: string
  disabled?: boolean
}

export function ModelSelector({ models, selectedModel, onModelChange, className, disabled = false }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const [activeModel, setActiveModel] = React.useState(selectedModel)
  const dropdownRef = React.useRef<HTMLDivElement>(null)
  const buttonRef = React.useRef<HTMLButtonElement>(null)
  const popoverId = React.useId()
  const buttonId = React.useId()

  const currentModel = React.useMemo(() => {
    return models.find((model) => model.id === activeModel) ?? models[0]
  }, [activeModel, models])

  React.useEffect(() => {
    setActiveModel(selectedModel)
  }, [selectedModel])

  const handleToggle = React.useCallback(() => {
    setIsOpen((prev) => !prev)
  }, [])

  const handleSelect = React.useCallback(
    (model: ChatModel) => {
      if (!model.available) return // Don't select unavailable models
      setActiveModel(model.id)
      onModelChange(model.id)
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
        <span className="text-text-muted">modelo</span>
        <span className="text-text">/</span>
        <span className="font-semibold text-text">{currentModel?.label}</span>
      </Button>

      {isOpen && (
        <div
          id={popoverId}
          role="listbox"
          aria-labelledby={buttonId}
          className="absolute left-0 top-full z-50 mt-2 w-[22rem] overflow-hidden rounded-xl border border-border bg-surface shadow-card"
        >
          {featureFlags.useProdStyleModels ? (
            // Production-style card layout with badges
            <div className="max-h-[60vh] overflow-y-auto p-2">
              <div className="px-2 pb-2">
                <h3 className="text-sm font-semibold text-text">Modelos de chat</h3>
                <p className="text-xs text-text-muted">Selecciona un modelo orientado a conversación.</p>
              </div>
              <div className="space-y-2">
                {models.map((model) => {
                  const isActive = model.id === currentModel?.id
                  const isAvailable = model.available !== false
                  return (
                    <button
                      key={model.id}
                      type="button"
                      onClick={() => handleSelect(model)}
                      disabled={!isAvailable}
                      className={cn(
                        'group relative flex w-full items-start gap-3 rounded-lg border px-3 py-3 text-left transition-all',
                        isAvailable
                          ? [
                              'border-transparent bg-surface-2/40',
                              'hover:border-border hover:bg-surface-2 hover:shadow-sm',
                              isActive && 'border-primary/60 bg-primary/10 shadow-sm',
                            ]
                          : 'cursor-not-allowed border-transparent bg-surface-2/20 opacity-50',
                      )}
                    >
                      <span
                        className={cn(
                          'flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg border transition-colors',
                          isAvailable
                            ? [
                                'border-border bg-surface-2 text-text',
                                isActive && 'border-primary/40 bg-primary/20',
                              ]
                            : 'border-border/50 bg-surface text-text-muted',
                        )}
                      >
                        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <circle cx="12" cy="12" r="5" strokeWidth="1.6" />
                          <path d="M12 7v10" strokeWidth="1.6" strokeLinecap="round" />
                        </svg>
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <p className={cn('font-semibold', isAvailable ? 'text-text' : 'text-text-muted')}>
                            {model.label}
                          </p>
                          {isActive && isAvailable && (
                            <span className="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary" />
                          )}
                          {!isAvailable && (
                            <span className="text-[10px] font-medium uppercase tracking-wider text-text-muted">
                              No disponible
                            </span>
                          )}
                        </div>
                        {model.description && (
                          <p
                            className={cn(
                              'mt-1 text-xs leading-relaxed',
                              isAvailable ? 'text-text-muted' : 'text-text-muted/70',
                            )}
                          >
                            {model.description}
                          </p>
                        )}
                        {model.tags && model.tags.length > 0 && (
                          <div className="mt-2 flex flex-wrap items-center gap-1.5">
                            {model.tags.map((tag) => {
                              const badgeStyle = BADGE_STYLES[tag as ModelBadge]
                              return (
                                <span
                                  key={`${model.id}-${tag}`}
                                  className={cn(
                                    'rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.08em]',
                                    badgeStyle
                                      ? `${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`
                                      : 'border-border bg-surface-2/50 text-text-muted',
                                  )}
                                >
                                  {tag}
                                </span>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          ) : (
            // Legacy simple list view (fallback)
            <div className="max-h-[60vh] overflow-y-auto p-1">
              {models.map((model) => {
                const isActive = model.id === currentModel?.id
                const isAvailable = model.available !== false
                return (
                  <button
                    key={model.id}
                    type="button"
                    onClick={() => handleSelect(model)}
                    disabled={!isAvailable}
                    className={cn(
                      'flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors',
                      isAvailable
                        ? [
                            'hover:bg-surface-2',
                            isActive && 'bg-primary/10 text-primary font-medium',
                            !isActive && 'text-text',
                          ]
                        : 'cursor-not-allowed text-text-muted/50',
                    )}
                  >
                    <span>{model.label}</span>
                    {!isAvailable && <span className="text-xs">(No disponible)</span>}
                  </button>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
