# Research: Metric Data Availability & NULL Values

## Problem Statement

During metric scaling audit, we observed that BBVA (and other banks) had NULL values for certain metrics when querying recent dates. This is not a bug but a data availability pattern.

## Root Cause Analysis

### 1. Different Metric Publication Schedules

The CNBV (Comisión Nacional Bancaria y de Valores) publishes different regulatory reports on different schedules:

| Report Type | Metrics | Available Since | Publication Delay |
|-------------|---------|-----------------|-------------------|
| **Boletín Estadístico** | ICAP, IMOR, Cartera Total | 2000 | ~2-3 months |
| **Portafolio de Información (IFRS9)** | PE, CT Etapas | 2022 | ~5-6 months |
| **Índices de Cobertura** | ICOR | 2017 | ~3-4 months |

### 2. Current Data Ranges (as of 2026-01-27)

```sql
SELECT
    MAX(fecha) FILTER (WHERE icap_total IS NOT NULL) as ultimo_icap,  -- 2025-10-01
    MAX(fecha) FILTER (WHERE imor IS NOT NULL) as ultimo_imor,        -- 2025-10-01
    MAX(fecha) FILTER (WHERE pe_total IS NOT NULL) as ultimo_pe,      -- 2025-07-01
    MAX(fecha) FILTER (WHERE icor IS NOT NULL) as ultimo_icor         -- 2025-09-01
FROM bank_fact_kpis_mensual k
JOIN bank_dim_periodo p ON k.periodo_id = p.periodo_id;
```

### 3. IFRS9 Metrics (PE, CT) Only Since 2022

The "Pérdida Esperada" (PE) and "Cartera por Etapas" (CT) metrics are part of IFRS9 accounting standards that were adopted in Mexico in 2022. Before that date, these metrics simply don't exist.

## Impact on User Experience

When a user asks "Dame el PE de BBVA" and the system queries the latest available date (Oct 2025), the PE column will be NULL because the latest PE data is from July 2025.

Current behavior:
- Chart may show incomplete data or error
- User doesn't understand why data is missing
- No indication of data freshness

## Proposed Improvements

### Option A: Data Freshness Awareness in Response (Recommended)

Add metadata to chart responses indicating data availability:

```python
# In chart response
{
    "metric_name": "PE_TOTAL",
    "data_freshness": {
        "latest_available": "2025-07-01",
        "requested_range": "2025-01-01 to 2025-10-01",
        "data_gap_months": 3,
        "note": "Los datos de Pérdida Esperada se publican con ~5 meses de retraso"
    }
}
```

**Implementation location:** `plugins/bank-advisor-private/src/bankadvisor/services/chart_formatter.py`

### Option B: Automatic Date Range Adjustment

When querying metrics with known delays, automatically adjust the date range:

```python
METRIC_PUBLICATION_DELAYS = {
    "pe_total": 5,      # 5 months delay
    "ct_etapa_1": 5,
    "ct_etapa_2": 5,
    "ct_etapa_3": 5,
    "icor": 4,          # 4 months delay
    "icap_total": 3,    # 3 months delay
    "imor": 3,
}

def adjust_date_range(metric: str, end_date: date) -> date:
    delay = METRIC_PUBLICATION_DELAYS.get(metric, 3)
    return end_date - relativedelta(months=delay)
```

**Implementation location:** `plugins/bank-advisor-private/src/bankadvisor/services/template_sql_generator.py`

### Option C: Proactive User Notification

Add a system message when metrics have significant data gaps:

```
📊 Nota: Los datos de Pérdida Esperada (PE) están disponibles hasta julio 2025.
La CNBV publica estos reportes con aproximadamente 5 meses de retraso.
```

**Implementation location:** `plugins/bank-advisor-private/src/bankadvisor/services/response_builder.py`

## Recommendation

**Implement Option A + C combined:**

1. Add `data_freshness` metadata to all chart responses
2. Display a subtle notification when data gap > 2 months
3. Don't auto-adjust dates (user should know the limitation)

### Implementation Steps

1. Create `MetricAvailabilityService` to track latest available dates per metric
2. Add `data_freshness` field to `BankChartData` schema
3. Update `ChartFormatter` to include freshness info
4. Update frontend to display freshness indicator (optional badge)

### Database Query for Freshness Check

```sql
-- Get latest available date per metric
CREATE OR REPLACE VIEW bank_view_metric_freshness AS
SELECT
    'icap_total' as metric,
    MAX(p.fecha) as latest_date
FROM bank_fact_kpis_mensual k
JOIN bank_dim_periodo p ON k.periodo_id = p.periodo_id
WHERE k.icap_total IS NOT NULL
UNION ALL
SELECT 'pe_total', MAX(p.fecha)
FROM bank_fact_kpis_mensual k
JOIN bank_dim_periodo p ON k.periodo_id = p.periodo_id
WHERE k.pe_total IS NOT NULL
-- ... etc for other metrics
;
```

## Files to Modify

| File | Change |
|------|--------|
| `services/chart_formatter.py` | Add data_freshness to response |
| `services/template_sql_generator.py` | Query freshness before generating SQL |
| `schemas/bank_chart.py` | Add DataFreshness model |
| `config/synonyms.yaml` | Add publication_delay per metric |

## Acceptance Criteria

- [ ] User sees notification when data is >2 months old
- [ ] Chart response includes `data_freshness` metadata
- [ ] No changes to existing functionality
- [ ] Tests updated for new behavior
