'use client'

import * as React from 'react'
import { Button, Badge } from '../ui'
import { cn } from '../../lib/utils'

interface Model {
  id: string
  name: string
  description: string
  capabilities: string[]
  maxTokens: number
  isAvailable: boolean
}

const AVAILABLE_MODELS: Model[] = [
  {
    id: 'SAPTIVA_CORTEX',
    name: 'SAPTIVA Cortex',
    description: 'General purpose model for conversations and analysis',
    capabilities: ['chat', 'analysis', 'code'],
    maxTokens: 4096,
    isAvailable: true,
  },
  {
    id: 'SAPTIVA_OPS',
    name: 'SAPTIVA Ops',
    description: 'Specialized for operations and planning tasks',
    capabilities: ['planning', 'operations', 'strategy'],
    maxTokens: 2048,
    isAvailable: true,
  },
  {
    id: 'SAPTIVA_NEXUS',
    name: 'SAPTIVA Nexus',
    description: 'Advanced model for complex reasoning',
    capabilities: ['reasoning', 'research', 'analysis'],
    maxTokens: 8192,
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
      {/* Trigger button */}
      <Button
        variant="outline"
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="w-full justify-between"
      >
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <span className="font-medium">{selectedModelInfo.name}</span>
        </div>
        <svg
          className={cn('h-4 w-4 transition-transform', isOpen && 'rotate-180')}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </Button>

      {/* Dropdown menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Menu */}
          <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-md shadow-lg z-20 max-h-64 overflow-y-auto">
            <div className="p-2">
              <div className="text-xs font-medium text-gray-500 mb-2 px-2">Choose Model</div>
              {AVAILABLE_MODELS.map((model) => (
                <button
                  key={model.id}
                  onClick={() => handleModelSelect(model.id)}
                  disabled={!model.isAvailable}
                  className={cn(
                    'w-full text-left px-3 py-3 rounded-md transition-colors hover:bg-gray-50',
                    selectedModel === model.id && 'bg-primary-50 border border-primary-200',
                    !model.isAvailable && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  <div className="flex items-start justify-between mb-1">
                    <div className="flex items-center space-x-2">
                      <div className={cn(
                        'w-2 h-2 rounded-full',
                        model.isAvailable ? 'bg-green-500' : 'bg-gray-400'
                      )}></div>
                      <span className="font-medium text-sm text-gray-900">{model.name}</span>
                      {selectedModel === model.id && (
                        <Badge variant="info" size="sm">Active</Badge>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 mb-2">{model.description}</p>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-1">
                      {model.capabilities.map((cap) => (
                        <Badge key={cap} variant="secondary" size="sm">
                          {cap}
                        </Badge>
                      ))}
                    </div>
                    <span className="text-xs text-gray-500">
                      {model.maxTokens.toLocaleString()} tokens
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// Model info display component
export function ModelInfo({ modelId }: { modelId: string }) {
  const model = AVAILABLE_MODELS.find(m => m.id === modelId)
  
  if (!model) return null

  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-medium text-gray-900">{model.name}</h4>
        <Badge variant={model.isAvailable ? 'success' : 'secondary'} size="sm">
          {model.isAvailable ? 'Available' : 'Unavailable'}
        </Badge>
      </div>
      <p className="text-sm text-gray-600 mb-2">{model.description}</p>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center space-x-1">
          {model.capabilities.map((cap) => (
            <Badge key={cap} variant="secondary" size="sm">
              {cap}
            </Badge>
          ))}
        </div>
        <span>Max: {model.maxTokens.toLocaleString()} tokens</span>
      </div>
    </div>
  )
}