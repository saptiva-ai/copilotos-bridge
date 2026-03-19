# Deployment Playbook

## Overview
Standard procedures for deploying services to production. Supports granular (service-by-service) and full releases.

## Core Commands

| Command | Description |
|---------|-------------|
| `./scripts/deploy/load-env.sh prod` | **CRITICAL**: Load production environment variables |
| `./scripts/deploy/sync-env.sh` | **NEW**: Sync local .env.prod with production server (with backup) |
| `./scripts/deploy/validate-deploy.sh <VERSION>` | Validate prerequisites (secrets, images, SSH) |
| `./scripts/deploy/deploy-service.sh "<services>" <VERSION>` | Deploy specific services (e.g., "backend web") |
| `./scripts/deploy/detect-changes.sh` | Identify which services changed since last deploy |
| `make prod.build SVC="<services>"` | Build production images locally |
| `./scripts/deploy/tag-push-service.sh "<services>" <VERSION>` | Tag and push images to Docker Hub |

## Standard Workflow (Granular)

1. **Sync Credentials** (if changed):
   ```bash
   ./scripts/deploy/sync-env.sh
   ```
2. **Detect Changes**:
   ```bash
   CHANGED=$(./scripts/deploy/detect-changes.sh | tail -1)
   ```
2. **Build**:
   ```bash
   make prod.build SVC="$CHANGED"
   ```
3. **Push**:
   ```bash
   ./scripts/deploy/tag-push-service.sh "$CHANGED" <VERSION>
   ```
4. **Deploy**:
   ```bash
   source scripts/deploy/load-env.sh prod
   ./scripts/deploy/deploy-service.sh "$CHANGED" <VERSION>
   ```

## Critical Rules

1. **Environment Loading**: Never run `deploy-service.sh` without sourcing `load-env.sh prod` first.
2. **Validation**: `validate-deploy.sh` must pass (errors = block, warnings = review).
3. **Registry versions**: Versions are managed in `infra/docker-compose.registry.yml`.
4. **Environment Variables**: Use `--env-file` in docker commands if variables contain special characters (avoid `source .env`).
5. **Rollback**: To rollback, redeploy the previous known-good version:
   ```bash
   ./scripts/deploy/deploy-service.sh "backend" 1.2.2
   ```

## Post-Deploy Checks

1. **Health Checks**:
   ```bash
   ssh $DEPLOY_SERVER "cd $DEPLOY_PROJECT_DIR && docker compose ps"
   curl -s https://back-invex.saptiva.com/api/health
   ```
2. **Logs**:
   ```bash
   ssh $DEPLOY_SERVER "cd $DEPLOY_PROJECT_DIR && docker compose logs -f <service>"
   ```
