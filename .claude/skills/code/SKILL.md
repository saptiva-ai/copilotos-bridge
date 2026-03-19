---
name: code
description: Write code following project conventions, Clean Architecture, and SOLID principles. Use PROACTIVELY when implementing features after plan approval. (project)
allowed-tools: [Read, Write, Edit, Grep, Glob, Bash, LSP]
---

# Code Implementation Skill

> Implement features with Clean Architecture, SOLID principles, and TDD discipline.

## Implementation Flow

```
┌─────────────────┐
│   Approved      │  From plan-architect
│     Plan        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Understand    │  Tidewave, LSP, explore skill
│    Context      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Write Test    │  test_ca{id}_{description}
│    (RED)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Implement     │  Minimal code (GREEN)
│    Code         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Refactor      │  Apply SOLID, stay GREEN
│                 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Guardrails    │  ruff, type-check, tests
└─────────────────┘
```

## Quick Reference

### File Locations

| Type | Location |
|------|----------|
| Backend service | `apps/backend/src/services/` |
| Backend router | `apps/backend/src/routers/` |
| Beanie model | `apps/backend/src/models/` |
| React component | `apps/web/src/components/[feature]/` |
| React hook | `apps/web/src/hooks/` |
| Unit tests | `apps/backend/tests/unit/test_*.py` |

### Commands

```bash
# Backend
cd apps/backend && ruff check .    # Lint
cd apps/backend && ruff format .   # Format
make test T=api                    # Tests

# Frontend
cd apps/web && pnpm lint           # Lint
cd apps/web && pnpm type-check     # Types
make test T=web                    # Tests
```

### Commit Format

```
feat(scope): add feature description
fix(scope): resolve bug description
test(scope): add tests for feature
```

## Reference Files

| File | Content |
|------|---------|
| `conventions.md` | Style guides, naming, types |
| `architecture.md` | Clean Architecture, layers, patterns |
| `solid.md` | SOLID principles with stack examples |
| `guardrails.md` | Security checks, validation rules |

## External References

- `docs/context/code/PATTERNS.md` - Codebase patterns
- `docs/context/product/EPICS/` - Mini-PRDs with acceptance criteria

## Pre-Commit Checklist

- [ ] Tests written and passing (TDD)
- [ ] SOLID principles applied
- [ ] Type hints / TypeScript types complete
- [ ] Guardrails pass (lint, format, type-check)
- [ ] No hardcoded secrets
- [ ] Follows project conventions
