import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // CRITICAL: Never intercept Next.js internal routes or API routes
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname === '/favicon.ico' ||
    pathname === '/robots.txt' ||
    pathname === '/sitemap.xml' ||
    pathname.startsWith('/healthz')
  ) {
    return NextResponse.next();
  }

  // Redirect root to chat (if needed)
  if (pathname === '/') {
    return NextResponse.redirect(new URL('/chat', request.url));
  }

  // Add pathname header for debugging
  const response = NextResponse.next();
  response.headers.set('x-pathname', pathname);

  return response;
}

// DEFENSIVE MATCHER: Exclude Next.js internals and API routes
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, robots.txt, sitemap.xml (static files)
     * - api, healthz routes (API/health routes)
     */
    '/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|api|healthz).*)',
  ],
};