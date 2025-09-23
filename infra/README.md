# Infrastructure

This directory contains infrastructure-related configurations.

## Docker Compose

The main `docker-compose.yml` file in the root directory provides a minimal, production-ready setup with:

- **MongoDB**: Database with authentication
- **Redis**: Cache and session storage
- **API**: FastAPI backend with health checks
- **Web**: Next.js frontend

## Development

For development, use:

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f api web
```

## Additional Configurations

Additional Docker Compose configurations for specific environments can be found in:

- `docs/setup/docker-compose.staging.yml` - Staging environment
- `docs/setup/docker-compose.fast.yml` - Fast development setup
- `docker-compose.prod.yml` - Production with external services

## Clean Architecture

We maintain a clean, minimal approach:
- Single `docker-compose.yml` for main use case
- Specific variants only when necessary
- Documentation-based configurations in `docs/setup/`