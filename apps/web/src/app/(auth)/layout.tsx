import Image from 'next/image'
import type { ReactNode } from 'react'

const authHighlights = [
  {
    title: 'Acceso',
    description: 'Interfaz unificada para conversaciones e investigación.',
  },
  {
    title: 'Seguridad',
    description: 'Autenticación y gestión de sesiones.',
  },
  {
    title: 'Documentación',
    description: 'Guías y recursos para equipos.',
  },
]

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="safe-area-top min-h-screen bg-bg px-4 py-12">
      <div className="mx-auto grid w-full max-w-6xl items-center gap-10 md:grid-cols-[1.1fr_1fr]">
        <div className="hidden rounded-xl border border-border bg-surface p-10 text-text shadow-card md:flex md:flex-col">
          <div className="mb-10 flex items-center space-x-4">
            <div className="relative h-14 w-14">
              <Image
                src="/Saptiva_Logo-05.png"
                alt="Saptiva logo"
                fill
                sizes="56px"
                className="object-contain"
              />
            </div>
            <div>
              <p className="text-sm uppercase tracking-[0.4em] text-text-muted">Saptiva</p>
              <h2 className="text-2xl font-bold">Copilot OS</h2>
            </div>
          </div>

          <h3 className="text-3xl font-bold leading-snug text-text">
            Plataforma SAPTIVA para equipos.
          </h3>

          <div className="mt-10 space-y-6">
            {authHighlights.map((item) => (
              <div key={item.title} className="rounded-xl border border-border bg-surface-2 p-5">
                <h4 className="text-lg font-bold text-text">{item.title}</h4>
                <p className="mt-2 text-sm text-text-muted">{item.description}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-center">
          {children}
        </div>
      </div>
    </div>
  )
}
