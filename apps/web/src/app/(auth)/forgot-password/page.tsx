import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Recuperar contraseña | Copilot OS',
  description: 'Recupera el acceso a tu cuenta de Copilot OS.',
}

export default function ForgotPasswordPage() {
  return (
    <div className="w-full max-w-md rounded-xl border border-border bg-surface p-8 shadow-card">
      <div className="mb-8 text-center">
        <h2 className="text-2xl font-bold text-text">Recuperar contraseña</h2>
        <p className="mt-2 text-sm text-text-muted">
          Ingresa tu correo electrónico para recibir instrucciones.
        </p>
      </div>

      <form className="space-y-5">
        <div className="space-y-2">
          <label htmlFor="email" className="text-sm font-medium text-text">
            Correo electrónico
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-text placeholder-text-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/60"
            placeholder="tu.nombre@saptiva.ai"
          />
        </div>

        <button
          type="submit"
          className="w-full rounded-md bg-primary px-8 py-3 text-base font-bold text-white transition-colors duration-300 hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
        >
          Enviar instrucciones
        </button>
      </form>
    </div>
  )
}
