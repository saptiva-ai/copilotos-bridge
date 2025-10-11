# 🚀 Production Deployment Guide - CopilotOS

**Last Updated:** 2025-10-09
**Target Environment:** Production Server
**Deployment Methods:** TAR Transfer (recommended), Docker Registry, Manual

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Security Pre-Flight Checks](#security-pre-flight-checks)
4. [Deployment Methods](#deployment-methods)
5. [Step-by-Step Deployment](#step-by-step-deployment)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Procedures](#rollback-procedures)
9. [Monitoring & Maintenance](#monitoring--maintenance)
10. [Security Best Practices](#security-best-practices)
11. [Lessons from Incidents](#lessons-from-incidents)

---

## Overview

This guide provides comprehensive instructions for deploying CopilotOS to production environments. It consolidates best practices learned from production incidents and provides step-by-step procedures for safe, repeatable deployments.

### When to Use This Guide

- **Production deployments** - Deploying to live servers
- **Major releases** - Feature releases, dependency updates
- **Recovery scenarios** - After incidents or rollbacks

### Related Documentation

- **Development Setup:** `docs/GETTING_STARTED.md`
- **Incident Analysis:** `docs/POST-MORTEM-DATA-LOSS-2025-10-09.md`
- **DevOps Analysis:** `docs/DEPLOYMENT-FAILURES-ANALYSIS.md`
- **Architecture:** `README.md`

---

## Prerequisites

### System Requirements

**On Production Server:**
- Docker 20.10+ and Docker Compose
- Git 2.30+
- Bash 4.0+
- openssl (for secrets)
- 8GB+ RAM recommended
- 50GB+ free disk space

**On Local Machine:**
- Docker (for building images)
- SSH access to production server
- Git repository access

### Required Credentials

Before deployment, prepare:

1. **SAPTIVA API Key** (REQUIRED)
   - Get from: https://saptiva.com/dashboard/api-keys
   - Format: `va-ai-...`
   - **CRITICAL:** Must be different from development key

2. **Aletheia API Key** (optional)
   - Required only for deep research features
   - Get from: https://aletheia.saptiva.ai/keys

3. **Server Access**
   - SSH credentials for production server
   - Sudo access for Nginx configuration (if needed)

4. **Production Environment File**
   - `envs/.env.prod` must exist
   - Run `make setup-interactive-prod` if not configured

---

## Security Pre-Flight Checks

### ⚠️ CRITICAL: Pre-Deployment Security Actions

**Run this command BEFORE every deployment:**

```bash
make security-audit
```

This will check for:
- Secrets in Git history
- Hardcoded API keys in code
- Weak passwords in env files
- Insecure file permissions
- IP addresses exposed in documentation

### API Key Security Check

**IMPORTANT:** If your SAPTIVA API key was ever committed to Git:

1. **Revoke the exposed key immediately:**
   ```bash
   # Visit: https://saptiva.com/dashboard/api-keys
   # Revoke the old key
   ```

2. **Generate new API key:**
   ```bash
   # Generate new key from Saptiva dashboard
   # Update envs/.env.prod with new key
   ```

3. **Verify key is NOT in git history:**
   ```bash
   git log --all -S "your-old-key-prefix" --oneline
   ```

**Reference:** See `docs/SECURITY_AUDIT_REPORT.md` if exists for detailed findings.

---

## Deployment Methods

### Method Comparison

| Method | Speed | Use Case | Requires |
|--------|-------|----------|----------|
| **`make deploy-fast`** | ⚡ 3-5 min | Bug fixes, small changes | SSH access |
| **`make deploy`** | 🕐 8-12 min | Regular releases, recommended | SSH access |
| **`make deploy-clean`** | 🧹 12-15 min | Dependencies, major updates | SSH access |
| **`make deploy-prod`** | ⚡ 3-5 min | When registry configured | Docker Registry |

### Choosing the Right Method

**Use `make deploy-fast` when:**
- Quick bug fixes
- CSS/frontend changes
- No dependency updates
- Daily/hourly deployments

**Use `make deploy` when:** (RECOMMENDED DEFAULT)
- Regular feature releases
- Weekly deployments
- Code changes with dependencies
- Unsure which method to use

**Use `make deploy-clean` when:**
- Dependency updates (requirements.txt, package.json)
- Major version bumps
- Environment variable changes
- After troubleshooting build issues
- Monthly major releases

**Use `make deploy-prod` when:**
- Docker Registry (GitHub Packages/Docker Hub) configured
- Team workflow with CI/CD
- Multiple deployments per day

---

## Step-by-Step Deployment

### Phase 1: Pre-Deployment Checks ✅

**Estimated time:** 5-10 minutes

#### 1.1 Environment Configuration

```bash
# Verify production environment file exists
cat envs/.env.prod | head -20

# Check critical variables
grep -E "PROD_SERVER_IP|SAPTIVA_API_KEY|MONGODB_PASSWORD" envs/.env.prod
```

**Checklist:**
- [ ] `PROD_SERVER_IP` matches actual server
- [ ] `PROD_DOMAIN` is correct (if using domain)
- [ ] `SAPTIVA_API_KEY` is production key (not dev key)
- [ ] `MONGODB_PASSWORD` is strong (20+ characters)
- [ ] `REDIS_PASSWORD` is strong (20+ characters)
- [ ] `JWT_SECRET_KEY` is 64+ hex characters
- [ ] `SECRET_KEY` is 64+ hex characters

#### 1.2 Security Audit

```bash
# Run comprehensive security scan
make security-audit

# Install git hooks (if not already done)
make install-hooks
```

**Must pass before proceeding!**

#### 1.3 Local Testing

```bash
# Run complete test suite
make test-all

# Verify local build works
docker compose -f infra/docker-compose.yml build

# Check for uncommitted changes
git status
```

**Checklist:**
- [ ] All tests passing
- [ ] Local build successful
- [ ] Git working directory clean
- [ ] On `main` branch (or release branch)

#### 1.4 Server Verification

```bash
# Verify SSH access
ssh jf@$PROD_SERVER_IP "echo 'SSH OK'"

# Check server resources
make deploy-status

# Or manually check:
ssh jf@$PROD_SERVER_IP "df -h && free -h && docker ps"
```

**Requirements:**
- [ ] SSH access working
- [ ] At least 10GB free disk space
- [ ] Server has Docker running
- [ ] No critical resource warnings

---

### Phase 2: Backup Current Production ✅

**Estimated time:** 5 minutes

#### 2.1 Database Backup

```bash
# On production server, create backup
ssh jf@$PROD_SERVER_IP << 'EOF'
  cd /home/jf/copilotos-bridge
  timestamp=$(date +%Y%m%d_%H%M%S)

  # Backup MongoDB
  docker exec copilotos-mongodb mongodump \
    --gzip \
    --archive=/backup/mongodb_${timestamp}.gz

  # Copy to host
  mkdir -p /home/jf/backups/mongodb
  docker cp copilotos-mongodb:/backup/mongodb_${timestamp}.gz \
    /home/jf/backups/mongodb/

  echo "Backup completed: mongodb_${timestamp}.gz"
EOF
```

#### 2.2 Environment Backup

```bash
ssh jf@$PROD_SERVER_IP << 'EOF'
  cd /home/jf/copilotos-bridge
  timestamp=$(date +%Y%m%d_%H%M%S)

  # Backup environment files
  mkdir -p /home/jf/backups/envs
  cp -r envs /home/jf/backups/envs/backup_${timestamp}

  echo "Environment backed up: backup_${timestamp}"
EOF
```

#### 2.3 Document Current State

```bash
# Save current git commit
ssh jf@$PROD_SERVER_IP "cd /home/jf/copilotos-bridge && git log -1 --oneline" > pre_deploy_commit.txt

# Save current container status
ssh jf@$PROD_SERVER_IP "docker ps" > pre_deploy_containers.txt

# Save current health status
curl -s http://$PROD_SERVER_IP:8001/api/health > pre_deploy_health.json
```

**Checklist:**
- [ ] MongoDB backup created and verified
- [ ] Environment files backed up
- [ ] Current state documented
- [ ] Backup timestamp noted: ________________

---

### Phase 3: Deployment Execution ✅

**Estimated time:** 5-15 minutes (depending on method)

#### 3.1 Choose Deployment Method

**For regular deployments (RECOMMENDED):**

```bash
make deploy
```

**For quick fixes:**

```bash
make deploy-fast
```

**For clean rebuild:**

```bash
make deploy-clean
```

#### 3.2 Monitor Deployment

**In a separate terminal, watch logs:**

```bash
# Watch deployment progress
ssh jf@$PROD_SERVER_IP "cd /home/jf/copilotos-bridge && docker compose logs -f api web"
```

#### 3.3 Deployment Success Indicators

**Look for these signs:**
- ✅ "Build completed" messages
- ✅ "Transfer completed" for TAR deployments
- ✅ "Containers started" confirmation
- ✅ API health check returns `{"status":"healthy"}`

**Watch for errors:**
- ❌ Build failures (exit immediately)
- ❌ Transfer errors (check connectivity)
- ❌ Container crash loops (check logs)

---

### Phase 4: Post-Deployment Verification ✅

**Estimated time:** 10 minutes

#### 4.1 Service Health Checks

```bash
# Run automated health checks
make deploy-status

# Or manually verify each service
curl -s http://$PROD_SERVER_IP:8001/api/health | jq
curl -s http://$PROD_SERVER_IP:3000 | head -20
```

**Expected responses:**
- API: `{"status": "healthy", "database": "connected", "redis": "connected"}`
- Web: HTML with `<title>CopilotOS</title>`

#### 4.2 Container Status

```bash
ssh jf@$PROD_SERVER_IP "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```

**Expected containers:**
- `copilotos-api` - Up, healthy
- `copilotos-web` - Up, healthy
- `copilotos-mongodb` - Up, healthy
- `copilotos-redis` - Up, healthy

#### 4.3 Authentication Flow Test

```bash
# Test login endpoint
curl -X POST http://$PROD_SERVER_IP:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"demo","password":"Demo1234"}' | jq
```

**Expected:** Returns `access_token`, `refresh_token`, and `user` object

#### 4.4 Database Connectivity

```bash
# Test MongoDB
ssh jf@$PROD_SERVER_IP \
  "docker exec copilotos-mongodb mongosh --eval 'db.runCommand({ping: 1})'"

# Test Redis
ssh jf@$PROD_SERVER_IP \
  "docker exec copilotos-redis redis-cli ping"
```

**Expected:** MongoDB returns `{ ok: 1 }`, Redis returns `PONG`

#### 4.5 Performance Check

```bash
# Check response times
time curl -s http://$PROD_SERVER_IP:8001/api/health > /dev/null

# Check resource usage
ssh jf@$PROD_SERVER_IP "docker stats --no-stream"
```

**Expected:**
- API response time: < 500ms
- CPU usage: < 50%
- Memory usage: < 80%

---

### Phase 5: Security Validation ✅

#### 5.1 Verify No Secrets in Logs

```bash
ssh jf@$PROD_SERVER_IP \
  "docker compose logs --tail=200 | grep -i 'password\|secret\|key' | head -20"
```

**Expected:** Should show masked values like `***` or empty strings, NOT actual secrets

#### 5.2 CORS Configuration Check

```bash
curl -H "Origin: https://evil.com" -I http://$PROD_SERVER_IP:8001/api/health
```

**Expected:** Should NOT include `Access-Control-Allow-Origin: https://evil.com`

#### 5.3 Rate Limiting Verification

```bash
# Send 150 requests rapidly
for i in {1..150}; do
  curl -s http://$PROD_SERVER_IP:8001/api/health > /dev/null
done
```

**Expected:** Should eventually get `429 Too Many Requests` response

---

### Phase 6: Finalization ✅

#### 6.1 Clear Application Cache

```bash
# Important: Clear Redis cache to ensure new code loads
make clear-cache
```

#### 6.2 Update Documentation

```bash
# Record deployment details
echo "Deployment Date: $(date)" >> deployments.log
echo "Commit: $(git log -1 --oneline)" >> deployments.log
echo "Deployed by: $(whoami)" >> deployments.log
echo "Method: deploy" >> deployments.log
echo "---" >> deployments.log
```

#### 6.3 Notify Team

- Update team chat/Slack with deployment status
- Note any issues encountered
- Share rollback instructions if needed

---

## Post-Deployment Verification

### Success Criteria

Deployment is considered successful when:

1. ✅ All containers are running (`docker ps` shows healthy)
2. ✅ API health endpoint returns `{"status":"healthy"}`
3. ✅ Frontend is accessible and renders correctly
4. ✅ User can login successfully
5. ✅ Chat functionality works (can send/receive messages)
6. ✅ Database queries are working
7. ✅ Redis cache is operational
8. ✅ No critical errors in logs
9. ✅ All security checks pass
10. ✅ Performance is acceptable (response time < 2s)

### First 24 Hours Monitoring

**Monitor these metrics:**
- **Error rate:** Should be < 1%
- **Response time:** Should be < 2s (p95)
- **CPU usage:** Should be < 70%
- **Memory usage:** Should be < 80%
- **Disk space:** Should have > 10GB free

**Commands for monitoring:**

```bash
# Real-time logs
ssh jf@$PROD_SERVER_IP "docker compose logs -f --tail=100"

# Error logs only
ssh jf@$PROD_SERVER_IP "docker compose logs | grep -i error"

# Resource usage
ssh jf@$PROD_SERVER_IP "docker stats --no-stream"

# Health check every 5 minutes
watch -n 300 "make deploy-status"
```

---

## Troubleshooting

### Issue 1: MongoDB Authentication Failed

**Symptoms:**
```
pymongo.errors.OperationFailure: Authentication failed
```

**Solution:**
```bash
# 1. Verify credentials in env file match MongoDB initialization
ssh jf@$PROD_SERVER_IP "cat /home/jf/copilotos-bridge/envs/.env.prod | grep MONGODB"

# 2. If credentials mismatch, recreate volumes
ssh jf@$PROD_SERVER_IP << 'EOF'
  cd /home/jf/copilotos-bridge
  docker compose down -v  # WARNING: This deletes data!
  docker compose up -d
EOF
```

**Prevention:** Always ensure `.env.prod` is loaded correctly before starting services

---

### Issue 2: Frontend Module Not Found

**Symptoms:**
```
Module not found: Can't resolve 'react-hot-toast'
```

**Solution:**
```bash
# Rebuild web container without cache
ssh jf@$PROD_SERVER_IP << 'EOF'
  cd /home/jf/copilotos-bridge
  docker compose build --no-cache web
  docker compose up -d web
EOF
```

**Prevention:** Use `make deploy-clean` after package.json changes

---

### Issue 3: Code Changes Not Reflected

**Symptoms:**
- Modified code doesn't run
- Old behavior persists

**Solution:**
```bash
# Proper rebuild procedure
make rebuild-api      # For API changes
make rebuild-web      # For frontend changes
make rebuild-all      # For env var changes
```

**Why?**
- Docker caches image layers
- `docker restart` keeps old container
- Need `build --no-cache` + `down` + `up` to recreate

---

### Issue 4: Environment Variables Not Loading

**Symptoms:**
- Services can't connect to each other
- Placeholder values in use

**Solution:**
```bash
# Verify .env.prod exists and is loaded
ssh jf@$PROD_SERVER_IP << 'EOF'
  cd /home/jf/copilotos-bridge
  cat envs/.env.prod | head -30
  source envs/.env.prod
  echo "Deploy to: $DEPLOY_SERVER"
EOF
```

**Prevention:** Always run `make setup-interactive-prod` before first deployment

---

### Quick Diagnostic Commands

```bash
# Full diagnostic report
make debug-full

# Check container status
make status

# View recent errors
docker compose logs --tail=100 | grep -i error

# Test connectivity
make health
```

---

## Rollback Procedures

### Quick Rollback (5 minutes)

**Use when:** Deployment broke something critical, need immediate recovery

```bash
ssh jf@$PROD_SERVER_IP << 'EOF'
  cd /home/jf/copilotos-bridge

  # 1. Checkout previous commit
  git log --oneline | head -5
  git checkout <previous-commit-hash>

  # 2. Restart services
  docker compose down
  docker compose up -d

  # 3. Verify health
  sleep 10
  curl http://localhost:8001/api/health
EOF
```

---

### Full Rollback with Database Restore (15 minutes)

**Use when:** Data was corrupted or lost during deployment

```bash
ssh jf@$PROD_SERVER_IP << 'EOF'
  cd /home/jf/copilotos-bridge

  # 1. Stop services
  docker compose down

  # 2. Restore database backup
  timestamp=<backup-timestamp-from-phase-2>
  gunzip -c /home/jf/backups/mongodb/mongodb_${timestamp}.gz | \
    docker exec -i copilotos-mongodb mongorestore --archive --gzip

  # 3. Restore environment
  cp -r /home/jf/backups/envs/backup_${timestamp}/envs/* envs/

  # 4. Checkout code
  git checkout <stable-commit>

  # 5. Restart
  docker compose up -d

  # 6. Verify
  sleep 15
  curl http://localhost:8001/api/health
EOF
```

---

### When to Rollback

**Rollback immediately if:**
- ❌ API health check fails after 5 minutes
- ❌ Critical functionality broken (auth, chat, database)
- ❌ Data corruption detected
- ❌ Security vulnerability introduced

**Consider rollback if:**
- ⚠️ Error rate > 5% for 15 minutes
- ⚠️ Response time > 5s consistently
- ⚠️ Memory usage > 95%

**Do NOT rollback if:**
- ✅ Minor UI issues (can be fixed with hotfix)
- ✅ Non-critical feature broken (can be disabled)
- ✅ Performance slightly degraded but acceptable

---

## Monitoring & Maintenance

### Regular Health Checks

**Daily:**
```bash
# Quick status check
make deploy-status

# Check for errors
ssh jf@$PROD_SERVER_IP \
  "docker compose logs --since 24h | grep -i error | wc -l"
```

**Weekly:**
```bash
# Resource usage
make resources

# Database backup verification
ssh jf@$PROD_SERVER_IP \
  "ls -lh /home/jf/backups/mongodb/ | tail -10"

# Security audit
make security-audit
```

**Monthly:**
```bash
# Full system audit
make security-audit

# Disk cleanup
ssh jf@$PROD_SERVER_IP "docker system prune -af --volumes"

# Update dependencies
# (requires thorough testing before deploying)
```

### Automated Monitoring Setup

**Configure log rotation:**
```bash
# Setup cron job for log rotation
ssh jf@$PROD_SERVER_IP << 'EOF'
  echo "0 2 * * * docker system prune -f --filter until=72h" | crontab -
EOF
```

**Backup automation:**
```bash
# Setup daily backups at 2 AM
ssh jf@$PROD_SERVER_IP << 'EOF'
  echo "0 2 * * * /home/jf/scripts/backup-mongodb.sh" | crontab -
EOF
```

---

## Security Best Practices

### Secrets Management

**DO:**
- ✅ Use `make setup-interactive-prod` for production secrets
- ✅ Store production secrets in secure vault (HashiCorp Vault, AWS Secrets Manager)
- ✅ Use different secrets for dev/staging/prod
- ✅ Rotate secrets every 90 days
- ✅ Set file permissions to 600 on .env files

**DON'T:**
- ❌ Commit .env files to Git
- ❌ Share secrets via email/Slack/messaging
- ❌ Use weak or default passwords
- ❌ Reuse the same secrets across environments
- ❌ Store production secrets in code

### Credential Rotation

**If credentials are compromised:**

1. **Immediate actions:**
   ```bash
   # Remove from Git history (if committed)
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch envs/.env*" \
     --prune-empty --tag-name-filter cat -- --all

   # Force push (coordinate with team!)
   git push origin --force --all
   ```

2. **Rotate credentials:**
   ```bash
   # Regenerate production secrets
   make setup-interactive-prod

   # Redeploy with new secrets
   make deploy-clean
   ```

3. **Verify rotation:**
   - Revoke old SAPTIVA API key
   - Confirm old credentials no longer work
   - Update team documentation

### File Permissions

```bash
# Secure env files (on production server)
ssh jf@$PROD_SERVER_IP << 'EOF'
  cd /home/jf/copilotos-bridge
  chmod 600 envs/.env*
  ls -la envs/
  # Should show: -rw------- (600)
EOF
```

---

## Lessons from Incidents

This section summarizes key lessons from production incidents to prevent recurrence.

### Critical Lessons

**1. Backups Are NOT Optional**

> "If it's not in backup, it doesn't exist"

- **Incident:** Data loss on 2025-10-09 (see POST-MORTEM)
- **Solution:** Automated backups every 6 hours + verification
- **Reference:** `docs/POST-MORTEM-DATA-LOSS-2025-10-09.md`

**2. Never Use `-v` Flag Without Recent Backup**

```bash
# DANGEROUS: Deletes all volumes permanently
docker compose down -v

# SAFE: Always backup first
make db-backup
docker compose down -v
```

**3. Test Production Builds Locally**

- **Incident:** Multiple deployment failures (see DEPLOYMENT-FAILURES-ANALYSIS)
- **Solution:** Always run `docker compose build` locally before deploying
- **Reference:** `docs/DEPLOYMENT-FAILURES-ANALYSIS.md`

**4. Dev/Prod Parity Is Critical**

- Development must use production-like configurations
- Use staging environment for final testing
- Never deploy untested configuration changes

**5. Configuration Should Be Explicit**

- Avoid hardcoded env_file paths in docker-compose.yml
- Use environment variables for all credentials
- Document all configuration dependencies

### Recommended Reading

For detailed technical analysis and prevention strategies:

- **📄 POST-MORTEM-DATA-LOSS-2025-10-09.md** - Complete incident timeline and recovery procedures
- **📄 DEPLOYMENT-FAILURES-ANALYSIS.md** - DevOps analysis of 6 deployment failures, CI/CD recommendations
- **📄 README.md** - Architecture overview and development workflows

---

## Appendix

### A. Environment Variables Reference

**Required Variables (Production):**

```bash
# Project
COMPOSE_PROJECT_NAME=copilotos-prod

# Server
PROD_SERVER_IP=your.server.ip
PROD_SERVER_USER=username
PROD_DEPLOY_PATH=/home/username/copilotos-bridge

# Database
MONGODB_USER=copilotos_prod_user
MONGODB_PASSWORD=<strong-password-64-chars>
MONGODB_DATABASE=copilotos

# Redis
REDIS_PASSWORD=<strong-password-64-chars>

# Security
JWT_SECRET_KEY=<hex-64-chars>
SECRET_KEY=<hex-64-chars>

# API Keys
SAPTIVA_API_KEY=va-ai-<your-production-key>
SAPTIVA_BASE_URL=https://api.saptiva.com

# Optional
ALETHEIA_API_KEY=<if-using-research>
```

### B. Makefile Commands Reference

**Deployment Commands:**

| Command | Description | Use Case |
|---------|-------------|----------|
| `make deploy-fast` | Incremental build (3-5 min) | Quick fixes, CSS changes |
| `make deploy` | Full build with cache (8-12 min) | Regular releases (RECOMMENDED) |
| `make deploy-clean` | No-cache rebuild (12-15 min) | Dependencies, major updates |
| `make deploy-prod` | Registry workflow (3-5 min) | With Docker Registry |
| `make deploy-status` | Check server status | Verify deployment |
| `make clear-cache` | Clear Redis + restart | After every deployment |

**Development Commands:**

| Command | Description |
|---------|-------------|
| `make dev` | Start development |
| `make rebuild-api` | Rebuild API only |
| `make rebuild-web` | Rebuild Web only |
| `make rebuild-all` | Rebuild everything |
| `make logs` | View all logs |
| `make health` | Check service health |

### C. Scripts Reference

**Deployment Scripts:**

- `scripts/deploy-with-tar.sh` - Main TAR deployment script
- `scripts/deploy-from-registry.sh` - Registry deployment
- `scripts/push-to-registry.sh` - Push to Docker registry

**Security Scripts:**

- `scripts/security-check.sh` - Pre-deployment security scan
- `scripts/interactive-env-setup.sh` - Interactive environment setup

**Maintenance Scripts:**

- `scripts/backup-mongodb.sh` - MongoDB backup automation
- `scripts/clear-server-cache.sh` - Clear production cache
- `scripts/docker-cleanup.sh` - Safe Docker cleanup

---

## Support

### Getting Help

**Commands:**
```bash
make help              # Show all available commands
make troubleshoot      # Show troubleshooting guide
make debug-full        # Full diagnostic report
```

**Documentation:**
- Main README: `README.md`
- Getting Started: `docs/GETTING_STARTED.md`
- Post-Mortems: `docs/POST-MORTEM-*.md`
- DevOps Analysis: `docs/DEPLOYMENT-FAILURES-ANALYSIS.md`

### Contact

- **Technical Lead:** Jaziel Flores (jf@saptiva.com)
- **GitHub Issues:** https://github.com/your-org/copilotos-bridge/issues

---

**Document Version:** 1.0
**Last Reviewed:** 2025-10-09
**Next Review:** 2025-11-09
