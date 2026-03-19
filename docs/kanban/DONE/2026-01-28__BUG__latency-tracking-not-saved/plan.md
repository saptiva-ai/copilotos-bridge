# Plan: Fix Latency Tracking

## Status: Pending

## Phase 1: Streaming Path Fix

### Files to Modify
1. `apps/backend/src/services/streaming/stream_response_finalizer.py`
   - Pass `latency_ms` as separate parameter to `add_assistant_message()`

### Implementation
```python
# Around line 253, change:
assistant_message = await chat_service.add_assistant_message(
    chat_session=session,
    content=sanitized_content,
    model=model_name,
    metadata=assistant_metadata,
    latency_ms=int(latency_ms) if latency_ms else None,  # ADD THIS
)
```

### Tests
- Run: `make test T=api TEST_ARGS='-k streaming'`
- Verify latency_ms is passed in mock assertions

## Phase 2: Non-Streaming Path Fix

### Files to Modify
1. `apps/backend/src/routers/chat/endpoints/message_endpoints.py`
   - Calculate and pass latency for non-streaming responses

2. `apps/backend/src/routers/chat_new_endpoint.py`
   - Same fix for alternate chat endpoint

### Implementation
```python
# Around line 377, add latency calculation:
processing_time_ms = int((time.time() - start_time) * 1000)

assistant_message = await chat_service.add_assistant_message(
    chat_session=chat_session,
    content=handler_result.sanitized_content or handler_result.content,
    model=context.model,
    metadata=message_metadata,
    latency_ms=processing_time_ms,  # ADD THIS
)
```

### Tests
- Run: `make test T=api TEST_ARGS='-k chat'`
- Verify integration test shows latency in response

## Phase 3: Verification

### Manual Testing
1. Send a message in chat (streaming)
2. Query MongoDB: `db.messages.findOne({"latency_ms": {$ne: null}})`
3. Verify dashboard shows latency metrics

### Deployment
- Bump backend version to 1.4.22
- Build, push, deploy following standard procedure
- Flush Redis cache after deploy

## Acceptance Criteria
- [ ] Streaming messages have `latency_ms` populated
- [ ] Non-streaming messages have `latency_ms` populated
- [ ] Dashboard "Avg Latency" shows non-zero value
- [ ] Dashboard "Response Latency Percentiles" shows data
