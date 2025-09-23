'use client'

import * as React from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

import { Button } from '../ui'
import { cn } from '../../lib/utils'

import { useChat } from '../../lib/store'
import { ModelSelector } from '../chat'
import { useAuthStore } from '../../lib/auth-store'

interface HeaderProps {
  className?: string
}

export function Header({ className }: HeaderProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false)
  const router = useRouter()
  const {
    selectedModel,
    setSelectedModel,
    isLoading,
  } = useChat()
  const { user, accessToken, isHydrated, logout } = useAuthStore((state) => ({
    user: state.user,
    accessToken: state.accessToken,
    isHydrated: state.isHydrated,
    logout: state.logout,
  }))

  const isAuthenticated = React.useMemo(
    () => Boolean(isHydrated && accessToken && user),
    [isHydrated, accessToken, user]
  )

  const userInitials = React.useMemo(() => {
    if (!user?.username) return 'US'
    const parts = user.username.split(/[._-]/).filter(Boolean)
    if (parts.length >= 2) {
      return `${parts[0][0] ?? ''}${parts[1][0] ?? ''}`.toUpperCase()
    }
    return user.username.slice(0, 2).toUpperCase()
  }, [user])

  const handleLogout = React.useCallback(() => {
    logout()
    router.replace('/login')
  }, [logout, router])

  return (
    <header className={cn('sticky top-0 z-40 w-full border-b border-gray-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60', className)}>
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        {/* Logo */}
        <div className="flex items-center">
          <Link href="/" className="flex items-center space-x-2">
            <img
              src="/Saptiva_Logo-05.png"
              alt="Saptiva Logo"
              className="h-8 w-auto"
            />
            <span className="font-bold text-xl text-saptiva-dark">Saptiva CopilotOS</span>
          </Link>
        </div>

        {/* Navigation - Desktop */}
        {isAuthenticated && (
          <nav className="hidden md:flex items-center space-x-6 text-sm font-medium">
          <Link 
            href="/chat" 
            className="text-saptiva-slate transition-colors hover:text-saptiva-mint"
          >
            Chat
          </Link>
          <Link 
            href="/research" 
            className="text-saptiva-slate transition-colors hover:text-saptiva-mint"
          >
            Research
          </Link>
          <Link 
            href="/history" 
            className="text-saptiva-slate transition-colors hover:text-saptiva-mint"
          >
            History
          </Link>
          <Link 
            href="/reports" 
            className="text-saptiva-slate transition-colors hover:text-saptiva-mint"
          >
            Reports
          </Link>
        </nav>
        )}

        {/* Actions */}
        <div className="flex items-center space-x-4">
          {isAuthenticated && (
            <ModelSelector
              selectedModel={selectedModel}
              onModelChange={setSelectedModel}
              disabled={isLoading}
            />
          )}

          {isAuthenticated ? (
            <div className="hidden items-center space-x-3 md:flex">
              <div className="flex items-center space-x-3 rounded-full bg-saptiva-light/20 px-3 py-1">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-saptiva-blue text-sm font-semibold text-white">
                  {userInitials}
                </span>
                <div className="flex flex-col text-left">
                  <span className="text-sm font-semibold text-saptiva-slate">{user?.username}</span>
                  <span className="text-xs text-saptiva-slate/70">{user?.email}</span>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={handleLogout}>
                Cerrar sesión
              </Button>
            </div>
          ) : (
            <div className="hidden items-center space-x-3 md:flex">
              <Link href="/login" className="text-sm font-semibold text-saptiva-blue hover:text-saptiva-mint">
                Iniciar sesión
              </Link>
              <Link
                href="/register"
                className="rounded-full bg-saptiva-blue px-4 py-2 text-sm font-semibold text-white hover:bg-saptiva-lightBlue"
              >
                Crear cuenta
              </Link>
            </div>
          )}

          {/* Mobile menu button */}
          <Button
            variant="ghost"
            size="sm"
            className="md:hidden"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </Button>
        </div>
      </div>

      {/* Mobile menu */}
      {isMobileMenuOpen && (
        <div className="border-t border-gray-200 md:hidden">
          <div className="px-4 py-6 space-y-4">
            {isAuthenticated ? (
              <>
                <Link 
                  href="/chat"
                  className="block text-saptiva-slate hover:text-saptiva-mint transition-colors"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Chat
                </Link>
                <Link 
                  href="/research"
                  className="block text-saptiva-slate hover:text-saptiva-mint transition-colors"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Research
                </Link>
                <Link 
                  href="/history"
                  className="block text-saptiva-slate hover:text-saptiva-mint transition-colors"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  History
                </Link>
                <Link 
                  href="/reports"
                  className="block text-saptiva-slate hover:text-saptiva-mint transition-colors"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Reports
                </Link>
                <div className="border-t border-gray-200 pt-4">
                  <div className="mb-3 flex items-center space-x-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-full bg-saptiva-blue text-sm font-semibold text-white">
                      {userInitials}
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-saptiva-slate">{user?.username}</p>
                      <p className="text-xs text-saptiva-slate/70">{user?.email}</p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-center"
                    onClick={() => {
                      setIsMobileMenuOpen(false)
                      handleLogout()
                    }}
                  >
                    Cerrar sesión
                  </Button>
                </div>
              </>
            ) : (
              <>
                <Link 
                  href="/login"
                  className="block text-saptiva-slate hover:text-saptiva-mint transition-colors"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Iniciar sesión
                </Link>
                <Link 
                  href="/register"
                  className="block text-saptiva-slate hover:text-saptiva-mint transition-colors"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Crear cuenta
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  )
}
