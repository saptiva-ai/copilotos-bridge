# 🎯 Deployment Best Practices

**Last Updated:** 2025-10-02  
**Based on:** Production deployment experience and lessons learned

## 📋 Quick Reference

### Choosing the Right Deployment Method

| Situation | Command | Time | Why |
|-----------|---------|------|-----|
| **Daily deployments, small changes** | `make deploy-quick` | 3-5 min | Fast incremental build, perfect for code changes |
| **After dependency changes** | `make deploy-clean` | 12-15 min | Full rebuild ensures all changes are compiled |
| **Version still showing as old** | `make deploy-clean` | 12-15 min | Clears all caches including Next.js internal cache |
| **Redeploy same version** | `make deploy-tar-fast` | 2-3 min | Skips build, uses existing images |
| **Major refactoring** | `make deploy-clean` | 12-15 min | Safest for complex changes |
| **First deployment** | `make deploy-clean` | 12-15 min | Guarantees clean state |

## 🚀 Deployment Workflow

### Standard Deployment Process

```bash
# 1. Make your changes
git add .
git commit -m "feat: your feature description"

# 2. Test locally
make dev
# ... test your changes ...

# 3. Push to remote
git push origin develop

# 4. Merge to main (if ready for production)
git checkout main
git merge develop
git push origin main

# 5. Deploy (choose method based on changes)
make deploy-quick      # For most cases
# OR
make deploy-clean      # For critical updates

# 6. Clear cache if needed
make clear-cache

# 7. Verify deployment
make deploy-status
```

## ⚠️ Common Issues and Solutions

### Issue 1: Old Version Still Showing After Deployment

**Symptoms:**
- Browser shows old UI/behavior even after deployment
- Hard refresh (Ctrl+Shift+R) doesn't help
- Containers are running but code seems stale

**Root Cause:**
Incremental builds can miss Next.js internal compilation cache changes

**Solution:**
```bash
# Use clean build deployment
make deploy-clean

# Then clear server cache
make clear-cache

# Finally, hard refresh browser
# Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
```

**Why This Works:**
- `--no-cache` forces complete Docker rebuild
- All Next.js compilation happens from scratch
- Compiled output includes all recent changes

### Issue 2: Dependency Updates Not Applied

**Symptoms:**
- New npm packages not working
- Python packages giving import errors
- Build seems to use old dependencies

**Root Cause:**
Docker layer caching keeps old `npm install` or `pip install` results

**Solution:**
```bash
# Always use clean build for dependency changes
make deploy-clean
```

**When to Use:**
- ✅ `package.json` changed
- ✅ `pnpm-lock.yaml` changed
- ✅ `requirements.txt` changed
- ✅ Dockerfile changed

### Issue 3: Cache Not Clearing Properly

**Symptoms:**
- Users still seeing old content
- API responses seem cached
- Session data persists unexpectedly

**Solution:**
```bash
# Clear production cache
make clear-cache

# This clears:
# - Redis cache (server-side data)
# - Next.js cache (restart web container)
```

## 🎓 Understanding Cache Layers

### 3-Layer Cache System

```
┌─────────────────────────────────────────────────┐
│  1. Browser Cache (Client-Side)                │
│  - Cached JS/CSS/images                         │
│  - Clear with: Ctrl+Shift+R                     │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  2. Next.js Compilation Cache (Server-Side)     │
│  - Compiled .next output                        │
│  - Clear with: deploy-clean or restart          │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  3. Redis Cache (Server-Side Data)              │
│  - API responses, sessions                      │
│  - Clear with: make clear-cache                 │
└─────────────────────────────────────────────────┘
```

### When to Clear Each Layer

**Browser Cache:**
- After every deployment (user-initiated)
- Use hard refresh: `Ctrl+Shift+R`

**Next.js Cache:**
- When incremental build doesn't show changes
- Use: `make deploy-clean`
- Automatically cleared on container restart

**Redis Cache:**
- After deployment to clear API cache
- Use: `make clear-cache`
- Or manually via `deploy-status` + manual flush

## 🔍 Verification Checklist

### Pre-Deployment

- [ ] All changes committed and pushed
- [ ] On correct branch (usually `main`)
- [ ] Local tests passing
- [ ] No console errors in dev environment

### Post-Deployment

