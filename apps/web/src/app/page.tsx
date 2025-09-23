'use client'

import Image from 'next/image'
import Link from 'next/link'
import {
  SparklesIcon,
  ShieldCheckIcon,
  PresentationChartLineIcon,
} from '@heroicons/react/24/outline'

const features = [
  {
    title: 'Experiencias Conversacionales Enriquecidas',
    description:
      'Interactúa con los modelos de Saptiva para obtener respuestas estratégicas, análisis profundos y creatividad asistida.',
    icon: SparklesIcon,
  },
  {
    title: 'Investigación Profunda Con Fuentes Verificables',
    description:
      'Activa flujos de investigación con trazabilidad y reportes ejecutivos listos para compartir con tu equipo.',
    icon: PresentationChartLineIcon,
  },
  {
    title: 'Arquitectura Segura y Escalable',
    description:
      'Autenticación robusta, trazabilidad completa y cumplimiento respaldado por la plataforma Copilot OS.',
    icon: ShieldCheckIcon,
  },
]

export default function HomePage() {
  const rawAppName = process.env.NEXT_PUBLIC_APP_NAME ?? 'Copilot OS'
  const appBadgeLabel = rawAppName.replace(/Copilot\s?OS?\s*Bridge/gi, 'Copilot OS')
  const primaryCtaHref = '/login'
  const primaryCtaLabel = 'Iniciar sesión'
  const secondaryCtaHref = '/register'
  const secondaryCtaLabel = 'Crear cuenta'

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-gradient-to-br from-saptiva-dark via-saptiva-slate to-saptiva-dark text-white">
      <div className="absolute inset-0 opacity-20" aria-hidden="true">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(68,114,196,0.45),_transparent_70%)]" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(138,245,212,0.25),_transparent_60%)]" />
      </div>

      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 py-12">
        <div className="mx-auto flex w-full max-w-5xl flex-col items-center text-center">
          <div className="mb-10 flex flex-col items-center">
            <div className="relative mb-6 h-24 w-24">
              <Image
                src="/Saptiva_Logo-05.png"
                alt="Saptiva logo"
                fill
                priority
                sizes="96px"
                className="object-contain drop-shadow-[0_10px_30px_rgba(138,245,212,0.45)]"
              />
            </div>
            <span className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-saptiva-light/80">
              {appBadgeLabel}
            </span>
          </div>

          <h1 className="mb-6 bg-gradient-to-r from-saptiva-mint via-saptiva-lightBlue to-saptiva-blue bg-clip-text text-4xl font-bold text-transparent md:text-6xl">
            Conversaciones inteligentes con poder empresarial
          </h1>

          <p className="mb-10 max-w-3xl text-lg text-saptiva-light md:text-xl">
            Integra la experiencia conversacional de Saptiva con automatizaciones de investigación profunda,
            colaboración segura y capacidades de análisis que potencian a tus equipos.
          </p>

          <div className="mb-16 flex flex-col items-center gap-4 sm:flex-row">
            <Link
              href={primaryCtaHref}
              className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-saptiva-blue to-saptiva-mint px-8 py-3 text-base font-semibold uppercase tracking-wide text-white shadow-lg transition-all duration-300 hover:scale-[1.02] hover:from-saptiva-lightBlue hover:to-saptiva-green focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saptiva-mint/60"
            >
              {primaryCtaLabel}
            </Link>
            <Link
              href={secondaryCtaHref}
              className="inline-flex items-center justify-center rounded-full border border-white/20 px-8 py-3 text-base font-semibold text-white transition-colors duration-300 hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saptiva-mint/60"
            >
              {secondaryCtaLabel}
            </Link>
          </div>
        </div>

        <div className="grid w-full max-w-5xl gap-6 md:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm transition-all duration-300 hover:border-saptiva-mint/60 hover:bg-white/10"
            >
              <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-saptiva-mint/15 text-saptiva-mint">
                <feature.icon className="h-6 w-6" aria-hidden="true" />
              </div>
              <h3 className="mb-2 text-lg font-semibold text-white">{feature.title}</h3>
              <p className="text-sm text-saptiva-light/90">
                {feature.description}
              </p>
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-saptiva-mint/60 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
            </div>
          ))}
        </div>

        <div className="mt-16 grid w-full max-w-4xl gap-6 rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm md:grid-cols-3">
          <div className="text-center">
            <p className="text-3xl font-bold text-white">+50</p>
            <p className="mt-1 text-sm text-saptiva-light/90">Automatizaciones disponibles</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-white">99.9%</p>
            <p className="mt-1 text-sm text-saptiva-light/90">Disponibilidad garantizada</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-white">24/7</p>
            <p className="mt-1 text-sm text-saptiva-light/90">Monitoreo y soporte</p>
          </div>
        </div>
      </div>
    </div>
  )
}
