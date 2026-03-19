# P1 Bugs Investigation - ISSUE-007

**Date**: 2026-01-14
**Status**: Investigation Complete
**Priority**: P1 (UX/Frontend)

---

## Bug 7: Table Numbers Incorrect

### User Report

**Reporter**: Cris Huertas
**Screenshot**: `img/00ce35b8-0686-403f-8ead-49cb4b1c0d34.png`
**Complaint**: "los datos están mal, todos los bancos colocaron aprox 115K créditos hipotecarios en 2024 y aquí dice que solo BBVA colocó esa cantidad de créditos"

### Investigation Findings

**Table Structure** (from screenshot):
- Año, Banco, Número de Créditos, Cartera Hipotecaria Colocada (MDP), Crédito Promedio (MDP)
- Shows data from 2019-2023 (but title claims 2019-2023, actual data includes 2024)

**Schema Analysis**:
```sql
\d monthly_kpis
-- Available columns:
- cartera_vivienda_total (double precision) ← Mortgage portfolio TOTAL VALUE
- banco_norm, fecha, cartera_total, cartera_vencida, etc.

-- MISSING columns:
- numero_creditos ← DOES NOT EXIST
- credito_promedio ← DOES NOT EXIST
```

**Root Cause**: **Hallucination/Synthesis without Grounding**

The LLM is generating tables with metrics that **do not exist in the database schema**:
1. "Número de Créditos" (Credit Count) - NOT AVAILABLE
2. "Crédito Promedio" (Average Credit) - NOT AVAILABLE

We only have:
- `cartera_vivienda_total` - Total mortgage portfolio value in millions of pesos (MDP)
- No granular credit count data
- No individual credit amounts to calculate averages

### Current Behavior

When user asks: "número de créditos hipotecarios por banco en 2024"

**System Response**: Clarification request (no table generated)
```json
{
  "type": "clarification",
  "message": "Para ayudarte, necesito que especifiques la métrica y el banco."
}
```

This is CORRECT behavior - system correctly identifies that "número de créditos" is not a valid metric.

### Historical Bug Context

The screenshot shows a table that **should not have been generated** because:
1. The metrics don't exist in our schema
2. The system should have asked for clarification
3. If the table was generated, it was synthesized/hallucinated without grounding

### Solution

**Status**: ✅ Already fixed by current clarification system

The system now correctly:
1. Detects invalid metrics
2. Asks for clarification
3. Does NOT generate tables with non-existent metrics

**No additional fixes needed** - the clarification system (commit ef9a5b17) prevents this bug.

---

## Bug 8: Chart Persistence (Charts Don't Restore)

### User Report

**Reporter**: Carlos Lara
**Screenshot**: `img/0232d0c3-a5c6-49ba-a23c-f64aa0c84459.png`
**Complaint**: "No sé si es porque bajaste el servicio pero probé ahorita en blanco y no restaura la gráfica"

### Investigation Findings

#### Backend: Artifact Persistence Logic

**File**: `apps/backend/src/services/streaming/chart_flow_handler.py`
**Lines**: 422-476

```python
# Step 6: Persist artifact if service provided
if artifact_service and (
    chart_data_dict.get("type") != "knowledge"
    or chart_data_dict.get("plotly_config")
):
    try:
        artifact_request = BankChartArtifactRequest(
            user_id=user_id,
            session_id=session_id,
            chart_data=chart_data_dict,
            sql_query=metadata.get("sql_generated"),
            metric_interpretation=metadata.get("metric_interpretation"),
        )

        artifact = await artifact_service.create_bank_chart_artifact(
            artifact_request
        )

        artifact_id = artifact.id
        artifact_created = True

        # Send artifact event
        await event_queue.put(
            ChartFlowHandler.build_artifact_event(
                artifact_id=artifact.id,
                title=artifact.title,
                created_at=artifact.created_at.isoformat(),
            )
        )
        events_emitted += 1

    except Exception as artifact_exc:
        logger.error(
            "chart_flow_handler.artifact_failed",
            error=str(artifact_exc),
            exc_type=type(artifact_exc).__name__,
            session_id=session_id,
        )
        # Don't block stream on artifact persistence failure
```

**✅ Backend Code Exists**: Yes, artifact persistence is implemented
**✅ artifact_service Passed**: Yes, from `streaming_handler.py:948`

#### Frontend: Artifact Loading Logic

**File**: `apps/web/src/components/chat/ChatMessage.tsx`
**Lines**: 149-230

```typescript
// State for artifact data (BA-P0-003: Load bank_chart artifacts)
const [artifactData, setArtifactData] = React.useState<Record<string, any>>({});

// Fetch artifact content for bank_chart types
React.useEffect(() => {
  const fetchArtifacts = async () => {
    for (const inv of artifactInvocations) {
      const artifactId = inv.result?.id as string;
      const artifactType = inv.result?.type as string;

      // Only fetch if it's a bank_chart and we haven't loaded it yet
      if (
        artifactType === "bank_chart" &&
        artifactId &&
        !artifactData[artifactId]
      ) {
        try {
          const response = await fetch(`/api/artifacts/${artifactId}`);
          if (response.ok) {
            const data = await response.json();
            setArtifactData(prev => ({ ...prev, [artifactId]: data }));
          }
        } catch (error) {
          console.error("Failed to fetch artifact:", error);
        }
      }
    }
  };

  fetchArtifacts();
}, [artifactInvocations, artifactData]);
```

**✅ Frontend Code Exists**: Yes, artifact fetching is implemented

