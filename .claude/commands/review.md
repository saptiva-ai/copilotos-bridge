---
name: review
description: Review code changes vs plan scope (no fixes).
argument-hint: "<TASK-ID>__<slug> [--staged|--commit|--pr]"
allowed-tools: [Read, Grep, Glob, LSP, Bash]
---

Review changes against `plan.md` scope and report issues.

## Modes
- `--staged` (default): Review staged changes
- `--commit`: Review last commit
- `--pr`: Review PR diff against main

## Steps
1. Locate task folder and read `plan.md` + `card.md`.
2. Collect diff based on mode.
3. Flag scope creep if files outside plan phase list are modified.
4. Check correctness, security, and missing tests.
5. Return actionable findings in chat; do not edit files.

## Notes
- `KANBAN_ROOT` can override the default `docs/kanban` root.

## Delegation Policy

Do not invoke subagents for review. The main agent reviews and reports findings directly.
