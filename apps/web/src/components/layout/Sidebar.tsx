'use client'

import * as React from 'react'
import Link from 'next/link'

import { Button } from '../ui'
import { cn } from '../../lib/utils'

interface SidebarProps {
  isOpen: boolean
  onClose?: () => void
  className?: string
}



export function Sidebar({ isOpen, onClose, className }: SidebarProps) {
  return (
    <>
      {/* Backdrop for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 z-20 bg-black bg-opacity-50 xl:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-16 z-30 h-[calc(100vh-4rem)] w-64 transform bg-white border-r border-gray-200 transition-transform duration-200 ease-in-out lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full',
          className
        )}
      >
        <div className="flex h-full flex-col">
          {/* New Chat Button */}
          <div className="p-4">
            <Button className="w-full justify-start">
              <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
              </svg>
              New Chat
            </Button>
          </div>

          <div className="flex-1 px-4 overflow-y-auto">
            <h3 className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Recent Chats
            </h3>
            <ul className="space-y-1">
              {/* Mock recent chats - these would come from a store/API */}
              {[
                { id: '1', title: 'AI Development Best Practices', time: '2m ago' },
                { id: '2', title: 'Quantum Computing Research', time: '1h ago' },
                { id: '3', title: 'Machine Learning Algorithms', time: '3h ago' },
                { id: '4', title: 'Web Development Trends', time: '1d ago' },
              ].map((chat) => (
                <li key={chat.id}>
                  <Link
                    href={`/chat/${chat.id}`}
                    className="block px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900 rounded-md group"
                    onClick={onClose}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate flex-1">{chat.title}</span>
                      <span className="ml-2 text-xs text-gray-400 group-hover:text-gray-600">
                        {chat.time}
                      </span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </aside>
    </>
  )
}