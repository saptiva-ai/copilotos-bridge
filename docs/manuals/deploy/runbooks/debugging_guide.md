# Deployment & Debugging Guide - OctaviOS Chat

## Quick Reference

```bash
# Development (hot-reload)
cd infra
docker compose --env-file ../envs/.env -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production (optimized images)
docker compose --env-file ../envs/.env up -d

# Rebuild specific service
docker compose --env-file ../envs/.env build <service> --no-cache
```

---

## 1. Development with Hot-Reload

### Problem: Code Changes Not Reflected

When you edit source code and changes aren't reflected in the running container, you're likely running in **production mode** (no volume mounts).

### Solution: Use Development Compose Override

```bash
cd infra

# Start ALL services with hot-reload
docker compose --env-file ../envs/.env \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  up -d

# Start specific service with hot-reload
docker compose --env-file ../envs/.env \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  up -d backend bank-advisor
```

### How It Works

`docker-compose.dev.yml` adds volume mounts that override the container's `/app/src` with your local source code:

```yaml
# docker-compose.dev.yml
services:
  backend:
    volumes:
      - ../apps/backend/src:/app/src          # Hot-reload source
      - ../apps/backend/tests:/app/tests:ro   # Read-only tests

  bank-advisor:
    volumes:
      - ../plugins/bank-advisor-private/src:/app/src
      - ../plugins/bank-advisor-private/config:/app/config
```

### Verify Hot-Reload Is Active

```bash
# Check if your changes are in the container
docker compose --env-file ../envs/.env \
  -f docker-compose.yml -f docker-compose.dev.yml \
  exec backend grep "your_change" /app/src/services/your_file.py

# If the change appears, hot-reload is working
# If not, you're in production mode
```

---

## 2. When to Rebuild vs Hot-Reload

| Change Type | Action |
|-------------|--------|
| Python source code (`src/`) | Hot-reload (no rebuild) |
| Config files (`config/`) | Hot-reload (no rebuild) |
| Dependencies (`requirements.txt`) | Rebuild required |
| Dockerfile changes | Rebuild required |
| New files outside mounted dirs | Rebuild required |

### Rebuild Commands

```bash
# Rebuild single service (with cache)
docker compose --env-file ../envs/.env build backend

# Rebuild WITHOUT cache (when cache is stale)
docker compose --env-file ../envs/.env build backend --no-cache

# Nuclear option: remove image and rebuild
docker compose --env-file ../envs/.env stop backend
docker rmi octavios-chat-bajaware_invex-backend
docker compose --env-file ../envs/.env build backend
docker compose --env-file ../envs/.env up -d backend
```

---

## 3. Debugging Docker Issues

### Issue: Container Uses Old Code

**Symptoms:**
- You edited a file but `grep` shows old content in container
- Tests pass locally but fail in container

**Diagnosis:**
```bash
# Check what's actually in the container
docker compose exec backend cat /app/src/services/bank_analytics_client.py | head -50

# Compare with local file
head -50 apps/backend/src/services/bank_analytics_client.py
```

**Solutions (in order of escalation):**

1. **Use dev compose** (if not already):
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d backend
   ```

2. **Restart container** (picks up volume changes):
   ```bash
   docker compose restart backend
   ```

3. **Recreate container** (forces fresh start):
   ```bash
   docker compose up -d --force-recreate backend
   ```

4. **Rebuild image** (when deps changed):
   ```bash
   docker compose build backend && docker compose up -d backend
   ```

5. **Clean rebuild** (nuclear option):
   ```bash
   docker compose down backend
   docker rmi octavios-chat-bajaware_invex-backend
   docker compose build backend --no-cache
   docker compose up -d backend
   ```

### Issue: Redis Cache Returns Stale Data

```bash
# Clear all Redis cache
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" FLUSHDB

# Clear specific cache pattern
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" KEYS "bank_query*" | xargs -r redis-cli -a "$REDIS_PASSWORD" DEL
```

### Issue: Container Won't Start / Unhealthy

```bash
# Check logs for errors
docker compose logs backend --tail=100

# Check health status
docker compose ps

# Interactive debug (run bash in container)
docker compose exec backend bash

# Check if dependencies are installed
docker compose exec backend pip list | grep structlog
```

---

## 4. Service-Specific Debugging

### Backend (port 8000)

```bash
# Logs
docker compose logs backend -f

# Health check
curl http://localhost:8000/api/health

