# Bank Chart Canvas - Phase 1 Implementation Summary

**Date**: 2025-01-15
**Status**: ✅ Backend Foundation Complete
**Next**: Phase 2 - Frontend Components

---

## 📋 Overview

Phase 1 implements the complete backend foundation for migrating bank chart visualizations from inline chat rendering to a dedicated canvas sidebar. This includes:

- ✅ Database schema extensions with TTL support
- ✅ Artifact persistence service
- ✅ Streaming handler integration
- ✅ RESTful API endpoints
- ✅ Migration scripts

---

## 🗂️ Files Modified/Created

### **Created Files**

| File | Description | Lines |
|------|-------------|-------|
| `apps/backend/src/services/artifact_service.py` | Complete artifact service with chart-specific methods | 280 |
| `scripts/migrations/add_bank_chart_ttl_indexes.py` | MongoDB migration with rollback support | 120 |
| `docs/BANK_CHART_CANVAS_PHASE1_SUMMARY.md` | This document | - |

### **Modified Files**

| File | Changes | Impact |
|------|---------|--------|
| `apps/backend/src/models/artifact.py` | + `expires_at` field, + `create_bank_chart()` factory method, + TTL indexes | Low risk |
| `apps/backend/src/schemas/bank_chart.py` | + `BankChartArtifactRequest`, + `BankChartArtifactResponse` | Low risk |
| `apps/backend/src/routers/chat/handlers/streaming_handler.py` | + Artifact persistence logic after `bank_chart` SSE event, + `artifact_created` event | Medium risk |
| `apps/backend/src/routers/artifacts.py` | + `/session/{id}/charts` endpoint, + `/{id}/full` endpoint | Low risk |

---

## 🔑 Key Features Implemented

### 1. **Artifact Model Extensions** (`artifact.py`)

```python
# New Fields
expires_at: Optional[datetime] = Field(None, description="TTL timestamp")

# New Indexes
[("chat_session_id", 1), ("created_at", -1)],  # Efficient session queries
"expires_at",  # TTL auto-cleanup

# Factory Method
@classmethod
def create_bank_chart(
    cls,
    user_id: str,
    session_id: str,
    chart_data: Dict[str, Any],
    title: Optional[str] = None,
    ttl_days: int = 30,
) -> "Artifact":
    """Creates bank_chart artifact with auto-generated title and TTL"""
```

**Benefits:**
- Automatic cleanup after 30 days (configurable)
- Auto-generated titles: `"Gráfica: IMOR - INVEX, Sistema"`
- Type-safe factory method prevents invalid artifacts

---

### 2. **Artifact Service** (`artifact_service.py`)

Complete service layer with SOLID principles:

```python
class ArtifactService:
    async def create_bank_chart_artifact(request) -> Artifact
    async def get_charts_by_session(session_id, limit=10) -> List[Artifact]
    async def get_latest_chart_in_session(session_id) -> Optional[Artifact]
    async def get_artifact_by_id(artifact_id) -> Optional[Artifact]
    async def get_artifacts_by_user(user_id, type=None) -> List[Artifact]
    async def delete_artifact(artifact_id, user_id) -> bool
```

**Key Methods:**

1. **`create_bank_chart_artifact()`**
   - Enriches `chart_data` with `sql_query` and `metric_interpretation` in metadata
   - Persists to MongoDB
   - Returns full Artifact instance
   - Logs with structured logging

2. **`get_charts_by_session()`**
   - Queries by `chat_session_id` + type filter
   - Sorts by `created_at DESC` (most recent first)
   - Supports pagination via `limit`
   - Used for canvas chart history

3. **`get_latest_chart_in_session()`**
   - Convenience method for auto-open logic
   - Returns single most recent chart or None

---

### 3. **Streaming Handler Integration** (`streaming_handler.py`)

**Location:** After line 1590 (after `bank_chart` SSE event)

**Flow:**
```
1. User sends query → LLM decides to call bank_analytics tool
2. StreamingHandler receives BankChartData from MCP
3. ✅ Send SSE event: "bank_chart" (for preview in chat)
4. 🆕 Persist artifact to MongoDB (new code)
5. 🆕 Send SSE event: "artifact_created" with artifact_id
6. Frontend receives both events and renders preview + opens canvas
```

