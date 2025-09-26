import type { Metadata } from 'next'

import { LoginForm } from '../../../components/auth'

export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: 'Iniciar sesión | Copilot OS',
  description: 'Accede a la plataforma Copilot OS con tus credenciales corporativas.',
}

export default function LoginPage() {
  return <LoginForm />
}
