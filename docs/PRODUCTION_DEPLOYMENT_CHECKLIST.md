# 🚀 Production Deployment Checklist

**Last Updated:** 2025-10-09
**Target Environment:** Production Server (34.42.214.246)
**Domain:** copilotos.saptiva.com

---

## ⚠️ CRITICAL SECURITY ACTIONS REQUIRED BEFORE DEPLOYMENT

### 🔴 Priority 1: API Key Security (IMMEDIATE)

**Status:** ⚠️ **SECURITY RISK DETECTED**

The SAPTIVA API key currently in `envs/.env.prod` (line 38) was **previously exposed** in the git repository history and documentation. According to the security audit report (docs/SECURITY_AUDIT_REPORT.md), this key should have been revoked.

**Required Actions:**

1. **Revoke the exposed API key:**
   ```bash
   # Visit: https://saptiva.com/dashboard/api-keys
   # Revoke key: va-ai-Jm4BHu... (108 characters)
   ```

2. **Generate new API key:**
   ```bash
   # 1. Generate new key from Saptiva dashboard
   # 2. Update envs/.env.prod:
   SAPTIVA_API_KEY=<your-new-key-here>
   ```

3. **Verify key is NOT in git history:**
   ```bash
   git log --all -S "va-ai-Jm4B" --oneline
   # Should show commits but key should be redacted in current code
   ```

**Risk if not addressed:** Unauthorized API usage, billing fraud, data access compromise.

---

## 📋 Pre-Deployment Checklist

### ✅ Phase 1: Environment Configuration

- [ ] **Update Production Environment File** (`envs/.env.prod`)
  - [ ] Set correct `PROD_SERVER_IP=34.42.214.246`
  - [ ] Set correct `PROD_DOMAIN=copilotos.saptiva.com`
  - [ ] Generate NEW `SAPTIVA_API_KEY` (revoke old one)
  - [ ] Verify `MONGODB_PASSWORD` is strong
  - [ ] Verify `REDIS_PASSWORD` is strong
  - [ ] Verify `JWT_SECRET_KEY` is 64+ characters
  - [ ] Verify `SECRET_KEY` is 64+ characters

- [ ] **Verify Environment Variable Loading**
  ```bash
  # Test that deployment scripts load .env.prod correctly
  source envs/.env.prod
  echo "Server: $DEPLOY_SERVER"
  echo "Path: $DEPLOY_PATH"
  echo "Domain: $PROD_DOMAIN"
  ```

### ✅ Phase 2: Server Preparation

- [ ] **Verify SSH Access**
  ```bash
  ssh jf@34.42.214.246 "echo 'SSH OK'"
  ```

- [ ] **Check Server Resources**
  ```bash
  make deploy-check-resources
  # Or manually:
  ssh jf@34.42.214.246 "df -h && free -h && docker --version"
  ```

- [ ] **Verify Server Directory Structure**
  ```bash
  ssh jf@34.42.214.246 "ls -la /home/jf/copilotos-bridge"
  ```

- [ ] **Check Running Services**
  ```bash
  ssh jf@34.42.214.246 "docker ps | grep copilotos"
  ```

### ✅ Phase 3: Code and Dependencies

- [ ] **Verify Local Build**
  ```bash
  # Test that containers build successfully
  docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml build
  ```

- [ ] **Run Security Scan**
  ```bash
  make security-audit
  # Verify no new secrets were added
  ```

- [ ] **Run Pre-commit Hooks**
  ```bash
  make install-hooks
  git add -A
  git commit --dry-run
  # Should pass all checks
  ```

- [ ] **Verify Dependencies**
  ```bash
  make verify-deps
  ```

### ✅ Phase 4: Backup Current Production

- [ ] **Create Production Backup**
  ```bash
  # On production server
  ssh jf@34.42.214.246 << 'EOF'
    cd /home/jf/copilotos-bridge
    timestamp=$(date +%Y%m%d_%H%M%S)

    # Backup database
    docker exec copilotos-mongodb mongodump --out /tmp/backup_$timestamp

    # Backup environment
    mkdir -p /home/jf/backups/copilotos-production
    cp -r envs /home/jf/backups/copilotos-production/envs_$timestamp

    # Backup docker volumes
    docker run --rm -v copilotos_mongodb_data:/data -v /home/jf/backups:/backup \
      ubuntu tar czf /backup/mongodb_$timestamp.tar.gz /data

    echo "Backup completed: $timestamp"
  EOF
  ```

