# Data Migration Playbook

## Database Initialization

**Script**: `scripts/database/init-bankadvisor-db.sh`

Usage:
```bash
# Initialize fresh DB structure
./scripts/database/init-bankadvisor-db.sh
```

## Schema Evolution

### MongoDB (Beanie)
Beanie handles most schema changes automatically via model definitions. For data transformations:

```bash
# Example: Migrate timestamps
python scripts/database/migrate-conversation-timestamps.py
```

### PostgreSQL (Bank Advisor)
SQL migrations are stored in `plugins/bank-advisor-private/migrations/`.

## Migration Checklist

1. **Backup**: ALWAYS run `backup-mongodb.sh` or PG dump before migrating.
2. **Dry Run**: If script supports it, verify logic without writing.
3. **Execution**: Run migration script.
4. **Validation**: Verify data integrity post-migration.

## Rollback Strategy

If a migration fails:
1. Restore from Backup (see `devops/backup.md`).
2. Analyze logs.
3. Fix script and retry.
