"use client";

import Image from "next/image";
import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col items-center justify-center gap-10 px-4">
        {/* Logos OctaviOS + Bajaware - side by side, centered */}
        <div className="flex items-center gap-4">
          <div className="relative h-48 w-48">
            {/* Light theme logo - hidden in dark mode */}
            <Image
              src="/OctaviOS_WhiteBack2.png"
              alt="OctaviOS Chat"
              fill
              priority
              sizes="192px"
              className="object-contain drop-shadow-[0_10px_30px_rgba(45,212,191,0.45)] dark:hidden"
            />
            {/* Dark theme logo - hidden in light mode */}
            <Image
              src="/OctaviOS_DarkBack2.png"
              alt="OctaviOS Chat"
              fill
              priority
              sizes="192px"
              className="object-contain drop-shadow-[0_10px_30px_rgba(45,212,191,0.45)] hidden dark:block"
            />
          </div>

          {/* Partner logo Bajaware - smaller, beside OctaviOS */}
          <div className="relative h-12 w-52">
            {/* Light theme: blue logo */}
            <Image
              src="/bajaware-logo-blue.png"
              alt="Bajaware"
              fill
              priority
              sizes="128px"
              className="object-contain dark:hidden"
            />
            {/* Dark theme: white logo */}
            <Image
              src="/bajaware-logo-white.png"
              alt="Bajaware"
              fill
              priority
              sizes="128px"
              className="object-contain hidden dark:block"
            />
          </div>
        </div>

        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}
