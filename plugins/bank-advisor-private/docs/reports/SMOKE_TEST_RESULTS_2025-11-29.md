# Smoke Test Results - Pre-Demo Validation
**Date:** 2025-11-29
**Target:** BankAdvisor Analytics System (HU3 Pipeline)
**Demo Date:** 2025-12-03

---

## Executive Summary

**Overall Status:** 🟡 **PARTIAL PASS** (40% success rate)

The BankAdvisor system is **operational** with the HU3 NLP pipeline working for basic queries. However, **6 out of 10 demo queries are failing**, requiring fixes before the December 3rd demo.

### Quick Stats
- **Server Health:** ✅ Healthy
- **Database:** ✅ 206 records loaded (2018-01 to 2025-07)
- **Unit Tests:** ✅ 14/14 passing (100%)
- **Smoke Tests:** ⚠️ 4/10 passing (40%)
- **Configuration:** ✅ synonyms.yaml and visualizations.yaml loaded

---

## Test Results Breakdown

### ✅ PASSING (4/10)

| ID | Query | Duration | Status |
|----|-------|----------|--------|
| Q1 | IMOR de INVEX en 2024 | ~2500ms | ✅ PASS |
| Q4 | Reservas totales de INVEX | ~1200ms | ✅ PASS |
| Q7 | ICOR de INVEX 2024 | ~1800ms | ✅ PASS |
| Q10 | cartera (ambiguous) | ~800ms | ✅ PASS (clarification) |

**Analysis:** Simple single-metric queries work correctly when:
- Metric is clearly specified (IMOR, ICOR, Reservas)
- Bank is explicitly mentioned (INVEX)
- Date range is specific (2024)

---

### ❌ FAILING (6/10)

| ID | Query | Error | Category |
|----|-------|-------|----------|
| Q2 | Cartera comercial de INVEX vs sistema | Empty data | Comparison |
| Q3 | Cartera comercial sin gobierno | Multi-metric detection | Entity Detection |
| Q5 | ICAP de INVEX contra sistema en 2024 | Empty data | Comparison |
| Q6 | Cartera vencida en 2024 | Asks for clarification | Entity Detection |
| Q8 | Evolución del IMOR en 2024 | Asks for clarification | Entity Detection |
| Q9 | Compara IMOR de INVEX vs sistema | Empty data | Comparison |

#### **Issue 1: Comparison Queries Failing (Q2, Q5, Q9)**
**Symptoms:** Queries with "vs sistema" or "contra sistema" return `{"type": "empty"}`

**Root Cause (Hypothesis):**
- EntityService may not be detecting "sistema" as a valid bank entity
- OR comparison logic in AnalyticsService isn't implemented yet
- OR bank name "sistema" doesn't exist in monthly_kpis table

**Example Response:**
```json
{
  "data": {
    "type": "empty",
    "message": "No hay datos disponibles para el rango de fechas seleccionado"
  }
}
```

**Recommendation:** Check if `bank_name = 'sistema'` exists in database. If not, add entity recognition for "sistema" as aggregate/average.

---

#### **Issue 2: Entity Detection Defaults (Q6, Q8)**
**Symptoms:** Queries that should default to INVEX ask for bank clarification

**Examples:**
- Q6: "Cartera vencida en 2024" → Should default to INVEX
- Q8: "Evolución del IMOR en 2024" → Should default to INVEX

**Root Cause:** EntityService requires explicit bank mention, no smart defaults

**Expected Behavior:**
When no bank is mentioned but metric + date are clear, system should:
1. Default to INVEX (primary bank)
2. OR return data for all banks as multi-line chart
3. NOT ask for clarification

**Recommendation:** Add default bank logic to EntityService or adjust clarification threshold.

---

#### **Issue 3: Multi-Metric Detection (Q3)**
**Symptoms:** "Cartera comercial sin gobierno" triggers multi-metric clarification

**Root Cause:**
- "sin gobierno" isn't recognized as a metric modifier
- System detects both "cartera_comercial_total" AND "entidades_gubernamentales_total"
- Triggers multi-metric clarification instead of calculation

**Expected Behavior:**
"Cartera comercial sin gobierno" should map to:
```yaml
metric: cartera_comercial_sin_gob
calculation: cartera_comercial_total - entidades_gubernamentales_total
```

**Status in synonyms.yaml:** ✅ Metric IS defined with `calculation: "subtract:entidades_gubernamentales_total"`

**Recommendation:** Check if AnalyticsService correctly handles `calculation` field from metric config.

---

## Infrastructure Status

