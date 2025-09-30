/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@copilotos/shared'],
  output: 'standalone',
  trailingSlash: false,
  // Use default .next directory - volume is mounted there in Docker
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
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
    // SAFE REWRITES: Never intercept /_next, /api, or static files
    if (process.env.NODE_ENV === 'development') {
      // Use API_BASE_URL (internal Docker network) for server-side proxy
      // This avoids CORS issues by proxying through Next.js
      const apiUrl = process.env.API_BASE_URL || 'http://api:8001'
      console.log('[Next.js Rewrites] Proxying /api/* to:', apiUrl)
      return [
        {
          // Proxy API calls to backend in dev
          source: '/api/:path*',
          destination: `${apiUrl}/api/:path*`,
        }
      ];
    }
    return [];
  },
}

module.exports = nextConfig