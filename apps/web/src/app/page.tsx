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
    title: 'Acceso',
    description:
      'Interfaz para interactuar con modelos SAPTIVA mediante chat.',
    icon: SparklesIcon,
  },
  {
    title: 'Investigación',
    description:
      'Herramientas de deep research con trazabilidad de fuentes.',
    icon: PresentationChartLineIcon,
  },
  {
    title: 'Seguridad',
    description:
      'Autenticación y gestión de sesiones para equipos.',
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
    <div className="relative min-h-screen overflow-x-hidden bg-bg text-text">

      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 py-12">
        <div className="mx-auto flex w-full max-w-5xl flex-col items-center text-center">
          <div className="mb-8 flex flex-col items-center">
            <div className="relative mb-2 h-48 w-48">
              <Image
                src="/Saptiva_AI_logo_new.webp"
                alt="Saptiva AI logo"
                fill
                priority
                sizes="192px"
                className="object-contain drop-shadow-[0_10px_30px_rgba(73,247,217,0.45)]"
              />
            </div>
          </div>

          <h1 className="mb-6 text-xl font-bold text-text">
            Acceso a Copilot
          </h1>

          <p className="mb-10 max-w-3xl text-base text-text-muted">
            Interfaz para interactuar con modelos de lenguaje y herramientas de investigación.
          </p>

          <div className="mb-16 flex flex-col items-center gap-4 sm:flex-row">
            <Link
              href={primaryCtaHref}
              className="inline-flex items-center justify-center rounded-md bg-primary px-8 py-3 text-base font-bold text-white transition-colors duration-300 hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
            >
              {primaryCtaLabel}
            </Link>
            <Link
              href={secondaryCtaHref}
              className="inline-flex items-center justify-center rounded-md border border-border px-8 py-3 text-base font-normal text-text transition-colors duration-300 hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
            >
              {secondaryCtaLabel}
            </Link>
          </div>
        </div>

        <div className="grid w-full max-w-5xl gap-6 md:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="group relative overflow-hidden rounded-xl border border-border bg-surface p-6 transition-all duration-300 hover:border-primary/60 hover:bg-surface-2"
            >
              <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary/15 text-primary">
                <feature.icon className="h-6 w-6" aria-hidden="true" />
              </div>
              <h3 className="mb-2 text-base font-bold text-text">{feature.title}</h3>
              <p className="text-sm text-text-muted">
                {feature.description}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-16 rounded-xl border border-border bg-surface p-6 text-center">
          <p className="text-sm text-text-muted">Plataforma desarrollada por Saptiva Inc.</p>
        </div>
      </div>
    </div>
  )
}
