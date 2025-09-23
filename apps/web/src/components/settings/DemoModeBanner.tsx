'use client'

import * as React from 'react'

import { useSettingsStore } from '../../lib/settings-store'
import { Button } from '../ui'

interface DemoModeBannerProps {
  onOpenSettings: () => void
}

export function DemoModeBanner({ onOpenSettings }: DemoModeBannerProps) {
  const { status } = useSettingsStore()

  if (!status || status.mode !== 'demo') {
    return null
  }

  return (
    <div className="mb-4 rounded-2xl border border-yellow-500/30 bg-yellow-500/15 p-4 text-sm text-yellow-100 backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold uppercase tracking-wide text-yellow-200/90">
            Modo demo activo
          </p>
          <p className="mt-1 text-yellow-100/80">
            Configura una SAPTIVA API key para habilitar respuestas reales del modelo. Actualmente se muestran respuestas de demostración.
          </p>
        </div>
        <Button
          variant="outline"
          className="border-yellow-500/40 bg-yellow-500/20 text-yellow-100 hover:bg-yellow-500/30"
          onClick={onOpenSettings}
        >
          Configurar ahora
        </Button>
      </div>
    </div>
  )
}
