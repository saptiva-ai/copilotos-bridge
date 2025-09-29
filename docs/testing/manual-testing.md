# Manual Testing Guide

After running the automated verification script, perform these manual tests in your browser.

## Prerequisites

Ensure services are running:
```bash
DC() { docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml "$@"; }
export UID=$(id -u) GID=$(id -g) DEEP_RESEARCH_ENABLED=true
DC up -d
```

---

## Test 1: Homepage and Assets Loading

1. **Open browser:** http://localhost:3000
2. **Expected:** Redirect to `/chat`
3. **Open DevTools** (F12) → Network tab
4. **Refresh page** (Ctrl+R)
5. **Verify:**
   - ✅ No 404 errors for `_next/static/chunks/*`
   - ✅ No 502 Bad Gateway errors
   - ✅ All fonts, CSS, JS files load successfully (200 OK)
   - ✅ Page renders without console errors

**Screenshot locations to check in Network tab:**
- `/_next/static/chunks/webpack-*.js` → 200 OK
- `/_next/static/chunks/main-*.js` → 200 OK
- `/_next/static/chunks/pages/*.js` → 200 OK
- `/_next/static/media/*.woff2` (fonts) → 200 OK

---

## Test 2: Authentication Flow

1. **Navigate to:** http://localhost:3000/register
2. **Fill form:**
   - Email: `manual@test.com`
   - Username: `manualtest`
   - Password: `Manual123!`
   - Full Name: `Manual Test`
3. **Click "Register"**
4. **Expected:** 
   - ✅ Successful registration
   - ✅ Redirect to `/chat`
   - ✅ User is logged in (check localStorage for `auth_token`)

**Verify in DevTools → Application → Local Storage:**
- `auth_token` should be present
- Token should start with `eyJ...` (JWT format)

---

## Test 3: Chat Interface

1. **Ensure you're logged in** (from Test 2)
2. **Navigate to:** http://localhost:3000/chat
3. **Expected:**
   - ✅ Chat interface loads
   - ✅ Sidebar shows conversations (if any)
   - ✅ Input field is present
   - ✅ Send button is clickable

4. **Send a test message:** "Hello, test message"
5. **Expected:**
   - ✅ Message appears in chat
   - ✅ Loading indicator shows
   - ✅ Response streams back (or error if backend not fully configured)

---

## Test 4: Deep Research Feature (Dev Mode)

1. **In chat interface**, type: "What is quantum computing?"
2. **Check if Deep Research is offered** (depends on UI implementation)
3. **If Deep Research button/toggle exists**, try to trigger it
4. **Expected in Dev (`DEEP_RESEARCH_ENABLED=true`):**
   - ✅ Request is accepted
   - ✅ Task ID is returned
   - ✅ May fail if Aletheia is not running (expected)

**Check in DevTools → Network → XHR:**
- POST to `/api/deep-research`
- Response should NOT be 503 in dev mode
- Should return `{"task_id": "...", ...}` or error about Aletheia

---

## Test 5: Deep Research Kill Switch (Prod Mode)

### Restart with Deep Research Disabled

```bash
# Stop services
DC down

# Restart in "production simulation" mode
export DEEP_RESEARCH_ENABLED=false
DC up -d

# Wait for services to be healthy
sleep 30
```

### Test in Browser

1. **Login again** (tokens may have expired)
2. **Try to trigger Deep Research** from chat
3. **Expected:**
   - ✅ Request returns 503 Service Unavailable
   - ✅ Error message: "Deep Research is temporarily disabled"
   - ✅ UI shows appropriate error (if implemented)

**Check in DevTools → Network → XHR:**
- POST to `/api/deep-research`
- Status: `503 Service Unavailable`
- Body: `{"detail": {"error": "Deep Research is temporarily disabled", ...}}`

---

## Test 6: Hot Reload (Development)

1. **Ensure in dev mode:**
   ```bash
   export DEEP_RESEARCH_ENABLED=true
   DC up -d
   ```

2. **Open:** http://localhost:3000/chat
3. **Edit a file:** `apps/web/src/app/chat/page.tsx`
   - Add a comment or change some text
4. **Save the file**
5. **Check browser** (should auto-refresh via HMR)
6. **Expected:**
   - ✅ Page updates automatically
   - ✅ No need to manually refresh
   - ✅ Changes appear within 1-2 seconds

---

## Test 7: Mobile Responsiveness

1. **Open DevTools** (F12)
2. **Toggle device toolbar** (Ctrl+Shift+M)
3. **Select device:** iPhone 12 Pro or similar
4. **Navigate to:** http://localhost:3000/chat
5. **Expected:**
   - ✅ Layout adapts to mobile viewport
   - ✅ No horizontal scrolling
   - ✅ Buttons are touch-friendly
   - ✅ Text is readable

---

## Test 8: Health Check Endpoints

### Browser Tests

1. **Open:** http://localhost:3000/healthz
2. **Expected:** JSON response:
   ```json
   {"status":"ok","timestamp":"...","service":"web"}
   ```

3. **Open:** http://localhost:8001/api/health
4. **Expected:** JSON response:
   ```json
   {"status":"healthy","timestamp":"...","checks":{"database":{...}}}
   ```

---

## Troubleshooting

### Issue: 404 on Assets

**Symptoms:** Console shows `GET /_next/static/chunks/... 404`

**Check:**
```bash
# Verify .next directory exists in container
DC exec web ls -la /app/apps/web/.next/static/chunks

# Check Next.js config
cat apps/web/next.config.js | grep distDir
# Should NOT have custom distDir
```

### Issue: Page Not Loading

**Symptoms:** Blank page, no console errors

**Check:**
```bash
# View web logs
DC logs web --tail=50

# Check if compilation succeeded
# Should see: "✓ Compiled / in X.Xs"
```

### Issue: Authentication Fails

**Symptoms:** Login doesn't work, no token stored

**Check:**
```bash
# View API logs
DC logs api --tail=50

# Test API directly
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"manualtest","password":"Manual123!"}'
```

### Issue: Deep Research Not Working

**Symptoms:** 500 error when trying Deep Research

**Expected:** This is normal if Aletheia is not running

**Check logs:**
```bash
DC logs api | grep -i "deep research"
# Should see: "Aletheia unavailable, using mock mode"
```

---

## Success Criteria

✅ All tests pass without errors  
✅ No 404 or 502 errors in browser console  
✅ Authentication flow works end-to-end  
✅ Deep Research respects kill switch (503 when disabled)  
✅ Hot reload works in development  
✅ Health endpoints return correct status  

---

## Reporting Issues

If you encounter issues:

1. **Run automated verification:**
   ```bash
   bash verify-deployment.sh
   ```

2. **Capture logs:**
   ```bash
   DC logs > logs.txt
   ```

3. **Browser console:**
   - Open DevTools (F12)
   - Go to Console tab
   - Take screenshot of any errors

4. **Network requests:**
   - Open DevTools (F12)
   - Go to Network tab
   - Filter: XHR
   - Take screenshot of failed requests