# Test bank query routing
docker compose exec backend python -c "
from src.services.bank_analytics_client import is_bank_query
import asyncio
print(asyncio.run(is_bank_query('Dame el IMOR de INVEX')))
"
```

### Bank-Advisor (port 8002)

```bash
# Logs
docker compose logs bank-advisor -f

# Health check
curl http://localhost:8002/health

# Check synonyms loaded
docker compose exec bank-advisor cat /app/config/synonyms.yaml | grep -A5 "imor:"

# Test metric detection
docker compose exec bank-advisor python -c "
from bankadvisor.services.config_service import ConfigService
cs = ConfigService()
print(cs.find_metric('cartera de consumo'))
"
```

### Web Frontend (port 3000)

```bash
# Logs (verbose in dev mode)
docker compose logs web -f

# Check if API proxy works
curl http://localhost:3000/api/health
```

---

## 5. Production Deployment

### Pre-Deployment Checklist

1. **Run tests locally:**
   ```bash
   cd /home/jazielflo/Proyects/octavios-chat-bajaware_invex
   python tests/e2e/test_happy_path_suite.py
   ```

2. **Build optimized images:**
   ```bash
   docker compose build --no-cache
   ```

3. **Verify env variables:**
   ```bash
   # Check .env has all required vars
   grep -E "^[A-Z]" envs/.env | wc -l
   ```

### Deployment Steps

```bash
# 1. Pull latest code
git pull origin main

# 2. Stop services gracefully
docker compose down

# 3. Build fresh images (production target)
docker compose build --no-cache

# 4. Start services
docker compose up -d

# 5. Verify health
docker compose ps
curl http://localhost:8000/api/health
curl http://localhost:8002/health

# 6. Run smoke test
python tests/e2e/test_happy_path_suite.py --max=10
```

### Rollback Procedure

```bash
# 1. Stop current deployment
docker compose down

# 2. Checkout previous version
git checkout <previous-commit>

# 3. Rebuild and start
docker compose build
docker compose up -d
```

---

## 6. Optimizing Docker Builds

### Use BuildKit (faster builds)

```bash
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
docker compose build
```

### Multi-stage Builds

Our Dockerfiles use multi-stage builds:
- `development` stage: includes test tools, debugger
- `production` stage: minimal, optimized

```dockerfile
# Dockerfile example
FROM python:3.11-slim AS base
# ... common setup

FROM base AS development
RUN pip install pytest pytest-cov debugpy
# ... dev tools

FROM base AS production
COPY --from=base /app /app
# ... only runtime deps
```

### Layer Caching Tips

1. **Order Dockerfile commands by change frequency:**
   ```dockerfile
   # Rarely changes (cached)
   COPY requirements.txt .
   RUN pip install -r requirements.txt

   # Frequently changes (invalidates cache)
   COPY src/ ./src/
   ```

2. **Use .dockerignore:**
   ```
   # .dockerignore
   __pycache__
   *.pyc
   .git
   .env
   tests/
   docs/
   ```

---

## 7. Common Gotchas

### Volume Permissions (Linux)

```bash
# If you get permission errors on Linux
export UID=$(id -u)
export GID=$(id -g)
docker compose up -d
```

### Stale Docker Images

```bash
# List dangling images
docker images -f "dangling=true"

# Clean up
docker system prune -f
```

### Network Issues Between Services

```bash
# Check network connectivity
docker compose exec backend ping bank-advisor

# Verify DNS resolution
docker compose exec backend nslookup bank-advisor
```

---

## 8. Quick Debugging Workflow

When something breaks:

```bash
# 1. Check service status
docker compose ps

# 2. Check logs for errors
docker compose logs <service> --tail=50

# 3. Verify code is current (dev mode)
docker compose exec <service> cat /app/src/<file> | grep "expected_content"

# 4. Clear caches if needed
docker compose exec redis redis-cli FLUSHDB

# 5. Restart service
docker compose restart <service>

# 6. If still broken, rebuild
docker compose build <service> --no-cache && docker compose up -d <service>
```

---

## Summary Commands Cheat Sheet

```bash
# Development
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Check logs
docker compose logs -f <service>

# Rebuild service
docker compose build <service> --no-cache

# Clear Redis cache
docker compose exec redis redis-cli FLUSHDB

# Verify code in container
docker compose exec <service> cat /app/src/<path>

# Run tests
python tests/e2e/test_happy_path_suite.py

# Full restart
docker compose down && docker compose up -d
```
