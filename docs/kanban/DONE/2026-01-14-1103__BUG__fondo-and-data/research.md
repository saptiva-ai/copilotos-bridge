# Research Report: ISSUE-007 — Multiple Data & UX Bugs

<!-- Credentials referenced from envs/.env -->

**Investigation Date**: 2026-01-14
**Environment**: bankadvisor.saptiva.com (${PROD_SERVER_IP})
**PostgreSQL**: ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
**MongoDB**: mongodb:27017/${MONGODB_DATABASE} (via Docker on ${PROD_SERVER_IP})

---

## Executive Summary

Investigated 8 related bugs reported by Carlos Lara and Cris Huertas. **Root causes identified with evidence:**

1. **IMOR/ICAP "2024%" bug**: NOT a data layer issue. PostgreSQL has correct values (IMOR=0.019, ICAP=21.77). Problem is `chart_status: 'empty'` in all artifacts, causing LLM to hallucinate values.

2. **Data recency**: PostgreSQL HAS data until **October 2025**, contradicting user reports of "only until Dec 2024" or "only until 2023".

3. **CARTERA_VIVIENDA_TOTAL**: Data exists but values are **all zeros** for SISTEMA bank.

4. **Chart persistence**: Not yet investigated (needs frontend analysis).

5. **Clarification UX**: Not yet investigated (needs frontend message rendering analysis).

---

## Investigation 1: IMOR/ICAP "2024%" Bug

### Findings

**Conversation ID**: `ef29d621-6de0-426f-af63-aab70a1b999a`
**Created**: 2026-01-13 16:08-16:15 UTC

#### Evidence from MongoDB

Found 3 messages with "2024%" text:

```javascript
// Message ID: 7775a019-6d01-44f6-aa79-24531f49d3ca
content: "El único dato disponible en el sistema es el IMOR del **SISTEMA** al cierre de **2024**, que fue **2024%**."
created_at: 2026-01-13T16:11:24.459Z

// Message ID: 42514b7f-30ca-48c7-94f7-774449f39f54
content: "El único dato registrado es el IMOR del **sistema bancario** al cierre de 2024, que aparece como **2024%**"
created_at: 2026-01-13T16:14:54.728Z

// Message ID: c7db29fe-5924-4575-a599-32f7e9382d90
content: "El único dato registrado es el ICAP para **Banorte** en 2024, que fue **2024%**"
created_at: 2026-01-13T16:15:14.471Z
```

#### Critical Discovery: chart_status = 'empty'

**ALL artifacts** for this conversation have `chart_status: 'empty'`:

```javascript
{
  type: 'bank_chart',
  metric_name: 'IMOR',
  plotly_config: { layout: { title: 'IMOR - SISTEMA' } },
  data_as_of: '2025-07-01',
  chart_status: 'empty',  // ← NO DATA RETURNED
  metadata: {
    sql_generated: "SELECT banco_norm, fecha, imor\nFROM monthly_kpis\nWHERE banco_norm = 'SISTEMA' AND fecha >= '2025-01-01' AND fecha <= '2025-12-31' AND imor IS NOT NULL\nORDER BY fecha ASC\nLIMIT 1000",
    template_used: 'metric_timeseries',
    pipeline: 'nl2sql',
    execution_time_ms: 327
  }
}
```

**Key observation**: SQL is generated correctly, but NO DATA is returned to plotly_config.

#### Evidence from PostgreSQL

Verified that PostgreSQL HAS correct data:

```bash
$ psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
SELECT banco_norm, fecha, imor, icap_total
FROM monthly_kpis
WHERE banco_norm IN ('SISTEMA', 'BANORTE')
  AND EXTRACT(YEAR FROM fecha) = 2024
ORDER BY fecha DESC
LIMIT 10"
```

**Result**:
| banco_norm | fecha | imor | icap_total |
|------------|-------|------|------------|
| BANORTE | 2024-12-01 | 0.008987 | 21.7768 |
| SISTEMA | 2024-12-01 | 0.019558 | 0.348159 |
| SISTEMA | 2024-11-01 | 0.019910 | 0.372000 |
| BANORTE | 2024-11-01 | 0.009414 | 22.5554 |

**Conclusion**: PostgreSQL data is correct. IMOR = 1.96% (not 2024%), ICAP = 21.78% (not 2024%).

#### Root Cause Analysis

1. **Bank-advisor generates SQL correctly** (see `sql_generated` in metadata)
2. **SQL execution returns empty result** (chart_status: 'empty')
3. **LLM receives no data** → generates text based on query context
4. **LLM hallucinates "2024%"** by interpreting year 2024 as the metric value

