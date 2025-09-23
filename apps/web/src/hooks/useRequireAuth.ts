'use client'

import { useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { shallow } from 'zustand/shallow'

import { useAuthStore } from '../lib/auth-store'

export function useRequireAuth() {
  const router = useRouter()
  const hasCheckedRef = useRef(false)

  const {
    isHydrated,
    accessToken,
    refreshToken,
    user,
    refreshSession,
    fetchProfile,
    logout,
  } = useAuthStore(
    (state) => ({
      isHydrated: state.isHydrated,
      accessToken: state.accessToken,
      refreshToken: state.refreshToken,
      user: state.user,
      refreshSession: state.refreshSession,
      fetchProfile: state.fetchProfile,
      logout: state.logout,
    }),
    shallow
  )

  useEffect(() => {
    if (!isHydrated || hasCheckedRef.current) {
      return
    }

    hasCheckedRef.current = true

    const ensureSession = async () => {
      const refreshed = await refreshSession()
      const currentState = useAuthStore.getState()

      if (!refreshed && !currentState.accessToken) {
        logout()
        router.replace('/login')
        return
      }

      if (currentState.accessToken && !currentState.user) {
        await fetchProfile()
      }
    }

    void ensureSession()
  }, [isHydrated, refreshSession, fetchProfile, logout, router])

  useEffect(() => {
    if (!isHydrated) return
    if (!accessToken && !refreshToken) {
      router.replace('/login')
    }
  }, [isHydrated, accessToken, refreshToken, router])

  const isAuthenticated = Boolean(accessToken && user)

  return { isAuthenticated, isHydrated }
}
