---
name: prd
description: Decompose PRD.md into mini-PRDs (one per epic) using prd-builder skill.
argument-hint: ""
allowed-tools: [Read, Write, Edit, Grep, Glob, Task]
---

Decompose existing PRD.md into executable mini-PRDs for each user story/epic.

## Context
- Business requirements: `docs/context/product/BRD.md`
- Product requirements: `docs/context/product/PRD.md`
- Architecture: `docs/architecture/README.md`
- Gaps (optional): `docs/context/project/GAPS.md`

## Process
1. Use `prd-architect` agent to parse BRD.md + PRD.md
2. Extract all user stories (HU1, HU2, HU3, ...)
3. For each HU, generate mini-PRD using `prd-builder` skill template
4. Output to `docs/context/product/EPICS/EPIC-HU{x}.md`
5. Create `docs/context/product/EPICS/README.md` index

## Agent Delegation (Deterministic)

**CRITICAL**: Use Task() with subagent_type for deterministic execution:

```python
Task(
    subagent_type="prd-architect",
    prompt=f"Feature description: $ARGUMENTS"
)
```

### Full Context Pattern

For PRD decomposition, include all context:

```python
Task(
    subagent_type="prd-architect",
    prompt=f"""
Feature description: $ARGUMENTS

Context files:
- BRD: docs/context/product/BRD.md
- PRD: docs/context/product/PRD.md
- Architecture: docs/architecture/README.md
- Gaps: docs/context/project/GAPS.md (optional)

Task: Decompose PRD into mini-PRDs using prd-builder skill.
Output: docs/context/product/EPICS/EPIC-HU{{1..N}}.md + README.md
"""
)
```

## Expected Output
```
docs/context/product/EPICS/
├── README.md       # Index with status table
├── EPIC-HU1.md     # Mini-PRD for User Story 1
├── EPIC-HU2.md     # Mini-PRD for User Story 2
└── ...
```

## Execution Flow

1. Parse `$ARGUMENTS` (if specific epic requested)
2. Read BRD.md and PRD.md
3. Invoke `prd-architect` via Task() with full context
4. Agent uses `prd-builder` skill to generate mini-PRDs
5. Output saved to `docs/context/product/EPICS/`
