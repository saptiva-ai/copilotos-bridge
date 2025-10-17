# BACKUP SETUP GUIDE

**Last Updated:** 2025-10-09  
**Version:** 1.0  
**Status:** PRODUCTION READY  
**Related:** [`DISASTER-RECOVERY.md`](DISASTER-RECOVERY.md) | [`POST-MORTEM-DATA-LOSS-2025-10-09.md`](POST-MORTEM-DATA-LOSS-2025-10-09.md)

---

## 📋 OVERVIEW

This guide provides step-by-step instructions for setting up automated backups for the Copilotos Bridge application. Automated backups are **CRITICAL** for data safety and disaster recovery.

**What This Sets Up:**
- MongoDB database backups every 6 hours
- Docker volume backups daily at 2 AM
- Backup health monitoring every 15 minutes
- 30-day backup retention policy
- Automatic cleanup of old backups

---

## ⚡ QUICK START (5 MINUTES)

### On Production Server

```bash
# 1. Navigate to project directory
cd ~/copilotos-bridge

# 2. Source production environment
source envs/.env.prod

# 3. Create backup directories
mkdir -p ~/backups/mongodb
mkdir -p ~/backups/docker-volumes

# 4. Install cron jobs
crontab -e
```

**Add these lines to crontab:**
```cron
# MongoDB backup every 6 hours
0 */6 * * * source ~/copilotos-bridge/envs/.env.prod && ~/copilotos-bridge/scripts/backup-mongodb.sh >> ~/backups/mongodb/cron.log 2>&1

# Docker volumes backup daily at 2 AM
0 2 * * * source ~/copilotos-bridge/envs/.env.prod && ~/copilotos-bridge/scripts/backup-docker-volumes.sh >> ~/backups/docker-volumes/cron.log 2>&1

# Backup health monitoring every 15 minutes
*/15 * * * * ~/copilotos-bridge/scripts/monitor-backups.sh >> ~/backups/mongodb/monitor.log 2>&1
```

**Save and exit** (`:wq` in vim, or `Ctrl+X, Y, Enter` in nano)

```bash
# 5. Verify cron jobs are installed
crontab -l

# 6. Run first manual backup to test
cd ~/copilotos-bridge
make backup-mongodb-prod

# 7. Verify backup was created
ls -lht ~/backups/mongodb/ | head -3
```

**Expected Output:**
```
✓ MongoDB Backup Completed Successfully
📦 File:      copilotos_20251009_143022.gz
📊 Size:      15M
📁 Location:  /home/jf/backups/mongodb
```

---

## 📂 DIRECTORY STRUCTURE

```
~/backups/
├── mongodb/
│   ├── copilotos_20251009_140000.gz    # Backup from 2 PM
│   ├── copilotos_20251009_080000.gz    # Backup from 8 AM
│   ├── copilotos_20251009_020000.gz    # Backup from 2 AM
│   ├── backup.log                      # Backup execution log
│   ├── monitor.log                     # Monitoring log
│   ├── cron.log                        # Cron execution log
│   └── alerts.log                      # Alert log (if monitoring detects issues)
└── docker-volumes/
    ├── copilotos-prod_mongodb_data_20251009_020000.tar.gz
    ├── copilotos-prod_redis_data_20251009_020000.tar.gz
    ├── backup.log
    └── cron.log
```

---

## 🔧 DETAILED SETUP

### Step 1: Verify Prerequisites

```bash
# Check Docker is running
docker ps

# Check MongoDB container is running
docker ps | grep mongodb

# Verify environment variables are set
echo "MongoDB Password: ${MONGODB_PASSWORD:0:4}***"  # Should show first 4 chars
echo "Project Name: ${COMPOSE_PROJECT_NAME}"

# If variables are empty, source the .env.prod file
source ~/copilotos-bridge/envs/.env.prod
```

### Step 2: Create Backup Directories

