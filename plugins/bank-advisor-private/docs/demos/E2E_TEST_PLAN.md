# E2E Test Plan - BankAdvisor Frontend Integration

**Fecha**: 2025-11-27
**Versión**: 1.0
**Scope**: Frontend → Backend → bank-advisor → Database

---

## 🎯 Objetivo

Validar el flujo completo de integración NL2SQL desde el frontend de OctaviOS hasta la base de datos PostgreSQL, asegurando que los usuarios puedan:
- Hacer queries en lenguaje natural
- Visualizar gráficos bancarios interactivos inline
- Obtener respuestas en < 3 segundos
- Experimentar 0 errores críticos

---

## 🏗️ Arquitectura del Sistema (E2E)

```
┌──────────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js + React)                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 1. User Input: "IMOR de INVEX en 2024"                     │  │
│  │ 2. POST /api/chat/sessions/{id}/messages                   │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI)                                               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 3. message_endpoints.py:218-229                            │  │
│  │    → ToolExecutionService.invoke_bank_analytics()          │  │
│  │ 4. bank_analytics_client.py                                │  │
│  │    → POST http://bank-advisor:8002/rpc                     │  │
│  │      {method: "tools/call", params: {name: "bank_analytics"}}│
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  BANK-ADVISOR (FastAPI + FastMCP)                                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 5. main.py:554 - json_rpc_endpoint()                       │  │
│  │ 6. _bank_analytics_impl()                                  │  │
│  │    → NL2SQL Pipeline:                                      │  │
│  │      a. QuerySpecParser.parse() → QuerySpec               │  │
│  │      b. Nl2SqlContextService.get_context() → RAG           │  │
│  │      c. SqlGenerationService.generate() → SQL              │  │
│  │      d. SqlValidator.validate() → Security check           │  │
│  │      e. session.execute(sql) → Raw rows                    │  │
│  │      f. Data transformation → Legacy format                │  │
│  │      g. VisualizationService → Plotly config               │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  DATABASE (PostgreSQL)                                           │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 7. SELECT * FROM monthly_kpis                              │  │
│  │    WHERE banco_nombre = 'INVEX'                            │  │
│  │    AND EXTRACT(YEAR FROM fecha) = 2024                     │  │
│  │    → 12 rows (Jan-Dec 2024)                                │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  RESPONSE FLOW (Upstream)                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 8. BankChartData returned to backend                       │  │
│  │ 9. Artifact created in MongoDB                             │  │
│  │ 10. LLM generates response with artifact_id                │  │
│  │ 11. Frontend receives message + artifact_id                │  │
│  │ 12. BankChartViewer renders Plotly chart inline            │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📋 Test Cases

### TC-1: Query Simple - Métrica Única

**ID:** TC-SIMPLE-001
**Priority:** P0
**Preconditions:**
- Docker containers running (backend, bank-advisor, postgres)
- Database populated with 191 records
- User logged in to OctaviOS

**Steps:**
1. Navigate to chat page
2. Type: `"IMOR de INVEX en 2024"`
3. Press Enter

**Expected Results:**

| Step | Component | Expected Output | Validation |
|------|-----------|-----------------|------------|
| 1 | Frontend | Chat input visible | ✅ UI loads |
| 2 | Backend | is_bank_query() → true | ✅ Logs show "bank_analytics.detected" |
| 3 | bank-advisor | RPC call received | ✅ Logs show "tool.bank_analytics.invoked" |
| 4 | NL2SQL Parser | QuerySpec generated | ✅ metric="IMOR", banks=["INVEX"], year=2024 |
| 5 | SQL Generator | SQL query created | ✅ Contains WHERE banco_nombre='INVEX' AND year=2024 |
| 6 | SQL Validator | Security check passed | ✅ No blacklisted keywords |
| 7 | Database | 12 rows returned | ✅ Jan-Dec 2024 data |
| 8 | Visualization | Plotly config generated | ✅ 1 trace with 12 points |
| 9 | Backend | Artifact created | ✅ MongoDB has new artifact |
| 10 | LLM | Response with artifact_id | ✅ Message contains artifact reference |
| 11 | Frontend | Chart rendered inline | ✅ Plotly component visible |
| 12 | User | Interactive chart | ✅ Can zoom, hover tooltips work |

**Performance:**
- Total latency: < 3 seconds
- RPC call: < 1.5 seconds
- Frontend render: < 500ms

**Data Validation:**
```javascript
// Expected plotly_config.data structure
{
  x: ["Jan 2024", "Feb 2024", ..., "Dec 2024"],  // 12 months
  y: [0.05, 0.06, 0.05, ...],  // IMOR values (ratio format)
  type: "scatter",
  mode: "lines+markers",
  name: "INVEX"
}
```

---

### TC-2: Query Comparativa - Dos Bancos

**ID:** TC-COMPARE-001
**Priority:** P0

**Steps:**
1. Type: `"Compara IMOR de INVEX vs Sistema en 2024"`
2. Press Enter

**Expected Results:**

| Validation Point | Expected | How to Verify |
|------------------|----------|---------------|
| QuerySpec | banks=["INVEX", "SISTEMA"] | Check logs: "nl2sql.query_spec" |
| SQL Query | WHERE banco_nombre IN ('INVEX', 'SISTEMA') | Check logs: "sql.generated" |
| Rows Returned | 24 rows (12 INVEX + 12 Sistema) | Check logs: "sql.rows_fetched" |
| Plotly Traces | 2 traces in data array | plotly_config.data.length === 2 |
| Chart Legend | Shows "INVEX" and "Sistema" | Visual verification |
| Colors | Distinct colors for each bank | trace[0].marker.color !== trace[1].marker.color |

**Data Sample:**
```json
{
  "plotly_config": {
    "data": [
      {
        "name": "INVEX",
        "x": ["Jan 2024", "Feb 2024", ...],
        "y": [0.05, 0.06, ...],
        "marker": {"color": "#1f77b4"}
      },
      {
        "name": "Sistema",
        "x": ["Jan 2024", "Feb 2024", ...],
        "y": [0.08, 0.07, ...],
        "marker": {"color": "#ff7f0e"}
      }
    ]
  }
}
```

---

### TC-3: Query con Rango Temporal

**ID:** TC-TIMERANGE-001
**Priority:** P1

**Input Queries:**
- `"IMOR de INVEX últimos 3 meses"`
- `"cartera comercial de INVEX desde 2023"`
- `"ICOR de Sistema en primer trimestre 2024"`

**Expected Behavior:**

| Query | Expected SQL Filter | Expected Points |
|-------|---------------------|-----------------|
| "últimos 3 meses" | `fecha >= CURRENT_DATE - INTERVAL '3 months'` | 3 |
| "desde 2023" | `EXTRACT(YEAR FROM fecha) >= 2023` | 24+ |
| "primer trimestre 2024" | `fecha BETWEEN '2024-01-01' AND '2024-03-31'` | 3 |

---

### TC-4: Manejo de Errores - Query Inválida

**ID:** TC-ERROR-001
**Priority:** P0

**Test Scenarios:**

#### Scenario A: SQL Injection Attempt
**Input:** `"IMOR'; DROP TABLE monthly_kpis; --"`

**Expected:**
- ✅ SqlValidator.validate() rejects query
- ✅ Error logged: "sql.validation_failed"
- ✅ Frontend shows error message (no crash)
- ✅ Database remains intact (103 INVEX + 88 Sistema = 191 rows)

#### Scenario B: Unknown Metric
**Input:** `"dame el ROE de INVEX"`

**Expected:**
- ✅ Parser detects unknown metric
- ✅ Response: "Lo siento, no tengo datos de ROE. Métricas disponibles: IMOR, ICOR..."
- ✅ No SQL executed

#### Scenario C: Ambiguous Query (Future P0-3)
**Input:** `"dame los datos del banco"`

**Expected (Post P0-3):**
- ✅ requires_clarification=true
- ✅ Frontend shows options: INVEX / Sistema / Ambos
- ✅ User selects → new query auto-generated

---

### TC-5: Performance - Concurrent Users

**ID:** TC-PERF-001
**Priority:** P1

**Setup:**
- 5 concurrent users
- Each sends 10 queries (50 total)

**Expected:**
- ✅ All queries complete within 5 seconds
- ✅ No database deadlocks
- ✅ Redis cache hit rate > 50% (after first query)
- ✅ Memory usage stable (no leaks)

**Load Test Script:**
```bash
# Using Apache Bench
ab -n 50 -c 5 -p query.json -T application/json \
   http://localhost:8000/api/chat/sessions/test-session/messages
