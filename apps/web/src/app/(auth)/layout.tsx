import type { ReactNode } from 'react'

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-bg text-text">
      <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col items-center justify-center gap-10 px-4">
        <div className="flex flex-col items-center text-center">
          <h1 className="text-3xl font-semibold">CopilotOS</h1>
          <p className="mt-2 text-sm text-text-muted">
            Experiencia conversacional y de investigación profunda en una sola plataforma.
          </p>
        </div>

        <div className="w-full max-w-md">
          {children}
        </div>
      </div>
    </div>
  )
}