- [ ] **Document Current State**
  ```bash
  # Save current git commit
  ssh jf@34.42.214.246 "cd /home/jf/copilotos-bridge && git log -1 --oneline" > pre_deploy_commit.txt

  # Save current container status
  ssh jf@34.42.214.246 "docker ps" > pre_deploy_containers.txt
  ```

### ✅ Phase 5: Deployment Execution

- [ ] **Review Deployment Plan**
  ```bash
  cat scripts/deploy-with-tar.sh
  # Understand what the script will do
  ```

- [ ] **Perform Deployment**

  **Option A: Quick Deployment (Recommended for code changes)**
  ```bash
  make deploy-quick
  ```

  **Option B: Full Clean Deployment (Recommended for dependencies/config changes)**
  ```bash
  make deploy-clean
  ```

  **Option C: Manual Deployment**
  ```bash
  ./scripts/deploy-with-tar.sh
  ```

- [ ] **Monitor Deployment**
  ```bash
  # Watch logs during deployment
  ssh jf@34.42.214.246 "cd /home/jf/copilotos-bridge && docker compose logs -f"
  ```

### ✅ Phase 6: Post-Deployment Verification

- [ ] **Run Health Checks**
  ```bash
  # From local machine
  make prod-health-check

  # Or manually check each service
  curl http://34.42.214.246:8001/api/health
  curl http://34.42.214.246:3000
  ```

- [ ] **Verify All Services**
  ```bash
  ssh jf@34.42.214.246 << 'EOF'
    cd /home/jf/copilotos-bridge
    docker compose ps
    docker compose logs --tail=50 api
    docker compose logs --tail=50 web
  EOF
  ```

- [ ] **Test Authentication Flow**
  ```bash
  # Test login endpoint
  curl -X POST http://34.42.214.246:8001/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"identifier":"demo","password":"Demo1234"}'
  ```

- [ ] **Test Domain Access** (if DNS is configured)
  ```bash
  curl https://copilotos.saptiva.com/api/health
  ```

- [ ] **Verify Database Connectivity**
  ```bash
  ssh jf@34.42.214.246 "docker exec copilotos-mongodb mongosh --eval 'db.runCommand({ping: 1})'"
  ```

- [ ] **Verify Redis Connectivity**
  ```bash
  ssh jf@34.42.214.246 "docker exec copilotos-redis redis-cli ping"
  ```

### ✅ Phase 7: Performance and Monitoring

- [ ] **Check Resource Usage**
  ```bash
  ssh jf@34.42.214.246 << 'EOF'
    echo "=== CPU & Memory ==="
    docker stats --no-stream

    echo "=== Disk Usage ==="
    df -h | grep -E "/$|/var"

    echo "=== Network Ports ==="
    netstat -tlnp | grep -E ":(3000|8001|80|443)"
  EOF
  ```

- [ ] **Verify Logs are Being Collected**
  ```bash
  ssh jf@34.42.214.246 "docker compose logs --tail=100 | wc -l"
  ```

- [ ] **Set Up Log Monitoring** (if not already configured)
  ```bash
  # Configure log rotation
  # Configure alerting for errors
  # Set up metrics collection
  ```

### ✅ Phase 8: Security Validation

- [ ] **Verify No Secrets in Logs**
  ```bash
  ssh jf@34.42.214.246 "docker compose logs | grep -i 'password\|secret\|key' | head -20"
  # Should not expose actual secrets
  ```

- [ ] **Check CORS Configuration**
  ```bash
  curl -H "Origin: https://evil.com" -I http://34.42.214.246:8001/api/health
  # Should not allow unauthorized origins
  ```

- [ ] **Verify Rate Limiting**
  ```bash
  for i in {1..150}; do curl -s http://34.42.214.246:8001/api/health > /dev/null; done
  # Should eventually get rate limited
  ```

- [ ] **SSL/TLS Configuration** (if using HTTPS)
  ```bash
  # Check SSL certificate
  openssl s_client -connect copilotos.saptiva.com:443 -servername copilotos.saptiva.com

  # Test SSL rating
  # Visit: https://www.ssllabs.com/ssltest/analyze.html?d=copilotos.saptiva.com
  ```

---

## 🔧 Common Deployment Issues

### Issue 1: MongoDB Authentication Failed

