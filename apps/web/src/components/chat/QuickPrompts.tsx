'use client'

import React from 'react'

interface QuickPrompt {
  id: string
  title: string
  description: string
  prompt: string
  category: string
  icon?: string
}

interface QuickPromptsProps {
  onPromptSelect: (prompt: string) => void
  className?: string
}

const QUICK_PROMPTS: QuickPrompt[] = [
  {
    id: 'research-tech',
    title: 'Investigación Tecnológica',
    description: 'Investigar tecnologías emergentes',
    prompt: 'Investiga las últimas tendencias en inteligencia artificial y machine learning para 2025',
    category: 'research',
    icon: '🔬'
  },
  {
    id: 'business-analysis',
    title: 'Análisis de Negocio',
    description: 'Analizar oportunidades de mercado',
    prompt: 'Analiza las oportunidades de mercado en el sector fintech en América Latina',
    category: 'business',
    icon: '📊'
  },
  {
    id: 'code-review',
    title: 'Revisión de Código',
    description: 'Revisar y optimizar código',
    prompt: 'Revisa este código Python y sugiere mejoras de rendimiento y legibilidad',
    category: 'coding',
    icon: '💻'
  },
  {
    id: 'creative-writing',
    title: 'Escritura Creativa',
    description: 'Crear contenido original',
    prompt: 'Escribe un artículo técnico sobre las mejores prácticas en desarrollo de APIs REST',
    category: 'writing',
    icon: '✍️'
  },
  {
    id: 'data-analysis',
    title: 'Análisis de Datos',
    description: 'Interpretar datasets y métricas',
    prompt: 'Ayúdame a analizar patrones en datos de ventas e identificar insights clave',
    category: 'data',
    icon: '📈'
  },
  {
    id: 'problem-solving',
    title: 'Resolución de Problemas',
    description: 'Encontrar soluciones creativas',
    prompt: 'Necesito resolver un problema de escalabilidad en mi aplicación web',
    category: 'problem',
    icon: '🧩'
  }
]

const CATEGORY_COLORS = {
  research: 'bg-blue-900/20 border-blue-400/20 hover:bg-blue-800/30 text-blue-200',
  business: 'bg-green-900/20 border-green-400/20 hover:bg-green-800/30 text-green-200',
  coding: 'bg-purple-900/20 border-purple-400/20 hover:bg-purple-800/30 text-purple-200',
  writing: 'bg-orange-900/20 border-orange-400/20 hover:bg-orange-800/30 text-orange-200',
  data: 'bg-teal-900/20 border-teal-400/20 hover:bg-teal-800/30 text-teal-200',
  problem: 'bg-rose-900/20 border-rose-400/20 hover:bg-rose-800/30 text-rose-200',
}

export function QuickPrompts({ onPromptSelect, className = '' }: QuickPromptsProps) {
  const handlePromptClick = (prompt: QuickPrompt) => {
    // Analytics event
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'example_clicked', {
        prompt_id: prompt.id,
        category: prompt.category,
        title: prompt.title
      })
    }

    onPromptSelect(prompt.prompt)
  }

  return (
    <div className={`w-full max-w-4xl mx-auto ${className}`}>
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-2xl font-semibold text-white mb-2">
          ¿En qué puedo ayudarte hoy?
        </h2>
        <p className="text-saptiva-light/70">
          Selecciona uno de estos ejemplos o escribe tu propia consulta
        </p>
      </div>

      {/* Desktop Grid (2-4 columns) using SAPTIVA tokens */}
      <div className="hidden md:grid grid-responsive mb-6">
        {QUICK_PROMPTS.map((prompt) => (
          <button
            key={prompt.id}
            onClick={() => handlePromptClick(prompt)}
            className={`
              card-interactive text-left focus:outline-none focus:ring-2
              focus:ring-saptiva-mint/60 focus:ring-offset-2 focus:ring-offset-saptiva-dark
              ${CATEGORY_COLORS[prompt.category as keyof typeof CATEGORY_COLORS]}
            `}
          >
            <div className="flex items-start gap-3">
              <span className="text-2xl">{prompt.icon}</span>
              <div className="flex-1">
                <h3 className="font-semibold text-white mb-1">
                  {prompt.title}
                </h3>
                <p className="text-sm text-saptiva-light/70 mb-3">
                  {prompt.description}
                </p>
                <p className="text-xs text-saptiva-light/60 overflow-hidden" style={{
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                }}>
                  "{prompt.prompt}"
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Mobile Horizontal Chips (≤600px) */}
      <div className="md:hidden">
        <div
          className="flex gap-3 overflow-x-auto pb-4"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        >
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt.id}
              onClick={() => handlePromptClick(prompt)}
              className={`
                chip flex-shrink-0 border whitespace-nowrap
                transition-all duration-200 hover:scale-105 focus:outline-none
                focus:ring-2 focus:ring-saptiva-mint/60 focus:ring-offset-2 focus:ring-offset-saptiva-dark
                ${CATEGORY_COLORS[prompt.category as keyof typeof CATEGORY_COLORS]}
              `}
            >
              <span className="mr-2">{prompt.icon}</span>
              {prompt.title}
            </button>
          ))}
        </div>

        {/* Mobile Description */}
        <div className="mt-4 text-center">
          <p className="text-sm text-saptiva-light/60">
            Desliza para ver más ejemplos →
          </p>
        </div>
      </div>

      {/* Additional Help Text */}
      <div className="text-center mt-8">
        <p className="text-sm text-saptiva-light/60">
          💡 También puedes activar <strong className="text-saptiva-mint">Deep Research</strong> para investigaciones profundas
        </p>
      </div>
    </div>
  )
}

export default QuickPrompts