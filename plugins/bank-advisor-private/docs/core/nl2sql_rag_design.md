# NL2SQL RAG Collections Design

**Author**: Senior Backend Engineer
**Date**: 2025-11-27
**Phase**: 2 (Context Service)

## Overview

This document defines the Qdrant vector database collections used to support
the BankAdvisor NL2SQL pipeline. We leverage the existing `QdrantService` and
`EmbeddingService` from the main OctaviOS backend.

## Architecture Decision

**Reuse Existing Infrastructure**: We will NOT create a parallel Qdrant client.
Instead, we'll:
1. Use the existing `QdrantService` from `apps/backend/src/services/qdrant_service.py`
2. Inject it into the BankAdvisor plugin via dependency injection
3. Create separate collections with prefix `bankadvisor_` to avoid conflicts with document RAG

## Collection Schemas

### 1. `bankadvisor_schema` - Database Schema Metadata

**Purpose**: Store searchable descriptions of tables, columns, and their relationships.

**Vector Source**: Column descriptions + usage examples

**Payload Structure**:
```python
{
    "table_name": "monthly_kpis",
    "column_name": "imor",
    "data_type": "float",
    "description": "Índice de Morosidad - Ratio of non-performing loans to total portfolio",
    "metric_tags": ["quality", "risk", "npm"],  # For filtering
    "example_sql": "SELECT fecha, imor FROM monthly_kpis WHERE banco_nombre = 'INVEX'",
    "is_nullable": False,
    "typical_range": {"min": 0.0, "max": 10.0},  # For validation
    "created_at": 1732723200.0
}
```

**Sample Entries** (to be seeded):
- `imor` - Índice de Morosidad
- `icor` - Índice de Cobertura
- `cartera_total` - Total loan portfolio
- `cartera_comercial_total` - Commercial loans
- `icap_total` - Capitalization index
- `tda_cartera_total` - Portfolio deterioration rate
- `tasa_mn` - Interest rate (MXN)
- `fecha` - Date column (YYYY-MM-DD)
- `banco_nombre` - Bank name (INVEX, SISTEMA)

### 2. `bankadvisor_metrics` - Metric Definitions

**Purpose**: Store canonical metric definitions, formulas, and aliases.

**Vector Source**: Metric name + aliases + description

**Payload Structure**:
```python
{
    "metric_name": "IMOR",
    "aliases": ["morosidad", "npm", "non-performing ratio"],
    "formula": "(stage_3_loans + write_offs) / total_portfolio",
    "description": "Non-performing loan ratio - key credit risk indicator",
    "preferred_columns": ["imor"],  # Columns to use in SELECT
    "requires_banks": False,  # True if metric only makes sense with bank filter
    "typical_viz": "line",  # line, bar, table
    "example_queries": [
        "IMOR de INVEX últimos 6 meses",
        "Compara morosidad INVEX vs Sistema 2024"
    ],
    "data_status": "populated",  # populated, empty, partial
    "created_at": 1732723200.0
}
```

**Sample Entries**:
- IMOR (populated)
- ICOR (populated)
- CARTERA_COMERCIAL (populated)
- CARTERA_TOTAL (populated)
- ICAP (populated)
- TDA (populated)
- TASA_MN (populated)
- TASA_ME (empty - no data, should return clarification)

### 3. `bankadvisor_examples` - NL→SQL Examples

**Purpose**: Store few-shot examples of NL queries → QuerySpec → SQL.

**Vector Source**: Natural language query text

**Payload Structure**:
```python
{
    "natural_language": "IMOR de INVEX últimos 3 meses",
    "query_spec": {
        "metric": "IMOR",
        "bank_names": ["INVEX"],
        "time_range": {"type": "last_n_months", "n": 3},
        "granularity": "month",
        "visualization_type": "line"
    },
    "sql": """
        SELECT fecha, imor
        FROM monthly_kpis
        WHERE banco_nombre = 'INVEX'
          AND fecha >= (CURRENT_DATE - INTERVAL '3 months')
        ORDER BY fecha ASC
        LIMIT 1000
    """,
    "notes": "Standard time-series query with single bank filter",
    "complexity": "simple",  # simple, medium, complex
    "created_at": 1732723200.0
}
```

**Sample Entries**:
1. Simple metric + bank + time: "IMOR de INVEX últimos 3 meses"
2. Comparison query: "Compara cartera comercial INVEX vs Sistema 2024"
3. Aggregation: "ICOR promedio de INVEX en 2024"
4. Multi-metric (future): "IMOR e ICOR de INVEX"
5. No time filter: "Cartera total de INVEX histórica"

