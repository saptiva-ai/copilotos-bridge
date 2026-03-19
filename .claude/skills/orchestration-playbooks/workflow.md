# Workflow Details

> Complete orchestration flow with entry/exit criteria.

## Full Workflow

```
┌──────────────────────────────────────────────────────────────────┐
│                         /do <task>                                │
│                              │                                    │
│              ┌───────────────┴───────────────┐                    │
│              ▼                               ▼                    │
│     ┌─────────────────┐             ┌─────────────────┐          │
│     │  Strategic?     │─── yes ───▶│  prd-architect  │          │
│     │  (epic/PRD)     │             │  plan-architect │          │
│     └────────┬────────┘             └─────────────────┘          │
│              │ no                                                 │
│              ▼                                                    │
│     ┌─────────────────┐             ┌─────────────────┐          │
│     │  Tactical?      │─── yes ───▶│ software-devlpr │          │
│     │  (implement)    │             │  code-reviewer  │          │
│     └────────┬────────┘             └─────────────────┘          │
│              │ no                                                 │
│              ▼                                                    │
│     ┌─────────────────┐             ┌─────────────────┐          │
│     │  Operational?   │─── yes ───▶│   test-runner   │          │
│     │  (run/check)    │             │   dev-validator │          │
│     └─────────────────┘             │   infra-doctor  │          │
│                                     │   repo-scout    │          │
│                                     └─────────────────┘          │
└──────────────────────────────────────────────────────────────────┘
```

## Phase 0: PRD (Requirements)

**Entry:** BRD exists, epic identified
**Agent:** `prd-architect`
**Outputs:**
- Mini-PRD at `docs/context/EPICS/EPIC-HUx.md`
- Updated `docs/context/EPICS/GAPS.md` if blockers found

**Validation:**
- [ ] Mini-PRD has acceptance criteria
- [ ] Dependencies identified
- [ ] Risk assessment included

## Phase 1: Explore (Context)

**Entry:** Task defined, need codebase understanding
**Agent:** `repo-scout`
**Commands:** `/repo-map`
**Outputs:**
- `.claude/output/repo_map.md` updated
- Key files identified

**Validation:**
- [ ] Relevant patterns identified
- [ ] Existing code understood
- [ ] No duplicate implementation risk

## Phase 2: Plan (Design)

**Entry:** Context gathered, ready to design
**Agent:** `plan-architect`
**Commands:** EnterPlanMode
**Outputs:**
- Implementation plan with phases
- File changes listed
- Risk assessment

**Validation:**
- [ ] User approved plan (ExitPlanMode)
- [ ] Test strategy defined
- [ ] Dependencies resolved

## Phase 3: Code (Implementation)

**Entry:** Plan approved
**Agent:** `software-developer`
**Pattern:** TDD (Red → Green → Refactor)
**Outputs:**
- Production code
- Unit tests
- Integration tests if needed

**Validation:**
- [ ] Tests written before code (TDD)
- [ ] All tests pass locally
- [ ] SOLID principles followed

## Phase 4: Test (Validation)

**Entry:** Code written
**Agent:** `test-runner` (full), `dev-validator` (quick)
**Commands:** `/quick-checks`, `make test T=api`
**Outputs:**
- Test results
- Coverage report (if applicable)

**Validation:**
- [ ] Exit code 0
- [ ] No regressions
- [ ] Edge cases covered

## Phase 5: Review (Quality)

**Entry:** Tests pass
**Agent:** `code-reviewer`
**Focus:**
- Security vulnerabilities
- OWASP Top 10
- Pattern adherence
- Performance issues

**Validation:**
- [ ] No P0/P1 issues
- [ ] Conventions followed
- [ ] Ready for merge

## Phase 6: Docs (Closure)

**Entry:** Review passed
**Agent:** `doc-sync`
**Outputs:**
- Mini-PRD status updated
- GAPS.md updated
- README changes if needed

**Validation:**
- [ ] Mini-PRD marked complete
- [ ] Documentation matches code
- [ ] Sprint status updated

## Quick Paths

### Bug Fix Path
```
Explore → Code → Test → Review
```

### Feature Path (Full)
```
PRD → Explore → Plan → Code → Test → Review → Docs
```

### Refactor Path
```
Explore → Plan → Code → Test → Review
```

### Investigation Path
```
Explore → (report findings)
```
