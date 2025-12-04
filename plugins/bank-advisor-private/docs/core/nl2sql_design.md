# NL2SQL Architecture Design - BankAdvisor Plugin

## Executive Summary

This document describes the architecture for upgrading BankAdvisor's NL2SQL capabilities from basic intent→SQL mapping to a robust RAG-enhanced query pipeline.

**Goal**: Enable natural language queries like:
- "¿Cuál fue el IMOR de INVEX en los últimos 3 meses?"
- "Compara la cartera comercial de INVEX vs Banorte en 2024"
- "Muéstrame el ICOR del sistema bancario en el último trimestre"

**Constraints**:
- MUST NOT break existing happy path (IMOR, cartera comercial, ICOR)
- MUST maintain security (SQL injection prevention)
- MUST be honest about schema limitations (some metrics lack DB columns)

---

## Current State Analysis

### Existing Components

1. **IntentService** (`services/intent_service.py`)
   - Maps queries → section IDs (31 intents from `sections.yaml`)
   - Uses keyword matching + fuzzy search
   - Returns `AmbiguityResult` for disambiguation

2. **AnalyticsService** (`services/analytics_service.py`)
   - Hardcoded SQL templates per metric
   - Whitelist validation (`SAFE_METRIC_COLUMNS`)
   - TOPIC_MAP for basic NL recognition

3. **VisualizationService** (`services/visualization_service.py`)
   - Generates Plotly configs from query results

4. **Database Schema** (`models/kpi.py`)
   - Single table: `monthly_kpis`
   - Columns: 15+ metrics (cartera_total, imor, icor, etc.)
   - Dimensions: `fecha`, `institucion`, `banco_norm`
   - **Known gaps**: `icap_total`, `tda_cartera_total`, `tasa_mn`, `tasa_me` exist in model but NOT in PostgreSQL

5. **OctaviOS Infrastructure**
   - Qdrant vector DB (`rag_documents` collection)
   - Embedding service (paraphrase-multilingual-MiniLM-L12-v2, 384 dims)
   - Saptiva LLM client (for NL processing)

### Current Limitations

1. **No time range parsing**: "últimos 3 meses", "2024", "último trimestre" ignored
2. **No bank recognition**: "INVEX", "Banorte" not extracted
3. **No comparison queries**: Can't compare multiple banks
4. **Rigid SQL**: Intent → fixed SQL template (no dynamic generation)
5. **Schema gaps**: Several metrics in whitelist but missing in DB

---

## Proposed Architecture

### Pipeline Overview

```
User Query
    ↓
┌─────────────────────────────────────┐
│ 1. INTENT CLASSIFICATION            │
│    (IntentService - existing)       │
│    Output: metric_hint, mode_hint   │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 2. NL → SPEC PARSER                 │
│    (new: QuerySpecParser)           │
│    Uses: Saptiva LLM + prompts      │
│    Output: QuerySpec JSON           │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 3. RAG CONTEXT RETRIEVAL            │
│    (new: NL2SQLContextService)      │
│    Queries Qdrant for:              │
│    - Schema definitions             │
│    - Metric formulas                │
│    - Example queries                │
│    Output: RagContext               │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 4. SQL GENERATION                   │
│    (new: SqlGenerationService)      │
│    Uses: Saptiva LLM + RAG context  │
│    Output: SqlGenerationResult      │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 5. SQL VALIDATION                   │
│    (new: SqlValidator)              │
│    Checks: DDL/DML, whitelist       │
│    Output: ValidationResult         │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 6. EXECUTION & VISUALIZATION        │
│    (existing: AnalyticsService +    │
│     VisualizationService)           │
│    Output: Plotly config            │
└─────────────────────────────────────┘
```

---

## Component Specifications

### 2.1. QuerySpec (Pydantic Model)

**File**: `plugins/bank-advisor-private/src/bankadvisor/specs.py`

```python
class TimeRangeSpec(BaseModel):
    type: Literal["last_n_months", "last_n_quarters", "year", "between_dates", "all"]
    n: Optional[int] = None
    start_date: Optional[str] = None  # ISO format YYYY-MM-DD
    end_date: Optional[str] = None

class QuerySpec(BaseModel):
    metric: str  # Canonical name: "IMOR", "CARTERA_COMERCIAL", etc.
    bank_names: List[str]  # ["INVEX", "SISTEMA"], empty = all banks
    time_range: TimeRangeSpec
    granularity: Literal["month", "quarter", "year"] = "month"
    visualization_type: Literal["line", "bar", "table"] = "line"
    comparison_mode: bool = False  # True if comparing banks
    requires_clarification: bool = False
    missing_fields: List[str] = []
```

**Design rationale**:
- Explicit typing for all parameters
- Supports common time expressions
- `requires_clarification` flag for incomplete queries
- `missing_fields` for error reporting

