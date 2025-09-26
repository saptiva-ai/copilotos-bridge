import type { Metadata } from 'next'

import { RegisterForm } from '../../../components/auth'

export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: 'Crear cuenta | Copilot OS',
  description: 'Registra un nuevo acceso para aprovechar las capacidades de Copilot OS.',
}

export default function RegisterPage() {
  return <RegisterForm />
}