**Code Added:**
```python
# After sending bank_chart event
try:
    artifact_service = get_artifact_service()

    # Extract metadata for enrichment
    metadata = chart_data_dict.get("metadata", {})
    sql_query = metadata.get("sql_generated")
    metric_interpretation = metadata.get("metric_interpretation")

    # Create and persist artifact
    artifact = await artifact_service.create_bank_chart_artifact(
        BankChartArtifactRequest(
            user_id=context.user_id,
            session_id=str(chat_session.id),
            chart_data=chart_data_dict,
            sql_query=sql_query,
            metric_interpretation=metric_interpretation,
        )
    )

    # Notify frontend
    await event_queue.put({
        "event": "artifact_created",
        "data": json.dumps({
            "artifact_id": artifact.id,
            "type": "bank_chart",
            "title": artifact.title,
            "created_at": artifact.created_at.isoformat(),
        })
    })

    logger.info("bank_chart_artifact_persisted", artifact_id=artifact.id)

except Exception as artifact_exc:
    logger.error("Failed to persist artifact", error=str(artifact_exc))
    # Don't block stream - user still sees preview
```

**Error Handling:**
- Non-blocking: If persistence fails, stream continues
- User still sees chart preview in chat
- Error logged with full context for debugging

---

### 4. **API Endpoints** (`artifacts.py`)

#### **GET `/api/artifacts/session/{session_id}/charts`**

**Purpose:** Fetch all bank_chart artifacts for a session (for canvas history)

**Query Parameters:**
- `limit` (optional, default=10): Max charts to return

**Response:**
```json
[
  {
    "id": "artifact_abc123",
    "title": "Gráfica: IMOR - INVEX, Sistema",
    "created_at": "2025-01-15T10:30:00Z",
    "metric_name": "imor",
    "bank_names": ["INVEX", "Sistema"]
  }
]
```

**Authorization:**
- Verifies user owns the chat session
- 403 if unauthorized
- 404 if session not found

**Use Cases:**
- Canvas "chart history" dropdown (future)
- Multi-chart mode (Phase 3)
- Session cleanup

---

#### **GET `/api/artifacts/{artifact_id}/full`**

**Purpose:** Fetch complete artifact with all enriched data

**Response:**
```json
{
  "id": "artifact_abc123",
  "title": "Gráfica: IMOR - INVEX, Sistema",
  "type": "bank_chart",
  "content": {
    "metric_name": "imor",
    "bank_names": ["INVEX", "Sistema"],
    "plotly_config": {
      "data": [...],
      "layout": {...}
    },
    "time_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    },
    "metadata": {
      "sql_generated": "SELECT fecha, banco, valor...",
      "metric_interpretation": "El IMOR representa...",
      "pipeline": "hu3_nlp"
    },
    "data_as_of": "2025-01-15T10:30:00Z"
  },
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "session_id": "session_xyz789"
}
```

**Authorization:**
- Verifies user owns the artifact
- 403 if unauthorized
- 404 if artifact not found

**Use Cases:**
- Canvas full-screen chart view
- SQL query tab display
- Metric interpretation tab
- Re-fetching after page reload

---

### 5. **Database Migration** (`add_bank_chart_ttl_indexes.py`)

**Run:**
```bash
python scripts/migrations/add_bank_chart_ttl_indexes.py
```

**Creates:**
1. TTL index on `expires_at` field (auto-delete after 30 days)
2. Compound index on `(chat_session_id, created_at)` for efficient queries
3. Validates existing `bank_chart` artifacts

**Rollback:**
```bash
python scripts/migrations/add_bank_chart_ttl_indexes.py --rollback
```

**Output:**
```
🔌 Connected to MongoDB: octavios_chat
📦 Collection: artifacts

📊 Creating indexes for bank_chart artifacts...
✅ Created TTL index on 'expires_at' field
✅ Created compound index on (chat_session_id, created_at)
📈 Found 0 existing bank_chart artifacts

🎉 Migration completed successfully!
```

---

## 🧪 Testing Checklist

### **Unit Tests**

- [ ] `ArtifactService.create_bank_chart_artifact()` creates artifact correctly
- [ ] `ArtifactService.create_bank_chart_artifact()` enriches metadata with sql_query
- [ ] `ArtifactService.get_charts_by_session()` returns charts sorted by date
- [ ] `ArtifactService.get_latest_chart_in_session()` returns None if no charts
- [ ] Artifact factory method sets expires_at correctly

