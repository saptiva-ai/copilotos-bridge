/* eslint-disable no-console */

const shouldLog = () => process.env.NODE_ENV !== 'production'

export function logDebug(...args: unknown[]): void {
  if (shouldLog()) {
    console.debug(...args)
  }
}

export function logInfo(...args: unknown[]): void {
  if (shouldLog()) {
    console.info(...args)
  }
}

export function logWarn(...args: unknown[]): void {
  if (shouldLog()) {
    console.warn(...args)
  }
}

export function logError(...args: unknown[]): void {
  if (shouldLog()) {
    console.error(...args)
  }
}

export function logOnce(message: string): void {
  if (!shouldLog()) return
  if (typeof window !== 'undefined') {
    const key = `__logged__${message}`
    if (window.sessionStorage.getItem(key)) return
    window.sessionStorage.setItem(key, '1')
  }
  console.info(message)
}
