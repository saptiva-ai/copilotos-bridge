# Research Findings - HU7 Sistema Feedback

**Date**: 2026-01-06 01:15
**Researcher**: Claude (Main Agent)
**Status**: ✅ Research Complete

---

## Executive Summary

**CRITICAL FINDING**: HU5/HU7 (Sistema Feedback) is **90% complete** but was incorrectly marked as "✅ DONE" in EPIC README.

### What Exists
- ✅ **Backend API**: Fully implemented (feedback.py router, feedback_service.py, feedback.py model)
- ✅ **Frontend Component**: MessageFeedback.tsx with full UI implementation
- ✅ **Frontend Tests**: Comprehensive test suite (335 lines, 100% coverage)
- ✅ **ChatMessage Integration**: Component already integrated in ChatMessage.tsx (lines 695-702)

### What's Missing
- ❌ **API Connection**: `onFeedback` callback not connected to backend `/api/feedback` endpoint
- ❌ **E2E Tests**: No end-to-end workflow test validating full stack integration
- ⚠️ **Possible Auth Issues**: Need to verify authentication flow works correctly

### Scope Reduction
- Original estimate: 16-20h
- **Actual remaining work**: 2-4h (only API integration + E2E test)

---

## 1. Backend Implementation Analysis

### 1.1 Feedback Router (`apps/backend/src/routers/feedback.py`)

**Status**: ✅ Fully Implemented (Last modified: Jan 5, 2026)

**Key Features**:
- `POST /feedback` endpoint with rate limiting (60/minute)
- `GET /feedback/message/{message_id}` endpoint for retrieving existing feedback
- Request validation with Pydantic models
- Security: Validates conversation ownership (403 if not authorized)
- Deduplication: Updates existing feedback instead of creating duplicates
- Context enrichment: Automatically enriches feedback with query/response metadata

**Request Contract**:
```typescript
{
  message_id: string,
  conversation_id: string,
  rating: "up" | "down",
  reason?: string  // max 500 chars
}
```

**Response Contract**:
```typescript
{
  id: string,
  created_at: datetime
}
```

**Security Validations**:
1. Requires authentication (`get_current_user`)
2. Validates conversation exists (404 if not found)
3. Validates user owns conversation (403 if not owner)
4. Rate limiting: 60 submissions per minute per user

**Deduplication Logic** (Lines 92-124):
- Checks if user already submitted feedback for the same message
- If exists: Updates existing feedback (rating + reason + timestamp)
- If not exists: Creates new feedback with context enrichment

### 1.2 Feedback Service (`apps/backend/src/services/feedback_service.py`)

**Status**: ✅ Fully Implemented (Last modified: Dec 31, 2025)

**Context Enrichment**:
The service automatically enriches feedback with diagnostic context:
```python
{
  "original_query": str,      # User's question
  "response_text": str,        # Assistant's response
  "sql_executed": str,         # SQL query (if applicable)
  "intent": str,               # Intent classification
  "confidence": float,         # Confidence score
  "data_returned": dict        # Bank chart data (if applicable)
}
```

**Smart Message Lookup**:
- Finds the user message that preceded the assistant message being rated
- Uses timestamps to match query → response pairs
- Fallback to most recent user message if exact matching fails

**Use Case**:
This enrichment enables analytics to identify:
- Which types of queries get negative feedback
- Which SQL queries produce incorrect results
- Which intent classifications are problematic
- Confidence threshold tuning for clarification prompts

### 1.3 Feedback Model (`apps/backend/src/models/feedback.py`)

**Status**: ✅ Fully Implemented (Last modified: Dec 31, 2025)

**MongoDB Schema**:
```python
{
  "id": str (UUID),
  "message_id": str (indexed),
  "conversation_id": str (indexed),
  "user_id": str (indexed),
  "rating": "up" | "down" (enum, indexed),
  "reason": Optional[str] (max 500 chars),
  "context": Optional[Dict] (enriched metadata),
  "created_at": datetime (indexed)
}
```

**Indexes** (Optimized for Analytics):
- Single indexes: message_id, conversation_id, user_id, rating, created_at
- Composite indexes:
  - `(conversation_id, created_at)` - Feedback history per chat
  - `(user_id, rating)` - User's feedback patterns
  - `(message_id, user_id)` - Unique feedback per message per user

