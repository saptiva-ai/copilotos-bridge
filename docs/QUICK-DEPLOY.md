# ⚡ Quick Deployment Guide

> **TL;DR**: Deploy in 3-5 minutes with `make deploy-quick`

## 🚀 Fastest Deployment Options

### Option 1: Ultra-Fast (Incremental Build)
```bash
make deploy-quick
```
**Time:** ~3-5 minutes
**Best for:** Small code changes, bug fixes, minor updates

### Option 2: Fast (Skip Build)
```bash
make deploy-tar-fast
```
**Time:** ~2-3 minutes
**Best for:** When images are already built and you just need to redeploy

### Option 3: Full Clean Build
```bash
make deploy-tar
```
**Time:** ~8-12 minutes
**Best for:** Major changes, dependency updates, first deployment

## 📊 Comparison Table

| Method | Time | Build Type | Use Case |
|--------|------|------------|----------|
| `deploy-quick` | 3-5 min | Incremental (with cache) | Daily deployments, small changes |
| `deploy-tar-fast` | 2-3 min | Skip build | Redeploy existing images |
| `deploy-tar` | 8-12 min | Clean build (no cache) | Major updates, first deploy |
| `deploy-build-only` | 3-6 min | Incremental | Build without deploying |
| `deploy-server-only` | 1-2 min | N/A | Deploy only (tar files on server) |

## 🎯 Quick Commands Cheatsheet

### Deploy Commands
```bash
# Quick deploy (recommended for most cases)
make deploy-quick

# Check status before/after deploy
make deploy-status

# Build only (test build without deploying)
make deploy-build-only

# Deploy only (assumes tar files exist on server)
make deploy-server-only
```

### Verification Commands
```bash
# Check production status
make deploy-status

# Clear cache on server (if seeing old version)
make clear-cache

# Check logs
ssh jf@34.42.214.246 "docker logs -f copilotos-api"
```

## 🔥 One-Liner Deployments

### Quick Deploy + Status Check
```bash
make deploy-quick && make deploy-status
```

### Build + Deploy + Clear Cache
```bash
make deploy-quick && ssh jf@34.42.214.246 "cd /home/jf/copilotos-bridge && ./scripts/clear-server-cache.sh"
```

### Deploy and Monitor
```bash
make deploy-quick && ssh jf@34.42.214.246 "docker logs -f copilotos-api"
```

## ⚙️ Advanced Options

### Parallel Export (Experimental)
```bash
./scripts/deploy-with-tar.sh --incremental --parallel
```
**Time:** ~2-4 minutes
**Warning:** Uses more CPU/memory during export

### Split Workflow
```bash
# 1. Build locally
make deploy-build-only

# 2. Later, deploy to server
make deploy-server-only
```

## 🐛 Troubleshooting

### Seeing old version after deploy?
```bash
# Clear server cache
make clear-cache

# Or manually
ssh jf@34.42.214.246 "cd /home/jf/copilotos-bridge && ./scripts/clear-server-cache.sh"
```

### Build takes too long?
```bash
# Use incremental mode
make deploy-quick
```

### Need to verify deployment?
```bash
# Check all services
make deploy-status

# Check specific service logs
ssh jf@34.42.214.246 "docker logs --tail=50 copilotos-api"
ssh jf@34.42.214.246 "docker logs --tail=50 copilotos-web"
```

### Container not healthy?
```bash
# Check status
ssh jf@34.42.214.246 "docker ps"

# Restart specific service
ssh jf@34.42.214.246 "cd /home/jf/copilotos-bridge/infra && docker compose restart api"

# Full restart
ssh jf@34.42.214.246 "cd /home/jf/copilotos-bridge/infra && docker compose down && docker compose up -d"
```

## 📝 Deployment Workflow Examples

### Daily Development Cycle
```bash
# 1. Make changes locally
git add .
git commit -m "feat: add new feature"
git push origin develop

# 2. Merge to main (if ready)
git checkout main
git merge develop
git push origin main

# 3. Quick deploy
make deploy-quick

# 4. Verify
make deploy-status
```

### Hotfix Deployment
```bash
# 1. Create hotfix
git checkout -b hotfix/critical-bug main
# ... make changes ...
git commit -m "fix: critical bug"

# 2. Merge to main
git checkout main
git merge hotfix/critical-bug
git push origin main

# 3. Fast deploy
make deploy-quick

# 4. Monitor
ssh jf@34.42.214.246 "docker logs -f copilotos-api"
```

### Production Release
```bash
# 1. Create release branch
git checkout -b release/v1.3.0 develop

# 2. Update version, test, etc.
# ...

# 3. Merge to main
git checkout main
git merge release/v1.3.0
git tag v1.3.0
git push origin main --tags

# 4. Full clean deploy
make deploy-tar

# 5. Verify extensively
make deploy-status
```

## 🎓 Best Practices

### When to use each method:

**`make deploy-quick` (Incremental)**
- ✅ Daily deployments
- ✅ Small code changes
- ✅ Bug fixes
- ✅ UI updates
- ❌ Dependency changes (use full build)
- ❌ Major refactoring (use full build)

**`make deploy-tar-fast` (Skip Build)**
- ✅ Redeploying same version
- ✅ Testing deployment process
- ✅ Rollback to previous build
- ❌ After code changes (need to build first)

**`make deploy-tar` (Full Build)**
- ✅ First deployment
- ✅ Dependency updates
- ✅ Major version changes
- ✅ After long time without deploying
- ✅ When incremental build might miss changes

### Performance Tips:

1. **Use incremental builds** for daily work
2. **Keep Docker layer cache** warm (don't prune too often)
3. **Parallel export** if you have CPU to spare
4. **Split build and deploy** if deploying multiple times
5. **Monitor build times** to detect when full build needed

## 📊 Time Breakdown

### Incremental Build (`deploy-quick`)
```
Build (with cache):  1-2 min
Export to tar:       1-2 min
Transfer (SCP):      1-2 min
Load + Deploy:       1 min
────────────────────────────
Total:               3-5 min
```

### Full Build (`deploy-tar`)
```
Build (no cache):    6-8 min
Export to tar:       1-2 min
Transfer (SCP):      1-2 min
Load + Deploy:       1 min
────────────────────────────
Total:               8-12 min
```

### Skip Build (`deploy-tar-fast`)
```
Export to tar:       1-2 min
Transfer (SCP):      1-2 min
Load + Deploy:       1 min
────────────────────────────
Total:               2-3 min
```

## 🔗 Related Documentation

- **Full Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **TAR Method Details**: [DEPLOYMENT-TAR-GUIDE.md](DEPLOYMENT-TAR-GUIDE.md)
- **Registry Method**: [scripts/README-DEPLOY.md](../scripts/README-DEPLOY.md)
- **Makefile Reference**: [Makefile](../Makefile) - Run `make help`

---

**Last Updated:** 2025-10-02
**Maintained by:** Development Team
