# PRE-DEPLOYMENT CHECKLIST

**Version:** 1.0
**Last Updated:** 2025-10-09
**Purpose:** Ensure safe deployment with zero data loss risk

---

## 🎯 DEPLOYMENT READINESS - NEXT DEPLOY (IMMEDIATE)

**Estimated Time:** 15-20 minutes
**Deploy Method:** `make deploy` (regular deployment)
**Risk Level:** 🟡 MEDIUM (first deploy after backup system implementation)

---

## ✅ PHASE 1: PRE-DEPLOYMENT VERIFICATION (5 min)

### 1.1 Git Status Check
```bash
# Check current branch and status
git status
git log --oneline -5

# Expected: Clean working tree on main branch
```

**Checklist:**
- [ ] On `main` branch
- [ ] No uncommitted changes
- [ ] Recent commits are documented
- [ ] Version tags are up to date

### 1.2 Local Testing
```bash
# Run local tests (if applicable)
make test-all

# Verify no critical failures
```

**Checklist:**
- [ ] All tests pass or failures are documented
- [ ] No new security issues
- [ ] Linting passes

### 1.3 Backup Scripts Verification (CRITICAL)
```bash
# Test new backup scripts locally (development environment)
cd ~/Proyects/backup/copilotos-bridge

# 1. Check scripts are executable
ls -la scripts/backup-*.sh scripts/restore-*.sh scripts/monitor-*.sh

# 2. Verify documentation exists
ls -la docs/DISASTER-RECOVERY.md docs/BACKUP-SETUP.md

# 3. Check Makefile has new commands
make help | grep -A 5 "Backup & Disaster"
```

**Checklist:**
- [ ] All backup scripts are executable (rwxr-xr-x)
- [ ] Documentation is complete and accessible
- [ ] Makefile includes new backup commands
- [ ] Scripts have no syntax errors (`bash -n script.sh`)

---

## 🚨 PHASE 2: CRITICAL PRE-DEPLOY ACTIONS (3 min)

### 2.1 Create Manual Backup (MANDATORY)

**ON PRODUCTION SERVER:**
```bash
# SSH into production
ssh production-server

# Navigate to project
cd ~/copilotos-bridge

# Source environment
source envs/.env.prod

# Create pre-deployment backup
mkdir -p ~/backups/mongodb-pre-deploy
docker exec copilotos-prod-mongodb mongodump \
    --uri="mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin" \
    --gzip \
    --archive="~/backups/mongodb-pre-deploy/pre-deploy-$(date +%Y%m%d_%H%M%S).gz"

# Verify backup was created
ls -lh ~/backups/mongodb-pre-deploy/ | tail -3
```

**Checklist:**
- [ ] Backup created successfully
- [ ] Backup size is reasonable (> 1MB typically)
- [ ] Backup file is accessible
- [ ] Backup timestamp is recent

**⚠️ CRITICAL:** Do NOT proceed if backup fails!

### 2.2 Document Current State
```bash
# Capture current state for comparison
git log -1 --format="%h - %s" > /tmp/pre-deploy-commit.txt
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | grep copilotos > /tmp/pre-deploy-containers.txt
docker images | grep copilotos > /tmp/pre-deploy-images.txt

# Test current application
curl -s http://localhost:8001/api/health | jq > /tmp/pre-deploy-health.txt
```

**Checklist:**
- [ ] Current commit documented
- [ ] Container states documented
- [ ] Application is healthy
- [ ] Baseline metrics captured

### 2.3 Verify Production Environment
```bash
# Check disk space
df -h | grep -E "/$|/home|/opt"

# Check Docker resources
docker system df

# Check running containers
docker ps | grep copilotos
```

**Checklist:**
- [ ] Disk space > 10GB free
- [ ] Docker has space for new images
- [ ] All services are running and healthy
- [ ] No zombie containers or volumes

---

## 📦 PHASE 3: DEPLOYMENT EXECUTION (8-12 min)

### 3.1 Deployment Command

**Choose ONE based on scenario:**

```bash
# Option 1: Regular deployment (RECOMMENDED for this deploy)
make deploy           # 8-12 min, full build with cache

# Option 2: Fast deployment (use if only minor changes)
make deploy-fast      # 3-5 min, incremental build

# Option 3: Clean deployment (use if dependencies changed)
make deploy-clean     # 12-15 min, no cache, guaranteed fresh
```

**For THIS deploy, use:** `make deploy`

**Reasoning:** First deploy after major changes (backup system), want full build with cache for safety.

### 3.2 Monitor Deployment Progress

**Watch deployment logs:**
```bash
# In another terminal, watch logs
ssh production-server "docker logs -f copilotos-prod-api"
```

**Checklist:**
- [ ] Build completes without errors
- [ ] Images transfer successfully
- [ ] Containers start without crashes
- [ ] Health checks pass

