# Plan Output Template

## Implementation Plan: [Feature Name]

**Epic:** EPIC-HUx
**Complexity:** LOW | MEDIUM | HIGH
**Estimated Files:** X new, Y modified

### Objective
[1-2 sentences from mini-PRD]

### Files to Change

#### Create
| File | Purpose | Phase |
|------|---------|-------|
| `apps/backend/src/services/new_service.py` | Business logic | 1 |
| `apps/backend/tests/unit/test_new_service.py` | Unit tests | 1 |
| `apps/web/src/components/NewComponent.tsx` | UI component | 2 |

#### Modify
| File | Change | Risk |
|------|--------|------|
| `apps/backend/src/routers/api.py` | Add endpoint | LOW |
| `apps/backend/src/services/existing.py` | Extend method | MEDIUM |

### Phases

#### Phase 1: [Name] (backend)
- [ ] Write failing test for CA-01 (RED)
- [ ] Implement `new_service.py` to pass test (GREEN)
- [ ] Refactor with SOLID principles
- [ ] Wire to router
- [ ] Run guardrails: `ruff check`, `pytest`

#### Phase 2: [Name] (frontend)
- [ ] Create `NewComponent.tsx`
- [ ] Add to page layout
- [ ] Write component tests
- [ ] Test integration

### Dependencies

| Dependency | Status | Blocking? |
|------------|--------|-----------|
| MongoDB schema | EXISTS | No |
| Auth middleware | EXISTS | No |
| Gap P1-1 | PENDING | Yes → resolve first |

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing API | LOW | HIGH | Add versioning |
| Performance regression | MEDIUM | MEDIUM | Add benchmarks |

### Success Criteria

Maps to mini-PRD acceptance criteria:

| CA | Description | Test Function |
|----|-------------|---------------|
| CA-01 | User can login | `test_ca01_login_succeeds` |
| CA-02 | Invalid password error | `test_ca02_invalid_password` |

### Validation Commands

```bash
# Before implementation (baseline)
make test T=api

# After each phase
ruff check apps/backend/src/
pytest apps/backend/tests/unit -q

# Final validation
make test T=api
make test T=web
```

### Handoff

After approval, delegate to:
- **Agent:** `code-implementer`
- **Input:** This plan + mini-PRD
- **Approach:** TDD (RED → GREEN → REFACTOR)
