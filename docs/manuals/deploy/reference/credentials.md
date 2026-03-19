# Credential & Secrets Operations

This guide centralises the safe handling of production credentials, combining the earlier credential management playbook, the rotation checklist, and the Makefile helper reference.

---

## Environment Layout

```
envs/
--- .env                  # Development (ignored in git)
--- .env.local            # Local dev overrides (ignored)
--- .env.local.example    # Template for new developers
--- .env.prod             # Production secrets (ignored)
--- .env.prod.example     # Template without secrets
```

Key rules:

- Duplicate values between dev and prod only when absolutely required.
- Production secrets must never leave the server or secure vault.
- Generate secrets with `make generate-credentials` instead of manual typing.
- Sync `.env.prod` with operations runbooks whenever entries change.

---

## Rotation Workflow (MongoDB, Redis, JWT)

1. **Prepare**
   - Run `make security-audit` and ensure backups are updated.
   - Notify stakeholders of maintenance window.
   - Have new credentials ready (use the generator described below).
2. **Update Secrets**
   - Edit `envs/.env.prod` with new values.
   - If using secrets manager, update entries there first.
3. **Rotate Service Passwords**
   ```bash
   make rotate-mongo-password   # prompts for old/new values
   make rotate-redis-password   # if applicable
   ```
   Scripts update the database users without dropping data.
4. **Restart Safely**
   ```bash
   docker compose down api
   docker compose up -d api
   ```
   > Never rely on `docker compose restart` - it does **not** reload env vars.
5. **Validate**
   ```bash
   make deploy-status
   ssh <user>@<host> "docker logs --tail 50 copilotos-api"
   ```
   Confirm authentication succeeds and the app can connect to MongoDB/Redis.
6. **Document**
   - Record rotation date and operator.
   - Store revoked credentials securely for audit (if policy requires).

---

## Makefile Helpers

| Command | Purpose |
|---------|---------|
| `make generate-credentials` | Outputs 32-char DB password + 64-char JWT secret. |
| `make rotate-mongo-password` | Interactive rotation without data loss. |
| `make rotate-redis-password` | Same flow for Redis (if enabled). |

Example output:

```
Secure Credential Generator
MongoDB/Redis Password (32 chars):
gpo2lTwR3JRoZn3Bk8O2kpt25LoVDcl9

JWT Secret Key (64 chars):
nbOGCY9CEaS6XZoCvJ6WqecjsvswiSO6oXp0LZnd/AxIsAASXHPCxD/wcLxUBuiEBlRlDUFjSBCsv2hDmGLjZQ==
```

---

## Pitfalls to Avoid

- **Restarting containers instead of recreating them**  
  Always use `down` + `up -d` so new env vars are loaded. `restart` keeps old values.

- **Deleting volumes to "reset" credentials**  
  This wipes production data. Use the rotation scripts, never `make reset` in prod.

- **Leaving legacy `env_file` entries**  
  Ensure compose files reference the correct environment file for the target stack.

- **Committing secrets**  
  `.env.prod` and any outputs containing secrets must stay off git. Rotate immediately if leakage is suspected.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `pymongo.errors.OperationFailure: Authentication failed` | Containers using old Mongo credentials | Recreate container with new env vars; verify rotation script finished successfully. |
| `redis.exceptions.AuthenticationError` | Redis password not rotated in server | Run the Redis rotation helper and redeploy service. |
| App works locally but not in prod | `.env.prod` out of sync or missing new keys | Compare against `.env.prod.example`, update, redeploy. |
| Accidentally ran rotation with wrong password | Mongo user now has unknown password | Restore from most recent backup and re-run rotation carefully. |

When in doubt, pair this guide with the incident reports under `operations/incidents/` to see how previous credential mistakes were mitigated.

