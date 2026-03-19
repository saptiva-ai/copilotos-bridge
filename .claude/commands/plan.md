---
name: plan
description: Create or update a task plan in docs/kanban.
argument-hint: "<TASK-ID> <slug> [notes]"
allowed-tools: [Read, Grep, Glob, EnterPlanMode, ExitPlanMode, TodoWrite, Bash]
---

Create an implementation plan in the task folder before coding.

## Inputs
- `TASK-ID`: `TASK-YYYY-MM-DD-HHMM`
- `slug`: short kebab-case
- `KANBAN_ROOT` (optional): defaults to `docs/kanban`

## Steps
1. Ensure task folder exists:
   ```bash
   task_dir=$(.claude/scripts/kanban_task.sh ensure DOING "$TASK_ID" "$slug")
   ```
2. Update `card.md` (status, phase, scope in/out, artifacts).
3. Write `plan.md` with required format:
   - Objective
   - Scope (In/Out)
   - Phases with per-phase file lists
   - Validation commands
   - Success criteria
4. No code changes in this phase.

## Delegation Policy

Do not invoke subagents for planning. The main agent writes `plan.md` directly in the task folder.
