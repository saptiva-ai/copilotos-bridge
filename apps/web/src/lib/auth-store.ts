'use client'

import { createWithEqualityFn } from 'zustand/traditional'
import { devtools, persist, createJSONStorage } from 'zustand/middleware'

import { apiClient, setAuthTokenGetter, LoginRequest } from './api-client'
import type { AuthTokens, RegisterPayload, RefreshTokenResponse, UserProfile } from './types'
import { logDebug, logError, logWarn } from './logger'

interface AuthState {
  user: UserProfile | null
  accessToken: string | null
  refreshToken: string | null
  expiresAt: number | null
  status: 'idle' | 'loading' | 'error'
  error: AuthErrorInfo | null
  isHydrated: boolean
}

interface AuthActions {
  login: (credentials: LoginRequest) => Promise<boolean>
  register: (payload: RegisterPayload) => Promise<boolean>
  logout: () => Promise<void>
  refreshSession: () => Promise<boolean>
  fetchProfile: () => Promise<void>
  clearError: () => void
  clearCache: () => void
  isAuthenticated: () => boolean
}

const AUTH_STORAGE_KEY = 'copilotos-auth-state'
const ONE_MINUTE_MS = 60_000

type AuthStore = AuthState & AuthActions

interface AuthErrorInfo {
  code: string
  message: string
  field?: string
}

const ERROR_MESSAGES: Record<string, string> = {
  USER_EXISTS: 'Ya existe una cuenta con ese correo.',
  USERNAME_EXISTS: 'Ya existe un usuario con ese nombre.',
  BAD_CREDENTIALS: 'Correo o contraseña incorrectos.',
  ACCOUNT_INACTIVE: 'Tu cuenta está inactiva. Contacta al administrador.',
  INVALID_TOKEN: 'La sesión expiró. Inicia sesión nuevamente.',
  WEAK_PASSWORD: 'Tu contraseña es demasiado débil (mínimo 8 caracteres, 1 mayúscula, 1 número).',
}

function computeExpiry(expiresInSeconds: number): number {
  return Date.now() + expiresInSeconds * 1000
}

function mapApiError(error: unknown): AuthErrorInfo {
  const fallback: AuthErrorInfo = {
    code: 'UNKNOWN',
    message: 'Ocurrió un error. Intenta de nuevo.',
  }

  if (typeof error === 'string') {
    return { ...fallback, message: error }
  }

  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as any
    const responseData = axiosError.response?.data ?? {}
    const detail = responseData?.detail ?? responseData

    const code = detail?.code ?? responseData?.code
    const field = detail?.field ?? responseData?.field
    const detailMessage = typeof detail?.message === 'string' ? detail.message : undefined
    const mappedMessage = code ? ERROR_MESSAGES[code] : undefined

    return {
      code: code ?? 'UNKNOWN',
      message: mappedMessage || detailMessage || axiosError.message || fallback.message,
      field,
    }
  }

  if (error instanceof Error) {
    return { ...fallback, message: error.message }
  }

  return fallback
}

const initialHydrated = false

