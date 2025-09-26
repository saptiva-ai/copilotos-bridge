import { useCallback, useRef, useMemo, useEffect } from 'react'

/**
 * Hook para optimizaciones de rendimiento avanzadas
 */
export function usePerformanceOptimization() {
  const frameRef = useRef<number>()
  const taskQueue = useRef<(() => void)[]>([])
  const isProcessing = useRef(false)

  // Debounce optimizado con cancelación
  const useAdvancedDebounce = useCallback(<T extends (...args: any[]) => any>(
    func: T,
    delay: number,
    options: {
      leading?: boolean
      trailing?: boolean
      maxWait?: number
    } = {}
  ) => {
    const { leading = false, trailing = true, maxWait } = options
    const timeoutRef = useRef<NodeJS.Timeout>()
    const maxTimeoutRef = useRef<NodeJS.Timeout>()
    const lastCallRef = useRef<number>()
    const lastInvokeRef = useRef<number>(0)

    return useCallback((...args: Parameters<T>) => {
      const now = Date.now()
      const since = now - (lastInvokeRef.current || 0)

      lastCallRef.current = now

      const invokeFunc = () => {
        lastInvokeRef.current = now
        return func(...args)
      }

      const shouldInvoke = () => {
        if (leading && !timeoutRef.current) return true
        if (maxWait !== undefined && since >= maxWait) return true
        return false
      }

      const startTimer = () => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current)

        timeoutRef.current = setTimeout(() => {
          timeoutRef.current = undefined
          if (trailing && lastCallRef.current) {
            invokeFunc()
          }
        }, delay)

        if (maxWait !== undefined && !maxTimeoutRef.current) {
          maxTimeoutRef.current = setTimeout(() => {
            maxTimeoutRef.current = undefined
            if (timeoutRef.current) {
              clearTimeout(timeoutRef.current)
              timeoutRef.current = undefined
            }
            invokeFunc()
          }, maxWait)
        }
      }

      if (shouldInvoke()) {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current)
          timeoutRef.current = undefined
        }
        if (maxTimeoutRef.current) {
          clearTimeout(maxTimeoutRef.current)
          maxTimeoutRef.current = undefined
        }
        return invokeFunc()
      }

      startTimer()
    }, [func, delay, leading, trailing, maxWait])
  }, [])

  // Throttle con cancelación
  const useAdvancedThrottle = useCallback(<T extends (...args: any[]) => any>(
    func: T,
    delay: number,
    options: { leading?: boolean; trailing?: boolean } = {}
  ) => {
    const { leading = true, trailing = true } = options
    const timeoutRef = useRef<NodeJS.Timeout>()
    const lastExecRef = useRef<number>(0)
    const argsRef = useRef<Parameters<T>>()

    return useCallback((...args: Parameters<T>) => {
      const now = Date.now()
      argsRef.current = args

      const invokeFunc = () => {
        lastExecRef.current = now
        return func(...args)
      }

      const shouldInvoke = now - lastExecRef.current >= delay

      if (shouldInvoke) {
        if (leading) {
          return invokeFunc()
        }
      }

      if (trailing && !timeoutRef.current) {
        timeoutRef.current = setTimeout(() => {
          timeoutRef.current = undefined
          if (argsRef.current) {
            invokeFunc()
          }
        }, delay - (now - lastExecRef.current))
      }
    }, [func, delay, leading, trailing])
  }, [])

  // Queue de tareas para evitar bloquear el hilo principal
  const scheduleTask = useCallback((task: () => void, priority: 'low' | 'normal' | 'high' = 'normal') => {
    if (priority === 'high') {
      taskQueue.current.unshift(task)
    } else {
      taskQueue.current.push(task)
    }

    if (!isProcessing.current) {
      processTaskQueue()
    }
  }, [])

  const processTaskQueue = useCallback(() => {
    if (taskQueue.current.length === 0) {
      isProcessing.current = false
      return
    }

    isProcessing.current = true

    const processNextTask = () => {
      const task = taskQueue.current.shift()
      if (task) {
        try {
          task()
        } catch (error) {
          console.error('Error processing task:', error)
        }
      }

      if (taskQueue.current.length > 0) {
        frameRef.current = requestAnimationFrame(processNextTask)
      } else {
        isProcessing.current = false
      }
    }

    frameRef.current = requestAnimationFrame(processNextTask)
  }, [])

  // Memoización avanzada con cleanup
  const useStableMemo = useCallback(<T>(
    factory: () => T,
    deps: React.DependencyList,
    shouldUpdate?: (prev: T, next: T) => boolean
  ) => {
    const prevDeps = useRef<React.DependencyList>()
    const prevValue = useRef<T>()

    return useMemo(() => {
      if (!prevDeps.current || deps.some((dep, i) => dep !== prevDeps.current![i])) {
        const newValue = factory()

        if (shouldUpdate && prevValue.current !== undefined) {
          if (!shouldUpdate(prevValue.current, newValue)) {
            return prevValue.current
          }
        }

        prevDeps.current = deps
        prevValue.current = newValue
        return newValue
      }

      return prevValue.current!
    }, deps)
  }, [])

  // Hook para optimizar re-renders de componentes hijo
  const useChildrenMemo = useCallback((
    children: React.ReactNode,
    deps: React.DependencyList = []
  ) => {
    return useMemo(() => children, deps)
  }, [])

  // Batch de actualizaciones de estado
  const useBatchedUpdates = useCallback(() => {
    const updates = useRef<(() => void)[]>([])
    const scheduled = useRef(false)

    const flushUpdates = useCallback(() => {
      if (updates.current.length > 0) {
        const toFlush = [...updates.current]
        updates.current = []
        scheduled.current = false

        // Usar React.unstable_batchedUpdates si está disponible
        if (typeof (React as any).unstable_batchedUpdates === 'function') {
          ;(React as any).unstable_batchedUpdates(() => {
            toFlush.forEach(update => update())
          })
        } else {
          toFlush.forEach(update => update())
        }
      }
    }, [])

    const batchUpdate = useCallback((update: () => void) => {
      updates.current.push(update)

      if (!scheduled.current) {
        scheduled.current = true
        scheduleTask(flushUpdates, 'high')
      }
    }, [flushUpdates, scheduleTask])

    return { batchUpdate }
  }, [scheduleTask])

  // Cleanup en unmount
  useEffect(() => {
    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current)
      }
      taskQueue.current = []
      isProcessing.current = false
    }
  }, [])

  return {
    useAdvancedDebounce,
    useAdvancedThrottle,
    scheduleTask,
    useStableMemo,
    useChildrenMemo,
    useBatchedUpdates
  }
}