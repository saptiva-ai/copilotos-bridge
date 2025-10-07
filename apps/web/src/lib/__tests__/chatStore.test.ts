import { describe, expect, beforeEach, it } from '@jest/globals'
import { useAppStore } from '../store'
import { createDefaultToolsState } from '../tool-mapping'
import type { ChatSession } from '../types'

const resetStore = () => {
  const state = useAppStore.getState()
  useAppStore.setState({
    ...state,
    chatSessions: [],
    pendingCreationId: null,
    isCreatingConversation: false,
    currentChatId: null,
    toolsEnabled: createDefaultToolsState(),
    toolsEnabledByChatId: {},
    draftToolsEnabled: createDefaultToolsState(),
  })
}

describe('chat store – optimistic conversation flow', () => {
  beforeEach(() => {
    resetStore()
  })

  it('creates an optimistic conversation and marks creation state', () => {
    const createdAt = new Date().toISOString()

    const tempId = useAppStore.getState().createConversationOptimistic('temp-test', createdAt, 'idempotent-key')
    const state = useAppStore.getState()

    expect(tempId).toBe('temp-test')
    expect(state.isCreatingConversation).toBe(true)
    expect(state.pendingCreationId).toBe('temp-test')
    expect(state.chatSessions[0]).toMatchObject({
      id: 'temp-test',
      pending: true,
      isOptimistic: true,
      state: 'creating',
      idempotency_key: 'idempotent-key',
    })
    expect((state.chatSessions[0] as any)?.tools_enabled).toEqual(state.draftToolsEnabled)
  })

  it('reconciles optimistic conversation with real session without duplicates', () => {
    const createdAt = new Date().toISOString()
    const tempId = useAppStore.getState().createConversationOptimistic(undefined, createdAt, 'reconcile-key')

    const realSession: ChatSession = {
      id: 'real-session',
      title: 'Chat real',
      created_at: createdAt,
      updated_at: createdAt,
      first_message_at: null,
      last_message_at: null,
      message_count: 0,
      model: 'turbo',
      preview: '',
      pinned: false,
      state: 'draft',
      idempotency_key: 'reconcile-key',
    }

    useAppStore.getState().reconcileConversation(tempId, realSession)
    const reconciled = useAppStore.getState()

    expect(reconciled.chatSessions).toHaveLength(1)
    expect(reconciled.chatSessions[0].id).toBe('real-session')
    expect(reconciled.chatSessions[0].pending).toBe(false)
    expect(reconciled.pendingCreationId).toBeNull()
    expect(reconciled.isCreatingConversation).toBe(false)

    // Adding the same real session again should not create duplicates
    useAppStore.getState().addChatSession(realSession)
    const afterDuplicate = useAppStore.getState()
    expect(afterDuplicate.chatSessions).toHaveLength(1)
  })

  it('removes optimistic conversation on cancellation and clears creation state', () => {
    const tempId = useAppStore.getState().createConversationOptimistic(undefined, new Date().toISOString(), 'cancel-key')
    useAppStore.getState().removeOptimisticConversation(tempId)

    const state = useAppStore.getState()
    expect(state.chatSessions).toHaveLength(0)
    expect(state.pendingCreationId).toBeNull()
    expect(state.isCreatingConversation).toBe(false)
  })
})
