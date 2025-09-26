'use client'

import { useState, useEffect } from 'react'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

import { Input, Button } from '../ui'
import { useAuthStore } from '../../lib/auth-store'

type FieldErrorState = {
  identifier?: string
  password?: string
}

export function LoginForm() {
  const router = useRouter()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrorState>({})
  const [generalError, setGeneralError] = useState<string | null>(null)

  const { status, error, clearError, login, isHydrated, accessToken, user } = useAuthStore((state) => ({
    status: state.status,
    error: state.error,
    clearError: state.clearError,
    login: state.login,
    isHydrated: state.isHydrated,
    accessToken: state.accessToken,
    user: state.user,
  }))

  useEffect(() => {
    if (isHydrated && accessToken && user) {
      router.replace('/chat')
    }
  }, [accessToken, user, isHydrated, router])

  useEffect(() => {
    if (!error) {
      setGeneralError(null)
      return
    }

    if (error.field && ['email', 'username', 'identifier'].includes(error.field)) {
      setFieldErrors((prev) => ({ ...prev, identifier: error.message }))
      setGeneralError(null)
      return
    }

    if (error.field === 'password') {
      setFieldErrors((prev) => ({ ...prev, password: error.message }))
      setGeneralError(null)
      return
    }

    setGeneralError(error.message)
  }, [error])

  const resetFieldError = (field: keyof FieldErrorState) => {
    setFieldErrors((prev) => (prev[field] ? { ...prev, [field]: undefined } : prev))
    if (error) {
      clearError()
    }
    if (generalError) {
      setGeneralError(null)
    }
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    clearError()
    setGeneralError(null)

    const trimmedIdentifier = identifier.trim()
    const trimmedPassword = password.trim()

    const nextFieldErrors: FieldErrorState = {}
    if (!trimmedIdentifier) {
      nextFieldErrors.identifier = 'Ingresa tu correo o usuario.'
    }
    if (!trimmedPassword) {
      nextFieldErrors.password = 'Ingresa tu contraseña.'
    }

    if (Object.keys(nextFieldErrors).length > 0) {
      setFieldErrors(nextFieldErrors)
      return
    }

    const success = await login({ identifier: trimmedIdentifier, password: trimmedPassword })
    if (success) {
      router.push('/chat')
    }
  }

  const isLoading = status === 'loading'

  return (
    <div className="w-full max-w-md rounded-2xl border border-border bg-surface px-8 py-10 shadow-card">
      <div className="mb-8 text-center">
        <div className="mb-2 flex justify-center">
          <Image
            src="/Saptiva_AI_logo_new.webp"
            alt="Saptiva AI logo"
            width={128}
            height={128}
            className="h-32 w-32 object-contain drop-shadow-[0_10px_30px_rgba(73,247,217,0.35)]"
            priority
          />
        </div>
        <h2 className="text-2xl font-semibold text-text">Iniciar sesión</h2>
        <p className="mt-1 text-sm text-text-muted">Accede con tus credenciales corporativas.</p>
      </div>

      {generalError && (
        <div className="mb-6 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {generalError}
        </div>
      )}

      <form className="space-y-5" onSubmit={handleSubmit} noValidate>
        <Input
          label="Correo electrónico o usuario"
          placeholder="tu.nombre@saptiva.ai"
          value={identifier}
          onChange={(event) => {
            setIdentifier(event.target.value)
            resetFieldError('identifier')
          }}
          disabled={isLoading}
          error={fieldErrors.identifier}
          autoComplete="username"
        />

        <Input
          label="Contraseña"
          type="password"
          placeholder="••••••••"
          value={password}
          onChange={(event) => {
            setPassword(event.target.value)
            resetFieldError('password')
          }}
          disabled={isLoading}
          error={fieldErrors.password}
          autoComplete="current-password"
        />

        <Button
          type="submit"
          loading={isLoading}
          disabled={isLoading}
          className="w-full rounded-xl bg-primary text-base font-semibold text-[#0B1217] transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0B1217]"
        >
          Iniciar sesión
        </Button>
      </form>

      <div className="mt-6 text-center text-sm text-text-muted">
        <Link
          href="/forgot-password"
          className="text-link transition-opacity hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
        >
          ¿Olvidaste tu contraseña?
        </Link>
      </div>

      <p className="mt-4 text-center text-sm text-text-muted">
        ¿Aún no tienes cuenta?{' '}
        <Link
          href="/register"
          className="text-link transition-opacity hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
        >
          Crear cuenta
        </Link>
      </p>
    </div>
  )
}