## Seeding Strategy

### Initial Seed (MVP)
- **Schema**: 15 core columns from `MonthlyKPI` model
- **Metrics**: 8 metrics (IMOR, ICOR, CARTERA_*, ICAP, TDA, TASA_MN)
- **Examples**: 10-15 hand-crafted examples covering common patterns

### Seeding Script Location
- `plugins/bank-advisor-private/scripts/seed_nl2sql_rag.py`

### Seed Execution
```bash
# From plugin root
python -m scripts.seed_nl2sql_rag --env production
```

## RAG Retrieval Strategy

### Context Building for a QuerySpec

Given a `QuerySpec` with:
- `metric="IMOR"`
- `bank_names=["INVEX"]`
- `time_range=TimeRangeSpec(type="last_n_months", n=3)`

**Step 1**: Build search queries
```python
# Query 1: Metric definition
metric_query = f"{spec.metric} {' '.join(spec.bank_names)} banking metric"

# Query 2: Schema columns
schema_query = f"{spec.metric} monthly_kpis database column"

# Query 3: Similar examples
example_query = original_nl_query  # User's original text
```

**Step 2**: Retrieve from Qdrant
```python
# Search metric collection
metric_defs = qdrant.search(
    collection_name="bankadvisor_metrics",
    query_vector=embedding_service.encode_single(metric_query),
    top_k=3,
    score_threshold=0.7
)

# Search schema collection
schema_snippets = qdrant.search(
    collection_name="bankadvisor_schema",
    query_vector=embedding_service.encode_single(schema_query),
    top_k=5,
    score_threshold=0.7
)

# Search examples
examples = qdrant.search(
    collection_name="bankadvisor_examples",
    query_vector=embedding_service.encode_single(example_query),
    top_k=3,
    score_threshold=0.75  # Higher threshold for examples
)
```

**Step 3**: Build `RagContext`
```python
RagContext(
    metric_definitions=[hit.payload for hit in metric_defs],
    schema_snippets=[hit.payload for hit in schema_snippets],
    example_queries=[hit.payload for hit in examples],
    available_columns=list(AnalyticsService.SAFE_METRIC_COLUMNS.keys())
)
```

## Fallback Strategy

If Qdrant is unavailable or returns no results:

```python
# Hardcoded minimal context from AnalyticsService
RagContext(
    metric_definitions=[],
    schema_snippets=[],
    example_queries=[],
    available_columns=list(AnalyticsService.SAFE_METRIC_COLUMNS.keys())
)
```

This allows SQL generation to still work using only template-based logic.

## Performance Expectations

- **Collection Sizes** (after seeding):
  - `bankadvisor_schema`: ~15 points (one per column)
  - `bankadvisor_metrics`: ~8 points (one per metric)
  - `bankadvisor_examples`: ~15 points (hand-crafted examples)
  - **Total**: ~40 points (negligible overhead)

- **Storage**: 40 points × 3 KB = ~120 KB

- **Query Latency**: <5ms per collection (Qdrant HNSW index)

- **Total RAG overhead**: ~15-20ms (3 searches + embedding generation)

## Collection Lifecycle

### Creation
- Created during plugin startup via `Nl2SqlContextService.ensure_collections()`
- Idempotent (won't recreate if exists)

### Updates
- Manual via seeding script when:
  - New columns added to `monthly_kpis`
  - New metrics become available
  - Better examples are crafted

### Deletion
- Tied to Qdrant service lifecycle
- Can be cleared via admin endpoint: `DELETE /admin/rag/clear`

## Security Considerations

1. **No User Data**: These collections contain only schema metadata, never user queries or results
2. **Read-Only Access**: Plugin only reads from these collections, never writes during normal operation
3. **Whitelist Enforcement**: RAG context is always intersected with `SAFE_METRIC_COLUMNS` before SQL generation
4. **TTL**: Points have `created_at` for manual cleanup, but no auto-expiry (static metadata)

## Future Enhancements (Phase 4+)

- [ ] User feedback loop: Store successful queries as new examples
- [ ] Query complexity scoring: Use retrieval scores to predict SQL generation success
- [ ] Multi-lingual support: Add English descriptions and queries
- [ ] Dynamic schema discovery: Auto-sync with DB schema changes
