import { Suspense } from 'react'

import { assertProdNoMock } from '../../lib/runtime'
import { ChatView } from './_components/ChatView'

assertProdNoMock()

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatView />
    </Suspense>
  )
}
