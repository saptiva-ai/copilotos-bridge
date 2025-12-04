/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@copilotos/shared'],
  output: 'standalone',
  trailingSlash: false,
  // Use default .next directory - volume is mounted there in Docker
  generateBuildId: async () => {
    // Force new build ID to bust browser cache after proxy fix
    return `build-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
  },
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
  // Allow all hosts in development and production (for WSL/Docker access)
  experimental: {
    serverActions: {
      allowedOrigins: [
        'localhost:3000',
        '127.0.0.1:3000',
        '*.localhost:3000',
        'invex.saptiva.com',
        'back-invex.saptiva.com',
        '*.saptiva.com',
      ],
    },
  },
  async headers() {
    return [
      {
        // Apply anti-cache headers to all API routes and auth pages
        source: '/(api|auth|login|register)/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0',
          },
          {
            key: 'Pragma',
            value: 'no-cache',
          },
          {
            key: 'Expires',
            value: '0',
          },
          {
            key: 'Surrogate-Control',
            value: 'no-store',
          },
        ],
      },
    ]
  },
  async rewrites() {
    // Enable API proxy when API_BASE_URL is set (Docker) or in development mode
    const apiUrl = process.env.API_BASE_URL || process.env.NEXT_DEV_API_PROXY

    if (apiUrl) {
      // Use API_BASE_URL (internal Docker network) for server-side proxy
      // This avoids CORS issues by proxying through Next.js
      console.log('[Next.js Rewrites] Proxying /api/* to:', apiUrl)
      return [
        {
          // Proxy API calls to backend
          source: '/api/:path*',
          destination: `${apiUrl}/api/:path*`,
        }
      ];
    }

    return [];
  },
}

module.exports = nextConfig