```bash
# Create directories with proper permissions
mkdir -p ~/backups/mongodb
mkdir -p ~/backups/docker-volumes
chmod 700 ~/backups  # Only owner can read/write/execute
```

### Step 3: Test Backup Scripts Manually

#### Test MongoDB Backup
```bash
cd ~/copilotos-bridge
source envs/.env.prod

# Run backup
./scripts/backup-mongodb.sh

# Check output
ls -lh ~/backups/mongodb/
cat ~/backups/mongodb/backup.log | tail -5
```

**Expected Output:**
- Backup file created (~10-50MB depending on data size)
- Log entry showing SUCCESS
- No error messages

#### Test Docker Volumes Backup
```bash
./scripts/backup-docker-volumes.sh

# Check output
ls -lh ~/backups/docker-volumes/
```

#### Test Backup Monitoring
```bash
./scripts/monitor-backups.sh

# Should show:
# ✓ Found 1 recent backup(s) (< 6 hours old)
```

### Step 4: Configure Cron Jobs

#### Understanding the Cron Schedule

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday=0)
│ │ │ │ │
│ │ │ │ │
* * * * * command to execute
```

**Examples:**
- `0 */6 * * *` - Every 6 hours (at 00:00, 06:00, 12:00, 18:00)
- `0 2 * * *` - Daily at 2:00 AM
- `*/15 * * * *` - Every 15 minutes

#### Edit Crontab

```bash
# Open crontab editor
crontab -e

# If asked to choose an editor, select nano (easier) or vim
```

#### Add Cron Jobs

**Copy and paste this entire block:**

```cron
# ========================================
# Copilotos Bridge - Automated Backups
# ========================================
# Post-mortem: docs/POST-MORTEM-DATA-LOSS-2025-10-09.md
# Reference: docs/BACKUP-SETUP.md

# MongoDB backup every 6 hours (00:00, 06:00, 12:00, 18:00)
0 */6 * * * source $HOME/copilotos-bridge/envs/.env.prod && $HOME/copilotos-bridge/scripts/backup-mongodb.sh >> $HOME/backups/mongodb/cron.log 2>&1

# Docker volumes backup daily at 2 AM
0 2 * * * source $HOME/copilotos-bridge/envs/.env.prod && $HOME/copilotos-bridge/scripts/backup-docker-volumes.sh >> $HOME/backups/docker-volumes/cron.log 2>&1

# Backup health monitoring every 15 minutes
*/15 * * * * $HOME/copilotos-bridge/scripts/monitor-backups.sh >> $HOME/backups/mongodb/monitor.log 2>&1

# Weekly backup log rotation (Sundays at 1 AM)
0 1 * * 0 find $HOME/backups/mongodb/ -name "*.log" -size +10M -exec mv {} {}.old \; 2>&1
```

**Save and exit:**
- vim: Press `ESC`, then `:wq`, then `Enter`
- nano: Press `Ctrl+X`, then `Y`, then `Enter`

### Step 5: Verify Cron Jobs

```bash
# List installed cron jobs
crontab -l

# Check cron service is running
systemctl status cron  # Ubuntu/Debian
# or
systemctl status crond  # CentOS/RHEL

# View cron execution log
sudo tail -f /var/log/syslog | grep CRON  # Ubuntu/Debian
# or
sudo tail -f /var/log/cron  # CentOS/RHEL
```

### Step 6: Wait and Verify First Automated Backup

```bash
# Wait for next scheduled backup (up to 6 hours for MongoDB)
# Or manually trigger next cron run

# Check if backup was created recently
ls -lht ~/backups/mongodb/ | head -5

# Check cron execution log
tail -50 ~/backups/mongodb/cron.log

# Check for errors
grep -i error ~/backups/mongodb/cron.log
```

**If Backups Are Not Running:**
```bash
# 1. Check cron logs for errors
sudo grep CRON /var/log/syslog | tail -20