**Create:** `apps/backend/tests/unit/test_artifact_service.py`

```python
import pytest
from services.artifact_service import ArtifactService
from schemas.bank_chart import BankChartArtifactRequest

@pytest.mark.asyncio
async def test_create_bank_chart_artifact(artifact_service, sample_chart_data):
    """Test creation of bank_chart artifact with enriched metadata"""
    request = BankChartArtifactRequest(
        user_id="user123",
        session_id="session456",
        chart_data=sample_chart_data,
        sql_query="SELECT * FROM metrics WHERE...",
        metric_interpretation="IMOR representa...",
    )

    artifact = await artifact_service.create_bank_chart_artifact(request)

    assert artifact.type == "bank_chart"
    assert artifact.chat_session_id == "session456"
    assert artifact.content["metadata"]["sql_generated"] == "SELECT * FROM metrics WHERE..."
    assert artifact.expires_at is not None
```

---

### **Integration Tests**

- [ ] POST to streaming handler creates artifact in MongoDB
- [ ] SSE stream sends both `bank_chart` and `artifact_created` events
- [ ] GET `/api/artifacts/session/{id}/charts` returns correct charts
- [ ] GET `/api/artifacts/{id}/full` returns complete content
- [ ] 403 error when accessing other user's artifacts
- [ ] TTL index expires documents after 30 days (simulated)

**Create:** `apps/backend/tests/integration/test_bank_chart_flow.py`

---

### **Manual Testing**

**Test 1: Basic Flow**
```bash
# 1. Start services
make dev

# 2. Run migration
python scripts/migrations/add_bank_chart_ttl_indexes.py

# 3. Send query via chat API
curl -X POST http://localhost:8000/api/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "Cuál es el IMOR de INVEX últimos 3 meses?"}'

# 4. Verify artifact in MongoDB
mongo octavios_chat --eval 'db.artifacts.find({type: "bank_chart"})'

# 5. Fetch via API
curl http://localhost:8000/api/artifacts/session/{session_id}/charts \
  -H "Authorization: Bearer $TOKEN"
```

**Expected:**
- MongoDB has 1 artifact with type="bank_chart"
- API returns array with 1 chart
- Chart has `sql_generated` in metadata
- `expires_at` is set to +30 days from now

---

## 📊 Database Schema

### **artifacts Collection**

```javascript
{
  _id: "artifact_abc123",
  user_id: "user_xyz789",
  chat_session_id: "session_456",
  title: "Gráfica: IMOR - INVEX, Sistema",
  type: "bank_chart",
  content: {
    type: "bank_chart",
    metric_name: "imor",
    bank_names: ["INVEX", "Sistema"],
    plotly_config: {
      data: [...],
      layout: {...}
    },
    time_range: {
      start: "2024-01-01",
      end: "2024-12-31"
    },
    metadata: {
      sql_generated: "SELECT fecha, banco, valor FROM metricas...",
      metric_interpretation: "El IMOR representa el índice de morosidad...",
      pipeline: "hu3_nlp",
      execution_time_ms: 150
    },
    data_as_of: "2025-01-15T10:30:00Z",
    source: "bank-advisor-mcp"
  },
  versions: [],
  created_at: ISODate("2025-01-15T10:30:00Z"),
  updated_at: ISODate("2025-01-15T10:30:00Z"),
  expires_at: ISODate("2025-02-14T10:30:00Z")  // +30 days
}
```

### **Indexes**

```javascript
// TTL Index (auto-delete)
db.artifacts.createIndex(
  { expires_at: 1 },
  { name: "expires_at_ttl", expireAfterSeconds: 0 }
)

// Compound Index (efficient session queries)
db.artifacts.createIndex(
  { chat_session_id: 1, created_at: -1 },
  { name: "session_created_desc" }
)
```

---

## 🚀 Deployment Steps

### **1. Run Migration**

```bash
# Connect to production MongoDB
export MONGODB_URL="mongodb://prod-host:27017/octavios_chat"

# Run migration
python scripts/migrations/add_bank_chart_ttl_indexes.py

# Verify indexes
mongo $MONGODB_URL --eval '
  db.artifacts.getIndexes().forEach(function(idx) {
    print(JSON.stringify(idx, null, 2));
  });
'
```

