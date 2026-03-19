# Mini-PRD Template

Use este template para cada épica/HU extraída del PRD.md.

**Output location:** `docs/context/product/EPICS/EPIC-HU{x}.md`

```markdown
# EPIC-HUx: [Descriptive Name]

> **Status**: [DONE | IN PROGRESS | PENDING]
> **Priority**: [P0 | P1 | P2]
> **Close Date**: [DD MMM YYYY]

---

## Agent Execution Context

> **CRITICAL**: This section provides everything a sub-agent needs to execute.

### Target Files

| Action | Path | Description |
|--------|------|-------------|
| CREATE | `apps/<service>/src/...` | Main service logic |
| CREATE | `apps/<service>/src/routers/...` | API endpoints |
| MODIFY | `apps/<service>/src/main.py` | Register router |
| CREATE | `apps/web/src/components/...` | UI component |
| CREATE | `apps/<service>/tests/unit/...` | Unit tests |

### Integration Points

```
[Existing Component] --> [New Component] --> [Existing Component]
     |                        |                      |
  Input: [type]         Process: [what]       Output: [type]
```

### Example Input/Output

**Input** (what the feature receives):
```json
{
  "example_field": "example_value"
}
```

**Output** (what the feature produces):
```json
{
  "result": "expected_output"
}
```

### Validation Commands

```bash
# Run after implementation to verify
make test T=api                    # Backend tests
# OR
make test T=web                    # Web tests
```

---

## General Description

### Objective
[One sentence describing the main objective]

### Solution enables
- [Capability 1]
- [Capability 2]

### Problems solved

| Current Problem | Impact |
|-----------------|--------|
| [Problem 1] | [User/business impact] |

### Success metrics

| Metric | Baseline | Target | How to measure |
|--------|----------|--------|----------------|
| [Metric 1] | [Current] | [Target] | [Source] |

## Strategic Alignment

### Why this epic? (BRD Alignment)

**BRD use case**: #X - [Use case name]

> [Literal quote from BRD justifying this epic]

**Direct connection**:
- This epic implements [specific part] of the use case
- Contributes to North Star metric because [explanation]
- Aligns with design principle: "[principle]"

### How does it integrate? (Architecture Alignment)

**Components involved**:

```
[ASCII flow diagram showing data flow]
```

**Technical dependencies**:

| Component | Status | Required for |
|-----------|--------|--------------|
| [Component 1] | [DONE/PENDING] | [Phase X] |

## Deliverables List

| # | Deliverable | File Path | Completion Criteria |
|---|-------------|-----------|---------------------|
| E1 | [Name] | `path/to/file.py` | [How to verify] |

## Acceptance Criteria

### Functional
- [ ] **CA-01**: [Verifiable criterion with specific behavior]

### Non-Functional
- [ ] **CA-XX**: [Performance/Security/UX with measurable target]

## Implementation Phases

### Phase 1: [Name]

**Deliverables**: E1, E2

**Files to create/modify**:

| File | Action | Purpose |
|------|--------|---------|
| `path/to/file1.py` | CREATE | [Description] |
| `path/to/file2.tsx` | MODIFY | [Description] |

**Sub-agent delegation**:

```yaml
Agent: plan-architect
Task: Design implementation for Phase 1
Input: This mini-PRD section
Output: Detailed file-by-file plan
```

```yaml
Agent: feature-dev:code-architect
Task: Implement E1, E2
Input: plan-architect output + this mini-PRD
Output: Working code with tests
```

## Demo Evidence (REQUIRED)

> **CRITICAL**: EPIC cannot be marked DONE without demo evidence.

| Evidence Type | Location | Date | Verified By |
|---------------|----------|------|-------------|
| Screenshot | `docs/demos/EPIC-HUx_screenshot.png` | | |
| Demo Video | `docs/demos/EPIC-HUx_demo.mp4` | | |
| Stakeholder Sign-off | Email/Slack link | | @[name] |

**Instructions**:
1. Create `docs/demos/` directory if it doesn't exist
2. Record a screen capture showing the feature working end-to-end
3. Take a screenshot of the key functionality
4. Get stakeholder approval (via email, Slack, or meeting notes)
5. Link evidence in this table before marking EPIC as DONE

**Validation**: Run `.claude/scripts/validate_epic.sh docs/context/product/EPICS/EPIC-HUx.md` before closing

## Definition of Done

| Criterion | Verification Command | Pass Condition |
|-----------|---------------------|----------------|
| All target files exist | `.claude/scripts/validate_epic.sh` | Exit 0 |
| Tests | `make test T=api` (or web) | Exit 0 |
| Lint | `make lint` or specific command | No errors |
| Type | `make type-check` or specific command | No errors |
| Demo evidence | Check Demo Evidence table above | All files exist |

## Risks and Mitigation

| Risk | Prob | Impact | Mitigation |
|------|------|--------|------------|
| [Risk] | [H/M/L] | [H/M/L] | [Action] |

## References

| Document | Relevant Section |
|----------|------------------|
| BRD.md | [Specific section] |
| 00_architecture/*.md | [Specific doc] |
| GAPS.md | [Gap ID] |
```