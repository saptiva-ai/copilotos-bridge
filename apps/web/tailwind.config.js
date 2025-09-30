/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme palette según plan-ui.yaml TOK-01
        bg: '#0B1217',
        surface: '#121A21',
        'surface-2': '#18222C',
        border: '#1F2A33',
        text: '#E6E8EB',
        'text-muted': '#9AA4AF',
        primary: {
          DEFAULT: '#49F7D9',
          600: '#2DC4AE',
          700: '#1EA595',
        },
        success: '#49F7D9',
        warning: '#F4C430',
        danger: '#F87171',
        link: '#49F7D9',

        // Legacy SAPTIVA colors para compatibilidad
        saptiva: {
          mint: '#49F7D9',
          blue: '#4472C4',
          lightBlue: '#5B9BD5',
          orange: '#ED7D31',
          yellow: '#FFC000',
          green: '#49F7D9',
          purple: '#954F72',
          dark: '#0B1217',
          charcoal: '#121A21',
          slate: '#44546A',
          silver: '#9AA4AF',
          light: '#E6E8EB',
          hyperlink: '#49F7D9',
        },

        // Grays mantenidos para elementos neutros
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
        },
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'ui-sans-serif', 'system-ui'], // SAPTIVA Lab token system
        mono: ['Fira Code', 'monospace'],
      },
      maxWidth: {
        'container': '1200px', // SAPTIVA container token
      },
      fontSize: {
        // Escala tipográfica específica del plan: sm:13, base:15, lg:18, xl:24
        sm: ['13px', { lineHeight: '18px' }],
        base: ['15px', { lineHeight: '22px' }],
        lg: ['18px', { lineHeight: '26px' }],
        xl: ['24px', { lineHeight: '32px' }],
        // Mantenemos tamaños adicionales para flexibilidad
        xs: ['12px', { lineHeight: '16px' }],
        '2xl': ['32px', { lineHeight: '40px' }],
        '3xl': ['40px', { lineHeight: '48px' }],
      },
      fontWeight: {
        // Weights específicos del Lab: 400/700 solamente
        normal: '400',
        bold: '700',
      },
      borderRadius: {
        // SAPTIVA token system según plan (card: 12px)
        'sm': '8px',
        'md': '12px',       // Radius principal del plan
        'lg': '16px',
        'xl': '12px',       // Para cards según plan
        'none': '0',
        'DEFAULT': '0.25rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
        'full': '9999px',
      },
      boxShadow: {
        // Shadow específica del plan
        'card': '0 6px 20px rgba(0,0,0,0.24)',
        // Mantener shadows estándar
        'sm': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        'DEFAULT': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        'md': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
        'lg': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
        'none': 'none',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'typing': 'typing 1.5s steps(30, end) infinite',
        'fade-in': 'fadeIn 0.6s ease-in-out',
        // P0-UX-HIST-001: Highlight animation for new conversations
        'highlight-fade': 'highlightFade 2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        typing: {
          '0%, 50%': { opacity: '1' },
          '51%, 100%': { opacity: '0' },
        },
        // P0-UX-HIST-001: Highlight fade keyframes
        highlightFade: {
          '0%': { backgroundColor: 'rgba(73, 247, 217, 0.15)', borderColor: 'rgba(73, 247, 217, 0.6)' },
          '100%': { backgroundColor: 'rgba(73, 247, 217, 0)', borderColor: 'transparent' },
        },
      },
    },
  },
  plugins: [
    (() => {
      try {
        return require('@tailwindcss/forms')
      } catch (error) {
        console.warn('[@tailwindcss/forms] plugin not found, continuing without it.')
        return null
      }
    })(),
    (() => {
      try {
        return require('@tailwindcss/typography')
      } catch (error) {
        console.warn('[@tailwindcss/typography] plugin not found, continuing without it.')
        return null
      }
    })(),
  ].filter(Boolean),
}
