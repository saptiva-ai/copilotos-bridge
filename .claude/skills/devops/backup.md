# Backup & Recovery Playbook

## MongoDB Backup

**Script**: `scripts/database/backup-mongodb.sh`

### Usage
```bash
# Basic backup (defaults to ~/backups/mongodb)
./scripts/database/backup-mongodb.sh --env-file envs/.env.prod

# Custom retention and directory
./scripts/database/backup-mongodb.sh --retention-days 7 --backup-dir /mnt/backups/mongo
```

### Recovery
```bash
# Restore a specific file
./scripts/database/restore-mongodb.sh --backup-file ~/backups/mongodb/octavios_YYYYMMDD_HHMMSS.gz
```

## PostgreSQL Backup (Bank Advisor)

**Procedure**: Manual ssh command (standardized in `deploy-service.sh`).

### Usage
```bash
ssh $DEPLOY_SERVER "cd $DEPLOY_PROJECT_DIR && \
    mkdir -p backups && \
    docker exec postgres pg_dump -U octavios -d bankadvisor \
    --no-owner --no-acl | gzip > backups/pg_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
```

## Environment Backup

**Procedure**: Manual copy before sync.

### Usage
```bash
ssh $DEPLOY_SERVER "cp $DEPLOY_PROJECT_DIR/envs/.env.prod $DEPLOY_PROJECT_DIR/envs/.env.prod.backup-$(date +%Y%m%d-%H%M%S)"
```

## Critical Notes
- **Retention**: Default is 30 days for MongoDB.
- **Verification**: Always check backup file size (`stat -c%s`) to ensure it's not empty.
- **Encryption**: Backups are GZIPped but not currently encrypted at rest.