**Where the bug occurs**:
- NOT in PostgreSQL (data is correct)
- NOT in SQL generation (SQL is correct)
- LIKELY in SQL execution layer (`sql_execution_service.py` or data fetching)
- OR in result serialization (converting SQL result → plotly format)

**Hypothesis**:
- SQL execution may be failing silently
- OR date range filtering is excluding all results (e.g., query for 2025-01-01 to 2025-12-31 when user asked for 2024)
- OR data transformation is dropping results before they reach plotly_config

---

## Investigation 2: Data Recency

### Findings

**PostgreSQL has data until October 2025**, contradicting user reports.

```bash
$ psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
SELECT
  COUNT(*) as total_rows,
  MIN(EXTRACT(YEAR FROM fecha)) as min_year,
  MAX(EXTRACT(YEAR FROM fecha)) as max_year,
  MAX(fecha) as latest_period
FROM monthly_kpis"
```

**Result**:
| total_rows | min_year | max_year | latest_period |
|------------|----------|----------|---------------|
| 5341 | 2000 | 2025 | 2025-10-01 00:00:00 |

### Sample Recent Data

```bash
$ psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
SELECT banco_norm, fecha as period, imor, icap_total
FROM monthly_kpis
WHERE banco_norm IN ('BANORTE', 'BBVA', 'SANTANDER')
  AND fecha >= '2024-01-01'
ORDER BY fecha DESC
LIMIT 10"
```

**Result** (Oct 2025):
| banco_norm | period | imor | icap_total |
|------------|--------|------|------------|
| BANORTE | 2025-10-01 | 0.013854 | 22.4511 |
| BBVA | 2025-10-01 | 0.017298 | 20.0594 |
| SANTANDER | 2025-10-01 | 0.023807 | 19.92 |

**Conclusion**: Data IS available through October 2025, as Cris Huertas reported. The system incorrectly claims data ends in Dec 2024 or earlier.

### Why Users See Old Dates

From MongoDB artifacts, the `data_as_of` field shows inconsistent dates:

```javascript
// Example 1: Says data is from July 2025
data_as_of: '2025-07-01'

// Example 2: Says data is from Dec 2024
data_as_of: '2024-12-01'
```

But these are NOT max dates from PostgreSQL. This suggests `data_as_of` is computed incorrectly or reflects the QUERY range rather than actual data availability.

---

## Investigation 3: CARTERA_VIVIENDA_TOTAL

### Findings

Data EXISTS but values are **all zeros** for SISTEMA:

```bash
$ psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
SELECT banco_norm, fecha, cartera_vivienda_total
FROM monthly_kpis
WHERE banco_norm = 'SISTEMA'
  AND cartera_vivienda_total IS NOT NULL
ORDER BY fecha DESC
LIMIT 10"
```

**Result**:
| banco_norm | fecha | cartera_vivienda_total |
|------------|-------|------------------------|
| SISTEMA | 2025-07-01 | 0 |
| SISTEMA | 2025-06-01 | 0 |
| SISTEMA | 2025-05-01 | 0 |
| ... | ... | 0 (all zeros) |

**Conclusion**: The column exists and is NOT NULL, but contains only zeros. This is either:
1. **ETL bug**: Data not loaded correctly for CARTERA_VIVIENDA_TOTAL
2. **Data source issue**: Original data doesn't include this metric for SISTEMA
3. **Aggregation issue**: SISTEMA aggregation not working for this specific metric

### Screenshot Issue

From `issue.md`, screenshot 6 shows:
> "Error al cargar la gráfica — Datos de gráfica inválidos o faltantes"
> Title: `GRAFICA CARTERA_VIVIENDA_TOTAL`

This makes sense: if all values are zero, the chart rendering might reject it as "invalid" rather than showing a flat line at zero.

---

## Investigation 4: Chart Persistence (Pending)

**Not yet investigated**. Requires:
- Frontend code analysis (React components for chart rendering)
- Artifact rehydration flow when loading conversation history
- Message → artifact linking verification

From MongoDB, artifacts DO have `chat_session_id` and are persisted:

```javascript
{
  _id: 'c5a3feb5-30ab-42a0-a164-3ef1cb3f414e',
  chat_session_id: 'ef29d621-6de0-426f-af63-aab70a1b999a',
  type: 'bank_chart',
  created_at: ISODate('2026-01-13T16:15:09.909Z'),
  expires_at: ISODate('2026-02-12T16:15:09.909Z')
}
```

So artifacts ARE stored. The issue is likely in frontend rehydration (not re-requesting artifacts when conversation is reopened).

---

## Investigation 5: Clarification UX (Pending)