### 2.2. QuerySpecParser

**File**: `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py`

**Function**:
```python
async def build_query_spec(
    user_query: str,
    intent_hint: Optional[str],
    mode_hint: Optional[str],
    llm_client: Any
) -> QuerySpec:
    """
    Converts NL query to structured QuerySpec using LLM.

    Steps:
    1. Extract metric from intent_hint (fallback to user_query)
    2. Call LLM with prompt template + JSON schema
    3. Parse banks: ["INVEX", "Banorte"] → ["INVEX", "SISTEMA"]
    4. Parse time: "últimos 3 meses" → TimeRangeSpec(type="last_n_months", n=3)
    5. Validate completeness

    Returns:
        QuerySpec with requires_clarification=True if incomplete
    """
```

**Prompt template**:
```
You are a banking query parser. Convert this natural language query to JSON.

Query: {user_query}
Metric hint: {intent_hint}

Available metrics: IMOR, ICOR, CARTERA_COMERCIAL, CARTERA_TOTAL, etc.
Available banks: INVEX, SISTEMA (use SISTEMA for "sistema bancario" or aggregate)

Output ONLY valid JSON matching this schema:
{schema}

Examples:
Input: "IMOR de INVEX últimos 3 meses"
Output: {"metric": "IMOR", "bank_names": ["INVEX"], "time_range": {"type": "last_n_months", "n": 3}, ...}

Input: "cartera comercial 2024"
Output: {"metric": "CARTERA_COMERCIAL", "bank_names": [], "time_range": {"type": "year", "start_date": "2024-01-01", "end_date": "2024-12-31"}, ...}
```

**Bank normalization rules**:
- "INVEX" → "INVEX"
- "Banorte", "BBVA", "Santander", etc. → Return error (not in DB)
- "sistema", "sistema bancario", "promedio" → "SISTEMA"
- Empty/unspecified → [] (all banks)

### 2.3. NL2SQL Vector Collections (Qdrant)

**New collections**:

1. **`nl2sql_schema`** (schema documentation)
   ```python
   {
       "table": "monthly_kpis",
       "column": "imor",
       "description": "Índice de Morosidad: (Etapa 3 + Castigos) / Cartera Comercial",
       "data_type": "float",
       "example_values": "1.5, 2.3, 0.8",
       "tags": ["calidad_cartera", "morosidad"]
   }
   ```

2. **`nl2sql_metrics`** (metric definitions)
   ```python
   {
       "metric_name": "IMOR",
       "formula": "(etapa_3 + castigos) / cartera_comercial",
       "columns_required": ["imor"],
       "visualization_type": "line",
       "typical_range": [0, 5],
       "description": "Mide el % de cartera en morosidad",
       "aliases": ["morosidad", "índice de morosidad"]
   }
   ```

3. **`nl2sql_examples`** (query examples)
   ```python
   {
       "nl_query": "IMOR de INVEX últimos 6 meses",
       "sql_template": "SELECT fecha, imor FROM monthly_kpis WHERE banco_norm = 'INVEX' AND fecha >= CURRENT_DATE - INTERVAL '6 months' ORDER BY fecha",
       "query_spec": {...},
       "tags": ["IMOR", "time_series", "single_bank"]
   }
   ```

**Population strategy**:
- Initial seed: Manual CSV/JSON files loaded during deployment
- Future: Auto-extract from `sections.yaml` + database introspection
- Versioning: Tag vectors with schema version for migrations

### 2.4. NL2SQLContextService

**File**: `plugins/bank-advisor-private/src/bankadvisor/services/nl2sql_context_service.py`

```python
class RagContext(BaseModel):
    metric_definitions: List[Dict[str, Any]]
    schema_snippets: List[Dict[str, Any]]
    example_queries: List[Dict[str, Any]]
    available_columns: List[str]

async def rag_context_for_spec(
    spec: QuerySpec,
    qdrant_client: QdrantClient,
    embedding_service: EmbeddingService
) -> RagContext:
    """
    Retrieves relevant context for SQL generation.

    Queries:
    1. Search nl2sql_metrics for spec.metric
    2. Search nl2sql_schema for required columns
    3. Search nl2sql_examples for similar queries

    Returns:
        RagContext with top-k results from each collection
    """
```

**Search strategy**:
- Embed `spec.metric + time_range description` (e.g., "IMOR últimos 3 meses")
- Top 3 from each collection (similarity > 0.7)
- Filter by metric tags
- Deduplicate columns

### 2.5. SqlGenerationService

**File**: `plugins/bank-advisor-private/src/bankadvisor/services/sql_generation_service.py`

