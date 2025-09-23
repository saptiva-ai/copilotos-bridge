'use client'

import * as React from 'react'
import { Dialog, Transition } from '@headlessui/react'

import { useSettingsStore } from '../../lib/settings-store'
import { Button, Input } from '../ui'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const {
    status,
    saving,
    error,
    saveApiKey,
    clearApiKey,
    setError,
  } = useSettingsStore()

  const [apiKey, setApiKey] = React.useState('')

  React.useEffect(() => {
    if (isOpen) {
      setApiKey('')
      setError(null)
    }
  }, [isOpen, setError])

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!apiKey.trim()) {
      setError('Ingresa una API key válida')
      return
    }

    const success = await saveApiKey({ apiKey: apiKey.trim(), validate: true })
    if (success) {
      setApiKey('')
      onClose()
    }
  }

  const handleClear = async () => {
    await clearApiKey()
  }

  const isConfigured = status?.configured ?? false
  const configuredViaEnv = status?.source === 'environment'

  return (
    <Transition.Root show={isOpen} as={React.Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={React.Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/50" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={React.Fragment}
              enter="ease-out duration-200"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-150"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="w-full max-w-xl transform overflow-hidden rounded-2xl border border-white/10 bg-saptiva-dark/95 p-6 text-left align-middle shadow-xl transition-all">
                <Dialog.Title as="h2" className="text-xl font-semibold text-white">
                  Configurar SAPTIVA API Key
                </Dialog.Title>
                <Dialog.Description className="mt-1 text-sm text-saptiva-light/70">
                  Proporciona una API key válida para habilitar respuestas reales del modelo SAPTIVA.
                </Dialog.Description>

                <form onSubmit={handleSubmit} className="mt-6 space-y-6">
                  <section className="rounded-xl border border-white/10 bg-black/30 p-4">
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-saptiva-light/70">
                      Estado actual
                    </h3>
                    <div className="mt-3 flex flex-wrap items-center gap-3">
                      <span
                        className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                          isConfigured
                            ? 'bg-saptiva-mint/15 text-saptiva-mint'
                            : 'bg-yellow-500/20 text-yellow-200'
                        }`}
                      >
                        {isConfigured ? 'Live mode' : 'Demo mode'}
                      </span>
                      {status?.hint && (
                        <span className="text-xs text-saptiva-light/60">
                          Key: {status.hint}
                        </span>
                      )}
                      {status?.statusMessage && (
                        <span className="text-xs text-saptiva-light/60">
                          {status.statusMessage}
                        </span>
                      )}
                    </div>
                    {configuredViaEnv && (
                      <p className="mt-3 rounded-lg border border-saptiva-lightBlue/20 bg-saptiva-lightBlue/10 p-3 text-xs text-saptiva-light/80">
                        La key actual proviene de las variables de entorno. Puedes sobrescribirla guardando una nueva key desde aquí.
                      </p>
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
                      value={apiKey}
                      onChange={(event) => setApiKey(event.target.value)}
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
                    <div className="rounded-lg border border-red-400/30 bg-red-500/10 p-3 text-xs text-red-200">
                      {error}
                    </div>
                  )}

                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="text-xs text-saptiva-light/50">
                      Usa <kbd className="rounded bg-white/10 px-1.5 py-0.5 text-[10px]">⌘K</kbd> / <kbd className="rounded bg-white/10 px-1.5 py-0.5 text-[10px]">Ctrl+K</kbd> para abrir este modal rápidamente.
                    </div>
                    <div className="flex items-center gap-2">
                      {isConfigured && !configuredViaEnv && (
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
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}
