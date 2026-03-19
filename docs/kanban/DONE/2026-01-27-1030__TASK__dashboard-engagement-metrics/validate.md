# Validation: Dashboard Engagement Metrics

> Status: PENDING (task not yet implemented)

---

## Validation Checklist

### Phase 1: Latency Bug Fix

- [ ] New assistant messages have `latency_ms` field in MongoDB
- [ ] Dashboard "Avg Latency" shows value > 0
- [ ] Latency percentiles (P50, P95, P99) display correctly

```bash
# Verify latency field exists
docker exec octavios-chat-bajaware_invex-backend python3 -c "
from pymongo import MongoClient
import os
client = MongoClient(os.environ['MONGODB_URL'])
db = client['octavios']
recent = db.messages.find_one({'role': 'assistant'}, sort=[('created_at', -1)])
print(f'latency_ms: {recent.get(\"latency_ms\", \"NOT FOUND\")}')
"
```

### Phase 2: Engagement Metrics

- [ ] New "Engagement" tab visible in dashboard
- [ ] WAU displays correct count (verify manually)
- [ ] DAU displays correct count
- [ ] Stickiness (DAU/MAU) shows percentage
- [ ] Queries/User shows reasonable number
- [ ] WAU Trend chart renders 8 weeks
- [ ] TTFI displays in minutes

```bash
# Verify engagement queries work
docker exec octavios-chat-bajaware_invex-dashboard python3 -c "
from queries.engagement import EngagementQueries
from db import get_db
db = get_db()
q = EngagementQueries(db)
print(f'WAU: {q.get_wau()}')
print(f'DAU: {q.get_dau()}')
print(f'Stickiness: {q.get_stickiness():.1f}%')
"
```

### Phase 3: Design Improvements

- [ ] IBM Plex Sans font loads (check Network tab)
- [ ] KPI values use monospace font (tabular-nums)
- [ ] Chart labels are legible at 11px
- [ ] Tab icons display correctly
- [ ] Sparklines render in KPI cards (if implemented)

```bash
# Check font loaded
curl -s http://localhost:8050/dashboard/ | grep -o "IBM Plex"
```

### Phase 4: Export

- [ ] "Export CSV" button visible on Conversations tab
- [ ] Clicking button downloads file
- [ ] CSV contains expected columns:
  - timestamp
  - user_email
  - session_id
  - query
- [ ] Data matches production records

---

## Manual Test Scenarios

### Scenario 1: New User TTFI

1. Create new user account
2. Log in to Bank Advisor chat
3. Send query that generates chart
4. Check TTFI in dashboard (should show user's time)

### Scenario 2: WAU Accuracy

1. Note current WAU count
2. Have user send a query who hasn't queried in 7+ days
3. Refresh dashboard
4. WAU should increase by 1

### Scenario 3: Latency Tracking

1. Send a complex query (multi-turn, chart generation)
2. Note response time visually
3. Check dashboard latency
4. Values should be in same order of magnitude

---

## Performance Validation

- [ ] Dashboard page load < 3 seconds
- [ ] Refresh interval doesn't cause lag
- [ ] MongoDB CPU doesn't spike on refresh

```bash
# Check MongoDB query times
docker exec octavios-chat-bajaware_invex-mongodb mongosh --quiet --eval '
db.setProfilingLevel(1, { slowms: 100 })
// Wait for dashboard refresh, then:
db.system.profile.find().sort({ts: -1}).limit(5).pretty()
'
```

---

## Rollback Plan

If issues found:

1. Revert to previous dashboard image:
   ```bash
   docker compose -f infra/docker-compose.yml \
     -f infra/docker-compose.images.yml pull dashboard
   docker compose ... up -d dashboard
   ```

2. Backend latency tracking is additive (no rollback needed)

---

## Sign-off

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| QA | | | |
| Product | Carlos Lara | | |
