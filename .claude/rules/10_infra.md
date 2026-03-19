---
paths:
  - infra/**
  - scripts/**
  - .claude/**
  - envs/**
---

# Infra Rules

When this applies: editing infra/scripts/claude tooling/environment.

## Critical: Docker Compose with Environment Variables

**ALWAYS** use `--env-file envs/.env` when running docker-compose commands:

```bash
# Correct (variables interpolate properly)
docker compose -f infra/docker-compose.yml --env-file envs/.env up -d

# WRONG (variables like $MONGODB_USER become empty strings)
docker compose -f infra/docker-compose.yml up -d
```

> **Why:** The `env_file:` directive in compose only passes variables TO containers.
> It does NOT interpolate `$VAR` references in the compose file itself.

## Do:
- Use `infra/docker-compose.yml` as the compose entrypoint.
- **ALWAYS** include `--env-file envs/.env` in compose commands.
- Use `infra/docker-compose.dev.yml` overlay for development (hot reload).
- Treat logical `api` as compose service `backend`.
- Use docker label filters for health checks.
- Ensure `TIDEWAVE_ENABLED=true` is in .env for MCP support.

## Don't:
- Run `docker compose up` WITHOUT `--env-file envs/.env`.
- Assume a compose service named `api` exists.
- Change compose file names without updating docs and scripts.
- Configure Tidewave MCP manually in `.mcp.json` (use `claude mcp add`).

## Commands:

### Development (with hot reload)
```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml \
  --env-file envs/.env up -d
```

### Production
```bash
docker compose -f infra/docker-compose.yml --env-file envs/.env up -d
```

### Service inspection
```bash
docker compose -f infra/docker-compose.yml config --services
docker ps -q --filter "label=com.docker.compose.service=backend" \
  --filter "label=com.docker.compose.project=octavios-chat-bajaware_invex"
docker compose -f infra/docker-compose.yml logs --tail=200 backend
```

### MCP Setup (Tidewave)
```bash
claude mcp add --transport http tidewave http://localhost:8000/tidewave/mcp
claude mcp list
```

## Refs:
- `docs/manuals/dev/mcp_debugging.md`
- `scripts/testing/test-runner.sh`
- `.claude/skills/test/SKILL.md`
