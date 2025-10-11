# DISASTER RECOVERY PROCEDURES

**Last Updated:** 2025-10-09  
**Version:** 1.0  
**Status:** PRODUCTION READY  

---

## 📋 OVERVIEW

This document provides comprehensive disaster recovery procedures for the Copilotos Bridge application. It was created in response to the data loss incident documented in [`POST-MORTEM-DATA-LOSS-2025-10-09.md`](POST-MORTEM-DATA-LOSS-2025-10-09.md).

**Purpose:** Enable rapid recovery from data loss, system failures, or corruption incidents with minimal downtime.

**Target Audience:** DevOps engineers, system administrators, and on-call personnel.

---

## 🚨 INCIDENT RESPONSE WORKFLOW

### Quick Decision Tree

```
Data Loss Incident Detected
    ↓
Is production data affected?
    ├─ YES → Follow CRITICAL RECOVERY (Priority 0)
    └─ NO  → Follow STANDARD RECOVERY (Priority 1)
        ↓
Do you have a recent backup?
    ├─ YES → Proceed to RESTORE PROCEDURES
    └─ NO  → Escalate to senior engineering + notify stakeholders
```

### Priority Levels

| Priority | Response Time | Description |
|----------|---------------|-------------|
| **P0** | < 15 minutes | Production data loss, service down |
| **P1** | < 1 hour | Partial data loss, degraded service |
| **P2** | < 4 hours | Development/staging issues |
| **P3** | < 24 hours | Pre-emptive recovery, testing |

---

## 🔧 PREREQUISITES

### Required Access
- [ ] SSH access to production server
- [ ] Docker host access (sudo privileges)
- [ ] Production `.env.prod` file with credentials
- [ ] Backup directory access (`~/backups/mongodb` and `~/backups/docker-volumes`)

### Required Tools
- [ ] Docker and Docker Compose installed
- [ ] `mongodump` and `mongorestore` available (via container)
- [ ] Backup scripts from `scripts/` directory
- [ ] This disaster recovery document

### Verification Commands
```bash
# Verify SSH access
ssh production-server "echo 'Access OK'"

# Verify Docker is running
docker ps

# Verify backup directory exists
ls -lh ~/backups/mongodb/

# Source production environment
source envs/.env.prod
echo "MongoDB Password: ${MONGODB_PASSWORD:0:4}***"
```

---

## 📦 BACKUP PROCEDURES

### Automated Backups (Recommended)

**Schedule:**
- MongoDB backups: Every 6 hours
- Docker volume backups: Daily at 2 AM
- Backup monitoring: Every 15 minutes

**Setup Instructions:**

1. **Configure cron jobs:**
```bash
# Edit crontab
crontab -e

# Add these entries:
# MongoDB backup every 6 hours
0 */6 * * * source ~/copilotos-bridge/envs/.env.prod && ~/copilotos-bridge/scripts/backup-mongodb.sh >> ~/backups/mongodb/cron.log 2>&1

# Docker volumes backup daily at 2 AM
0 2 * * * source ~/copilotos-bridge/envs/.env.prod && ~/copilotos-bridge/scripts/backup-docker-volumes.sh >> ~/backups/docker-volumes/cron.log 2>&1

# Backup health monitoring every 15 minutes
*/15 * * * * ~/copilotos-bridge/scripts/monitor-backups.sh >> ~/backups/mongodb/monitor.log 2>&1
```

2. **Verify cron jobs are running:**
```bash
# List cron jobs
crontab -l

# Check recent cron execution
grep CRON /var/log/syslog | tail -20

# Verify backups exist
ls -lht ~/backups/mongodb/ | head -5
```

### Manual Backups

#### MongoDB Backup (Recommended before deployments)

```bash
# Navigate to project directory
cd ~/copilotos-bridge

# Source environment variables
source envs/.env.prod

# Run backup
./scripts/backup-mongodb.sh

# Verify backup was created
ls -lht ~/backups/mongodb/ | head -1
```

**Expected Output:**
```
✓ MongoDB Backup Completed Successfully
📦 File:      copilotos_20251009_143022.gz
📊 Size:      15M
📁 Location:  /home/jf/backups/mongodb
```

