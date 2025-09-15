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

        {/* Search and Filter */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex space-x-4">
              <Input
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1"
              />
              <Button variant="outline" onClick={loadSessions}>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </Button>
            </div>
          </CardContent>
        </Card>

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
          <div className="space-y-4">
            {filteredSessions.map((session) => (
              <Card key={session.id} className="hover:shadow-md transition-shadow border-l-4 border-l-saptiva-mint">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg mb-2">
                        <Link 
                          href={`/chat?session=${session.id}`}
                          className="hover:text-saptiva-blue transition-colors"
                        >
                          {session.title}
                        </Link>
                      </CardTitle>
                      <div className="flex items-center space-x-4 text-sm text-saptiva-slate">
                        <Badge variant={getModelBadgeColor(session.model) as any} size="sm">
                          {session.model.toUpperCase()}
                        </Badge>
                        <span>{session.message_count} messages</span>
                        <span>{formatDate(session.created_at)}</span>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        asChild
                        className="text-saptiva-blue hover:text-saptiva-blue/80"
                      >
                        <Link href={`/chat?session=${session.id}`}>
                          Continue
                        </Link>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteSession(session.id)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </Button>
                    </div>
                  </div>
                </CardHeader>

                {session.preview && (
                  <CardContent>
                    <p className="text-sm text-saptiva-slate line-clamp-2">
                      {session.preview}
                    </p>
                  </CardContent>
                )}
              </Card>
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
            <Button asChild>
              <Link href="/chat">
                Start New Chat
              </Link>
            </Button>
          </div>
        )}

        {/* Statistics */}
        {!loading && filteredSessions.length > 0 && (
          <Card className="mt-8 border-saptiva-blue/20 bg-secondary-50">
            <CardHeader>
              <CardTitle className="text-saptiva-blue">📊 Usage Statistics</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-saptiva-slate">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="font-medium text-saptiva-dark">{sessions.length}</div>
                  <div>Total Conversations</div>
                </div>
                <div>
                  <div className="font-medium text-saptiva-dark">
                    {sessions.reduce((acc, s) => acc + s.message_count, 0)}
                  </div>
                  <div>Total Messages</div>
                </div>
                <div>
                  <div className="font-medium text-saptiva-dark">
                    {Math.round(sessions.reduce((acc, s) => acc + s.message_count, 0) / sessions.length || 0)}
                  </div>
                  <div>Avg per Session</div>
                </div>
                <div>
                  <div className="font-medium text-saptiva-dark">
                    {sessions.filter(s => s.created_at > new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()).length}
                  </div>
                  <div>This Week</div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </SimpleLayout>
  )
}