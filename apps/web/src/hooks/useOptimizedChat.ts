import { useState, useCallback, useRef, useEffect } from 'react'
import { useAppStore } from '../lib/store'
import type { ChatMessage } from '../lib/types'

interface UseOptimizedChatOptions {
  enablePredictiveLoading?: boolean
  enableResponseCache?: boolean
  streamingChunkSize?: number
}

export function useOptimizedChat(options: UseOptimizedChatOptions = {}) {
  const {
    enablePredictiveLoading = true,
    enableResponseCache = true,
    streamingChunkSize = 3
  } = options

  const [isTyping, setIsTyping] = useState(false)
  const [predictedResponse, setPredictedResponse] = useState<string | null>(null)
  const responseCache = useRef(new Map<string, string>())

  const { addMessage, updateMessage } = useAppStore()

  // Cache de respuestas comunes para velocidad instantánea
  const initializeResponseCache = useCallback(() => {
    const commonResponses = [
      { q: 'hola', a: '¡Hola! ¿En qué puedo ayudarte hoy?' },
      { q: 'hello', a: 'Hello! How can I help you today?' },
      { q: 'gracias', a: '¡De nada! ¿Hay algo más en lo que pueda asistirte?' },
      { q: 'thank you', a: "You're welcome! Is there anything else I can help with?" },
      { q: 'adios', a: '¡Hasta luego! Que tengas un excelente día.' },
      { q: 'goodbye', a: 'Goodbye! Have a great day!' },
    ]

    commonResponses.forEach(({ q, a }) => {
      responseCache.current.set(q.toLowerCase().trim(), a)
    })
  }, [])

  // Inicializar cache al montar
  useEffect(() => {
    if (enableResponseCache) {
      initializeResponseCache()
    }
  }, [enableResponseCache, initializeResponseCache])

  // Función para obtener respuesta cacheada
  const getCachedResponse = useCallback((message: string): string | null => {
    if (!enableResponseCache) return null

    const normalized = message.toLowerCase().trim()
    return responseCache.current.get(normalized) || null
  }, [enableResponseCache])

  // Función para finalizar streaming (DEFINIDA ANTES para evitar ReferenceError)
  const completeStreaming = useCallback((messageId: string, finalData: Partial<ChatMessage>) => {
    updateMessage(messageId, {
      ...finalData,
      status: finalData.status ?? 'delivered',
      isStreaming: false
    })
  }, [updateMessage])

  // Función para actualizar contenido de streaming de forma optimizada
  const updateStreamingContent = useCallback((messageId: string, newContent: string) => {
    updateMessage(messageId, {
      content: newContent,
      // Mantener streaming status hasta que se complete
      status: 'streaming',
      isStreaming: true
    })
  }, [updateMessage])

  // Función optimizada para enviar mensajes
  const sendOptimizedMessage = useCallback(async (
    message: string,
    sendMessage: (msg: string, placeholderId: string) => Promise<Partial<ChatMessage> | void>
  ) => {
    // 1. Agregar mensaje del usuario inmediatamente
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user' as const,
      content: message,
      timestamp: new Date(),
      status: 'delivered' as const
    }
    addMessage(userMessage)

    // 2. Verificar cache para respuesta instantánea
    const cachedResponse = getCachedResponse(message)

    if (cachedResponse) {
      // Respuesta instantánea con simulación de typing para naturalidad
      const assistantId = `assistant-${Date.now()}`

      // Agregar mensaje vacío con indicador de typing
      addMessage({
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        status: 'streaming',
        isStreaming: true
      })

      // Simular typing durante un corto tiempo para naturalidad
      setTimeout(() => {
        updateMessage(assistantId, {
          content: cachedResponse,
          status: 'delivered',
          isStreaming: false
        })
      }, 300 + Math.random() * 500) // 300-800ms de typing simulado

      return
    }

    // 3. Para respuestas no cacheadas, mostrar typing indicator inmediato
    setIsTyping(true)
    const assistantId = `assistant-${Date.now()}`

    addMessage({
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      status: 'streaming',
      isStreaming: true
    })

    try {
      // 4. Enviar mensaje real
      const finalMessage = await sendMessage(message, assistantId)

      if (finalMessage) {
        completeStreaming(assistantId, finalMessage)
      } else {
        completeStreaming(assistantId, { status: 'delivered' })
      }
    } catch (error) {
      // Manejar error actualizando el mensaje
      completeStreaming(assistantId, {
        content: 'Lo siento, hubo un error al procesar tu mensaje.',
        status: 'error'
      })
    } finally {
      setIsTyping(false)
    }
  }, [addMessage, completeStreaming, getCachedResponse, updateMessage, updateStreamingContent])

  // Función para precarga predictiva (experimental)
  const startPredictiveLoading = useCallback((partialMessage: string) => {
    if (!enablePredictiveLoading || partialMessage.length < 3) return

    // Predicciones simples basadas en patrones comunes
    const predictions = {
      'como ': 'Como puedo ayudarte con eso...',
      'what ': 'What would you like to know...',
      'how ': 'How can I assist you...',
      'why ': 'Why do you ask...'
    }

    const prediction = Object.entries(predictions).find(([prefix]) =>
      partialMessage.toLowerCase().includes(prefix)
    )

    if (prediction) {
      setPredictedResponse(prediction[1])
    }
  }, [enablePredictiveLoading])

  return {
    // Estado
    isTyping,
    predictedResponse,

    // Funciones optimizadas
    sendOptimizedMessage,
    updateStreamingContent,
    completeStreaming,
    startPredictiveLoading,

    // Utilidades
    getCachedResponse,

    // Configuración
    cacheSize: responseCache.current.size
  }
}