#### Docker Volumes Backup

```bash
# Backup all Docker volumes
./scripts/backup-docker-volumes.sh

# Backup specific volumes
./scripts/backup-docker-volumes.sh --volumes "copilotos-prod_mongodb_data,copilotos-prod_redis_data"

# Verify backup
ls -lht ~/backups/docker-volumes/ | head -5
```

---

## 🔄 RESTORE PROCEDURES

### MongoDB Restore (Complete Database Recovery)

**CRITICAL:** This procedure will overwrite the current database!

#### Step 1: Verify Backup Integrity

```bash
# List available backups
ls -lht ~/backups/mongodb/*.gz | head -10

# Check backup size (should be > 1MB typically)
ls -lh ~/backups/mongodb/copilotos_20251009_143022.gz

# Optional: Extract backup info
gunzip -l ~/backups/mongodb/copilotos_20251009_143022.gz
```

#### Step 2: Stop Application (Prevent Write Conflicts)

```bash
# Stop API containers
cd ~/copilotos-bridge/infra
docker compose down api web

# Verify containers are stopped
docker ps | grep copilotos
```

#### Step 3: Restore Database

```bash
# Source environment
cd ~/copilotos-bridge
source envs/.env.prod

# Restore with DROP (removes existing data)
./scripts/restore-mongodb.sh \
    --backup-file ~/backups/mongodb/copilotos_20251009_143022.gz \
    --drop

# Confirm when prompted by typing: yes
```

**Expected Output:**
```
✓ Database restored successfully!
Collections restored: 8

Next steps:
  1. Verify data: make db-collections
  2. Test application functionality
  3. Check logs: docker logs copilotos-prod-mongodb
```

#### Step 4: Verify Restore

```bash
# Check database collections
docker exec copilotos-prod-mongodb mongosh \
    mongodb://copilotos_user:${MONGODB_PASSWORD}@localhost:27017/copilotos?authSource=admin \
    --eval "db.getCollectionNames()"

# Count documents in key collections
docker exec copilotos-prod-mongodb mongosh \
    mongodb://copilotos_user:${MONGODB_PASSWORD}@localhost:27017/copilotos?authSource=admin \
    --eval "db.users.countDocuments(); db.chat_sessions.countDocuments(); db.chat_messages.countDocuments()"
```

#### Step 5: Restart Application

```bash
cd ~/copilotos-bridge/infra
docker compose up -d

# Wait for services to be healthy
sleep 30

# Verify health
curl http://localhost:8001/api/health | jq
```

### Docker Volume Restore

**Use Case:** Restore raw volume data (alternative to mongorestore)

```bash
# CRITICAL: This deletes the volume and recreates it!

# 1. Stop containers using the volume
docker compose down

# 2. Remove existing volume
docker volume rm copilotos-prod_mongodb_data

# 3. Create new empty volume
docker volume create copilotos-prod_mongodb_data

# 4. Extract backup into volume
docker run --rm \
    -v copilotos-prod_mongodb_data:/data \
    -v ~/backups/docker-volumes:/backup \
    alpine \
    tar xzf /backup/copilotos-prod_mongodb_data_20251009_143022.tar.gz -C /data

# 5. Restart containers
docker compose up -d
```

---

## 🧪 TESTING DISASTER RECOVERY

**IMPORTANT:** Test disaster recovery procedures in a non-production environment first!

### Quarterly DR Testing Schedule

**Test Scenarios:**
1. **Q1:** Complete MongoDB restore from backup
2. **Q2:** Docker volume restore
3. **Q3:** Backup integrity verification
4. **Q4:** Full disaster recovery drill (simulated production failure)

### Test Procedure (Development Environment)

```bash
# 1. Create test backup
make dev
make db-backup

# 2. Populate with test data
make create-demo-user

# 3. Simulate data loss
docker volume rm copilotos_mongodb_data

# 4. Attempt restore
./scripts/restore-mongodb.sh --backup-file backups/mongodb-XXXXX.archive

# 5. Verify data integrity
make list-users  # Should show demo user
```

