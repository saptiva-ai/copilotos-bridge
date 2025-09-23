'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'

import type { ChatSession } from '../../lib/types'
import { cn, formatRelativeTime } from '../../lib/utils'

interface ConversationListProps {
  sessions: ChatSession[]
  onNewChat: () => void
  onSelectChat: (chatId: string) => void
  activeChatId?: string | null
  isLoading?: boolean
  onClose?: () => void
  onCollapse?: () => void
  isCollapsed?: boolean
  className?: string
}

export function ConversationList({
  sessions,
  onNewChat,
  onSelectChat,
  activeChatId,
  isLoading = false,
  onClose,
  onCollapse,
  isCollapsed,
  className,
}: ConversationListProps) {
  const router = useRouter()

  const handleSelect = (chatId: string) => {
    onSelectChat(chatId)
    router.push(`/chat/${chatId}`)
    onClose?.()
  }

  const handleCreate = () => {
    onNewChat()
    router.push('/chat')
    onClose?.()
  }

  return (
    <div
      className={cn(
        'flex h-full flex-col bg-saptiva-dark/60 backdrop-blur-xl text-saptiva-light',
        'border-r border-white/10 shadow-[rgba(0,0,0,0.08)_1px_0px_0px_0px]',
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3 px-5 pb-4 pt-6">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.2em] text-saptiva-light/60">Sesiones</p>
          <h2 className="text-lg font-semibold text-white">Conversaciones</h2>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/5 text-saptiva-light transition hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saptiva-mint/60 lg:hidden"
              aria-label="Cerrar historial"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="m16 8-8 8" strokeWidth="1.8" strokeLinecap="round" />
                <path d="m8 8 8 8" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
            </button>
          )}

          <button
            type="button"
            onClick={handleCreate}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-saptiva-mint/20 text-saptiva-mint transition hover:scale-[1.02] hover:bg-saptiva-mint/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saptiva-mint/60"
            aria-label="Nueva conversación"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M12 5v14" strokeWidth="1.8" strokeLinecap="round" />
              <path d="M5 12h14" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>

          {onCollapse && (
            <button
              type="button"
              onClick={onCollapse}
              className="hidden h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/5 text-saptiva-light transition hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saptiva-mint/60 lg:flex"
              aria-label={isCollapsed ? 'Mostrar historial' : 'Ocultar historial'}
            >
              {isCollapsed ? (
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M10 6 16 12 10 18" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : (
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M14 6 8 12 14 18" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-6">
        {isLoading ? (
          <div className="flex h-full items-center justify-center text-sm text-saptiva-light/70">
            Cargando conversaciones...
          </div>
        ) : sessions.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-6 text-sm text-saptiva-light/70">
            <p className="font-semibold text-white">Tu primer chat</p>
            <p className="mt-2 leading-relaxed">
              Aún no tienes conversaciones guardadas. Empieza una nueva sesión para explorar el
              conocimiento de Saptiva.
            </p>
            <button
              type="button"
              onClick={handleCreate}
              className="mt-4 inline-flex items-center justify-center rounded-full bg-saptiva-blue px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white hover:bg-saptiva-lightBlue/90"
            >
              Iniciar conversación
            </button>
          </div>
        ) : (
          <ul className="space-y-1">
            {sessions.map((session) => {
              const isActive = activeChatId === session.id
              return (
                <li key={session.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(session.id)}
                    className={cn(
                      'group flex w-full flex-col rounded-xl border border-transparent px-4 py-3 text-left transition-all duration-150',
                      'bg-white/0 hover:bg-white/5 hover:shadow-[0_8px_20px_rgba(27,27,39,0.35)]',
                      isActive && 'border-saptiva-mint/40 bg-white/10 shadow-[0_0_0_1px_rgba(138,245,212,0.15)]',
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-semibold text-white truncate">
                        {session.title || 'Conversación sin título'}
                      </span>
                      <span className="text-xs text-saptiva-light/60">
                        {formatRelativeTime(session.updated_at || session.created_at)}
                      </span>
                    </div>
                    {session.preview && (
                      <p
                        className="mt-1 text-xs text-saptiva-light/70"
                        style={{
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                        }}
                      >
                        {session.preview}
                      </p>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
