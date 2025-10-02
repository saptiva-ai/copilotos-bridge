'use client'

import { useAuthStore } from '@/lib/auth-store'
import { SessionExpiredModal } from '../auth/SessionExpiredModal'

/**
 * Provider that listens for session expiration events and shows the modal
 * This should be mounted at the root layout level
 */
export function SessionExpiredProvider() {
  const sessionExpired = useAuthStore((state) => state.sessionExpired)
  const sessionExpiredReason = useAuthStore((state) => state.sessionExpiredReason)
  const dismissSessionExpired = useAuthStore((state) => state.dismissSessionExpired)

  return (
    <SessionExpiredModal
      isOpen={sessionExpired}
      reason={sessionExpiredReason || 'expired'}
      onClose={dismissSessionExpired}
    />
  )
}
