import React, { useCallback, useRef } from 'react'

/**
 * Simple debounce function that doesn't use hooks internally
 */
function createDebounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number,
  options: {
    leading?: boolean
    trailing?: boolean
    maxWait?: number
  } = {}
) {
  const { leading = false, trailing = true, maxWait } = options
  let timeoutId: NodeJS.Timeout | undefined
  let maxTimeoutId: NodeJS.Timeout | undefined
  let lastCallTime: number | undefined
  let lastInvokeTime = 0

  return (...args: Parameters<T>) => {
    const now = Date.now()
    const since = now - lastInvokeTime

    lastCallTime = now

    const invokeFunc = () => {
      lastInvokeTime = now
      return func(...args)
    }

    const shouldInvoke = () => {
      if (leading && !timeoutId) return true
      if (maxWait !== undefined && since >= maxWait) return true
      return false
    }

    const startTimer = () => {
      if (timeoutId) clearTimeout(timeoutId)

      timeoutId = setTimeout(() => {
        timeoutId = undefined
        if (trailing && lastCallTime) {
          invokeFunc()
        }
      }, delay)

      if (maxWait !== undefined && !maxTimeoutId) {
        maxTimeoutId = setTimeout(() => {
          maxTimeoutId = undefined
          if (timeoutId) {
            clearTimeout(timeoutId)
            timeoutId = undefined
          }
          invokeFunc()
        }, maxWait)
      }
    }

    if (shouldInvoke()) {
      if (timeoutId) {
        clearTimeout(timeoutId)
        timeoutId = undefined
      }
      if (maxTimeoutId) {
        clearTimeout(maxTimeoutId)
        maxTimeoutId = undefined
      }
      return invokeFunc()
    }

    startTimer()
  }
}

/**
 * Hook para optimizaciones de rendimiento simplificado
 */
export function usePerformanceOptimization() {
  const taskQueue = useRef<(() => void)[]>([])
  const isProcessing = useRef(false)

  // Simple task processor
  const processTaskQueue = useCallback(() => {
    if (taskQueue.current.length === 0) {
      isProcessing.current = false
      return
    }

    isProcessing.current = true
    const task = taskQueue.current.shift()

    if (task) {
      try {
        task()
      } catch (error) {
        // Use eslint-disable for intentional console in dev helper
        // eslint-disable-next-line no-console
        console.error('Task execution error:', error)
      }
    }

    // Process next task
    if (taskQueue.current.length > 0) {
      setTimeout(processTaskQueue, 0)
    } else {
      isProcessing.current = false
    }
  }, [])

  // Task scheduler
  const scheduleTask = useCallback((task: () => void, priority: 'high' | 'normal' | 'low' = 'normal') => {
    if (priority === 'high') {
      taskQueue.current.unshift(task)
    } else {
      taskQueue.current.push(task)
    }

    if (!isProcessing.current) {
      processTaskQueue()
    }
  }, [processTaskQueue])

  // Debounce factory function - returns a plain function, not a hook
  const createAdvancedDebounce = useCallback(<T extends (...args: any[]) => any>(
    func: T,
    delay: number,
    options: {
      leading?: boolean
      trailing?: boolean
      maxWait?: number
    } = {}
  ) => {
    // Return a memoized debounced function
    return createDebounce(func, delay, options)
  }, [])

  // Batch update helper
  const batchUpdate = useCallback((update: () => void) => {
    scheduleTask(update, 'high')
  }, [scheduleTask])

  return {
    createAdvancedDebounce,
    scheduleTask,
    batchUpdate,
  }
}