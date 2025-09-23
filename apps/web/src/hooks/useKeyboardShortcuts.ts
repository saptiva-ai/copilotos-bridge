'use client'

import * as React from 'react'

interface KeyboardShortcuts {
  onSettingsOpen?: () => void
}

export function useKeyboardShortcuts({ onSettingsOpen }: KeyboardShortcuts) {
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl+K to open settings
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        onSettingsOpen?.()

        // Analytics event
        if (typeof window !== 'undefined' && (window as any).gtag) {
          (window as any).gtag('event', 'settings_opened', {
            trigger: 'keyboard_shortcut'
          })
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onSettingsOpen])
}