#### Backend: Artifact API Endpoints

**File**: `apps/backend/src/routers/artifacts.py`

Available endpoints:
- ✅ `GET /api/artifacts/{artifact_id}` - Retrieve artifact (lines 158-178)
- ✅ `GET /api/artifacts/session/{session_id}/charts` - Get session charts (lines 219-293)
- ✅ `GET /api/artifacts/{artifact_id}/full` - Get complete artifact (lines 296-351)

### Possible Failure Points

#### 1. Artifact Creation Failures (Silent)

The backend catches exceptions but doesn't re-raise:
```python
except Exception as artifact_exc:
    logger.error("chart_flow_handler.artifact_failed", ...)
    # Don't block stream on artifact persistence failure
```

**Issue**: If artifact creation fails, the chart still renders but won't persist.

#### 2. artifact_created Event Not Handled

Backend emits:
```python
await event_queue.put({
    "event": "artifact_created",
    "data": json.dumps({
        "artifact_id": artifact_id,
        "type": "bank_chart",
        "title": title,
        "created_at": created_at,
    })
})
```

**Need to verify**: Does frontend handle `artifact_created` SSE event?

#### 3. artifact_id Not Saved in Message

The frontend expects:
```typescript
const artifactId = inv.result?.id as string;
```

Where `inv` comes from `metadata?.tool_invocations`.

**Need to verify**: Is `tool_invocations` populated with artifact_id after creation?

#### 4. Message Doesn't Include tool_invocations

When conversation is restored, the message needs:
```typescript
metadata: {
  tool_invocations: [
    {
      tool_name: "create_artifact",
      result: {
        id: "<artifact_id>",
        type: "bank_chart"
      }
    }
  ]
}
```

**Need to verify**: Are tool_invocations saved to MongoDB with the message?

### Root Cause Hypothesis

Most likely issue: **artifact_id is not being saved in the message's tool_invocations**

When the message is persisted to MongoDB, it needs to include:
1. The `tool_invocations` metadata
2. With a `create_artifact` tool invocation
3. Containing the `artifact_id` in `result.id`

Without this linkage, when the conversation is restored:
- Frontend can't find `artifactInvocations`
- No fetch to `/api/artifacts/{artifactId}`
- Chart doesn't restore

### Debugging Steps

1. **Check if artifacts are being created**:
```bash
# Connect to MongoDB
mongo ${MONGODB_URL}

# Query artifacts collection
db.artifacts.find({type: "bank_chart"}).count()
db.artifacts.find({type: "bank_chart"}).limit(5).pretty()
```

2. **Check if messages include tool_invocations**:
```bash
# Query messages with bank_chart kind
db.messages.find({kind: "bank_chart"}).limit(5).pretty()

# Look for metadata.tool_invocations field
db.messages.find({"metadata.tool_invocations": {$exists: true}}).limit(5).pretty()
```

3. **Check backend logs for artifact failures**:
```bash
docker logs octavios-chat-bajaware_invex-backend 2>&1 | grep "artifact_failed"
docker logs octavios-chat-bajaware_invex-backend 2>&1 | grep "artifact_persisted"
```

4. **Test SSE events during chart creation**:
```javascript
// In browser console during chart generation
const evtSource = new EventSource('/api/chat/stream/...');
evtSource.addEventListener('artifact_created', (e) => {
  console.log('Artifact created:', e.data);
});
```

### Solution Path

**Option 1: Fix Message Persistence** (Recommended)

Ensure that when a chart is sent:
1. Backend creates artifact
2. Backend saves artifact_id in message metadata
3. Message is persisted with tool_invocations

**Option 2: Frontend Workaround**

If artifact_id isn't in message:
1. Frontend calls `/api/artifacts/session/{session_id}/charts`
2. Matches charts to messages by timestamp/content
3. Loads most recent chart for messages with `kind: "bank_chart"`

**Option 3: Separate Chart History**

Add a "Chart History" panel that:
1. Shows all charts for the session
2. Allows reloading any chart
3. Independent of message restoration

### Status

**Current**: ❌ Bug exists - Charts don't restore when returning to conversation

**Next Steps**:
1. Run debugging steps to identify exact failure point
2. Implement fix based on findings (most likely Option 1)
3. Add E2E test for chart persistence
4. Add frontend error handling for failed artifact loads

---

## Summary

| Bug | Status | Root Cause | Fix Required |
|-----|--------|------------|--------------|
| **Table Numbers** | ✅ Fixed | Hallucination (metrics don't exist in schema) | None - clarification system prevents this |
| **Chart Persistence** | ❌ Open | artifact_id not saved in message metadata (hypothesis) | Investigation + backend fix |

## Related Files

### Bug 7 (Table Numbers)
- `plugins/bank-advisor-private/src/bankadvisor/services/clarification_service.py` - Prevents invalid metrics
- `plugins/bank-advisor-private/etl/core/loaders_unified.py` - Schema definition (no credit count columns)

### Bug 8 (Chart Persistence)
- `apps/backend/src/services/streaming/chart_flow_handler.py` - Artifact creation logic
- `apps/backend/src/routers/artifacts.py` - Artifact API endpoints
- `apps/web/src/components/chat/ChatMessage.tsx` - Artifact loading frontend
- `apps/backend/src/models/artifact.py` - Artifact Beanie model
- `apps/backend/src/models/chat.py` - ChatMessage model (check if tool_invocations persisted)

---

**Last Updated**: 2026-01-14
