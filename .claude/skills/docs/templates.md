# Documentation Update Templates

## CA Status Update

When marking an acceptance criterion as done:

```markdown
# Before
- [ ] **CA-01**: User can login with valid email and password

# After
- [x] **CA-01**: User can login with valid email and password ✅ 2025-01-15
```

## Epic Status Update

When all CAs are complete:

```markdown
# Before
## Status: IN PROGRESS
**Last Updated:** 2025-01-10

# After
## Status: DONE
**Last Updated:** 2025-01-15
**Completed:** 2025-01-15
```

## Gap Resolution Update

When a gap is resolved:

```markdown
# In GAPS.md

# Before
| P1-1 | Missing auth middleware | HIGH | OPEN | - |

# After
| P1-1 | Missing auth middleware | HIGH | RESOLVED | Implemented in EPIC-HU1, PR #42 |
```

## Sprint Update

When an HU is completed:

```markdown
# In SPRINT_CURRENT.md

# Before
## HU-1: User Authentication
- **Status:** IN PROGRESS
- **Started:** 2025-01-10

# After
## HU-1: User Authentication
- **Status:** DONE
- **Started:** 2025-01-10
- **Completed:** 2025-01-15
- **PRs:** #42, #43
```

## Stale Documentation Flag

When flagging stale docs (don't fix, just report):

```markdown
## Stale Documentation Detected

| Document | Issue | Recommendation |
|----------|-------|----------------|
| `docs/context/code/PATTERNS.md` | Missing new SSE streaming pattern | Add section for EventSource |
| `docs/architecture/data/postgres_schema.md` | References old Qdrant schema | Update to Weaviate |
```

## Missing Documentation Flag

When flagging missing docs:

```markdown
## Missing Documentation

- [ ] New endpoint `/api/auth/refresh` needs API documentation
- [ ] New component `SessionManager` needs README
- [ ] New pattern `MCP Protocol v2` needs PATTERNS.md entry
```

## Sync Report Template

After completing sync:

```markdown
## Documentation Sync Report

**Trigger:** test-runner exit 0
**Date:** 2025-01-15
**Epic:** EPIC-HU1

### Updates Made

#### Mini-PRD: EPIC-HU1.md
| Change | Before | After |
|--------|--------|-------|
| Status | IN PROGRESS | DONE |
| CA-01 | `[ ]` | `[x]` ✅ |
| CA-02 | `[ ]` | `[x]` ✅ |
| CA-03 | `[ ]` | `[x]` ✅ |

#### GAPS.md
| Gap | Before | After |
|-----|--------|-------|
| P1-1 | OPEN | RESOLVED |

#### SPRINT_CURRENT.md
- HU-1 marked as DONE

### Stale Documentation
None detected.

### Missing Documentation
- [ ] Add API docs for `/api/auth/login`

### Verification
```bash
grep "DONE" docs/context/product/EPICS/EPIC-HU1.md  # ✅
grep "P1-1.*RESOLVED" docs/context/project/GAPS.md  # ✅
```
```
