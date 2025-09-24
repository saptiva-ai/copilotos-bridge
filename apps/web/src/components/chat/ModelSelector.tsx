'use client'

import * as React from 'react'
import { Button } from '../ui'
import { cn } from '../../lib/utils'

// Enhanced model structure for hierarchical organization
interface ModelVariant {
  id: string
  name: string
  contextWindow: string
  isAvailable: boolean
  pricing: 'free' | 'pro' | 'enterprise'
}

interface ModelFamily {
  id: string
  name: string
  variants: ModelVariant[]
}

interface ModelProvider {
  id: string
  name: string
  families: ModelFamily[]
}

// Quick presets for common use cases
interface QuickPreset {
  id: string
  name: string
  modelId: string
  description: string
}

const QUICK_PRESETS: QuickPreset[] = [
  {
    id: 'fast',
    name: 'Rápido',
    modelId: 'SAPTIVA_TURBO',
    description: 'Respuestas rápidas, ideal para consultas simples'
  },
  {
    id: 'precise',
    name: 'Preciso',
    modelId: 'SAPTIVA_CORTEX',
    description: 'Análisis detallado y respuestas precisas'
  },
  {
    id: 'creative',
    name: 'Creativo',
    modelId: 'SAPTIVA_MULTIMODAL',
    description: 'Generación creativa y multimodal'
  }
]

const MODEL_PROVIDERS: ModelProvider[] = [
  {
    id: 'saptiva',
    name: 'SAPTIVA',
    families: [
      {
        id: 'core',
        name: 'Core',
        variants: [
          { id: 'SAPTIVA_TURBO', name: 'Turbo', contextWindow: '4K', isAvailable: true, pricing: 'free' },
          { id: 'SAPTIVA_CORTEX', name: 'Cortex', contextWindow: '16K', isAvailable: true, pricing: 'pro' },
          { id: 'SAPTIVA_OPS', name: 'Ops', contextWindow: '8K', isAvailable: true, pricing: 'pro' }
        ]
      },
      {
        id: 'specialized',
        name: 'Especializados',
        variants: [
          { id: 'SAPTIVA_CODER', name: 'Coder', contextWindow: '32K', isAvailable: true, pricing: 'pro' },
          { id: 'SAPTIVA_MULTIMODAL', name: 'Multimodal', contextWindow: '16K', isAvailable: true, pricing: 'enterprise' }
        ]
      }
    ]
  }
]

interface ModelSelectorProps {
  selectedModel: string
  onModelChange: (modelId: string) => void
  className?: string
  disabled?: boolean
}

