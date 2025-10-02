'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'

import type { ChatSession, ChatSessionOptimistic } from '../../lib/types'
import { cn, formatRelativeTime, debounce } from '../../lib/utils'
import { useAuthStore } from '../../lib/auth-store'
import { useKeyboardNavigation } from '../../hooks/useKeyboardNavigation'
// import { VirtualizedConversationList } from './VirtualizedConversationList'

// Threshold for enabling virtualization (performance optimization)
// Temporarily disabled due to react-window build issues in production
const VIRTUALIZATION_THRESHOLD = 999999

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
  // P0-UX-HIST-001: Optimistic UI
  isCreatingConversation?: boolean
  optimisticConversations?: Map<string, ChatSessionOptimistic>
  // Anti-spam: Can create new chat
  canCreateNew?: boolean
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
  isCreatingConversation = false,
  optimisticConversations = new Map(),
  canCreateNew = true,
}: ConversationListProps) {
  const router = useRouter()
  const [hoveredChatId, setHoveredChatId] = React.useState<string | null>(null)
  const [renamingChatId, setRenamingChatId] = React.useState<string | null>(null)
  const [renameValue, setRenameValue] = React.useState('')
  const { user, logout } = useAuthStore()
  const renameInputRef = React.useRef<HTMLInputElement>(null)
  const accountMenuRef = React.useRef<HTMLDivElement>(null)
  const [showAccountMenu, setShowAccountMenu] = React.useState(false)
  const isGridLayout = layoutVersion === 'grid'
  const isDesktopVariant = variant === 'desktop'
  const showList = !(isGridLayout && isDesktopVariant && isCollapsed)

  // Sort sessions first for keyboard navigation
  // P0-UX-HIST-001: Merge optimistic conversations with real sessions
  // Progressive Commitment: Filter empty conversations
  const sortedSessions = React.useMemo(() => {
    // Convert optimistic conversations to array
    const optimisticSessions = Array.from(optimisticConversations.values())

    // Combine optimistic and real sessions (optimistic at the top)
    const allSessions = [...optimisticSessions, ...sessions]

    // Filter out empty conversations (defensive - shouldn't exist with progressive commitment)
    // Keep conversations that have messages OR are optimistic (being created)
    const validSessions = allSessions.filter((s) => {
      const isOptimistic = 'isOptimistic' in s && s.isOptimistic
      const hasMessages = s.message_count > 0
      const hasFirstMessage = s.first_message_at !== null && s.first_message_at !== undefined

      return isOptimistic || hasMessages || hasFirstMessage
    })

    // Sort by last_message_at, then first_message_at, then created_at (most recent first)
    const getSortTimestamp = (session: ChatSession | ChatSessionOptimistic) => {
      // For optimistic sessions, use created_at (they're brand new)
      if ('isOptimistic' in session && session.isOptimistic) {
        return new Date(session.created_at).getTime()
      }

      // For real sessions, prefer last_message_at, fallback to first_message_at, then created_at
      const timestamp = session.last_message_at || session.first_message_at || session.created_at
      return new Date(timestamp).getTime()
    }

    const pinned = validSessions
      .filter((s) => s.pinned)
      .sort((a, b) => getSortTimestamp(b) - getSortTimestamp(a))

    const unpinned = validSessions
      .filter((s) => !s.pinned)
      .sort((a, b) => getSortTimestamp(b) - getSortTimestamp(a))

    return [...pinned, ...unpinned]
  }, [sessions, optimisticConversations])

  // Keyboard navigation hook
  const keyboardNav = useKeyboardNavigation({
    items: sortedSessions,
    onSelect: (session) => handleSelect(session),
    activeItemId: activeChatId,
    getItemId: (session) => session.id,
    isEnabled: !renamingChatId, // Disable when renaming
    onEscape: () => {
      if (renamingChatId) {
        setRenamingChatId(null)
        setRenameValue('')
      }
    },
  })

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

  React.useEffect(() => {
    if (!showAccountMenu) {
      return
    }

    const handleClickOutside = (event: MouseEvent) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(event.target as Node)) {
        setShowAccountMenu(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showAccountMenu])

  const handleLogout = async () => {
    await logout()
  }

  const handleSelect = (session: ChatSession | ChatSessionOptimistic) => {
    // REMOVED: No bloquear navegación por estado lifecycle
    // La UI central decide qué mostrar basado en state + messages.length
    // El usuario SIEMPRE puede hacer switch entre conversaciones

    onSelectChat(session.id)
    router.push(`/chat/${session.id}`)
    onClose?.()
  }

  // P0-FE-BLOCK-BUTTON: Check if there's an existing empty draft or creating conversation
  const existingEmptyDraft = React.useMemo(() => {
    return sortedSessions.find(
      (s) => (s.state === 'draft' || s.state === 'creating') && s.message_count === 0
    )
  }, [sortedSessions])

  const handleCreate = React.useCallback(() => {
    // Anti-spam: Block creation if not allowed
    if (!canCreateNew) {
      toast('Termina o envía un mensaje antes de iniciar otra conversación', {
        icon: '💡',
        duration: 3000,
      })
      return
    }

    // PR4: Prevent double-click with isCreatingConversation state
    if (isCreatingConversation) {
      return
    }

    // P0-FE-BLOCK-BUTTON: If there's an empty draft, redirect to it instead of creating new
    if (existingEmptyDraft) {
      toast('Ya tienes una conversación vacía abierta', { icon: '💡' })
      onSelectChat(existingEmptyDraft.id)
      router.push(`/chat/${existingEmptyDraft.id}`)
      onClose?.()
      return
    }

    onNewChat()
    router.push('/chat')
    onClose?.()
  }, [canCreateNew, isCreatingConversation, existingEmptyDraft, onSelectChat, router, onClose, onNewChat])

  // Hover actions handlers - UX-002
  const handleStartRename = (chatId: string, currentTitle: string) => {
    setRenamingChatId(chatId)
    setRenameValue(currentTitle || 'Conversación sin título')
    setHoveredChatId(null)
  }

  // Debounced rename handler - waits 500ms after user stops typing
  const debouncedRename = React.useMemo(
    () => debounce((chatId: string, newTitle: string) => {
      if (onRenameChat && newTitle.trim()) {
        onRenameChat(chatId, newTitle.trim())
      }
    }, 500),
    [onRenameChat]
  )

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

  // sortedSessions is now defined at the top for keyboard navigation

  // Use virtualization for large lists (>50 items) for performance
  const shouldVirtualize = sortedSessions.length > VIRTUALIZATION_THRESHOLD

  const listContent = isLoading ? (
    <div className="flex h-full items-center justify-center text-sm text-saptiva-light/70">
      Cargando conversaciones...
    </div>
  ) : sessions.length === 0 ? (
    // Empty state - no card, just subtle text
    <div className="flex h-full items-center justify-center px-6 text-center">
      <p className="text-sm text-saptiva-light/50">
        No hay conversaciones aún
      </p>
    </div>
  ) : false ? null : (
    // Virtualization temporarily disabled - always use regular list
    // TODO: Fix react-window build issues and re-enable virtualization
    // Regular list for smaller collections (<= 50 items)
    <ul
      className="space-y-1"
      ref={keyboardNav.listRef as React.RefObject<HTMLUListElement>}
      role={keyboardNav.listProps.role}
      aria-activedescendant={keyboardNav.listProps['aria-activedescendant']}
      tabIndex={keyboardNav.listProps.tabIndex}
    >
      {sortedSessions.map((session, index) => {
        const isActive = activeChatId === session.id
        const isHovered = hoveredChatId === session.id
        const isRenaming = renamingChatId === session.id
        const isPinned = session.pinned
        const isFocused = keyboardNav.isFocused(session)
        // P0-UX-HIST-001: Check if this is an optimistic or new session
        const sessionOpt = session as ChatSessionOptimistic
        const isOptimistic = sessionOpt.isOptimistic === true
        const isNew = sessionOpt.isNew === true

        return (
          <li key={session.id} {...keyboardNav.getItemProps(session, index)}>
            <div
              className={cn(
                'group relative flex w-full flex-col rounded-lg border border-transparent px-3 py-2 transition-all duration-150',
                'bg-transparent hover:bg-white/5',
                isActive && 'bg-white/10',
                isFocused && !isActive && 'ring-1 ring-white/20 bg-white/5',
                // P0-UX-HIST-001: Highlight new sessions with animation
                isNew && 'animate-highlight-fade bg-white/10',
              )}
              onMouseEnter={() => setHoveredChatId(session.id)}
              onMouseLeave={() => setHoveredChatId(null)}
            >
              {/* Main content area - clickable to select */}
              <button
                type="button"
                onClick={() => !isRenaming && handleSelect(session)}
                className={cn(
                  "flex w-full flex-col text-left transition-opacity",
                  sessionOpt.state === 'creating' && "opacity-75"
                )}
                disabled={isRenaming}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    {/* Pin indicator - Classic office pushpin */}
                    {isPinned && (
                      <svg className="h-3 w-3 text-saptiva-mint flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M16,12V4H17V2H7V4H8V12L6,14V16H11.2V22H12.8V16H18V14L16,12Z" />
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
                      <>
                        <span className="text-sm font-medium text-white truncate">
                          {session.title || 'Conversación sin título'}
                        </span>
                        {/* P0-UX-HIST-001: Show spinner for optimistic sessions */}
                        {isOptimistic && (
                          <svg
                            className="h-3 w-3 animate-spin text-saptiva-mint flex-shrink-0"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                          >
                            <circle
                              className="opacity-25"
                              cx="12"
                              cy="12"
                              r="10"
                              stroke="currentColor"
                              strokeWidth="4"
                            ></circle>
                            <path
                              className="opacity-75"
                              fill="currentColor"
                              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            ></path>
                          </svg>
                        )}
                      </>
                    )}
                  </div>

                  {!isRenaming && (
                    <div className="flex items-center gap-1.5 flex-shrink-0 opacity-70">
                      {/* Removed NEW badge and timestamp for minimal design */}
                    </div>
                  )}
                </div>

                {/* Removed preview text for minimal design */}
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

                  {/* Pin button - Classic office pushpin */}
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
                    <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M16,12V4H17V2H7V4H8V12L6,14V16H11.2V22H12.8V16H18V14L16,12Z" />
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
          'flex h-full flex-col w-[288px] bg-neutral-950',
          'border-r border-white/10',
          className,
        )}
      >
        <div className="flex items-center justify-between gap-2 px-3 py-3">
          {/* Removed: "Sesiones" and "Conversaciones" headers for minimal design */}
          <div className="flex-1" />
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
            disabled={isCreatingConversation || !canCreateNew}
            className={cn(
              "flex h-10 w-full items-center justify-center rounded-lg transition border border-white/10",
              isCreatingConversation || !canCreateNew
                ? "bg-white/5 text-white/60 cursor-not-allowed"
                : existingEmptyDraft
                ? "bg-white/10 text-white hover:bg-white/15"
                : "bg-white/5 text-white/70 hover:bg-white/10"
            )}
            aria-label={
              isCreatingConversation
                ? "Creando conversación..."
                : !canCreateNew
                ? "Termina o envía un mensaje antes de crear otra"
                : existingEmptyDraft
                ? "Ir a conversación vacía existente"
                : "Nueva conversación"
            }
            title={
              !canCreateNew
                ? "Termina o envía un mensaje antes de crear otra conversación"
                : existingEmptyDraft
                ? "Ya tienes una conversación vacía"
                : undefined
            }
          >
            {isCreatingConversation ? (
              <svg
                className="h-5 w-5 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            ) : existingEmptyDraft ? (
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M15 18l-6-6 6-6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M12 5v14" strokeWidth="1.8" strokeLinecap="round" />
                <path d="M5 12h14" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
            )}
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
          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-xl bg-surface-2 p-3 transition-colors hover:bg-surface-2/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
          >
            <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center">
              <svg className="h-4 w-4 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M13 16l4-4-4-4" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M7 12h10" strokeWidth="1.6" strokeLinecap="round" />
                <path d="M12 21H7a1 1 0 01-1-1V4a1 1 0 011-1h5" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
            </div>
            <div className="flex-1 min-w-0 text-left">
              <p className="text-sm font-bold text-text truncate">Cerrar sesión</p>
              <p className="text-xs text-text-muted truncate">Salir de la cuenta actual</p>
            </div>
          </button>
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
                  disabled={isCreatingConversation || !canCreateNew}
                  className={cn(
                    "flex h-9 w-9 items-center justify-center rounded-xl border transition focus-visible:outline-none focus-visible:ring-2",
                    isCreatingConversation || !canCreateNew
                      ? "border-border/30 bg-surface-2/60 text-text/60 cursor-not-allowed"
                      : existingEmptyDraft
                      ? "border-primary/60 bg-primary/10 text-primary hover:bg-primary/20 focus-visible:ring-primary"
                      : "border-border/40 bg-surface-2 text-text hover:bg-surface focus-visible:ring-primary"
                  )}
                  aria-label={
                    isCreatingConversation
                      ? "Creando conversación..."
                      : !canCreateNew
                      ? "Termina o envía un mensaje antes de crear otra"
                      : existingEmptyDraft
                      ? "Ir a conversación vacía existente"
                      : "Nueva conversación"
                  }
                  title={
                    !canCreateNew
                      ? "Termina o envía un mensaje antes de crear otra conversación"
                      : existingEmptyDraft
                      ? "Ya tienes una conversación vacía"
                      : undefined
                  }
                >
                  {isCreatingConversation ? (
                    <svg
                      className="h-4 w-4 animate-spin"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                  ) : existingEmptyDraft ? (
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path d="M15 18l-6-6 6-6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ) : (
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path d="M12 5v14" strokeWidth="1.8" strokeLinecap="round" />
                      <path d="M5 12h14" strokeWidth="1.8" strokeLinecap="round" />
                    </svg>
                  )}
                </button>
              </div>
            ) : (
              <div className="ml-auto flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleCreate}
                  disabled={isCreatingConversation || !canCreateNew}
                  className={cn(
                    "flex h-9 w-9 items-center justify-center rounded-xl border transition focus-visible:outline-none focus-visible:ring-2",
                    isCreatingConversation || !canCreateNew
                      ? "border-border/30 bg-surface-2/60 text-text/60 cursor-not-allowed"
                      : existingEmptyDraft
                      ? "border-primary/60 bg-primary/10 text-primary hover:bg-primary/20 focus-visible:ring-primary"
                      : "border-border/40 bg-surface-2 text-text hover:bg-surface focus-visible:ring-primary"
                  )}
                  aria-label={
                    isCreatingConversation
                      ? "Creando conversación..."
                      : !canCreateNew
                      ? "Termina o envía un mensaje antes de crear otra"
                      : existingEmptyDraft
                      ? "Ir a conversación vacía existente"
                      : "Nueva conversación"
                  }
                  title={
                    !canCreateNew
                      ? "Termina o envía un mensaje antes de crear otra conversación"
                      : existingEmptyDraft
                      ? "Ya tienes una conversación vacía"
                      : undefined
                  }
                >
                  {isCreatingConversation ? (
                    <svg
                      className="h-4 w-4 animate-spin"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                  ) : existingEmptyDraft ? (
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path d="M15 18l-6-6 6-6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ) : (
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path d="M12 5v14" strokeWidth="1.8" strokeLinecap="round" />
                      <path d="M5 12h14" strokeWidth="1.8" strokeLinecap="round" />
                    </svg>
                  )}
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
                disabled={isCreatingConversation || !canCreateNew}
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-full transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saptiva-mint/60",
                  isCreatingConversation || !canCreateNew
                    ? "bg-saptiva-mint/10 text-saptiva-mint/60 cursor-not-allowed"
                    : "bg-saptiva-mint/20 text-saptiva-mint hover:scale-[1.02] hover:bg-saptiva-mint/30"
                )}
                aria-label={
                  isCreatingConversation
                    ? "Creando conversación..."
                    : !canCreateNew
                    ? "Termina o envía un mensaje antes de crear otra"
                    : "Nueva conversación"
                }
                title={
                  !canCreateNew
                    ? "Termina o envía un mensaje antes de crear otra conversación"
                    : undefined
                }
              >
                {isCreatingConversation ? (
                  <svg
                    className="h-5 w-5 animate-spin"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                ) : (
                  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M12 5v14" strokeWidth="1.8" strokeLinecap="round" />
                    <path d="M5 12h14" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                )}
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