### 3.3 Deployment Failure Protocol

**IF deployment fails:**
```bash
# 1. STOP immediately
# 2. Capture error logs
docker logs copilotos-prod-api > /tmp/deploy-failure-api.log
docker logs copilotos-prod-web > /tmp/deploy-failure-web.log

# 3. Check if data is intact
docker exec copilotos-prod-mongodb mongosh \
    mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin \
    --eval "db.users.countDocuments()"

# 4. Restore previous state (if needed)
# See: docs/DISASTER-RECOVERY.md

# 5. DO NOT run `docker compose down -v`
```

---

## ✅ PHASE 4: POST-DEPLOYMENT VERIFICATION (5 min)

### 4.1 Service Health Check
```bash
# Wait for services to stabilize
sleep 30

# Check health endpoint
curl -s http://localhost:8001/api/health | jq

# Expected output:
# {
#   "status": "healthy",
#   "database": "connected",
#   "redis": "connected"
# }
```

**Checklist:**
- [ ] API health endpoint returns 200 OK
- [ ] Web frontend loads (https://your-domain.com)
- [ ] All containers are running
- [ ] No error logs in recent 50 lines

### 4.2 Data Integrity Check
```bash
# Verify database collections
docker exec copilotos-prod-mongodb mongosh \
    mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin \
    --eval "db.getCollectionNames()"

# Count critical collections
docker exec copilotos-prod-mongodb mongosh \
    mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin \
    --eval "print('Users: ' + db.users.countDocuments()); \
            print('Sessions: ' + db.chat_sessions.countDocuments()); \
            print('Messages: ' + db.chat_messages.countDocuments())"
```

**Checklist:**
- [ ] All expected collections exist
- [ ] Document counts match pre-deploy baseline (or higher)
- [ ] No data loss detected
- [ ] Sample queries return expected data

### 4.3 Functional Smoke Tests
```bash
# Test authentication
curl -X POST http://localhost:8001/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"identifier":"demo","password":"Demo1234"}'

# Should return access_token

# Test models endpoint
curl -s http://localhost:8001/api/models | jq '.allowed_models[]'
```

**Checklist:**
- [ ] Login works
- [ ] Protected endpoints require authentication
- [ ] Models are available
- [ ] Chat endpoint is accessible

### 4.4 Performance Baseline
```bash
# Check response times
time curl -s http://localhost:8001/api/health > /dev/null

# Check resource usage
docker stats --no-stream | grep copilotos
```

**Checklist:**
- [ ] API responds in < 2 seconds
- [ ] Memory usage is reasonable (< 1GB per service)
- [ ] CPU usage is normal (< 50% idle)
- [ ] No memory leaks observed

### 4.5 Backup System Verification (NEW)
```bash
# Test new backup scripts on production
cd ~/copilotos-bridge

# Test backup command
make backup-mongodb-prod

# Verify backup was created
ls -lht ~/backups/mongodb/ | head -3

# Test monitoring
make monitor-backups
```

**Checklist:**
- [ ] Backup scripts work on production
- [ ] Backup created successfully post-deploy
- [ ] Monitoring detects backup
- [ ] No errors in backup logs

---

## 📋 PHASE 5: POST-DEPLOY CONFIGURATION (5 min)

### 5.1 Setup Automated Backups (IF NOT ALREADY DONE)

```bash
# On production server
crontab -e

# Add cron jobs (see docs/BACKUP-SETUP.md)
0 */6 * * * source $HOME/copilotos-bridge/envs/.env.prod && $HOME/copilotos-bridge/scripts/backup-mongodb.sh >> $HOME/backups/mongodb/cron.log 2>&1
0 2 * * * source $HOME/copilotos-bridge/envs/.env.prod && $HOME/copilotos-bridge/scripts/backup-docker-volumes.sh >> $HOME/backups/docker-volumes/cron.log 2>&1
*/15 * * * * $HOME/copilotos-bridge/scripts/monitor-backups.sh >> $HOME/backups/mongodb/monitor.log 2>&1

# Verify cron jobs are installed
crontab -l
```

**Checklist:**
- [ ] Cron jobs are configured
- [ ] Cron service is running
- [ ] First automated backup will run within 6 hours
- [ ] Monitoring is active

### 5.2 Clear Caches (IMPORTANT)
```bash
# Clear Redis cache
make clear-cache

# Or manually:
docker exec copilotos-prod-redis redis-cli -a ${REDIS_PASSWORD} FLUSHALL
docker compose restart web
```

**Checklist:**
- [ ] Redis cache cleared
- [ ] Web container restarted
- [ ] Frontend shows latest code

### 5.3 Update Documentation
```bash
# Update deployment log
echo "$(date '+%Y-%m-%d %H:%M:%S') - Deployment successful - Commit: $(git log -1 --format='%h')" >> ~/deployment-history.log

# Document any issues encountered
# Add to docs/DEPLOYMENT-NOTES.md
```

**Checklist:**
- [ ] Deployment logged
- [ ] Issues documented
- [ ] Team notified via Slack/Discord

---

## 🧪 PHASE 6: IMPROVEMENTS FOR NEXT DEPLOY

### 6.1 Quick Wins (Implement Today)

**1. Add Pre-Deploy Backup to Makefile:**
```makefile
## Pre-deployment safety backup
pre-deploy-backup:
	@echo "$(BLUE)Creating pre-deployment backup...$(NC)"
	@ssh $(PROD_SERVER_HOST) "cd $(PROD_DEPLOY_PATH) && source envs/.env.prod && ./scripts/backup-mongodb.sh --backup-dir ~/backups/mongodb-pre-deploy"
	@echo "$(GREEN)✓ Pre-deploy backup created$(NC)"
```

**2. Add Post-Deploy Verification:**
```makefile
## Post-deployment verification
post-deploy-verify:
	@echo "$(BLUE)Running post-deployment verification...$(NC)"
	@ssh $(PROD_SERVER_HOST) "cd $(PROD_DEPLOY_PATH) && make health"
	@ssh $(PROD_SERVER_HOST) "cd $(PROD_DEPLOY_PATH) && docker exec copilotos-prod-mongodb mongosh --eval 'db.users.countDocuments()'"
	@echo "$(GREEN)✓ Verification complete$(NC)"
```

**3. Create Deployment Wrapper:**
```bash
#!/bin/bash
# scripts/safe-deploy.sh
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SAFE DEPLOYMENT WORKFLOW"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Pre-deploy backup
echo "Step 1/4: Creating backup..."
make pre-deploy-backup

# 2. Deploy
echo "Step 2/4: Deploying..."
make deploy

# 3. Verify
echo "Step 3/4: Verifying..."
make post-deploy-verify

# 4. Clear cache
echo "Step 4/4: Clearing cache..."
make clear-cache

echo "✓ Deployment complete!"
```

### 6.2 Medium-Term Improvements (Next Week)

**1. Staging Environment:**
- [ ] Create staging environment matching production
- [ ] Test all deployments in staging first
- [ ] Automate staging → production promotion

**2. Deployment Metrics:**
- [ ] Track deployment duration
- [ ] Monitor error rates post-deploy
- [ ] Alert on anomalies

**3. Automated Testing:**
- [ ] Run integration tests post-deploy
- [ ] Automated smoke tests
- [ ] Performance regression tests

### 6.3 Long-Term Improvements (Next Month)

**1. Blue-Green Deployments:**
- [ ] Set up parallel environments
- [ ] Zero-downtime deployments
- [ ] Instant rollback capability

**2. Monitoring & Observability:**
- [ ] Application performance monitoring (APM)
- [ ] Distributed tracing
- [ ] Real-time alerts

**3. CI/CD Pipeline:**
- [ ] GitHub Actions / GitLab CI
- [ ] Automated testing on PR
- [ ] Automated staging deployments

---

## 📊 SUCCESS METRICS

**Deployment Success Criteria:**
- ✅ Zero data loss
- ✅ Zero downtime (or < 30 seconds)
- ✅ All services healthy post-deploy
- ✅ Backup system operational
- ✅ No critical errors in logs

**Post-Deployment Health:**
- Response time < 2s
- Error rate < 0.1%
- All monitoring green
- User reports no issues

---

## 🚨 ROLLBACK PLAN

**IF deployment fails catastrophically:**

```bash
# IMMEDIATE ACTIONS:
# 1. Stop new containers
docker compose down --remove-orphans

# 2. DO NOT USE -v FLAG (preserves data)

# 3. Restore from backup
~/copilotos-bridge/scripts/restore-mongodb.sh \
    --backup-file ~/backups/mongodb-pre-deploy/pre-deploy-[TIMESTAMP].gz \
    --drop

# 4. Restart with previous images
docker compose up -d

# 5. Verify restoration
make health
```

**See:** `docs/DISASTER-RECOVERY.md` for complete procedures.

---

## 📞 EMERGENCY CONTACTS

- **On-Call Engineer:** [Your Name]
- **Backup:** [Senior DevOps]
- **Escalation:** [CTO/Engineering Director]
- **Slack Channel:** `#incidents`

---

## ✍️ DEPLOYMENT LOG

**Date:** 2025-10-09
**Time:** [FILL IN]
**Commit:** [FILL IN]
**Deployed By:** [FILL IN]
**Duration:** [FILL IN]
**Issues:** [FILL IN]
**Rollback Required:** [ ] Yes [ ] No

---

**REMEMBER:**
- ✅ Always create backup before deploy
- ✅ Never use `docker compose down -v` without recent backup
- ✅ Test restore procedures regularly
- ✅ Document everything

**Good luck with your deployment! 🚀**
