import { logWarn } from './logger'

export const RUNTIME = {
  NODE_ENV: process.env.NODE_ENV,
  API_BASE: process.env.NEXT_PUBLIC_API_URL,
  ENABLE_MSW: process.env.NEXT_PUBLIC_ENABLE_MSW,
}

export function assertProdNoMock() {
  const isBrowser = typeof window !== 'undefined'
  const isProd = process.env.NODE_ENV === 'production'
  const isCI = process.env.CI === 'true' || process.env.CI === '1'
  const mswFlag = process.env.NEXT_PUBLIC_ENABLE_MSW

  if (isProd) {
    const resolvedApiBase = process.env.NEXT_PUBLIC_API_URL || (isCI ? 'http://localhost:8001' : undefined)

    if (!process.env.NEXT_PUBLIC_API_URL && resolvedApiBase) {
      // Ensure downstream code sees the computed fallback during CI builds
      process.env.NEXT_PUBLIC_API_URL = resolvedApiBase
    }

    if (!resolvedApiBase) {
      throw new Error('API base missing; refusing to fall back to mocks in production.')
    }

    const effectiveMswFlag = mswFlag ?? (isCI ? 'false' : undefined)

    if (!process.env.NEXT_PUBLIC_ENABLE_MSW && effectiveMswFlag) {
      process.env.NEXT_PUBLIC_ENABLE_MSW = effectiveMswFlag
    }

    if (effectiveMswFlag === 'true') {
      throw new Error('MSW enabled in production env. Disable it or guard behind a feature flag.')
    }
  }

  // Additional runtime checks
  if (isBrowser && isProd) {
    // Check for potential mock indicators in localStorage
    const mockIndicators = ['msw', 'mock-api', 'dev-mode']
    for (const indicator of mockIndicators) {
      if (localStorage.getItem(indicator) === 'true' || localStorage.getItem(indicator) === 'on') {
        logWarn(`Found mock indicator '${indicator}' in localStorage during production. Consider clearing.`)
      }
    }
  }
}
