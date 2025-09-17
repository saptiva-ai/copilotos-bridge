'use client'

import { useState } from 'react'
import { Button, Input, Card, CardHeader, CardTitle, CardContent, Badge } from '../../components/ui'
import { SimpleLayout } from '../../components/layout'
import { formatProgressMessage, calculateProgress } from '../../lib/streaming'
import dynamic from 'next/dynamic'

const StreamingManager = dynamic(() => import('../../components/research/StreamingManager').then(mod => mod.StreamingManager), {
  ssr: false,
})
import { useApiClient } from '../../lib/api-client'

interface ResearchTask {
  id: string
  query: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  result?: string
  created_at: string
  stream_url?: string
}

export default function ResearchPage() {
  const [query, setQuery] = useState('')
  const [tasks, setTasks] = useState<ResearchTask[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const apiClient = useApiClient()

  const startResearch = async () => {
    if (!query.trim()) return

    setIsLoading(true)
    try {
      const response = await apiClient.startDeepResearch({
        query: query.trim(),
        research_type: 'deep_research',
        stream: true,
        params: {
          depth_level: 'medium',
          max_iterations: 3,
          sources_limit: 10,
          include_citations: true
        }
      })

      const newTask: ResearchTask = {
        id: response.task_id,
        query: query.trim(),
        status: response.status as any,
        progress: 0,
        created_at: response.created_at,
        stream_url: response.stream_url
      }

      setTasks(prev => [newTask, ...prev])
      setCurrentTaskId(response.task_id)
      setQuery('')
      
    } catch (error) {
      console.error('Error starting research:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const cancelTask = async (taskId: string) => {
    try {
      await apiClient.cancelResearchTask(taskId)
      setTasks(prev => prev.map(task => 
        task.id === taskId ? { ...task, status: 'failed' } : task
      ))
      if (currentTaskId === taskId) {
        setCurrentTaskId(null)
        // disconnect()
      }
    } catch (error) {
      console.error('Error canceling task:', error)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success'
      case 'running': return 'warning'
      case 'failed': return 'destructive'
      default: return 'secondary'
    }
  }

  return (
    <SimpleLayout>
      <StreamingManager currentTaskId={currentTaskId} setTasks={setTasks} />
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-saptiva-dark mb-2">
            Deep Research
          </h1>
          <p className="text-saptiva-slate">
            Comprehensive research with multiple sources and detailed analysis
          </p>
        </div>

        {/* Research Input */}
        <Card className="mb-8">
          <CardContent className="pt-6">
            <div className="flex space-x-4">
              <Input
                placeholder="Enter your research query..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && startResearch()}
                className="flex-1"
              />
              <Button 
                onClick={startResearch}
                disabled={!query.trim() || isLoading}
                loading={isLoading}
                className="bg-saptiva-blue hover:bg-saptiva-blue/90"
              >
                Start Research
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Active Tasks */}
        <div className="space-y-4">
          {tasks.map((task) => (
            <Card key={task.id} className="border-l-4 border-l-saptiva-mint">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg mb-2">{task.query}</CardTitle>
                    <div className="flex items-center space-x-4 text-sm text-saptiva-slate">
                      <Badge variant={getStatusColor(task.status) as any} size="sm">
                        {task.status?.toUpperCase() || 'UNKNOWN'}
                      </Badge>
                      <span>{new Date(task.created_at).toLocaleString()}</span>
                      {task.progress > 0 && (
                        <span>{Math.round(task.progress * 100)}% complete</span>
                      )}
                    </div>
                  </div>
                  
                  {task.status === 'running' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => cancelTask(task.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      Cancel
                    </Button>
                  )}
                </div>
              </CardHeader>

              {task.status === 'running' && (
                <CardContent>
                  <div className="mb-2">
                    <div className="flex justify-between text-sm text-saptiva-slate mb-1">
                      <span>Progress</span>
                      <span>{Math.round(task.progress * 100)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-saptiva-mint h-2 rounded-full transition-all duration-300"
                        style={{ width: `${task.progress * 100}%` }}
                      />
                    </div>
                  </div>
                  
                  {currentTaskId === task.id && (
                    <div className="text-sm text-saptiva-slate">
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-saptiva-mint rounded-full animate-pulse"></div>
                        <span>Research in progress...</span>
                      </div>
                    </div>
                  )}
                </CardContent>
              )}

              {task.result && task.status === 'completed' && (
                <CardContent>
                  <div className="prose max-w-none">
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <p className="text-sm text-gray-600 mb-2 font-medium">Research Result:</p>
                      <div className="text-sm whitespace-pre-wrap">{task.result}</div>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          ))}

          {tasks.length === 0 && (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-saptiva-mint/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-saptiva-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-saptiva-dark mb-2">No research tasks yet</h3>
              <p className="text-saptiva-slate">Start your first research query above</p>
            </div>
          )}
        </div>

        {/* Research Tips */}
        <Card className="mt-8 border-saptiva-blue/20 bg-secondary-50">
          <CardHeader>
            <CardTitle className="text-saptiva-blue">💡 Research Tips</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-saptiva-slate">
            <ul className="space-y-1">
              <li>• Be specific in your queries for better results</li>
              <li>• Research tasks can take several minutes to complete</li>
              <li>• Results include citations and source links</li>
              <li>• You can run multiple research tasks simultaneously</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </SimpleLayout>
  )
}