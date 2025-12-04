# 🚦 Smoke Test Guide - Pre-Demo Validation

**Purpose:** Automated validation that ALL demo queries work before going live.

This is your **"traffic light"** script - if it's green, you're safe to demo. If it's red, fix issues first.

---

## 🎯 Quick Start

### Run Smoke Test (Default: localhost:8001)

```bash
cd plugins/bank-advisor-private
./scripts/smoke_demo_bank_analytics.sh
```

### Run Against Custom Host/Port

```bash
# Production server
./scripts/smoke_demo_bank_analytics.sh demo.invex.com 8001

# Custom port
./scripts/smoke_demo_bank_analytics.sh localhost 8080
```

---

## 📊 What Does It Validate?

The smoke test executes **10 real queries** (the exact ones from the demo script) and validates:

### 1. Server Health
- ✅ Server is reachable (HTTP 200)
- ✅ Status is "healthy"
- ✅ ETL has run successfully (not "never_run" or "failure")

### 2. Query Execution (10 queries)
For each query:
- ✅ Returns HTTP 200 (no server errors)
- ✅ No application errors in response
- ✅ Contains required fields: `data`, `plotly_config`, `title`
- ✅ Data structure is valid: `data.months` exists and has rows
- ✅ Plotly config is valid: has `data` and `layout`
- ✅ Chart type matches expectation (line for evolution, bar for comparison)
- ✅ Performance is acceptable (< 2s per query)

### 3. Edge Cases
- ✅ Ambiguous queries return proper error structure
- ✅ Error messages are user-friendly

---

## 🔍 Demo Queries Tested

| # | Query | Expected Chart | Max Time |
|---|-------|----------------|----------|
| 1 | IMOR de INVEX en los últimos 3 meses | Line (scatter) | 2000ms |
| 2 | Cartera comercial de INVEX vs sistema | Bar | 1500ms |
| 3 | Cartera comercial sin gobierno | Bar | 2000ms |
| 4 | Reservas totales de INVEX | Bar | 1500ms |
| 5 | ICAP de INVEX contra sistema en 2024 | Any | 2000ms |
| 6 | Cartera vencida últimos 12 meses | Line (scatter) | 2500ms |
| 7 | ICOR de INVEX 2024 | Any | 2000ms |
| 8 | Evolución del IMOR en 2024 | Line (scatter) | 2500ms |
| 9 | Compara IMOR de INVEX vs sistema | Bar | 1500ms |
| 10 | cartera (ambiguous) | Error | 1000ms |

---

## 🟢 Success Output

```
═══════════════════════════════════════════════════════════════════════════════
🚦 SMOKE TEST PRE-DEMO - BankAdvisor Analytics
═══════════════════════════════════════════════════════════════════════════════

STEP 1: Server Health Check
────────────────────────────────────────────────────────────────────────────────
✅ Server healthy

STEP 2: Demo Queries Validation
────────────────────────────────────────────────────────────────────────────────
[1/10] Q1_IMOR_evolution
    Query: "IMOR de INVEX en los últimos 3 meses"
    ✅ PASS (342ms)

[2/10] Q2_cartera_comercial_comparison
    Query: "Cartera comercial de INVEX vs sistema"
    ✅ PASS (198ms)

[3/10] Q3_cartera_sin_gobierno
    Query: "Cartera comercial sin gobierno"
    ✅ PASS (276ms)

...

═══════════════════════════════════════════════════════════════════════════════
📊 SUMMARY
═══════════════════════════════════════════════════════════════════════════════
Total Queries:  10
✅ Passed:       10
❌ Failed:       0
Success Rate:   100.0%

═══════════════════════════════════════════════════════════════════════════════
🟢 ALL CHECKS PASSED - SAFE TO DEMO
═══════════════════════════════════════════════════════════════════════════════
```

**Exit code:** `0` (success)

---

## 🔴 Failure Output

```
[5/10] Q5_ICAP
    Query: "ICAP de INVEX contra sistema en 2024"
    ❌ FAIL (3241ms)
       - Performance warning: 3241ms > 2000ms threshold
       - Expected at least 1 rows, got 0

═══════════════════════════════════════════════════════════════════════════════
📊 SUMMARY
═══════════════════════════════════════════════════════════════════════════════
Total Queries:  10
✅ Passed:       9
❌ Failed:       1
Success Rate:   90.0%

═══════════════════════════════════════════════════════════════════════════════
🔴 SOME CHECKS FAILED - DO NOT DEMO UNTIL FIXED
═══════════════════════════════════════════════════════════════════════════════

Failed queries:
  - Q5_ICAP: ICAP de INVEX contra sistema en 2024
      Performance warning: 3241ms > 2000ms threshold
      Expected at least 1 rows, got 0
```

**Exit code:** `1` (failure)

---

## 🛠️ Troubleshooting Common Failures

### ❌ Health Check Failed: "Cannot connect to http://localhost:8001"

**Cause:** Server is not running or not accessible.

**Fix:**
```bash
# Check if container is running
docker ps | grep bank-advisor

# If not running, start it
cd /path/to/octavios-chat-bajaware_invex
docker-compose up -d

# Wait 30 seconds, then retry smoke test
```

---

### ❌ Health Check Failed: "Last ETL run failed" or "never_run"

**Cause:** ETL has not been executed or failed.