```bash
# 1. Check server status
make deploy-status

# Expected output:
# - Containers: all "healthy"
# - Git commit: matches your local commit
# - API health: "healthy"

# 2. Test critical paths
# - Login/logout
# - Create conversation
# - Send messages
# - Check history menu

# 3. Monitor logs for errors
ssh jf@34.42.214.246 "docker logs -f copilotos-api --tail=50"
```

## 📊 Deployment Time Expectations

### Build Times

| Method | Time | Use Case |
|--------|------|----------|
| `deploy-quick` | 3-5 min | Incremental build with Docker cache |
| `deploy-clean` | 12-15 min | Full rebuild with `--no-cache` |
| `deploy-tar-fast` | 2-3 min | Skip build, use existing images |

### Time Breakdown (Clean Build)

```
Build Phase:
  ├─ API build        ~3-4 min
  ├─ Web build        ~6-8 min
  └─ Total build      ~10-12 min

Deploy Phase:
  ├─ Export to tar    ~1-2 min
  ├─ Transfer         ~1-2 min
  ├─ Load & start     ~1 min
  └─ Total deploy     ~3-5 min

Total: ~12-15 minutes
```

## 🛠️ Advanced Scenarios

### Scenario 1: Emergency Rollback

If deployment causes critical issues:

```bash
# Option 1: Revert Git and redeploy
git revert HEAD
git push origin main
make deploy-clean

# Option 2: Deploy specific commit
git checkout <previous-commit>
make deploy-clean
```

### Scenario 2: Testing Changes Without Full Deploy

```bash
# Build locally without deploying
make deploy-build-only

# Verify images exist
docker images | grep copilotos

# If good, deploy
make deploy-tar-fast
```

### Scenario 3: Parallel Development

When multiple developers are deploying:

```bash
# Always check server state first
make deploy-status

# Coordinate with team
# Deploy during agreed time windows
# Avoid deploying during active development
```

## 🎯 Decision Tree

```
Need to deploy?
  │
  ├─ First deployment ever?
  │  └─ YES → make deploy-clean
  │
  ├─ Dependency changes (package.json, requirements.txt)?
  │  └─ YES → make deploy-clean
  │
  ├─ Major refactoring or Dockerfile changes?
  │  └─ YES → make deploy-clean
  │
  ├─ Previous incremental deploy showed old version?
  │  └─ YES → make deploy-clean + make clear-cache
  │
  ├─ Small code changes (UI, API logic)?
  │  └─ YES → make deploy-quick
  │
  └─ Redeploy same version (e.g., after server restart)?
     └─ YES → make deploy-tar-fast
```

## 📝 Best Practices Summary

### ✅ DO

- **Use `deploy-quick` for daily deployments** - Fast and usually sufficient
- **Use `deploy-clean` when in doubt** - Slower but guaranteed fresh
- **Clear cache after deployment** - Ensures users see new version
- **Verify deployment status** - Check logs and health endpoints
- **Test critical paths** - Don't assume deployment worked
- **Monitor for 5-10 minutes** - Catch issues early
- **Communicate deployments** - Let team know when deploying

### ❌ DON'T

- **Don't use incremental build for dependency changes** - Will miss updates
- **Don't skip cache clearing** - Users may see stale content
- **Don't deploy during peak hours** - Minimize user impact
- **Don't deploy untested code** - Test locally first
- **Don't assume deployment worked** - Always verify
- **Don't forget to merge to main** - Keep branches in sync

## 🔗 Related Documentation

- **Quick Deploy Guide:** [QUICK-DEPLOY.md](QUICK-DEPLOY.md)
- **Deployment Details:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **Optimization Update:** [DEPLOYMENT-OPTIMIZATION-UPDATE.md](DEPLOYMENT-OPTIMIZATION-UPDATE.md)
- **TAR Method:** [DEPLOYMENT-TAR-GUIDE.md](DEPLOYMENT-TAR-GUIDE.md)

## 📞 Troubleshooting

If you encounter issues:

1. **Check deployment status:** `make deploy-status`
2. **View logs:** `ssh jf@34.42.214.246 "docker logs copilotos-api --tail=100"`
3. **Try clean deployment:** `make deploy-clean`
4. **Clear all caches:** `make clear-cache` + browser hard refresh
5. **Verify containers:** `ssh jf@34.42.214.246 "docker ps"`

---

**Author:** Development Team  
**Last Updated:** 2025-10-02  
**Version:** 1.0
