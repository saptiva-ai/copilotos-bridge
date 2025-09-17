'use client'

import * as React from 'react'
import { useSearchParams } from 'next/navigation'
import { ChatLayout } from '../../components/layout'
import { ChatMessage } from '../../lib/types'
import { 
  ChatInterface, 
  ChatWelcomeMessage, 
  ModelSelector, 
  ToolsPanel, 
} from '../../components/chat'
import { Card, CardHeader, CardContent } from '../../components/ui'
import { useChat, useUI } from '../../lib/store'

function ChatPageContent() {
  const searchParams = useSearchParams()
  const sessionId = searchParams?.get('session')
  
  // Use Zustand store instead of local state
  const {
    messages,
    isLoading,
    selectedModel,
    toolsEnabled,
    sendMessage,
    startNewChat,
    setSelectedModel,
    addMessage,
    clearMessages,
    setLoading,
    toggleTool,
  } = useChat()
  
  const { checkConnection } = useUI()

  // Load session if provided in URL
  React.useEffect(() => {
    if (sessionId && sessionId !== 'new') {
      // Load existing session - implement when API is ready
      console.log('Loading session:', sessionId)
    } else if (!sessionId || sessionId === 'new') {
      startNewChat()
    }
  }, [sessionId, startNewChat])

  // Check API connection on mount
  React.useEffect(() => {
    checkConnection()
  }, [checkConnection])

  // Mock function to simulate API call
  const simulateAPIResponse = async (userMessage: string): Promise<string> => {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000))
    
    // Mock responses based on content
    if (userMessage.toLowerCase().includes('research') || toolsEnabled.deepResearch) {
      return `I'll help you with comprehensive research on "${userMessage}".

Based on my analysis using ${toolsEnabled.deepResearch ? 'deep research capabilities' : 'available information'}:

**Key Findings:**
- This is a complex topic that requires careful consideration
- There are multiple perspectives to explore
- Current developments suggest ongoing evolution

**Sources Analyzed:** ${toolsEnabled.deepResearch ? '15 academic papers, 8 news articles' : '5 general sources'}

**Recommendations:**
1. Consider multiple viewpoints on this topic
2. Stay updated with recent developments
3. Cross-reference information from reliable sources

Would you like me to dive deeper into any specific aspect of this topic?`
    }
    
    return `Thanks for your message: "${userMessage}"

I'm using the ${selectedModel} model to provide this response. ${toolsEnabled.webSearch ? 'I also searched the web for current information.' : ''}

This is a mock response to demonstrate the chat interface. In a real implementation, this would be connected to the actual API backend that communicates with the Saptiva models.

Some key points about your query:
- It's an interesting question that deserves thoughtful consideration
- There are multiple angles we could explore
- I'm happy to dive deeper into any specific aspects

How can I help you further?`
  }

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return

    // Add user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    }

    addMessage(userMessage)
    setLoading(true)

    try {
      // Simulate API call
      const response = await simulateAPIResponse(message)
      
      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response,
        timestamp: new Date().toISOString(),
        model: selectedModel,
        tokens: Math.floor(Math.random() * 500) + 100, // Mock token count
        latency: Math.floor(Math.random() * 2000) + 500, // Mock latency
      }

      addMessage(assistantMessage)
    } catch (error) {
      // Add error message
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error while processing your message. Please try again.',
        timestamp: new Date().toISOString(),
        model: selectedModel,
        isError: true,
      }

      addMessage(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleRetryMessage = async (messageId: string) => {
    // Find the failed message and the user message before it
    const messageIndex = messages.findIndex(m => m.id === messageId)
    if (messageIndex > 0) {
      const userMessage = messages[messageIndex - 1]
      if (userMessage.role === 'user') {
        // Retry with the user's message
        await handleSendMessage(userMessage.content)
      }
    }
  }

  const handleCopyMessage = (text: string) => {
    // The copyToClipboard function in the component will handle this
    console.log('Message copied:', text.substring(0, 50) + '...')
  }

  return (
    <ChatLayout>
      <div className="h-screen flex">
        {/* Main chat area */}
        <div className="flex-1 flex flex-col">
          <ChatInterface
            messages={messages}
            onSendMessage={handleSendMessage}
            onRetryMessage={handleRetryMessage}
            onCopyMessage={handleCopyMessage}
            loading={isLoading}
            welcomeMessage={<ChatWelcomeMessage />}
          />
        </div>

        {/* Right sidebar with controls */}
        <div className="w-80 border-l border-gray-200 bg-gray-50 p-4 space-y-4 overflow-y-auto">
          {/* Model Selection */}
          <Card>
            <CardHeader className="pb-3">
              <h3 className="font-semibold text-gray-900">Model</h3>
            </CardHeader>
            <CardContent>
              <ModelSelector
                selectedModel={selectedModel}
                onModelChange={setSelectedModel}
                disabled={isLoading}
              />
            </CardContent>
          </Card>

          {/* Tools Configuration */}
          <Card>
            <CardHeader className="pb-3">
              <h3 className="font-semibold text-gray-900">Tools & Research</h3>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Object.entries(toolsEnabled).map(([toolName, enabled]) => (
                  <div key={toolName} className="flex items-center justify-between">
                    <label className="text-sm font-medium text-gray-700 capitalize">
                      {toolName.replace('_', ' ')}
                    </label>
                    <button
                      onClick={() => toggleTool(toolName)}
                      disabled={isLoading}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        enabled ? 'bg-saptiva-mint' : 'bg-gray-200'
                      } ${isLoading ? 'opacity-50' : ''}`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                          enabled ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Chat Statistics */}
          <Card>
            <CardHeader className="pb-3">
              <h3 className="font-semibold text-gray-900">Session Stats</h3>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Messages:</span>
                  <span className="font-medium">{messages.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Current model:</span>
                  <span className="font-medium">{selectedModel?.replace('saptiva-', '')?.toUpperCase() || 'UNKNOWN'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Tools active:</span>
                  <span className="font-medium">
                    {Object.values(toolsEnabled).filter(Boolean).length || 'None'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader className="pb-3">
              <h3 className="font-semibold text-gray-900">Quick Actions</h3>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <button 
                  className="w-full text-left text-sm text-gray-600 hover:text-primary-600 transition-colors"
                  onClick={() => clearMessages()}
                  disabled={isLoading}
                >
                  🗑️ Clear chat
                </button>
                <button 
                  className="w-full text-left text-sm text-gray-600 hover:text-primary-600 transition-colors"
                  disabled={messages.length === 0 || isLoading}
                >
                  💾 Save conversation
                </button>
                <button 
                  className="w-full text-left text-sm text-gray-600 hover:text-primary-600 transition-colors"
                  disabled={messages.length === 0 || isLoading}
                >
                  📤 Export chat
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </ChatLayout>
  )
}

export default function ChatPage() {
  return (
    <React.Suspense fallback={<div>Loading...</div>}>
      <ChatPageContent />
    </React.Suspense>
  )
}