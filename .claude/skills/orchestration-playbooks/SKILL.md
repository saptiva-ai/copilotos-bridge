---
name: orchestration-playbooks
description: Standard orchestration flow (explore -> plan -> code -> test -> review -> docs), exit codes, and slash commands. Use when needing workflow guidance or understanding agent delegation. (project)
allowed-tools: [Read, Grep, Glob, Task, TodoWrite]
---

# Orchestration Playbooks

> Single-tier agent architecture with skill-based routing.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION SKILL                          │
│                  (routing logic, shared context)                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
     ┌─────────────────────┼─────────────────────────┐
     ▼                     ▼                         ▼
┌─────────────┐     ┌─────────────┐          ┌─────────────┐
│  STRATEGIC  │     │   TACTICAL  │          │ OPERATIONAL │
│   (sonnet)  │     │   (sonnet)  │          │   (haiku)   │
└──────┬──────┘     └──────┬──────┘          └──────┬──────┘
       │                   │                        │
   ┌───┴───┐           ┌───┴───┐               ┌───┴───┐
   ▼       ▼           ▼       ▼               ▼       ▼
┌─────┐ ┌─────┐    ┌─────┐ ┌─────┐        ┌─────┐ ┌─────┐
│prd- │ │plan-│    │soft-│ │code-│        │test-│ │dev- │
│arch │ │arch │    │dev  │ │rev  │        │run  │ │val  │
└─────┘ └─────┘    └─────┘ └─────┘        └─────┘ └─────┘
                   ┌─────┐                ┌─────┐ ┌─────┐
                   │doc- │                │infra│ │repo-│
                   │sync │                │doc  │ │scout│
                   └─────┘                └─────┘ └─────┘
```

## Standard Flow

```
PRD → Explore → Plan → Code → Test → Review → Docs
 │       │        │      │      │       │       │
 └─prd-  └─repo-  └─plan-└─soft-└─test- └─code- └─doc-
  arch    scout   arch    dev    runner reviewer sync
```

| Phase | Skill/Command | Agent |
|-------|---------------|-------|
| 0. PRD | `prd-builder` skill | `prd-architect` |
| 1. Explore | `explore` skill, `/repo-map` | `repo-scout` |
| 2. Plan | `plan` skill, EnterPlanMode | `plan-architect` |
| 3. Code | `code` skill (TDD + SOLID) | `software-developer` |
| 4. Test | `/quick-checks`, `make test` | `test-runner` |
| 5. Review | `review` skill | `code-reviewer` |
| 6. Docs | `docs` skill | `doc-sync` |

## Quick Navigation

| Need | File |
|------|------|
| Which agent for what | `delegation-matrix.md` |
| Complete workflow details | `workflow.md` |
| Exit code meanings | `exit-codes.md` |

## Exit Codes

- `0` success
- `1` tests failed
- `2` infra or preflight failure

## Slash Commands

Core: `/repo-map`, `/quick-checks`, `/dev-up`, `/infra-doctor`
Test: `/api-test`, `/web-test`, `/e2e`
Workflow: `/do`, `/dev-loop`

## Agent Hygiene

- Active agents in `.claude/agents/` only
- Unused agents go to `.claude/agents_parking/`
- See `.claude/rules/60_agent_hygiene.md`

## References

- `.claude/rules/50_orchestration.md`
- `.claude/rules/60_agent_hygiene.md`
