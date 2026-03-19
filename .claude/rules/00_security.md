# Security Rules

When this applies: always (global).

Do:
- Follow the denylist in `.claude/settings.json` before reading files.
- Redact secrets in outputs and logs.

Don't:
- Read or print `.env*`, credentials, tokens, or private keys.
- Commit secrets or sample prod IPs.

Commands:
- `git diff --cached | grep -E "(API_KEY|password|secret)"`

Refs:
- `@CLAUDE.md`
