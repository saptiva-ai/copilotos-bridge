'use client'

import * as React from 'react'
import Image from 'next/image'

import { cn } from '../../lib/utils'
import { ModelSelector, type ChatModel } from './ModelSelector'
import { featureFlags } from '../../lib/feature-flags'

interface ChatShellProps {
  sidebar: React.ReactNode
  children: React.ReactNode
  footer?: React.ReactNode
  models: ChatModel[]
  selectedModel?: string
  onModelChange?: (model: string) => void
}

export function ChatShell(props: ChatShellProps) {
  const layoutGridEnabled = featureFlags.webSearch

  if (!layoutGridEnabled) {
    return <LegacyChatShell {...props} />
  }

  return <GridChatShell {...props} />
}

function GridChatShell({ sidebar, children, footer, models, selectedModel, onModelChange }: ChatShellProps) {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = React.useState(false)
  const [isDesktopSidebarCollapsed, setIsDesktopSidebarCollapsed] = React.useState(false)
  const [isDesktop, setIsDesktop] = React.useState(false)

  const sidebarWidth = isDesktopSidebarCollapsed ? 64 : 280
  const safeLeft = !isDesktop && !isMobileSidebarOpen ? '48px' : '0px'

  // Update body data attribute for CSS variable switching
  React.useEffect(() => {
    if (typeof document !== 'undefined') {
      document.body.setAttribute(
        'data-sidebar',
        isDesktopSidebarCollapsed ? 'collapsed' : 'expanded'
      )
    }
  }, [isDesktopSidebarCollapsed])

  React.useEffect(() => {
    const mediaQuery = window.matchMedia('(min-width: 1024px)')

    const update = () => {
      setIsDesktop(mediaQuery.matches)
      if (mediaQuery.matches) {
        setIsMobileSidebarOpen(false)
      }
    }

    update()

    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', update)
      return () => mediaQuery.removeEventListener('change', update)
    }

    mediaQuery.addListener(update)
    return () => mediaQuery.removeListener(update)
  }, [])

  const handleCloseSidebar = React.useCallback(() => {
    setIsMobileSidebarOpen(false)
  }, [])

  const handleToggleDesktopSidebar = React.useCallback(() => {
    setIsDesktopSidebarCollapsed((collapsed) => !collapsed)
  }, [])

  const handleRequestSidebar = React.useCallback(() => {
    if (isDesktop) {
      setIsDesktopSidebarCollapsed(false)
      return
    }
    setIsMobileSidebarOpen(true)
  }, [isDesktop])

  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'b') {
        event.preventDefault()
        if (isDesktop) {
          handleToggleDesktopSidebar()
        } else {
          setIsMobileSidebarOpen((open) => !open)
        }
      }

      if (event.key === 'Escape') {
        setIsMobileSidebarOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleToggleDesktopSidebar, isDesktop])

  const cloneSidebar = React.useCallback(
    (extraProps: Record<string, unknown>) => {
      if (!React.isValidElement(sidebar)) return sidebar
      return React.cloneElement(sidebar as React.ReactElement, extraProps)
    },
    [sidebar],
  )

  const desktopSidebar = React.useMemo(
    () =>
      cloneSidebar({
        onCollapse: handleToggleDesktopSidebar,
        isCollapsed: isDesktopSidebarCollapsed,
        variant: 'desktop',
        layoutVersion: 'grid',
      }),
    [cloneSidebar, handleToggleDesktopSidebar, isDesktopSidebarCollapsed],
  )

  const mobileSidebar = React.useMemo(
    () =>
      cloneSidebar({
        onClose: handleCloseSidebar,
        variant: 'mobile',
        layoutVersion: 'grid',
      }),
    [cloneSidebar, handleCloseSidebar],
  )

  const containerStyle = React.useMemo<React.CSSProperties>(() => {
    const style: React.CSSProperties = {
      ['--safe-left' as any]: safeLeft,
    }

    if (isDesktop) {
      style.display = 'grid'
      style.gridTemplateColumns = `${sidebarWidth}px 1fr`
      style.gridTemplateRows = '56px 1fr'
      style.gridTemplateAreas = '"sidebar header" "sidebar content"'
    } else {
      style.display = 'flex'
      style.flexDirection = 'column'
    }

    return style
  }, [isDesktop, sidebarWidth, safeLeft])

  return (
    <div className="relative h-[100dvh] w-full overflow-hidden bg-bg text-text" style={containerStyle}>
      {isDesktop ? (
        <>
          <aside
            style={{ gridArea: 'sidebar', width: sidebarWidth }}
            className={cn(
              'relative z-[5] flex h-full flex-col overflow-hidden border-r border-border bg-sidebar transition-[width] duration-200',
            )}
          >
            <div className="flex-1 overflow-hidden">
              {desktopSidebar}
            </div>
          </aside>

          <header
            style={{ gridArea: 'header', paddingLeft: 'calc(var(--safe-left, 0px) + 15px)' }}
            className="z-30 flex items-center justify-between gap-3 border-b border-border/40 bg-surface/95 px-4 backdrop-blur"
          >
            {selectedModel && onModelChange ? (
              <ModelSelector
                models={models}
                selectedModel={selectedModel}
                onModelChange={onModelChange}
                className="max-w-xs"
              />
            ) : null}
            <div className="flex items-center">
              <Image
                src="/Saptiva_AI_logo_new.webp"
                alt="Saptiva AI"
                width={120}
                height={32}
                className="h-8 w-auto"
                priority
              />
            </div>
          </header>

          <main style={{ gridArea: 'content' }} className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <div className="flex-1 overflow-hidden">{children}</div>
            {footer ? <div className="shrink-0 border-t border-border/40 bg-surface">{footer}</div> : null}
          </main>
        </>
      ) : (
        <LegacyMobileLayout
          mobileSidebar={mobileSidebar}
          isMobileSidebarOpen={isMobileSidebarOpen}
          onRequestSidebar={handleRequestSidebar}
          onCloseSidebar={handleCloseSidebar}
          models={models}
          selectedModel={selectedModel}
          onModelChange={onModelChange}
          footer={footer}
        >
          {children}
        </LegacyMobileLayout>
      )}
    </div>
  )
}

