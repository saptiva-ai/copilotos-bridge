# Incident: Web Build Environment Variables (2026-02-05)

## Summary

**Severity**: High (Production Login Broken)
**Duration**: ~30 minutes
**Services Affected**: Web (frontend)
**Root Cause**: `NEXT_PUBLIC_API_URL` hardcoded as `http://localhost:8000` at build time

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 16:48 | Deployed web v1.4.13 with BUG-015 fix (canvas panel) |
| 16:50 | User reports CORS error on login |
| 16:55 | Investigation reveals `localhost:8000` in JavaScript bundle |
| 17:05 | Root cause identified: build-time env variable issue |
| 17:10 | Rebuilt image with `NEXT_PUBLIC_API_URL=""` |
| 17:12 | Deployed web v1.4.14, login working |

## Root Cause Analysis

### The Problem

Next.js `NEXT_PUBLIC_*` variables are **inlined at build time**, not runtime. When the Docker image was built, the local environment had:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

This value got embedded directly into the JavaScript bundle:

```javascript
// Minified output in production
getApiBaseUrl(){let e="http://localhost:8000";return e&&""!==e.trim()?e:""}
```

When deployed to production, the browser tried to call `http://localhost:8000` from `https://bankadvisor.saptiva.com`, causing CORS errors.

### Why It Happened

1. Local development uses `NEXT_PUBLIC_API_URL=http://localhost:8000` for direct API calls
2. The build command didn't explicitly override this value
3. Docker build inherited the host environment variable
4. The resulting image had localhost hardcoded in the bundle

### Correct Behavior

For production builds, `NEXT_PUBLIC_API_URL` should be **empty** (`""`), which tells the frontend to use relative URLs (`/api/*`). Next.js then proxies these requests to the backend via `next.config.js` rewrites.

## Technical Details

### How Next.js Environment Variables Work

```
┌─────────────────────────────────────────────────────────────┐
│                    BUILD TIME                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  NEXT_PUBLIC_API_URL="http://localhost:8000"        │    │
│  │           ↓ (inlined by webpack)                    │    │
│  │  const apiUrl = "http://localhost:8000"  // FROZEN! │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    RUNTIME                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Setting NEXT_PUBLIC_API_URL at runtime has         │    │
│  │  NO EFFECT on client-side code!                     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Correct Build Command

```bash
# ALWAYS use explicit empty value for production builds
NEXT_PUBLIC_API_URL="" docker compose -f infra/docker-compose.yml \
  --env-file envs/.env build web \
  --build-arg NEXT_PUBLIC_API_URL=""
```

### Verification Command

After building, verify the bundle doesn't contain localhost:

```bash
# Check for hardcoded localhost in the bundle
docker run --rm <image>:latest sh -c \
  "grep -r 'localhost:8000' /app/apps/web/.next/static/chunks/ 2>/dev/null" \
  && echo "❌ FAIL: localhost:8000 found in bundle" \
  || echo "✅ PASS: No localhost:8000 in bundle"

# Verify getApiBaseUrl returns empty string
docker run --rm <image>:latest sh -c \
  "grep -o 'getApiBaseUrl.\\{0,50\\}' /app/apps/web/.next/static/chunks/294*.js"
# Should show: getApiBaseUrl(){return""}
```

## Prevention Measures

### 1. Build Script Update

Add verification step to build scripts:

```bash
#!/bin/bash
# build-web.sh

# Ensure clean build environment
unset NEXT_PUBLIC_API_URL
export NEXT_PUBLIC_API_URL=""

# Build
docker compose -f infra/docker-compose.yml build web \
  --build-arg NEXT_PUBLIC_API_URL=""

# Verify
if docker run --rm octavios-chat-bajaware_invex-web:latest sh -c \
  "grep -q 'localhost:8000' /app/apps/web/.next/static/chunks/*.js 2>/dev/null"; then
  echo "❌ BUILD FAILED: localhost:8000 detected in bundle"
  exit 1
fi

echo "✅ Build verified: No localhost in bundle"
```

### 2. Pre-Deploy Checklist Addition

Add to `checklists/pre-deploy.md`:

```markdown
## Web Build Verification (CRITICAL)

- [ ] Built with `NEXT_PUBLIC_API_URL=""`
- [ ] Verified no `localhost:8000` in JavaScript bundle
- [ ] `getApiBaseUrl()` returns empty string in minified code
```

### 3. CI/CD Guard

Add to GitHub Actions or CI pipeline:

```yaml
- name: Verify Web Build
  run: |
    if docker run --rm ${{ env.WEB_IMAGE }} sh -c \
      "grep -q 'localhost:8000' /app/apps/web/.next/static/chunks/*.js 2>/dev/null"; then
      echo "::error::localhost:8000 found in web bundle - build is invalid for production"
      exit 1
    fi
```

## Lessons Learned

1. **Next.js NEXT_PUBLIC_* variables are build-time only** - They cannot be changed at runtime
2. **Always verify bundles before pushing** - A 5-second grep can prevent 30 minutes of downtime
3. **Document build requirements** - Environment expectations should be explicit in build scripts
4. **Add CI guards for common mistakes** - Automated checks catch human errors

## Action Items

| Item | Owner | Status |
|------|-------|--------|
| Update pre-deploy checklist | Claude | ✅ Done |
| Add verification to build script | TBD | Pending |
| Add CI/CD guard | TBD | Pending |
| Document in runbooks | Claude | ✅ Done |

## Related Documents

- [Pre-Deploy Checklist](../checklists/pre-deploy.md)
- [Web Build Verification Runbook](../runbooks/web_build_verification.md)
- [Deploy Procedure v1.4.5](../procedures/current_v1.4.5.md)
