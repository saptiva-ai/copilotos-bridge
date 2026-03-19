---
name: prd-builder
description: Transform PRD epics into modular mini-PRDs for agentic development. Use when decomposing existing PRD.md into executable contracts for sub-agents. (project)
allowed-tools: [Read, Write, Edit, Grep, Glob]
---

# PRD Builder Skill

> Decompose PRD.md into executable mini-PRDs (one per epic) for agentic workflows.

## Purpose

Transform **existing PRD.md** into **modular mini-PRDs** that serve as **executable contracts for sub-agents**.

### Why Mini-PRDs?

Each mini-PRD is designed to be **self-contained and executable by sub-agents**:

1. **Input for Sub-Agents**: Execution contracts for `plan-architect`, `feature-dev:code-architect`, `test-runner`, etc.
2. **Complete Context**: All context a sub-agent needs to implement without asking questions.
3. **Agentic Flow**: `BRD.md + PRD.md → [Parse epics] → mini-PRDs → [Sub-agents execute] → Feature delivered`

### What Makes a Mini-PRD Agent-Ready?

| Requirement | Why |
|-------------|-----|
| Explicit file paths | WHERE to create/modify code |
| Architecture context | HOW components connect |
| Acceptance criteria | WHEN task is complete |
| Dependencies listed | WHAT must exist before starting |
| Example inputs/outputs | Concrete validation |

## Agent Flow

```
1. Load BRD.md for business context
2. Load PRD.md and parse all user stories (HU1, HU2, ...)
3. Read architecture docs to understand system
4. FOR EACH user story in PRD:
   a. Extract BRD alignment (Why - use case, metric)
   b. Map architecture components (How - data flow)
   c. Define concrete deliverables (What - files, endpoints)
   d. Specify file paths and code locations
   e. Add example inputs/outputs for validation
   f. Generate mini-PRD using template.md
   g. Write to docs/context/EPICS/EPIC-HU{x}.md
5. Create EPICS/README.md index with status table
6. Validate each mini-PRD is agent-executable
```

## Required Context

### 1. BRD (Primary Business Context)
```bash
Read: docs/context/product/BRD.md
```
Extract: use cases, North Star metric, success metrics, design principles

### 2. PRD (User Stories Source)
```bash
Read: docs/context/product/PRD.md
```
Extract: All HU (user stories) with acceptance criteria, priorities, status

### 3. Architecture
```bash
Read: docs/architecture/README.md
Read: docs/context/architecture/AGENTS.md (if exists)
Read: docs/context/architecture/DATA.md (if exists)
```
Extract: components, agent contracts, data flow, dependencies

### 4. Gaps (Optional)
```bash
Read: docs/context/project/GAPS.md
```
Extract: blocking gaps, dependencies each epic may resolve

## Input Assumptions

| Requirement | Location | Format |
|-------------|----------|--------|
| Business requirements | `docs/context/product/BRD.md` | Markdown with use cases |
| Product requirements | `docs/context/product/PRD.md` | Markdown with HU sections |
| Architecture docs | `docs/architecture/` | Markdown files |
| Current gaps (optional) | `docs/context/project/GAPS.md` | Markdown with blocking issues |

## Output Structure

```
docs/context/product/EPICS/
├── README.md              # Index: status table for all epics
├── EPIC-HU1.md            # Mini-PRD for User Story 1
├── EPIC-HU2.md            # Mini-PRD for User Story 2
├── EPIC-HU3.md            # Mini-PRD for User Story 3
└── ...
```

Each `EPIC-HU{x}.md` file contains:
- Agent Execution Context (target files, integration points, examples)
- BRD alignment (why this epic matters)
- Architecture alignment (how it integrates)
- Deliverables with file paths
- Acceptance criteria (CA-01, CA-02, ...)
- Implementation phases
- Definition of Done with validation commands

## Reference Files

| File | Content |
|------|---------|
| `template.md` | Complete mini-PRD template |
| `checklist.md` | Quality validation checklist |
| `delegation.md` | Agentic flow and examples |

## Quick Start

1. Ensure BRD.md and PRD.md exist
2. For each epic in PRD, use `template.md`
3. Write to `docs/context/product/EPICS/EPIC-HU{x}.md`
4. Validate with `checklist.md`
5. Create `EPICS/README.md` index
6. Document delegation with `delegation.md`

## Example Invocation

```yaml
Task: "Decompose PRD.md into mini-PRDs"
Agent: prd-architect
Skill: prd-builder
Input:
  - docs/context/product/BRD.md
  - docs/context/product/PRD.md
Output: docs/context/product/EPICS/EPIC-HU{1..N}.md + README.md
```
