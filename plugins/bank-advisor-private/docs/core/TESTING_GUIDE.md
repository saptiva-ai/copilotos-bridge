# BankAdvisor - Testing Guide

Complete guide for testing the BankAdvisor integration.

---

## Pre-requisites

### Services Running

```bash
# Backend (BankAdvisor MCP)
curl http://localhost:8002/health
# Should return: {"status": "healthy", ...}

# Frontend (Next.js)
# Should be accessible at: http://localhost:3002

# Check both services
docker ps | grep bank-advisor
# Should show: bank-advisor container running
```

---

## Frontend UI Testing

### Test 1: BankAdvisor Appears in Menu

**Steps**:
1. Open browser at http://localhost:3002
2. Click the **[+]** button (circular, bottom-left corner)
3. Menu should slide up from bottom

**Expected Result**:
```
Menu items should include:
✅ Agregar archivos
✅ BankAdvisor          ← Should appear here
✅ Deep research
✅ Web search
```

**Troubleshooting**:
- If not visible: Check `.env.local` has `NEXT_PUBLIC_FEATURE_BANK_ADVISOR=true`
- Restart dev server: `pnpm dev`

---

### Test 2: BankAdvisor Activation

**Steps**:
1. Open ToolMenu (click [+])
2. Click **"BankAdvisor"**
3. Menu should close

**Expected Result**:
- Chip appears below textarea: `[📊 BankAdvisor ✕]`
- Chip should be blue-tinted
- Click ✕ should remove chip

---

### Test 3: Query Execution (Evolution)

**Steps**:
1. Activate BankAdvisor (from Test 2)
2. Type in textarea: `IMOR de INVEX en 2024`
3. Press Enter or click Send

**Expected Result**:
```
1. Message sent with tool metadata
2. Loading indicator appears
3. Response renders with:
   - Text: "Aquí está el IMOR de INVEX..."
   - Chart: Line chart showing IMOR evolution
   - Chart has:
     - Title: "IMOR - INVEX"
     - X-axis: Months (2024)
     - Y-axis: Percentage
     - Red line (#E45756)
```

**Verification**:
- Open DevTools → Network → Filter "EventStream"
- Should see SSE stream with `bank_chart` event

---

### Test 4: Query Execution (Comparison)

**Steps**:
1. Activate BankAdvisor
2. Type: `IMOR de INVEX vs sistema`
3. Send

**Expected Result**:
- Bar chart comparing INVEX vs SISTEMA
- Two bars with different colors:
  - INVEX: Red (#E45756)
  - SISTEMA: Gray (#AAB0B3)

---

### Test 5: Calculated Metric

**Steps**:
1. Activate BankAdvisor
2. Type: `Cartera comercial sin gobierno`
3. Send

**Expected Result**:
- Chart renders (may take ~1.6s - uses LLM)
- Shows calculated value (comercial - gubernamental)

---

### Test 6: Adversarial - Future Date

**Steps**:
1. Activate BankAdvisor
2. Type: `IMOR de INVEX en 2030`
3. Send

**Expected Result**:
- Response: "No hay datos disponibles para el período solicitado"
- NO crash
- NO chart (empty response is valid)

---

### Test 7: Adversarial - Ambiguous Query

**Steps**:
1. Activate BankAdvisor
2. Type: `cartera`
3. Send

**Expected Result**:
- Clarification message with options:
  ```
  La consulta es ambigua. ¿Te refieres a:
  - Cartera total
  - Cartera comercial
  - Cartera de consumo
  - Cartera vencida
  ```

---

## Backend Integration Testing

### Test 8: Direct MCP Call

```bash
curl -X POST http://localhost:8002/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "bank_analytics",
      "arguments": {"metric_or_query": "IMOR de INVEX en 2024"}
    },
    "id": 1
  }' | python -m json.tool
```

**Expected Result**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [{
      "type": "text",
      "text": "..."
    }]
  },
  "id": 1
}
```

---

### Test 9: Metrics Endpoint

```bash
curl http://localhost:8002/metrics | python -m json.tool
```

**Expected Result**:
```json
{
  "service": "bank-advisor-mcp",
  "version": "1.0.0",
  "etl": {
    "total_runs_7d": 1,
    "successful_runs_7d": 1,
    "last_run_age_minutes": 1550.6
  },
  "data": {
    "total_rows": 206,
    "bank_count": 2
  },
  "performance": {
    "baseline": {
      "ratios_p50_ms": 16,
      "timelines_p50_ms": 112
    }
  }
}
```

---

## Automated Testing

### Smoke Test

```bash
cd plugins/bank-advisor-private
python scripts/smoke_demo_bank_analytics.py --port 8002
```

**Expected**: 12/12 queries pass

### ETL Validation

```bash
python scripts/ops_validate_etl.py --port 8002
```

**Expected**: 🟢 ETL HEALTHY

### Performance Benchmark

```bash
python scripts/benchmark_performance_http.py --port 8002
```

**Expected**:
- p50: ~200ms
- p95: ~1.7s
- All queries successful

---

## Visual Regression Testing

### Screenshot Checklist

Capture screenshots for:
1. ☐ ToolMenu with BankAdvisor visible
2. ☐ Active chip: `[BankAdvisor ✕]`
3. ☐ Evolution chart (line)
4. ☐ Comparison chart (bars)
5. ☐ Clarification message
6. ☐ Empty result message

### Browser Testing

| Browser | Status |
|---------|--------|
| Chrome | ☐ |
| Firefox | ☐ |
| Safari | ☐ |
| Edge | ☐ |

---

## Monitoring During Demo

### Pre-Demo Checklist (30 min before)

```bash
# 1. Backend health
curl http://localhost:8002/health
# ✅ status: healthy, etl.last_run_status: success