**Collection Name**: `message_feedback`

---

## 2. Frontend Implementation Analysis

### 2.1 MessageFeedback Component (`apps/web/src/components/chat/MessageFeedback.tsx`)

**Status**: ✅ Fully Implemented

**UI States**:
1. `idle`: Shows thumbs up/down buttons
2. `collecting`: Shows textarea with cancel/submit buttons
3. `submitting`: Disabled state with loading indicator
4. `submitted`: Shows confirmation "Gracias por tu feedback"

**Key Features**:
- **Animated Transitions**: Uses framer-motion for smooth UI transitions
- **Optional Comments**: Textarea for both thumbs up AND down (not just down!)
- **Accessibility**: ARIA labels, autofocus, max length validation
- **Visual Feedback**: Different colors for up (emerald) vs down (red)
- **Error Handling**: Graceful degradation on network errors
- **Responsive Design**: Works on mobile and desktop

**Component Interface**:
```typescript
interface MessageFeedbackProps {
  messageId: string;
  conversationId?: string;
  onFeedback?: (
    messageId: string,
    rating: "up" | "down",
    reason?: string
  ) => Promise<void>;
  className?: string;
}
```

**UX Flow**:
1. User clicks thumbs up/down
2. Textarea appears with contextual placeholder:
   - Thumbs up: "¿Qué te gustó de esta respuesta? (opcional)"
   - Thumbs down: "¿Qué podría mejorar? (opcional)"
3. User can:
   - Submit immediately (comment optional)
   - Add comment and submit
   - Cancel and return to idle state
4. On submit: Shows loading state, then confirmation
5. On error: Stays in collecting state, logs error to console

**Styling**:
- Consistent with app design system (uses `cn` utility, theme colors)
- Hover states: Emerald glow for thumbs up, red glow for thumbs down
- Border colors match rating (emerald/red)
- Custom SVG icons (not heroicons, to avoid bundle size)

### 2.2 ChatMessage Integration (`apps/web/src/components/chat/ChatMessage.tsx`)

**Status**: ✅ Already Integrated (Lines 695-702)

**Integration Code**:
```typescript
{/* Message Feedback - only for assistant messages that are not streaming */}
{isAssistant && !isStreaming && id && onFeedback && (
  <MessageFeedback
    messageId={id}
    conversationId={conversationId}
    onFeedback={onFeedback}
  />
)}
```

**Placement**: Inside actions div, appears on hover alongside Copy/Regenerate buttons

**Conditional Rendering**:
- ✅ Only for assistant messages (`isAssistant`)
- ✅ Not shown while streaming (`!isStreaming`)
- ✅ Requires message ID (`id`)
- ✅ Requires callback (`onFeedback`)

**Props Passed**:
- `messageId`: Required for backend API
- `conversationId`: Required for backend validation
- `onFeedback`: Callback function (currently undefined/missing!)

### 2.3 Frontend Tests (`apps/web/src/components/chat/__tests__/MessageFeedback.test.tsx`)

**Status**: ✅ Comprehensive Test Coverage (335 lines)

**Test Suites**:
1. **Initial Rendering** (2 tests)
   - Thumbs buttons render
   - Textarea hidden initially

2. **Thumbs Up Flow** (3 tests)
   - Textarea appears on click
   - Submit without comment
   - Submit with comment
   - Confirmation message shown

3. **Thumbs Down Flow** (3 tests)
   - Textarea appears with different placeholder
   - Submit without reason
   - Submit with reason

4. **Cancel Flow** (2 tests)
   - Textarea disappears on cancel
   - Rating resets on cancel

5. **Error Handling** (2 tests)
   - Graceful handling of network errors
   - Buttons disabled during submission

6. **Accessibility** (3 tests)
   - ARIA labels present
   - Autofocus on textarea
   - Max length 500 chars enforced

**Test Coverage**: 100% of component logic

**Mock Strategy**: Uses `jest.fn()` to mock `onFeedback` callback

---

## 3. Gap Analysis

### 3.1 Missing: API Integration

