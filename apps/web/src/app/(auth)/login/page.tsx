import type { Metadata } from 'next'

import { LoginForm } from '../../../components/auth'

export const metadata: Metadata = {
  title: 'Iniciar sesión | CopilotOS Bridge',
  description: 'Accede a la plataforma CopilotOS Bridge con tus credenciales corporativas.',
}

export default function LoginPage() {
  return <LoginForm />
}
