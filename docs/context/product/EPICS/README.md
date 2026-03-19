# Bank Advisor - Epics Index

> **Purpose**: Index of executable mini-PRDs for agentic development workflow
> **Version**: 1.0
> **Last Update**: 2025-12-30

## Overview

This directory contains modular mini-PRDs (one per user story) designed as **executable contracts for sub-agents**. Each mini-PRD includes complete context, file paths, acceptance criteria, and validation commands needed for autonomous implementation.

---

## Status Dashboard

| Epic | Priority | Status | Progress | Target Date | Blocking Gaps |
|------|----------|--------|----------|-------------|---------------|
| [EPIC-HU1](EPIC-HU1.md) | P0 | ✅ DONE | 100% | 29 Dec 2025 | None |
| [EPIC-HU2](EPIC-HU2.md) | P0 | ✅ DONE | 100% | 06 Jan 2026 | None |
| [EPIC-HU3](EPIC-HU3.md) | P1 | ⚠️ IN PROGRESS | 60% | 15 Jan 2026 | P1-1 (Abstention Mode) |
| [EPIC-HU4](EPIC-HU4.md) | P1 | ✅ DONE | 100% | 28 Dec 2025 | None |
| [EPIC-HU5](EPIC-HU5.md) | P1 | ✅ DONE | 100% | 31 Dec 2025 | None |

**Overall v1.2 Progress**: 90% (4.5/5 epics done, 0.5/5 in progress)

---

## BRD Alignment

Each epic maps to specific BRD use cases and success metrics:

| Epic | BRD Use Case | North Star Contribution | Success Metric |
|------|--------------|------------------------|----------------|
| HU1 | UC-3: Consulta a datos | Enables WAU baseline | TTI < 3s |
| HU2 | UC-2: Benchmark competitivo | Drives WAU adoption | Multi-bank queries/week |
| HU3 | UC-5: UX fluida | Reduces friction | Abstention rate < 10% |
| HU4 | UC-1: Consulta cualitativa CUB | Enables trust | RAG accuracy > 95% |
| HU5 | UC-4: Feedback de usuario | Improves system | Feedback submissions/week |

**North Star Metric**: WAU (Weekly Active Users) >= 5 users/week

---

## Architecture Coverage

| Component | HU1 | HU2 | HU3 | HU4 | HU5 |
|-----------|-----|-----|-----|-----|-----|
| Intent Router | ✅ | ✅ | ✅ | ✅ | - |
| QuerySpec Builder | ✅ | ✅ | ✅ | - | - |
| SQL Agent | ✅ | ✅ | - | - | - |
| Knowledge Synthesizer | - | - | - | ✅ | - |
| Chart Builder | - | ✅ | - | - | - |
| Feedback Service | - | - | - | - | ✅ |

**Legend**: ✅ Done | ⚠️ In Progress | - Not Applicable

---

## Quick Reference

### By Completion Status

**Done (deployable)**:
- [EPIC-HU1: Query Multi-Banco](EPIC-HU1.md)
- [EPIC-HU2: Comparación Multi-Banco](EPIC-HU2.md)
- [EPIC-HU4: RAG con Glosario](EPIC-HU4.md)
- [EPIC-HU5: Sistema Feedback](EPIC-HU5.md)

**In Progress (15 Jan target)**:
- [EPIC-HU3: UI Clarificación](EPIC-HU3.md)

### By Priority

**P0 (Must Have for v1.2)**:
- [EPIC-HU1: Query Multi-Banco](EPIC-HU1.md) - ✅ Done
- [EPIC-HU2: Comparación Multi-Banco](EPIC-HU2.md) - ✅ Done

**P1 (Should Have for v1.2)**:
- [EPIC-HU3: UI Clarificación](EPIC-HU3.md) - ⚠️ In Progress
- [EPIC-HU4: RAG con Glosario](EPIC-HU4.md) - ✅ Done
- [EPIC-HU5: Sistema Feedback](EPIC-HU5.md) - ✅ Done

---

## Agentic Workflow

```
BRD.md + PRD.md
      │
      ▼
┌─────────────────┐
│  prd-architect  │ → Generates mini-PRDs (this directory)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  repo-scout     │ → Maps codebase structure
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ plan-architect  │ → Designs implementation plan
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│code-implementer │ → Implements with TDD
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  test-runner    │ → Validates with tests
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ code-reviewer   │ → Reviews for quality
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    doc-sync     │ → Updates docs/PRDs
└─────────────────┘
```

---

## Dependencies Graph

```
HU1 (Query Multi-Banco)
 │
 ├──> HU2 (Comparación) - Requires multi-bank QuerySpec support
 ├──> HU3 (UI Clarificación) - Requires confidence scoring
 └──> HU4 (RAG Glosario) - Requires Ontology_Terms grounding

HU5 (Feedback) - Independent, integrates with all
```

**Critical Path**: HU1 → HU2, HU3

---

## Go/No-Go Criteria (15 Jan 2026)

### Must Have (all epics)
- [ ] HU1: 10+ bancos consultables
- [ ] HU2: Comparación hasta 5 bancos simultáneos con gráfica
- [ ] HU3: UI clarificación funcional para queries ambiguos
- [ ] HU4: RAG con 3,500+ términos regulatorios
- [ ] HU5: Sistema feedback con thumbs up/down funcional

### Performance
- [ ] TTI < 5 segundos (p95)
- [ ] Accuracy vs CNBV: ±0.01%
- [ ] Abstention rate < 10% on ambiguous queries

### Quality
- [ ] 0 bugs críticos
- [ ] Tests E2E passing (10 demo queries)
- [ ] Documentación completa

---

## References

| Document | Purpose |
|----------|---------|
| [BRD.md](../BRD.md) | Business requirements and use cases |
| [PRD.md](../product/PRD.md) | Product requirements and user stories |
| [architecture/](../architecture/) | System architecture and components |
| [GAPS.md](../PRD-old/GAPS.md) | Technical gaps and blockers |
| [PATTERNS.md](../PATTERNS.md) | Code patterns and conventions |

---

## Maintenance

| Field | Value |
|-------|-------|
| Owner | Jaziel Flores (prd-architect) |
| Update Frequency | On epic completion or major milestone |
| Version Strategy | Semantic versioning aligned with PRD |

**Next Review**: 15 Jan 2026 (v1.2 release)
