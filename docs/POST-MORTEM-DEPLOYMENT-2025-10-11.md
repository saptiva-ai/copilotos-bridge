# Post-Mortem: Production Deployment - October 11, 2025

**Status:** ✅ Resolved
**Severity:** Medium (no data loss, zero downtime)
**Duration:** ~27 minutes of troubleshooting
**Date:** 2025-10-11

## Executive Summary

Attempted automated deployment to production on October 11, 2025 encountered 4 incidents during execution. Despite technical issues, **the deployment maintained zero downtime and zero data loss**. All user data (5 users, 20 chat sessions, 36 messages) remained accessible throughout the process. The existing production containers continued serving traffic while issues were resolved.

## Timeline of Events

| Time | Event | Impact |
|------|-------|--------|
| 07:45 | Initial deployment attempt started | - |
| 07:45 | **Incident #1**: MongoDB backup env vars issue | Delay: 5 min |
| 07:50 | Backup successful, deployment continued | - |
| 07:52 | **Incident #2**: Docker images not found | Deployment failed |
| 07:55 | **Incident #3**: Port binding conflicts | Cleanup required |
| 08:00 | Decided to keep existing containers running | Zero downtime achieved |
| 08:05 | **Incident #4**: MongoDB auth during verification | Workaround used |
| 08:12 | Verification complete, data confirmed intact | Full recovery |

**Total time:** ~27 minutes
**Data loss:** ZERO
**Downtime:** ZERO
**Users affected:** ZERO

## Incidents

### 🔴 Incident #1: MongoDB Backup Environment Variables

**What happened:**
```
✖ [2025-10-11 07:45:40] MONGODB_PASSWORD environment variable is required!
```

**Root cause:**
- Environment variables don't automatically propagate through SSH commands
- `source envs/.env.prod` doesn't work in SSH one-liners
- Script expected variables to be available but they weren't loaded

**Impact:** Low
- Delayed deployment by ~5 minutes
- Backup eventually succeeded with corrected command

**Resolution:**
```bash
# Passed variables inline in SSH command
ssh jf@34.42.214.246 "cd /home/jf/copilotos-bridge && \
  MONGODB_PASSWORD=ProdMongo2024\!SecurePass \
  MONGODB_USER=copilotos_prod_user \
  ./scripts/backup-mongodb.sh"
```

**Improvements implemented:**
1. ✅ Updated `backup-mongodb.sh` to support `--env-file` flag
2. ✅ Created documentation: `docs/SSH_ENVIRONMENT_PATTERNS.md`
3. ✅ Added examples for SSH environment variable handling

---

### 🔴 Incident #2: Docker Images Not Found (CRITICAL)

**What happened:**
```
Error response from daemon: No such image: copilotos-api:a576ebb-20251011-014736
```

**Root cause:**
- Used `./scripts/deploy.sh tar --skip-build --force`
- `--skip-build` flag assumes images exist with versioned tags
- Server only had images tagged as `latest` from previous build
- Script attempted to export non-existent versioned images
- Result: Empty tar files (4.0K each) transferred to server

**Impact:** Medium
- Automated deployment completely failed
- Manual cleanup required
- ~15 minutes troubleshooting time

**Why this is critical:**
This was the PRIMARY deployment failure. The versioning system expected:
- Local images: `copilotos-api:a576ebb-20251011-014736`
- Actual images: `copilotos-api:latest`

The mismatch meant tar export step silently failed, creating empty archives.

**Resolution:**
- Verified existing containers still healthy
- Since only scripts/docs changed (no app code), kept existing deployment
- Manual cleanup: `docker compose -p infra down`

**Improvements implemented:**
1. ✅ **Pre-flight validation** in `deploy.sh`:
   ```bash
   # Validates images exist if --skip-build is used
   if [ "$SKIP_BUILD" = true ]; then
       if ! docker image inspect "copilotos-api:$NEW_VERSION" >/dev/null 2>&1; then
           log_error "Image not found: copilotos-api:$NEW_VERSION"
           exit 1
       fi
   fi
   ```

2. ✅ **Created `deploy-on-server.sh`** for in-place deployments:
   - Runs directly on production server
   - Does `git pull` + `docker compose build` in-place
   - No image versioning mismatch
   - No tar transfer overhead

3. ✅ **Dry-run mode** (`--dry-run` flag):
   - Validates ALL steps before executing
   - Checks image availability
   - Detects COMPOSE_PROJECT_NAME
   - Shows deployment plan

---

### 🟡 Incident #3: Port Binding Conflicts

**What happened:**
```
Error: Bind for 0.0.0.0:6380 failed: port is already allocated
```

**Root cause:**
- Deploy script defaulted to project name "infra" (directory name)
- Existing containers use project name "copilotos-prod" (from `.env.prod`)
- Two sets of containers tried to bind same ports:
  - Existing: `copilotos-prod-redis` on port 6380
  - New: `infra-redis` also trying port 6380

**Impact:** Low
- Failed containers created with "infra-" prefix
- Cleanup required: `docker compose -p infra down`
- Existing "copilotos-prod-*" containers unaffected

