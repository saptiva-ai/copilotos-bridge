# Agentic Development Flow

Una vez generado el mini-PRD, esta es la secuencia de ejecución:

```
mini-PRD created
     │
     ▼
┌─────────────────┐
│  plan-architect │  Design implementation plan
└────────┬────────┘
         │ approved plan
         ▼
┌─────────────────┐
│ code-implementer│  Implement with TDD + SOLID
└────────┬────────┘
         │ code + tests
         ▼
┌─────────────────┐
│   test-runner   │  Validate with MCP diagnostics
└────────┬────────┘
         │ ✅ tests pass
         ▼
┌─────────────────┐
│  code-reviewer  │  Review before merge
└────────┬────────┘
         │ approved
         ▼
┌─────────────────┐
│    doc-sync     │  Update PRD status + docs
└─────────────────┘
```

## Sub-Agent Delegation Examples

### Planning Phase

```yaml
Agent: plan-architect
Task: Design implementation plan for EPIC-HU1
Input: |
  Read: docs/context/product/EPICS/EPIC-HU1.md
  Focus: Agent Execution Context section
Output: File-by-file implementation plan with sequence
```

### Implementation Phase

```yaml
Agent: code-implementer
Task: Implement EPIC-HU1 Phase 1
Input: |
  PRD: docs/context/product/EPICS/EPIC-HU1.md
  Plan: Approved output from plan-architect
  Files: Target Files table from PRD
Approach: |
  1. Write failing test for CA-01 (RED)
  2. Implement minimal code to pass (GREEN)
  3. Refactor with SOLID principles
  4. Run guardrails (ruff, pytest)
Output: Working code + tests matching Example Input/Output
```

### Testing Phase

```yaml
Agent: test-runner
  PRD: docs/context/product/EPICS/EPIC-HU1.md
  Commands: Validation Commands from PRD
  Criteria: Acceptance Criteria from PRD
Output: Test results with pass/fail status
```

### Review Phase

```yaml
Agent: code-reviewer
Task: Review EPIC-HU1 before merge
Input: |
  PRD: docs/context/product/EPICS/EPIC-HU1.md
  Changes: git diff from implementation
Output: Review feedback with severity levels
```