### ✅ What's Working

1. **Docker Services**
   - bank-advisor-mcp container: Running
   - postgres container: Running
   - Health endpoint: Responding correctly

2. **Database**
   - monthly_kpis: 206 records (2018-01 to 2025-07)
   - etl_runs: Test record present
   - All columns present and populated

3. **Configuration**
   - synonyms.yaml: Loaded with 18 metrics
   - visualizations.yaml: Present in container
   - ConfigService: Loading successfully

4. **RPC Endpoint**
   - JSON-RPC 2.0 protocol: Working
   - MCP wrapper parsing: Working
   - Response format: Compatible with both HU3 and legacy

5. **HU3 Pipeline Components**
   - EntityService: Extracting entities from queries
   - ConfigService: Loading metric definitions and aliases
   - Clarification system: Detecting ambiguous terms (Q10 test passed)

---

### ⚠️ What's Broken

1. **Comparison Queries** - "vs sistema" pattern not working (3 queries)
2. **Default Entity Logic** - Unnecessarily asking for bank when obvious (2 queries)
3. **Metric Calculations** - "sin gobierno" modifier not being processed (1 query)
4. **Plotly Generation** - HU3 pipeline returns data but no plotly_config yet

---

## Performance Analysis

### Response Times (Passing Queries)

| Query | Duration | Threshold | Status |
|-------|----------|-----------|--------|
| Q1 (IMOR 2024) | 2500ms | 3000ms | ✅ OK |
| Q4 (Reservas) | 1200ms | 1500ms | ✅ OK |
| Q7 (ICOR 2024) | 1800ms | 2000ms | ✅ OK |
| Q10 (Clarification) | 800ms | 1000ms | ✅ OK |

**Average Response Time:** ~1575ms
**Performance Grade:** ✅ **GOOD** (all within thresholds)

---

## Recommendations

### 🔴 **CRITICAL (Before Demo)**

1. **Fix Comparison Queries**
   - Verify "sistema" exists in database or add entity mapping
   - Implement comparison logic in AnalyticsService if missing
   - Test: Q2, Q5, Q9 should return comparative data

2. **Add Smart Entity Defaults**
   - When metric + date are clear, default to INVEX
   - Avoid unnecessary clarification prompts
   - Test: Q6, Q8 should return data without asking

3. **Fix "sin gobierno" Calculation**
   - Verify AnalyticsService processes `calculation` field
   - Test: Q3 should return calculated metric

### 🟡 **IMPORTANT (Post-Demo)**

4. **Add Plotly Generation to HU3**
   - HU3 should return both `data.values` AND `plotly_config`
   - Maintain backward compatibility with legacy format

5. **Expand Test Coverage**
   - Add tests for comparison queries
   - Add tests for metric calculations
   - Add tests for default entity logic

### 🟢 **NICE TO HAVE**

6. **Performance Optimization**
   - Current response times are acceptable but could be faster
   - Consider caching for frequently requested metrics

7. **Error Messages**
   - Improve clarification messages to be more specific
   - Add suggestions when query can't be processed

---

## Risk Assessment for Demo

### 🔴 HIGH RISK - Do Not Demo These

- ❌ Q2: Cartera comercial INVEX vs sistema
- ❌ Q3: Cartera comercial sin gobierno
- ❌ Q5: ICAP INVEX contra sistema
- ❌ Q6: Cartera vencida en 2024 (asks for clarification)
- ❌ Q8: Evolución del IMOR en 2024 (asks for clarification)
- ❌ Q9: Compara IMOR INVEX vs sistema

### 🟢 LOW RISK - Safe to Demo

- ✅ Q1: IMOR de INVEX en 2024
- ✅ Q4: Reservas totales de INVEX
- ✅ Q7: ICOR de INVEX 2024
- ✅ Q10: cartera (shows clarification UI)

**Recommendation:** Build demo script around the 4 working queries and add variants:
- "IMOR de INVEX en 2024" (working)
- "ICOR de INVEX en 2024" (working)
- "Reservas totales de INVEX" (working)
- "ICAP de INVEX en 2024" (likely working - similar to Q1/Q7)
- "Cartera total de INVEX" (likely working - similar pattern)
- "cartera" (working - demonstrates clarification UI)

---

## Next Steps

### Immediate Actions (Today)

1. ✅ Document smoke test results (this file)
2. ⬜ Debug Q2 comparison query - inspect database for "sistema" records
3. ⬜ Debug Q3 calculation query - trace through AnalyticsService
4. ⬜ Debug Q6/Q8 entity detection - add default logic

