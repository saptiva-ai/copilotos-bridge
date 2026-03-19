# Orchestration Rules

When this applies: always (global) for Claude Code runs.

Do:
- Follow the flow: Explore → Plan → Code → Test → Review → Docs.
- Prefer leaf slash commands (`/repo-map`, `/dev-up`, `/quick-checks`, `/infra-doctor`).
- Use Task subagents for scoped work (repo-scout, test-runner, code-reviewer).

Don't:
- Create recursive orchestration loops (command calling itself).
- Skip docs updates when workflows change.

Commands:
- `/repo-map`
- `/quick-checks`
- `/infra-doctor`

Refs:
- `.claude/skills/orchestration-playbooks/SKILL.md`
- `.claude/rules/60_agent_hygiene.md`