### **2. Deploy Backend**

```bash
# Build and deploy backend with new code
make rebuild-api
make restart-api

# Verify health
curl http://localhost:8000/health
```

### **3. Verify Endpoints**

```bash
# Test new endpoints (replace with real IDs)
curl http://localhost:8000/api/artifacts/session/session_123/charts \
  -H "Authorization: Bearer $TOKEN"

curl http://localhost:8000/api/artifacts/artifact_456/full \
  -H "Authorization: Bearer $TOKEN"
```

### **4. Monitor Logs**

```bash
# Watch for artifact creation logs
make logs-api | grep "bank_chart_artifact"

# Expected output:
# bank_chart_artifact_persisted artifact_id=artifact_abc metric=imor
```

---

## 🔄 Rollback Plan

### **Scenario 1: Migration Issues**

```bash
# Rollback indexes
python scripts/migrations/add_bank_chart_ttl_indexes.py --rollback

# Verify indexes removed
mongo $MONGODB_URL --eval 'db.artifacts.getIndexes()'
```

### **Scenario 2: StreamingHandler Bug**

```bash
# Revert streaming_handler.py to previous commit
git checkout HEAD~1 -- apps/backend/src/routers/chat/handlers/streaming_handler.py

# Rebuild and restart
make rebuild-api && make restart-api
```

**Impact:** Users will still see chart previews in chat, but:
- No artifact persistence
- No auto-open canvas (Phase 2 feature)
- No chart history

---

## 📈 Metrics to Monitor

### **Success Metrics**

| Metric | Target | Query |
|--------|--------|-------|
| Artifact creation rate | >95% | `db.artifacts.countDocuments({type: "bank_chart", created_at: {$gt: ...}})` |
| Artifact fetch latency | <100ms | Prometheus: `http_request_duration_seconds{endpoint="/artifacts/.*"}` |
| TTL cleanup working | Yes | Check `expires_at` docs disappear after 30 days |
| Error rate on persistence | <1% | Logs: `grep "Failed to persist artifact"` |

### **Grafana Dashboard Queries**

```promql
# Artifact creation rate
sum(rate(artifact_created_total{type="bank_chart"}[5m]))

# Artifact fetch latency (p95)
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket{endpoint="/artifacts"}[5m])) by (le)
)

# Artifact persistence failures
sum(rate(artifact_persistence_errors_total[5m]))
```

---

## 🎯 Next Steps: Phase 2 - Frontend Components

### **Tasks**

1. ✅ **Backend Foundation** (Phase 1) - **COMPLETED**
2. ⏳ **Frontend Components** (Phase 2) - **NEXT**
   - Extend TypeScript types
   - Create `BankChartPreview` component
   - Create `BankChartCanvasView` component
   - Update `CanvasPanel` with bank_chart case
   - Implement auto-open logic in `ChatView`
   - Add highlight sync between chat and canvas

3. ⏳ **Integration & Testing** (Phase 3)
4. ⏳ **Polish & Deploy** (Phase 4)

### **Dependencies for Phase 2**

- ✅ Backend endpoints ready
- ✅ SSE events defined (`bank_chart`, `artifact_created`)
- ✅ MongoDB schema stable
- ⏳ Frontend canvas store needs extension
- ⏳ React components need creation

---

## 📚 References

- **Original Plan:** `Plan de Implementación Técnico - Gráficas en Canvas Lateral`
- **Architecture Doc:** `docs/ARCHITECTURE.md`
- **Artifact Model:** `apps/backend/src/models/artifact.py`
- **Streaming Handler:** `apps/backend/src/routers/chat/handlers/streaming_handler.py`
- **Bank Chart Schema:** `apps/backend/src/schemas/bank_chart.py`

---

## ✅ Phase 1 Completion Checklist

- [x] Artifact model extended with `expires_at` and factory method
- [x] TTL and compound indexes migration script created
- [x] ArtifactService implemented with 6 methods
- [x] StreamingHandler integrated with artifact persistence
- [x] Two new API endpoints created (`/session/{id}/charts`, `/{id}/full`)
- [x] All code documented with docstrings
- [x] Error handling implemented (non-blocking)
- [x] Structured logging added
- [x] Migration script tested locally
- [x] Summary documentation created

**Phase 1 Status:** ✅ **COMPLETE - Ready for Phase 2**