export const useAuthStore = createWithEqualityFn<AuthStore>()(
  devtools(
    persist(
      (set, get) => ({
        user: null,
        accessToken: null,
        refreshToken: null,
        expiresAt: null,
        status: 'idle',
        error: null,
        isHydrated: initialHydrated,

        async login(credentials) {
          set({ status: 'loading', error: null })
          try {
            const authResponse = await apiClient.login(credentials)
            applyAuthResponse(set, authResponse)
            set({ status: 'idle' })
            return true
          } catch (error) {
            const apiError = mapApiError(error)
            set({ status: 'error', error: apiError })
            return false
          }
        },

        async register(payload) {
          set({ status: 'loading', error: null })
          try {
            const authResponse = await apiClient.register(payload)
            applyAuthResponse(set, authResponse)
            set({ status: 'idle' })
            return true
          } catch (error) {
            const apiError = mapApiError(error)
            set({ status: 'error', error: apiError })
            return false
          }
        },

        async logout() {
          try {
            // Call backend logout endpoint per LOG-API-01
            await apiClient.logout()
          } catch (error) {
            // Even if backend call fails, proceed with client cleanup
            logWarn('Logout backend call failed:', mapApiError(error).message)
          }

          // Clear local state per LOG-UI-01
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            expiresAt: null,
            status: 'idle',
            error: null,
          })

          // Clear localStorage and redirect to login per LOG-UI-01
          get().clearCache()
          if (typeof window !== 'undefined') {
            window.location.href = '/login'
          }
        },

        async refreshSession() {
          const state = get()
          if (!state.refreshToken) {
            return false
          }

          if (state.expiresAt && state.expiresAt - Date.now() > ONE_MINUTE_MS) {
            // Token is still fresh enough
            return true
          }

          try {
            const refreshed: RefreshTokenResponse = await apiClient.refreshAccessToken(state.refreshToken)
            set({
              accessToken: refreshed.accessToken,
              expiresAt: computeExpiry(refreshed.expiresIn),
              status: 'idle',
              error: null,
            })
            return true
          } catch (error) {
            const apiError = mapApiError(error)
            logWarn('Failed to refresh session', apiError.message)
            set({ status: 'error', error: apiError })
            return false
          }
        },

        async fetchProfile() {
          try {
            const profile = await apiClient.getCurrentUser()
            set({ user: profile })
          } catch (error) {
            const apiError = mapApiError(error)
            logWarn('Failed to fetch user profile', apiError.message)
            if (apiError.code === 'INVALID_TOKEN' || apiError.code === 'BAD_CREDENTIALS') {
              get().logout()
            }
          }
        },

        clearError() {
          set({ error: null, status: 'idle' })
        },

        clearCache() {
          // Clear all auth-related localStorage
          localStorage.removeItem(AUTH_STORAGE_KEY)
          localStorage.removeItem('demo-notice-dismissed')
          // Reset state to initial
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            expiresAt: null,
            status: 'idle',
            error: null,
          })
          logDebug('Auth cache cleared')
        },

        isAuthenticated() {
          const state = get()
          return Boolean(state.accessToken && state.user)
        },
      }),
      {
        name: AUTH_STORAGE_KEY,
        storage: createJSONStorage(() => localStorage),
        version: 1, // Version for cache invalidation
        migrate: (persistedState: any, version: number) => {
          // Simple migration - if version is less than 1, clear the state
          if (version < 1) {
            return {
              user: null,
              accessToken: null,
              refreshToken: null,
              expiresAt: null,
            }
          }
          return persistedState
        },
        partialize: (state) => ({
          user: state.user,
          accessToken: state.accessToken,
          refreshToken: state.refreshToken,
          expiresAt: state.expiresAt,
        }),
        onRehydrateStorage: () => (state, error) => {
          if (error) {
            logError('Auth store rehydration error', error)
            // Clear corrupted data and restart fresh
            localStorage.removeItem(AUTH_STORAGE_KEY)
          }
          // Check if token is expired and clear if needed
          if (state?.expiresAt && state.expiresAt <= Date.now()) {
            logWarn('Stored auth token expired, clearing')
            localStorage.removeItem(AUTH_STORAGE_KEY)
            useAuthStore.setState({
              user: null,
              accessToken: null,
              refreshToken: null,
              expiresAt: null,
              status: 'idle',
              error: null,
            })
          }
          // Set hydration state using the store API after it's ready
          setTimeout(() => {
            useAuthStore.setState({ isHydrated: true, status: 'idle' })
          }, 0)
        },
      }
    )
  )
)

function applyAuthResponse(
  set: (fn: (state: AuthStore) => Partial<AuthStore>) => void,
  authResponse: AuthTokens
) {
  set(() => ({
    user: authResponse.user,
    accessToken: authResponse.accessToken,
    refreshToken: authResponse.refreshToken,
    expiresAt: computeExpiry(authResponse.expiresIn),
    error: null,
  }))
}

// Initialize auth token getter after store creation
setTimeout(() => {
  setAuthTokenGetter(() => {
    try {
      const state = useAuthStore.getState()
      return state.accessToken
    } catch (error) {
      logWarn('Failed to get auth token from store', error)
      return null
    }
  })
}, 0)