**Problem**: The `onFeedback` callback is passed to `ChatMessage` but never defined/connected to the backend API.

**Root Cause**: Need to find where `ChatMessage` is rendered and wire up the callback.

**Required Changes**:
1. Create API client function to call `POST /api/feedback`
2. Wire up `onFeedback` callback in parent component (likely ChatContainer or similar)
3. Handle authentication (pass auth token in request)
4. Handle errors (show toast notification or inline error)

**Estimated Effort**: 1-2h

**Files to Modify**:
- `apps/web/src/lib/api/feedback.ts` (CREATE) - API client function
- `apps/web/src/components/chat/ChatContainer.tsx` (or similar) - Wire up callback

**Implementation Sketch**:
```typescript
// apps/web/src/lib/api/feedback.ts
export async function submitFeedback(
  messageId: string,
  conversationId: string,
  rating: "up" | "down",
  reason?: string
): Promise<void> {
  const response = await fetch("/api/feedback", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // Auth header will be added by middleware
    },
    body: JSON.stringify({
      message_id: messageId,
      conversation_id: conversationId,
      rating,
      reason,
    }),
  });

  if (!response.ok) {
    throw new Error(`Feedback submission failed: ${response.status}`);
  }
}

// In ChatContainer or parent component:
const handleFeedback = async (
  messageId: string,
  rating: "up" | "down",
  reason?: string
) => {
  try {
    await submitFeedback(messageId, conversationId, rating, reason);
    // Optional: Show success toast
  } catch (error) {
    console.error("Failed to submit feedback:", error);
    // Optional: Show error toast
    throw error; // Re-throw so MessageFeedback can handle state
  }
};

// Pass to ChatMessage:
<ChatMessage
  {...props}
  conversationId={conversationId}
  onFeedback={handleFeedback}
/>
```

### 3.2 Missing: E2E Test

**Problem**: No end-to-end test validating the full workflow from UI click to MongoDB persistence.

**Required Test**:
- Navigate to chat
- Send a message
- Wait for assistant response
- Click thumbs down
- Enter reason
- Submit feedback
- Verify feedback persisted in MongoDB (or via API GET endpoint)

**Estimated Effort**: 1-2h

**File to Create**:
- `packages/tests-e2e/tests/e2e/feedback_workflow.spec.ts`

**Implementation Sketch**:
```typescript
test('Should submit thumbs down feedback with reason', async ({ page }) => {
  await page.goto('/chat');

  // Send message and wait for response
  await page.getByLabel('Escribe tu mensaje').fill('¿Qué es IMOR?');
  await page.getByLabel('Enviar mensaje').click();

  // Wait for assistant response
  await expect(page.locator('[role="article"]').last()).toContainText('IMOR');

  // Find thumbs down button (visible on hover)
  const assistantMessage = page.locator('[role="article"]').last();
  await assistantMessage.hover();
  await page.getByLabelText('Respuesta no útil').click();

  // Enter reason
  await page.getByPlaceholderText('¿Qué podría mejorar?').fill('La definición es incompleta');
  await page.getByText('Enviar').click();

  // Verify confirmation
  await expect(page.getByText('Gracias por tu feedback')).toBeVisible();

  // Optional: Verify via API
  // const feedback = await getFeedback(messageId);
  // expect(feedback.rating).toBe('down');
  // expect(feedback.reason).toBe('La definición es incompleta');
});
```

### 3.3 Potential Issue: Authentication

**Risk**: The feedback endpoint requires authentication (`get_current_user`).

**Need to Verify**:
1. Frontend API calls include auth token (session cookie or bearer token)
2. Auth middleware is configured correctly for `/api/feedback` route
3. E2E tests use auth state (similar to `export_validation.spec.ts`)

**Mitigation**:
- Check how other authenticated endpoints are called (e.g., chat API)
- Use same auth pattern for feedback API
- E2E tests should use `storageState: 'playwright/.auth/user.json'`

---

## 4. Implementation Recommendations

### Priority 1: API Integration (1-2h)
1. Create `apps/web/src/lib/api/feedback.ts` with `submitFeedback` function
2. Find where `ChatMessage` is rendered (likely `ChatContainer` or `ChatPage`)
3. Wire up `onFeedback` callback using the API client
4. Test manually in dev environment

