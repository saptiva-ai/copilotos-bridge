/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@copilotos/shared'],
  output: 'standalone',
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
  async rewrites() {
    // Solo usar rewrite en desarrollo, en producción usar nginx
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/:path*`,
        },
      ];
    }
    return [];
  },
}

module.exports = nextConfig