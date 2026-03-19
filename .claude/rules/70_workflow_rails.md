# Workflow Rails

Applies to all tasks in this repo.

## File Creation Policy
- Default deny: no docs outside `docs/kanban/**`
- Task folder files: `card.md`, `research.md`, `plan.md`, `validate.md` (max 4)
- Refactors require own BACKLOG task
- Exceptions: approved in plan, linked in `card.md`

## Phase Protocol
1. Research: no code. Edit `research.md`, `card.md` only
2. Plan: no code. Edit `plan.md`, `card.md` only
3. Implement: only Phase N from `plan.md`
4. Validate: run commands, write `validate.md`, close task

## Subagent Policy
- All subagents parked by default (in `.claude/agents_parking/`)
- Only `repo-scout` allowed, only during Research, only writes `research.md`
- `/plan`, `/implement`, `/review`, `/validate` are main-agent only
- Subagent output outside task `research.md` = regression
- Reactivation: move from parking + update this file

## Context Budget
- If `/context` > ~60%: use `/clear`
- Reload: task docs + repo map (`.claude/docs/repo_map.md`)