**Symptoms:**
```
pymongo.errors.OperationFailure: Authentication failed
```

**Solution:**
```bash
# 1. Remove volumes and recreate
ssh jf@34.42.214.246 << 'EOF'
  cd /home/jf/copilotos-bridge
  docker compose down -v
  docker compose up -d
EOF
```

### Issue 2: Frontend Module Not Found

**Symptoms:**
```
Module not found: Can't resolve 'react-hot-toast'
```

**Solution:**
```bash
# Rebuild web container without cache
ssh jf@34.42.214.246 << 'EOF'
  cd /home/jf/copilotos-bridge
  docker compose build --no-cache web
  docker compose up -d web
EOF
```

### Issue 3: Environment Variables Not Loading

**Symptoms:**
- Deployment scripts use placeholder values
- Services can't connect to each other

**Solution:**
```bash
# Verify .env.prod exists and is loaded
ssh jf@34.42.214.246 << 'EOF'
  cd /home/jf/copilotos-bridge
  cat envs/.env.prod | head -30
  source envs/.env.prod
  echo "Deploy to: $DEPLOY_SERVER"
EOF
```

---

## 🎯 Success Criteria

Deployment is considered successful when:

1. ✅ All containers are running (`docker compose ps` shows healthy)
2. ✅ API health endpoint returns `{"status":"healthy"}`
3. ✅ Frontend is accessible and renders correctly
4. ✅ User can login successfully
5. ✅ Chat functionality works (can send/receive messages)
6. ✅ Database queries are working
7. ✅ Redis cache is operational
8. ✅ No critical errors in logs
9. ✅ All security checks pass
10. ✅ Performance is acceptable (response time < 2s)

---

## 📞 Rollback Plan

If deployment fails critically:

### Quick Rollback

```bash
ssh jf@34.42.214.246 << 'EOF'
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

### Full Rollback with Database Restore

```bash
ssh jf@34.42.214.246 << 'EOF'
  cd /home/jf/copilotos-bridge

  # 1. Stop services
  docker compose down

  # 2. Restore database backup
  timestamp=<backup-timestamp>
  docker run --rm -v copilotos_mongodb_data:/data -v /home/jf/backups:/backup \
    ubuntu tar xzf /backup/mongodb_$timestamp.tar.gz -C /

  # 3. Restore environment
  cp /home/jf/backups/copilotos-production/envs_$timestamp/.env.prod envs/

  # 4. Checkout code
  git checkout <stable-commit>

  # 5. Restart
  docker compose up -d
EOF
```

---

## 📊 Post-Deployment Monitoring

### First 24 Hours

Monitor these metrics closely:

- **Error rate:** Should be < 1%
- **Response time:** Should be < 2s (p95)
- **CPU usage:** Should be < 70%
- **Memory usage:** Should be < 80%
- **Disk space:** Should have > 10GB free
- **API key usage:** Monitor for unexpected spikes

### Commands for Monitoring

```bash
# Real-time logs
ssh jf@34.42.214.246 "cd /home/jf/copilotos-bridge && docker compose logs -f --tail=100"

# Error logs only
ssh jf@34.42.214.246 "cd /home/jf/copilotos-bridge && docker compose logs | grep -i error"

# Resource usage
ssh jf@34.42.214.246 "docker stats --no-stream"

# Health check every 5 minutes
watch -n 300 "make prod-health-check"
```

---

## ✅ Final Checklist

Before closing this deployment:

- [ ] All health checks pass
- [ ] No critical errors in logs
- [ ] Team notified of deployment
- [ ] Deployment documented (commit hash, timestamp)
- [ ] Monitoring dashboards checked
- [ ] Backup verified and accessible
- [ ] Rollback plan tested and ready
- [ ] Post-deployment review scheduled

---

**Deployment Date:** _______________
**Deployed By:** _______________
**Commit Hash:** _______________
**Notes:**

```
<deployment-notes>
Add any deployment-specific notes here
</deployment-notes>
```

---

## 📚 Related Documentation

- [Deployment Guide](DEPLOY_GUIDE.md) - Comprehensive deployment instructions
- [Security Audit Report](SECURITY_AUDIT_REPORT.md) - Security findings and remediation
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Getting Started](GETTING_STARTED.md) - Development setup

---

**Status:** 🟡 **READY FOR DEPLOYMENT** (after API key rotation)
