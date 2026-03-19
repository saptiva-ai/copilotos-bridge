# Plan: Production Feedback Bugs

## Status: Pending (requires research completion)

## Phase 1: Chart Re-render Fix (BUG-1)

### Files to Modify
- `apps/web/src/components/chat/ChartRenderer.tsx`
- `apps/web/src/components/chat/MessageContent.tsx`

### Changes
1. Add unique key based on message ID
2. Implement useEffect cleanup for chart state
3. Force re-mount on data change

### Tests
- `apps/web/src/components/chat/__tests__/ChartRenderer.test.tsx`

---

## Phase 2: Hallucination Guard (BUG-2)

### Files to Modify
- `plugins/bank-advisor-private/src/nlp/` (system prompt)
- `apps/backend/src/services/streaming/` (validation)

### Changes
1. Update system prompt with strict data grounding
2. Add response validation against SQL results
3. Implement "data not available" fallback

### Tests
- `tests/integration/test_hallucination_guard.py`

---

## Phase 3: Data Consistency (BUG-3)

### Files to Modify
- `apps/backend/src/services/` (context handling)

### Changes
1. Track numerical values in conversation metadata
2. Add consistency check before response
3. Alert on contradictions

### Tests
- `tests/integration/test_data_consistency.py`

---

## Validation Commands
```bash
make test T=api TEST_ARGS='-k chart'
make test T=web
make test T=api TEST_ARGS='-k hallucination'
make test T=api TEST_ARGS='-k consistency'
```