**Resolution:**
```bash
# Removed failed containers
docker compose -p infra down

# Existing containers continued running
docker ps --filter "name=copilotos-prod"
# All 4 containers: healthy, Up 34 hours
```

**Improvements implemented:**
1. ✅ **Auto-detect existing COMPOSE_PROJECT_NAME**:
   ```bash
   # Extract project name from running containers
   local running_containers=$(ssh "$DEPLOY_SERVER" \
       "docker ps --filter 'name=copilotos' --format '{{.Names}}' | head -1")

   # Example: copilotos-prod-web -> copilotos-prod
   local detected_project=$(echo "$running_containers" | sed 's/-[^-]*$//')

   # Validate matches configured name
   if [ "$COMPOSE_PROJECT_NAME" != "$detected_project" ]; then
       log_warning "COMPOSE_PROJECT_NAME mismatch!"
       log_warning "This may cause port conflicts"
   fi
   ```

2. ✅ **Port availability check** in pre-flight validation:
   - Checks ports 3000, 8001, 6379, 27017 before deployment
   - Warns if ports already in use

---

### 🟢 Incident #4: MongoDB Authentication During Verification

**What happened:**
```
MongoServerError: Authentication failed.
```

**Root cause:**
- Attempted direct MongoDB connection using credentials from wrong env file
- Used local `.env` credentials instead of production credentials

**Impact:** Very low
- Only affected post-deployment verification
- Application was unaffected (uses correct credentials from Docker env)

**Resolution:**
Used health check API endpoint instead:
```bash
curl -s http://localhost:8001/api/health | jq .
# ✅ Confirmed: status: "healthy", database: connected, latency: 2.16ms
```

**Improvements implemented:**
1. ✅ Documentation emphasizes using health check API
2. ✅ Pre-flight validation uses API instead of direct DB access

---

## Data Verification

Post-deployment verification confirmed **zero data loss**:

### Database Integrity
```
Users:           5
Chat Sessions:   20
Messages:        36
History Events:  36
```

### User Data Sample
```json
{
  "username": "jaziel",
  "email": "jf2@saptiva.com",
  "sessions": 14,
  "chat_titles": [
    "Cuento mágico nocturno",
    "Empresa tecnológica fabricante de dis...",
    "Saptiva plataforma digital",
    "async await explicación",
    "Servidor definición función",
    ...
  ]
}
```

### System Health
```
API:      healthy (2.16ms latency)
Web:      HTTP 200 (19ms response)
Database: connected, 5 users accessible
Uptime:   34 hours (containers never restarted)
```

## Root Cause Analysis

### Primary Cause
**Incompatible deployment workflow**: The consolidated `deploy.sh` script assumed a "build local → export → transfer" workflow that was incompatible with the existing server setup. Specifically:

1. Script expected versioned images to exist locally
2. Used `--skip-build` but images weren't built with version tags
3. Attempted to export/transfer non-existent images
4. Created port conflicts due to project name mismatch

### Contributing Factors
1. **SSH environment handling**: Lack of understanding about SSH environment variable propagation
2. **No pre-flight validation**: Script didn't validate prerequisites before execution
3. **No dry-run capability**: Couldn't test deployment plan without executing it
4. **Legacy compatibility**: New versioning system incompatible with existing setup

## Lessons Learned

### What Went Well ✅
1. **Zero downtime**: Existing containers kept running throughout issues
2. **Zero data loss**: Backup created successfully, all data verified intact
3. **Graceful degradation**: System remained operational despite deployment failures
4. **Quick rollback decision**: Recognized existing setup was stable, left it running
5. **Comprehensive verification**: Checked users, chats, messages, health endpoints

### What Could Be Improved ⚠️
1. **Pre-deployment validation**: Need automated checks before execution
2. **Dry-run capability**: Test deployment without actually executing
3. **Environment variable handling**: Better patterns for SSH execution
4. **Documentation**: SSH patterns and deployment workflows needed docs
5. **Alternative deployment path**: Need in-place server deployment option

## Improvements Implemented

### ✅ Immediate (Completed 2025-10-11)

1. **Pre-flight Validation in deploy.sh** (`scripts/deploy.sh:209-323`)
   - ✅ Validates images exist if --skip-build used
   - ✅ Auto-detects COMPOSE_PROJECT_NAME from running containers
   - ✅ Checks deployment path exists on server
   - ✅ Validates docker-compose.yml present
   - ✅ Verifies registry configuration for registry deployments
   - ✅ Checks port availability

2. **Dry-run Mode** (`scripts/deploy.sh:120-122, 756-786`)
   - ✅ `--dry-run` flag added
   - ✅ Runs all validations without executing
   - ✅ Shows deployment plan
   - ✅ Lists steps that would be executed

   Usage:
   ```bash
   ./scripts/deploy.sh --dry-run
   # Output:
   # ✔ All pre-flight checks passed
   # ✔ Dry-run complete - all validations passed!
   #
   # Deployment plan:
   #   Version:  a576ebb-20251011-020534
   #   Method:   tar
   #   Steps:
   #     1. Backup current deployment
   #     2. Build Docker images
   #     3. Deploy via tar method
   #     ...
   ```

