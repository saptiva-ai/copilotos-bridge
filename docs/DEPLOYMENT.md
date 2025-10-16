# 🚀 Secure Production Deployment Guide

> **⚡ TL;DR**: For fastest deployment, see [QUICK-DEPLOY.md](QUICK-DEPLOY.md) (3-5 minutes)

## 🔒 Security Notice
⚠️ **SECURITY UPDATE**: This system has been hardened with comprehensive secrets management. All hardcoded credentials have been **REMOVED** and replaced with secure configuration.

## 📋 Overview
This system operates in **production mode only** with mandatory security requirements:
- **Zero hardcoded credentials** ✅
- **Secure secrets management** ✅
- **Encrypted credential storage** ✅
- **Fail-fast security validation** ✅

## 🎯 Quick Deployment Options

| Command | Time | Best For |
|---------|------|----------|
| `make deploy-quick` | 3-5 min | Daily deployments (incremental build) |
| `make deploy-tar-fast` | 2-3 min | Redeploy existing images |
| `make deploy-tar` | 8-12 min | Major updates (clean build) |



## 🐳 Docker Registry Deployment (Recommended)

### Why Use Docker Registry?
- **Efficiency**: No need to build on production servers
- **Consistency**: Same images across all environments
- **Speed**: Pull images instead of building (~2-3 min vs ~10-15 min)
- **Rollback**: Easy version management with tags

### 🎯 Quick Start (Using Scripts)

We provide automated scripts for easy deployment:

```bash
# === LOCAL MACHINE ===
# Build and push to registry
./scripts/push-to-registry.sh

# === PRODUCTION SERVER ===
ssh your_user@34.42.214.246
cd /home/your_user/copilotos-bridge
./scripts/deploy-from-registry.sh
```

📚 **See [scripts/README-DEPLOY.md](../scripts/README-DEPLOY.md) for complete guide**

### Quick Deploy Commands

#### 1. Build and Push to Registry (Local Machine)
```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build images locally
cd infra
docker compose -f docker-compose.yml build --no-cache

# Tag images for registry
docker tag copilotos-api:latest ghcr.io/jazielflo/copilotos-bridge/api:latest
docker tag copilotos-web:latest ghcr.io/jazielflo/copilotos-bridge/web:latest

# Optional: Tag with version/commit
export VERSION=$(git rev-parse --short HEAD)
docker tag copilotos-api:latest ghcr.io/jazielflo/copilotos-bridge/api:$VERSION
docker tag copilotos-web:latest ghcr.io/jazielflo/copilotos-bridge/web:$VERSION

# Push to registry
docker push ghcr.io/jazielflo/copilotos-bridge/api:latest
docker push ghcr.io/jazielflo/copilotos-bridge/web:latest
docker push ghcr.io/jazielflo/copilotos-bridge/api:$VERSION
docker push ghcr.io/jazielflo/copilotos-bridge/web:$VERSION
```

#### 2. Deploy on Production Server
```bash
# SSH to production
ssh your_user@34.42.214.246

# Navigate to project
cd /home/your_user/copilotos-bridge

# Pull latest code
git pull origin main

# Login to registry (if private)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull latest images
docker pull ghcr.io/jazielflo/copilotos-bridge/api:latest
docker pull ghcr.io/jazielflo/copilotos-bridge/web:latest

# Tag locally (docker-compose expects copilotos-api/web names)
docker tag ghcr.io/jazielflo/copilotos-bridge/api:latest copilotos-api:latest
docker tag ghcr.io/jazielflo/copilotos-bridge/web:latest copilotos-web:latest

# Restart services
cd infra
docker compose -f docker-compose.yml down
docker compose -f docker-compose.yml up -d

# Verify deployment
docker ps
curl -sS http://localhost:8001/api/health | jq '.'
```

### One-Liner Deploy Script
```bash
#!/bin/bash
# Quick production deploy from registry
set -e

echo "🚀 Deploying from Docker Registry..."

# Pull latest images
docker pull ghcr.io/your_user/copilotos-bridge/api:latest
docker pull ghcr.io/your_user/copilotos-bridge/web:latest

# Tag for local use
docker tag ghcr.io/your_user/copilotos-bridge/api:latest copilotos-api:latest
docker tag ghcr.io/your_user/copilotos-bridge/web:latest copilotos-web:latest

# Restart services
cd infra
docker compose down
docker compose up -d

# Health check
sleep 10
curl -sS http://localhost:8001/api/health || echo "⚠️  API not ready yet"

echo "✅ Deploy complete!"
```

