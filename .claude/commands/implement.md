---
name: implement
description: Implement a task phase from plan.md (Phase N only).
argument-hint: "<TASK-ID>__<slug> [--phase N]"
allowed-tools: [Read, Grep, Glob, Bash]
---

Implement only Phase N from `plan.md`. Do not expand scope.

## Inputs
- Task folder: `docs/kanban/DOING/TASK-...__slug/`
- Optional `--phase N` (default: 1)
- `KANBAN_ROOT` (optional): defaults to `docs/kanban`

## Steps
1. Locate task folder and read `card.md` + `plan.md`.
2. Implement only the tasks listed under Phase N and its file list.
3. If scope change is needed:
   - Create a BACKLOG task and stop:
     ```bash
     .claude/scripts/kanban_task.sh ensure BACKLOG TASK-YYYY-MM-DD-HHMM short-slug
     ```
   - Do not change current plan or scope.
4. Update `card.md` with a short change summary and `pr_files` list.

## Delegation Policy

Do not invoke subagents for implementation. The main agent executes the phase directly.
