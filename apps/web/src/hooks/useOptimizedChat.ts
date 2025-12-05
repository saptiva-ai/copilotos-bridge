import { useState, useCallback, useRef, useEffect } from "react";
import { flushSync } from "react-dom";
import { useAppStore } from "../lib/store";
import type { ChatMessage } from "../lib/types";
import { logDebug } from "../lib/logger";

interface UseOptimizedChatOptions {
  enablePredictiveLoading?: boolean;
  enableResponseCache?: boolean;
  streamingChunkSize?: number;
}

export function useOptimizedChat(options: UseOptimizedChatOptions = {}) {
  const {
    enablePredictiveLoading = true,
    enableResponseCache = true,
    streamingChunkSize = 3,
  } = options;

  const [isTyping, setIsTyping] = useState(false);
  const [predictedResponse, setPredictedResponse] = useState<string | null>(
    null,
  );
  const responseCache = useRef(new Map<string, string>());
  const currentRequestController = useRef<AbortController | null>(null);

  // Throttling refs para evitar bloquear el navegador con demasiados flushSync
  const lastUpdateTime = useRef<number>(0);
  const pendingUpdate = useRef<{ messageId: string; content: string } | null>(
    null,
  );
  const throttleTimer = useRef<NodeJS.Timeout | null>(null);
  // FIX ISSUE-001: Promise para sincronizar flush pendiente antes de completar streaming
  const pendingFlushPromise = useRef<Promise<void> | null>(null);

  const { addMessage, updateMessage } = useAppStore();

  // Cache de respuestas comunes para velocidad instantánea
  const initializeResponseCache = useCallback(() => {
    const commonResponses = [
      { q: "hola", a: "¡Hola! ¿En qué puedo ayudarte hoy?" },
      { q: "hello", a: "Hello! How can I help you today?" },
      { q: "gracias", a: "¡De nada! ¿Hay algo más en lo que pueda asistirte?" },
      {
        q: "thank you",
        a: "You're welcome! Is there anything else I can help with?",
      },
      { q: "adios", a: "¡Hasta luego! Que tengas un excelente día." },
      { q: "goodbye", a: "Goodbye! Have a great day!" },
    ];

    commonResponses.forEach(({ q, a }) => {
      responseCache.current.set(q.toLowerCase().trim(), a);
    });
  }, []);

  // Inicializar cache al montar
  useEffect(() => {
    if (enableResponseCache) {
      initializeResponseCache();
    }
  }, [enableResponseCache, initializeResponseCache]);

  // Función para obtener respuesta cacheada
  const getCachedResponse = useCallback(
    (message: string): string | null => {
      if (!enableResponseCache) return null;

      const normalized = message.toLowerCase().trim();
      return responseCache.current.get(normalized) || null;
    },
    [enableResponseCache],
  );

  // Función para finalizar streaming (DEFINIDA ANTES para evitar ReferenceError)
  // FIX ISSUE-001: Ahora es async para esperar flush pendiente
  const completeStreaming = useCallback(
    async (messageId: string, finalData: Partial<ChatMessage>) => {
      // FIX ISSUE-001: Esperar a que termine el flush pendiente para evitar race condition
      if (pendingFlushPromise.current) {
        await pendingFlushPromise.current;
        pendingFlushPromise.current = null;
      }

      // Limpiar cualquier throttle timer pendiente (por si acaso)
      if (throttleTimer.current !== null) {
        clearTimeout(throttleTimer.current);
        throttleTimer.current = null;
      }

      // Aplicar finalData (ya no necesitamos aplicar pendingUpdate porque el Promise lo hizo)
      // DEBUG: Log finalData to verify metadata is being passed
      console.warn("[🔍 COMPLETE_STREAMING] Applying final data:", {
        messageId,
        hasMetadata: !!(finalData as any)?.metadata,
        hasBankChartData: !!(finalData as any)?.metadata?.bank_chart_data,
        finalDataKeys: Object.keys(finalData),
        metadataKeys: (finalData as any)?.metadata
          ? Object.keys((finalData as any).metadata)
          : [],
      });
      flushSync(() => {
        updateMessage(messageId, {
          ...finalData,
          status: finalData.status ?? "delivered",
          isStreaming: false,
        });
      });

      // Reset throttle state
      lastUpdateTime.current = 0;
      pendingUpdate.current = null;
    },
    [updateMessage],
  );

  // Función para actualizar contenido de streaming de forma optimizada
  const updateStreamingContent = useCallback(
    (messageId: string, newContent: string) => {
      const extractDisplayContent = (raw: string) => {
        if (typeof raw !== "string") return raw as unknown as string;
        const trimmed = raw.trim();
        if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
          try {
            const parsed = JSON.parse(trimmed);
            if (parsed && typeof parsed === "object" && parsed.content) {
              return String(parsed.content);
            }
          } catch {
            // ignore parse errors, fallback to raw
          }
        }
        return raw;
      };

      const displayContent = extractDisplayContent(newContent);
      const now = Date.now();
      const timeSinceLastUpdate = now - lastUpdateTime.current;
      const THROTTLE_MS = 50;

      // console.log("[DEBUG] updateStreamingContent - length:", newContent.length, "timeSince:", timeSinceLastUpdate, "hasTimer:", throttleTimer.current !== null);

      // Siempre guardar el último contenido
      pendingUpdate.current = { messageId, content: newContent };

      // Actualizar inmediatamente si:
      // 1. Es el primer chunk (lastUpdateTime === 0)
      // 2. Han pasado >= THROTTLE_MS desde la última actualización
      if (lastUpdateTime.current === 0 || timeSinceLastUpdate >= THROTTLE_MS) {
        // console.log("[DEBUG] IMMEDIATE UPDATE - length:", newContent.length);
        // Actualizar inmediatamente
        flushSync(() => {
          updateMessage(messageId, {
            content: displayContent,
            status: "streaming",
            isStreaming: true,
          });
        });
        lastUpdateTime.current = now;
        pendingUpdate.current = null;

        // Limpiar timer y promise si existen
        if (throttleTimer.current !== null) {
          clearTimeout(throttleTimer.current);
          throttleTimer.current = null;
        }
        pendingFlushPromise.current = null;
      } else {
        // Programar actualización para el próximo intervalo si no hay timer activo
        if (throttleTimer.current === null) {
          const delay = THROTTLE_MS - timeSinceLastUpdate;
          // console.log("[DEBUG] SCHEDULING TIMER - delay:", delay, "ms");

          // FIX ISSUE-001: Crear Promise para que completeStreaming pueda esperar
          pendingFlushPromise.current = new Promise<void>((resolve) => {
            throttleTimer.current = setTimeout(() => {
              // console.log("[DEBUG] TIMER FIRED - pendingLength:", pendingUpdate.current?.content.length);
              if (pendingUpdate.current) {
                flushSync(() => {
                  updateMessage(pendingUpdate.current!.messageId, {
                    content: extractDisplayContent(
                      pendingUpdate.current!.content,
                    ),
                    status: "streaming",
                    isStreaming: true,
                  });
                });
                lastUpdateTime.current = Date.now();
                pendingUpdate.current = null;
              }
              throttleTimer.current = null;
              resolve(); // FIX ISSUE-001: Resolver promise cuando termine el flush
            }, delay);
          });
        } else {
          // console.log("[DEBUG] TIMER ALREADY EXISTS - just updating pending");
        }
      }
    },
    [updateMessage],
  );

  // Función optimizada para enviar mensajes
  // MVP-LOCK: Added metadata parameter to attach file_ids to user messages
  const sendOptimizedMessage = useCallback(
    async (
      message: string,
      sendMessage: (
        msg: string,
        placeholderId: string,
        abortController?: AbortController,
      ) => Promise<Partial<ChatMessage> | void>,
      metadata?: Record<string, any>,
    ) => {
      // 1. Agregar mensaje del usuario inmediatamente
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user" as const,
        content: message,
        timestamp: new Date(),
        status: "delivered" as const,
        ...(metadata && { metadata }), // MVP-LOCK: Include metadata if provided
      };

      // DEBUG: Log user message with metadata before adding to store
      logDebug("[useOptimizedChat] Creating user message", {
        hasMetadata: !!metadata,
        metadata,
        userMessage,
        metadataInMessage: userMessage.metadata,
      });

      addMessage(userMessage);

      // 2. Verificar cache para respuesta instantánea
      const cachedResponse = getCachedResponse(message);

      if (cachedResponse) {
        // Respuesta instantánea con simulación de typing para naturalidad
        const assistantId = `assistant-${Date.now()}`;

        // Agregar mensaje vacío con indicador de typing
        addMessage({
          id: assistantId,
          role: "assistant",
          content: "",
          timestamp: new Date(),
          status: "streaming",
          isStreaming: true,
        });

        // Simular typing durante un corto tiempo para naturalidad
        setTimeout(
          () => {
            updateMessage(assistantId, {
              content: cachedResponse,
              status: "delivered",
              isStreaming: false,
            });
          },
          300 + Math.random() * 500,
        ); // 300-800ms de typing simulado

        return;
      }

      // 3. Para respuestas no cacheadas, mostrar typing indicator inmediato
      setIsTyping(true);
      const assistantId = `assistant-${Date.now()}`;

      // Crear AbortController para este request
      currentRequestController.current = new AbortController();

      addMessage({
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        status: "streaming",
        isStreaming: true,
      });

      try {
        // 4. Enviar mensaje real con AbortController
        const finalMessage = await sendMessage(
          message,
          assistantId,
          currentRequestController.current,
        );

        // FIX: Await completeStreaming to ensure metadata is written to store before render
        if (finalMessage) {
          await completeStreaming(assistantId, finalMessage);
        } else {
          await completeStreaming(assistantId, { status: "delivered" });
        }
      } catch (error) {
        // Verificar si fue cancelado
        if (error instanceof Error && error.name === "AbortError") {
          await completeStreaming(assistantId, {
            content: "Mensaje cancelado",
            status: "error",
          });
        } else {
          // Manejar otros errores
          await completeStreaming(assistantId, {
            content: "Lo siento, hubo un error al procesar tu mensaje.",
            status: "error",
          });
        }
      } finally {
        setIsTyping(false);
        currentRequestController.current = null;
      }
    },
    [addMessage, completeStreaming, getCachedResponse, updateMessage],
  );

  // Función para precarga predictiva (experimental)
  const startPredictiveLoading = useCallback(
    (partialMessage: string) => {
      if (!enablePredictiveLoading || partialMessage.length < 3) return;

      // Predicciones simples basadas en patrones comunes
      const predictions = {
        "como ": "Como puedo ayudarte con eso...",
        "what ": "What would you like to know...",
        "how ": "How can I assist you...",
        "why ": "Why do you ask...",
      };

      const prediction = Object.entries(predictions).find(([prefix]) =>
        partialMessage.toLowerCase().includes(prefix),
      );

      if (prediction) {
        setPredictedResponse(prediction[1]);
      }
    },
    [enablePredictiveLoading],
  );

  // Función para cancelar streaming
  const cancelCurrentRequest = useCallback(() => {
    if (currentRequestController.current) {
      currentRequestController.current.abort();
      currentRequestController.current = null;
      setIsTyping(false);
    }
  }, []);

  // Limpiar el controlador y timers cuando se desmonte
  // FIX ISSUE-002: Limpiar pendingFlushPromise para prevenir memory leak
  useEffect(() => {
    return () => {
      // Limpiar AbortController
      if (currentRequestController.current) {
        currentRequestController.current.abort();
      }

      // Limpiar timer pendiente
      if (throttleTimer.current !== null) {
        clearTimeout(throttleTimer.current);
        throttleTimer.current = null;
      }

      // Limpiar Promise pendiente y estado
      pendingFlushPromise.current = null;
      pendingUpdate.current = null;
      lastUpdateTime.current = 0;
    };
  }, []);

  return {
    // Estado
    isTyping,
    predictedResponse,

    // Funciones optimizadas
    sendOptimizedMessage,
    updateStreamingContent,
    completeStreaming,
    startPredictiveLoading,
    cancelCurrentRequest,

    // Utilidades
    getCachedResponse,

    // Configuración
    cacheSize: responseCache.current.size,
  };
}
