'use client'

import * as React from 'react'
import { Dialog, Transition } from '@headlessui/react'

import { useSettingsStore } from '../../lib/settings-store'
import { SaptivaKeyForm } from './SaptivaKeyForm'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { status, saving, error, saveApiKey, clearApiKey, setError } = useSettingsStore()

  const handleSubmit = React.useCallback(
    async (apiKey: string) => {
      const success = await saveApiKey({ apiKey, validate: true })
      if (success) {
        onClose()
      }
      return success
    },
    [saveApiKey, onClose]
  )

  const handleClear = React.useCallback(async () => {
    return clearApiKey()
  }, [clearApiKey])

  const handleClose = React.useCallback(() => {
    setError(null)
    onClose()
  }, [setError, onClose])

  return (
    <Transition.Root show={isOpen} as={React.Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose}>
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
                <SaptivaKeyForm
                  status={status}
                  saving={saving}
                  error={error}
                  isOpen={isOpen}
                  onSubmit={handleSubmit}
                  onClear={handleClear}
                  setError={setError}
                />
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}
