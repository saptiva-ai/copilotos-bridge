# Web CLAUDE.md

When this applies: working under `apps/web/`.

Entrypoints

- App layout: `apps/web/src/app/layout.tsx`.
- Components: `apps/web/src/components/`.
- Lib/utilities: `apps/web/src/lib/`.

Testing

- `make test T=web` (compose service `web`).
- `cd apps/web && pnpm test` (if running locally).

Lint/Format

- `cd apps/web && pnpm lint`

Refs

- `.claude/skills/code/SKILL.md`
- `.claude/skills/test/SKILL.md`
