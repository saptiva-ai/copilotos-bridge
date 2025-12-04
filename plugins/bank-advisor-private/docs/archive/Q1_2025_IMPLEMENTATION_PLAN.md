# Q1 2025 Implementation Plan - BankAdvisor

**Date**: 2025-12-03
**Target**: Q1 2025 (52 hours total)
**Tasks**: RAG Feedback Loop + Consolidate Dual Pipelines

---

## Task 1: RAG Feedback Loop (16 hours)

### Objective
Implement automatic seeding of successful queries to RAG for improved relevance and reduced latency.

### Current State
- RAG seeded with **30 static examples** in `scripts/seed_nl2sql_rag.py`
- No learning from production queries
- First-time queries have lower hit rates

### Target State
- Auto-seed successful queries to RAG
- Learn from user patterns
- Expected improvements:
  - First 100 queries: -20% hit rate improvement
  - After 100 queries: +40% hit rate
  - Overall latency reduction: -30%

### Implementation Steps

#### 1.1 Query Logging Infrastructure (4 hours)

**Create**: `src/bankadvisor/services/query_logger_service.py`

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import asyncpg

@dataclass
class QueryLog:
    """Logged successful query for RAG feedback."""
    query_id: str
    user_query: str
    generated_sql: str
    banco: Optional[str]
    metric: str
    intent: str
    execution_time_ms: float
    success: bool
    error_message: Optional[str]
    timestamp: datetime

class QueryLoggerService:
    """Service for logging queries to feed RAG."""

    async def log_successful_query(
        self,
        user_query: str,
        generated_sql: str,
        spec: QuerySpec,
        execution_time_ms: float
    ):
        """
        Log successful query execution for future RAG seeding.

        Args:
            user_query: Original NL query
            generated_sql: Generated SQL that succeeded
            spec: Parsed query specification
            execution_time_ms: Query execution time
        """
        pass  # Implementation details

    async def get_recent_successful_queries(
        self,
        limit: int = 100,
        min_confidence: float = 0.8
    ) -> List[QueryLog]:
        """Retrieve recent high-confidence queries for RAG seeding."""
        pass
```

**Database Schema**:
```sql
CREATE TABLE query_logs (
    id SERIAL PRIMARY KEY,
    query_id UUID UNIQUE NOT NULL,
    user_query TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    banco VARCHAR(50),
    metric VARCHAR(100) NOT NULL,
    intent VARCHAR(50) NOT NULL,
    execution_time_ms FLOAT NOT NULL,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),

    -- RAG seeding metadata
    seeded_to_rag BOOLEAN DEFAULT FALSE,
    seed_timestamp TIMESTAMPTZ,
    query_embedding VECTOR(1536),  -- OpenAI ada-002 dimension

    -- Indexing for performance
    INDEX idx_query_logs_timestamp (timestamp DESC),
    INDEX idx_query_logs_success (success) WHERE success = TRUE,
    INDEX idx_query_logs_metric (metric),
    INDEX idx_query_logs_banco (banco)
);
```

#### 1.2 RAG Feedback Loop Service (6 hours)

**Create**: `src/bankadvisor/services/rag_feedback_service.py`

```python
class RagFeedbackService:
    """Service for feeding successful queries back to RAG."""

    def __init__(
        self,
        query_logger: QueryLoggerService,
        qdrant_client: QdrantClient,
        collection_name: str = "bankadvisor_queries"
    ):
        self.query_logger = query_logger
        self.qdrant = qdrant_client
        self.collection_name = collection_name

    async def seed_from_query_logs(
        self,
        batch_size: int = 50,
        min_age_hours: int = 1,
        max_age_days: int = 90
    ):
        """
        Seed RAG from recent successful queries.

        Args:
            batch_size: Number of queries to seed per batch
            min_age_hours: Minimum age (avoid seeding too fresh queries)
            max_age_days: Maximum age (decay old patterns)
        """
        # 1. Get recent successful queries
        queries = await self.query_logger.get_recent_successful_queries(
            limit=batch_size,
            min_age_hours=min_age_hours,
            max_age_days=max_age_days,
            not_seeded=True
        )

        # 2. Generate embeddings (batch)
        embeddings = await self._generate_embeddings_batch(
            [q.user_query for q in queries]
        )

        # 3. Upsert to Qdrant
        points = [
            {
                "id": str(uuid.uuid4()),
                "vector": embedding,
                "payload": {
                    "type": "learned_query",
                    "user_query": q.user_query,
                    "generated_sql": q.generated_sql,
                    "banco": q.banco,
                    "metric": q.metric,
                    "intent": q.intent,
                    "learned_from": q.timestamp.isoformat(),
                    "execution_time_ms": q.execution_time_ms,
                    "confidence": self._calculate_confidence(q)
                }
            }
            for q, embedding in zip(queries, embeddings)
        ]

        await self.qdrant.upsert(
            collection_name=self.collection_name,
            points=points
        )

        # 4. Mark as seeded
        await self.query_logger.mark_as_seeded([q.query_id for q in queries])

    def _calculate_confidence(self, query_log: QueryLog) -> float:
        """
        Calculate confidence score for learned query.

        Factors:
        - Execution time (faster = higher confidence)
        - Query complexity
        - Age (newer = higher confidence)
        """
        confidence = 1.0

        # Execution time factor (< 200ms = good)
        if query_log.execution_time_ms < 200:
            confidence *= 1.0
        elif query_log.execution_time_ms < 500:
            confidence *= 0.9
        else:
            confidence *= 0.7

        # Age decay (linear over 90 days)
        age_days = (datetime.now() - query_log.timestamp).days
        age_factor = max(0.5, 1.0 - (age_days / 90) * 0.5)
        confidence *= age_factor

        return confidence