```python
class SqlGenerationResult(BaseModel):
    success: bool
    sql: Optional[str] = None
    error_code: Optional[str] = None  # "missing_columns", "unsupported_metric"
    error_message: Optional[str] = None
    used_template: bool = False  # True if template was used instead of LLM

async def build_sql_from_spec(
    spec: QuerySpec,
    context: RagContext,
    llm_client: Any
) -> SqlGenerationResult:
    """
    Generates SQL from spec + RAG context.

    Strategy:
    1. Check for pre-defined template (IMOR, cartera comercial, etc.)
    2. If no template, use LLM with strict prompt
    3. Validate all columns exist in context.available_columns
    4. Return error if metric requires missing DB columns
    """
```

**SQL templates** (for happy path):
```python
SQL_TEMPLATES = {
    ("IMOR", "last_n_months"): """
        SELECT fecha, banco_norm, imor
        FROM monthly_kpis
        WHERE banco_norm IN ({banks})
          AND fecha >= CURRENT_DATE - INTERVAL '{n} months'
        ORDER BY fecha, banco_norm
    """,
    ...
}
```

**LLM Prompt** (fallback):
```
You are a PostgreSQL SQL generator for banking analytics.

Query specification:
{spec_json}

Available schema:
{schema_snippets}

Metric definitions:
{metric_definitions}

Example queries:
{example_queries}

Generate a SELECT query that:
1. ONLY uses columns from available schema
2. Filters by bank_names if specified
3. Filters by time_range
4. Returns data for visualization
5. Orders by fecha

RULES:
- NO INSERT, UPDATE, DELETE, DROP, ALTER
- NO subqueries unless necessary
- Use proper date arithmetic
- Include LIMIT 1000 if not aggregated

Output ONLY the SQL query, no explanations.
```

### 2.6. SqlValidator

**File**: `plugins/bank-advisor-private/src/bankadvisor/services/sql_validator.py`

```python
class ValidationResult(BaseModel):
    valid: bool
    error_message: Optional[str] = None
    sanitized_sql: Optional[str] = None  # With added LIMIT if needed

def validate_sql(sql: str, allowed_tables: List[str]) -> ValidationResult:
    """
    Validates SQL for security and correctness.

    Checks:
    1. No DDL/DML keywords (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE)
    2. Only SELECT statements
    3. Only whitelisted tables (monthly_kpis)
    4. No suspicious patterns (--,  /*,  UNION, EXEC)
    5. Add LIMIT 1000 if missing and query is not aggregated

    Returns:
        ValidationResult with sanitized SQL or error
    """
```

**Validation rules**:
```python
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "EXEC", "EXECUTE", "UNION", "--", "/*"
]

ALLOWED_TABLES = ["monthly_kpis"]
```

### 2.7. Integration with _bank_analytics_impl()

**File**: `plugins/bank-advisor-private/src/main.py`

**Current flow**:
```python
async def _bank_analytics_impl(...):
    # 1. IntentService.disambiguate()
    # 2. AnalyticsService.get_dashboard_data()  # Hardcoded SQL
    # 3. VisualizationService.build_plotly_config()
```

**New flow**:
```python
async def _bank_analytics_impl(metric_or_query: str, mode: str, session: AsyncSession):
    # 1. Intent classification (existing)
    intent_result = IntentService.disambiguate(metric_or_query)

    # 2. Build QuerySpec
    spec = await QuerySpecParser.build_query_spec(
        user_query=metric_or_query,
        intent_hint=intent_result.resolved_id,
        mode_hint=mode,
        llm_client=saptiva_client
    )

    # Handle clarification
    if spec.requires_clarification:
        return {
            "error": "ambiguous_query",
            "message": f"Query is ambiguous. Please specify: {', '.join(spec.missing_fields)}"
        }

    # 3. RAG context retrieval
    context = await NL2SQLContextService.rag_context_for_spec(spec, qdrant_client, embedding_service)

    # 4. Check for missing schema
    if not context.available_columns:
        return {
            "error": "unsupported_metric",
            "message": f"Metric '{spec.metric}' requires database columns not yet available"
        }

    # 5. SQL generation
    sql_result = await SqlGenerationService.build_sql_from_spec(spec, context, saptiva_client)

    if not sql_result.success:
        return {
            "error": sql_result.error_code,
            "message": sql_result.error_message
        }

    # 6. SQL validation
    validation = SqlValidator.validate_sql(sql_result.sql, allowed_tables=["monthly_kpis"])

    if not validation.valid:
        return {
            "error": "invalid_sql",
            "message": validation.error_message
        }

    # 7. Execute SQL (existing logic)
    result = await session.execute(text(validation.sanitized_sql))
    rows = result.fetchall()

    # 8. Visualization (existing logic)
    plotly_config = VisualizationService.build_plotly_config(rows, spec)

    return {
        "data": format_data(rows),
        "plotly_config": plotly_config,
        "metadata": {...}
    }
```

