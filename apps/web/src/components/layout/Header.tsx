'use client'

import * as React from 'react'
import Link from 'next/link'
import { Button } from '../ui'
import { cn } from '../../lib/utils'

interface HeaderProps {
  className?: string
}

export function Header({ className }: HeaderProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false)

  return (
    <header className={cn('sticky top-0 z-40 w-full border-b border-gray-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60', className)}>
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        {/* Logo */}
        <div className="flex items-center">
          <Link href="/" className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-md bg-saptiva-mint flex items-center justify-center">
              <span className="text-saptiva-dark font-bold text-sm">S</span>
            </div>
            <span className="font-bold text-xl text-saptiva-dark">SAPTIVA CopilotOS</span>
          </Link>
        </div>

        {/* Navigation - Desktop */}
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

        {/* Actions */}
        <div className="flex items-center space-x-4">
          {/* User menu */}
          <div className="hidden md:flex items-center space-x-2">
            <Button variant="ghost" size="sm">
              <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              User
            </Button>
            <Button variant="ghost" size="sm">
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </Button>
          </div>

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
              <Button variant="ghost" size="sm" className="w-full justify-start">
                <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                User Profile
              </Button>
              <Button variant="ghost" size="sm" className="w-full justify-start">
                <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Settings
              </Button>
            </div>
          </div>
        </div>
      )}
    </header>
  )
}