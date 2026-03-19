# Research: User Session Bug Analysis

## Date: 2026-01-13

## Methodology

1. Connected to production MongoDB via SSH (`jf@${PROD_MONGO_HOST}`)
2. Extracted messages with error patterns (`no encontré`, `chart_status: empty/error`)
3. Correlated user queries with error responses
4. Analyzed bank-advisor logs for root cause

---

## Data Extraction

### MongoDB Collections Analyzed

```javascript
// Collections
- chat_sessions: 50 recent sessions
- messages: 500 recent messages
- users: all (passwords excluded)
```

### Key Queries Used

```javascript
// Find error messages
db.messages.find({
  role: "assistant",
  $or: [
    {content: /no encontr/i},
    {"metadata.bank_chart_data.chart_status": "empty"},
    {"metadata.bank_chart_data.chart_status": "error"}
  ]
})

// Correlate with user queries
db.messages.find({
  session_id: <error_session>,
  role: "user",
  created_at: {$lt: <error_time>}
}).sort({created_at: -1}).limit(1)
```

---

## User Query Patterns (2026-01-13)

### Successful Queries

```
✅ "Dame el ICAP de BBVA" → 2005.94%
✅ "¿Cuál es la cartera total de INVEX?" → 50,608M MDP
✅ "¿Qué es ICAP?" → Knowledge response
✅ "Comparativo ICAP entre Santander y BBVA" → Chart generated
✅ "Dame el imor de HSBC" → 299.09% (for current period)
```

### Failed Queries

```
❌ "Dame el imor de HSBC del 2023" → No data
❌ "Dame las reservas totales de INVEX" → Metric not found
❌ "Dame el imor para los 10 bancos mas grandes" → Ranking not implemented
❌ "Cual es la cartera hipoteca del sistema bancario?" → SISTEMA aggregation (FIXED)
❌ "cuántas tarjetas de crédito colocaron los 10 bancos" → Data unavailable
```

---

## Bug Analysis

### BUG-HSBC-GAPS: HSBC Data Inconsistency

**Evidence from logs:**
```
2026-01-13 17:48:51 hu3_nlp.success result_type=data  (current period - works)
2026-01-13 16:27:49 result_type=empty (2024 period - fails)
2026-01-13 16:27:32 result_type=empty (2023 period - fails)
```

**Hypothesis:** ETL pipeline has gaps for HSBC historical data.

**Verification needed:**
```sql
SELECT DISTINCT DATE_TRUNC('year', fecha), banco_norm
FROM monthly_kpis
WHERE banco_norm = 'HSBC'
GROUP BY 1, 2
ORDER BY 1;
```

---

### BUG-RESERVAS: Metric Not Mapped

**User query:** "Dame las reservas totales de INVEX al cierre del mes"

**Log analysis:**
```
result_type=empty
```

**Investigation needed:**
1. Check if `reservas_totales` or `estimacion_preventiva` column exists
2. Add mapping to `columns.yaml` if exists

---

### BUG-RANKING: TOP N Not Implemented

**User queries:**
```
- "Dame el imor para los 10 bancos mas grandes"
- "cuántas tarjetas de crédito colocaron los 10 bancos"
```

**Current behavior:** Returns empty because ranking intent is detected but query execution doesn't filter to TOP N.

**Fix needed:** Implement `LIMIT N` with `ORDER BY` for ranking queries.

---

## Fixed Issues (Same Day)

### FIX-1: ClarificationStrategy Refactor

**Problem:** Queries like "¿Cómo se comportó la cartera hipotecaria en 2024?" triggered clarification buttons asking for bank.

**Solution:**
- Created `ClarificationStrategy` enum (NONE, SMART_DEFAULT, SOFT_ASK, HARD_ASK)
- Evolution/comparison queries default to SISTEMA
- Removed duplicate clarification code

**Files changed:**
- `clarification_service.py`: +150 lines (new strategy logic)
- `main.py`: -40 lines (removed duplicate code)
- `BankAdvisorResponse.tsx`: +50 lines (soft-ask suggestions)

---

### FIX-2: SISTEMA Aggregation

**Problem:** `hip_cartera_vivienda_mensual` table doesn't have `banco_norm='SISTEMA'` rows.

**Solution:**
- Added dynamic `SUM() + GROUP BY` for SISTEMA queries on hip_* views
- Applied in `analytics_service.py`

---

## Session Statistics

| User ID | Sessions | Success Rate |
|---------|----------|--------------|
| 76ac87f9-* | 3 | 80% |
| 9d8f06d5-* | 15 | 60% |
| 94bca44c-* | 1 | 50% |

---

## Recommendations

### Priority 1: Data Quality
1. Audit ETL for HSBC data gaps
2. Verify all banks have complete historical data

### Priority 2: Feature Gaps
1. Implement ranking queries (TOP N)
2. Map RESERVAS metric if data exists

### Priority 3: UX Improvements
1. Better error messages for data unavailability
2. Suggest alternative time periods when data is missing
