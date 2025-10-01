# Scripts Directory

This directory contains utility scripts for development, deployment, testing, and troubleshooting.

## Quick Reference

### 🚀 Most Useful Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `quick-diagnostic.sh` | Quick system health check | `./scripts/quick-diagnostic.sh` or `make diag` |
| `dev-troubleshoot.sh` | Fix common development issues | `./scripts/dev-troubleshoot.sh [issue-type]` |
| `migrate-conversation-timestamps.py` | Database migration tool | `make db-migrate` |

## Development Scripts

### `quick-diagnostic.sh`
**Purpose:** Comprehensive system health check
**Usage:** `./scripts/quick-diagnostic.sh` or `make diag`

Checks:
- Container status (API, Web, MongoDB, Redis)
- Service health endpoints
- Volume mounts and file synchronization
- Database collections
- Recent errors in logs
- Environment variables
- Port availability

**When to use:** First thing when something isn't working, or before reporting an issue.

### `dev-troubleshoot.sh`
**Purpose:** Automated fixes for common development issues
**Usage:** `./scripts/dev-troubleshoot.sh [option]`

Available options:
- `ports` - Fix port conflicts (3000, 8001, 27018, 6380)
- `cache` - Clear all caches (Docker, Next.js, Python)
- `permissions` - Fix file permission issues
- `volumes` - Fix volume mount issues
- `rebuild` - Full rebuild with clean slate
- `database` - Fix MongoDB connection issues
- `redis` - Fix Redis connection issues
- `all` - Run all fixes (nuclear option)

**Examples:**
```bash
./scripts/dev-troubleshoot.sh cache
./scripts/dev-troubleshoot.sh ports
./scripts/dev-troubleshoot.sh all
```

## Database Scripts

### `migrate-conversation-timestamps.py`
**Purpose:** Migrate conversation timestamps from messages
**Usage:** `make db-migrate`

Populates `first_message_at` and `last_message_at` fields for existing conversations by querying their messages.

### `migrate-ready-to-active.py`
**Purpose:** Migrate conversations from old 'ready' state to 'active'
**Usage:** `python scripts/migrate-ready-to-active.py [--dry-run]`

Fixes breaking change from old state model (ready/active) to new Progressive Commitment model (draft/active/creating/error). All 'ready' conversations with messages are migrated to 'active'.

### `fix-orphaned-drafts.py`
**Purpose:** Fix conversations stuck in DRAFT state
**Usage:** `make db-fix-drafts`

Transitions non-empty DRAFT conversations to ACTIVE state.

### `cleanup-duplicate-drafts.py`
**Purpose:** Remove duplicate draft conversations
**Usage:** Run directly in API container

### `apply-draft-unique-index.py`
**Purpose:** Apply unique index for one draft per user
**Usage:** Run once during setup

### `apply-email-unique-index.py`
**Purpose:** Apply unique email index for users
**Usage:** Run once during setup

## User Management

### `create-demo-user.py`
**Purpose:** Create demo user for testing
**Usage:** `make create-demo-user`

Creates user with credentials:
- Username: `demo`
- Password: `Demo1234`
- Email: `demo@example.com`

### `fix_demo_user.py`
**Purpose:** Fix/reset demo user if corrupted
**Usage:** Run directly in API container

## Testing Scripts

### `test-mongodb.py`
**Purpose:** Test MongoDB connection and basic operations
**Usage:** Run in API container

### `test-auth-and-chat.py`
**Purpose:** Integration test for authentication and chat
**Usage:** Run in API container

### `test-auth-logging.py`
**Purpose:** Test improved MongoDB authentication error logging
**Usage:** `docker exec infra-api python /app/test-auth-logging.py`

Simulates authentication failure to verify enhanced error logging shows detailed connection info, troubleshooting hints, and specific error detection.

### `test-all-models.py`
**Purpose:** Test all Saptiva model endpoints
**Usage:** Run in API container

### `test_integration.py`
**Purpose:** Complete integration test suite
**Usage:** Run in API container

### `test-saptiva-connection.sh`
**Purpose:** Test external Saptiva API connection
**Usage:** `./scripts/test-saptiva-connection.sh`

### `test-error-handling.sh`
**Purpose:** Test API error handling
**Usage:** `./scripts/test-error-handling.sh`

## Deployment Scripts

### `push-to-registry.sh`
**Purpose:** Build and push Docker images to registry
**Usage:** `make push-registry` or `./scripts/push-to-registry.sh`

Options:
- `--no-build` - Push existing images without rebuilding

### `deploy-from-registry.sh`
**Purpose:** Deploy from Docker registry (run on production server)
**Usage:** `make deploy-registry` or `./scripts/deploy-from-registry.sh`

### `deploy-prod.sh`
**Purpose:** Complete production deployment workflow
**Usage:** `./scripts/deploy-prod.sh`

### `deploy-local.sh`
**Purpose:** Local deployment testing
**Usage:** `./scripts/deploy-local.sh`

### `deploy-staging.sh`
**Purpose:** Deploy to staging environment
**Usage:** `./scripts/deploy-staging.sh`

## Setup Scripts

### `setup.sh`
**Purpose:** Initial project setup
**Usage:** `./scripts/setup.sh`

Sets up:
- Environment files
- Dependencies
- Initial configuration

### `setup-dev.sh`
**Purpose:** Development environment setup
**Usage:** `./scripts/setup-dev.sh`

### `setup-docker-secrets.sh`
**Purpose:** Configure Docker secrets for production
**Usage:** `./scripts/setup-docker-secrets.sh`