# 2. Test script permissions
ls -l ~/copilotos-bridge/scripts/backup-mongodb.sh  # Should be executable (rwxr-xr-x)

# 3. Test script manually
~/copilotos-bridge/scripts/backup-mongodb.sh

# 4. Check environment variables are set
env | grep MONGODB

# 5. Ensure cron can access Docker
docker ps  # Should work for the user running cron
```

---

## 📊 MONITORING & ALERTS

### Manual Backup Health Check

```bash
# Check backup freshness
make monitor-backups

# Or directly:
~/copilotos-bridge/scripts/monitor-backups.sh
```

**Expected Output (Healthy):**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Backup Health Monitor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Found 2 recent backup(s) (< 6 hours old)

Latest backup:
  📦 File:    copilotos_20251009_143022.gz
  📊 Size:    15M
  ⏰ Age:     45 minutes

Backup statistics:
  📊 Total backups: 18
  💾 Total size:    250M

✓ Backup health check passed
```

**Output (CRITICAL - Needs Attention):**
```
✗ CRITICAL: No MongoDB backup found in last 6 hours!

Latest backup: copilotos_20251009_020000.gz
Age: 12 hours ago

Action required:
  1. Check if backup cron job is running
  2. Run manual backup: ./scripts/backup-mongodb.sh
  3. Check backup.log for errors
```

### Email Alerts (Optional)

To receive email alerts when backups fail:

```bash
# 1. Install mailutils
sudo apt-get install mailutils  # Ubuntu/Debian
# or
sudo yum install mailx  # CentOS/RHEL

# 2. Configure monitoring with email
~/copilotos-bridge/scripts/monitor-backups.sh --alert-email admin@example.com

# 3. Update cron job to include email alert
crontab -e

# Change monitoring line to:
*/15 * * * * $HOME/copilotos-bridge/scripts/monitor-backups.sh --alert-email admin@example.com >> $HOME/backups/mongodb/monitor.log 2>&1
```

### Slack/Discord Webhooks (Advanced)

For Slack/Discord alerts, see [`DISASTER-RECOVERY.md`](DISASTER-RECOVERY.md) section "Alert Configuration".

---

## 🗑️ BACKUP RETENTION POLICY

**Default Retention:**
- **MongoDB backups:** 30 days (configurable via `--retention-days`)
- **Docker volume backups:** 30 days
- **Automatic cleanup:** Old backups are deleted when new ones are created

**Modify Retention:**
```bash
# Change retention to 60 days
./scripts/backup-mongodb.sh --retention-days 60

# Update cron job
crontab -e

# Change backup line to:
0 */6 * * * source $HOME/copilotos-bridge/envs/.env.prod && $HOME/copilotos-bridge/scripts/backup-mongodb.sh --retention-days 60 >> $HOME/backups/mongodb/cron.log 2>&1
```

**Storage Estimates:**
- Average MongoDB backup: 15-50 MB per backup
- 30 days at 4 backups/day: ~1.8 - 6 GB
- Docker volume backups: Similar size to MongoDB backups
- **Total estimate:** 5-15 GB for 30 days of backups

---

## 🔧 CUSTOMIZATION

### Backup to External Storage

```bash
# Mount external drive
sudo mount /dev/sdb1 /mnt/backups

# Update backup directory
mkdir -p /mnt/backups/mongodb

# Run backup with custom directory
./scripts/backup-mongodb.sh --backup-dir /mnt/backups/mongodb
```

### Backup to Cloud Storage (S3, Google Cloud, etc.)

```bash
# After creating local backup, sync to cloud
# Example with AWS S3:

# Install AWS CLI
sudo apt-get install awscli

# Configure credentials
aws configure

# Add to cron job (after backup completes)
0 */6 * * * source $HOME/copilotos-bridge/envs/.env.prod && $HOME/copilotos-bridge/scripts/backup-mongodb.sh >> $HOME/backups/mongodb/cron.log 2>&1 && aws s3 sync $HOME/backups/mongodb/ s3://your-bucket/copilotos-backups/ --exclude "*.log"
```

