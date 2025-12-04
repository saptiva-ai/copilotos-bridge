# Data Model Evolution Plan

This document outlines the planned evolution from the current denormalized schema
to a normalized fact/dimension model for scalability.

---

## Current State (v1.0)

### Schema

```sql
-- Single denormalized table
CREATE TABLE monthly_kpis (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    banco_norm VARCHAR(50) NOT NULL,

    -- Metrics (15+ columns)
    imor DECIMAL(10,4),
    icap DECIMAL(10,4),
    icor DECIMAL(10,4),
    cartera_comercial_total DECIMAL(18,2),
    cartera_vencida_total DECIMAL(18,2),
    reservas_etapa_todas DECIMAL(18,2),
    perdida_esperada_total DECIMAL(18,2),
    -- ... more columns

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Current indexes
CREATE INDEX idx_monthly_kpis_banco ON monthly_kpis(banco_norm);
CREATE INDEX idx_monthly_kpis_fecha ON monthly_kpis(fecha);
CREATE UNIQUE INDEX idx_monthly_kpis_banco_fecha ON monthly_kpis(banco_norm, fecha);
```

### Characteristics

| Aspect | Current State |
|--------|---------------|
| Rows | ~200 (INVEX + SISTEMA, 2017-2025) |
| Columns | 20+ metric columns |
| Query pattern | Filter by banco_norm, fecha range |
| Performance | p50 < 20ms for simple queries |

### Limitations

1. **Adding metrics**: Requires ALTER TABLE
2. **Multi-bank scale**: Wide rows become unwieldy at 50+ banks
3. **Metric metadata**: No place for units, descriptions, formatting
4. **Audit trail**: No historical tracking of value changes

---

## Target State (v2.0)

### Normalized Schema

```sql
-- =============================================================================
-- Dimension Tables
-- =============================================================================

CREATE TABLE dim_bank (
    bank_id SERIAL PRIMARY KEY,
    bank_code VARCHAR(20) NOT NULL UNIQUE,  -- 'INVEX', 'SISTEMA'
    bank_name VARCHAR(100) NOT NULL,
    bank_type VARCHAR(20),  -- 'individual', 'aggregate'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE dim_metric (
    metric_id SERIAL PRIMARY KEY,
    metric_code VARCHAR(50) NOT NULL UNIQUE,  -- 'imor', 'icap'
    metric_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(20),  -- 'ratio', 'currency', 'count'
    unit VARCHAR(20),  -- '%', 'MXN', null
    precision INT DEFAULT 2,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE dim_date (
    date_id SERIAL PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    year INT NOT NULL,
    month INT NOT NULL,
    quarter INT NOT NULL,
    month_name VARCHAR(20),
    quarter_name VARCHAR(10),
    is_current BOOLEAN DEFAULT FALSE
);

-- =============================================================================
-- Fact Table
-- =============================================================================

CREATE TABLE fact_monthly_kpi (
    fact_id SERIAL PRIMARY KEY,
    bank_id INT NOT NULL REFERENCES dim_bank(bank_id),
    metric_id INT NOT NULL REFERENCES dim_metric(metric_id),
    date_id INT NOT NULL REFERENCES dim_date(date_id),
    value DECIMAL(18,6) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(bank_id, metric_id, date_id)
);

-- =============================================================================
-- Indexes for Query Patterns
-- =============================================================================

-- Evolution queries: WHERE bank_id = X AND metric_id = Y ORDER BY date_id
CREATE INDEX idx_fact_bank_metric_date
ON fact_monthly_kpi(bank_id, metric_id, date_id);

-- Comparison queries: WHERE metric_id = X AND date_id = Y
CREATE INDEX idx_fact_metric_date
ON fact_monthly_kpi(metric_id, date_id);

-- Ranking queries: WHERE metric_id = X AND date_id = Y ORDER BY value
CREATE INDEX idx_fact_metric_date_value
ON fact_monthly_kpi(metric_id, date_id, value DESC);
```

### Benefits

| Aspect | Improvement |
|--------|-------------|
| Adding metrics | INSERT into dim_metric (no schema change) |
| Multi-bank scale | Vertical growth, not horizontal |
| Metric metadata | Full metadata in dim_metric |
| Audit trail | Can add `fact_kpi_history` table |
| Query flexibility | Star schema joins are well-optimized |

---

## Migration Strategy

### Phase 1: Parallel Tables (Low Risk)

**Duration**: 1-2 weeks

1. Create dimension tables (`dim_bank`, `dim_metric`, `dim_date`)
2. Create fact table (`fact_monthly_kpi`)
3. Create ETL job to populate both schemas
4. Validate data consistency between schemas