export function ModelSelector({
  selectedModel,
  onModelChange,
  className,
  disabled = false,
}: ModelSelectorProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const [searchQuery, setSearchQuery] = React.useState('')
  const [view, setView] = React.useState<'presets' | 'hierarchy'>('presets')
  const dropdownRef = React.useRef<HTMLDivElement>(null)
  const buttonRef = React.useRef<HTMLButtonElement>(null)
  const searchRef = React.useRef<HTMLInputElement>(null)

  // Find selected model info across all providers
  const selectedModelInfo = React.useMemo(() => {
    for (const provider of MODEL_PROVIDERS) {
      for (const family of provider.families) {
        const variant = family.variants.find(v => v.id === selectedModel)
        if (variant) {
          return { provider: provider.name, variant, family: family.name }
        }
      }
    }
    return {
      provider: 'SAPTIVA',
      variant: MODEL_PROVIDERS[0].families[0].variants[0],
      family: 'Core'
    }
  }, [selectedModel])

  // Filter models based on search query
  const filteredProviders = React.useMemo(() => {
    if (!searchQuery.trim()) return MODEL_PROVIDERS

    return MODEL_PROVIDERS.map(provider => ({
      ...provider,
      families: provider.families.map(family => ({
        ...family,
        variants: family.variants.filter(variant =>
          variant.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          family.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          provider.name.toLowerCase().includes(searchQuery.toLowerCase())
        )
      })).filter(family => family.variants.length > 0)
    })).filter(provider => provider.families.length > 0)
  }, [searchQuery])

  const handleModelSelect = (modelId: string) => {
    onModelChange(modelId)
    setIsOpen(false)
    setSearchQuery('')
    setView('presets')
  }

  const handleToggleOpen = React.useCallback(() => {
    setIsOpen(prev => !prev)
    setSearchQuery('')
    setView('presets')
  }, [])

  // Handle keyboard shortcuts
  const handleKeyDown = React.useCallback((e: KeyboardEvent) => {
    // Cmd/Ctrl+K opens and focuses search when popover is open
    if ((e.metaKey || e.ctrlKey) && e.key === 'k' && isOpen) {
      e.preventDefault()
      searchRef.current?.focus()
    }
  }, [isOpen])

  React.useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  // Auto-focus search when switching to hierarchy view
  React.useEffect(() => {
    if (isOpen && view === 'hierarchy') {
      setTimeout(() => searchRef.current?.focus(), 100)
    }
  }, [isOpen, view])

  // Click outside handler
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
    <div
      ref={dropdownRef}
      className={cn('relative inline-block', className)}
    >
      {/* Model Pill Button */}
      <Button
        ref={buttonRef}
        type="button"
        variant="ghost"
        disabled={disabled}
        onClick={handleToggleOpen}
        className={cn(
          'flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 text-sm font-medium text-text transition-all',
          'hover:border-primary/60 hover:bg-surface-2',
          isOpen && 'border-primary/60 bg-surface-2',
          disabled && 'cursor-not-allowed opacity-60'
        )}
      >
        <div className="flex items-center gap-2">
          <span className="text-text-muted">{selectedModelInfo.provider}</span>
          <span className="text-text">/</span>
          <span className="font-bold text-text">{selectedModelInfo.variant.name}</span>
          <span className="text-xs text-text-muted">({selectedModelInfo.variant.contextWindow})</span>
        </div>
        <svg
          className={cn('h-3 w-3 transition-transform', isOpen && 'rotate-180')}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </Button>

      {/* Popover */}
      {isOpen && (
        <div className="absolute left-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-lg border border-border bg-surface shadow-card">
          {/* Header with tabs */}
          <div className="border-b border-border p-3">
            <div className="flex rounded-lg bg-surface-2 p-1">
              <button
                type="button"
                onClick={() => setView('presets')}
                className={cn(
                  'flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-all',
                  view === 'presets'
                    ? 'bg-surface text-text shadow-sm'
                    : 'text-text-muted hover:text-text'
                )}
              >
                Presets
              </button>
              <button
                type="button"
                onClick={() => setView('hierarchy')}
                className={cn(
                  'flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-all',
                  view === 'hierarchy'
                    ? 'bg-surface text-text shadow-sm'
                    : 'text-text-muted hover:text-text'
                )}
              >
                Todos los modelos
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="max-h-64 overflow-y-auto">
            {view === 'presets' ? (
              // Quick Presets View
              <div className="p-3 space-y-2">
                {QUICK_PRESETS.map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => handleModelSelect(preset.modelId)}
                    className={cn(
                      'flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-all',
                      selectedModel === preset.modelId
                        ? 'border-primary/60 bg-primary/10'
                        : 'border-border hover:border-border/60 hover:bg-surface-2'
                    )}
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-text">{preset.name}</span>
                        {selectedModel === preset.modelId && (
                          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                        )}
                      </div>
                      <p className="mt-1 text-xs text-text-muted">{preset.description}</p>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              // Hierarchy View
              <div>
                {/* Search */}
                <div className="border-b border-border p-3">
                  <input
                    ref={searchRef}
                    type="text"
                    placeholder="Buscar modelos... (⌘K)"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-text placeholder:text-text-muted focus:border-primary/60 focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>

                {/* Model Hierarchy */}
                <div className="p-3 space-y-4">
                  {filteredProviders.map((provider) => (
                    <div key={provider.id}>
                      <h4 className="mb-2 text-xs font-bold uppercase tracking-wide text-text-muted">
                        {provider.name}
                      </h4>
                      <div className="space-y-3">
                        {provider.families.map((family) => (
                          <div key={family.id}>
                            <h5 className="mb-1 text-xs font-medium text-text-muted">
                              {family.name}
                            </h5>
                            <div className="space-y-1">
                              {family.variants.map((variant) => (
                                <button
                                  key={variant.id}
                                  type="button"
                                  onClick={() => handleModelSelect(variant.id)}
                                  disabled={!variant.isAvailable}
                                  className={cn(
                                    'flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-all',
                                    selectedModel === variant.id
                                      ? 'bg-primary/10 text-text'
                                      : variant.isAvailable
                                      ? 'text-text hover:bg-surface-2'
                                      : 'cursor-not-allowed text-text-muted opacity-50'
                                  )}
                                >
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium">{variant.name}</span>
                                    <span className="text-xs text-text-muted">
                                      {variant.contextWindow}
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    {variant.pricing !== 'free' && (
                                      <span className="rounded-full bg-surface-2 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-text-muted">
                                        {variant.pricing}
                                      </span>
                                    )}
                                    {selectedModel === variant.id && (
                                      <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                                    )}
                                  </div>
                                </button>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}