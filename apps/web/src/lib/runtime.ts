export const RUNTIME = {
  NODE_ENV: process.env.NODE_ENV,
  API_BASE: process.env.NEXT_PUBLIC_API_URL,
  ENABLE_MSW: process.env.NEXT_PUBLIC_ENABLE_MSW,
}

export function assertProdNoMock() {
  const isBrowser = typeof window !== 'undefined'
  const isProd = process.env.NODE_ENV === 'production'
  const mswFlag = process.env.NEXT_PUBLIC_ENABLE_MSW

  if (isProd) {
    if (!process.env.NEXT_PUBLIC_API_URL) {
      throw new Error('API base missing; refusing to fall back to mocks in production.')
    }
    if (mswFlag === 'true') {
      throw new Error('MSW enabled in production env. Disable it or guard behind a feature flag.')
    }
  }

  // Additional runtime checks
  if (isBrowser && isProd) {
    // Check for potential mock indicators in localStorage
    const mockIndicators = ['msw', 'mock-api', 'dev-mode']
    for (const indicator of mockIndicators) {
      if (localStorage.getItem(indicator) === 'true' || localStorage.getItem(indicator) === 'on') {
        console.warn(`Found mock indicator '${indicator}' in localStorage during production. Consider clearing.`)
      }
    }
  }
}
