'use client'

import * as React from 'react'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { cn } from '../../lib/utils'

interface AppLayoutProps {
  children: React.ReactNode
  showSidebar?: boolean
  className?: string
}

export function AppLayout({ children, showSidebar = true, className }: AppLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = React.useState(false)

  return (
    <div className="h-screen bg-gray-50 flex flex-col overflow-hidden">
      <Header />

      <div className="flex flex-1 overflow-hidden">
        {showSidebar && (
          <Sidebar
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
          />
        )}

        <main
          className={cn(
            'flex-1 transition-all duration-200 ease-in-out overflow-hidden',
            showSidebar && 'xl:ml-64', // Sidebar colapsa en ≤1024px (xl: 1280px+)
            className
          )}
        >
          <div className="p-6 h-full overflow-y-auto">
            {children}
          </div>
        </main>
      </div>

      {/* Mobile sidebar toggle button */}
      {showSidebar && (
        <button
          type="button"
          className="fixed bottom-4 left-4 z-40 rounded-full bg-primary-600 p-3 text-white shadow-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 xl:hidden"
          onClick={() => setSidebarOpen(true)}
        >
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      )}
    </div>
  )
}

// Layout components for different pages
export function ChatLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppLayout showSidebar={true} className="p-0">
      {children}
    </AppLayout>
  )
}

export function SimpleLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppLayout showSidebar={false}>
      {children}
    </AppLayout>
  )
}