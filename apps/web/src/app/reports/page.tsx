'use client'

import { useState, useEffect, useCallback } from 'react'
import { Button, Card, CardHeader, CardTitle, CardContent, Badge, Input } from '../../components/ui'
import { SimpleLayout } from '../../components/layout'
import { useApiClient } from '../../lib/api-client'
import { useRequireAuth } from '../../hooks/useRequireAuth'

interface Report {
  id: string
  title: string
  task_id: string
  format: 'md' | 'pdf' | 'docx' | 'html'
  size: number
  created_at: string
  sources_count: number
  pages?: number
  status: 'generating' | 'ready' | 'error'
}

type ApiTask = {
  task_id: string
  status: string
  task_type: string
  query?: string
  created_at?: string
}

export default function ReportsPage() {
  const { isAuthenticated, isHydrated } = useRequireAuth()
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filteredReports, setFilteredReports] = useState<Report[]>([])
  const [selectedFormat, setSelectedFormat] = useState<string>('all')
  const [error, setError] = useState<string | null>(null)
  const apiClient = useApiClient()

  useEffect(() => {
    let filtered = reports
    
    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(report => 
        report.title.toLowerCase().includes(query)
      )
    }
    
    // Filter by format
    if (selectedFormat !== 'all') {
      filtered = filtered.filter(report => report.format === selectedFormat)
    }
    
    setFilteredReports(filtered)
  }, [reports, searchQuery, selectedFormat])

  const loadReports = useCallback(async () => {
    if (!isAuthenticated) return
    try {
      setLoading(true)
      setError(null)
      const data = await apiClient.getUserTasks(50, 0)
      const tasks = (data?.tasks || []) as ApiTask[]
      const normalizedReports: Report[] = tasks
        .filter((task) => task.task_type === 'deep_research')
        .map((task: ApiTask) => {
          const status = task.status === 'completed'
            ? 'ready'
            : task.status === 'failed' || task.status === 'cancelled'
              ? 'error'
              : 'generating'

          return {
            id: task.task_id,
            title: task.query || `Research Task ${task.task_id}`,
            task_id: task.task_id,
            format: 'md',
            size: 0,
            created_at: task.created_at || new Date().toISOString(),
            sources_count: 0,
            status,
          }
        })

      setReports(normalizedReports)
    } catch (error) {
      console.error('Error loading reports:', error)
      setReports([])
      setError('Unable to load reports right now. Please try again later.')
    } finally {
      setLoading(false)
    }
  }, [apiClient, isAuthenticated])

  useEffect(() => {
    if (isAuthenticated) {
      loadReports()
    }
  }, [loadReports, isAuthenticated])

  const downloadReport = async (reportId: string, format: string, title: string) => {
    try {
      const blob = await apiClient.downloadReport(reportId, format, true)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url
      a.download = `${title}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Error downloading report:', error)
      // Mock download for development
      alert(`Downloading ${title}.${format} (Mock)`)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ready': return { variant: 'success' as const, text: 'Ready' }
      case 'generating': return { variant: 'warning' as const, text: 'Generating' }
      case 'error': return { variant: 'error' as const, text: 'Error' }
      default: return { variant: 'secondary' as const, text: status }
    }
  }

  const getFormatIcon = (format: string) => {
    switch (format) {
      case 'pdf':
        return (
          <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
          </svg>
        )
      case 'docx':
        return (
          <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
          </svg>
        )
      case 'html':
        return (
          <svg className="w-5 h-5 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 110 2H4a1 1 0 01-1-1zM14 9a1 1 0 100 2h2a1 1 0 100-2h-2zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" />
          </svg>
        )
      default:
        return (
          <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
          </svg>
        )
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (!isHydrated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-saptiva-slate">Preparando tus reportes...</p>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <SimpleLayout>
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-saptiva-dark mb-2">
            Research Reports
          </h1>
          <p className="text-saptiva-slate">
            Download and manage your research reports in various formats
          </p>
        </div>

        {error && (
          <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Search and Filter */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex space-x-4">
              <Input
                placeholder="Search reports..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1"
              />
              
              <select
                value={selectedFormat}
                onChange={(e) => setSelectedFormat(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                <option value="all">All Formats</option>
                <option value="pdf">PDF</option>
                <option value="docx">Word</option>
                <option value="md">Markdown</option>
                <option value="html">HTML</option>
              </select>
              
              <Button variant="outline" onClick={loadReports}>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Reports List */}
        {loading ? (
          <div className="grid gap-4">
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
        ) : filteredReports.length > 0 ? (
          <div className="grid gap-4">
            {filteredReports.map((report) => (
              <Card key={report.id} className="hover:shadow-md transition-shadow border-l-4 border-l-saptiva-mint">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3">
                      {getFormatIcon(report.format)}
                      <div className="flex-1">
                        <CardTitle className="text-lg mb-2">{report.title}</CardTitle>
                        <div className="flex items-center space-x-4 text-sm text-saptiva-slate">
                          <Badge variant={getStatusBadge(report.status).variant} size="sm">
                            {getStatusBadge(report.status).text}
                          </Badge>
                          <span className="uppercase font-medium">{report.format}</span>
                          <span>{formatFileSize(report.size)}</span>
                          <span>{report.sources_count} sources</span>
                          {report.pages && <span>{report.pages} pages</span>}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      {report.status === 'ready' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => downloadReport(report.id, report.format, report.title)}
                          className="text-saptiva-blue hover:text-saptiva-blue/80"
                        >
                          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          Download
                        </Button>
                      )}
                      
                      {report.status === 'generating' && (
                        <div className="flex items-center space-x-2 text-sm text-saptiva-slate">
                          <div className="w-4 h-4 border-2 border-saptiva-mint border-t-transparent rounded-full animate-spin"></div>
                          <span>Generating...</span>
                        </div>
                      )}
                    </div>
                  </div>
                </CardHeader>

                <CardContent>
                  <div className="text-sm text-saptiva-slate">
                    <div className="flex justify-between items-center">
                      <span>Created: {formatDate(report.created_at)}</span>
                      <span>Task ID: {report.task_id}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-saptiva-mint/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-saptiva-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-saptiva-dark mb-2">
              {searchQuery || selectedFormat !== 'all' ? 'No matching reports' : 'No reports yet'}
            </h3>
            <p className="text-saptiva-slate mb-4">
              {searchQuery || selectedFormat !== 'all'
                ? 'Try adjusting your search or filter criteria'
                : 'Complete a research task to generate your first report'}
            </p>
            <Button>
              <a href="/research">
                Start Research
              </a>
            </Button>
          </div>
        )}

        {/* Format Information */}
        <Card className="mt-8 border-saptiva-blue/20 bg-secondary-50">
          <CardHeader>
            <CardTitle className="text-saptiva-blue">📄 Report Formats</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-saptiva-slate">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium text-saptiva-dark mb-2">Available Formats:</h4>
                <ul className="space-y-1">
                  <li>• <strong>PDF</strong> - Professional, print-ready format</li>
                  <li>• <strong>Word (DOCX)</strong> - Editable document format</li>
                  <li>• <strong>Markdown</strong> - Developer-friendly text format</li>
                  <li>• <strong>HTML</strong> - Web-ready format with styling</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium text-saptiva-dark mb-2">Features:</h4>
                <ul className="space-y-1">
                  <li>• Source citations and references</li>
                  <li>• Structured content with headings</li>
                  <li>• Research metadata included</li>
                  <li>• Multiple download options</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </SimpleLayout>
  )
}
