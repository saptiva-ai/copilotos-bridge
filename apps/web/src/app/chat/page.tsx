import { Suspense } from 'react'

import { assertProdNoMock } from '../../lib/runtime'
import { ChatView } from './_components/ChatView'

export const dynamic = 'force-dynamic'

assertProdNoMock()

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatView />
    </Suspense>
  )
}
