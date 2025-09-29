'use client'

import * as React from 'react'
import { Button, Badge, Input } from '../ui'
import { cn } from '../../lib/utils'
import { apiClient } from '../../lib/api-client'
import type { FeatureFlagsResponse } from '../../lib/api-client'

interface ResearchParams {
  budget?: number
  maxIterations?: number
  scope?: string
  sourcesLimit?: number
  depthLevel: 'shallow' | 'medium' | 'deep'
  focusAreas: string[]
  language: string
  includeCitations: boolean
}

interface ToolsConfig {
  webSearch: boolean
  deepResearch: boolean
  researchParams: ResearchParams
}

interface ToolsPanelProps {
  config: ToolsConfig
  onChange: (config: ToolsConfig) => void
  className?: string
  disabled?: boolean
}

const DEPTH_LEVELS = [
  { value: 'shallow', label: 'Shallow', description: 'Quick overview' },
  { value: 'medium', label: 'Medium', description: 'Balanced depth' },
  { value: 'deep', label: 'Deep', description: 'Comprehensive analysis' },
] as const

export function ToolsPanel({
  config,
  onChange,
  className,
  disabled = false
}: ToolsPanelProps) {
  const [isExpanded, setIsExpanded] = React.useState(false)
  const [focusAreaInput, setFocusAreaInput] = React.useState('')
  const [featureFlags, setFeatureFlags] = React.useState<FeatureFlagsResponse | null>(null)

  // P0-DR-KILL-001, P0-DR-002: Fetch feature flags from backend on mount
  React.useEffect(() => {
    const fetchFlags = async () => {
      try {
        const flags = await apiClient.getFeatureFlags()
        setFeatureFlags(flags)
      } catch (error) {
        console.error('Failed to fetch feature flags:', error)
        // Default to disabled if we can't fetch flags
        setFeatureFlags({
          deep_research_kill_switch: true,
          deep_research_enabled: false,
          deep_research_auto: false,
          deep_research_complexity_threshold: 0.7
        })
      }
    }
    fetchFlags()
  }, [])

  const updateConfig = (updates: Partial<ToolsConfig>) => {
    onChange({ ...config, ...updates })
  }

  const updateResearchParams = (updates: Partial<ResearchParams>) => {
    updateConfig({
      researchParams: { ...config.researchParams, ...updates }
    })
  }

  const addFocusArea = () => {
    const area = focusAreaInput.trim()
    if (area && !config.researchParams.focusAreas.includes(area)) {
      updateResearchParams({
        focusAreas: [...config.researchParams.focusAreas, area]
      })
      setFocusAreaInput('')
    }
  }

  const removeFocusArea = (area: string) => {
    updateResearchParams({
      focusAreas: config.researchParams.focusAreas.filter(a => a !== area)
    })
  }

  const hasActiveTools = config.webSearch || config.deepResearch

  return (
    <div className={cn('border border-gray-200 rounded-lg bg-white', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <svg className="h-4 w-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="font-medium text-gray-900">Tools</span>
          {hasActiveTools && (
            <Badge variant="info" size="sm">
              {[config.webSearch && 'Web Search', config.deepResearch && 'Deep Research']
                .filter(Boolean).length} active
            </Badge>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          disabled={disabled}
        >
          <svg
            className={cn('h-4 w-4 transition-transform', isExpanded && 'rotate-180')}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
          </svg>
        </Button>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-3 space-y-4">
          {/* Tool toggles */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-gray-900">Available Tools</h4>
            
            {/* Web Search */}
            <label className="flex items-start space-x-3">
              <input
                type="checkbox"
                checked={config.webSearch}
                onChange={(e) => updateConfig({ webSearch: e.target.checked })}
                disabled={disabled}
                className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <div className="flex-1">
                <div className="font-medium text-gray-900">Web Search</div>
                <div className="text-sm text-gray-600">
                  Search the web for current information and sources
                </div>
              </div>
            </label>

            {/* Deep Research - P0-DR-KILL-001: Completely disabled when kill switch active */}
            {!featureFlags?.deep_research_kill_switch && (
              <label className="flex items-start space-x-3">
                <input
                  type="checkbox"
                  checked={config.deepResearch}
                  onChange={(e) => updateConfig({ deepResearch: e.target.checked })}
                  disabled={disabled || !featureFlags?.deep_research_enabled}
                  className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                  title={!featureFlags?.deep_research_enabled ? 'Deep Research is temporarily disabled' : ''}
                />
                <div className="flex-1">
                  <div className={cn(
                    "font-medium",
                    !featureFlags?.deep_research_enabled ? "text-gray-400" : "text-gray-900"
                  )}>
                    Deep Research
                    {!featureFlags?.deep_research_enabled && (
                      <Badge variant="warning" size="sm" className="ml-2">
                        Disabled
                      </Badge>
                    )}
                  </div>
                  <div className="text-sm text-gray-600">
                    {!featureFlags?.deep_research_enabled
                      ? 'This feature is temporarily disabled'
                      : 'Comprehensive research with multiple iterations and sources'}
                  </div>
                  {config.deepResearch && featureFlags?.deep_research_enabled && (
                    <Badge variant="warning" size="sm" className="mt-1">
                      Uses more resources
                    </Badge>
                  )}
                </div>
              </label>
            )}
          </div>

          {/* Deep Research Parameters */}
          {config.deepResearch && (
            <div className="space-y-3 pt-3 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-900">Research Parameters</h4>
              
              {/* Depth Level */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Research Depth
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {DEPTH_LEVELS.map((level) => (
                    <button
                      key={level.value}
                      type="button"
                      onClick={() => updateResearchParams({ depthLevel: level.value })}
                      disabled={disabled}
                      className={cn(
                        'p-2 text-sm rounded-md border transition-colors',
                        config.researchParams.depthLevel === level.value
                          ? 'bg-primary-50 border-primary-200 text-primary-700'
                          : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
                      )}
                    >
                      <div className="font-medium">{level.label}</div>
                      <div className="text-xs text-gray-500">{level.description}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Advanced settings */}
              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="Max Sources"
                  type="number"
                  value={config.researchParams.sourcesLimit || 20}
                  onChange={(e) => updateResearchParams({ sourcesLimit: parseInt(e.target.value) || 20 })}
                  disabled={disabled}
                  min="1"
                  max="50"
                />
                <Input
                  label="Max Iterations"
                  type="number"
                  value={config.researchParams.maxIterations || 5}
                  onChange={(e) => updateResearchParams({ maxIterations: parseInt(e.target.value) || 5 })}
                  disabled={disabled}
                  min="1"
                  max="20"
                />
              </div>

              {/* Focus Areas */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Focus Areas
                </label>
                <div className="flex space-x-2 mb-2">
                  <Input
                    value={focusAreaInput}
                    onChange={(e) => setFocusAreaInput(e.target.value)}
                    placeholder="e.g., quantum computing, AI ethics"
                    disabled={disabled}
                    onKeyDown={(e) => e.key === 'Enter' && addFocusArea()}
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={addFocusArea}
                    disabled={disabled || !focusAreaInput.trim()}
                  >
                    Add
                  </Button>
                </div>
                {config.researchParams.focusAreas.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {config.researchParams.focusAreas.map((area) => (
                      <Badge
                        key={area}
                        variant="secondary"
                        size="sm"
                        className="flex items-center space-x-1"
                      >
                        <span>{area}</span>
                        <button
                          onClick={() => removeFocusArea(area)}
                          disabled={disabled}
                          className="ml-1 hover:text-red-600"
                        >
                          <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              {/* Options */}
              <div className="space-y-2">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={config.researchParams.includeCitations}
                    onChange={(e) => updateResearchParams({ includeCitations: e.target.checked })}
                    disabled={disabled}
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <span className="text-sm text-gray-700">Include citations and sources</span>
                </label>
              </div>
            </div>
          )}

          {/* Summary */}
          {hasActiveTools && (
            <div className="pt-3 border-t border-gray-200">
              <div className="text-xs text-gray-500">
                Active tools will be used to enhance responses with real-time information and comprehensive analysis.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}