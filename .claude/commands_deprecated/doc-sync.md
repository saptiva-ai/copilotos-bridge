---
name: doc-sync
description: Synchronize documentation after code changes.
argument-hint: "[EPIC-HUx or --auto]"
allowed-tools: [Read, Write, Edit, Grep, Glob, Bash, Task]
---

Update documentation to reflect code changes.

## Triggers
- After tests pass (feedback loop from test-runner)
- Manual invocation with specific epic
- `--auto`: Detect changes from git diff

## Process
1. Identify code changes (git diff or specified)
2. Map to mini-PRD (EPIC-HUx.md)
3. Update CA status: `- [ ]` → `- [x] ✅ YYYY-MM-DD`
4. Update GAPS.md if gaps resolved
5. Check epic completion (all CAs done → EPIC DONE)
6. Flag stale documentation

## Agent Delegation
```yaml
Agent: doc-sync
Input:
  - $ARGUMENTS or git diff
  - Mini-PRD file
Output: Documentation sync report
```

## Reference
- Status values: `.claude/skills/docs/status-values.md`
- Templates: `.claude/skills/docs/templates.md`
- Checklist: `.claude/skills/docs/checklist.md`

Invoke the `doc-sync` agent to synchronize documentation.
