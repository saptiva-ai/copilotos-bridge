# Compliance Playbook

## Policy Reference

**Source of Truth**: `.claude/security_policy.md`

## Enforcement Checklist

### 1. Access Control
- [ ] No hardcoded passwords in code.
- [ ] Production access restricted to authorized SSH keys.
- [ ] Least Privilege: Database users have minimal necessary scopes.

### 2. Network Security
- [ ] Database ports (27017, 5432) NOT exposed publicly (use Docker internal network).
- [ ] SSH (22) restricted by IP allowlist where possible.
- [ ] TLS enabled for all web endpoints (Nginx).

### 3. Data Protection
- [ ] PII encryption at rest (if applicable).
- [ ] Backups encrypted or stored in secure buckets.
- [ ] Logs do not contain sensitive user data (sanitize logs).

### 4. Code Review
- [ ] Security review required for Auth module changes.
- [ ] Dependencies pinned to specific versions (lockfiles).
