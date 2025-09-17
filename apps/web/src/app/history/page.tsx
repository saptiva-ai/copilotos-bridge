'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Button, Card, CardHeader, CardTitle, CardContent, Badge, Input } from '../../components/ui'
import { SimpleLayout } from '../../components/layout'
import { useApiClient } from '../../lib/api-client'

interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
  model: string
  preview?: string
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filteredSessions, setFilteredSessions] = useState<ChatSession[]>([])
  const apiClient = useApiClient()

  useEffect(() => {
    loadSessions()
  }, [])

  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredSessions(sessions)
    } else {
      const query = searchQuery.toLowerCase()
      setFilteredSessions(
        sessions.filter(session => 
          session.title.toLowerCase().includes(query) ||
          session.preview?.toLowerCase().includes(query) ||
          session.model.toLowerCase().includes(query)
        )
      )
    }
  }, [sessions, searchQuery])

  const loadSessions = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getChatSessions(50, 0)
      setSessions(data.sessions || [])
    } catch (error) {
      console.error('Error loading sessions:', error)
      // Mock data for development
      const mockSessions: ChatSession[] = [
        {
          id: '1',
          title: 'API Integration Discussion',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          message_count: 15,
          model: 'saptiva-cortex',
          preview: 'Discussion about integrating FastAPI with Next.js frontend...'
        },
        {
          id: '2',
          title: 'Color Palette Implementation',
          created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          message_count: 8,
          model: 'saptiva-nexus',
          preview: 'Implementing SAPTIVA brand colors across the application...'
        },
        {
          id: '3',
          title: 'Database Schema Design',
          created_at: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
          message_count: 23,
          model: 'saptiva-ops',
          preview: 'Planning the database structure for chat sessions and research tasks...'
        }
      ]
      setSessions(mockSessions)
    } finally {
      setLoading(false)
    }
  }

  const deleteSession = async (sessionId: string) => {
    if (!confirm('Are you sure you want to delete this chat session?')) return

    try {
      await apiClient.deleteChatSession(sessionId)
      setSessions(prev => prev.filter(session => session.id !== sessionId))
    } catch (error) {
      console.error('Error deleting session:', error)
    }
  }

  const getModelBadgeColor = (model: string) => {
    switch (model) {
      case 'saptiva-cortex': return 'default'
      case 'saptiva-nexus': return 'secondary'  
      case 'saptiva-ops': return 'outline'
      default: return 'default'
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffTime = Math.abs(now.getTime() - date.getTime())
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

    if (diffDays === 1) return 'Today'
    if (diffDays === 2) return 'Yesterday'
    if (diffDays <= 7) return `${diffDays - 1} days ago`
    return date.toLocaleDateString()
  }

  return (
    <SimpleLayout>
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-saptiva-dark mb-2">
            Chat History
          </h1>
          <p className="text-saptiva-slate">
            Browse your previous conversations and continue where you left off
          </p>
        </div>

        

        {/* Sessions List */}
        {loading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <Card key={i} className="animate-pulse">
                <CardHeader>
                  <div className="h-6 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                </CardHeader>
                <CardContent>
                  <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
                  <div className="h-4 bg-gray-200 rounded w-2/3"></div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : filteredSessions.length > 0 ? (
          <div className="space-y-2">
            {filteredSessions.map((session) => (
              <Link 
                key={session.id} 
                href={`/chat?session=${session.id}`}
                className="block p-3 rounded-md hover:bg-gray-50 transition-colors"
              >
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-gray-800 truncate">{session.title}</span>
                  <span className="text-xs text-gray-500">{formatDate(session.created_at)}</span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-saptiva-mint/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-saptiva-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-saptiva-dark mb-2">
              {searchQuery ? 'No matching conversations' : 'No conversations yet'}
            </h3>
            <p className="text-saptiva-slate mb-4">
              {searchQuery 
                ? 'Try adjusting your search terms' 
                : 'Start your first conversation to see it here'}
            </p>
            <Button>
              <Link href="/chat">
                Start New Chat
              </Link>
            </Button>
          </div>
        )}

        
      </div>
    </SimpleLayout>
  )
}