**Rollback**: Drop new tables, continue using `monthly_kpis`

### Phase 2: Compatibility Views (Medium Risk)

**Duration**: 1-2 weeks

1. Create view `v_monthly_kpis` that looks like old table:

```sql
CREATE VIEW v_monthly_kpis AS
SELECT
    d.full_date AS fecha,
    b.bank_code AS banco_norm,
    MAX(CASE WHEN m.metric_code = 'imor' THEN f.value END) AS imor,
    MAX(CASE WHEN m.metric_code = 'icap' THEN f.value END) AS icap,
    -- ... etc
FROM fact_monthly_kpi f
JOIN dim_bank b ON f.bank_id = b.bank_id
JOIN dim_metric m ON f.metric_id = m.metric_id
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.full_date, b.bank_code;
```

2. Update `AnalyticsService` to use view
3. Run smoke tests against view
4. Monitor performance

**Rollback**: Point `AnalyticsService` back to `monthly_kpis`

### Phase 3: Direct Fact Access (Higher Value)

**Duration**: 2-3 weeks

1. Create `MetricRepository` abstraction:

```python
class MetricRepository:
    async def get_evolution(
        self,
        bank_code: str,
        metric_code: str,
        date_start: date,
        date_end: date
    ) -> List[MetricValue]:
        ...

    async def get_comparison(
        self,
        bank_codes: List[str],
        metric_code: str,
        date: date
    ) -> List[MetricValue]:
        ...
```

2. Update `AnalyticsService` to use repository
3. Implement repository with direct fact table queries
4. Add caching layer if needed

**Rollback**: Repository switches to view-based implementation

### Phase 4: Deprecate Old Schema

**Duration**: 1 week

1. Stop writing to `monthly_kpis`
2. Monitor for any missed dependencies
3. Rename to `monthly_kpis_deprecated`
4. Drop after 30 days

---

## Performance Projections

### Current (Denormalized)

| Dataset Size | Query Time |
|--------------|------------|
| 200 rows | < 20ms |
| 2,000 rows | < 50ms |
| 20,000 rows | ~200ms (estimate) |

### Projected (Normalized + Indexes)

| Dataset Size | Query Time |
|--------------|------------|
| 200 rows | < 5ms |
| 2,000 rows | < 10ms |
| 20,000 rows | < 50ms |
| 200,000 rows | < 100ms |

**Key optimizations**:
- Composite indexes on common query patterns
- No wide row scans
- Better query planner statistics

---

## Data Volume Estimates

### Current

| Dimension | Count |
|-----------|-------|
| Banks | 2 (INVEX, SISTEMA) |
| Metrics | 15 |
| Months | 103 (2017-2025) |
| **Total fact rows** | ~3,000 |

### 1 Year Projection (5 banks)

| Dimension | Count |
|-----------|-------|
| Banks | 5 |
| Metrics | 20 |
| Months | 115 |
| **Total fact rows** | ~11,500 |

### 3 Year Projection (20 banks)

| Dimension | Count |
|-----------|-------|
| Banks | 20 |
| Metrics | 30 |
| Months | 140 |
| **Total fact rows** | ~84,000 |

**Conclusion**: Even at 3-year scale, fact table remains manageable.

---

## Implementation Checklist

### Phase 1
- [ ] Create dim_bank table and seed
- [ ] Create dim_metric table and seed
- [ ] Create dim_date table and seed
- [ ] Create fact_monthly_kpi table
- [ ] Create ETL dual-write job
- [ ] Validate row counts match

### Phase 2
- [ ] Create v_monthly_kpis view
- [ ] Update AnalyticsService to use view
- [ ] Run full smoke test suite
- [ ] Run performance benchmark
- [ ] Document any performance regressions

### Phase 3
- [ ] Define MetricRepository interface
- [ ] Implement fact-based repository
- [ ] Update AnalyticsService dependency
- [ ] Add integration tests
- [ ] Monitor production metrics

### Phase 4
- [ ] Stop dual-write to monthly_kpis
- [ ] Rename to deprecated
- [ ] Wait 30 days
- [ ] Drop deprecated table

---

## Questions for Review

1. **Timeline**: When should we start Phase 1?
2. **Banks**: Which banks are next after INVEX?
3. **Metrics**: Any new metrics planned?
4. **Audit**: Do we need historical value tracking?
5. **Performance**: What's the acceptable p95 for 10x data?

---

## References

- [Star Schema Design](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/)
- [PostgreSQL Indexing](https://www.postgresql.org/docs/current/indexes.html)
- Current schema: `src/bankadvisor/models/kpi.py`
