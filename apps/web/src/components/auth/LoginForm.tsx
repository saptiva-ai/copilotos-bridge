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
    <div className="w-full rounded-2xl border border-white/10 bg-white/5 p-8 backdrop-blur">
      <div className="mb-8 text-center">
        <h2 className="text-2xl font-semibold text-white">Bienvenido de nuevo</h2>
        <p className="mt-2 text-sm text-saptiva-light/80">
          Ingresa con tu correo electrónico o nombre de usuario para continuar
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
          className="w-full rounded-full bg-gradient-to-r from-saptiva-blue to-saptiva-mint text-base font-semibold text-white hover:from-saptiva-lightBlue hover:to-saptiva-green"
        >
          {status === 'loading' ? 'Ingresando...' : 'Iniciar sesión'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-saptiva-light/80">
        ¿Aún no tienes cuenta?{' '}
        <Link href="/register" className="text-saptiva-mint hover:underline">
          Crea una ahora
        </Link>
      </p>
    </div>
  )
}
