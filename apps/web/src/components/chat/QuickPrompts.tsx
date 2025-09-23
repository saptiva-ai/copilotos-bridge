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
  research: 'bg-blue-50 border-blue-200 hover:bg-blue-100',
  business: 'bg-green-50 border-green-200 hover:bg-green-100',
  coding: 'bg-purple-50 border-purple-200 hover:bg-purple-100',
  writing: 'bg-orange-50 border-orange-200 hover:bg-orange-100',
  data: 'bg-teal-50 border-teal-200 hover:bg-teal-100',
  problem: 'bg-rose-50 border-rose-200 hover:bg-rose-100',
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
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
          ¿En qué puedo ayudarte hoy?
        </h2>
        <p className="text-gray-600">
          Selecciona uno de estos ejemplos o escribe tu propia consulta
        </p>
      </div>

      {/* Desktop Grid (2-4 columns) */}
      <div className="hidden md:grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 gap-4 mb-6">
        {QUICK_PROMPTS.map((prompt) => (
          <button
            key={prompt.id}
            onClick={() => handlePromptClick(prompt)}
            className={`
              p-6 rounded-2xl border-2 text-left transition-all duration-200
              hover:scale-105 hover:shadow-lg focus:outline-none focus:ring-2
              focus:ring-blue-500 focus:ring-offset-2
              ${CATEGORY_COLORS[prompt.category as keyof typeof CATEGORY_COLORS]}
            `}
          >
            <div className="flex items-start gap-3">
              <span className="text-2xl">{prompt.icon}</span>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 mb-1">
                  {prompt.title}
                </h3>
                <p className="text-sm text-gray-600 mb-3">
                  {prompt.description}
                </p>
                <p className="text-xs text-gray-500 overflow-hidden" style={{
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
                flex-shrink-0 px-4 py-3 rounded-full border text-sm font-medium
                transition-all duration-200 hover:scale-105 focus:outline-none
                focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 whitespace-nowrap
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
          <p className="text-sm text-gray-500">
            Desliza para ver más ejemplos →
          </p>
        </div>
      </div>

      {/* Additional Help Text */}
      <div className="text-center mt-8">
        <p className="text-sm text-gray-500">
          💡 También puedes activar <strong>Deep Research</strong> para investigaciones profundas
        </p>
      </div>
    </div>
  )
}

export default QuickPrompts