### Recovery Time Objectives (RTO)

| Scenario | Target RTO | Actual RTO (tested) |
|----------|------------|---------------------|
| MongoDB restore (< 1GB) | 15 minutes | ⏱ _Test pending_ |
| MongoDB restore (1-10GB) | 30 minutes | ⏱ _Test pending_ |
| Docker volume restore | 20 minutes | ⏱ _Test pending_ |
| Full system recovery | 45 minutes | ⏱ _Test pending_ |

### Recovery Point Objectives (RPO)

| Data Type | Target RPO | Current RPO |
|-----------|------------|-------------|
| User data | 6 hours | 6 hours (backup every 6h) |
| Chat sessions | 6 hours | 6 hours |
| Research tasks | 6 hours | 6 hours |

**Action Item:** Test and document actual recovery times during next DR drill.

---

## ⚠️ COMMON FAILURE SCENARIOS

### Scenario 1: Accidental `docker compose down -v`

**Symptoms:**
- MongoDB container starts with empty database
- All users, sessions, and messages are missing
- No authentication works

**Recovery:**
```bash
# 1. Immediately stop containers
docker compose down

# 2. Do NOT run any up commands yet
# 3. Find most recent backup
ls -lht ~/backups/mongodb/ | head -3

# 4. Restore from backup (follow MongoDB Restore procedure above)
./scripts/restore-mongodb.sh --backup-file ~/backups/mongodb/[LATEST].gz --drop

# 5. Restart services
docker compose up -d
```

**Prevention:**
- Never use `docker compose down -v` without a recent backup
- Use `make docker-cleanup` instead (safer)
- Alias dangerous commands to require confirmation

### Scenario 2: Corrupted Database Files

**Symptoms:**
- MongoDB fails to start
- Logs show "WiredTiger error" or "corrupt data"
- Cannot connect to database

**Recovery:**
```bash
# 1. Stop MongoDB
docker compose down mongodb

# 2. Backup corrupted volume (for forensics)
docker run --rm \
    -v copilotos-prod_mongodb_data:/data:ro \
    -v ~/backups/forensics:/backup \
    alpine \
    tar czf /backup/corrupted_$(date +%s).tar.gz -C /data .

# 3. Remove corrupted volume
docker volume rm copilotos-prod_mongodb_data

# 4. Restore from backup (follow procedure above)

# 5. Restart MongoDB
docker compose up -d mongodb
```

### Scenario 3: Backup Files Missing or Empty

**Symptoms:**
- Backup directory exists but files are < 1KB
- No backups in last 24 hours
- Cron jobs not running

**Immediate Actions:**
```bash
# 1. Create immediate manual backup (if data still exists)
./scripts/backup-mongodb.sh

# 2. Check cron status
systemctl status cron
crontab -l

# 3. Check backup logs
tail -100 ~/backups/mongodb/cron.log

# 4. Verify MongoDB container is running
docker ps | grep mongodb

# 5. Test backup script manually
./scripts/backup-mongodb.sh --help
```

### Scenario 4: Multiple Containers Using Wrong Images

**Symptoms:**
- Services restart but use development mode
- Old code is running after deployment
- Environment variables not loading

**Recovery:**
```bash
# 1. Verify current images
docker images | grep copilotos

# 2. Check which images containers are using
docker ps --format "{{.Names}}: {{.Image}}"

# 3. Redeploy with correct images
cd ~/copilotos-bridge
make deploy-clean

# 4. Verify deployment
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
```

---

## 📊 MONITORING & ALERTS

### Backup Health Monitoring

```bash
# Manual health check
./scripts/monitor-backups.sh

# Check backup age
find ~/backups/mongodb -name "*.gz" -mmin -360 -ls

# View backup log
tail -50 ~/backups/mongodb/backup.log
```

### Alert Configuration

**Email Alerts (Optional):**
```bash
# Install mail utilities
sudo apt-get install mailutils

# Test email alerts
echo "Test alert" | mail -s "Backup Test" admin@example.com

# Configure backup monitoring with email
./scripts/monitor-backups.sh --alert-email admin@example.com
```

