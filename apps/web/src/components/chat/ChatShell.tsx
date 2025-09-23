'use client'

import * as React from 'react'

import { cn } from '../../lib/utils'

interface ChatShellProps {
  sidebar: React.ReactNode
  children: React.ReactNode
  footer?: React.ReactNode
}

export function ChatShell({ sidebar, children, footer }: ChatShellProps) {
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
    <div className="relative flex h-[100dvh] w-full overflow-hidden bg-gradient-to-br from-saptiva-dark via-[#1e2033] to-[#11131f] text-saptiva-light">
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
          'fixed inset-0 z-40 bg-[rgba(8,10,17,0.72)] backdrop-blur-md transition-opacity duration-200 lg:hidden',
          isMobileSidebarOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0',
        )}
        onClick={handleCloseSidebar}
      />
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-[85vw] max-w-[22rem] overflow-hidden rounded-r-3xl shadow-2xl transition-transform duration-300 lg:hidden',
          'bg-saptiva-dark/90 backdrop-blur-xl',
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
            className="flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/10 text-white shadow-lg backdrop-blur transition hover:bg-white/20"
            aria-label={isDesktopSidebarCollapsed ? 'Mostrar historial' : 'Mostrar conversaciones'}
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M4 6h16" strokeWidth="1.8" strokeLinecap="round" />
              <path d="M4 12h12" strokeWidth="1.8" strokeLinecap="round" />
              <path d="M4 18h8" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Message area with dedicated scroll container */}
        <section className="flex-1 min-h-0 overflow-hidden px-2 py-4">
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
