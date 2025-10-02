'use client'

import { memo } from 'react'

export interface ChatHeroProps {
  userName?: string
}

/**
 * Hero component - Centered greeting shown when no messages exist
 * This follows ChatGPT's UX pattern of a welcoming empty state
 */
export const ChatHero = memo(function ChatHero({ userName = 'Jaziel' }: ChatHeroProps) {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center text-center gap-4 pointer-events-none px-4">
      <h1 className="text-3xl font-semibold text-white/95">
        ¿Cómo puedo ayudarte, {userName}?
      </h1>
    </div>
  )
})

ChatHero.displayName = 'ChatHero'