```

#### 1.3 Integration with NL2SQL Pipeline (3 hours)

**Modify**: `src/bankadvisor/services/nl2sql_context_service.py`

```python
class Nl2SqlContextService:
    """Enhanced with feedback loop integration."""

    async def retrieve_context(
        self,
        spec: QuerySpec,
        top_k: int = 3
    ) -> RagContext:
        """
        Retrieve RAG context with learned queries prioritized.

        Query strategy:
        1. Search in learned_queries (type="learned_query")
        2. Search in static_examples (type="example")
        3. Merge with learned queries weighted higher
        """
        query_embedding = await self._embed_query(spec.user_query)

        # Search learned queries
        learned_results = await self.qdrant.search(
            collection_name="bankadvisor_queries",
            query_vector=query_embedding,
            query_filter={
                "must": [{"key": "type", "match": {"value": "learned_query"}}]
            },
            limit=top_k,
            score_threshold=0.75
        )

        # Search static examples
        static_results = await self.qdrant.search(
            collection_name="bankadvisor_queries",
            query_vector=query_embedding,
            query_filter={
                "must": [{"key": "type", "match": {"value": "example"}}]
            },
            limit=top_k,
            score_threshold=0.70
        )

        # Merge with learned queries prioritized
        all_results = []
        for result in learned_results:
            result.score *= 1.2  # 20% boost for learned queries
            all_results.append(result)
        all_results.extend(static_results)

        # Sort by score and take top_k
        all_results.sort(key=lambda x: x.score, reverse=True)
        top_results = all_results[:top_k]

        return self._build_context(top_results, spec)
```

**Modify**: `src/main.py` - Add logging after successful query execution

```python
async def _attempt_nl2sql_pipeline(user_query: str, mode: str):
    """Enhanced with query logging."""
    start_time = datetime.now()

    # ... existing NL2SQL pipeline code ...

    # After successful execution
    if result and result.get("success"):
        execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Log to query logger for RAG feedback
        await query_logger.log_successful_query(
            user_query=user_query,
            generated_sql=sql,
            spec=spec,
            execution_time_ms=execution_time_ms
        )

    return result
```

#### 1.4 Scheduled Feedback Job (2 hours)

**Create**: `src/bankadvisor/jobs/rag_feedback_job.py`

```python
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class RagFeedbackJob:
    """Scheduled job to seed RAG from query logs."""

    def __init__(self, feedback_service: RagFeedbackService):
        self.feedback_service = feedback_service
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Start scheduled job - runs every hour."""
        self.scheduler.add_job(
            self._run_feedback_loop,
            trigger='interval',
            hours=1,
            id='rag_feedback_loop',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("rag_feedback.job_started", interval="1h")

    async def _run_feedback_loop(self):
        """Execute feedback loop - seed last hour's queries."""
        try:
            logger.info("rag_feedback.job_running")

            await self.feedback_service.seed_from_query_logs(
                batch_size=50,
                min_age_hours=1,  # Wait 1h before seeding (ensure stability)
                max_age_days=90
            )

            logger.info("rag_feedback.job_complete")
        except Exception as e:
            logger.error("rag_feedback.job_failed", error=str(e))
```

#### 1.5 Testing & Validation (1 hour)

**Create**: `tests/unit/test_rag_feedback_service.py`

```python
import pytest
from bankadvisor.services.rag_feedback_service import RagFeedbackService

@pytest.mark.asyncio
async def test_seed_from_query_logs():
    """Test that successful queries are seeded to RAG."""
    # 1. Create test query logs
    # 2. Run feedback loop
    # 3. Verify queries seeded to Qdrant
    # 4. Verify learned queries have higher relevance
    pass

@pytest.mark.asyncio
async def test_learned_queries_prioritized():
    """Test that learned queries rank higher than static examples."""
    # 1. Seed a learned query
    # 2. Search for similar query
    # 3. Verify learned query appears in top results
    pass
