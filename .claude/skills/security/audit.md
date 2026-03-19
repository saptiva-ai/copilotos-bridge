# Security Audit Playbook

## Automated Scans

**Script**: `scripts/security/security-audit.sh`

### Usage
```bash
# Full audit (Git secrets, permissions, config)
./scripts/security/security-audit.sh

# Focused audit (faster)
./scripts/security/security-audit-focused.sh
```

## Audit Scope

1. **Git Secrets**: Scans commit history for keys/tokens using `git-secrets`.
2. **File Permissions**: Checks for sensitive files (SSH keys, .env) with open permissions.
3. **Configuration**: Validates secure defaults in `docker-compose.yml` and `nginx.conf`.
4. **Dependencies**: (Optional) Checks `pnpm audit` or `uv pip check`.

## Reporting

Audit logs are saved to `docs/security/audit-reports/`.

**Critical Findings**:
- **ACTION REQUIRED**: Rotate compromised credentials immediately.
- **Log Incident**: Create `SECURITY_ALERT.md` if leak is confirmed.
