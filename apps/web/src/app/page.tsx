'use client'

import Link from 'next/link'
import { Button, Card, CardHeader, CardTitle, CardContent, Badge } from '../components/ui'
import { SimpleLayout } from '../components/layout'

export default function Home() {
  return (
    <SimpleLayout>
      <div className="max-w-4xl mx-auto">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <div className="flex justify-center mb-6">
            <img
              src="/Saptiva_Logo-05.png"
              alt="Saptiva Logo"
              className="h-16 w-auto"
            />
          </div>
          <h1 className="text-4xl font-bold text-saptiva-dark mb-4">
            Saptiva CopilotOS
          </h1>
          <p className="text-xl text-saptiva-slate mb-8">
            A unified conversational interface combining direct LLM interactions 
            with deep research capabilities powered by Aletheia orchestrator.
          </p>
          <div className="flex justify-center space-x-4">
            <Link href="/chat">
              <Button size="lg" className="px-8">
                Start Chatting
                <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </Button>
            </Link>
            <Link href="/research">
              <Button variant="outline" size="lg" className="px-8">
                Deep Research
                <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </Button>
            </Link>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          <Card>
            <CardHeader>
              <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-saptiva-mint" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <CardTitle>Quick Chat</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Ask questions and get instant AI responses using powerful Saptiva models.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="w-12 h-12 bg-secondary-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-saptiva-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <CardTitle>Deep Research</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Comprehensive research with multiple sources, iterations, and detailed analysis.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-saptiva-orange" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 00-2-2z" />
                </svg>
              </div>
              <CardTitle>Real-time Streaming</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Watch research progress in real-time with live updates and streaming responses.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Available Models */}
        <Card className="mb-12">
          <CardHeader>
            <CardTitle>Available Models</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid sm:grid-cols-3 gap-4">
              <div className="flex items-center space-x-3 p-3 bg-primary-50 rounded-lg border border-primary-200">
                <div className="w-3 h-3 bg-saptiva-mint rounded-full"></div>
                <div>
                  <div className="font-medium text-saptiva-dark">SAPTIVA Cortex</div>
                  <div className="text-sm text-saptiva-slate">General purpose</div>
                </div>
                <Badge variant="success" size="sm">Available</Badge>
              </div>
              <div className="flex items-center space-x-3 p-3 bg-secondary-50 rounded-lg border border-secondary-200">
                <div className="w-3 h-3 bg-saptiva-blue rounded-full"></div>
                <div>
                  <div className="font-medium text-saptiva-dark">SAPTIVA Ops</div>
                  <div className="text-sm text-saptiva-slate">Operations</div>
                </div>
                <Badge variant="success" size="sm">Available</Badge>
              </div>
              <div className="flex items-center space-x-3 p-3 bg-orange-50 rounded-lg border border-orange-200">
                <div className="w-3 h-3 bg-saptiva-orange rounded-full"></div>
                <div>
                  <div className="font-medium text-saptiva-dark">SAPTIVA Nexus</div>
                  <div className="text-sm text-saptiva-slate">Advanced reasoning</div>
                </div>
                <Badge variant="success" size="sm">Available</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Status */}
        <Card>
          <CardHeader>
            <CardTitle>🚀 System Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">✅ Completed</h4>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Next.js frontend with TypeScript</li>
                  <li>• Component system with Tailwind CSS</li>
                  <li>• Chat interface with real-time streaming</li>
                  <li>• Model selection and tools configuration</li>
                  <li>• FastAPI backend with all endpoints</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium text-gray-900 mb-2">🔧 Ready to Configure</h4>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Environment variables</li>
                  <li>• Database connection (MongoDB)</li>
                  <li>• Redis for caching</li>
                  <li>• Aletheia orchestrator integration</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </SimpleLayout>
  )
}