```

---

## Task 2: Consolidate Dual Pipelines (8 hours)

### Objective
Remove legacy intent-based pipeline and migrate 100% to NL2SQL.

### Current State
```
User Query
    │
    ├─→ [NL2SQL Pipeline] (85% coverage) ✅
    │   ├─ QuerySpecParser
    │   ├─ Nl2SqlContextService (RAG)
    │   ├─ SqlGenerationService
    │   └─ SqlValidator
    │
    └─→ [Legacy Pipeline] (15% fallback) ❌
        ├─ EntityService (deprecated)
        ├─ IntentService (active)
        └─ AnalyticsService
```

### Target State
```
User Query
    │
    └─→ [NL2SQL Pipeline] (100% coverage) ✅
        ├─ QuerySpecParser
        ├─ Nl2SqlContextService (RAG)
        ├─ SqlGenerationService
        └─ SqlValidator
```

### Implementation Steps

#### 2.1 Coverage Analysis (1 hour)

**Create**: `scripts/analyze_pipeline_coverage.py`

```python
"""
Analyze which queries hit legacy vs NL2SQL pipeline.

Output:
- % queries handled by NL2SQL
- % queries falling back to legacy
- Types of queries that fail NL2SQL
- Action items to reach 100% coverage
"""
import asyncio
from datetime import datetime, timedelta

async def analyze_coverage():
    """Analyze query logs from last 30 days."""
    # Query query_logs table
    # Group by pipeline_used (nl2sql vs legacy)
    # Identify failure patterns

    conn = await asyncpg.connect(DATABASE_URL)

    result = await conn.fetch("""
        SELECT
            pipeline_used,
            COUNT(*) as total,
            AVG(execution_time_ms) as avg_time,
            COUNT(DISTINCT metric) as unique_metrics,
            COUNT(DISTINCT banco) as unique_bancos
        FROM query_logs
        WHERE timestamp > NOW() - INTERVAL '30 days'
        GROUP BY pipeline_used;
    """)

    print("Pipeline Coverage (Last 30 Days)")
    print("="*50)
    for row in result:
        print(f"{row['pipeline_used']}: {row['total']} queries")

    # Identify legacy-only queries
    legacy_queries = await conn.fetch("""
        SELECT user_query, COUNT(*) as frequency
        FROM query_logs
        WHERE pipeline_used = 'legacy'
          AND timestamp > NOW() - INTERVAL '30 days'
        GROUP BY user_query
        ORDER BY frequency DESC
        LIMIT 20;
    """)

    print("\nTop Legacy-Only Queries:")
    print("="*50)
    for i, row in enumerate(legacy_queries, 1):
        print(f"{i}. {row['user_query']} ({row['frequency']}x)")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(analyze_coverage())
```

#### 2.2 Extend NL2SQL to Handle Legacy Cases (3 hours)

Based on coverage analysis, extend NL2SQL to handle edge cases:

**Modify**: `src/bankadvisor/services/query_spec_parser.py`

```python
class QuerySpecParser:
    """Enhanced to handle legacy edge cases."""

    async def parse(self, user_query: str, ...) -> QuerySpec:
        """
        Parse with fallback handling for edge cases.

        New cases to handle:
        1. Multi-metric queries: "IMOR y ICOR de INVEX"
        2. Aggregation queries: "promedio de IMOR últimos 12 meses"
        3. Comparison queries: "INVEX vs SISTEMA"
        4. Range queries: "IMOR entre 0.5% y 1%"
        """
        # Try rule-based parsing first
        spec = self._rule_based_parse(user_query)

        if spec.is_complete():
            return spec

        # Fallback to LLM-based parsing for complex queries
        spec = await self._llm_parse(user_query)

        return spec
```

**Add**: Support for complex query types in SQL generation

```python
# src/bankadvisor/services/sql_generation_service.py

class SqlGenerationService:
    """Enhanced with complex query templates."""

    MULTI_METRIC_TEMPLATE = """
    SELECT
        fecha,
        banco_norm,
        {metrics}  -- e.g., "imor, icor"
    FROM monthly_kpis
    WHERE banco_norm = '{banco}'
      AND fecha >= '{date_start}'
      AND fecha <= '{date_end}'
    ORDER BY fecha;
    """

    COMPARISON_TEMPLATE = """
    SELECT
        fecha,
        banco_norm,
        {metric}
    FROM monthly_kpis
    WHERE banco_norm IN ({bancos})  -- e.g., 'INVEX', 'SISTEMA'
      AND fecha >= '{date_start}'
      AND fecha <= '{date_end}'
    ORDER BY fecha, banco_norm;
    """
