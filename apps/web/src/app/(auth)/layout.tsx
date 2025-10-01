import Image from 'next/image'
import type { ReactNode } from 'react'

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-bg text-text">
      <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col items-center justify-center gap-10 px-4">
        {/* Logo Saptiva */}
        <div className="flex flex-col items-center">
          <div className="relative h-20 w-20">
            <Image
              src="/Saptiva_AI_logo_new.webp"
              alt="Saptiva AI"
              fill
              priority
              sizes="80px"
              className="object-contain"
            />
          </div>
        </div>

        <div className="w-full max-w-md">
          {children}
        </div>
      </div>
    </div>
  )
}