**Fix:**
```bash
# Check ETL status
curl http://localhost:8001/health | jq .etl

# Run ETL manually
docker exec bank-advisor-mcp python -m bankadvisor.etl_runner

# Verify it completed successfully
curl http://localhost:8001/health | jq .etl.last_run_status
# Should return: "success"

# Retry smoke test
./scripts/smoke_demo_bank_analytics.sh
```

---

### ❌ Query Failed: "Expected at least X rows, got 0"

**Cause:** Database is empty or has incomplete data.

**Fix:**
```bash
# Verify database has data
docker exec bank-advisor-mcp psql -U postgres -d invex_bankadvisor -c \
  "SELECT COUNT(*) FROM monthly_kpis;"

# If count is 0 or very low, re-run ETL
docker exec bank-advisor-mcp python -m bankadvisor.etl_runner

# Retry smoke test
./scripts/smoke_demo_bank_analytics.sh
```

---

### ❌ Query Failed: "Performance warning: XXXXms > 2000ms threshold"

**Cause:** Query is slower than expected (possible DB indexing issue or heavy load).

**Options:**

1. **Accept the performance** (if it's close to threshold):
   - Edit `scripts/smoke_demo_bank_analytics.py`
   - Increase `max_duration_ms` for that specific query

2. **Optimize the database**:
   ```bash
   # Add indexes (if not already present)
   docker exec bank-advisor-mcp psql -U postgres -d invex_bankadvisor -c \
     "CREATE INDEX IF NOT EXISTS idx_monthly_kpis_fecha ON monthly_kpis(fecha);"

   docker exec bank-advisor-mcp psql -U postgres -d invex_bankadvisor -c \
     "CREATE INDEX IF NOT EXISTS idx_monthly_kpis_banco ON monthly_kpis(banco_norm);"

   # Retry smoke test
   ./scripts/smoke_demo_bank_analytics.sh
   ```

3. **Restart the server** (clear any caches):
   ```bash
   docker-compose restart
   sleep 30
   ./scripts/smoke_demo_bank_analytics.sh
   ```

---

### ❌ Query Failed: "Expected chart type 'bar', got 'scatter'"

**Cause:** Visualization service is returning wrong chart type (NLP intent detection issue).

**Fix:**
1. Check logs for NLP intent classification:
   ```bash
   docker logs bank-advisor-mcp | grep "tool.bank_analytics" | tail -20
   ```

2. Verify synonyms configuration:
   ```bash
   cat config/synonyms.yaml | grep -A 5 "cartera_comercial"
   ```

3. If issue persists, check `src/bankadvisor/services/visualization_service.py`

---

## 📁 Output Files

The smoke test saves detailed results to:

```
docs/smoke_test_results_YYYYMMDD_HHMMSS.json
```

**Contents:**
```json
{
  "timestamp": "2025-12-02T23:45:12.345678",
  "server": "http://localhost:8001",
  "health_check": {
    "success": true,
    "message": "Server healthy"
  },
  "queries": [
    {
      "id": "Q1_IMOR_evolution",
      "query": "IMOR de INVEX en los últimos 3 meses",
      "success": true,
      "duration_ms": 342.12,
      "issues": []
    },
    ...
  ],
  "summary": {
    "total": 10,
    "passed": 10,
    "failed": 0,
    "success_rate": 100.0
  }
}
```

**Use this file to:**
- Debug failures in detail
- Track performance trends over time
- Document pre-demo validation

---

## 🔄 Integration with CI/CD (Future)

The smoke test can be integrated into a CI/CD pipeline:

```yaml
# .github/workflows/smoke-test.yml
name: Smoke Test

on:
  push:
    branches: [main, develop]
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM

jobs:
  smoke-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start services
        run: docker-compose up -d
      - name: Wait for services
        run: sleep 30
      - name: Run smoke test
        run: ./scripts/smoke_demo_bank_analytics.sh
```

---

## 💡 Best Practices

### Before EVERY Demo

1. **Run smoke test 1 hour before** - Gives you time to fix issues
2. **Save the results** - Keep a copy of successful smoke test output
3. **Rerun if you make changes** - Any code change = rerun smoke test

### During Development

- **Run after major changes** - Catch regressions early
- **Update thresholds** - Adjust `max_duration_ms` if performance improves
- **Add new queries** - When adding demo queries, add them to smoke test

### Day of Demo

1. Run smoke test **1 hour before**
2. If 🟢 green: You're good to go
3. If 🔴 red: **DO NOT PROCEED** until fixed
4. Keep smoke test results handy (save JSON file)

---

## 🎯 Success Criteria

The demo is **safe to proceed** if:
- ✅ Smoke test returns exit code 0
- ✅ All 10 queries pass
- ✅ Health check shows "success" ETL status
- ✅ Performance is < 2s per query
- ✅ No unexpected errors in logs

**If ANY of these fail, investigate before the demo.**

---

## 📞 Support

**If smoke test keeps failing:**

1. Check server logs: `docker logs bank-advisor-mcp | tail -100`
2. Verify database connection: `docker exec bank-advisor-mcp psql -U postgres -d invex_bankadvisor -c '\dt'`
3. Check ETL execution: `curl http://localhost:8001/health | jq .etl`
4. Review E2E test results: `.venv/bin/python -m pytest tests/test_e2e_demo_flows.py -v`

**If all else fails:**
- Restart services: `docker-compose restart`
- Re-run ETL: `docker exec bank-advisor-mcp python -m bankadvisor.etl_runner`
- Check for resource issues: `docker stats`

---

**Remember:** This is your safety net. If the smoke test passes, the demo will work. 🟢

**If it fails, don't demo. Fix first, then demo.** 🔴