```

#### 2.3 Remove Legacy Code (2 hours)

**Delete or deprecate**:
1. `src/bankadvisor/entity_service.py` (deprecated)
2. `src/bankadvisor/services/intent_service.py` (migrate to NL2SQL)
3. Legacy intent enum and constants

**Modify**: `src/main.py`

```python
# Before: Dual pipeline with fallback
async def _bank_analytics_impl(metric_or_query: str, mode: str):
    """Old implementation with legacy fallback."""
    try:
        result = await _attempt_nl2sql_pipeline(metric_or_query, mode)
        if result:
            return result
    except Exception as e:
        logger.warning("nl2sql_failed", error=str(e), falling_back_to_legacy=True)

    # FALLBACK TO LEGACY ❌
    return await _legacy_intent_pipeline(metric_or_query, mode)

# After: NL2SQL only
async def _bank_analytics_impl(metric_or_query: str, mode: str):
    """New implementation - NL2SQL only."""
    try:
        result = await _attempt_nl2sql_pipeline(metric_or_query, mode)
        if result:
            return result
        else:
            # Return structured error instead of fallback
            return {
                "success": False,
                "error": "query_not_understood",
                "message": "No pude entender tu consulta. ¿Podrías reformularla?",
                "suggestions": await _get_query_suggestions(metric_or_query)
            }
    except Exception as e:
        logger.error("nl2sql_error", error=str(e))
        return {
            "success": False,
            "error": "internal_error",
            "message": f"Error procesando consulta: {str(e)}"
        }
```

#### 2.4 Migration Script (1 hour)

**Create**: `scripts/migrate_to_nl2sql_only.py`

```python
"""
Migration script to consolidate pipelines.

Steps:
1. Backup legacy code to archive/
2. Update imports in main.py
3. Remove legacy test files
4. Update documentation
5. Run smoke tests
"""
import shutil
from pathlib import Path

def migrate():
    print("Migrating to NL2SQL-only pipeline...")

    # 1. Archive legacy code
    archive_dir = Path("archive/legacy_pipeline_2025-12-03")
    archive_dir.mkdir(parents=True, exist_ok=True)

    legacy_files = [
        "src/bankadvisor/entity_service.py",
        "src/bankadvisor/services/intent_service.py",
    ]

    for file in legacy_files:
        if Path(file).exists():
            shutil.move(file, archive_dir / Path(file).name)
            print(f"Archived: {file}")

    # 2. Update main.py imports
    print("Updating main.py...")
    # Remove legacy imports
    # Remove fallback logic

    # 3. Run tests
    print("Running smoke tests...")
    import subprocess
    result = subprocess.run(["python", "scripts/smoke_demo_bank_analytics.py"])

    if result.returncode == 0:
        print("✅ Migration complete!")
    else:
        print("❌ Tests failed - rollback needed")
        # Rollback logic

if __name__ == "__main__":
    migrate()
```

#### 2.5 Testing & Documentation (1 hour)

**Update**: `README.md`

```markdown
## Architecture Changes (v2.0)

**Before** (Dual Pipeline):
- 85% NL2SQL + 15% Legacy fallback
- 2 code paths to maintain

**After** (Unified):
- 100% NL2SQL
- Single code path
- 50% less technical debt
```

**Run**: Full test suite
```bash
# Smoke tests
python scripts/smoke_demo_bank_analytics.py

# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/test_nl2sql_e2e.py
```

---

## Success Metrics

### RAG Feedback Loop
- [ ] Query logs table created and populating
- [ ] 50+ learned queries seeded to RAG after 1 week
- [ ] Latency reduction: 177ms → ~120ms (30% improvement)
- [ ] RAG hit rate: +40% for frequent query patterns

### Pipeline Consolidation
- [ ] 0 queries using legacy pipeline
- [ ] Legacy code archived
- [ ] Test coverage: 100% passing
- [ ] Documentation updated
- [ ] -300 LOC removed

---

## Timeline

### Week 1 (16 hours)
- Day 1-2: RAG Feedback infrastructure (query logging + DB schema)
- Day 3: RAG Feedback service implementation
- Day 4: Integration with NL2SQL pipeline

### Week 2 (8 hours)
- Day 5: Pipeline coverage analysis
- Day 6: Extend NL2SQL for edge cases
- Day 7: Remove legacy code + migration
- Day 8: Testing + documentation

---

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| NL2SQL doesn't cover 100% | Keep legacy as emergency fallback for 1 month, then remove |
| RAG feedback creates noise | Implement confidence threshold + manual review dashboard |
| Performance regression | Monitor latency p50/p95 before/after migration |
| Breaking changes | Feature flag for gradual rollout |

---

## Next Steps

1. **Create query_logs table migration**
2. **Implement QueryLoggerService**
3. **Integrate with main.py**
4. **Deploy to staging for validation**
5. **Run coverage analysis**
6. **Execute migration script**
