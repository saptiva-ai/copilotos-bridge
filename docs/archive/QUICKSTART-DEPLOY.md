# ⚡ Quick Start: Production Deployment

The fastest way to deploy Copilotos Bridge to production using Docker Registry.

## 🎯 TL;DR

```bash
# === LOCAL MACHINE ===
make deploy-prod

# === PRODUCTION SERVER ===
ssh jf@34.42.214.246
cd /home/jf/copilotos-bridge
git pull origin main
make deploy-registry
```

## 📖 Step-by-Step

### Prerequisites
```bash
# Configure GitHub token
export GITHUB_TOKEN=ghp_your_token_here
```

### 1. Build and Push (5-10 minutes)
```bash
# From project root on local machine
make push-registry
```

This will:
- Build API and Web images
- Tag with git commit hash
- Push to ghcr.io/jazielflo/copilotos-bridge

### 2. Deploy on Server (2-3 minutes)
```bash
# SSH to production
ssh jf@34.42.214.246

# Navigate and pull code
cd /home/jf/copilotos-bridge
git pull origin main

# Deploy from registry
make deploy-registry
```

This will:
- Pull images from registry
- Stop old containers
- Start new containers
- Run health checks

### 3. Verify
```bash
# Check container status
docker ps

# Test API
curl http://localhost:8001/api/health | jq '.'

# Check version
git log -1 --oneline
```

## 🔥 Alternative: Manual Commands

### Build & Push
```bash
./scripts/push-to-registry.sh
# or without rebuild:
./scripts/push-to-registry.sh --no-build
```

### Deploy
```bash
./scripts/deploy-from-registry.sh
# or specific version:
./scripts/deploy-from-registry.sh abc1234
```

## 🔄 Rollback
```bash
# On production server
./scripts/deploy-from-registry.sh <previous-commit-hash>
```

## 📚 Full Documentation
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Complete deployment guide
- [scripts/README-DEPLOY.md](../scripts/README-DEPLOY.md) - Detailed script documentation

## 🆘 Common Issues

### "permission denied" pushing to registry
```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u jazielflo --password-stdin
```

### "Secret 'SECRET_KEY' too short"
```bash
# On production server
cd infra
# Regenerate secrets with minimum 32 characters
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))"
```

### API unhealthy after deploy
```bash
# Check logs
docker logs copilotos-api --tail 50

# Verify secrets
cat infra/.env | grep -E '(SECRET_KEY|JWT_SECRET)'
```

---

**Pro tip**: Always commit and push code to git before deploying!
