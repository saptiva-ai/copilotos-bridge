# Documentation Sync Checklist

## Pre-Sync

- [ ] Identify which mini-PRD is affected
- [ ] Identify which CAs were validated by tests
- [ ] Check git diff for changed files
- [ ] Note which gaps (if any) were addressed

## Mini-PRD Updates

### Acceptance Criteria
- [ ] Mark each validated CA as done: `- [x] **CA-xx**: ...`
- [ ] Add timestamp: `✅ YYYY-MM-DD`
- [ ] Verify test function exists: `test_ca{id}_*`

### Epic Status
- [ ] If some CAs done: Status = `IN PROGRESS`
- [ ] If all CAs done: Status = `DONE`
- [ ] Update `Last Updated` date
- [ ] If done, add `Completed` date

## GAPS.md Updates

- [ ] Find gaps addressed by this implementation
- [ ] Update status: `OPEN` → `RESOLVED`
- [ ] Add resolution note: "Implemented in EPIC-HUx, PR #y"
- [ ] Verify gap is actually closed (not partial)

## SPRINT_CURRENT.md Updates

- [ ] Update HU status if applicable
- [ ] Add completion date if done
- [ ] Link PRs if available

## Stale Documentation Check

- [ ] Check if PATTERNS.md needs new pattern
- [ ] Check if architecture/* needs update
- [ ] Check if API docs need update
- [ ] Flag (don't fix) any stale docs found

## Missing Documentation Check

- [ ] New endpoints without docs?
- [ ] New components without README?
- [ ] New patterns without PATTERNS.md entry?
- [ ] Flag (don't create) any missing docs

## Post-Sync Verification

```bash
# Verify CA update
grep "CA-01.*\[x\]" docs/context/product/EPICS/EPIC-HU*.md

# Verify epic status
grep "Status: DONE" docs/context/product/EPICS/EPIC-HU*.md

# Verify gap resolution
grep "RESOLVED" docs/context/project/GAPS.md

# Count remaining open items
grep -c "\- \[ \]" docs/context/product/EPICS/EPIC-*.md
grep -c "OPEN" docs/context/project/GAPS.md
```

## Report Generation

- [ ] Generate sync report using template
- [ ] List all updates made
- [ ] List stale docs detected
- [ ] List missing docs detected
- [ ] Include verification commands

## Handoff

If sync reveals issues:
- **Stale docs**: Flag for human review
- **Missing docs**: Create TODO item
- **Unresolved gaps**: Keep status as OPEN
- **Partial implementation**: Keep CA as unchecked
