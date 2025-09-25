'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'

import type { ChatSession } from '../../lib/types'
import { cn, formatRelativeTime } from '../../lib/utils'
import { useAuthStore } from '../../lib/auth-store'

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
  // New actions for UX-002
  onRenameChat?: (chatId: string, newTitle: string) => void
  onPinChat?: (chatId: string) => void
  onDeleteChat?: (chatId: string) => void
  layoutVersion?: 'legacy' | 'grid'
  variant?: 'desktop' | 'mobile'
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
  onRenameChat,
  onPinChat,
  onDeleteChat,
  layoutVersion = 'legacy',
  variant = 'desktop',
}: ConversationListProps) {
  const router = useRouter()
  const [showAccountMenu, setShowAccountMenu] = React.useState(false)
  const [hoveredChatId, setHoveredChatId] = React.useState<string | null>(null)
  const [renamingChatId, setRenamingChatId] = React.useState<string | null>(null)
  const [renameValue, setRenameValue] = React.useState('')
  const { user, logout } = useAuthStore()
  const accountMenuRef = React.useRef<HTMLDivElement>(null)
  const renameInputRef = React.useRef<HTMLInputElement>(null)
  const isGridLayout = layoutVersion === 'grid'
  const isDesktopVariant = variant === 'desktop'
  const showList = !(isGridLayout && isDesktopVariant && isCollapsed)

  // Close account menu when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(event.target as Node)) {
        setShowAccountMenu(false)
      }
    }

    if (showAccountMenu) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showAccountMenu])

  // Keyboard shortcut for collapse - UX-002
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl+B toggles sidebar collapse
      if ((e.metaKey || e.ctrlKey) && e.key === 'b' && onCollapse) {
        e.preventDefault()
        onCollapse()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onCollapse])

  // Auto-focus rename input
  React.useEffect(() => {
    if (renamingChatId && renameInputRef.current) {
      renameInputRef.current.focus()
      renameInputRef.current.select()
    }
  }, [renamingChatId])

  const handleLogout = async () => {
    await logout()
  }

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

  // Hover actions handlers - UX-002
  const handleStartRename = (chatId: string, currentTitle: string) => {
    setRenamingChatId(chatId)
    setRenameValue(currentTitle || 'Conversación sin título')
    setHoveredChatId(null)
  }

  const handleFinishRename = () => {
    if (renamingChatId && renameValue.trim() && onRenameChat) {
      onRenameChat(renamingChatId, renameValue.trim())
    }
    setRenamingChatId(null)
    setRenameValue('')
  }

  const handleCancelRename = () => {
    setRenamingChatId(null)
    setRenameValue('')
  }

  const handleRenameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleFinishRename()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      handleCancelRename()
    }
  }

  const handlePin = (chatId: string) => {
    if (onPinChat) {
      onPinChat(chatId)
    }
    setHoveredChatId(null)
  }

  const handleDelete = (chatId: string) => {
    if (onDeleteChat && confirm('¿Estás seguro de que quieres eliminar esta conversación?')) {
      onDeleteChat(chatId)
    }
    setHoveredChatId(null)
  }

  const listContent = isLoading ? (
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
        const isHovered = hoveredChatId === session.id
        const isRenaming = renamingChatId === session.id
        const isPinned = session.pinned // Assuming this property exists in ChatSession

        return (
          <li key={session.id}>
            <div
              className={cn(
                'group relative flex w-full flex-col rounded-xl border border-transparent px-4 py-3 transition-all duration-150',
                'bg-white/0 hover:bg-white/5 hover:shadow-[0_8px_20px_rgba(27,27,39,0.35)]',
                isActive && 'border-saptiva-mint/40 bg-white/10 shadow-[0_0_0_1px_rgba(138,245,212,0.15)]',
              )}
              onMouseEnter={() => setHoveredChatId(session.id)}
              onMouseLeave={() => setHoveredChatId(null)}
            >
              {/* Main content area - clickable to select */}
              <button
                type="button"
                onClick={() => !isRenaming && handleSelect(session.id)}
                className="flex w-full flex-col text-left"
                disabled={isRenaming}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    {/* Pin indicator */}
                    {isPinned && (
                      <svg className="h-3 w-3 text-saptiva-mint flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M16 12V4a1 1 0 00-1-1H9a1 1 0 00-1 1v8H6a1 1 0 00-1 1v1a1 1 0 001 1h2v5a1 1 0 001 1h6a1 1 0 001-1v-5h2a1 1 0 001-1v-1a1 1 0 00-1-1h-2z"/>
                      </svg>
                    )}

                    {isRenaming ? (
                      <input
                        ref={renameInputRef}
                        type="text"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={handleRenameKeyDown}
                        onBlur={handleFinishRename}
                        className="bg-surface-2 text-sm font-semibold text-white rounded px-2 py-1 border border-border focus:border-primary focus:outline-none min-w-0 flex-1"
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : (
                      <span className="text-sm font-semibold text-white truncate">
                        {session.title || 'Conversación sin título'}
                      </span>
                    )}
                  </div>

                  {!isRenaming && (
                    <span className="text-xs text-saptiva-light/60 flex-shrink-0">
                      {formatRelativeTime(session.updated_at || session.created_at)}
                    </span>
                  )}
                </div>

                {!isRenaming && session.preview && (
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

              {/* Hover actions - UX-002 */}
              {isHovered && !isRenaming && (
                <div className="absolute right-2 top-3 flex items-center gap-1 bg-surface/90 backdrop-blur-sm rounded-lg border border-border p-1">
                  {/* Rename button */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleStartRename(session.id, session.title || '')
                    }}
                    className="h-7 w-7 flex items-center justify-center rounded text-text-muted hover:text-text hover:bg-surface-2 transition-colors"
                    title="Renombrar"
                  >
                    <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>

                  {/* Pin button */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      handlePin(session.id)
                    }}
                    className={cn(
                      'h-7 w-7 flex items-center justify-center rounded transition-colors',
                      isPinned
                        ? 'text-saptiva-mint hover:text-saptiva-mint/80 hover:bg-surface-2'
                        : 'text-text-muted hover:text-text hover:bg-surface-2'
                    )}
                    title={isPinned ? 'Desfijar' : 'Fijar'}
                  >
                    <svg className="h-3.5 w-3.5" fill={isPinned ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                    </svg>
                  </button>

                  {/* Delete button */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDelete(session.id)
                    }}
                    className="h-7 w-7 flex items-center justify-center rounded text-text-muted hover:text-danger hover:bg-danger/10 transition-colors"
                    title="Eliminar"
                  >
                    <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              )}
            </div>
          </li>
        )
      })}
    </ul>
  )
  if (!isGridLayout) {
    return (
      <div
        className={cn(
          'flex h-full flex-col bg-surface text-text',
          'border-r border-border',
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
        {listContent}
      </div>

      {/* Account bar fixed at bottom - ACC-01 */}
      {user && (
        <div className="border-t border-border p-4">
          <div className="relative" ref={accountMenuRef}>
            <button
              type="button"
              onClick={() => setShowAccountMenu(!showAccountMenu)}
              className="flex w-full items-center gap-3 rounded-xl bg-surface-2 p-3 transition-colors hover:bg-surface-2/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
            >
              {/* Avatar */}
              <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center">
                <span className="text-sm font-bold text-primary">
                  {user.username?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase() || 'U'}
                </span>
              </div>

              {/* User info */}
              <div className="flex-1 min-w-0 text-left">
                <p className="text-sm font-bold text-text truncate">{user.username}</p>
                <p className="text-xs text-text-muted truncate">{user.email}</p>
              </div>

              {/* Menu arrow */}
              <svg
                className={cn('h-4 w-4 text-text-muted transition-transform', showAccountMenu && 'rotate-180')}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Account menu */}
            {showAccountMenu && (
              <div className="absolute bottom-full left-0 right-0 mb-2 rounded-xl border border-border bg-surface shadow-card overflow-hidden">
                <button
                  type="button"
                  onClick={() => {
                    setShowAccountMenu(false)
                    // TODO: Navigate to profile page
                  }}
                  className="w-full px-3 py-2 text-left text-sm text-text hover:bg-surface-2 transition-colors"
                >
                  Perfil
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAccountMenu(false)
                    // TODO: Navigate to preferences page
                  }}
                  className="w-full px-3 py-2 text-left text-sm text-text hover:bg-surface-2 transition-colors"
                >
                  Preferencias
                </button>
                <hr className="border-border" />
                <button
                  type="button"
                  onClick={() => {
                    setShowAccountMenu(false)
                    handleLogout()
                  }}
                  className="w-full px-3 py-2 text-left text-sm text-danger hover:bg-danger/10 transition-colors"
                >
                  Cerrar sesión
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
  }

  return (
    <div className={cn('flex h-full flex-col bg-surface text-text', className)}>
      <div
        className={cn(
          'sticky top-0 z-20 flex items-center gap-2 border-b border-border/60 bg-surface/95 backdrop-blur',
          isDesktopVariant ? 'h-14 px-2' : 'px-4 py-4',
        )}
      >
        {isDesktopVariant ? (
          <>
            {onCollapse && (
              <button
                type="button"
                onClick={onCollapse}
                className="relative z-20 inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border/40 bg-surface-2 text-text transition hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                aria-label={isCollapsed ? 'Expandir historial' : 'Colapsar historial'}
              >
                {isCollapsed ? (
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M10 6 16 12 10 18" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M14 6 8 12 14 18" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </button>
            )}

            {!isCollapsed ? (
              <div className="flex w-full items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-[11px] uppercase tracking-[0.2em] text-text-muted">Sesiones</p>
                  <h2 className="text-sm font-semibold text-white">Conversaciones</h2>
                </div>
                <button
                  type="button"
                  onClick={handleCreate}
                  className="flex h-9 w-9 items-center justify-center rounded-xl border border-border/40 bg-surface-2 text-text transition hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  aria-label="Nueva conversación"
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M12 5v14" strokeWidth="1.8" strokeLinecap="round" />
                    <path d="M5 12h14" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                </button>
              </div>
            ) : (
              <div className="ml-auto flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleCreate}
                  className="flex h-9 w-9 items-center justify-center rounded-xl border border-border/40 bg-surface-2 text-text transition hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  aria-label="Nueva conversación"
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M12 5v14" strokeWidth="1.8" strokeLinecap="round" />
                    <path d="M5 12h14" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="flex w-full items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-[0.2em] text-saptiva-light/60">Sesiones</p>
              <h2 className="text-lg font-semibold text-white">Conversaciones</h2>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {onClose && (
                <button
                  type="button"
                  onClick={onClose}
                  className="flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/5 text-saptiva-light transition hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saptiva-mint/60"
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
            </div>
          </div>
        )}
      </div>

      {showList ? (
        <div className="flex-1 overflow-y-auto px-3 pb-6">{listContent}</div>
      ) : (
        <div className="flex flex-1 items-center justify-center">
          <span className="sr-only">Historial colapsado</span>
          <svg className="h-5 w-5 text-text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M4 6h16" strokeWidth="1.6" strokeLinecap="round" />
            <path d="M4 12h12" strokeWidth="1.6" strokeLinecap="round" />
            <path d="M4 18h8" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </div>
      )}

      {user && showList && (
        <div className="border-t border-border p-4">
          <div className="relative" ref={accountMenuRef}>
            <button
              type="button"
              onClick={() => setShowAccountMenu(!showAccountMenu)}
              className="flex w-full items-center gap-3 rounded-xl bg-surface-2 p-3 transition-colors hover:bg-surface-2/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
            >
              {/* Avatar */}
              <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center">
                <span className="text-sm font-bold text-primary">
                  {user.username?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase() || 'U'}
                </span>
              </div>

              {/* User info */}
              <div className="flex-1 min-w-0 text-left">
                <p className="text-sm font-bold text-text truncate">{user.username}</p>
                <p className="text-xs text-text-muted truncate">{user.email}</p>
              </div>

              {/* Menu arrow */}
              <svg
                className={cn('h-4 w-4 text-text-muted transition-transform', showAccountMenu && 'rotate-180')}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Account menu */}
            {showAccountMenu && (
              <div className="absolute bottom-full left-0 right-0 mb-2 rounded-xl border border-border bg-surface shadow-card overflow-hidden">
                <button
                  type="button"
                  onClick={() => {
                    setShowAccountMenu(false)
                    // TODO: Navigate to profile page
                  }}
                  className="w-full px-3 py-2 text-left text-sm text-text hover:bg-surface-2 transition-colors"
                >
                  Perfil
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAccountMenu(false)
                    // TODO: Navigate to preferences page
                  }}
                  className="w-full px-3 py-2 text-left text-sm text-text hover:bg-surface-2 transition-colors"
                >
                  Preferencias
                </button>
                <hr className="border-border" />
                <button
                  type="button"
                  onClick={() => {
                    setShowAccountMenu(false)
                    handleLogout()
                  }}
                  className="w-full px-3 py-2 text-left text-sm text-danger hover:bg-danger/10 transition-colors"
                >
                  Cerrar sesión
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
