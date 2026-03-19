---
id: "TASK-2026-01-27__data-freshness-awareness"
title: "Add Data Freshness Awareness to Bank Advisor Responses"
status: "DONE"
phase: "Validate"
priority: "MEDIUM"
scope_in:
  - "Add data_freshness metadata to chart responses"
  - "Display notification when data gap > 2 months"
  - "Track latest available date per metric"
scope_out:
  - "Auto-adjusting date ranges"
  - "Frontend UI changes (optional future work)"
  - "Data ingestion pipeline changes"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "python tests/e2e/conversation/test_cartera_vivienda_suite.py"
pr_files: []
test_status: "pending"
related_tasks:
  - "TASK-2026-01-27__metric-scaling-audit"
---

# Summary

- **Objective:** Make bank advisor aware of data publication delays and inform users when metrics have stale or unavailable data
- **Constraints:** No breaking changes, backward compatible

# Problem

Different CNBV regulatory reports have different publication schedules:

| Metric | Publication Delay | Latest Data (as of 2026-01) |
|--------|-------------------|----------------------------|
| ICAP, IMOR | ~3 months | Oct 2025 |
| ICOR | ~4 months | Sep 2025 |
| PE, CT (IFRS9) | ~5-6 months | Jul 2025 |

When users query for recent data on metrics like PE (Pérdida Esperada), they get NULL values with no explanation.

# Proposed Solution

## Phase 1: Response Metadata (MVP)

Add `data_freshness` to chart responses:

```json
{
  "metric_name": "PE_TOTAL",
  "data_freshness": {
    "metric": "pe_total",
    "latest_available": "2025-07-01",
    "publication_delay_months": 5,
    "is_stale": true,
    "note_es": "Datos disponibles hasta julio 2025 (publicación con ~5 meses de retraso)"
  }
}
```

## Phase 2: User Notification

When `is_stale` is true, include a note in the response:

```
📊 Nota: Los datos de Pérdida Esperada están disponibles hasta julio 2025.
```

# Implementation Plan

## Files to Create/Modify

1. **New:** `services/metric_freshness_service.py`
   - Track latest available date per metric
   - Cache freshness data (refresh every hour)

2. **Modify:** `schemas/bank_chart.py`
   - Add `DataFreshness` Pydantic model
   - Add `data_freshness` field to `BankChartData`

3. **Modify:** `config/synonyms.yaml`
   - Add `publication_delay_months` per metric

4. **Modify:** `services/chart_formatter.py`
   - Include freshness info in chart response

5. **Modify:** `services/response_builder.py`
   - Add staleness note to response text

# Acceptance Criteria

- [x] Chart responses include `data_freshness` metadata
- [x] User sees notification when metric data is >2 months stale
- [x] Freshness is checked against actual DB data, not hardcoded dates
- [x] No performance impact (freshness cached with 1-hour TTL)
- [ ] All existing tests pass (pending validation)
- [ ] New unit tests for freshness service (future enhancement)

# Technical Notes

## Freshness Query (to be cached)

```sql
SELECT
    'pe_total' as metric,
    MAX(p.fecha) as latest_date,
    5 as expected_delay_months
FROM bank_fact_kpis_mensual k
JOIN bank_dim_periodo p ON k.periodo_id = p.periodo_id
WHERE k.pe_total IS NOT NULL
UNION ALL
-- ... other metrics
```

## Configuration in synonyms.yaml

```yaml
metrics:
  pe_total:
    display_name: "Pérdida Esperada Total"
    column: "pe_total"
    type: "ratio"
    publication_delay_months: 5
    freshness_note: "Reportes IFRS9 publicados con ~5 meses de retraso"
```

# Updates
- 2026-01-27 - Created from metric-scaling-audit research findings
- 2026-01-27 - Implementation completed

# Implementation Summary

## Files Created

1. **`plugins/bank-advisor-private/src/bankadvisor/services/metric_freshness_service.py`**
   - `MetricFreshnessService` singleton with 1-hour cache
   - `METRIC_PUBLICATION_DELAYS` dict with expected delays per metric
   - `FRESHNESS_QUERY` SQL to get latest dates from DB
   - `get_freshness()` and `get_freshness_dict()` methods

## Files Modified

1. **`apps/backend/src/schemas/bank_chart.py`**
   - Added `DataFreshness` Pydantic model
   - Added `data_freshness` optional field to `BankChartData`

2. **`plugins/bank-advisor-private/config/synonyms.yaml`**
   - Added `publication_delay_months` to IFRS9 metrics:
     - imor: 3, icap_total: 3, icor: 4
     - pe_total, pe_empresarial, pe_consumo, pe_vivienda: 5
     - ct_etapa_1, ct_etapa_2, ct_etapa_3: 5

3. **`plugins/bank-advisor-private/src/bankadvisor/services/chart_formatter.py`**
   - Imported `get_metric_freshness_service`
   - Added `_get_data_freshness()` helper method
   - Updated `format_evolution()`, `format_ranking()`, `format_yoy_comparison()`, `build_financial_ranking_response()` to include `data_freshness` in responses

## Response Format

```json
{
  "metric_name": "Pérdida Esperada Total",
  "data_as_of": "2025-07-01",
  "data_freshness": {
    "metric": "pe_total",
    "latest_available": "2025-07-01",
    "publication_delay_months": 5,
    "is_stale": true,
    "staleness_months": 6,
    "note_es": "Datos disponibles hasta julio 2025 (publicación con ~5 meses de retraso)",
    "note_en": "Data available up to July 2025 (published with ~5 months delay)"
  }
}
```

## Feedback Vinculado

**1 reporte(s)** de usuarios en producción.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0020 | `7f5aa3b9` | me puedes actializar la grafica a noviembre 2025ç | Los datos de noviembre, no estan disponibles aun | 2026-02-03 |

<details>
<summary>Detalle completo de feedbacks</summary>

### FDBK-0020
- **User**: `7f5aa3b9-8f98-459e-abc2-0148b23486f9`
- **Conversation**: `145839a6-bf94-43d7-af63-9a30f55ec526`
- **Message**: `ff428da9-1083-4988-9e85-e7227f51a890`
- **Rating**: 👎
- **Query**: "me puedes actializar la grafica a noviembre 2025ç"
- **Feedback**: "Los datos de noviembre, no estan disponibles aun"
- **Fecha**: 2026-02-03T17:44:44.429Z

</details>