### Rollback to Previous Version
```bash
# List available versions
docker images ghcr.io/your_user/copilotos-bridge/api

# Pull specific version
export VERSION=abc1234
docker pull ghcr.io/your_user/copilotos-bridge/api:$VERSION
docker pull ghcr.io/your_user/copilotos-bridge/web:$VERSION

# Tag and deploy
docker tag ghcr.io/your_user/copilotos-bridge/api:$VERSION copilotos-api:latest
docker tag ghcr.io/your_user/copilotos-bridge/web:$VERSION copilotos-web:latest

cd infra && docker compose down && docker compose up -d
```

### Alternative: tar File Transfer (No Registry Access)
```bash
# === LOCAL MACHINE ===
# Build images
cd infra && docker compose -f docker-compose.yml build --no-cache

# Export to tar
docker save copilotos-api:latest -o copilotos-api.tar
docker save copilotos-web:latest -o copilotos-web.tar

# Transfer to server
scp copilotos-api.tar jf@34.42.214.246:/home/your_user/copilotos-bridge/
scp copilotos-web.tar jf@34.42.214.246:/home/your_user/copilotos-bridge/

# === PRODUCTION SERVER ===
ssh your_user@34.42.214.246
cd /home/your_user/copilotos-bridge

# Import images
docker load -i copilotos-api.tar
docker load -i copilotos-web.tar

# Restart services
cd infra && docker compose down && docker compose up -d

# Cleanup
rm -f copilotos-api.tar copilotos-web.tar
```

## 🔑 SAPTIVA API Key Configuration

### 🔐 Secure Configuration Methods

**⚠️ SECURITY WARNING: Never use hardcoded credentials!**

#### Method 1: Docker Secrets (Production Recommended)
```bash
# 1. Generate secure secrets
python3 scripts/generate-secrets.py

# 2. Setup Docker secrets
./scripts/setup-docker-secrets.sh

# 3. Deploy securely
docker stack deploy -c docker-compose.secure.yml copilotos
```

#### Method 2: Environment Variables (Development Only)
```bash
# Generate secure values first!
export SAPTIVA_API_KEY=your-saptiva-api-key-here
export MONGODB_PASSWORD=$(openssl rand -base64 32)
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export SECRET_KEY=$(openssl rand -hex 32)
```

### Security Priority Order
1. **Docker Secrets** (/run/secrets/) - HIGHEST SECURITY
2. **Environment Variables** - MEDIUM SECURITY
3. **Secure Files** (/etc/copilotos/secrets/) - HIGH SECURITY
4. **Admin UI** - For API key management only

## ⚙️ Deployment Steps

### 1. Environment Variables
Ensure `SAPTIVA_API_KEY` is set in your deployment environment:
```bash
# For Docker
export SAPTIVA_API_KEY=your-key
docker-compose up

# For Kubernetes
kubectl create secret generic saptiva-secret \
  --from-literal=SAPTIVA_API_KEY=your-key

# For other platforms
# Add SAPTIVA_API_KEY to your environment variables
```

### 2. Verify Configuration
After deployment, check the API key status:
```bash
# Health check
curl http://your-domain/api/health

# Key status (requires authentication)
curl -H "Authorization: Bearer YOUR_JWT" \
     http://your-domain/api/settings/saptiva-key
```

Expected response:
```json
{
  "configured": true,
  "mode": "live",
  "source": "environment" | "database",
  "hint": "••••hc_A",
  "status_message": "API key configured"
}
```

## 🔄 Automatic Loading
- API key is loaded automatically on startup
- Database configuration overrides environment variables
- System validates connectivity with SAPTIVA servers
- No manual intervention required after deployment

## ❌ Breaking Changes
- **Removed**: All mock/demo response functionality
- **Removed**: Fallback responses when API fails
- **Changed**: System fails fast if API key is missing
- **Changed**: All responses now come directly from SAPTIVA

## 🛡️ Security Notes
- API keys are encrypted when stored in database
- Environment variables should use secure secret management
- Key hints are shown as `••••last4` for privacy
- Keys are never logged in plaintext

## ⚠️ Common Deployment Pitfalls

### 1. MongoDB Authentication Failures

**Problem**: Silent authentication failures that cause API to crash loop with generic "Authentication failed" errors.

**Root Cause**: Password mismatch between:
- MongoDB initialization (`MONGO_INITDB_ROOT_PASSWORD` in docker-compose)
- API connection string (`MONGODB_PASSWORD` environment variable)

**Prevention**:
```bash
# ✅ ALWAYS ensure infra/.env is the single source of truth
# Verify passwords match before deployment:
cd infra
docker compose config | grep -E "(MONGODB_PASSWORD|MONGO_INITDB)"

# If passwords differ, fix infra/.env and recreate volumes:
docker compose down -v
docker compose up -d
```

