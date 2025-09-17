'use client'

import * as React from 'react'
import { Button, Badge } from '../ui'
import { cn } from '../../lib/utils'

interface Model {
  id: string
  name: string
  description: string
  isAvailable: boolean
}

const AVAILABLE_MODELS: Model[] = [
  {
    id: 'Saptiva Turbo',
    name: 'Saptiva Turbo',
    description: 'Respuestas rápidas, bajo costo',
    isAvailable: true,
  },
  {
    id: 'Saptiva Cortex',
    name: 'Saptiva Cortex',
    description: 'Tareas de razonamiento',
    isAvailable: true,
  },
  {
    id: 'Saptiva Ops',
    name: 'Saptiva Ops',
    description: 'Casos complejos con tools y SDK',
    isAvailable: true,
  },
  {
    id: 'Saptiva Coder',
    name: 'Saptiva Coder',
    description: 'Programación y codegen',
    isAvailable: true,
  },
  {
    id: 'Saptiva Multimodal',
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
  const selectedModelInfo = AVAILABLE_MODELS.find(m => m.id === selectedModel) || AVAILABLE_MODELS[0]

  const handleModelSelect = (modelId: string) => {
    onModelChange(modelId)
    setIsOpen(false)
  }

  return (
    <div className={cn('relative', className)}>
      <Button
        variant="ghost"
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="flex items-center space-x-1 text-sm"
      >
        <span>{selectedModelInfo.name}</span>
        <svg
          className={cn('h-4 w-4 transition-transform', isOpen && 'rotate-180')}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </Button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full right-0 mt-1 w-48 bg-white border border-gray-200 rounded-md shadow-lg z-20">
            <div className="p-1">
              {AVAILABLE_MODELS.map((model) => (
                <button
                  key={model.id}
                  onClick={() => handleModelSelect(model.id)}
                  disabled={!model.isAvailable}
                  className={cn(
                    'w-full text-left px-3 py-2 rounded-md text-sm transition-colors hover:bg-gray-50',
                    selectedModel === model.id && 'font-semibold',
                    !model.isAvailable && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  {model.name}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

