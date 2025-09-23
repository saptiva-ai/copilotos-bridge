import Image from 'next/image'
import type { ReactNode } from 'react'

const authHighlights = [
  {
    title: 'Acceso unificado',
    description: 'Gestiona conversaciones y tareas de investigación desde un mismo panel.',
  },
  {
    title: 'Seguridad empresarial',
    description: 'Autenticación basada en estándares y cifrado extremo a extremo.',
  },
  {
    title: 'Escalabilidad garantizada',
    description: 'Arquitectura preparada para equipos de cualquier tamaño dentro de tu organización.',
  },
]

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-saptiva-dark via-saptiva-slate to-saptiva-dark px-4 py-12">
      <div className="mx-auto grid w-full max-w-6xl items-center gap-10 md:grid-cols-[1.1fr_1fr]">
        <div className="hidden rounded-3xl border border-white/10 bg-white/5 p-10 text-white shadow-2xl backdrop-blur-lg md:flex md:flex-col">
          <div className="mb-10 flex items-center space-x-4">
            <div className="relative h-14 w-14">
              <Image
                src="/Saptiva_Logo-05.png"
                alt="Saptiva logo"
                fill
                sizes="56px"
                className="object-contain"
                priority
              />
            </div>
            <div>
              <p className="text-sm uppercase tracking-[0.4em] text-saptiva-light/80">Saptiva</p>
              <h2 className="text-2xl font-semibold">CopilotOS Bridge</h2>
            </div>
          </div>

          <h3 className="text-3xl font-bold leading-snug text-saptiva-light">
            Conecta a tus equipos con inteligencia conversacional y flujos de investigación confiables.
          </h3>

          <div className="mt-10 space-y-6">
            {authHighlights.map((item) => (
              <div key={item.title} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <h4 className="text-lg font-semibold text-white">{item.title}</h4>
                <p className="mt-2 text-sm text-saptiva-light/80">{item.description}</p>
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