```

---

### TC-6: Mobile Responsiveness

**ID:** TC-MOBILE-001
**Priority:** P2

**Devices:**
- iPhone 13 (390x844)
- iPad Pro (1024x1366)
- Samsung Galaxy S21 (360x800)

**Expected:**
- ✅ Chart scales to viewport
- ✅ Touch interactions work (pinch-zoom)
- ✅ Legend readable (no overlap)
- ✅ Tooltip shows on tap

---

### TC-7: Data Persistence

**ID:** TC-PERSIST-001
**Priority:** P0

**Steps:**
1. User sends query: "IMOR de INVEX 2024"
2. Chart renders successfully
3. User refreshes page
4. Navigate back to chat

**Expected:**
- ✅ Chart still visible after refresh
- ✅ artifact_id persisted in MongoDB
- ✅ No re-fetch from bank-advisor (served from cache/artifact)

**Validation:**
```bash
# MongoDB query
db.artifacts.findOne({type: "bank_chart"})

# Expected document
{
  "_id": "artifact-uuid",
  "user_id": "user-123",
  "chat_session_id": "session-456",
  "type": "bank_chart",
  "title": "IMOR - INVEX",
  "content": { /* BankChartData */ },
  "created_at": "2025-11-27T..."
}
```

---

### TC-8: Conversational Context

**ID:** TC-CONTEXT-001
**Priority:** P1

**Conversation Flow:**

| Turn | User Input | Expected Artifact | Notes |
|------|------------|-------------------|-------|
| 1 | "IMOR de INVEX en 2024" | Chart with INVEX only | Base query |
| 2 | "ahora compáralo con Sistema" | Chart with INVEX + Sistema | Context preserved |
| 3 | "muéstrame solo los últimos 6 meses" | Same banks, filtered to 6 months | Temporal refinement |

**Validation:**
- ✅ Turn 2 doesn't require re-specifying "INVEX"
- ✅ Turn 3 maintains bank selection from Turn 2

---

## 🔧 Manual Testing Checklist

### Pre-Test Setup

- [ ] Docker containers running:
  ```bash
  docker ps | grep -E "backend|bank-advisor|postgres|qdrant"
  ```
- [ ] Database populated:
  ```bash
  docker exec octavios-postgres psql -U octavios -d bankadvisor \
    -c "SELECT COUNT(*) FROM monthly_kpis;"
  # Expected: 191
  ```
- [ ] RAG collections seeded:
  ```bash
  # Check Qdrant collections
  curl http://localhost:6333/collections
  # Expected: nl2sql_schema, nl2sql_metrics, nl2sql_examples
  ```
- [ ] Environment variables set:
  ```bash
  cat apps/backend/.env | grep BANK_ADVISOR
  # Expected: BANK_ADVISOR_URL=http://bank-advisor:8002
  ```

### During Test Execution

**Browser DevTools Checklist:**
- [ ] Console: 0 errors
- [ ] Network: RPC call completes < 2s
- [ ] Performance: No layout shifts during chart render
- [ ] Memory: No leaks after 10 queries

**Backend Logs Checklist:**
```bash
docker logs octavios-backend --tail 100 | grep bank_analytics

