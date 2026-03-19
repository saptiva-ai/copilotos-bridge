# Secrets Management Playbook

## Credential Rotation

**Policy**: Rotate production credentials every 90 days or upon suspected compromise.

### MongoDB
**Script**: `scripts/database/rotate-mongo-credentials.sh`

```bash
# Rotate root and user passwords
./scripts/database/rotate-mongo-credentials.sh
```

### Redis
**Script**: `scripts/database/rotate-redis-credentials.sh`

```bash
# Update Redis password and config
./scripts/database/rotate-redis-credentials.sh
```

## Git Secrets Hook

**Setup**:
Ensure `pre-commit` is installed and configured.

```bash
# Install hooks
pre-commit install

# Run manual check
./scripts/security/git-secrets-check.sh
```

## Secret Detection Rules

Forbidden patterns (examples):
- AWS Access Keys
- GitHub Personal Access Tokens
- Third-party API keys (Stripe, OpenAI, etc.)
- RSA/OpenSSL Private Key headers

## Handling Leaks

1. **Revoke**: Invalidate the leaked key at the provider.
2. **Rotate**: Generate new key and update `.env.prod`.
3. **Clean**: Remove key from git history (BFG Repo-Cleaner) if committed.
4. **Deploy**: Restart services with new credentials.