# 2. Smoke test
python scripts/smoke_demo_bank_analytics.py --port 8002
# ✅ 12/12 passing

# 3. ETL freshness
python scripts/ops_validate_etl.py --port 8002
# ✅ Data fresh (< 36h)

# 4. Frontend accessible
curl -I http://localhost:3002
# ✅ 200 OK
```

### During Demo

**Keep these terminals open**:

```bash
# Terminal 1: Backend logs
docker logs -f octavios-chat-bajaware_invex-bank-advisor

# Terminal 2: Frontend logs (if errors)
cd apps/web && pnpm dev

# Terminal 3: Database monitor (optional)
docker exec -it octavios-chat-bajaware_invex-postgres psql -U postgres -d invex_bankadvisor
```

**Watch for**:
- `bank_analytics.performance` logs (check latency)
- `bank_analytics.error` logs (if any failures)
- SSE events in browser DevTools

---

## Rollback Plan

If BankAdvisor fails during demo:

### Option 1: Disable Feature Flag

```bash
# Edit .env.local
NEXT_PUBLIC_FEATURE_BANK_ADVISOR=false

# Restart frontend
pnpm dev
```

Result: BankAdvisor disappears from menu, rest of app works normally.

### Option 2: Restart Backend

```bash
docker restart octavios-chat-bajaware_invex-bank-advisor

# Wait 30 seconds
curl http://localhost:8002/health
```

### Option 3: Use Direct cURL (Fallback)

If UI fails, demonstrate with cURL:

```bash
curl -X POST http://localhost:8002/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"bank_analytics","arguments":{"metric_or_query":"IMOR de INVEX en 2024"}},"id":1}'
```

---

## Success Criteria

### UI Integration
- ✅ BankAdvisor appears in ToolMenu
- ✅ Chip renders when activated
- ✅ Chip can be removed with ✕

### Functionality
- ✅ Evolution queries render line charts
- ✅ Comparison queries render bar charts
- ✅ Calculated metrics work
- ✅ Adversarial cases handled gracefully

### Performance
- ✅ Simple queries < 30ms
- ✅ LLM queries < 2s
- ✅ No crashes or 500 errors

### Observability
- ✅ `/health` shows ETL status
- ✅ `/metrics` returns data
- ✅ Logs are structured (JSON)

---

## Current Status

**Services**:
- ✅ Backend: http://localhost:8002 (healthy)
- ✅ Frontend: http://localhost:3002 (ready)

**Next Step**: Open http://localhost:3002 and verify BankAdvisor appears in the [+] menu.
