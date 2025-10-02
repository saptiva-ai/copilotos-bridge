# 📦 Tar Deployment Guide

## Quick Start

### Automated Deployment (Recommended)

```bash
# One-command deployment from main branch
make deploy-tar
```

That's it! The script will:
1. ✅ Build images with `--no-cache`
2. ✅ Tag images correctly for docker-compose
3. ✅ Export to compressed tar files
4. ✅ Transfer to production server
5. ✅ Load images and restart containers
6. ✅ Verify deployment

**Total time:** ~12 minutes

## Deployment Methods Comparison

| Method | Time | Complexity | Use Case |
|--------|------|------------|----------|
| **`make deploy-tar`** | 12 min | Low | No registry access, full automation |
| **`make deploy-registry`** | 3 min | Medium | With GitHub Packages configured |
| **Manual tar transfer** | 15-20 min | High | Troubleshooting only |

## Advanced Usage

### Skip Build (Use Existing Images)

```bash
# If you already built images locally
make deploy-tar-fast
```

### Custom Server Configuration

```bash
# Override default server settings
DEPLOY_SERVER=user@your-server.com \
DEPLOY_PATH=/custom/path \
./scripts/deploy-with-tar.sh
```

### Flags

```bash
# Skip building (use existing images)
./scripts/deploy-with-tar.sh --skip-build

# Skip transfer (images already on server)
./scripts/deploy-with-tar.sh --skip-transfer
```

## Troubleshooting

### Issue: "Build takes too long"

**Solution:** Use `make deploy-tar-fast` if images are already built

### Issue: "Transfer failed"

**Cause:** SSH connection or permissions issue

**Solution:**
```bash
# Test SSH connection
ssh jf@34.42.214.246 "echo 'Connection OK'"

# Check available space on server
ssh jf@34.42.214.246 "df -h /home/jf"
```

### Issue: "Old version still showing"

**Causes:**
1. Redis cache (Next.js caching)
2. Cloudflare cache
3. Browser cache

**Solutions (in order):**

1. **Clear server cache:**
   ```bash
   make clear-cache
   ```
   This will:
   - Flush all Redis cache
   - Restart web container
   - Clear Next.js build cache

2. **Hard refresh browser:**
   - `Ctrl + Shift + R` (Windows/Linux)
   - `Cmd + Shift + R` (Mac)
   - Or use incognito mode

3. **Purge Cloudflare cache:**
   - Go to Cloudflare dashboard
   - Select "Purge Cache" → "Purge Everything"

### Issue: "Container using wrong image"

**Cause:** Docker Compose image naming mismatch

**Solution:** The script automatically handles this by tagging images correctly:
- `infra-api:latest` → `copilotos-api:latest`
- `infra-web:latest` → `copilotos-web:latest`

## Important Notes

### Docker Compose Image Naming

⚠️ **Known Issue:** Docker Compose builds images with the directory prefix (`infra-*`) but the docker-compose.yml references them by service name (`copilotos-*`).

**Our Solution:** The deployment script automatically creates both tags:

```bash
# After building
docker tag infra-api:latest copilotos-api:latest
docker tag infra-web:latest copilotos-web:latest
```

### Verification Steps

After deployment, the script automatically verifies:

1. **API Health:** Checks `/api/health` endpoint
2. **New Code:** Verifies `SessionExpiredModal.tsx` exists (commit 6203422+)
3. **Container Status:** All services are healthy

### Manual Verification

```bash
# SSH to server
ssh jf@34.42.214.246

# Check running containers
docker ps

# Verify new code
docker exec copilotos-web ls /app/apps/web/src/components/auth/SessionExpiredModal.tsx

# Check API health
curl http://localhost:8001/api/health | jq .

# View logs
docker logs -f copilotos-api
```

## Performance Optimization

### Build Cache

Docker build with `--no-cache` ensures latest code but takes longer:

```bash
# With cache (faster but may be outdated): 3-5 min
docker compose build api web

# Without cache (slower but guaranteed fresh): 10-15 min
docker compose build --no-cache api web
```

**Our choice:** Always use `--no-cache` in deployment to guarantee correctness.

### Compression Ratios

| Image | Original | Compressed | Ratio |
|-------|----------|------------|-------|
| API | 380MB | 85MB | 78% |
| Web | 1.33GB | 278MB | 79% |

### Network Transfer

Transfer time depends on your connection:

| Connection | Transfer Time (363MB) |
|------------|----------------------|
| 10 Mbps | ~5 minutes |
| 50 Mbps | ~1 minute |
| 100 Mbps | ~30 seconds |

## Deployment Checklist

Before deploying:

- [ ] All changes committed and pushed to `main`
- [ ] Local tests passing: `make test`
- [ ] Code linted: `make lint`
- [ ] Current branch is `main`: `git branch --show-current`

After deploying:

- [ ] API health check passes
- [ ] Frontend loads correctly
- [ ] New features visible in UI
- [ ] No errors in logs: `docker logs copilotos-api`
- [ ] Cloudflare cache purged (if needed)

## Rollback Procedure

If deployment fails:

```bash
# On server
ssh jf@34.42.214.246
cd /home/jf/copilotos-bridge

# Check git history
git log --oneline -10

# Rollback code
git checkout <previous-commit-hash>

# Rebuild and restart (or re-deploy old version)
cd infra
docker compose down
docker compose up -d --build
```

## Next Steps: Docker Registry

For faster deployments (3 min vs 12 min), consider setting up Docker Registry:

1. **Configure GitHub Packages** (see `scripts/README-DEPLOY.md`)
2. **Use `make deploy-prod`** instead
3. **Benefits:**
   - Build once, deploy many times
   - Faster transfers (already compressed)
   - Version tagging built-in
   - No local tar files needed

---

**Generated:** 2025-10-02
**Last Updated:** After implementing automated tar deployment
