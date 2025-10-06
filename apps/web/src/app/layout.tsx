import { Inter } from 'next/font/google'
import './globals.css'
import { ToasterProvider } from '../components/providers/ToasterProvider'
import { SyncProvider } from '../components/providers/SyncProvider'
import { SessionExpiredToast } from '../components/ui/SessionExpiredToast'

const inter = Inter({ subsets: ['latin'] })

// Force dynamic rendering for the entire app
export const dynamic = 'force-dynamic'
export const revalidate = 0

export const metadata = {
  title: 'Saptiva Copilot OS',
  description: 'Unified conversational interface combining direct LLM interactions with deep research capabilities',
  icons: {
    icon: '/saptiva_ai_logo.jpg',
    shortcut: '/saptiva_ai_logo.jpg',
    apple: '/saptiva_ai_logo.jpg',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        {children}
        <ToasterProvider />
        <SyncProvider />
        <SessionExpiredToast />
      </body>
    </html>
  )
}
