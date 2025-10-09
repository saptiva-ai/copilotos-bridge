# 🔧 Troubleshooting Guide - CopilotOS

Comprehensive guide for diagnosing and fixing common issues in CopilotOS development and deployment.

## Table of Contents

1. [Webpack Module Resolution Issues](#webpack-module-resolution-issues)
2. [Authentication Problems](#authentication-problems)
3. [Database Connection Issues](#database-connection-issues)
4. [API Key and Configuration Issues](#api-key-and-configuration-issues)
5. [Docker and Container Issues](#docker-and-container-issues)
6. [Performance and Resource Issues](#performance-and-resource-issues)
7. [Security Issues](#security-issues)
8. [Quick Reference](#quick-reference)

---

## Webpack Module Resolution Issues

### Issue: "Module not found: Can't resolve 'react-hot-toast'" (or similar)

**Symptoms:**
```
Module not found: Can't resolve 'react-hot-toast'
Module not found: Can't resolve 'next'
Module not found: Can't resolve 'react'
```

Despite the module being installed and visible in `node_modules/`.

**Root Cause Analysis:**

This is caused by **three interconnected issues**:

1. **Webpack Cache Corruption**
   - Webpack caches module resolution paths in `.next/cache/webpack`
   - When Docker containers restart, cache may contain stale symlink references
   - Node.js resolves correctly, but webpack's `enhanced-resolve` with cache fails

2. **Anonymous Volume Mount Timing**
   - `docker-compose.dev.yml` mounts `/app/apps/web/node_modules` as anonymous volume
   - Volume mounts **after** container starts
   - If `node_modules` isn't copied into image first, symlinks arrive late
   - Webpack cache is built before volume fully materializes

3. **pnpm Workspace Symlink Structure**
   - pnpm uses relative symlinks: `../../node_modules/.pnpm/react@18.3.1/...`
   - When cache references old paths and volume remounts, symlinks break
   - Structure exists but cache points to wrong location

**Visual Diagram:**
```
┌─────────────────────────────────────────────────────────────┐
│ Container Start                                              │
│ ├─ Dockerfile: COPY apps/web/node_modules (NEW FIX)         │
│ ├─ Volume Mount: /app/apps/web/node_modules (anonymous)     │
│ ├─ Webpack Starts: Loads cache from .next/cache             │
│ └─ Cache Miss: Tries to resolve react-hot-toast             │
│    ├─ Cache: Points to OLD symlink path                     │
│    ├─ Reality: Symlink remounted to NEW path                │
│    └─ Result: MODULE NOT FOUND ❌                           │
└─────────────────────────────────────────────────────────────┘

After Fix (Dockerfile + verify-deps.sh):
┌─────────────────────────────────────────────────────────────┐
│ Container Start                                              │
│ ├─ Dockerfile: COPY apps/web/node_modules (symlinks ready)  │
│ ├─ verify-deps.sh: Validates symlinks before dev server     │
│ ├─ Volume Mount: /app/apps/web/node_modules (consistent)    │
│ ├─ Webpack Starts: Cache misses, rebuilds with correct paths│
│ └─ Resolution: Symlinks valid, webpack caches correctly ✅   │
└─────────────────────────────────────────────────────────────┘
```

**Immediate Fix (Quick Recovery):**

```bash
# Option 1: Clear cache and restart (fastest)
make webpack-cache-clear

# Option 2: Clean rebuild (most thorough)
make dev-clean

# Option 3: Manual cache clear
docker compose -f docker-compose.dev.yml exec web rm -rf /app/apps/web/.next/cache
docker compose -f docker-compose.dev.yml restart web
```

**Permanent Prevention (Already Implemented):**

✅ **Dockerfile Fix** (apps/web/Dockerfile:62-64)
```dockerfile
# CRITICAL: Copy workspace-specific node_modules for pnpm workspace
# This ensures all symlinks are present before the anonymous volume mounts
COPY --from=deps --chown=app:appgroup /app/apps/web/node_modules ./apps/web/node_modules
```

✅ **Dependency Verification Script** (scripts/verify-deps.sh)
- Validates symlinks before dev server starts
- Checks critical dependencies (react, next, react-hot-toast, etc.)
- Auto-fix mode: `./scripts/verify-deps.sh --fix`

✅ **Makefile Commands**
```bash
make verify-deps       # Check dependency integrity
make verify-deps-fix   # Check and auto-repair
make dev-clean         # Clean rebuild with volume removal
```

**Verification Steps:**

After applying fix, verify it worked:

```bash
# 1. Check symlinks exist
docker compose -f docker-compose.dev.yml exec web ls -la /app/apps/web/node_modules/react-hot-toast
# Should show: lrwxrwxrwx ... react-hot-toast -> ../../node_modules/.pnpm/...

# 2. Run dependency verification
make verify-deps
# Should show all green checkmarks

# 3. Check webpack cache age
docker compose -f docker-compose.dev.yml exec web ls -lah /app/apps/web/.next/cache
# Fresh cache is okay after clearing

# 4. Test the application
curl http://localhost:3000
# Should return HTML (not error)
```

**Why This Solution Works:**

1. **Copying before mount** ensures symlinks exist in the image layer
2. **Anonymous volume inherits** the copied structure, maintaining consistency
3. **verify-deps.sh** catches issues before webpack starts
4. **Cache clearing** removes stale references when needed

**When to Use Each Fix:**

| Situation | Command | Why |
|-----------|---------|-----|
| First occurrence | `make webpack-cache-clear` | Quick fix, keeps dependencies |
| Recurring issue | `make dev-clean` | Full rebuild, ensures clean state |
| After pnpm install | `make verify-deps` | Validate new dependencies |
| Deployment | `make deploy-clean` | Always start from clean state |

**Prevention Checklist:**

- ✅ Use `make dev` (not `docker compose up` directly)
- ✅ Run `make verify-deps` after adding dependencies
- ✅ Clear cache after major dependency updates
- ✅ Use `make dev-clean` if switching branches with package changes
- ✅ Never manually edit `node_modules/` inside container
- ✅ Rebuild containers after Dockerfile changes

---

## Authentication Problems

### Issue: Login fails with mixed-case email (e.g., Test4@saptiva.com)

**Status:** ✅ FIXED in current version

**Symptoms:**
- Register with `Test4@saptiva.com` succeeds
- Login with `Test4@saptiva.com` fails with "Credenciales inválidas"
- Login with `test4@saptiva.com` (lowercase) works

**Root Cause:**
- **Register** (apps/api/src/services/auth_service.py:159): Normalized email to lowercase
- **Login** (apps/api/src/services/auth_service.py:212): Did NOT normalize, case-sensitive lookup
- MongoDB stored `test4@saptiva.com`, but login searched for `Test4@saptiva.com` (case-sensitive)

**Fix Applied:**

Created centralized email normalization:

**apps/api/src/core/email_utils.py**
```python
def normalize_email(email: str) -> str:
    """
    Canonicalize email: strip whitespace, lowercase, remove consecutive dots

    Examples:
        >>> normalize_email("  Test4@Saptiva.COM  ")
        'test4@saptiva.com'
    """
    # Full implementation in file
```

**Updated auth_service.py:**
```python
# Register (line 159)
normalized_email = normalize_email(str(payload.email))

# Login (line 212)
sanitized_identifier = sanitize_email_for_lookup(identifier)
user = await _get_user_by_identifier(sanitized_identifier)
```

**Verification:**

Test suite with 32 tests confirms fix:

```bash
cd apps/api
source .venv/bin/activate
pytest tests/test_email_utils.py -v
# Should show: 32 passed
```

**Live testing:**
```bash
# All these should work now:
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"Test4@saptiva.com","password":"Demo1234"}'

curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"test4@saptiva.com","password":"Demo1234"}'

curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"  TEST4@SAPTIVA.COM  ","password":"Demo1234"}'
```

### Issue: "Invalid token" or "Token expired"

**Symptoms:**
- API returns 401 Unauthorized
- Frontend shows "Session expired"
- Logout/login cycle required

**Diagnosis:**

```bash
# Check JWT configuration
cat envs/.env.local | grep JWT

# Expected:
# JWT_SECRET_KEY=<64-char-hex>
# ACCESS_TOKEN_EXPIRE_MINUTES=60
# REFRESH_TOKEN_EXPIRE_DAYS=7
```

**Common Causes:**

1. **JWT secret changed** (tokens signed with old secret are invalid)
   ```bash
   # Check if secret recently regenerated
   git log --oneline envs/.env.local
   ```

2. **Server time skew**
   ```bash
   # Check container time
   docker compose -f docker-compose.dev.yml exec api date
   # Should match host time
   ```

3. **Token not sent in request**
   ```bash
   # Check browser storage
   # DevTools → Application → Local Storage
   # Should see: accessToken, refreshToken
   ```

**Fixes:**

```bash
# Option 1: Clear tokens and re-login
# Frontend will auto-refresh, or logout/login

# Option 2: Regenerate JWT secret (requires all users to re-login)
make setup-interactive
make rebuild-api

# Option 3: Check token expiration settings
nano envs/.env.local
# Increase ACCESS_TOKEN_EXPIRE_MINUTES if needed
```

---

## Database Connection Issues

### Issue: "Cannot connect to MongoDB"

**Symptoms:**
```
ERROR:     Failed to connect to MongoDB
ERROR:     [Errno 111] Connection refused
```

**Diagnosis:**

```bash
# 1. Check MongoDB is running
docker compose -f docker-compose.dev.yml ps | grep mongodb
# Should show "Up"

# 2. Check MongoDB logs
make logs | grep mongodb
# Look for "Waiting for connections"

# 3. Test connection from API container
docker compose -f docker-compose.dev.yml exec api ping mongodb -c 3
# Should succeed

# 4. Verify credentials
cat envs/.env.local | grep MONGODB
```

**Common Causes & Fixes:**

1. **MongoDB not started**
   ```bash
   docker compose -f docker-compose.dev.yml up -d mongodb
   docker compose -f docker-compose.dev.yml restart api
   ```

2. **Wrong credentials**
   ```bash
   # Regenerate with correct values
   make setup-interactive
   make restart
   ```

3. **Port conflict** (27017 already in use)
   ```bash
   # Check what's using port 27017
   sudo lsof -i :27017
   # Kill conflicting process or change MongoDB port
   ```

4. **Volume corruption**
   ```bash
   # WARNING: This deletes all data
   make dev-clean
   ```

### Issue: "Database authentication failed"

**Symptoms:**
```
pymongo.errors.OperationFailure: Authentication failed
```

**Fix:**

```bash
# 1. Stop all services
make stop

# 2. Remove MongoDB volume (WARNING: Deletes data)
docker volume rm copilotos-bridge_mongodb_data

# 3. Regenerate configuration
make setup-interactive

# 4. Clean start
make dev-clean

# 5. Recreate users
make create-demo-user
```

---

## API Key and Configuration Issues

### Issue: "SAPTIVA API key is invalid"

**Symptoms:**
- Chat requests fail with 401
- API logs show "Invalid API key"
- Models list empty

**Diagnosis:**

```bash
# 1. Check key exists in env file
cat envs/.env.local | grep SAPTIVA_API_KEY
# Should show: SAPTIVA_API_KEY=va-ai-...

# 2. Verify key format
# Valid format: va-ai-[A-Za-z0-9_-]+
# Example: va-ai-Jm4BHuPx...

# 3. Test key directly
curl -H "Authorization: Bearer YOUR_KEY" \
     https://api.saptiva.com/v1/models
# Should return JSON with models list
```

**Fixes:**

```bash
# Option 1: Update key in env file
nano envs/.env.local
# Edit SAPTIVA_API_KEY=va-ai-your-new-key
make restart

# Option 2: Regenerate configuration
make setup-interactive
# Paste new API key when prompted
make rebuild-api

# Option 3: Check key on dashboard
# Visit: https://saptiva.com/dashboard/api-keys
# Verify key is active and not revoked
```

### Issue: Environment variables not loading

**Symptoms:**
- API uses default values
- Configuration changes don't take effect

**Diagnosis:**

```bash
# Check if env file exists
ls -la envs/.env.local
# Should show: -rw------- (600 permissions)

# Verify docker-compose loads it
grep "env_file" docker-compose.dev.yml
# Should show: - ./envs/.env.local

# Check API received the variables
docker compose -f docker-compose.dev.yml exec api env | grep SAPTIVA
```

**Fix:**

```bash
# Recreate containers (restart is not enough)
make rebuild-api

# Or full rebuild
make rebuild-all
```

---

## Docker and Container Issues

### Issue: "Port already in use" (3000 or 8001)

**Symptoms:**
```
Error response from daemon: driver failed programming external connectivity
Bind for 0.0.0.0:3000 failed: port is already allocated
```

**Diagnosis:**

```bash
# Find process using port 3000
sudo lsof -i :3000

# Or for port 8001
sudo lsof -i :8001
```

**Fix:**

```bash
# Option 1: Kill the process
sudo kill -9 <PID>

# Option 2: Stop all compose services
make stop
docker compose -f docker-compose.dev.yml down

# Option 3: Change port in docker-compose.dev.yml
# Edit ports: - "3001:3000" instead of "3000:3000"
```

### Issue: "No space left on device"

**Symptoms:**
```
ERROR: failed to solve: no space left on device
```

**Diagnosis:**

```bash
# Check Docker disk usage
docker system df

# Check available space
df -h
```

**Fix:**

```bash
# Option 1: Safe cleanup (removes old cache)
make docker-cleanup

# Option 2: Aggressive cleanup (removes all unused)
make docker-cleanup-aggressive

# Option 3: Manual cleanup
docker system prune -a --volumes
# WARNING: Removes all unused images, containers, volumes
```

### Issue: Changes to code not reflected in running container

**Symptoms:**
- Modified Python/TypeScript code doesn't run
- Old behavior persists after changes
- Hot reload not working

**Root Cause:**
- For **API (Python)**: Volume mounts should work, but bytecode cache may be stale
- For **Web (Next.js)**: Docker caches image layers, restart keeps old container

**Fix:**

```bash
# For API changes (Python)
make rebuild-api

# For Web changes (Next.js)
make rebuild-web

# For environment variable changes
make rebuild-all

# Why this works:
# - 'docker restart' keeps the same container (old code)
# - 'down + up' recreates container from image (new code)
# - '--build' forces image rebuild (no cache)
```

**Verification:**

```bash
# Add a print statement or log to verify new code runs
# Example in API:
echo 'print("CODE UPDATED v2")' >> apps/api/src/main.py

# Rebuild and check logs
make rebuild-api
make logs-api | grep "CODE UPDATED"
# Should show: CODE UPDATED v2
```

---

## Performance and Resource Issues

### Issue: High CPU usage

**Symptoms:**
- Docker Desktop shows 100% CPU
- System fans running loud
- Development sluggish

**Diagnosis:**

```bash
# Check container resource usage
make resources

# Continuous monitoring
make resources-monitor

# Check which container is the culprit
docker stats
```

**Common Causes:**

1. **Webpack rebuild loops**
   ```bash
   # Check web container logs for infinite rebuilds
   make logs-web
   # Look for: "Compiled successfully" repeated many times
   ```

2. **MongoDB indexing**
   ```bash
   # Check if MongoDB is building indexes
   make logs | grep mongodb | grep "Index build"
   ```

**Fix:**

```bash
# Option 1: Restart specific service
docker compose -f docker-compose.dev.yml restart web

# Option 2: Clear webpack cache
make webpack-cache-clear

# Option 3: Limit Docker resources
# Docker Desktop → Settings → Resources
# Set CPU limit (e.g., 4 CPUs max)
```

### Issue: High memory usage

**Diagnosis:**

```bash
# Check memory usage per container
docker stats --no-stream

# Check system memory
free -h
```

**Fix:**

```bash
# Option 1: Restart services to free memory
make restart

# Option 2: Cleanup unused data
make docker-cleanup

# Option 3: Set memory limits in docker-compose.dev.yml
# Add to service definition:
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

---

## Security Issues

### Issue: ".env files tracked in Git"

**Critical:** This exposes secrets publicly if pushed to GitHub.

**Detection:**

```bash
# Run security check
./scripts/security-check.sh

# Or manually check
git ls-files | grep -E '\.env$|\.env\.'
```

**Fix:**

```bash
# Remove from Git tracking (keeps local file)
git rm --cached envs/.env envs/.env.local envs/.env.prod
git commit -m "security: remove env files from tracking"

# Verify .gitignore
cat .gitignore | grep -E '\.env'
# Should contain:
# .env
# .env.*
# !.env.*.example
```

**If Already Pushed to GitHub:**

1. **Rotate all credentials immediately**
   ```bash
   # Revoke API keys on SAPTIVA dashboard
   # Regenerate all secrets
   make setup-interactive-prod
   make deploy-clean
   ```

2. **Remove from Git history** (advanced)
   ```bash
   # Use BFG Repo Cleaner or git filter-branch
   # See: SECURITY_ALERT.md for detailed steps
   ```

3. **Notify team** about credential rotation

### Issue: Weak or default passwords detected

**Detection:**

```bash
./scripts/security-check.sh
# Will flag: password, 123456, dev-secret, etc.
```

**Fix:**

```bash
# Regenerate with strong passwords
make setup-interactive

# Verify strength
cat envs/.env.local | grep PASSWORD
# Should be 24+ random characters
```

### Issue: Insecure file permissions on .env files

**Detection:**

```bash
ls -la envs/
# Look for: -rw-r--r-- (644) ← INSECURE
# Should be: -rw------- (600) ← SECURE
```

**Fix:**

```bash
# Secure all env files
chmod 600 envs/.env*

# Verify
ls -la envs/ | grep -E '\.env'
# Should show: -rw------- (600)
```

---

## Quick Reference

### Fast Diagnostic Commands

```bash
# Overall health check
make health

# Check all services status
make deploy-status

# View logs for all services
make logs

# View logs for specific service
make logs-api
make logs-web

# Check resource usage
make resources

# Run security audit
./scripts/security-check.sh

# Verify dependencies
make verify-deps
```

### Common Fix Commands

| Issue | Quick Fix | Thorough Fix |
|-------|-----------|--------------|
| Module not found | `make webpack-cache-clear` | `make dev-clean` |
| Code changes not reflected | `make rebuild-api` or `make rebuild-web` | `make rebuild-all` |
| Authentication issues | Check auth_service.py logs | `make rebuild-api` |
| Database connection | `make restart` | `make dev-clean` |
| Env vars not loading | `make restart` | `make rebuild-all` |
| High CPU/memory | `make restart` | `make docker-cleanup` |
| Port conflicts | `make stop` → fix conflict → `make dev` | Change ports in docker-compose |

### Recovery Workflow

If everything is broken:

```bash
# 1. Stop everything
make stop

# 2. Security check (make sure no credentials exposed)
./scripts/security-check.sh

# 3. Clean rebuild
make dev-clean

# 4. Verify dependencies
make verify-deps

# 5. Check health
make health

# 6. Recreate users
make create-demo-user

# 7. Test authentication
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"demo@saptiva.com","password":"Demo1234"}'
```

### When to Use Which Command

**Daily Development:**
```bash
make dev          # Start working
make logs         # Check what's happening
make restart      # Something acting weird
```

**After Code Changes:**
```bash
make rebuild-api  # Changed Python code
make rebuild-web  # Changed Next.js code
make rebuild-all  # Changed env vars or Dockerfile
```

**After Package Changes:**
```bash
make verify-deps       # Check dependencies
make webpack-cache-clear  # Clear stale cache
make dev-clean        # Nuclear option
```

**Before Deployment:**
```bash
./scripts/security-check.sh  # Security audit
make test-all               # Run all tests
make deploy-clean           # Deploy to production
```

---

## Getting Help

### Internal Resources

- **Main README:** `README.md`
- **Deployment Guide:** `docs/DEPLOY_GUIDE.md`
- **Security Alert:** `SECURITY_ALERT.md` (if exists)
- **Resource Optimization:** `docs/RESOURCE_OPTIMIZATION.md`
- **Makefile Help:** `make help`

### Debugging Steps

1. **Identify the service** (API, Web, MongoDB, Redis)
   ```bash
   make logs
   ```

2. **Check service health**
   ```bash
   make health
   ```

3. **Review recent changes**
   ```bash
   git log --oneline -10
   git diff HEAD~1
   ```

4. **Test in isolation**
   ```bash
   # Test API directly
   curl http://localhost:8001/api/health

   # Test frontend directly
   curl http://localhost:3000
   ```

5. **Check configuration**
   ```bash
   cat envs/.env.local
   cat docker-compose.dev.yml
   ```

6. **Verify dependencies**
   ```bash
   make verify-deps
   ```

7. **Clean slate if needed**
   ```bash
   make dev-clean
   ```

### Best Practices to Avoid Issues

✅ **DO:**
- Use `make` commands instead of direct `docker compose`
- Run `make verify-deps` after adding dependencies
- Clear cache after major dependency updates
- Use `make dev-clean` when switching branches
- Run `./scripts/security-check.sh` before commits
- Keep Docker Desktop updated
- Regularly run `make docker-cleanup`

❌ **DON'T:**
- Edit `node_modules/` inside containers
- Use `docker restart` after code changes (use `make rebuild-*`)
- Commit `.env` files to Git
- Ignore security warnings
- Skip testing after fixes
- Force-push without team coordination

---

**Remember:** When in doubt, `make dev-clean` will reset everything to a known-good state. Always run security checks before deployment!
