'use client'

import { useCallback, useEffect, useState } from 'react'
import { Modal } from '../ui/Modal'
import { Button } from '../ui'
import { useAuthStore } from '@/lib/auth-store'

interface SessionExpiredModalProps {
  isOpen: boolean
  reason?: 'expired' | 'invalid' | 'inactive' | 'unauthorized'
  onClose?: () => void
}

const REASON_MESSAGES = {
  expired: {
    title: 'Sesión expirada',
    message: 'Tu sesión ha expirado por inactividad. Por favor, inicia sesión nuevamente para continuar.',
    icon: '⏱️',
  },
  invalid: {
    title: 'Sesión inválida',
    message: 'Tu sesión no es válida. Por favor, inicia sesión nuevamente.',
    icon: '🔒',
  },
  inactive: {
    title: 'Cuenta inactiva',
    message: 'Tu cuenta está inactiva. Contacta al administrador para más información.',
    icon: '⚠️',
  },
  unauthorized: {
    title: 'Acceso no autorizado',
    message: 'No tienes permisos para realizar esta acción. Inicia sesión nuevamente.',
    icon: '🚫',
  },
}

export function SessionExpiredModal({
  isOpen,
  reason = 'expired',
  onClose
}: SessionExpiredModalProps) {
  const logout = useAuthStore((state) => state.logout)
  const [countdown, setCountdown] = useState(5)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const info = REASON_MESSAGES[reason]

  const handleRedirect = useCallback(() => {
    if (onClose) onClose()

    if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
  }, [onClose])

  useEffect(() => {
    if (!isOpen) {
      setCountdown(5)
      setIsLoggingOut(false)
      return
    }

    // Perform logout immediately when modal opens
    const performLogout = async () => {
      if (!isLoggingOut) {
        setIsLoggingOut(true)
        try {
          await logout()
        } catch (error) {
          // Logout will handle the redirect even if there's an error
          console.error('Error during automatic logout:', error)
        }
      }
    }

    performLogout()

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          handleRedirect()
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [isOpen, handleRedirect, isLoggingOut, logout])

  const handleLoginNow = useCallback(() => {
    handleRedirect()
  }, [handleRedirect])

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {}}
      size="sm"
      showCloseButton={false}
      className="bg-surface border border-border"
    >
      <div className="text-center py-2">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-yellow-500/10 mb-4">
          <span className="text-4xl">{info.icon}</span>
        </div>

        <h3 className="text-xl font-semibold text-text mb-2">
          {info.title}
        </h3>

        <p className="text-sm text-text-muted mb-6">
          {info.message}
        </p>

        <div className="mb-6 p-3 rounded-lg bg-background border border-border">
          <p className="text-xs text-text-muted mb-1">
            Redirigiendo al login en
          </p>
          <p className="text-2xl font-bold text-primary">
            {countdown}s
          </p>
        </div>

        <div className="flex gap-3">
          <Button
            onClick={handleLoginNow}
            className="flex-1 bg-primary hover:bg-primary/90 text-white"
          >
            Iniciar sesión ahora
          </Button>
        </div>

        <p className="mt-4 text-xs text-text-muted">
          Tus datos no guardados se perderán
        </p>
      </div>
    </Modal>
  )
}
