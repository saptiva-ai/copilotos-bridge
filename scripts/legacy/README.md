# Legacy Scripts

These scripts have been moved here because they contain hardcoded sensitive values (IPs, usernames, paths) and/or are superseded by the consolidated deployment system.

## Archived Scripts

### manual-deploy-prod.sh
**Status**: Superseded
**Reason**: Contains hardcoded IP (34.42.214.246) and username (jf)
**Replacement**: Use `scripts/deploy.sh` with consolidated deployment system

### README-DEPLOY.md
**Status**: Outdated
**Reason**: Contains hardcoded production values and outdated instructions
**Replacement**: See `docs/VERSIONED_DEPLOYMENT.md` for current deployment documentation

## Migration Guide

If you were using these scripts, please migrate to the new consolidated system:

### Old Command → New Command

```bash
# Old manual deployment
./scripts/manual-deploy-prod.sh
↓
# New versioned deployment with rollback
make deploy
```

### Configuration Required

Configure your production environment in `envs/.env.prod`:

```bash
PROD_SERVER_HOST=user@server-ip
PROD_DEPLOY_PATH=/opt/copilotos-bridge
REGISTRY_URL=ghcr.io/username/repo
REGISTRY_USER=username
```

## Benefits of New System

- ✅ No hardcoded values
- ✅ Automatic versioning (git SHA + timestamp)
- ✅ Pre-deployment backup
- ✅ Health check validation
- ✅ Automatic rollback on failure
- ✅ Deployment history tracking
- ✅ Multiple deployment methods (tar, registry, local)

## Documentation

- **Deployment Guide**: `docs/VERSIONED_DEPLOYMENT.md`
- **Getting Started**: `docs/GETTING_STARTED.md`
- **Production Deployment**: `docs/PRODUCTION_DEPLOYMENT.md`
