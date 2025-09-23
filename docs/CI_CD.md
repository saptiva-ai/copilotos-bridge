# CI/CD Pipeline

## Overview

Our CI/CD pipeline is streamlined for fast, reliable deployments with automatic rollback capabilities.

## Pipeline Stages

### 1. **Continuous Integration (CI)**
- **Trigger**: Push to `develop` or `main` branches
- **Duration**: ~5 minutes
- **Services**: MongoDB + Redis test instances
- **Steps**:
  - Install dependencies with `pnpm`
  - Quality checks (lint, compile)
  - Build shared package + web app
  - Minimal test suite (expandable)

### 2. **Production Deployment**
- **Target**: Production server (34.42.214.246)
- **Duration**: ~5 minutes
- **Features**:
  - Automatic backup before deployment
  - Docker Compose build with cache invalidation
  - Health checks (API + Web)
  - Automatic rollback on failure
  - Cleanup of old backups

## Key Improvements (September 2025)

### Simplified Docker Architecture
- **Removed**: Legacy Docker configurations (`infra/docker/`, multiple compose variants)
- **Kept**: Single `docker-compose.yml` for all environments
- **Added**: Proper environment variable handling

### Enhanced CI Process
- **Fixed**: `pnpm` support (was using `npm`)
- **Updated**: Modern `docker compose` commands (vs legacy `docker-compose`)
- **Added**: Shared package building step
- **Improved**: Health check reliability

### Production Readiness
- **Auto .env**: Creates environment file if missing
- **Rollback**: Automatic rollback on health check failure
- **Monitoring**: Better status reporting and error handling

## Manual Deployment

For emergency deployments or testing:

```bash
# Trigger deployment manually
gh workflow run "🚀 Copilot OS Production Pipeline" --ref develop

# Skip tests for emergency
gh workflow run "🚀 Copilot OS Production Pipeline" --ref develop -f skip_tests=true
```

## Environment Variables

The pipeline automatically creates a `.env` file on the server if missing, with secure defaults:

- **Database**: MongoDB with authentication
- **Cache**: Redis with password
- **Security**: JWT secrets (should be customized)
- **APIs**: External service URLs

## Health Checks

Deployment succeeds only if:
- **API**: Returns HTTP 200 on `/api/health`
- **Web**: Returns HTTP 200 or 307 (redirect) on root

## Rollback Strategy

On failure:
1. **Detect**: Health checks fail after deployment
2. **Restore**: Previous working version from backup
3. **Restart**: Services with known-good configuration
4. **Alert**: Exit with error code for notification

## Security Notes

- SSH key-based authentication
- Secure environment variable handling
- No secrets in repository (use GitHub Secrets)
- Automatic cleanup of sensitive backups
