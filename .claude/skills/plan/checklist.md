# Pre-Planning Checklist

## Before Starting

### Context Loaded?
- [ ] Read mini-PRD: `docs/context/product/EPICS/EPIC-HUx.md`
- [ ] Read BRD alignment: `docs/context/product/BRD.md`
- [ ] Check architecture: `docs/architecture/README.md`
- [ ] Check gaps: `docs/context/project/GAPS.md`
- [ ] Check sprint: `docs/context/project/SPRINT_CURRENT.md`

### Requirements Clear?
- [ ] Objective is specific (not vague)
- [ ] Acceptance criteria defined (CA-xx)
- [ ] Success metrics known
- [ ] Scope boundaries clear

### Blockers Checked?
- [ ] No blocking gaps in GAPS.md
- [ ] Required dependencies exist
- [ ] No conflicting PRs in progress

## During Planning

### Exploration Done?
- [ ] Similar code patterns identified
- [ ] Existing abstractions understood
- [ ] Dependencies mapped
- [ ] Test patterns reviewed

### Design Complete?
- [ ] All files listed (create + modify)
- [ ] Phases defined logically
- [ ] Risks assessed
- [ ] Validation commands specified

### TDD Ready?
- [ ] Test functions named: `test_ca{id}_{description}`
- [ ] Test file locations specified
- [ ] Each CA has corresponding test

## Quality Gates

### Complexity Check
| Complexity | Criteria | Action |
|------------|----------|--------|
| LOW | <5 files, 1 service | Proceed |
| MEDIUM | 5-10 files, 2-3 services | Review risks |
| HIGH | >10 files, >3 services | Split into phases/PRs |

### Risk Assessment
- [ ] HIGH impact risks have mitigations
- [ ] Breaking changes identified
- [ ] Rollback strategy (if needed)

## Before Submitting Plan

### Completeness
- [ ] All sections of template filled
- [ ] No TBD or placeholder values
- [ ] Commands are runnable
- [ ] File paths are accurate

### Alignment
- [ ] Plan matches mini-PRD objective
- [ ] All CAs covered
- [ ] Follows project conventions

### Ready for Handoff
- [ ] Plan is actionable by code-implementer
- [ ] No ambiguity requiring clarification
- [ ] TDD approach is clear

## Red Flags

Stop planning if:
- [ ] Mini-PRD is missing or incomplete
- [ ] Blocking gap exists
- [ ] Scope keeps expanding
- [ ] Architecture unclear

Action: Escalate to user or request clarification.
