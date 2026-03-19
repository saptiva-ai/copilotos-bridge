---
name: plan
description: Plan implementations before writing code with proper context and alignment. Use PROACTIVELY before implementing any feature, refactor, or significant code change. (project)
allowed-tools: [Read, Grep, Glob, EnterPlanMode, ExitPlanMode, TodoWrite]
---

# Plan Implementation Skill

> Design solutions before writing code.

## Planning Flow

```
┌─────────────────┐
│   mini-PRD      │  Input from prd-architect
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Read Context   │  BRD, architecture, gaps
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Explore Code    │  Existing patterns, dependencies
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Design Solution │  Files, phases, risks
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  User Approval  │  EnterPlanMode → ExitPlanMode
└────────┬────────┘
         │ approved
         ▼
┌─────────────────┐
│software-devlpr  │  Handoff to implementation
└─────────────────┘
```

## Quick Reference

### Context Documents

| Document | Purpose |
|----------|---------|
| `docs/context/product/EPICS/EPIC-HUx.md` | Mini-PRD with CAs |
| `docs/context/product/BRD.md` | Business requirements |
| `docs/architecture/` | Technical design |
| `docs/context/project/GAPS.md` | Known blockers |
| `docs/context/project/SPRINT_CURRENT.md` | Current sprint |

### Key Questions

Before planning, answer:

1. **What?** Objective in 1 sentence
2. **Where?** Files to create/modify
3. **How?** Test command (`make test`)
4. **Risk?** What can fail
5. **Deps?** Blockers or prerequisites

### Plan Mode

```
EnterPlanMode → Write plan → ExitPlanMode (user approves)
```

## Reference Files

| File | Content |
|------|---------|
| `template.md` | Plan output template |
| `checklist.md` | Pre-planning checklist |

## Handoff to software-developer

After approval:
```yaml
Agent: software-developer
Input:
  - Approved plan
  - mini-PRD file
  - Target files list
```
