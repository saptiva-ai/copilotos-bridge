# Runbook: Web Build Verification

## Purpose

Verify that the web Docker image is correctly built for production deployment, specifically checking that build-time environment variables are properly set.

## When to Use

- **Before every web image push to Docker Hub**
- After any changes to web build configuration
- When debugging CORS or API routing issues

## Quick Verification (30 seconds)

```bash
# Replace <image> with actual image name/tag
IMAGE="saptivaai/octavios-invex-web:1.4.14"

# 1. Check for localhost:8000 in bundle (should find NOTHING)
docker run --rm $IMAGE sh -c \
  "grep -r 'localhost:8000' /app/apps/web/.next/static/chunks/ 2>/dev/null" \
  && echo "❌ FAIL" || echo "✅ PASS: No localhost:8000"

# 2. Verify getApiBaseUrl returns empty string
docker run --rm $IMAGE sh -c \
  "grep -o 'getApiBaseUrl.\\{0,30\\}' /app/apps/web/.next/static/chunks/294*.js 2>/dev/null"
# Expected: getApiBaseUrl(){return""}
```

## Full Verification Script

```bash
#!/bin/bash
# verify-web-build.sh

set -e

IMAGE="${1:-octavios-chat-bajaware_invex-web:latest}"

echo "🔍 Verifying web build: $IMAGE"
echo "================================================"

# Test 1: No localhost:8000 in chunks
echo -n "1. Checking for localhost:8000 in bundle... "
if docker run --rm "$IMAGE" sh -c \
  "grep -rq 'localhost:8000' /app/apps/web/.next/static/chunks/ 2>/dev/null"; then
  echo "❌ FAIL"
  echo "   ERROR: localhost:8000 found in JavaScript bundle!"
  echo "   This will cause CORS errors in production."
  exit 1
fi
echo "✅ PASS"

# Test 2: getApiBaseUrl returns empty string
echo -n "2. Verifying getApiBaseUrl() returns ''... "
API_BASE=$(docker run --rm "$IMAGE" sh -c \
  "grep -o 'getApiBaseUrl(){[^}]*}' /app/apps/web/.next/static/chunks/294*.js 2>/dev/null | head -1")

if [[ "$API_BASE" == *'return""'* ]] || [[ "$API_BASE" == *"return''"* ]]; then
  echo "✅ PASS"
  echo "   Found: $API_BASE"
else
  echo "❌ FAIL"
  echo "   Expected: getApiBaseUrl(){return\"\"}"
  echo "   Found: $API_BASE"
  exit 1
fi

# Test 3: Container starts successfully
echo -n "3. Verifying container starts... "
CONTAINER_ID=$(docker run -d --rm "$IMAGE")
sleep 3
if docker ps -q --filter "id=$CONTAINER_ID" | grep -q .; then
  echo "✅ PASS"
  docker stop "$CONTAINER_ID" > /dev/null 2>&1 || true
else
  echo "❌ FAIL"
  echo "   Container failed to start"
  docker logs "$CONTAINER_ID" 2>&1 | tail -20
  exit 1
fi

# Test 4: Health endpoint responds
echo -n "4. Verifying health endpoint... "
CONTAINER_ID=$(docker run -d --rm -p 3333:3000 "$IMAGE")
sleep 5
HEALTH=$(curl -s http://localhost:3333/healthz 2>/dev/null || echo "")
docker stop "$CONTAINER_ID" > /dev/null 2>&1 || true

if [[ "$HEALTH" == *'"status":"ok"'* ]]; then
  echo "✅ PASS"
else
  echo "❌ FAIL"
  echo "   Health check failed: $HEALTH"
  exit 1
fi

echo "================================================"
echo "✅ All verification checks passed!"
echo "   Image is ready for production deployment."
```

## Common Issues

### Issue: `localhost:8000` Found in Bundle

**Symptom**: CORS errors in production browser console:
```
Access to XMLHttpRequest at 'http://localhost:8000/api/...' from origin
'https://bankadvisor.saptiva.com' has been blocked by CORS policy
```

**Cause**: Image was built with `NEXT_PUBLIC_API_URL=http://localhost:8000`

**Fix**: Rebuild with empty value:
```bash
NEXT_PUBLIC_API_URL="" docker compose -f infra/docker-compose.yml build web \
  --build-arg NEXT_PUBLIC_API_URL=""
```

### Issue: `getApiBaseUrl` Returns Non-Empty Value

**Cause**: Environment variable leaked from host during build

**Fix**:
1. Clear local environment: `unset NEXT_PUBLIC_API_URL`
2. Rebuild with explicit empty: `--build-arg NEXT_PUBLIC_API_URL=""`

### Issue: Can't Find Chunks Directory

**Cause**: Different Next.js output structure

**Fix**: Check actual structure:
```bash
docker run --rm $IMAGE find /app -name "*.js" -path "*chunks*" | head -5
```

## Build Best Practices

### 1. Always Use Explicit Build Args

```bash
# Good - explicit empty value
docker compose build web --build-arg NEXT_PUBLIC_API_URL=""

# Bad - relies on environment
docker compose build web
```

### 2. Clean Environment Before Build

```bash
# Unset any local overrides
unset NEXT_PUBLIC_API_URL
unset NEXT_PUBLIC_SAPTIVA_API_KEY

# Then build
docker compose build web --build-arg NEXT_PUBLIC_API_URL=""
```

### 3. Verify Before Push

```bash
# Build
docker compose build web --build-arg NEXT_PUBLIC_API_URL=""

# Verify
./scripts/verify-web-build.sh octavios-chat-bajaware_invex-web:latest

# Only push if verification passes
docker tag octavios-chat-bajaware_invex-web:latest saptivaai/octavios-invex-web:X.Y.Z
docker push saptivaai/octavios-invex-web:X.Y.Z
```

## Environment Variables Reference

| Variable | Build Time | Runtime | Notes |
|----------|------------|---------|-------|
| `NEXT_PUBLIC_API_URL` | ✅ Used | ❌ Ignored | Must be `""` for production |
| `NEXT_PUBLIC_SAPTIVA_*` | ✅ Used | ❌ Ignored | Inlined at build |
| `API_BASE_URL` | ❌ N/A | ✅ Server only | For SSR API calls |
| `BACKEND_API_URL` | ❌ N/A | ✅ Server only | Internal routing |

## Related

- [Incident Report: 2026-02-05](../lessons/2026-02-05_web_build_env_incident.md)
- [Pre-Deploy Checklist](../checklists/pre-deploy.md)
