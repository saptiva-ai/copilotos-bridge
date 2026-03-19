# Maintenance Playbook

## Disk Space Management

**Problem**: Large images and old logs consuming disk.

### Pruning Docker
```bash
# Clean unused images, containers, and networks (safe)
ssh $DEPLOY_SERVER "docker system prune -f"

# Aggressive clean (removes all unused images, not just dangling ones)
ssh $DEPLOY_SERVER "docker system prune -a --filter 'until=72h' -f"
```

## Logs Management

### Monitoring Logs
```bash
# Real-time tail
ssh $DEPLOY_SERVER "cd $DEPLOY_PROJECT_DIR && docker compose logs -f --tail 100"

# Check for specific errors
ssh $DEPLOY_SERVER "cd $DEPLOY_PROJECT_DIR && docker compose logs | grep -i 'error'"
```

## Service Health

### Monitoring Endpoints
- **Web**: `https://invex.saptiva.com`
- **API Health**: `https://back-invex.saptiva.com/api/health`
- **Prometheus Metrics**: `https://back-invex.saptiva.com/api/metrics`

### Restarting Services
```bash
# Simple restart (retains config)
ssh $DEPLOY_SERVER "cd $DEPLOY_PROJECT_DIR && docker compose restart <service>"

# Full recreation (reloads environment variables)
ssh $DEPLOY_SERVER "cd $DEPLOY_PROJECT_DIR && \
    docker compose stop <service> && \
    docker compose rm -f <service> && \
    docker compose up -d <service>"
```

