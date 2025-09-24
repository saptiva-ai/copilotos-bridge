'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

import { Input, Button } from '../ui'
import { useAuthStore } from '../../lib/auth-store'

export function LoginForm() {
  const router = useRouter()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')

  const {
    status,
    error,
    clearError,
    login,
    isHydrated,
    accessToken,
    user,
  } = useAuthStore((state) => ({
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

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    clearError()

    if (!identifier.trim() || !password.trim()) {
      return
    }

    const success = await login({ identifier: identifier.trim(), password })
    if (success) {
      router.push('/chat')
    }
  }

  return (
    <div className="w-full rounded-xl border border-border bg-surface p-8 shadow-card">
      <div className="mb-8 text-center">
        <h2 className="text-2xl font-bold text-text">Acceso SAPTIVA</h2>
        <p className="mt-2 text-sm text-text-muted">
          Ingresa tus credenciales para continuar
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-red-300 bg-red-900/30 px-4 py-2 text-sm text-red-200">
          {error}
        </div>
      )}

      <form className="space-y-5" onSubmit={handleSubmit}>
        <Input
          label="Correo electrónico o usuario"
          placeholder="tu.nombre@saptiva.ai"
          value={identifier}
          onChange={(event) => setIdentifier(event.target.value)}
          disabled={status === 'loading'}
          className="bg-white/80"
          required
        />

        <Input
          label="Contraseña"
          type="password"
          placeholder="Ingresa tu contraseña"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={status === 'loading'}
          className="bg-white/80"
          required
        />

        <Button
          type="submit"
          disabled={status === 'loading'}
          className="w-full rounded-md bg-primary text-base font-bold text-white hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
        >
          {status === 'loading' ? 'Ingresando...' : 'Iniciar sesión'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-text-muted">
        ¿Aún no tienes cuenta?{' '}
        <Link href="/register" className="text-link hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60">
          Crear cuenta
        </Link>
      </p>
      <p className="mt-4 text-center text-sm text-text-muted">
        <Link href="/forgot-password"
              className="text-link hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60">
          ¿Olvidaste tu contraseña?
        </Link>
      </p>
    </div>
  )
}
