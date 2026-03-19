# Research: REFACTOR-002 Handler & Repository Extraction

## Status: COMPLETE ✅

---

## Current State (2026-01-28)

### Architecture Already Implemented

El trabajo previo ya completó la mayoría de la extracción:

```
bankadvisor/
├── core/
│   └── pipeline.py           # PipelineContext, ValidationError
├── pipelines/
│   ├── __init__.py
│   ├── query_pipeline.py     # Orchestrator
│   ├── query_router.py       # Chain of Responsibility (267 lines) ✅
│   └── stages/
│       ├── input_validation.py   # 383 lines
│       ├── intent_detection.py   # 319 lines
│       └── time_range_resolver.py
├── handlers/                 # 16 handlers, 3,313 lines total ✅
│   ├── __init__.py
│   ├── base.py
│   ├── knowledge_handler.py      # 676 lines
│   ├── evolucion_banco_handler.py
│   ├── metricas_financieras_handler.py
│   ├── resumen_sistema_handler.py
│   ├── cartera_region_handler.py
│   ├── vivienda_perfil_handler.py
│   ├── cartera_actividad_handler.py
│   ├── cartera_tamano_handler.py
│   ├── cartera_destino_handler.py
│   ├── financial_handler.py
│   ├── multi_metric_handler.py
│   ├── market_share_handler.py
│   ├── segment_handler.py
│   ├── ranking_handler.py
│   └── comparative_handler.py
└── repositories/             # 6 repositories, 746 lines total ✅
    ├── __init__.py
    ├── base.py
    ├── column_resolver.py
    ├── kpi_repository.py
    ├── financial_repository.py
    ├── segment_repository.py
    └── operational_repository.py
```

---

## Line Count Analysis

### Current vs Target

| File | Current | Target | Gap |
|------|---------|--------|-----|
| `main.py` | 1,836 | ~200 | -1,636 |
| `analytics_service.py` | 2,525 | ~500 | -2,025 |

### What's Still in main.py (1,836 lines)

| Function | Lines | Should Move To |
|----------|-------|----------------|
| `ensure_data_populated()` | ~45 | `services/startup_service.py` |
| `lifespan()` | ~25 | Keep (app lifecycle) |
| Validation utilities | ~80 | `utils/validation.py` |
| `_handle_knowledge_query()` | ~20 | Already in KnowledgeHandler |
| `_find_bank_candidates()` | ~40 | `utils/bank_matcher.py` |
| `process_analytics_query()` | ~380 | `services/analytics_orchestrator.py` |
| `execute_bank_analytics()` | ~230 | `services/analytics_orchestrator.py` |
| `execute_sql_pipeline()` | ~300 | `services/nl2sql_service.py` |
| FastMCP tool registrations | ~150 | `mcp/tools.py` |
| API endpoints | ~200 | Keep (FastAPI routes) |
| Imports/constants | ~350 | Distributed |

### What's Still in analytics_service.py (2,525 lines)

| Function Category | Approx Lines | Should Move To |
|-------------------|--------------|----------------|
| Query building | ~500 | Repositories (partially done) |
| Data transformation | ~400 | `services/transform_service.py` |
| Visualization | ~300 | Already in `visualization_service.py` |
| Metric calculations | ~600 | `services/calculation_service.py` |
| Inline SQL templates | ~200 | `sql_templates/` |
| Orchestration logic | ~500 | Keep (reduced) |

---

## Research Questions Answered

### 1. Which handlers have the most code duplication?

**Answer**: Minimal duplication - handlers are well-factored.

| Handler | Lines | Notes |
|---------|-------|-------|
| knowledge_handler.py | 676 | Largest, but justified (glossary + RAG) |
| evolucion_banco_handler.py | 365 | Could share base with metricas_financieras |
| metricas_financieras_handler.py | 362 | Similar structure to evolucion |
| resumen_sistema_handler.py | 340 | Unique aggregation logic |

Common patterns already extracted to `base.py` (33 lines).

### 2. What's the interface contract for repository classes?

**Answer**: Defined in `repositories/base.py`:

```python
class BaseRepository:
    async def get_by_id(self, session, id) -> Optional[Model]
    async def get_many(self, session, filters, limit) -> List[Model]
    async def execute_query(self, session, query) -> List[Row]
```

All 6 repositories follow this contract.

### 3. Are there existing patterns in the codebase to follow?

**Answer**: Yes, strong patterns exist:

1. **Chain of Responsibility**: `QueryRouter` iterates handlers in priority order
2. **Strategy Pattern**: Each handler implements `matches()` + `handle()`
3. **Repository Pattern**: Data access isolated from business logic
4. **Pipeline Pattern**: `QueryPipeline` orchestrates stages
5. **Factory Pattern**: `get_query_router()`, `get_specific_handlers()`

### 4. What's the rollback strategy if migration causes regressions?

**Answer**:

1. **Feature flags**: `USE_NL2SQL_PIPELINE`, `USE_QUERY_ROUTER` env vars
2. **Fallback logic**: If router fails, falls back to legacy pipeline
3. **E2E tests**: `tests/e2e/test_bank_analytics_integration.py` covers main flows
4. **Git**: All changes are incremental commits

---

## Revised Scope for REFACTOR-002

Given that handlers and repositories are **already extracted**, the remaining work is:

### Phase 1: Extract Remaining Logic from main.py

| Task | Effort | Priority |
|------|--------|----------|
| Move `execute_sql_pipeline()` → `services/nl2sql_service.py` | Medium | P1 |
| Move orchestration → `services/analytics_orchestrator.py` | Medium | P1 |
| Move validation utils → `utils/validation.py` | Small | P2 |
| Move MCP tools → `mcp/tools.py` | Small | P2 |

### Phase 2: Slim Down analytics_service.py

| Task | Effort | Priority |
|------|--------|----------|
| Move data transforms → `services/transform_service.py` | Medium | P1 |
| Move metric calculations → `services/calculation_service.py` | Large | P2 |
| Extract SQL templates → `sql_templates/` | Small | P3 |

---

## Recommendation

**Option A**: Close REFACTOR-002 as mostly done, create new tickets for remaining extraction.

**Option B**: Re-scope REFACTOR-002 to focus only on main.py reduction (1,836 → 200).

**Option C**: Continue with full extraction of both files.

The original acceptance criteria (5 handlers, 4 repositories) is **already met**.
