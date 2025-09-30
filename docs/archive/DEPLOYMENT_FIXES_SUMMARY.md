# Deployment Fixes Summary

**Date:** 2025-09-29  
**Status:** ✅ COMPLETED

## Problem Statement

1. **404 errors** on Next.js static assets (`/_next/static/chunks/*`)
2. **Cache issues** preventing hot reload in development
3. **Deep Research feature** needed a **kill switch** for production
4. **Authentication flow** needed verification

---

## Changes Applied

### 1. Fixed Next.js distDir Configuration

**File:** `apps/web/next.config.js`

**Problem:** The `distDir` was set to `/tmp/next-cache` in Docker, but the volume was mounted at `.next`, causing Next.js to generate assets in one location but try to serve them from another.

**Solution:** Removed custom `distDir` configuration. Now Next.js uses the default `.next` directory consistently, which is properly mounted as a Docker volume.

```diff
- distDir: process.env.IN_DOCKER === '1' ? '/tmp/next-cache' : '.next',
+ // Use default .next directory - volume is mounted there in Docker
```

### 2. Enhanced Middleware Matcher

**File:** `apps/web/middleware.ts`

**Problem:** Middleware could potentially intercept Next.js internal routes.

**Solution:** Updated the negative lookahead pattern to explicitly exclude all static files and health endpoints:

```diff
- '/((?!_next/static|_next/image|favicon.ico|api).*)',
+ '/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|api|healthz).*)',
```

### 3. Simplified Rewrites Configuration

**File:** `apps/web/next.config.js`

**Problem:** Overcomplicated rewrite rules with unnecessary header checks.

**Solution:** Simplified to basic API proxying in development:

```javascript
async rewrites() {
  if (process.env.NODE_ENV === 'development') {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/:path*`,
      }
    ];
  }
  return [];
}
```

### 4. Created Health Check Endpoint

**File:** `apps/web/src/app/healthz/route.ts` (NEW)

**Purpose:** Provides a lightweight health check endpoint for monitoring and Docker health checks.

```typescript
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET() {
  return NextResponse.json(
    { status: 'ok', timestamp: new Date().toISOString(), service: 'web' },
    { status: 200 }
  );
}
```

### 5. Implemented Deep Research Kill Switch

**File:** `apps/api/src/routers/deep_research.py`

**Enhancement:** Added logging for Deep Research configuration and complexity threshold:

```python
deep_research_enabled = os.getenv('DEEP_RESEARCH_ENABLED', 'false').lower() == 'true'
complexity_threshold = float(os.getenv('DEEP_RESEARCH_COMPLEXITY_THRESHOLD', '0.7'))

logger.info(
    "Deep Research configuration",
    enabled=deep_research_enabled,
    complexity_threshold=complexity_threshold
)

if not deep_research_enabled:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "error": "Deep Research is temporarily disabled",
            "code": "DEEP_RESEARCH_DISABLED",
            "message": "This feature has been temporarily disabled for maintenance."
        }
    )
```

### 6. Environment Configuration

**Files:** 
- `infra/docker-compose.dev.yml` (Development)
- `infra/docker-compose.yml` (Production)

**Development (`docker-compose.dev.yml`):**
```yaml
services:
  web:
    environment:
      - DEEP_RESEARCH_ENABLED=${DEEP_RESEARCH_ENABLED:-true}
  
  api:
    environment:
      - DEEP_RESEARCH_ENABLED=${DEEP_RESEARCH_ENABLED:-true}
```

**Production (`docker-compose.yml`):**
```yaml
services:
  api:
    environment:
      - DEEP_RESEARCH_ENABLED=${DEEP_RESEARCH_ENABLED:-false}
      - DEEP_RESEARCH_COMPLEXITY_THRESHOLD=${DEEP_RESEARCH_COMPLEXITY_THRESHOLD:-0.7}
