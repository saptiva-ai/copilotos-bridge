# Infrastructure

This directory contains infrastructure-related configurations.

## Docker Compose

El archivo canónico `infra/docker-compose.yml` proporciona una configuración lista para desarrollo, testing y despliegues productivos con perfiles:

- **MongoDB**: Database with authentication
- **Redis**: Cache and session storage
- **API**: FastAPI backend with health checks
- **Web**: Next.js frontend
- **NGINX (profile `production`)**: reverse proxy y TLS
- **Playwright (profile `testing`)**: entorno para E2E

## Development

For development, use:

```bash
# Start all services
docker compose -f infra/docker-compose.yml up -d

# Check status
docker compose -f infra/docker-compose.yml ps

# View logs
docker compose -f infra/docker-compose.yml logs -f api web
```

## Additional Configurations

Additional Docker Compose configurations for specific environments can be found in:

- `docs/setup/docker-compose.staging.yml` - Staging environment blueprint
- `docs/setup/docker-compose.fast.yml` - Fast development setup

## Clean Architecture

We maintain a clean, minimal approach:
- Single `infra/docker-compose.yml` for the main use case
- Specific variants only when necessary (activated vía perfiles u overrides)
- Documentation-based configurations in `docs/setup/`
