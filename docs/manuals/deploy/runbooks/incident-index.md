# Incident & Troubleshooting Index

This table maps common symptoms to their known fixes and runbooks.

| Symptom / Error Message | Likely Cause | Fix / Runbook |
|-------------------------|--------------|---------------|
| `ModuleNotFoundError` in container | Stale volume mount (dev vs prod mismatch) | [Clear Volumes](debugging_guide.md#issue-container-uses-old-code) |
| `Conversación no encontrada` (frontend) | Frontend/Backend sync issue or Redis cache | [Clear Redis](debugging_guide.md#issue-redis-cache-returns-stale-data) |
| "Hallucinated" bank data | Truth-gating disabled or stale model | Check `BUG-09` fix in [v1.4.0 Guide](../procedures/current_v1.4.0.md) |
| `502 Bad Gateway` (Nginx) | Backend container crashed or starting up | [Check Logs](debugging_guide.md#issue-container-wont-start--unhealthy) |
| Container Unhealthy | Missing env vars or dependency fail | [Debug Startup](debugging_guide.md#3-debugging-docker-issues) |
| Password reset email not sent | SMTP config invalid | [Password Config](../checklists/password_config.md) |
| SSH Permission Denied | Wrong key or user permissions | [SSH Access](ssh_access.md) |
| High Memory Usage (>2GB) | Memory leak or unoptimized image | [Resource Optimization](resource_optimization.md) |

## Standard Debugging Steps

1. **Check Status**: `docker compose ps`
2. **Check Logs**: `docker compose logs --tail=100 <service>`
3. **Check Health**: `curl localhost:8000/api/health`
4. **Consult Guide**: [Full Debugging Guide](debugging_guide.md)
