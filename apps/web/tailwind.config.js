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
        bg: '#0F1A24',
        surface: '#15202B',
        'surface-2': '#1B2A36',
        border: '#243341',
        text: '#E6EDF3',
        'text-muted': '#A7B1BD',
        primary: {
          DEFAULT: '#16E0BD',
          600: '#12BFA0',
          700: '#0E9E85',
        },
        success: '#2ECC71',
        warning: '#F4C430',
        danger: '#FF6B6B',
        link: '#16E0BD',

        // Legacy SAPTIVA colors para compatibilidad
        saptiva: {
          mint: '#16E0BD', // Actualizado a primary del plan
          blue: '#4472C4',
          lightBlue: '#5B9BD5',
          orange: '#ED7D31',
          yellow: '#FFC000',
          green: '#2ECC71', // Actualizado a success del plan
          purple: '#954F72',
          dark: '#0F1A24', // Actualizado a bg del plan
          charcoal: '#15202B', // Actualizado a surface del plan
          slate: '#44546A',
          silver: '#A7B1BD', // Actualizado a text-muted del plan
          light: '#E6EDF3', // Actualizado a text del plan
          hyperlink: '#16E0BD', // Actualizado a link del plan
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
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}