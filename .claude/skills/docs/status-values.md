# Status Values Reference

## Mini-PRD Status

### Epic Status

| Status | Meaning | Next |
|--------|---------|------|
| `PENDING` | Not started | `IN PROGRESS` |
| `IN PROGRESS` | Being implemented | `DONE` or back to `PENDING` |
| `DONE` | All CAs complete | - |
| `BLOCKED` | Waiting on dependency | Resolve blocker |

**Location in file:**
```markdown
## Status: IN PROGRESS
**Last Updated:** 2025-01-15
```

### Acceptance Criteria Status

| Status | Markdown | Meaning |
|--------|----------|---------|
| Pending | `- [ ] **CA-01**: ...` | Not implemented |
| Done | `- [x] **CA-01**: ...` | Implemented and tested |

**Update format:**
```markdown
## Acceptance Criteria

### Functional
- [x] **CA-01**: User can login with valid email ✅ 2025-01-15
- [ ] **CA-02**: Invalid password shows error message
- [x] **CA-03**: Session expires after 30 minutes ✅ 2025-01-15
```

## GAPS.md Status

| Status | Meaning | Action |
|--------|---------|--------|
| `OPEN` | Gap exists, not addressed | Plan fix |
| `PARTIAL` | Partially fixed | Continue work |
| `RESOLVED` | Gap closed | Verify in code |

**Format:**
```markdown
| ID | Description | Priority | Status | Resolution |
|----|-------------|----------|--------|------------|
| P1-1 | Missing auth middleware | HIGH | RESOLVED | Added in PR #42 |
| P1-2 | No rate limiting | MEDIUM | OPEN | - |
```

## SPRINT_CURRENT.md Status

| Status | Meaning |
|--------|---------|
| `PLANNED` | In current sprint, not started |
| `IN PROGRESS` | Being worked on |
| `DONE` | Completed this sprint |
| `DEFERRED` | Moved to next sprint |

**Format:**
```markdown
## HU-1: User Authentication
- **Status:** DONE
- **Completed:** 2025-01-15
- **PRs:** #42, #43
```

## Status Transitions

### Epic Lifecycle

```
PENDING → IN PROGRESS → DONE
    ↑          │
    └──────────┘ (if blocked or deprioritized)
```

### CA Lifecycle

```
- [ ] CA-01: ... → - [x] CA-01: ... ✅ YYYY-MM-DD
```

### Gap Lifecycle

```
OPEN → PARTIAL → RESOLVED
  ↑       │
  └───────┘ (if partial fix rolled back)
```

## Timestamps

Always use ISO format: `YYYY-MM-DD`

```markdown
- [x] **CA-01**: User can login ✅ 2025-01-15
```

## Verification Queries

```bash
# Count pending CAs
grep -c "\- \[ \]" docs/context/product/EPICS/EPIC-*.md

# Count done CAs
grep -c "\- \[x\]" docs/context/product/EPICS/EPIC-*.md

# Find in-progress epics
grep -l "Status: IN PROGRESS" docs/context/product/EPICS/EPIC-*.md

# Find open gaps
grep "| OPEN |" docs/context/project/GAPS.md
```
