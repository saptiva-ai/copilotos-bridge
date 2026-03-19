---
id: "TASK-2026-01-27-0200__semantic-intent-router"
title: "Semantic Intent Router for Bank Advisor Pre-Check"
status: "BACKLOG"
phase: "Research"
scope_in:
  - "Replace regex/hardcoded lists with semantic similarity scoring"
  - "Leverage existing EmbeddingService (paraphrase-multilingual-MiniLM-L12-v2)"
  - "Add contextual enhancement using conversation history"
  - "Implement feedback learning system with Redis"
  - "Maintain backward compatibility with explicit tool enablement"
scope_out:
  - "Changes to bank-advisor plugin intent detection"
  - "New ML model training or fine-tuning"
  - "External API dependencies (OpenAI, etc.)"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "make test-local TEST_FILE='tests/unit/test_streaming_services.py' TEST_ARGS='-k BankAdvisorPreCheckService'"
  - "make test T=api TEST_ARGS='-k intent'"
pr_files:
  - "apps/backend/src/services/streaming/bank_advisor_precheck.py"
  - "apps/backend/src/services/intent/semantic_scorer.py"
  - "apps/backend/src/services/intent/context_enhancer.py"
  - "apps/backend/src/services/intent/feedback_collector.py"
  - "apps/backend/src/services/intent/__init__.py"
  - "apps/backend/tests/unit/test_semantic_intent_router.py"
test_status: "pending"
---

# Summary

- **Objective:** Replace hardcoded regex patterns in `BankAdvisorPreCheckService` with a semantic similarity-based intent classification system that dynamically adapts and learns from feedback.

- **Constraints:**
  - Must use existing `EmbeddingService` (Saptiva internal, paraphrase-multilingual-MiniLM-L12-v2)
  - Must use existing `RedisCache` for feedback storage
  - Latency must be <50ms for cached embeddings
  - No external API dependencies (100% open source / internal tools)
  - Must maintain backward compatibility with `tools_enabled` explicit override

# Problem Statement

Current implementation has several issues:

1. **Hardcoded patterns** - `GREETING_PATTERNS`, `ACKNOWLEDGMENT_PATTERNS`, `KNOWLEDGE_TRIGGERS` require manual maintenance
2. **Fragile regex** - "Holi" doesn't match "Hola" pattern
3. **No context awareness** - Ignores conversation history
4. **No learning** - When bank-advisor returns `None`, we don't learn

# Proposed Solution

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  SEMANTIC INTENT ROUTER ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐   ┌────────────────────┐   ┌─────────────────────┐   │
│  │   Level 1    │   │      Level 2       │   │      Level 3        │   │
│  │  Fast Cache  │──▶│  Semantic Scorer   │──▶│  Context Enhancer   │   │
│  │   (Redis)    │   │  (EmbeddingService)│   │  (Recent Messages)  │   │
│  └──────────────┘   └────────────────────┘   └─────────────────────┘   │
│         │                    │                        │                 │
│         └────────────────────┴────────────────────────┘                 │
│                              │                                          │
│                              ▼                                          │
│         ┌─────────────────────────────────────────────────┐            │
│         │            Decision Aggregator                   │            │
│         │  confidence = weighted_sum(fast, semantic, ctx)  │            │
│         │  decision = INVOKE if conf > 0.6 else SKIP       │            │
│         └─────────────────────────────────────────────────┘            │
│                              │                                          │
│                              ▼                                          │
│         ┌─────────────────────────────────────────────────┐            │
│         │           Feedback Collector (Redis)            │            │
│         │  if bank_advisor → None: mark as non_banking    │            │
│         └─────────────────────────────────────────────────┘            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

# Key Services to Leverage

| Service | Location | Usage |
|---------|----------|-------|
| `EmbeddingService` | `src/services/embedding_service.py` | `encode_single_async()` for semantic scoring |
| `RedisCache` | `src/core/redis_cache.py` | Feedback storage & embedding cache |
| `get_embedding_service()` | Singleton | No initialization overhead |

# Updates

- 2026-01-27 02:00 - Created task from session analysis.