# Expected log sequence:
# 1. bank_analytics.detected
# 2. bank_analytics.cache_miss (first time)
# 3. bank_analytics.success
# 4. bank_chart.artifact_created
```

**bank-advisor Logs Checklist:**
```bash
docker logs octavios-bank-advisor --tail 100

# Expected log sequence:
# 1. tool.bank_analytics.invoked
# 2. nl2sql.query_spec
# 3. rag.context_retrieved (if RAG enabled)
# 4. sql.generated
# 5. sql.validated
# 6. sql.executed (rows_fetched: 12)
# 7. visualization.config_generated
```

---

## 🐛 Known Issues & Workarounds

### Issue 1: Plotly Bundle Size (~3MB)
**Symptom:** Initial page load slow
**Workaround:** Use plotly.js-basic-dist-min (800KB)
**Solution:** Dynamic import + code splitting

### Issue 2: SSR Hydration Mismatch
**Symptom:** React warning "Text content does not match"
**Workaround:** `const Plot = dynamic(() => import("react-plotly.js"), { ssr: false })`

### Issue 3: Chart Not Responsive on Mobile
**Symptom:** Horizontal scroll on small screens
**Workaround:** Set `useResizeHandler={true}` and `style={{ width: "100%" }}`

---

## 📊 Test Metrics & Success Criteria

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Latency (P95)** | < 3s | Backend logs: `bank_analytics.latency_ms` |
| **Error Rate** | < 1% | Count errors / total queries |
| **Cache Hit Rate** | > 70% | Redis metrics after 100 queries |
| **SQL Injection Block** | 100% | TC-4 scenarios must all fail safely |
| **Mobile Usability** | 100% | All TC-6 checks pass |
| **Data Accuracy** | 100% | Spot-check 10 queries vs raw SQL |

---

## 🚀 Regression Test Suite

### Quick Smoke Test (5 minutes)
```bash
# 1. Health check
curl http://localhost:8002/health
# Expected: {"status": "healthy"}

