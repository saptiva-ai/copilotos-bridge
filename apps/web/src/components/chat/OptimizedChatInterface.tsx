import React, { memo, useMemo, useCallback, useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'
import type { ChatMessage } from '@/lib/types'
import { useVirtualizedList } from '@/hooks/useVirtualizedList'
import { usePerformanceOptimization } from '@/hooks/usePerformanceOptimization'

interface OptimizedChatInterfaceProps {
  messages: ChatMessage[]
  isLoading: boolean
  onSendMessage: (message: string) => void
  className?: string
}

// Componente de mensaje memoizado para evitar re-renders innecesarios
const OptimizedChatMessage = memo<{
  message: ChatMessage
  virtualIndex: number
}>(({ message, virtualIndex }) => {
  // Memoizar el contenido del mensaje si no ha cambiado
  const messageContent = useMemo(
    () => ({
      content: message.content,
      role: message.role,
      timestamp: message.timestamp,
      status: message.status
    }),
    [message.content, message.role, message.timestamp, message.status]
  )

  const isUser = messageContent.role === 'user'
  const isStreaming = message.isStreaming

  return (
    <div
      className={cn(
        'flex w-full mb-4 px-4',
        isUser ? 'justify-end' : 'justify-start'
      )}
      data-virtual-index={virtualIndex}
    >
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-2',
          isUser
            ? 'bg-blue-500 text-white'
            : 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100'
        )}
      >
        <div className="whitespace-pre-wrap">
          {messageContent.content}
          {isStreaming && (
            <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
          )}
        </div>
        {messageContent.timestamp && (
          <div className={cn(
            'text-xs mt-1 opacity-70',
            isUser ? 'text-blue-100' : 'text-gray-500'
          )}>
            {messageContent.timestamp instanceof Date
              ? messageContent.timestamp.toLocaleTimeString()
              : new Date(messageContent.timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  )
}, (prevProps, nextProps) => {
  // Comparación optimizada para determinar si debe re-renderizar
  const prevMsg = prevProps.message
  const nextMsg = nextProps.message

  return (
    prevMsg.id === nextMsg.id &&
    prevMsg.content === nextMsg.content &&
    prevMsg.status === nextMsg.status &&
    prevMsg.isStreaming === nextMsg.isStreaming &&
    (prevMsg.timestamp instanceof Date ? prevMsg.timestamp.getTime() : prevMsg.timestamp) === (nextMsg.timestamp instanceof Date ? nextMsg.timestamp.getTime() : nextMsg.timestamp) &&
    prevProps.virtualIndex === nextProps.virtualIndex
  )
})

OptimizedChatMessage.displayName = 'OptimizedChatMessage'

// Componente principal optimizado
export const OptimizedChatInterface = memo<OptimizedChatInterfaceProps>(({
  messages,
  isLoading,
  onSendMessage,
  className
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const [inputValue, setInputValue] = React.useState('')

  const { createAdvancedDebounce, scheduleTask } = usePerformanceOptimization()

  // Configuración de virtualización
  const ITEM_HEIGHT = 80 // Altura estimada por mensaje
  const CONTAINER_HEIGHT = 600 // Altura del contenedor de chat

  const virtualizedList = useVirtualizedList({
    itemHeight: ITEM_HEIGHT,
    containerHeight: CONTAINER_HEIGHT,
    overscan: 5,
    items: messages
  })

  // Auto-scroll optimizado con debounce
  const debouncedScrollToBottom = useMemo(() => createAdvancedDebounce(
    () => {
      if (containerRef.current) {
        containerRef.current.scrollTop = containerRef.current.scrollHeight
      }
    },
    100,
    { trailing: true }
  ), [createAdvancedDebounce])

  // Efecto para scroll automático cuando llegan nuevos mensajes
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1]
      if (lastMessage.role === 'assistant' || lastMessage.isStreaming) {
        scheduleTask(debouncedScrollToBottom, 'normal')
      }
    }
  }, [messages, debouncedScrollToBottom, scheduleTask])

  // Handler optimizado para envío de mensajes
  const handleSendMessage = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue.trim())
      setInputValue('')

      // Enfocar el input después del envío
      scheduleTask(() => {
        inputRef.current?.focus()
      }, 'high')
    }
  }, [inputValue, isLoading, onSendMessage, scheduleTask])

  // Handler optimizado para cambios en el input
  const debouncedInputChange = useMemo(() => createAdvancedDebounce(
    (value: string) => {
      setInputValue(value)
    },
    16, // ~60fps para una experiencia fluida
    { leading: true, trailing: true }
  ), [createAdvancedDebounce])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    debouncedInputChange(e.target.value)
  }, [debouncedInputChange])

  // Renderizar mensajes virtualizados
  const virtualizedMessages = useMemo(
    () => virtualizedList.visibleItems.map((message, index) => (
      <OptimizedChatMessage
        key={message.id}
        message={message}
        virtualIndex={message.virtualIndex}
      />
    )),
    [virtualizedList.visibleItems]
  )

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Área de mensajes con virtualización */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto relative"
        style={{ height: CONTAINER_HEIGHT }}
        onScroll={virtualizedList.handleScroll}
      >
        {/* Contenedor virtual con altura total */}
        <div style={{ height: virtualizedList.totalHeight, position: 'relative' }}>
          {/* Contenido visible con offset */}
          <div
            style={{
              transform: `translateY(${virtualizedList.offsetY}px)`,
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0
            }}
          >
            {virtualizedMessages}
          </div>
        </div>

        {/* Indicador de carga */}
        {isLoading && (
          <div className="flex justify-center py-4">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
            </div>
          </div>
        )}
      </div>

      {/* Formulario de entrada optimizado */}
      <form onSubmit={handleSendMessage} className="p-4 border-t">
        <div className="flex space-x-2">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={handleInputChange}
            placeholder="Escribe tu mensaje..."
            className="flex-1 resize-none rounded-lg border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={1}
            disabled={isLoading}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSendMessage(e as any)
              }
            }}
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isLoading}
            className={cn(
              'px-4 py-2 rounded-lg font-medium transition-colors',
              inputValue.trim() && !isLoading
                ? 'bg-blue-500 text-white hover:bg-blue-600'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            )}
          >
            Enviar
          </button>
        </div>
      </form>
    </div>
  )
})

OptimizedChatInterface.displayName = 'OptimizedChatInterface'
