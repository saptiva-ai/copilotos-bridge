'use client'

import * as React from 'react'
import { Button } from '../ui'
import { cn } from '../../lib/utils'

interface Model {
  id: string
  name: string
  description: string
  isAvailable: boolean
}

const AVAILABLE_MODELS: Model[] = [
  {
    id: 'SAPTIVA_TURBO',
    name: 'Saptiva Turbo',
    description: 'Respuestas rápidas, bajo costo',
    isAvailable: true,
  },
  {
    id: 'SAPTIVA_CORTEX',
    name: 'Saptiva Cortex',
    description: 'Tareas de razonamiento',
    isAvailable: true,
  },
  {
    id: 'SAPTIVA_OPS',
    name: 'Saptiva Ops',
    description: 'Casos complejos con tools y SDK',
    isAvailable: true,
  },
  {
    id: 'SAPTIVA_CODER',
    name: 'Saptiva Coder',
    description: 'Programación y codegen',
    isAvailable: true,
  },
  {
    id: 'SAPTIVA_MULTIMODAL',
    name: 'Saptiva Multimodal',
    description: 'Comprensión multimodal, interpretación de texto e imágenes',
    isAvailable: true,
  },
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
  disabled = false 
}: ModelSelectorProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const dropdownRef = React.useRef<HTMLDivElement>(null)

  const selectedModelInfo = React.useMemo(() => {
    return AVAILABLE_MODELS.find((model) => model.id === selectedModel) ?? AVAILABLE_MODELS[0]
  }, [selectedModel])

  const handleModelSelect = (modelId: string) => {
    onModelChange(modelId)
    setIsOpen(false)
  }

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!dropdownRef.current) return
      if (!dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  return (
    <div className={cn('relative', className)} ref={dropdownRef}>
      <Button
        type="button"
        variant="ghost"
        disabled={disabled}
        onClick={() => setIsOpen((open) => !open)}
        className={cn(
          'flex w-full items-center justify-between rounded-2xl border border-white/10 bg-black/30 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-saptiva-light/80 shadow-inner backdrop-blur transition',
          'hover:border-saptiva-mint/60 hover:text-saptiva-mint',
          disabled && 'opacity-50',
        )}
      >
        <div className="flex flex-col text-left">
          <span className="text-[10px] font-semibold tracking-[0.3em] text-saptiva-light/50">Modelo</span>
          <span className="text-sm text-white">{selectedModelInfo.name}</span>
        </div>
        <svg
          className={cn('h-3.5 w-3.5 transition-transform text-saptiva-light/60', isOpen && 'rotate-180')}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M19 9l-7 7-7-7" />
        </svg>
      </Button>

      {isOpen && (
        <div className="absolute top-full z-20 mt-2 w-64 overflow-hidden rounded-2xl border border-white/10 bg-[#171a27] shadow-2xl">
          <div className="flex items-center justify-between px-4 pb-2 pt-3 text-[11px] uppercase tracking-[0.28em] text-saptiva-light/50">
            <span>Modelos disponibles</span>
            <span>{AVAILABLE_MODELS.filter((model) => model.isAvailable).length}</span>
          </div>
          <ul className="max-h-64 divide-y divide-white/5 overflow-y-auto">
            {AVAILABLE_MODELS.map((model) => {
              const isActive = selectedModel === model.id
              return (
                <li key={model.id}>
                  <button
                    type="button"
                    onClick={() => handleModelSelect(model.id)}
                    disabled={!model.isAvailable || disabled}
                    className={cn(
                      'flex w-full items-start justify-between gap-3 px-4 py-3 text-left text-sm transition',
                      isActive
                        ? 'bg-saptiva-mint/10 text-white'
                        : 'text-saptiva-light/70 hover:bg-white/5 hover:text-white',
                      (!model.isAvailable || disabled) && 'cursor-not-allowed opacity-40',
                    )}
                  >
                    <div>
                      <p className="font-semibold">{model.name}</p>
                      <p className="text-[13px] text-saptiva-light/60">{model.description}</p>
                    </div>
                    {!model.isAvailable && (
                      <span className="mt-1 rounded-full bg-white/5 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-saptiva-light/50">
                        Próximamente
                      </span>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}