3. **Deploy On Server Script** (`scripts/deploy-on-server.sh`)
   - ✅ Runs directly on production server
   - ✅ Does git pull + docker compose build in-place
   - ✅ No image versioning issues
   - ✅ Respects existing COMPOSE_PROJECT_NAME
   - ✅ Includes backup and rollback

   Usage:
   ```bash
   ssh user@server 'cd /opt/copilotos-bridge && ./scripts/deploy-on-server.sh'
   ```

4. **Environment File Support** (`scripts/backup-mongodb.sh`)
   - ✅ Added `--env-file` flag
   - ✅ Loads credentials from file
   - ✅ Safer than inline credential passing

   Usage:
   ```bash
   ssh user@server "cd /path && ./scripts/backup-mongodb.sh --env-file envs/.env.prod"
   ```

5. **SSH Environment Patterns Documentation** (`docs/SSH_ENVIRONMENT_PATTERNS.md`)
   - ✅ Explains why SSH env vars don't work as expected
   - ✅ 4 different solution patterns with pros/cons
   - ✅ Real-world examples from this deployment
   - ✅ Security considerations
   - ✅ Testing patterns

### 📋 Recommended (Next Deployment)

1. **Server-side deployment workflow**
   - Prefer `deploy-on-server.sh` for production deployments
   - Use `deploy.sh registry` for registry-based deployments only
   - Keep `deploy.sh tar` for air-gapped or special cases

2. **Always run dry-run first**
   ```bash
   # On local machine
   ./scripts/deploy.sh --dry-run

   # If passes, then execute
   ./scripts/deploy.sh
   ```

3. **Use --env-file consistently**
   ```bash
   # MongoDB backup
   ssh user@server "./scripts/backup-mongodb.sh --env-file envs/.env.prod"

   # Other scripts - update to support --env-file
   ```

4. **Deployment checklist**
   - [ ] Run dry-run mode locally
   - [ ] Create pre-deployment backup
   - [ ] Verify backup integrity
   - [ ] Check disk space on server
   - [ ] Review git changes to deploy
   - [ ] Choose appropriate deployment method
   - [ ] Verify health checks after deployment

## Prevention Measures

### Technical Controls
1. ✅ Pre-flight validation catches issues before execution
2. ✅ Dry-run mode allows risk-free testing
3. ✅ Alternative deployment path for different scenarios
4. ✅ Better error messages and guidance

### Process Controls
1. 📋 Document preferred deployment method for production
2. 📋 Create deployment runbook with decision tree
3. 📋 Add pre-deployment checklist to PR template
4. 📋 Schedule dry-run as part of CI/CD

### Documentation
1. ✅ SSH environment variable patterns documented
2. ✅ Post-mortem created with lessons learned
3. 📋 Update main README with deployment section
4. 📋 Create video walkthrough of deployment process

## Recommendations

### For Next Deployment

**Recommended Approach:**
```bash
# 1. Run dry-run first
./scripts/deploy.sh --dry-run

# 2. Create backup
ssh user@server "cd /path && ./scripts/backup-mongodb.sh --env-file envs/.env.prod"

# 3. Deploy on server (preferred method)
ssh user@server "cd /path && ./scripts/deploy-on-server.sh"

# 4. Verify
make deploy-status
```

**Alternative (Registry-based):**
```bash
# 1. Build and push images
make push-registry

# 2. Deploy from registry
ssh user@server "cd /path && docker compose pull && docker compose up -d"
```

### For Emergency Rollback

If deployment fails:
```bash
# Automatic rollback is built-in to deploy-on-server.sh

# Manual rollback if needed:
ssh user@server "
  cd /path/infra
  docker compose down
  docker tag copilotos-api:backup-TIMESTAMP copilotos-api:latest
  docker tag copilotos-web:backup-TIMESTAMP copilotos-web:latest
  docker compose up -d
"
```

## Success Metrics

### This Deployment
- ✅ Zero data loss
- ✅ Zero downtime
- ✅ Zero users affected
- ✅ All improvements implemented within 2 hours
- ✅ Comprehensive documentation created
- ✅ Future deployments will be safer

### Goals for Future Deployments
- ⏱️ Reduce deployment time to <10 minutes
- 🎯 100% pre-flight check pass rate
- 📊 Automated health verification
- 🔄 One-command deployment with rollback

## References

- **Code Changes**: See git commits from 2025-10-11
- **Scripts Updated**:
  - `scripts/deploy.sh`
  - `scripts/deploy-on-server.sh`
  - `scripts/backup-mongodb.sh`
- **Documentation Created**:
  - `docs/SSH_ENVIRONMENT_PATTERNS.md`
  - `docs/POST-MORTEM-DEPLOYMENT-2025-10-11.md`
- **Related Post-mortems**:
  - `docs/POST-MORTEM-DATA-LOSS-2025-10-09.md`

## Sign-off

**Incident Handler:** Claude Code (AI Assistant)
**Reviewed By:** Jaziel Flores
**Date:** 2025-10-11
**Status:** ✅ Resolved, improvements implemented

---

*This post-mortem follows the blameless post-mortem format. The goal is to learn and improve, not to assign fault.*
