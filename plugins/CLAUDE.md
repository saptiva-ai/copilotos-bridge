# Plugins CLAUDE.md

When this applies: working under `plugins/`.

Entrypoints

- File manager: `plugins/public/file-manager/src/main.py`.
- Bank advisor: `plugins/bank-advisor-private/src/main.py`.

Compose services

- `file-manager`, `bank-advisor` (see `infra/docker-compose.yml`).

Testing

- Use repo-level commands (invoke `test` skill).

Refs

- `.claude/skills/explore/SKILL.md`
- `docs/context/BANK_ADVISOR.md`
