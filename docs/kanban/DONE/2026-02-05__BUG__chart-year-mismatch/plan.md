# Plan: Fix Chart Year Mismatch Bug

## Objective

Ensure that when users request data for a specific time period (year, month, date range), **both the text response AND the chart** show data from that same period.

---

## Phase 1: Pass time_range Through Handlers

### 1.1 Update Handler Base Class

**File**: `plugins/bank-advisor-private/src/bankadvisor/handlers/base.py`

Add helper method to extract time_range from spec:

```python
def _extract_time_range(self, spec: Optional[QuerySpec]) -> Tuple[Optional[str], Optional[str]]:
    """Extract start_date and end_date from QuerySpec.time_range."""
    if not spec or not spec.time_range:
        return None, None
    return spec.time_range.start_date, spec.time_range.end_date
```

### 1.2 Update Financial Handler

**File**: `plugins/bank-advisor-private/src/bankadvisor/handlers/financial_handler.py`

```python
async def handle(self, session, user_query, entities=None, spec=None):
    start_date, end_date = self._extract_time_range(spec)
    
    request = FinancialMetricsRequest(
        metric=detected_metric,
        banks=banks,
        start_date=start_date,  # NEW
        end_date=end_date,      # NEW
    )
```

### 1.3 Update Metricas Financieras Handler

**File**: `plugins/bank-advisor-private/src/bankadvisor/handlers/metricas_financieras_handler.py`

Pass time_range to the use case or repository call.

### 1.4 Update Evolution Handler

**File**: `plugins/bank-advisor-private/src/bankadvisor/handlers/evolucion_banco_handler.py`

```python
request = GrowthEvolutionRequest(
    banco=bank,
    period_type=period,
    start_date=spec.time_range.start_date if spec and spec.time_range else None,
    end_date=spec.time_range.end_date if spec and spec.time_range else None,
)
```

---

## Phase 2: Update Use Cases to Accept Date Filters

### 2.1 Update Financial Metrics Use Case

**File**: `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/financial_metrics.py`

Add `start_date` and `end_date` to request DTO and apply in SQL query.

### 2.2 Update Growth Evolution Use Case

**File**: `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/growth_evolution.py`

Already supports `start_date`/`end_date` - verify it's being used correctly.

---

## Phase 3: Fix SQL Generation Service

### 3.1 Replace MAX(fecha) with Parameterized Filters

**File**: `plugins/bank-advisor-private/src/bankadvisor/services/sql_generation_service.py`

**Lines 997-1002** - `_generate_extended_financieras_sql()`:

```python
# BEFORE:
where_clauses = [
    "fecha_corte = (SELECT MAX(fecha_corte) FROM bank_fact_metricas_financieras)",
]

# AFTER:
where_clauses = []
if spec.time_range and spec.time_range.start_date:
    where_clauses.append(f"fecha_corte >= '{spec.time_range.start_date}'")
if spec.time_range and spec.time_range.end_date:
    where_clauses.append(f"fecha_corte <= '{spec.time_range.end_date}'")

# Fallback to MAX only if no time_range specified
if not where_clauses:
    where_clauses.append(
        "fecha_corte = (SELECT MAX(fecha_corte) FROM bank_fact_metricas_financieras)"
    )
```

**Lines 1100-1109** - `_generate_operational_info_sql()`:

Same pattern - replace hardcoded MAX with conditional logic.

---

## Phase 4: Testing

### 4.1 Unit Tests

**File**: `plugins/bank-advisor-private/tests/unit/handlers/test_time_range_propagation.py` (NEW)

```python
@pytest.mark.asyncio
async def test_financial_handler_passes_time_range():
    spec = QuerySpec(
        metric="ACTIVO_TOTAL",
        time_range=TimeRangeSpec(type="year", start_date="2023-01-01", end_date="2023-12-31")
    )
    # Verify handler passes dates to use case
    ...

@pytest.mark.asyncio
async def test_sql_generation_uses_time_range():
    spec = QuerySpec(
        metric="ACTIVO_TOTAL",
        time_range=TimeRangeSpec(type="year", start_date="2023-01-01", end_date="2023-12-31")
    )
    result = service._generate_extended_financieras_sql(spec, config)
    assert "2023-01-01" in result.sql
    assert "MAX(fecha_corte)" not in result.sql
```

### 4.2 E2E Tests

**File**: `tests/e2e/regression/test_chart_year_mismatch.py` (NEW)

```python
YEAR_MISMATCH_TESTS = [
    {"query": "cartera de vivienda en 2023", "expected_year": "2023"},
    {"query": "IMOR de enero 2025", "expected_month": "2025-01"},
    {"query": "activos totales 2024", "expected_year": "2024"},
]

@pytest.mark.parametrize("test_case", YEAR_MISMATCH_TESTS)
async def test_chart_matches_requested_year(test_case):
    response = await call_bank_advisor(test_case["query"])
    chart_data = response.get("chart_data", {})
    
    # Extract dates from chart
    chart_dates = extract_dates_from_plotly(chart_data)
    
    # Verify all dates match expected year
    for date in chart_dates:
        assert date.startswith(test_case["expected_year"])
```

---

## Implementation Order

| Step | File | Change | Risk |
|------|------|--------|------|
| 1 | `handlers/base.py` | Add `_extract_time_range()` helper | Low |
| 2 | `handlers/financial_handler.py` | Pass time_range to use case | Medium |
| 3 | `handlers/metricas_financieras_handler.py` | Pass time_range | Medium |
| 4 | `handlers/evolucion_banco_handler.py` | Pass time_range | Medium |
| 5 | `services/sql_generation_service.py` | Replace MAX(fecha) logic | High |
| 6 | Unit tests | Add time_range propagation tests | Low |
| 7 | E2E tests | Add year mismatch tests | Low |

---

## Rollback Plan

If issues occur:
1. Revert handler changes (restore original calls without date params)
2. Revert SQL generation (restore MAX(fecha) logic)
3. Date parameters are optional, so partial rollback is safe

---

## Acceptance Criteria

- [ ] "cartera 2023" → chart shows **only** 2023 data
- [ ] "IMOR enero 2025" → chart and text show **same** values
- [ ] "evolución últimos 6 meses" → chart shows **exactly** 6 months
- [ ] All handlers extract and pass `spec.time_range`
- [ ] SQL generation uses time_range when provided, MAX(fecha) as fallback
- [ ] Unit tests pass for time_range propagation
- [ ] E2E tests verify chart matches requested period
