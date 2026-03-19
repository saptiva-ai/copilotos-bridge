# DevOps Skill

Infrastructure management, Docker operations, and MCP server configuration.

## When to use
- Setting up or debugging Docker containers
- Configuring MCP servers (Tidewave, Playwright)
- Troubleshooting environment variables
- Managing docker-compose workflows

---

## Quick Reference

### Start Development Stack
```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml \
  --env-file envs/.env up -d
```

### Start Production Stack
```bash
docker compose -f infra/docker-compose.yml --env-file envs/.env up -d
```

### Rebuild Service
```bash
make rebuild-backend
# or
docker compose -f infra/docker-compose.yml --env-file envs/.env build --no-cache backend
```

---

## MCP Configuration

### Add Tidewave MCP
```bash
# CORRECT - Use HTTP transport
claude mcp add --transport http tidewave http://localhost:8000/tidewave/mcp

# WRONG - Do NOT use SSE in .mcp.json for Tidewave
```

### Verify MCP Servers
```bash
claude mcp list
```

### Test Tidewave Endpoint
```bash
curl -X POST http://localhost:8000/tidewave/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"ping"}'
```

---

## Required Environment Variables

These MUST be in `envs/.env`:

```bash
# Tidewave MCP
TIDEWAVE_ENABLED=true
TIDEWAVE_ALLOW_REMOTE_ACCESS=true

# Database (for compose interpolation)
MONGODB_USER=octavios_user
MONGODB_PASSWORD=<password>
MONGODB_DATABASE=octavios
REDIS_PASSWORD=<password>
```

---

## Common Errors & Solutions

| Error | Cause | Fix |
|-------|-------|-----|
| "1 MCP server failed" | SSE config for Tidewave | Use `claude mcp add --transport http` |
| "405 Method Not Allowed" | GET on Tidewave endpoint | Tidewave uses POST only |
| "empty string is not valid username" | Missing `--env-file` | Add `--env-file envs/.env` |
| Backend "Restarting" loop | Env vars or outdated image | Use dev mode or rebuild |

---

## Debug Commands

```bash
# Check container status
docker ps --format "table {{.Names}}\t{{.Status}}"

# View backend logs
docker logs octavios-chat-bajaware_invex-backend 2>&1 | tail -50

# Check env vars in container
docker exec octavios-chat-bajaware_invex-backend env | grep -E "MONGODB|TIDEWAVE"

# Test backend health
curl -s http://localhost:8000/api/health | jq .
```

---

## References

- `docs/manuals/dev/mcp_debugging.md` - MCP troubleshooting guide
- `.claude/rules/10_infra.md` - Infrastructure rules
- `infra/docker-compose.yml` - Main compose file
- `infra/docker-compose.dev.yml` - Development overlay