---

## ✅ VERIFICATION CHECKLIST

After setup, verify everything is working:

- [ ] Cron jobs are installed (`crontab -l` shows all jobs)
- [ ] Cron service is running (`systemctl status cron`)
- [ ] Backup directories exist with proper permissions
- [ ] Manual backup test succeeded
- [ ] First automated backup was created (wait up to 6 hours)
- [ ] Backup monitoring shows healthy status
- [ ] No errors in cron logs
- [ ] Backups are being cleaned up after 30 days (check after 30 days)
- [ ] Team knows where backups are stored
- [ ] Disaster recovery procedures are documented

---

## 🚨 TROUBLESHOOTING

### Problem: Cron Jobs Not Running

**Solution:**
```bash
# Check cron service
systemctl status cron
sudo systemctl restart cron

# Check user permissions
groups  # Should include docker group

# Test script manually
~/copilotos-bridge/scripts/backup-mongodb.sh

# Check cron logs
sudo tail -100 /var/log/syslog | grep CRON
```

### Problem: Backup Script Fails

**Solution:**
```bash
# Check MongoDB container is running
docker ps | grep mongodb

# Check environment variables
source ~/copilotos-bridge/envs/.env.prod
echo $MONGODB_PASSWORD

# Check permissions
ls -l ~/copilotos-bridge/scripts/backup-mongodb.sh  # Should be executable
chmod +x ~/copilotos-bridge/scripts/backup-mongodb.sh

# Run with debug output
bash -x ~/copilotos-bridge/scripts/backup-mongodb.sh
```

### Problem: Backups Too Large

**Solution:**
```bash
# Check current backup sizes
du -sh ~/backups/mongodb/*

# Compress older backups more aggressively
find ~/backups/mongodb -name "*.gz" -mtime +7 -exec gzip -9 {} \;

# Reduce retention period
./scripts/backup-mongodb.sh --retention-days 15

# Consider off-site backup and local cleanup
```

### Problem: Disk Space Full

**Solution:**
```bash
# Check disk usage
df -h

# Find large backups
du -h ~/backups/ | sort -h | tail -20

# Manually clean old backups
find ~/backups/mongodb -name "*.gz" -mtime +30 -delete

# Move old backups to external storage
mv ~/backups/mongodb/*.gz /mnt/external-drive/
```

---

## 📞 SUPPORT

If you encounter issues with backup setup:

1. **Check Logs:**
   - `~/backups/mongodb/cron.log` - Backup execution
   - `~/backups/mongodb/monitor.log` - Monitoring
   - `/var/log/syslog` or `/var/log/cron` - System cron logs

2. **Review Documentation:**
   - [`DISASTER-RECOVERY.md`](DISASTER-RECOVERY.md) - Full recovery procedures
   - [`POST-MORTEM-DATA-LOSS-2025-10-09.md`](POST-MORTEM-DATA-LOSS-2025-10-09.md) - Context

3. **Escalate:**
   - Contact: devops-oncall@company.com
   - Slack: `#infrastructure` or `#incidents`

---

## 📝 NEXT STEPS

After completing setup:

1. **Test Restore:** Verify you can restore from backup
   ```bash
   # See DISASTER-RECOVERY.md for full procedure
   make restore-mongodb-prod
   ```

2. **Schedule DR Drill:** Test disaster recovery quarterly
   - Q1: MongoDB restore test
   - Q2: Docker volume restore test
   - Q3: Backup integrity verification
   - Q4: Full disaster recovery drill

3. **Update Runbooks:** Document any custom changes to this setup

4. **Train Team:** Ensure team knows how to restore from backups

---

**REMEMBER:** Automated backups are only useful if you can restore from them. Test your restore procedures regularly!

---

*Last Updated: 2025-10-09*  
*Version: 1.0*  
*Maintainer: DevOps Team*