---

## Schema Gaps & Mitigation

### Known Missing Columns

From database introspection:
- `icap_total` ✗ (exists in model, NOT in PostgreSQL)
- `tda_cartera_total` ✗
- `tasa_mn` ✗
- `tasa_me` ✗

### Mitigation Strategy

1. **Detection**: Check `context.available_columns` before SQL generation
2. **Error message**: Clear user-facing message
   ```
   "ICAP metric requires database columns that are not yet populated.
    Contact support to request ETL update."
   ```
3. **Documentation**: Add to `nl2sql_status_report.md`
4. **Future**: ETL migration to populate missing columns

---

## Testing Strategy

### Unit Tests

1. **QuerySpecParser**:
   - `test_parse_time_range_last_n_months()`
   - `test_parse_bank_names()`
   - `test_incomplete_query_requires_clarification()`

2. **SqlValidator**:
   - `test_reject_ddl_keywords()`
   - `test_whitelist_tables()`
   - `test_add_limit_if_missing()`

3. **SqlGenerationService**:
   - `test_use_template_for_known_queries()`
   - `test_llm_fallback_for_novel_queries()`

### Integration Tests

1. **E2E Happy Path**:
   - Input: `"IMOR de INVEX últimos 3 meses"`
   - Expected: Valid SQL + Plotly config
   - File: `tests/integration/test_nl2sql_e2e.py`

2. **E2E Unsupported Metric**:
   - Input: `"ICAP del sistema"`
   - Expected: `error="unsupported_metric"`

3. **E2E Ambiguous Query**:
   - Input: `"cartera"`
   - Expected: `requires_clarification=True`

---

## Rollout Plan

### Phase 1: Foundation (Week 1)
- [ ] Implement QuerySpec models
- [ ] Implement QuerySpecParser (basic)
- [ ] Unit tests for parser

### Phase 2: RAG Integration (Week 2)
- [ ] Create Qdrant collections (nl2sql_schema, nl2sql_metrics, nl2sql_examples)
- [ ] Seed initial data (50 examples)
- [ ] Implement NL2SQLContextService
- [ ] Unit tests for RAG retrieval

### Phase 3: SQL Generation (Week 3)
- [ ] Implement SqlValidator
- [ ] Implement SqlGenerationService (templates first)
- [ ] Integration tests (E2E)

### Phase 4: Integration (Week 4)
- [ ] Wire into `_bank_analytics_impl()`
- [ ] Regression tests (ensure IMOR/cartera/ICOR still work)
- [ ] Documentation + status report

---

## Success Criteria

1. **Backward compatibility**: IMOR, cartera comercial, ICOR continue working
2. **New capabilities**:
   - Parse time ranges ("últimos 3 meses", "2024")
   - Recognize banks ("INVEX", "SISTEMA")
   - Handle comparisons (multiple banks)
3. **Error handling**:
   - Clear errors for unsupported metrics (ICAP, etc.)
   - Disambiguation for ambiguous queries
4. **Security**: No SQL injection, validated queries only
5. **Tests**: >80% coverage for new code

---

## Future Enhancements

1. **Multi-table support**: When fact/dim tables are added
2. **Custom aggregations**: "average IMOR by quarter"
3. **Filters**: "IMOR where > 2%"
4. **Exports**: CSV/Excel generation
5. **Caching**: Store generated SQL for common queries
6. **Feedback loop**: Learn from user corrections

---

## Appendix: File Structure

```
plugins/bank-advisor-private/
├── src/bankadvisor/
│   ├── specs.py                    # NEW: QuerySpec models
│   ├── services/
│   │   ├── intent_service.py       # EXISTING
│   │   ├── analytics_service.py    # EXISTING (updated)
│   │   ├── visualization_service.py  # EXISTING
│   │   ├── query_spec_parser.py    # NEW
│   │   ├── nl2sql_context_service.py  # NEW
│   │   ├── sql_generation_service.py  # NEW
│   │   └── sql_validator.py        # NEW
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_query_spec_parser.py  # NEW
│   │   │   ├── test_sql_validator.py      # NEW
│   │   │   └── test_sql_generation.py     # NEW
│   │   └── integration/
│   │       └── test_nl2sql_e2e.py         # NEW
├── data/
│   ├── nl2sql_schema.jsonl         # NEW: Schema docs for Qdrant
│   ├── nl2sql_metrics.jsonl        # NEW: Metric definitions
│   └── nl2sql_examples.jsonl       # NEW: Query examples
└── docs/
    ├── nl2sql_design.md            # THIS FILE
    └── nl2sql_status_report.md     # NEW: Status/limitations
```
