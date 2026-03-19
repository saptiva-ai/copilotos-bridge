# Rollback Procedure

Use this checklist if a deployment fails and you need to revert to the previous state immediately.

## 1. Stop Services

```bash
docker compose -f infra/docker-compose.yml down
```

## 2. Revert Image Versions

Edit `infra/docker-compose.images.yml` to point to the previous working tags.

Example:
```yaml
services:
  backend:
    image: saptivaai/octavios-invex-backend:1.3.7  # Old version
  web:
    image: saptivaai/octavios-invex-web:1.3.5      # Old version
  bank-advisor:
    image: saptivaai/octavios-invex-bank-advisor:1.3.3-rag-fix
```

## 3. Restart Services

```bash
docker compose \
    -f infra/docker-compose.yml \
    -f infra/docker-compose.images.yml \
    -f infra/docker-compose.production.yml \
    --env-file envs/.env \
    up -d
```

## 4. Restore Database (If Corrupted)

**Only do this if the data is actually corrupted.**

```bash
# 1. Extract backup
tar xzf backups/mongodb-backup-pre-deployment.tar.gz

# 2. Copy to container
docker cp backups/mongodb-backup-pre-deployment \
    octavios-chat-bajaware_invex-mongodb:/tmp/

# 3. Restore
docker exec octavios-chat-bajaware_invex-mongodb mongorestore \
    --username="${MONGODB_USER}" \
    --password="${MONGODB_PASS}" \
    --authenticationDatabase=admin \
    --drop \
    /tmp/mongodb-backup-pre-deployment
```

## 5. Verify Stability

- [ ] Check logs: `docker compose logs -f --tail=100`
- [ ] Verify frontend load.
- [ ] Notify team of rollback.

```