---
name: explore
description: Explore the codebase efficiently using search patterns and navigation strategies. Use PROACTIVELY when starting any task that requires understanding project structure. (project)
allowed-tools: [Read, Grep, Glob, LSP, Bash]
---

# Explore Codebase Skill

> Navigate and understand project structure before acting.

## Exploration Flow

```
┌─────────────────┐
│   Start Here    │  What are you looking for?
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│ File  │ │ Code  │
│Pattern│ │Content│
└───┬───┘ └───┬───┘
    │         │
    ▼         ▼
  Glob      Grep
    │         │
    └────┬────┘
         ▼
┌─────────────────┐
│      Read       │  Examine specific files
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│      LSP        │  Go to definition, find refs
└─────────────────┘
```

## Quick Reference

### Search Priority

1. `src/` - Main source code
2. `tests/` - Usage examples
3. `config/` - Constants
4. `docs/` - Documentation

### Tool Selection

| Need | Tool | Example |
|------|------|---------|
| Find file by name | `Glob` | `**/*Service*.py` |
| Find code pattern | `Grep` | `class.*Service` |
| Read specific file | `Read` | Full file content |
| Trace definition | `LSP` | Go to definition |

### Search Limits

- Max **3 rounds** of Glob/Grep before asking user
- If file has **>500 lines**, read only relevant sections
- If not found in 3 attempts, **ask user**

## Reference Files

| File | Content |
|------|---------|
| `patterns.md` | Common search patterns by layer |
| `entrypoints.md` | Key files per service |

## Quick Searches

```bash
# Find service
Grep "class.*Service" apps/backend/src/services/

# Find endpoint
Grep "@router" apps/backend/src/routers/

# Find component
Glob "**/*ComponentName*.tsx" apps/web/src/

# Find test
Grep "def test_" apps/backend/tests/
```