**Detection**: The API now includes improved error logging (v1.2.1+) that shows:
- Username being used
- Host and database
- AuthSource configuration
- Specific troubleshooting hints
- Password mismatch detection

**Example error log** (improved in v1.2.1+):
```json
{
  "event": "❌ MongoDB Connection Failed - AUTHENTICATION ERROR",
  "error_type": "OperationFailure",
  "error_code": 18,
  "connection_details": {
    "username": "copilotos_user",
    "host": "mongodb:27017",
    "database": "copilotos",
    "auth_source": "admin"
  },
  "troubleshooting_hints": [
    "Check that MONGODB_PASSWORD in infra/.env matches docker-compose initialization",
    "Verify MongoDB container initialized with same password",
    "If password changed, recreate volumes: docker compose down -v"
  ]
}
```

### 2. Docker Image Verification

**Problem**: Deployed images don't contain latest code changes.

**Root Cause**: Using cached images or forgetting to rebuild after code changes.

**Prevention**:
```bash
# ✅ ALWAYS verify image contents before deployment
docker run --rm copilotos-api:latest cat /app/src/models/chat.py | head -20
docker run --rm copilotos-web:latest cat /app/apps/web/src/components/chat/ModelSelector.tsx | grep -A 5 "currentModel"

# If outdated, rebuild without cache:
cd infra
docker compose build --no-cache api web
```

### 3. Environment Variable Synchronization

**Problem**: Different password values in multiple files cause confusion.

**Solution**: Use `infra/.env` as single source of truth:

```bash
# ✅ Correct structure:
# infra/.env (source of truth)
MONGODB_PASSWORD=SecureMongoProd2024!Change
REDIS_PASSWORD=SecureRedisProd2024!Change

# docker-compose.yml references it:
environment:
  MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_PASSWORD:-secure_password_change_me}

# API uses same password via connection string:
MONGODB_URL: mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@mongodb:27017/${MONGODB_DATABASE}?authSource=admin
```

### 4. Volume Persistence Issues

**Problem**: Database retains old initialization with different password.

**Solution**: Always recreate volumes when changing passwords:
```bash
# ❌ WRONG: Restart without recreating volumes
docker compose restart

# ✅ CORRECT: Recreate volumes to apply new password
docker compose down -v
docker compose up -d
```

⚠️ **WARNING**: `-v` flag deletes all data. Only use in development or after backup.

## 🧪 Pre-Deployment Checklist

Before deploying to production:

1. **Environment Variables**
   ```bash
   # Verify all required variables are set
   docker compose config | grep -E "(MONGODB|REDIS|SAPTIVA|SECRET)"
   ```

2. **Image Verification**
   ```bash
   # Check git commit in images
   docker run --rm copilotos-api:latest cat /app/.git/refs/heads/main
   # Should match: git rev-parse HEAD
   ```

3. **Local Testing**
   ```bash
   # Test full stack locally before deploying
   cd infra
   docker compose up -d
   curl -sS http://localhost:8001/api/health | jq '.'
   # Open http://localhost:3000 and test chat
   ```

4. **Password Synchronization**
   ```bash
   # Verify password consistency
   grep MONGODB_PASSWORD infra/.env
   grep MONGO_INITDB_ROOT_PASSWORD infra/docker-compose.yml
   # These should reference the same value
   ```

5. **Database Migration**
   ```bash
   # Run any pending migrations
   make db-migrate
   ```

## 🚨 Troubleshooting

### No API Key Error
```
Error: SAPTIVA API key is required but not configured
```
**Solution**: Set SAPTIVA_API_KEY environment variable or configure via admin UI

### API Connection Failed
```
Error: Error calling SAPTIVA API
```
**Solution**: Check network connectivity and API key validity

### Service Status Check
```bash
# Check service logs
docker logs infra-api

# Verify environment
docker exec infra-api env | grep SAPTIVA
```

## ✅ Validation Checklist

Before deployment:
- [ ] SAPTIVA_API_KEY is set in environment
- [ ] API key is valid and active
- [ ] Network access to api.saptiva.com is available
- [ ] Health endpoint returns 200
- [ ] Chat functionality produces real responses (not demo text)
- [ ] No "demo mode" indicators in UI
- [ ] Error handling works correctly without fallbacks

## 📞 Support
If you encounter issues:
1. Check environment variable configuration
2. Verify API key validity with SAPTIVA support
3. Review application logs for specific error messages
4. Test API connectivity manually with curl

---
Generated: $(date)
System: Production Ready ✅