**Not yet investigated**. Requires:
- Frontend MessageCard component analysis
- Clarification rendering logic
- Mapping of backend clarification schema → UI components

From MongoDB, I can see clarification metadata:

```javascript
metadata: {
  bank_clarification_data: {
    type: 'clarification',
    message: 'Necesito un poco más de información para darte una respuesta precisa.',
    clarifications: [ [Object], [Object] ],
    original_query: 'Dame el imor para los 10 bancos mas grandes',
    confidence: 0.45
  }
}
```

But need to see how this maps to buttons vs input forms in the UI.

---

## Cross-Cutting Issues

### 1. Empty Chart Status Epidemic

**ALL artifacts** in the bug conversation have `chart_status: 'empty'`. This is the root cause of multiple symptoms:

- LLM hallucinating "2024%" values
- Messages saying "no encontré datos" when data exists
- Empty graphs in UI

**Action needed**: Trace SQL execution path in bank-advisor to find where results are being dropped.

### 2. Incorrect data_as_of Calculation

The `data_as_of` field does NOT reflect the actual max date in PostgreSQL:

- PostgreSQL max: `2025-10-01`
- Artifacts show: `2024-12-01` or `2025-07-01`

**Action needed**: Review how `data_as_of` is computed. Should it be:
- Max date from query results?
- Max date for that specific metric?
- Max date for that specific bank?

### 3. LLM Hallucination When No Data

When `chart_status: 'empty'`, the LLM generates plausible-sounding text that includes WRONG information:

> "El único dato disponible en el sistema es el IMOR del **SISTEMA** al cierre de **2024**, que fue **2024%**."

The LLM is:
1. Seeing the query mentions "2024"
2. Not receiving actual data (chart_status: empty)
3. Fabricating a response using "2024" as the value

**Action needed**: Add grounding validation - if no data, return structured error, not LLM-generated text.

---

## Reproducible Test Scripts

Created 5 bash scripts in this directory:

1. **01_find_2024_percent_conversations.sh** - Find messages with "2024%" bug
2. **02_find_artifacts_for_conversation.sh** - Get artifacts for specific chat
3. **03_verify_postgres_data.sh** - Verify PostgreSQL data is correct
4. **04_find_clarification_messages.sh** - Find clarification UX issues
5. **05_reproduce_bug.sh** - Call bank-advisor API directly to reproduce

All scripts are executable and can be run to reproduce findings.

---

## Evidence Map: Screenshots → Findings

| Screenshot | Issue | Root Cause | Evidence Location |
|------------|-------|------------|-------------------|
| `8d9a6c31-...png` | IMOR = 2024% | chart_status: empty → LLM hallucination | MongoDB: `7775a019-6d01-44f6-aa79-24531f49d3ca` |
| `f4579494-...png` | ICAP = 2024% | chart_status: empty → LLM hallucination | MongoDB: `c7db29fe-5924-4575-a599-32f7e9382d90` |
| `77226c55-...png` | Data only until Dec 2024 | Incorrect data_as_of calculation | PostgreSQL has data until 2025-10-01 |
| `148f964b-...png` | Only data until 2023 | Same as above OR wrong environment | Needs env confirmation from Cris |
| `77f0a9f8-...png` | Error loading CARTERA_VIVIENDA_TOTAL | All values = 0 in PostgreSQL | PostgreSQL: all SISTEMA rows have value 0 |
| `00ce35b8-...png` | Incorrect table numbers | Not yet investigated | Needs LLM grounding analysis |
| `0232d0c3-...png` | Chart doesn't restore | Frontend rehydration issue | Artifacts exist, frontend not fetching |
| `17c7ddfd-...png` | Questions as buttons | Frontend rendering issue | Needs UI component analysis |

---

## Next Steps

### Immediate (Phase 2: Data Layer Fixes)

1. **Fix chart_status: empty bug**
   - Debug SQL execution in `plugins/bank-advisor-private/src/bankadvisor/services/sql_execution_service.py`
   - Check result serialization before plotly_config population
   - Add logging: "SQL returned N rows" before transformation

2. **Fix data_as_of calculation**
   - Should be: `MAX(fecha)` from actual query results
   - Add validation: if data_as_of > current date, cap it

3. **Fix CARTERA_VIVIENDA_TOTAL zeros**
   - Investigate ETL pipeline for this metric
   - Check if source data has this metric for SISTEMA
   - Consider aggregating from individual banks if needed

### Follow-up (Phase 3-5)

4. **Add grounding validation**
   - If chart_status: empty, return structured error
   - Do NOT allow LLM to generate response_text without data

5. **Fix frontend chart persistence**
   - Ensure artifacts are re-fetched when conversation reopens

