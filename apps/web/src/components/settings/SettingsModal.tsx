'use client'

import * as React from 'react'
import { Button } from '../ui'
import { cn } from '../../lib/utils'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [apiKey, setApiKey] = React.useState('')
  const [isSaving, setIsSaving] = React.useState(false)
  const modalRef = React.useRef<HTMLDivElement>(null)
  const firstInputRef = React.useRef<HTMLInputElement>(null)

  // Focus trap - get all focusable elements
  const getFocusableElements = React.useCallback(() => {
    if (!modalRef.current) return []
    return modalRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    ) as NodeListOf<HTMLElement>
  }, [])

  // Handle keyboard events
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return

      // ESC to close
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }

      // Tab focus trap
      if (e.key === 'Tab') {
        const focusableElements = getFocusableElements()
        const firstElement = focusableElements[0]
        const lastElement = focusableElements[focusableElements.length - 1]

        if (e.shiftKey) {
          // Shift+Tab - if on first element, go to last
          if (document.activeElement === firstElement) {
            e.preventDefault()
            lastElement.focus()
          }
        } else {
          // Tab - if on last element, go to first
          if (document.activeElement === lastElement) {
            e.preventDefault()
            firstElement.focus()
          }
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose, getFocusableElements])

  // Focus management
  React.useEffect(() => {
    if (isOpen) {
      // Focus first input when modal opens
      setTimeout(() => firstInputRef.current?.focus(), 100)
    }
  }, [isOpen])

  // Load saved API key
  React.useEffect(() => {
    if (isOpen) {
      const savedKey = localStorage.getItem('saptiva_api_key') || ''
      setApiKey(savedKey)
    }
  }, [isOpen])

  const handleSave = async () => {
    setIsSaving(true)
    try {
      // Save to localStorage
      if (apiKey.trim()) {
        localStorage.setItem('saptiva_api_key', apiKey.trim())

        // Analytics event
        if (typeof window !== 'undefined' && (window as any).gtag) {
          (window as any).gtag('event', 'api_key_saved', {
            has_key: true
          })
        }
      } else {
        localStorage.removeItem('saptiva_api_key')
      }

      // TODO: Validate API key with backend
      await new Promise(resolve => setTimeout(resolve, 500)) // Simulate API call

      onClose()
    } catch (error) {
      console.error('Failed to save API key:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4"
      onClick={handleBackdropClick}
    >
      <div
        ref={modalRef}
        className="bg-white rounded-lab-lg shadow-xl w-full max-w-md mx-auto"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
      >
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 id="settings-title" className="text-lg font-semibold text-gray-900">
              Settings
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Close settings"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label htmlFor="api-key" className="block text-sm font-medium text-gray-700 mb-2">
                SAPTIVA API Key
              </label>
              <input
                ref={firstInputRef}
                id="api-key"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your SAPTIVA API key"
                className="w-full px-3 py-2 border border-gray-300 rounded-lab-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-normal"
              />
              <p className="mt-1 text-xs text-gray-500">
                Your API key is stored locally and never sent to our servers.
              </p>
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <Button
              variant="ghost"
              onClick={onClose}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              loading={isSaving}
              disabled={isSaving}
            >
              {isSaving ? 'Saving...' : 'Save'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}