import type { Metadata } from 'next'

import { RegisterForm } from '../../../components/auth'

export const metadata: Metadata = {
  title: 'Crear cuenta | CopilotOS Bridge',
  description: 'Registra un nuevo acceso para aprovechar las capacidades de CopilotOS Bridge.',
}

export default function RegisterPage() {
  return <RegisterForm />
}