interface LegacyMobileLayoutProps {
  children: React.ReactNode
  mobileSidebar: React.ReactNode
  isMobileSidebarOpen: boolean
  onRequestSidebar: () => void
  onCloseSidebar: () => void
  models: ChatModel[]
  selectedModel?: string
  onModelChange?: (model: string) => void
  footer?: React.ReactNode
}

function LegacyMobileLayout({
  children,
  mobileSidebar,
  isMobileSidebarOpen,
  onRequestSidebar,
  onCloseSidebar,
  models,
  selectedModel,
  onModelChange,
  footer,
}: LegacyMobileLayoutProps) {
  return (
    <div className="relative flex h-[100dvh] w-full flex-col overflow-hidden bg-bg text-text">
      <div className="absolute left-4 top-4 z-30 block">
        <button
          type="button"
          onClick={onRequestSidebar}
          className="flex h-11 w-11 items-center justify-center rounded-full border border-border bg-surface text-text shadow-card transition hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
          aria-label="Abrir historial"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M4 6h16" strokeWidth="1.8" strokeLinecap="round" />
            <path d="M4 12h12" strokeWidth="1.8" strokeLinecap="round" />
            <path d="M4 18h8" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      <div
        className={cn(
          'fixed inset-0 z-40 bg-black/50 transition-opacity duration-200',
          isMobileSidebarOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0',
        )}
        onClick={onCloseSidebar}
      />

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-[85vw] max-w-[22rem] overflow-hidden rounded-r-xl bg-sidebar shadow-card transition-transform duration-300',
          isMobileSidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="h-full" onClick={(event) => event.stopPropagation()}>
          {mobileSidebar}
        </div>
      </aside>

      <header
        className="sticky top-0 z-20 flex shrink-0 items-center justify-between gap-3 border-b border-border/40 bg-surface/95 px-4 py-3 backdrop-blur transition-all duration-200"
        style={{ paddingLeft: 'var(--safe-left, 48px)' }}
      >
        {selectedModel && onModelChange ? (
          <ModelSelector
            models={models}
            selectedModel={selectedModel}
            onModelChange={onModelChange}
            className="max-w-[50%]"
          />
        ) : null}
        <div className="flex items-center">
          <Image
            src="/Saptiva_AI_logo_new.webp"
            alt="Saptiva AI"
            width={100}
            height={28}
            className="h-7 w-auto"
            priority
          />
        </div>
      </header>

      <main className="flex-1 min-h-0 overflow-hidden">
        {children}
      </main>

      {footer ? <div className="shrink-0 border-t border-border/40 bg-surface">{footer}</div> : null}
    </div>
  )
}

function LegacyChatShell({ sidebar, children, footer, models, selectedModel, onModelChange }: ChatShellProps) {
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
      layoutVersion: 'legacy',
    })
  }, [sidebar, handleToggleDesktopSidebar, isDesktopSidebarCollapsed])

  const mobileSidebar = React.useMemo(() => {
    if (!React.isValidElement(sidebar)) return sidebar

    return React.cloneElement(sidebar as React.ReactElement, {
      onClose: handleCloseSidebar,
      layoutVersion: 'legacy',
    })
  }, [sidebar, handleCloseSidebar])

  return (
    <div className="safe-area-top relative flex h-[100dvh] w-full overflow-hidden bg-bg text-text">
      {/* Desktop sidebar - with persistent rail */}
      <aside
        className={cn(
          'hidden h-full shrink-0 overflow-hidden transition-[width] duration-200 ease-in-out lg:flex border-r border-border bg-sidebar',
          isDesktopSidebarCollapsed ? 'lg:w-16' : 'lg:w-[288px]',
        )}
      >
        <div className="relative h-full w-full">
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
          'fixed inset-y-0 left-0 z-50 w-[85vw] max-w-[22rem] overflow-hidden rounded-r-xl bg-sidebar shadow-card transition-transform duration-300 lg:hidden',
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
            className="flex h-11 w-11 items-center justify-center rounded-full border border-border bg-surface text-text shadow-card transition hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
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
        <header
          className={cn(
            "sticky top-0 z-20 shrink-0 border-b border-border/30 bg-surface/95 backdrop-blur px-4 py-3 transition-all duration-200",
            isDesktopSidebarCollapsed && "lg:pl-24"
          )}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Model Selector - header-left según UX-001 */}
              {selectedModel && onModelChange && (
                <ModelSelector
                  models={models}
                  selectedModel={selectedModel}
                  onModelChange={onModelChange}
                  className=""
                />
              )}
            </div>
            <div className="flex items-center gap-2">
              <Image
                src="/Saptiva_AI_logo_new.webp"
                alt="Saptiva AI"
                width={120}
                height={32}
                className="h-8 w-auto"
                priority
              />
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
