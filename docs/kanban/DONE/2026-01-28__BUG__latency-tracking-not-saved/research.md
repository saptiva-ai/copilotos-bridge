# Research: Latency Tracking Bug

## Investigation Date: 2026-01-28

## Problem Statement
Dashboard metrics show:
- Avg Latency: 0 ms
- Messages Today: 0
- Response Latency Percentiles: "No latency data available"

MongoDB query confirmed all messages have `latency_ms: null`:
```javascript
db.messages.find({"latency_ms": {$ne: null}}).count()  // Returns 0
db.messages.find({"metadata.latency_ms": {$ne: null}}).count()  // Returns N > 0
```

## Code Trace

### 1. Start Time Capture
`apps/backend/src/services/streaming/streaming_handler.py:381`:
```python
stream_start_time = time.perf_counter()
```

### 2. FinalizerContext Creation
`apps/backend/src/services/streaming/streaming_handler.py:455`:
```python
ctx = FinalizerContext(
    start_time=stream_start_time,  # <-- Passed here
    ...
)
```

### 3. Latency Calculation
`apps/backend/src/services/streaming/stream_response_finalizer.py:167-169`:
```python
latency_ms = None
if ctx.start_time is not None:
    latency_ms = round((time.perf_counter() - ctx.start_time) * 1000, 2)
```

### 4. Metadata Building
`apps/backend/src/services/streaming/message_persistence.py:65-66`:
```python
@staticmethod
def build_assistant_metadata(
    ...
    latency_ms: Optional[float] = None,
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    ...
    if latency_ms is not None:
        metadata["latency_ms"] = latency_ms  # <-- Goes INTO metadata dict
    return metadata
```

### 5. Message Persistence Call (THE BUG)
`apps/backend/src/services/streaming/stream_response_finalizer.py:253-263`:
```python
assistant_message = await chat_service.add_assistant_message(
    chat_session=session,
    content=sanitized_content,
    model=model_name,
    metadata=assistant_metadata,
    # latency_ms is NOT passed here!
)
```

### 6. ChatService Signature
`apps/backend/src/services/chat_service.py:772-790`:
```python
async def add_assistant_message(
    self,
    chat_session: "ChatSessionModel",
    content: str,
    model: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    latency_ms: Optional[int] = None,  # <-- Expects top-level param
) -> ChatMessageModel:
    ...
    message = ChatMessageModel(
        ...
        latency_ms=latency_ms,  # <-- Saved to top-level field
        metadata=metadata,
    )
```

## Non-Streaming Path Analysis
`apps/backend/src/routers/chat/endpoints/message_endpoints.py:377-382`:
The non-streaming path also does NOT pass latency_ms:
```python
assistant_message = await chat_service.add_assistant_message(
    chat_session=chat_session,
    content=handler_result.sanitized_content or handler_result.content,
    model=context.model,
    metadata=message_metadata,
    # latency_ms NOT PASSED
)
```

## Dashboard Query Analysis
`apps/dashboard/queries/performance.py` (assumed) queries:
```python
# Likely queries top-level field
pipeline = [
    {"$match": {"latency_ms": {"$ne": None}}},
    ...
]
```

## Fix Implementation

### Streaming Path Fix
In `stream_response_finalizer.py`, around line 253:

**Before:**
```python
assistant_message = await chat_service.add_assistant_message(
    chat_session=session,
    content=sanitized_content,
    model=model_name,
    metadata=assistant_metadata,
)
```

**After:**
```python
assistant_message = await chat_service.add_assistant_message(
    chat_session=session,
    content=sanitized_content,
    model=model_name,
    metadata=assistant_metadata,
    latency_ms=int(latency_ms) if latency_ms else None,
)
```

### Non-Streaming Path Fix
In `message_endpoints.py`, around line 377:

**Before:**
```python
assistant_message = await chat_service.add_assistant_message(
    chat_session=chat_session,
    content=handler_result.sanitized_content or handler_result.content,
    model=context.model,
    metadata=message_metadata,
)
```

**After:**
```python
# Calculate latency for non-streaming
processing_time_ms = int((time.time() - start_time) * 1000)

assistant_message = await chat_service.add_assistant_message(
    chat_session=chat_session,
    content=handler_result.sanitized_content or handler_result.content,
    model=context.model,
    metadata=message_metadata,
    latency_ms=processing_time_ms,
)
```

## Testing Strategy
1. Unit test: Verify `add_assistant_message` is called with `latency_ms` param
2. Integration test: Send message, verify `latency_ms` field in MongoDB
3. E2E test: Verify dashboard shows latency metrics after fix

## Impact
- Dashboard Engagement tab will show actual latency metrics
- No breaking changes to API contracts
- No migration needed (new messages will have latency, old ones stay null)
