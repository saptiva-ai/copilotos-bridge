'use client'

import * as React from 'react'

import { cn } from '../../lib/utils'
import { ModelSelector } from './ModelSelector'

interface ChatShellProps {
  sidebar: React.ReactNode
  children: React.ReactNode
  footer?: React.ReactNode
  selectedModel?: string
  onModelChange?: (model: string) => void
}

export function ChatShell({ sidebar, children, footer, selectedModel, onModelChange }: ChatShellProps) {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = React.useState(false)
  const [isDesktopSidebarCollapsed, setIsDesktopSidebarCollapsed] = React.useState(false)

  const handleCloseSidebar = React.useCallback(() => {
    setIsMobileSidebarOpen(false)
  }, [])

  const handleToggleDesktopSidebar = React.useCallback(() => {
    setIsDesktopSidebarCollapsed((collapsed) => !collapsed)
  }, [])

  const handleRequestSidebar = React.useCallback(() => {
    if (typeof window !== 'undefined' && window.matchMedia('(min-width: 1024px)').matches) {
      setIsDesktopSidebarCollapsed(false)
    } else {
      setIsMobileSidebarOpen(true)
    }
  }, [])

  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsMobileSidebarOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const desktopSidebar = React.useMemo(() => {
    if (!React.isValidElement(sidebar)) return sidebar

    return React.cloneElement(sidebar as React.ReactElement, {
      onCollapse: handleToggleDesktopSidebar,
      isCollapsed: isDesktopSidebarCollapsed,
    })
  }, [sidebar, handleToggleDesktopSidebar, isDesktopSidebarCollapsed])

  const mobileSidebar = React.useMemo(() => {
    if (!React.isValidElement(sidebar)) return sidebar

    return React.cloneElement(sidebar as React.ReactElement, {
      onClose: handleCloseSidebar,
    })
  }, [sidebar, handleCloseSidebar])

  return (
    <div className="safe-area-top relative flex h-[100dvh] w-full overflow-hidden bg-bg text-text">
      {/* Desktop sidebar */}
      <aside
        className={cn(
          'hidden h-full shrink-0 overflow-hidden transition-[width] duration-300 ease-in-out lg:flex',
          isDesktopSidebarCollapsed ? 'lg:w-0' : 'lg:w-80 xl:w-96',
        )}
        aria-hidden={isDesktopSidebarCollapsed}
      >
        <div
          className={cn(
            'relative h-full w-full transition-opacity duration-200 ease-in-out',
            isDesktopSidebarCollapsed ? 'pointer-events-none opacity-0' : 'opacity-100',
          )}
        >
          {desktopSidebar}
        </div>
      </aside>

      {/* Mobile sidebar */}
      <div
        className={cn(
          'fixed inset-0 z-40 bg-black/50 transition-opacity duration-200 lg:hidden',
          isMobileSidebarOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0',
        )}
        onClick={handleCloseSidebar}
      />
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-[85vw] max-w-[22rem] overflow-hidden rounded-r-xl shadow-card transition-transform duration-300 lg:hidden bg-surface',
          isMobileSidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="h-full" onClick={(event) => event.stopPropagation()}>
          {mobileSidebar}
        </div>
      </aside>

      {/* Chat area - Following saptiva-chat-fixes-v3.yaml structure */}
      <main className="flex-1 min-w-0 flex flex-col">
        {/* Mobile sidebar trigger */}
        <div
          className={cn(
            'absolute left-4 top-4 z-30 block lg:hidden',
            isDesktopSidebarCollapsed && 'lg:block',
          )}
        >
          <button
            type="button"
            onClick={handleRequestSidebar}
            className="flex h-11 w-11 items-center justify-center rounded-full border border-border bg-surface text-text shadow-card transition hover:bg-surface-2"
            aria-label={isDesktopSidebarCollapsed ? 'Mostrar historial' : 'Mostrar conversaciones'}
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M4 6h16" strokeWidth="1.8" strokeLinecap="round" />
              <path d="M4 12h12" strokeWidth="1.8" strokeLinecap="round" />
              <path d="M4 18h8" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Header con selector de modelo - UX-001 */}
        <header className="shrink-0 border-b border-border/30 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Model Selector - header-left según UX-001 */}
              {selectedModel && onModelChange && (
                <ModelSelector
                  selectedModel={selectedModel}
                  onModelChange={onModelChange}
                  className=""
                />
              )}
            </div>
            <div className="flex items-center gap-2">
              {/* Futuras acciones del header */}
            </div>
          </div>
        </header>

        {/* Message area - scroll manejado por ChatInterface CHT-05 */}
        <section className="flex-1 min-h-0 px-2 py-4">
          {children}
        </section>

        {/* Input area as footer - conditionally render */}
        {footer && (
          <footer className="shrink-0 border-t border-white/10">
            {footer}
          </footer>
        )}
      </main>
    </div>
  )
}