### Pre-Demo (By Dec 2)

5. ⬜ Re-run smoke test after fixes
6. ⬜ Achieve 80%+ pass rate (8/10 queries)
7. ⬜ Create updated demo script with working queries
8. ⬜ Run performance benchmark

### Demo Day (Dec 3)

9. ⬜ Use only verified working queries
10. ⬜ Have fallback queries ready if needed
11. ⬜ Monitor server health before demo

---

## Detailed Query Analysis

### Q1: IMOR de INVEX en 2024 ✅
**Status:** PASS
**Duration:** ~2500ms
**Response Format:**
```json
{
  "data": {
    "type": "data",
    "values": [
      {"date": "2024-01-01", "bank_name": "INVEX", "metric_value": 2.45},
      {"date": "2024-02-01", "bank_name": "INVEX", "metric_value": 2.38},
      ...
    ]
  },
  "metadata": {
    "metric": "imor",
    "bank": "INVEX",
    "date_range": {"start": "2024-01-01", "end": "2024-12-31"}
  }
}
```
**Why It Works:** Clear metric (IMOR), explicit bank (INVEX), specific date range (2024)

---

### Q2: Cartera comercial de INVEX vs sistema ❌
**Status:** FAIL - Empty data
**Duration:** ~1200ms
**Response:**
```json
{
  "data": {
    "type": "empty",
    "message": "No hay datos disponibles para el rango de fechas seleccionado"
  }
}
```
**Why It Fails:**
- Likely "sistema" not recognized as bank entity
- OR comparison logic not implemented
- Needs investigation

---

### Q3: Cartera comercial sin gobierno ❌
**Status:** FAIL - Multi-metric detection
**Expected:** Should calculate `cartera_comercial_total - entidades_gubernamentales_total`
**Actual:** Asks which metric (multi-metric clarification)
**Fix Required:** Verify calculation field processing in AnalyticsService

---

### Q4: Reservas totales de INVEX ✅
**Status:** PASS
**Duration:** ~1200ms
**Why It Works:** Simple metric query with explicit bank

---

### Q5: ICAP de INVEX contra sistema en 2024 ❌
**Status:** FAIL - Empty data
**Same Issue As:** Q2 (comparison queries)

---

### Q6: Cartera vencida en 2024 ❌
**Status:** FAIL - Unnecessary clarification
**Expected:** Should default to INVEX or show all banks
**Actual:** Asks "¿Para qué banco?"
**Fix Required:** Add smart defaults to EntityService

---

### Q7: ICOR de INVEX 2024 ✅
**Status:** PASS
**Duration:** ~1800ms
**Why It Works:** Same pattern as Q1

---

### Q8: Evolución del IMOR en 2024 ❌
**Status:** FAIL - Unnecessary clarification
**Expected:** Should default to INVEX or show trend across all banks
**Actual:** Asks "¿Para qué banco?"
**Same Issue As:** Q6

---

### Q9: Compara IMOR de INVEX vs sistema ❌
**Status:** FAIL - Empty data
**Same Issue As:** Q2, Q5 (comparison queries)

---

### Q10: cartera ✅
**Status:** PASS - Clarification working correctly
**Duration:** ~800ms
**Response:**
```json
{
  "data": {
    "type": "clarification",
    "reason": "ambiguous_term",
    "message": "Hay varios tipos de cartera disponibles. ¿A cuál te refieres?",
    "options": [
      {"id": "cartera_total", "label": "Cartera Total", "description": "..."},
      {"id": "cartera_comercial_total", "label": "Cartera Comercial", "description": "..."},
      ...
    ]
  }
}
```
**Why It Works:** Ambiguous term detection working as designed

---

## Appendix: Test Environment

**Server:** http://localhost:8002
**Database:** PostgreSQL (octavios-chat-bajaware_invex-postgres)
**Container:** octavios-chat-bajaware_invex-bank-advisor
**Branch:** develop
**Commit:** f9aa2614 (Merge branch 'develop')

**Data Range Available:**
- Start: 2018-01-01
- End: 2025-07-01
- Total Records: 206

**Test Script:** `scripts/smoke_demo_bank_analytics.py`
**Test Execution:**
```bash
python scripts/smoke_demo_bank_analytics.py
```

---

## Contact

For questions about this report or to request additional testing:
- Review detailed logs in smoke test output
- Check server logs: `docker logs octavios-chat-bajaware_invex-bank-advisor`
- Database queries: `docker exec -it octavios-chat-bajaware_invex-postgres psql -U octavios -d bankadvisor`