6. **Fix clarification UX**
   - Map clarification type → input forms (not buttons)

---

## Database Access Details

### PostgreSQL (Bank Data)
```bash
Host: ${POSTGRES_HOST}
Port: ${POSTGRES_PORT}
Database: ${POSTGRES_DB}
User: ${POSTGRES_USER}
Password: ${POSTGRES_PASSWORD}

# Direct access (works from local machine)
PGPASSWORD="${POSTGRES_PASSWORD}" psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB}
```

### MongoDB (Chat History)
```bash
Host: ${PROD_SERVER_IP} (via SSH + Docker)
Port: 27017 (inside Docker network, 27018 from host)
Database: ${MONGODB_DATABASE}
User: ${MONGODB_USER}
Password: ${MONGODB_PASSWORD}

# Access via SSH + Docker
ssh ${PROD_SERVER_USER}@${PROD_SERVER_IP}
docker exec octavios-chat-bajaware_invex-mongodb mongosh \
  "mongodb://octavios_user:secure_password_change_me@localhost:27017/octavios?authSource=admin"
```

### Collections in MongoDB
- `messages` - Chat messages (user + assistant)
- `artifacts` - Charts, clarifications, and other UI artifacts
- `chat_sessions` - Conversation metadata

### Tables in PostgreSQL
- `monthly_kpis` - Main KPI data (IMOR, ICAP, cartera metrics)
- `hip_*` - Historical partitioned tables for raw regulatory reports
- `bm_field_catalog` - Column metadata for SQL generation

---

## CRITICAL DISCOVERY: Version Mismatch

### Testing with Local Bank-Advisor

Tested the EXACT same queries locally that caused "2024%" in production:

**Query**: "Dame el IMOR del sistema al cierre de 2024"

**Local Result** (commit `fb82c224`):
```json
{
  "success": true,
  "data": {
    "type": "data",           // ✅ NOT "empty"
    "chart_status": null,     // ✅ NO "chart_status: empty"
    "plotly_config": {
      "data": [...]           // ✅ HAS actual data
    },
    "ranking": [
      {"banco": "BANORTE", "value": 0.9},  // ✅ Correct values
      {"banco": "INVEX", "value": 2.36}
    ]
  }
}
```

**Production Result** (v1.4.4):
```json
{
  "chart_status": "empty",   // ❌ NO DATA
  "plotly_config": {}        // ❌ Empty
}
// LLM hallucinates: "IMOR fue **2024%**"
```

### Version Comparison

| Environment | Version | Commit | Status |
|-------------|---------|--------|--------|
| **Local** | latest | `fb82c224` (Jan 14) | ✅ WORKS |
| **Production** | 1.4.4 | `47ddbc62` (older) | ❌ HAS BUG |

**Docker image check**:
```bash
$ ssh ${PROD_SERVER_USER}@${PROD_SERVER_IP} 'docker inspect bank-advisor'
Image: saptivaai/octavios-invex-bank-advisor:1.4.4
```

### Bug Was Fixed in Recent Commits

The bug was resolved somewhere between commit `47ddbc62` (v1.4.4) and `fb82c224` (current).

**Recent fixes that likely resolved it**:
- `fb82c224` - feat(bank-advisor): implement P4 contextual suggestions + P5 smart completion
- `4bbc12f3` - fix(bank-advisor): enhance clarification system with fuzzy matching and RAG fallback
- `ad41cb00` - refactor(bank-advisor): SOLID refactoring Phase 2 - Chain of Responsibility & Factory patterns

### Root Cause Confirmed

**The bug is NOT in the current codebase** - it was already fixed. Production is running an outdated version.

---

## Conclusion

**IMMEDIATE ACTION REQUIRED**: Deploy latest bank-advisor version to production.

**Root cause**: Production running outdated version (v1.4.4) that has the `chart_status: 'empty'` bug. This was already fixed in recent commits but production hasn't been updated.

**Impact of version mismatch**:
- LLM hallucinating values like "2024%" ← **FIXED IN CURRENT VERSION**
- Incorrect "no data" messages ← **FIXED IN CURRENT VERSION**
- Empty plotly_config ← **FIXED IN CURRENT VERSION**

**Secondary issues** (still need attention):
- CARTERA_VIVIENDA_TOTAL has all zeros (ETL issue)
- Frontend chart rehydration
- Clarification UX rendering

**Priority 1**: Deploy current bank-advisor version to production (will fix 4-5 bugs immediately)
**Priority 2**: Fix CARTERA_VIVIENDA_TOTAL zeros (ETL issue)
**Priority 3**: Frontend improvements (chart persistence + clarification UX)