**Slack/Discord Webhooks (Advanced):**
```bash
# Add to monitor-backups.sh
WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

send_alert() {
    curl -X POST "$WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "{\"text\": \"🚨 BACKUP ALERT: $1\"}"
}
```

### Key Metrics to Monitor

1. **Backup Freshness:** Last backup < 6 hours old
2. **Backup Size:** Not suspiciously small (> 1MB typically)
3. **Backup Success Rate:** > 95% success rate
4. **Disk Space:** Backup directory has sufficient space (> 10GB free)

---

## 🔐 SECURITY CONSIDERATIONS

### Backup Encryption (Recommended for Production)

```bash
# Encrypt backup after creation
gpg --symmetric --cipher-algo AES256 \
    ~/backups/mongodb/copilotos_20251009_143022.gz

# Decrypt before restore
gpg --decrypt \
    ~/backups/mongodb/copilotos_20251009_143022.gz.gpg \
    > /tmp/backup.gz
```

### Access Control

- **Backup Directory:** Readable only by backup user and administrators
- **MongoDB Credentials:** Stored in `.env.prod`, never committed to git
- **Backup Passwords:** Rotated quarterly, stored in password manager

### Audit Trail

All disaster recovery operations should be logged:

```bash
# Log recovery operations
echo "$(date): DR restore initiated by $(whoami)" >> ~/backups/audit.log
```

---

## 📞 EMERGENCY CONTACTS

### Escalation Path

1. **On-Call Engineer** (Primary)
   - Response time: < 15 minutes
   - Authority: Execute all DR procedures

2. **Senior DevOps** (Secondary)
   - Response time: < 1 hour
   - Authority: Approve data loss decisions

3. **CTO/Engineering Director** (Final)
   - Response time: < 4 hours
   - Authority: Business continuity decisions

### Communication Channels

- **Incident Channel:** `#incidents` (Slack/Discord)
- **Status Page:** https://status.yourcompany.com
- **Escalation Email:** devops-oncall@company.com

---

## 📝 POST-RECOVERY CHECKLIST

After completing disaster recovery:

- [ ] Verify all services are healthy
- [ ] Test key user flows (login, chat, research)
- [ ] Review logs for errors
- [ ] Document incident in post-mortem
- [ ] Create fresh backup post-recovery
- [ ] Update monitoring dashboards
- [ ] Notify stakeholders of resolution
- [ ] Schedule post-incident review meeting
- [ ] Update disaster recovery procedures if gaps found

---

## 🔗 RELATED DOCUMENTATION

- [`POST-MORTEM-DATA-LOSS-2025-10-09.md`](POST-MORTEM-DATA-LOSS-2025-10-09.md) - Incident that motivated this document
- [`PRODUCTION_DEPLOYMENT.md`](PRODUCTION_DEPLOYMENT.md) - Deployment procedures
- [`README.md`](../README.md) - Project overview and quick start
- `scripts/backup-mongodb.sh` - Backup script implementation
- `scripts/restore-mongodb.sh` - Restore script implementation
- `scripts/monitor-backups.sh` - Backup monitoring implementation

---

## 📅 MAINTENANCE SCHEDULE

| Task | Frequency | Owner | Last Completed |
|------|-----------|-------|----------------|
| Test backup restore | Quarterly | DevOps | ⏱ _Pending_ |
| Update DR procedures | Bi-annually | DevOps | 2025-10-09 |
| Rotate backup credentials | Quarterly | SecOps | ⏱ _Pending_ |
| Review backup retention | Monthly | DevOps | ⏱ _Pending_ |
| DR drill with full team | Annually | All | ⏱ _Pending_ |

---

## ✍️ DOCUMENT HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-09 | Claude AI | Initial creation based on post-mortem |

---

**REMEMBER:** The best disaster recovery plan is the one you've tested!

**Next Actions:**
1. Schedule first quarterly DR drill
2. Set up automated backups in production
3. Test backup/restore procedures in staging
4. Document actual recovery times during testing

---

*This document is a living document. Update it after every disaster recovery incident or drill.*
