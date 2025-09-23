'use client'

import { createWithEqualityFn } from 'zustand/traditional'
import { devtools, persist, createJSONStorage } from 'zustand/middleware'

import { apiClient, setAuthTokenGetter, LoginRequest } from './api-client'
import type { AuthTokens, RegisterPayload, RefreshTokenResponse, UserProfile } from './types'

interface AuthState {
  user: UserProfile | null
  accessToken: string | null
  refreshToken: string | null
  expiresAt: number | null
  status: 'idle' | 'loading' | 'error'
  error: string | null
  isHydrated: boolean
}

interface AuthActions {
  login: (credentials: LoginRequest) => Promise<boolean>
  register: (payload: RegisterPayload) => Promise<boolean>
  logout: () => void
  refreshSession: () => Promise<boolean>
  fetchProfile: () => Promise<void>
  clearError: () => void
  isAuthenticated: () => boolean
}

const AUTH_STORAGE_KEY = 'copilotos-auth-state'
const ONE_MINUTE_MS = 60_000

type AuthStore = AuthState & AuthActions

function computeExpiry(expiresInSeconds: number): number {
  return Date.now() + expiresInSeconds * 1000
}

function mapApiError(error: unknown): string {
  if (typeof error === 'string') return error
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as any
    return (
      axiosError.response?.data?.detail ||
      axiosError.response?.data?.error ||
      axiosError.message ||
      'Ocurrió un error inesperado'
    )
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Ocurrió un error inesperado'
}

const initialHydrated = typeof window === 'undefined'

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
            const message = mapApiError(error)
            set({ status: 'error', error: message })
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
            const message = mapApiError(error)
            set({ status: 'error', error: message })
            return false
          }
        },

        logout() {
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            expiresAt: null,
            status: 'idle',
            error: null,
          })
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
            const message = mapApiError(error)
            console.warn('Failed to refresh session', message)
            set({ status: 'error', error: message })
            return false
          }
        },

        async fetchProfile() {
          try {
            const profile = await apiClient.getCurrentUser()
            set({ user: profile })
          } catch (error) {
            const message = mapApiError(error)
            console.warn('Failed to fetch user profile', message)
            if (String(message).toLowerCase().includes('auth')) {
              get().logout()
            }
          }
        },

        clearError() {
          set({ error: null, status: 'idle' })
        },

        isAuthenticated() {
          const state = get()
          return Boolean(state.accessToken && state.user)
        },
      }),
      {
        name: AUTH_STORAGE_KEY,
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          user: state.user,
          accessToken: state.accessToken,
          refreshToken: state.refreshToken,
          expiresAt: state.expiresAt,
        }),
        onRehydrateStorage: () => (state, error) => {
          if (error) {
            console.error('Auth store rehydration error', error)
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
      console.warn('Failed to get auth token from store', error)
      return null
    }
  })
}, 0)
