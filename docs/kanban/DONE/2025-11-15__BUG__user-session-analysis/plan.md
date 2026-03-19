# Plan: User Session Bug Fixes

## Overview

Plan to fix remaining bugs identified in user session analysis.

---

## Phase 1: HSBC Data Gap Investigation (ETL)

### Objective
Identify and fix gaps in HSBC historical data.

### Steps

1. **Verify data availability**
   ```sql
   -- Run on GCP PostgreSQL
   SELECT
     DATE_TRUNC('month', fecha) as month,
     COUNT(*) as records
   FROM monthly_kpis
   WHERE banco_norm = 'HSBC'
   GROUP BY 1
   ORDER BY 1;
   ```

2. **Check ETL source files**
   - Location: `etl/data/`
   - Look for HSBC data in source CSVs

3. **If gaps exist:**
   - Re-run ETL for missing periods
   - Or document as data limitation

### Files
- `etl/scripts/` - ETL scripts
- `etl/data/` - Source data

### Success Criteria
- [ ] HSBC data verified for 2019-2025
- [ ] Gaps documented or fixed

---

## Phase 2: RESERVAS Metric Mapping

### Objective
Map "reservas" to the correct database column.

### Steps

1. **Find column in database**
   ```sql
   SELECT column_name
   FROM information_schema.columns
   WHERE table_name = 'monthly_kpis'
   AND column_name ILIKE '%reserv%' OR column_name ILIKE '%provision%';
   ```

2. **Add to columns.yaml**
   ```yaml
   reservas_totales:
     column: <found_column>
     display: "Reservas Totales"
     type: currency
     description: "Provisiones preventivas totales"
   ```

3. **Add synonyms**
   ```yaml
   # In synonyms.yaml
   reservas:
     - reservas totales
     - provisiones
     - estimacion preventiva
   ```

### Files
- `plugins/bank-advisor-private/config/columns.yaml`
- `plugins/bank-advisor-private/config/synonyms.yaml`

### Success Criteria
- [ ] Column identified in database
- [ ] Mapping added to config
- [ ] Query "Dame las reservas de INVEX" works

---

## Phase 3: Ranking Queries (TOP N)

### Objective
Implement ranking queries like "Top 10 bancos con mayor IMOR".

### Steps

1. **Detect ranking intent** (already exists)
   - `spec.intent == "ranking"`

2. **Add ranking logic to analytics_service.py**
   ```python
   if spec.intent == "ranking":
       # Get latest date for each bank
       # Order by metric value DESC
       # Limit to N (default 10)
       query = (
           select(banco_norm, metric_column)
           .where(fecha == latest_fecha)
           .order_by(metric_column.desc())
           .limit(spec.ranking_limit or 10)
       )
   ```

3. **Add ranking visualization**
   - Bar chart instead of line chart
   - Horizontal bars for readability

### Files
- `plugins/bank-advisor-private/src/bankadvisor/services/analytics_service.py`
- `plugins/bank-advisor-private/src/bankadvisor/services/plotly_generator.py`

### Success Criteria
- [ ] "Top 10 bancos IMOR" returns bar chart
- [ ] Ranking respects time period if specified

---

## Phase 4: Validate

### Test Queries

```bash
# After all fixes, test these:
"Dame el imor de HSBC del 2023"
"Dame las reservas totales de INVEX"
"Dame el imor para los 10 bancos mas grandes"
"Top 5 bancos con mejor ICAP"
```

### Automated Test
Add to e2e test suite:
```python
@pytest.mark.parametrize("query,expected_status", [
    ("Dame el IMOR de HSBC", "success"),
    ("Reservas de INVEX", "success"),
    ("Top 10 bancos IMOR", "success"),
])
def test_bug_015_fixes(query, expected_status):
    result = bank_analytics(query)
    assert result["chart_status"] == expected_status
```

---

## Timeline

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1: HSBC | 2h | GCP access |
| Phase 2: RESERVAS | 30min | None |
| Phase 3: Ranking | 2h | None |
| Phase 4: Validate | 30min | All above |

---

## Risks

1. **HSBC data may not exist** - Document as limitation
2. **RESERVAS column may not exist** - Check alternative metrics
3. **Ranking may need UI changes** - Coordinate with frontend