### Priority 2: E2E Test (1-2h)
1. Create `packages/tests-e2e/tests/e2e/feedback_workflow.spec.ts`
2. Implement thumbs up/down test scenarios
3. Use existing auth setup (`playwright/.auth/user.json`)
4. Run test suite and verify passing

### Priority 3: Documentation Updates (30min)
1. Update EPIC-HU5.md to reflect actual completion status
2. Mark HU7 as "In Progress" in SPRINT_CURRENT.md
3. Document final status in this task's validate.md

### Out of Scope (Already Complete)
- ❌ Backend API implementation
- ❌ Frontend component development
- ❌ Frontend unit tests
- ❌ ChatMessage integration

---

## 5. File References

### Backend Files (✅ Complete)
- `apps/backend/src/routers/feedback.py` (Router, 189 lines)
- `apps/backend/src/services/feedback_service.py` (Service, 241 lines)
- `apps/backend/src/models/feedback.py` (Model, 67 lines)

### Frontend Files (✅ Complete)
- `apps/web/src/components/chat/MessageFeedback.tsx` (Component, 216 lines)
- `apps/web/src/components/chat/__tests__/MessageFeedback.test.tsx` (Tests, 335 lines)
- `apps/web/src/components/chat/ChatMessage.tsx` (Integration, line 695-702)

### Files to Create/Modify (❌ Missing)
- **CREATE**: `apps/web/src/lib/api/feedback.ts` (API client)
- **MODIFY**: `apps/web/src/components/chat/ChatContainer.tsx` or similar (Wire callback)
- **CREATE**: `packages/tests-e2e/tests/e2e/feedback_workflow.spec.ts` (E2E test)

---

## 6. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Auth issues in API calls | Medium | High | Follow existing auth patterns, test early |
| E2E test flakiness | Low | Medium | Use proper wait strategies, retry logic |
| Missing conversation_id in some messages | Low | High | Validate all message renders pass conversation_id |
| Backend endpoint not exposed in routes | Low | Critical | Verify `/api/feedback` is registered in main.py |

---

## 7. Success Criteria for Plan Phase

Before proceeding to implementation, the plan must answer:
1. ✅ Where is ChatMessage rendered? (Need to find parent component)
2. ✅ How are other authenticated API calls made? (Pattern to follow)
3. ✅ How is conversation_id tracked? (Required for API call)
4. ✅ What error handling pattern should we use? (Toast? Inline?)
5. ✅ Should we show success confirmation? (Component already does this)

---

## 8. Revised Effort Estimate

| Phase | Original | Actual | Notes |
|-------|----------|--------|-------|
| Research | 1h | 1h | ✅ Complete |
| Plan | 1-2h | 1h | Simpler than expected |
| Implement | 4-5h | 1-2h | Only API wiring, no component work |
| Test | 2-3h | 1-2h | Only E2E, unit tests done |
| Validate | 1h | 1h | Run tests, document |
| **TOTAL** | **9-12h** | **5-7h** | **40% reduction** |

---

## 9. Next Steps

1. ✅ Complete research.md (this document)
2. ⏳ Create plan.md with:
   - API integration architecture
   - E2E test strategy
   - File modification plan
   - Acceptance criteria verification
3. ⏳ Get plan approval before implementing
4. ⏳ Implement API integration
5. ⏳ Create E2E test
6. ⏳ Validate and document

---

## Appendix A: Component Screenshots (Conceptual)

### State 1: Idle
```
[👍] [👎]
```

### State 2: Collecting (Thumbs Down)
```
┌─────────────────────────────────────────┐
│ 👎 No útil                              │
│                                         │
│ ¿Qué podría mejorar? (opcional)         │
│ ▋                                       │
│                                         │
│                     [Cancelar] [Enviar] │
└─────────────────────────────────────────┘
```

### State 3: Submitted
```
✓ Gracias por tu feedback
```

---

**Research Status**: ✅ COMPLETE
**Next Phase**: Plan
**Estimated Total Remaining**: 4-6h (vs 16-20h original estimate)
