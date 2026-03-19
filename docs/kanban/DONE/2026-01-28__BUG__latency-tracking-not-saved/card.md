---
id: "BUG-2026-01-28__latency-tracking-not-saved"
title: "Latency tracking not saved to MongoDB messages"
status: "DOING"
phase: "Implement"
priority: "P2"
scope_in:
  - "Fix streaming latency persistence to MongoDB"
  - "Fix non-streaming latency persistence to MongoDB"
  - "Ensure latency_ms is saved at top-level message field"
scope_out:
  - "Historical data backfill"
  - "chat_new_endpoint.py (unused draft file)"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "make test T=api TEST_ARGS='-k latency'"
pr_files: []
test_status: ""
---

# Summary
- **Objective**: Fix latency tracking so that `latency_ms` is properly saved to MongoDB messages
- **Symptom**: Dashboard shows "Avg Latency 0 ms" and "No latency data available"
- **Root Cause**: Latency is calculated correctly but saved to `metadata.latency_ms` instead of top-level `latency_ms` field

# Investigation Findings

## Data Model
The `ChatMessageModel` has a top-level `latency_ms: Optional[int]` field:
```python
# apps/backend/src/models/chat.py
class ChatMessageModel(Document):
    latency_ms: Optional[int] = None  # <-- TOP-LEVEL FIELD
    metadata: Optional[Dict[str, Any]] = None  # <-- Contains latency_ms too
```

## Current Flow (Streaming Path)

### 1. Latency Calculation (CORRECT)
`apps/backend/src/services/streaming/stream_response_finalizer.py:167-169`:
```python
latency_ms = None
if ctx.start_time is not None:
    latency_ms = round((time.perf_counter() - ctx.start_time) * 1000, 2)
```

### 2. Metadata Building (PARTIAL)
`apps/backend/src/services/streaming/message_persistence.py:65-66`:
```python
if latency_ms is not None:
    metadata["latency_ms"] = latency_ms  # <-- Goes to metadata dict
```

### 3. Message Persistence (BUG)
`apps/backend/src/services/streaming/stream_response_finalizer.py:253-263`:
```python
assistant_message = await chat_service.add_assistant_message(
    chat_session=session,
    content=sanitized_content,
    model=model_name,
    metadata=assistant_metadata,  # <-- latency is inside here
    # latency_ms=???  <-- NOT PASSED AS TOP-LEVEL PARAMETER
)
```

### 4. ChatService Signature
`apps/backend/src/services/chat_service.py:772`:
```python
async def add_assistant_message(
    self,
    ...
    latency_ms: Optional[int] = None,  # <-- EXPECTS top-level param
) -> ChatMessageModel:
```

## Root Cause
`StreamResponseFinalizer` calculates latency and passes it inside `metadata` dict, but `ChatService.add_assistant_message()` expects it as a **separate parameter** to save it to the top-level field.

## Fix Options

### Option A: Pass latency_ms as separate parameter (Recommended)
In `stream_response_finalizer.py`, extract latency from metadata and pass it:
```python
assistant_message = await chat_service.add_assistant_message(
    chat_session=session,
    content=sanitized_content,
    model=model_name,
    metadata=assistant_metadata,
    latency_ms=latency_ms,  # <-- ADD THIS
)
```

### Option B: Update dashboard to read from metadata
Change dashboard queries to read `metadata.latency_ms` instead of `latency_ms`.
This is **not recommended** as it diverges from the data model.

## Affected Files
- `apps/backend/src/services/streaming/stream_response_finalizer.py` (streaming fix)
- `apps/backend/src/routers/chat/endpoints/message_endpoints.py` (non-streaming fix)
- `apps/backend/src/routers/chat_new_endpoint.py` (alternate endpoint fix)
- `apps/dashboard/queries/performance.py` (verify reads top-level field)

# Updates
- 2026-01-28 01:10 - Created. Investigation complete, ready for implementation.
- 2026-01-28 01:20 - Implementation complete. Fixed both streaming and non-streaming paths.
  - stream_response_finalizer.py: Added `latency_ms=int(latency_ms) if latency_ms else None`
  - message_endpoints.py: Added latency calculation and `latency_ms=latency_ms` parameter
  - Backend version bumped to 1.4.22