# 2. Simple query
curl -X POST http://localhost:8002/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test",
    "method": "tools/call",
    "params": {
      "name": "bank_analytics",
      "arguments": {
        "metric_or_query": "IMOR de INVEX en 2024",
        "mode": "dashboard"
      }
    }
  }'
# Expected: result with plotly_config

# 3. Frontend smoke test
# Open http://localhost:3000/chat
# Type: "IMOR de INVEX"
# Expected: Chart renders in < 3s
```

### Full Regression (30 minutes)
- Run all TC-1 through TC-8
- Verify logs have 0 errors
- Check MongoDB for artifact persistence
- Validate Plotly charts visually

---

## 📝 Test Report Template

```markdown
# Test Execution Report

**Date:** YYYY-MM-DD
**Tester:** [Name]
**Environment:** [dev/staging/prod]
**Commit:** [git hash]

## Test Results

| Test Case | Status | Duration | Notes |
|-----------|--------|----------|-------|
| TC-1 | ✅ PASS | 2.1s | - |
| TC-2 | ✅ PASS | 2.3s | - |
| TC-3 | ⚠️ PARTIAL | 3.2s | Slow on "últimos 3 meses" query |
| TC-4 | ✅ PASS | - | SQL injection blocked |
| TC-5 | ❌ FAIL | - | 2/50 queries timed out |

## Issues Found

1. **BUG-001:** Query timeout on concurrent load
   - Severity: P1
   - Reproduce: Run TC-5 with 10 concurrent users
   - Workaround: Increase BANK_ADVISOR_TIMEOUT to 60s

## Recommendations

- Investigate database connection pool size
- Add Redis caching for repeated queries
- Consider CDN for Plotly.js bundle
```

---

## ✅ Definition of Done

Test plan is considered complete when:

- [ ] All P0 test cases pass (TC-1, TC-2, TC-4, TC-7)
- [ ] Latency < 3s for 95% of queries
- [ ] 0 critical errors in production logs
- [ ] Mobile responsiveness verified on 3+ devices
- [ ] Documentation updated with test results
- [ ] Stakeholder demo completed successfully

---

**Versión:** 1.0
**Última Actualización:** 2025-11-27
**Próxima Revisión:** Post-implementación de Tareas 1-6
