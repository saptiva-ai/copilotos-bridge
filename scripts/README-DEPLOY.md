# 🚀 Deployment Scripts Guide

Quick reference for deploying Copilotos Bridge to production using Docker Registry.

## 📋 Prerequisites

```bash
# Set GitHub token for registry access
export GITHUB_TOKEN=ghp_your_token_here

# Or configure Docker credentials
docker login ghcr.io -u jazielflo
```

## 🔄 Complete Deployment Workflow

### 1️⃣ Build and Push (Local Machine)

```bash
# Build and push to registry with auto-versioning
./scripts/push-to-registry.sh

# Or specify a custom version
./scripts/push-to-registry.sh --version v1.2.3

# Skip build if images already exist
./scripts/push-to-registry.sh --no-build
```

**What it does:**
- Builds API and Web images from source
- Tags with git commit hash (e.g., `e91d911`)
- Tags with `latest` if on `main` branch
- Pushes to `ghcr.io/jazielflo/copilotos-bridge`

### 2️⃣ Deploy to Production (Server)

```bash
# SSH to production server
ssh jf@34.42.214.246

# Pull latest code
cd /home/jf/copilotos-bridge
git pull origin main

# Deploy from registry
./scripts/deploy-from-registry.sh

# Or deploy specific version
./scripts/deploy-from-registry.sh e91d911
```

**What it does:**
- Pulls images from registry (no build needed!)
- Tags for local docker-compose compatibility
- Stops old containers
- Starts new containers
- Runs health checks

## 🎯 Common Scenarios

### Scenario 1: Regular Production Update
```bash
# === Local Machine ===
git checkout main
git pull
./scripts/push-to-registry.sh

# === Production Server ===
ssh jf@34.42.214.246
cd /home/jf/copilotos-bridge
git pull origin main
./scripts/deploy-from-registry.sh
```

### Scenario 2: Hotfix Deployment
```bash
# === Local Machine ===
git checkout hotfix-branch
./scripts/push-to-registry.sh --version hotfix-abc123

# === Production Server ===
ssh jf@34.42.214.246
cd /home/jf/copilotos-bridge
./scripts/deploy-from-registry.sh hotfix-abc123
```

### Scenario 3: Rollback to Previous Version
```bash
# === Production Server ===
# Check available versions
docker images ghcr.io/jazielflo/copilotos-bridge/api

# Rollback
./scripts/deploy-from-registry.sh abc1234  # previous commit hash
```

### Scenario 4: Manual tar Transfer (No Registry)
```bash
# === Local Machine ===
cd infra && docker compose build --no-cache
docker save copilotos-api:latest -o ~/copilotos-api.tar
docker save copilotos-web:latest -o ~/copilotos-web.tar
scp ~/copilotos-api.tar jf@34.42.214.246:/home/jf/copilotos-bridge/
scp ~/copilotos-web.tar jf@34.42.214.246:/home/jf/copilotos-bridge/

# === Production Server ===
ssh jf@34.42.214.246
cd /home/jf/copilotos-bridge
docker load -i copilotos-api.tar
docker load -i copilotos-web.tar
cd infra && docker compose down && docker compose up -d
rm -f ~/copilotos-bridge/*.tar
```

## 🔍 Verification Commands

```bash
# Check container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Health check
curl http://localhost:8001/api/health | jq '.'

# View logs
docker logs -f copilotos-api
docker logs -f copilotos-web

# Check image versions
docker images | grep copilotos

# Verify git commit
cd /home/jf/copilotos-bridge && git log -1 --oneline
```

## ⚙️ Environment Variables

### push-to-registry.sh
- `REGISTRY_URL` - Docker registry URL (default: ghcr.io/jazielflo/copilotos-bridge)
- `GITHUB_TOKEN` - GitHub PAT for authentication

### deploy-from-registry.sh
- `REGISTRY_URL` - Docker registry URL
- `SKIP_HEALTH` - Skip health check (default: false)

## 📊 Performance Comparison

| Method | Build Time | Transfer Time | Total Time |
|--------|------------|---------------|------------|
| **Registry Pull** | 0s (pre-built) | ~2-3 min | **~3 min** ✅ |
| tar Transfer | ~10-15 min | ~5-7 min | **~15-22 min** |
| Server Build | ~10-15 min | 0s | **~10-15 min** |

## 🛡️ Security Notes

### GitHub Token Permissions
Required scopes:
- `write:packages` - Push to registry
- `read:packages` - Pull from registry
- `delete:packages` - Delete old versions (optional)

### Create Token
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `write:packages`, `read:packages`
4. Save token securely

### Configure on Server
```bash
# Production server
echo "export GITHUB_TOKEN=ghp_your_token" >> ~/.bashrc
source ~/.bashrc
```

## 🆘 Troubleshooting

### Issue: "permission denied" on registry push
```bash
# Solution: Login to registry
echo $GITHUB_TOKEN | docker login ghcr.io -u jazielflo --password-stdin
```

### Issue: "repository does not exist"
```bash
# Solution: Package must be created first via web UI or initial push
# Go to: https://github.com/jazielflo?tab=packages
# Make packages public if needed
```

### Issue: "API unhealthy after deploy"
```bash
# Check logs
docker logs copilotos-api --tail 50

# Common causes:
# 1. SECRET_KEY too short (min 32 chars)
# 2. MongoDB connection issues
# 3. Missing .env variables

# Verify .env
cat infra/.env | grep -E '(SECRET_KEY|JWT_SECRET_KEY|MONGODB_URL)'
```

### Issue: "Web service not responding"
```bash
# Check if build finished
docker logs copilotos-web --tail 50

# Web takes longer to start (~30-60s)
# Wait and retry health check
```

## 📚 Related Documentation

- [DEPLOYMENT.md](../docs/DEPLOYMENT.md) - Complete deployment guide
- [docker-compose.yml](../infra/docker-compose.yml) - Service configuration
- [GitHub Packages](https://github.com/jazielflo/copilotos-bridge/pkgs/container/copilotos-bridge%2Fapi) - View published images

## 🎓 Quick Tips

1. **Always tag with commit hash** - Makes rollback easy
2. **Test locally first** - Use `make dev` before pushing
3. **Check health endpoint** - Before marking deploy as complete
4. **Keep old images** - For quick rollback (`docker images`)
5. **Clean up old images** - `docker image prune -a --force` (periodically)

---

**Need help?** Check logs, verify environment, or rollback to last known good version.
