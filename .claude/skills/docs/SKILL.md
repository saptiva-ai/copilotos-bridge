---
name: docs
description: Keep documentation synchronized with code changes. Use after test-runner confirms tests pass to close the feedback loop. (project)
allowed-tools: [Read, Write, Edit, Grep, Glob]
---

# Documentation Sync Skill

> Maintain consistency between code and documentation.

## Sync Flow

```
┌─────────────────┐
│  Code Changes   │  git diff, test results
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Map to PRD     │  Find related EPIC-HUx.md
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Update Status  │  CA-xx: ✅ DONE
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Check GAPS     │  Mark resolved gaps
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Epic Complete? │  All CAs done → EPIC DONE
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Flag Stale     │  Missing/outdated docs
└─────────────────┘
```

## Quick Reference

### Status Values

| Document | Status Values |
|----------|---------------|
| mini-PRD Epic | `PENDING` → `IN PROGRESS` → `DONE` |
| mini-PRD CA | `- [ ]` → `- [x]` |
| GAPS.md | `OPEN` → `PARTIAL` → `RESOLVED` |
| SPRINT | `IN PROGRESS` → `DONE` |

### Document Locations

| Document | Path |
|----------|------|
| Mini-PRDs | `docs/context/product/EPICS/EPIC-HU*.md` |
| Gaps | `docs/context/project/GAPS.md` |
| Sprint | `docs/context/project/SPRINT_CURRENT.md` |
| Patterns | `docs/context/code/PATTERNS.md` |
| Architecture | `docs/architecture/` |

### Update Commands

```bash
# Find PRDs with pending CAs
grep -r "\- \[ \]" docs/context/product/EPICS/EPIC-*.md

# Find open gaps
grep "OPEN" docs/context/project/GAPS.md

# Check sprint status
grep "IN PROGRESS" docs/context/project/SPRINT_CURRENT.md
```

## Reference Files

| File | Content |
|------|---------|
| `status-values.md` | All status values and transitions |
| `templates.md` | Update templates for each doc type |
| `checklist.md` | Sync verification checklist |

## Sync Rules

### DO
- Update CA status when tests pass
- Mark gaps RESOLVED when verified
- Flag stale docs (don't fix, report)
- Use ISO dates (YYYY-MM-DD)
- Add timestamps to status changes

### DON'T
- Remove content (only update status)
- Fix stale docs (report only)
- Update CLAUDE.md (requires review)
- Create new mini-PRDs (use prd-architect)

## Verification

```bash
# After sync, verify consistency
grep -c "DONE" docs/context/product/EPICS/EPIC-*.md
grep -c "RESOLVED" docs/context/project/GAPS.md
```