### `env-manager.sh`
**Purpose:** Manage environment variables
**Usage:** `./scripts/env-manager.sh`

## Verification Scripts

### `verify-deployment.sh`
**Purpose:** Verify deployment health and functionality
**Usage:** `make verify` or `./scripts/verify-deployment.sh`

Checks:
- All services are running
- Health endpoints
- Authentication
- Database connectivity

### `validate-setup.sh`
**Purpose:** Validate initial setup
**Usage:** `./scripts/validate-setup.sh`

### `health-check.sh`
**Purpose:** Basic health check
**Usage:** `./scripts/health-check.sh`

### `prod-health-check.sh`
**Purpose:** Production-specific health check
**Usage:** `./scripts/prod-health-check.sh`

## Security Scripts

### `security-audit.sh`
**Purpose:** Comprehensive security audit
**Usage:** `make security` or `./scripts/security-audit.sh`

### `security-audit-focused.sh`
**Purpose:** Focused security scan
**Usage:** `./scripts/security-audit-focused.sh`

### `security-audit-precise.sh`
**Purpose:** Precise security analysis
**Usage:** `./scripts/security-audit-precise.sh`

### `generate-secrets.py`
**Purpose:** Generate secure random secrets
**Usage:** `python scripts/generate-secrets.py`

### `export-passwords.py`
**Purpose:** Export encrypted passwords
**Usage:** `python scripts/export-passwords.py`

## Utility Scripts

### `fix-docker-permissions.sh`
**Purpose:** Fix Docker-related permission issues
**Usage:** `./scripts/fix-docker-permissions.sh`

### `test-docker-permissions.sh`
**Purpose:** Test Docker permissions
**Usage:** `./scripts/test-docker-permissions.sh`

### `run-tests.sh`
**Purpose:** Run test suite
**Usage:** `./scripts/run-tests.sh`

### `build-frontend.sh`
**Purpose:** Build frontend only
**Usage:** `./scripts/build-frontend.sh`

## Common Workflows

### Something Isn't Working
```bash
# 1. Run quick diagnostic
make diag

# 2. Check logs
make logs

# 3. Try clearing caches
./scripts/dev-troubleshoot.sh cache
make dev

# 4. If still broken, full diagnostic
make debug-full

# 5. Nuclear option
./scripts/dev-troubleshoot.sh all
```

### After Pulling New Code
```bash
# 1. Check if containers need rebuilding
make debug-file-sync

# 2. If files differ, restart (volume mount) or rebuild
make restart  # if using volume mounts
# OR
make rebuild-api  # if not using volume mounts

# 3. Run any new migrations
make db-migrate
```

### Before Deploying to Production
```bash
# 1. Run security audit
make security

# 2. Run all tests
make test

# 3. Verify local deployment
./scripts/verify-deployment.sh

# 4. Push to registry
make push-registry

# 5. Deploy on server
# (SSH to server)
make deploy-registry
```

### Database Issues
```bash
# 1. Check database status
make db-stats
make db-collections

# 2. Backup before making changes
make db-backup

# 3. Fix specific issues
make db-fix-drafts  # Fix orphaned drafts

# 4. Run migrations
make db-migrate

# 5. If needed, restore from backup
make db-restore
```

### Redis Issues
```bash
# 1. Check Redis stats
make redis-stats

# 2. Clear cache
make clear-cache

# 3. Monitor commands
make redis-monitor

# 4. Fix connection
./scripts/dev-troubleshoot.sh redis
```

## Best Practices

1. **Always run diagnostics first**: `make diag` gives you a quick overview
2. **Backup before migrations**: `make db-backup` before `make db-migrate`
3. **Check file sync**: After pulling code, run `make debug-file-sync`
4. **Use volume mounts in dev**: Faster iteration, no rebuild needed
5. **Clear caches when stuck**: `./scripts/dev-troubleshoot.sh cache`
6. **Check logs for errors**: `make debug-logs-errors` or `make logs`

## Adding New Scripts

When adding a new script:

1. Make it executable: `chmod +x scripts/your-script.sh`
2. Add usage comments at the top
3. Use consistent exit codes (0 = success, 1 = error)
4. Add color output for better UX (use existing scripts as template)
5. Consider adding a Makefile target for convenience
6. Update this README

## Script Naming Conventions

- `*.sh` - Shell scripts
- `*.py` - Python scripts (usually need to run in container)
- `test-*.sh` - Testing scripts
- `deploy-*.sh` - Deployment scripts
- `fix-*.py` - Database/data fixing scripts
- `*-audit.sh` - Security/analysis scripts

## Environment Variables

Scripts respect these environment variables:

- `COMPOSE_PROJECT_NAME` - Docker Compose project name (default: `copilotos`)
- `MONGODB_URL` - MongoDB connection string
- `REDIS_URL` - Redis connection string
- `SAPTIVA_API_KEY` - Saptiva API key

## Troubleshooting Scripts

If a script fails:

1. Check if services are running: `make status`
2. Check if environment is configured: `cat envs/.env`
3. Run with bash debug: `bash -x scripts/your-script.sh`
4. Check script permissions: `ls -l scripts/your-script.sh`
5. For Python scripts, ensure dependencies are installed in container

## Getting Help

- `make help` - Show all Makefile commands
- `make troubleshoot` - Show troubleshooting options
- `./scripts/dev-troubleshoot.sh help` - Troubleshooting script help
- Individual scripts usually support `--help` or `-h` flags
