# Research: Chart Year Mismatch Bug

## Status: 🔴 ROOT CAUSE IDENTIFIED

## Executive Summary

When user requests data for a specific year (e.g., "cartera en 2023"), the **text response is correct** but the **chart shows data from a different year** (usually the most recent data).

**Root Cause**: The handlers and SQL generation service ignore `QuerySpec.time_range` and hardcode `MAX(fecha)` filters.

---

## Evidence

### User Feedback (2026-02-05)

| ID | Feedback |
|----|----------|
| FDBK-0074 | "el texto de la respuesta esta bien, me da la cartera en 2023, pero la grafica no, me muestra de otro año que no pedí, en este caso de 2024" |
| FDBK-0072 | "el valor que menciona en enero 2025 (15,048.23) no corresponde al de la tabla y gráfico (15,047.93)" |

### Flow Analysis

```
User Query: "cartera de vivienda en 2023"
                ↓
┌─────────────────────────────────────────────────────────────┐
│ QuerySpecParser._extract_time_range_heuristic()             │
│ ✅ Correctly parses "2023" → TimeRangeSpec(                 │
│      type="year",                                           │
│      start_date="2023-01-01",                               │
│      end_date="2023-12-31"                                  │
│    )                                                        │
└─────────────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────────┐
│ Handler (evolucion_banco_handler, financial_handler, etc.)  │
│ ❌ DOES NOT USE spec.time_range                             │
│ → Passes no date filters to use case                        │
└─────────────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────────┐
│ SqlGenerationService._generate_extended_financieras_sql()   │
│ ❌ HARDCODES MAX(fecha):                                    │
│                                                             │
│ Line 997-998:                                               │
│ where_clauses = [                                           │
│   "fecha_corte = (SELECT MAX(fecha_corte) FROM ...)",       │
│ ]                                                           │
│                                                             │
│ Line 1105:                                                  │
│ WHERE fecha = (SELECT MAX(fecha) FROM {table})              │
└─────────────────────────────────────────────────────────────┘
                ↓
Result: Chart shows 2024 data, text says 2023
```

### Code Evidence

**1. Handlers don't pass time_range:**

```python
# evolucion_banco_handler.py:140-144
request = GrowthEvolutionRequest(
    banco=bank,
    period_type=period,
    limit=24 if bank is None else 12,  # ← No date range!
)
```

**2. SQL uses MAX(fecha):**

```python
# sql_generation_service.py:997-998
where_clauses = [
    "fecha_corte = (SELECT MAX(fecha_corte) FROM bank_fact_metricas_financieras)",
    # ← Always uses latest date, ignores spec.time_range
]
```

**3. No time_range usage in handlers:**

```bash
$ grep -r "time_range.*spec\|spec.*time_range" handlers/
# No matches found!
```

---

## Root Causes

### RC-1: Handlers Ignore spec.time_range

None of the handlers extract or pass `spec.time_range` to their use cases:
- `evolucion_banco_handler.py` - passes `limit` but not date range
- `financial_handler.py` - no date filtering
- `metricas_financieras_handler.py` - uses MAX(fecha)

### RC-2: SQL Generation Uses Hardcoded MAX(fecha)

Multiple SQL templates hardcode `MAX(fecha)`:
- `_generate_extended_financieras_sql()` - line 998
- `_generate_operational_info_sql()` - line 1105
- Various ranking queries

### RC-3: No Validation Between Text and Chart

There's no mechanism to ensure text and chart use the same time range. The LLM generates text based on the user's question (mentioning 2023), while the chart pulls from whatever the SQL returns (latest data).

---

## Files to Modify

### Priority 1: Pass time_range through handlers

| File | Changes |
|------|---------|
| `handlers/financial_handler.py` | Extract `spec.time_range`, pass to use case |
| `handlers/evolucion_banco_handler.py` | Add `start_date`/`end_date` to requests |
| `handlers/metricas_financieras_handler.py` | Use time_range filters |
| `handlers/market_share_handler.py` | Add time_range support |

### Priority 2: Fix SQL generation to use time_range

| File | Changes |
|------|---------|
| `services/sql_generation_service.py` | Replace `MAX(fecha)` with `spec.time_range` |
| Use case files | Accept and apply date filters |

### Priority 3: Add validation

| File | Changes |
|------|---------|
| `services/response_builder.py` | Validate time_range consistency |

---

## Proposed Solution

### Phase 1: Handler Changes

Add time_range extraction to all handlers:

```python
# In handler.handle():
start_date = None
end_date = None
if spec and spec.time_range:
    start_date = spec.time_range.start_date
    end_date = spec.time_range.end_date

request = EvolutionRequest(
    ...
    start_date=start_date,
    end_date=end_date,
)
```

### Phase 2: SQL Generation Changes

Replace hardcoded MAX(fecha) with parameterized filters:

```python
# Instead of:
"fecha_corte = (SELECT MAX(fecha_corte) FROM ...)"

# Use:
if spec.time_range.start_date:
    where_clauses.append(f"fecha_corte >= '{spec.time_range.start_date}'")
if spec.time_range.end_date:
    where_clauses.append(f"fecha_corte <= '{spec.time_range.end_date}'")
else:
    # Only fallback to MAX if no date specified
    where_clauses.append("fecha_corte = (SELECT MAX(fecha_corte) FROM ...)")
```

---

## Acceptance Criteria

- [ ] Query "cartera 2023" → chart shows only 2023 data
- [ ] Query "IMOR enero 2025" → chart and text show same value
- [ ] Query "evolución últimos 6 meses" → chart shows exactly 6 months
- [ ] Handlers use spec.time_range when available
- [ ] SQL generation respects time_range from spec
- [ ] E2E tests for year-specific queries

---

## Estimated Effort

| Phase | Effort | Risk |
|-------|--------|------|
| 1. Handler changes | 4h | Medium |
| 2. SQL generation changes | 3h | Medium |
| 3. Tests | 2h | Low |
| **Total** | **9h** | - |

---

## Related Issues

- `BUG-2026-01-30__wrong-month-data-mapping` - LLM confuses months (similar pattern)
- `BUG-2026-02-05__bank-code-confusion` - Similar text/data mismatch issue
