'use client'

import * as React from 'react'

interface KeyboardShortcuts {
  // Future keyboard shortcuts can be added here
  // Settings removed per ENV-only configuration policy
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcuts = {}) {
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Future keyboard shortcuts will be implemented here
      // Settings shortcut removed per security requirements
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [shortcuts])
}