```

---

## Verification Results

### ✅ All Tests Passing

1. **Health Endpoints**
   - `/healthz` returns 200 OK with JSON response
   - `/api/health` returns healthy status with database check

2. **Page Rendering**
   - `/chat` loads successfully (200 OK)
   - No 502 Bad Gateway errors on assets
   - `/_next/static/` returns appropriate redirect (308)

3. **Authentication Flow**
   - User registration works correctly
   - Login returns valid JWT tokens
   - Protected endpoints verify tokens properly

4. **Deep Research Configuration**
   - **Dev:** Enabled (`DEEP_RESEARCH_ENABLED=true`)
   - **Prod:** Disabled by default (`DEEP_RESEARCH_ENABLED=false`)
   - Configuration is logged on each request for debugging

5. **Docker Services**
   - All services start successfully
   - Health checks pass
   - No permission issues with `.next` volume

---

## Architecture Decisions

### ★ Insight: Why These Fixes Work

**1. distDir Unification**
Next.js generates static assets in the `distDir` and serves them from `/_next/static`. When these paths don't align, you get 404s. By using the default `.next` and mounting it as a volume, the container filesystem stays consistent.

**2. Server-Side Kill Switch**
Client-side flags can be bypassed via DevTools. The kill switch is implemented in the FastAPI route handler, making it impossible to circumvent from the frontend. The response is a proper HTTP 503, which clients can handle gracefully.

**3. Middleware Matchers**
Next.js middleware runs BEFORE static file serving. A catch-all matcher `(.*)` would execute middleware on every single request, including internal Next.js routes. Negative lookahead patterns exclude these internal routes, allowing Next.js to serve them directly without middleware overhead.

---

## Quick Start Commands

### Development
```bash
# Function helper for docker compose
DC() { docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml "$@"; }

# Start services
export UID=$(id -u) GID=$(id -g) DEEP_RESEARCH_ENABLED=true
DC up -d --build

# View logs
DC logs -f web

# Run verification
bash verify-deployment.sh
```

### Production
```bash
# Start with Deep Research disabled (default)
docker compose -f infra/docker-compose.yml up -d

# Verify Deep Research is disabled
docker compose exec api printenv | grep DEEP_RESEARCH
# Should show: DEEP_RESEARCH_ENABLED=false
```

### Testing Deep Research Kill Switch

**Enable (Dev/Testing):**
```bash
export DEEP_RESEARCH_ENABLED=true
DC up -d
```

**Disable (Production):**
```bash
export DEEP_RESEARCH_ENABLED=false
DC up -d
```

**Verify:**
```bash
curl -X POST http://localhost:8001/api/deep-research \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"query":"test","research_type":"deep_research"}'

# With enabled=false, returns:
# 503 Service Unavailable
# {"detail":{"error":"Deep Research is temporarily disabled",...}}
```

---

## Known Limitations

1. **Aletheia Service:** Deep Research requires the Aletheia orchestrator service to be running. In development without Aletheia, requests will fail after retries but won't crash the application.

2. **SAPTIVA_API_KEY Warning:** The warning `The "SAPTIVA_API_KEY" variable is not set` appears if you don't have the Saptiva API key configured. This is expected for local development.

---

## Files Modified

- ✏️ `apps/web/next.config.js`
- ✏️ `apps/web/middleware.ts`
- ✏️ `infra/docker-compose.dev.yml`
- ✏️ `apps/api/src/routers/deep_research.py`
- ➕ `apps/web/src/app/healthz/route.ts` (NEW)
- ➕ `verify-deployment.sh` (NEW)

---

## Next Steps

1. **Frontend UI for Deep Research Disabled:**
   Update `apps/web/src/app/research/page.tsx` to show a user-friendly message when Deep Research is disabled.

2. **Monitoring:**
   Add Prometheus metrics for:
   - Deep Research requests (accepted/rejected)
   - Kill switch state changes
   - Asset 404 errors

3. **E2E Tests:**
   Add Playwright tests to verify:
   - Assets load correctly
   - Deep Research respects kill switch
   - Authentication flow end-to-end

---

## Support

For issues or questions, run the verification script:
```bash
bash verify-deployment.sh
```

Check logs:
```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml logs web api
```
