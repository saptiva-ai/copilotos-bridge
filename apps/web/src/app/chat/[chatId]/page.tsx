import { Suspense } from 'react'
import { notFound } from 'next/navigation'

import { assertProdNoMock } from '../../../lib/runtime'
import { ChatView } from '../_components/ChatView'

interface ChatRouteProps {
  params: {
    chatId: string
  }
}

assertProdNoMock()

// Validate chatId format (basic UUID check)
function isValidChatId(chatId: string): boolean {
  if (!chatId || chatId === 'new' || chatId.length < 10) return false
  // Basic UUID format check - allow any reasonable chat ID format
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
  return uuidRegex.test(chatId)
}

export default function ChatRoute({ params }: ChatRouteProps) {
  const { chatId } = params

  // Validate chat ID format
  if (!isValidChatId(chatId)) {
    notFound()
  }

  return (
    <Suspense fallback={
      <div className="flex h-screen items-center justify-center">
        <p className="text-saptiva-slate">Cargando conversación...</p>
      </div>
    }>
      <ChatView initialChatId={chatId} />
    </Suspense>
  )
}
