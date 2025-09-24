'use client'

import * as React from 'react'

import type { SaptivaKeyStatus } from '../../lib/types'
import { Input, Button } from '../ui'

interface SaptivaKeyFormProps {
  status: SaptivaKeyStatus | null
  saving: boolean
  error: string | null
  isOpen: boolean
  onSubmit: (apiKey: string) => Promise<boolean>
  onClear: () => Promise<boolean>
  setError: (message: string | null) => void
}

const STATUS_BADGE_CLASSES: Record<'demo' | 'live', string> = {
  demo: 'bg-yellow-500/20 text-yellow-200 border border-yellow-500/30',
  live: 'bg-saptiva-mint/15 text-saptiva-mint border border-saptiva-mint/40',
}

function getStatusBadgeProps(status: SaptivaKeyStatus | null) {
  if (!status) {
    return {
      label: 'Demo mode',
      className: STATUS_BADGE_CLASSES.demo,
    }
  }

  const label = status.mode === 'live' ? 'Live mode' : 'Demo mode'
  const className = STATUS_BADGE_CLASSES[status.mode]

  return { label, className }
}

export function SaptivaKeyForm({
  status,
  saving,
  error,
  isOpen,
  onSubmit,
  onClear,
  setError,
}: SaptivaKeyFormProps) {
  const [value, setValue] = React.useState('')

  const configuredViaEnv = status?.source === 'environment'
  const showClearButton = Boolean(status?.configured && !configuredViaEnv)

  React.useEffect(() => {
    if (isOpen) {
      setValue('')
      setError(null)
    }
  }, [isOpen, setError])

  const handleSubmit = React.useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault()
      const trimmed = value.trim()
      if (!trimmed) {
        setError('Ingresa una API key válida')
        return
      }

      const success = await onSubmit(trimmed)
      if (success) {
        setValue('')
      }
    },
    [value, onSubmit, setError]
  )

  const handleClear = React.useCallback(async () => {
    const result = await onClear()
    if (result) {
      setValue('')
    }
  }, [onClear])

  const { label: badgeLabel, className: badgeClassName } = getStatusBadgeProps(status)

  return (
    <form onSubmit={handleSubmit} className="mt-6 space-y-6" noValidate>
      <section className="rounded-xl border border-white/10 bg-black/30 p-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-saptiva-light/70">
          Estado actual
        </h3>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <span
            data-testid="status-badge"
            className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${badgeClassName}`}
          >
            {badgeLabel}
          </span>
          {status?.hint && (
            <span className="text-xs text-saptiva-light/60" data-testid="status-hint">
              Key: {status.hint}
            </span>
          )}
          {status?.statusMessage && (
            <span className="text-xs text-saptiva-light/60" data-testid="status-message">
              {status.statusMessage}
            </span>
          )}
        </div>
        {configuredViaEnv && (
          <p className="mt-3 rounded-lg border border-saptiva-lightBlue/20 bg-saptiva-lightBlue/10 p-3 text-xs text-saptiva-light/80" data-testid="environment-hint">
            La key actual proviene de las variables de entorno. Puedes sobrescribirla guardando una nueva key desde aquí.
          </p>
        )}
        {(status?.lastValidatedAt || status?.updatedAt) && (
          <dl className="mt-3 grid gap-2 text-xs text-saptiva-light/60" data-testid="status-metadata">
            {status.lastValidatedAt && (
              <div className="flex items-center gap-2">
                <dt className="font-semibold uppercase tracking-wide text-saptiva-light/70">Última validación:</dt>
                <dd>{new Date(status.lastValidatedAt).toLocaleString()}</dd>
              </div>
            )}
            {status.updatedAt && (
              <div className="flex items-center gap-2">
                <dt className="font-semibold uppercase tracking-wide text-saptiva-light/70">Actualizada:</dt>
                <dd>{new Date(status.updatedAt).toLocaleString()}</dd>
              </div>
            )}
          </dl>
        )}
      </section>

      <section className="space-y-3">
        <label htmlFor="saptiva-key" className="block text-sm font-medium text-white/90">
          SAPTIVA API Key
        </label>
        <Input
          id="saptiva-key"
          name="saptiva-key"
          type="password"
          value={value}
          onChange={(event) => {
            setValue(event.target.value)
            if (error) {
              setError(null)
            }
          }}
          placeholder="va-ai-..."
          autoComplete="off"
          spellCheck={false}
          className="border-white/20 bg-black/30 text-white placeholder:text-saptiva-light/50"
        />
        <p className="text-xs text-saptiva-light/60">
          La key se valida contra SAPTIVA y se almacena cifrada. Solo usuarios autenticados pueden modificarla.
        </p>
      </section>

      {error && (
        <div className="rounded-lg border border-red-400/30 bg-red-500/10 p-3 text-xs text-red-200" role="alert">
          {error}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs text-saptiva-light/50">
          Usa <kbd className="rounded bg-white/10 px-1.5 py-0.5 text-[10px]">⌘K</kbd> / <kbd className="rounded bg-white/10 px-1.5 py-0.5 text-[10px]">Ctrl+K</kbd> para abrir este modal rápidamente.
        </div>
        <div className="flex items-center gap-2">
          {showClearButton && (
            <Button
              type="button"
              variant="ghost"
              onClick={handleClear}
              disabled={saving}
              className="border border-white/10 bg-black/30 text-saptiva-light/80 hover:bg-black/40"
            >
              Eliminar key
            </Button>
          )}
          <Button type="submit" loading={saving} disabled={saving}>
            Guardar API Key
          </Button>
        </div>
      </div>
    </form>
  )
}
