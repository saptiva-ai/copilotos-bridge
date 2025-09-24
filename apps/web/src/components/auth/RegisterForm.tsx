'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

import { Input, Button } from '../ui'
import { useAuthStore } from '../../lib/auth-store'

export function RegisterForm() {
  const router = useRouter()
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [localError, setLocalError] = useState<string | null>(null)

  const {
    status,
    error,
    clearError,
    register,
    isHydrated,
    accessToken,
    user,
  } = useAuthStore((state) => ({
    status: state.status,
    error: state.error,
    clearError: state.clearError,
    register: state.register,
    isHydrated: state.isHydrated,
    accessToken: state.accessToken,
    user: state.user,
  }))

  useEffect(() => {
    if (isHydrated && accessToken && user) {
      router.replace('/chat')
    }
  }, [accessToken, user, isHydrated, router])

  const updateField = (field: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }))
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    clearError()
    setLocalError(null)

    if (!form.username.trim() || !form.email.trim() || !form.password.trim()) {
      setLocalError('Completa todos los campos')
      return
    }

    if (form.password.length < 8) {
      setLocalError('La contraseña debe tener al menos 8 caracteres')
      return
    }

    if (form.password !== form.confirmPassword) {
      setLocalError('Las contraseñas no coinciden')
      return
    }

    const success = await register({
      username: form.username.trim(),
      email: form.email.trim(),
      password: form.password,
    })

    if (success) {
      router.push('/chat')
    }
  }

  const displayError = localError || error

  return (
    <div className="w-full rounded-xl border border-border bg-surface p-8 shadow-card">
      <div className="mb-8 text-center">
        <h2 className="text-xl font-bold text-text">Crear cuenta</h2>
        <p className="mt-2 text-sm text-text-muted">
          Configura tu acceso a SAPTIVA
        </p>
      </div>

      {displayError && (
        <div className="mb-4 rounded-md border border-red-300 bg-red-900/30 px-4 py-2 text-sm text-red-200">
          {displayError}
        </div>
      )}

      <form className="space-y-5" onSubmit={handleSubmit}>
        <Input
          label="Nombre de usuario"
          placeholder="ej. ana.castro"
          value={form.username}
          onChange={updateField('username')}
          disabled={status === 'loading'}
          className="bg-white/80"
          required
        />

        <Input
          label="Correo corporativo"
          type="email"
          placeholder="usuario@tuempresa.com"
          value={form.email}
          onChange={updateField('email')}
          disabled={status === 'loading'}
          className="bg-white/80"
          required
        />

        <Input
          label="Contraseña"
          type="password"
          placeholder="Mínimo 8 caracteres"
          value={form.password}
          onChange={updateField('password')}
          disabled={status === 'loading'}
          className="bg-white/80"
          required
        />

        <Input
          label="Confirmar contraseña"
          type="password"
          placeholder="Repite tu contraseña"
          value={form.confirmPassword}
          onChange={updateField('confirmPassword')}
          disabled={status === 'loading'}
          className="bg-white/80"
          required
        />

        <Button
          type="submit"
          disabled={status === 'loading'}
          className="w-full rounded-md bg-primary text-base font-bold text-white hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
        >
          {status === 'loading' ? 'Creando cuenta...' : 'Crear cuenta'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-text-muted">
        ¿Ya tienes acceso?{' '}
        <Link href="/login" className="text-link hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60">
          Iniciar sesión
        </Link>
      </p>
    </div>
  )
}
