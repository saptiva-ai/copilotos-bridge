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
        primary: {
          50: '#f0fdf9',
          100: '#dbf9f0',
          200: '#b8f2e1',
          300: '#8af5d4',
          400: '#56e3c2',
          500: '#34d1a8',
          600: '#28b893',
          700: '#259b7e',
          800: '#1e7a66',
          900: '#1b6454',
        },
        secondary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#4472c4',
          600: '#3b63b3',
          700: '#324e96',
          800: '#2a3f7a',
          900: '#1e2d5f',
        },
        saptiva: {
          mint: '#8AF5D4',
          blue: '#4472C4',
          lightBlue: '#5B9BD5',
          orange: '#ED7D31',
          yellow: '#FFC000',
          green: '#70AD47',
          purple: '#954F72',
          dark: '#1B1B27',
          charcoal: '#3C3939',
          slate: '#44546A',
          silver: '#A5A5A5',
          light: '#E7E6E6',
          hyperlink: '#0563C1',
        },
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
        sans: ['Inter', 'ui-sans-serif', 'system-ui'], // SAPTIVA token system
        mono: ['Fira Code', 'monospace'],
      },
      maxWidth: {
        'container': '1200px', // SAPTIVA container token
      },
      fontSize: {
        // Escala tipográfica específica del Lab: 12/14/16/18/20/24/32/40
        xs: ['12px', { lineHeight: '16px' }],
        sm: ['14px', { lineHeight: '20px' }],
        base: ['16px', { lineHeight: '24px' }],
        lg: ['18px', { lineHeight: '28px' }],
        xl: ['20px', { lineHeight: '28px' }],
        '2xl': ['24px', { lineHeight: '32px' }],
        '3xl': ['32px', { lineHeight: '40px' }],
        '4xl': ['40px', { lineHeight: '48px' }],
      },
      fontWeight: {
        // Weights específicos del Lab: 400/600
        normal: '400',
        semibold: '600',
      },
      borderRadius: {
        // SAPTIVA token system
        'sm': '8px',        // SAPTIVA sm token
        'md': '12px',       // SAPTIVA md token
        'lg': '16px',       // SAPTIVA lg token
        // Legacy support
        'lab-sm': '12px',   // Para chips y elementos pequeños
        'lab': '14px',      // Radius estándar
        'lab-lg': '16px',   // Para inputs y elementos grandes
        'none': '0',
        'DEFAULT': '0.25rem',
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
        'full': '9999px',
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