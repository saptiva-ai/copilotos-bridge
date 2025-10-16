# Technical Debt & Architecture Improvements

This document tracks identified architectural improvements and technical debt items.

## Priority Levels
- **P0**: Critical - Impacts performance or user experience
- **P1**: High - Should be addressed soon
- **P2**: Medium - Nice to have
- **P3**: Low - Future consideration

---

## ✅ COMPLETED

### P0: God Object in State Management
**Status**: ✅ COMPLETED (2025-10-07)
**Commit**: `7606915` - refactor(stores): split monolithic store into 6 specialized stores

**Problem**: `store.ts` (1,554 lines) violated Single Responsibility Principle

**Solution**: Split into 6 specialized Zustand stores:
- UIStore (104 lines)
- SettingsStore (91 lines)
- ResearchStore (68 lines)
- DraftStore (121 lines)
- ChatStore (406 lines)
- HistoryStore (338 lines)

**Benefits**:
- Better performance (selective re-renders)
- Easier testing and maintenance
- Clear separation of concerns

---

## 🔴 HIGH PRIORITY (P1)

### P1-001: Monolithic Router - chat.py (1,040 lines)
**File**: `apps/api/src/routers/chat.py`
**Estimated Effort**: 4-6 hours

**Problem**: Single file handles multiple responsibilities:
- Chat messaging (POST /chat)
- Model escalation (POST /chat/{id}/escalate)
- History retrieval (GET /history/{id})
- Session CRUD (GET /sessions, PATCH, DELETE)
- Research integration (GET /sessions/{id}/research)

**Proposed Solution**:
```
apps/api/src/routers/chat/
  __init__.py          # Router aggregator
  messaging.py         # Chat and escalation endpoints
  history.py           # History retrieval
  sessions.py          # Session CRUD operations

apps/api/src/services/
  chat_service.py      # Shared business logic
```

**Benefits**:
- Easier to test individual endpoints
- Better code organization
- Facilitates team collaboration

**Implementation Steps**:
1. Extract shared business logic to `chat_service.py`
2. Split endpoints into focused modules
3. Create aggregator in `__init__.py`
4. Update `main.py` router registration
5. Run existing tests to verify no regressions

---

### P1-002: Monolithic Router - deep_research.py (724 lines)
**File**: `apps/api/src/routers/deep_research.py`
**Estimated Effort**: 3-4 hours

**Problem**: Handles both research execution and result retrieval in single file

**Proposed Solution**:
```
apps/api/src/routers/deep_research/
  __init__.py
  execution.py         # POST /research/start
  results.py           # GET /research/{id}, /research/{id}/stream
  artifacts.py         # GET /research/{id}/artifacts
```

---

### P1-003: Monolithic Router - history.py (701 lines)
**File**: `apps/api/src/routers/history.py`
**Estimated Effort**: 3-4 hours

**Problem**: Complex history queries and event handling in single file

**Proposed Solution**:
```
apps/api/src/routers/history/
  __init__.py
  queries.py           # GET /history endpoints
  events.py            # Event creation and filtering
```

---

## 🟡 MEDIUM PRIORITY (P2)

### P2-001: Large UI Component - ConversationList.tsx (902 lines)
**File**: `apps/web/src/components/chat/ConversationList.tsx`
**Estimated Effort**: 2-3 hours

**Problem**: Monolithic component handles:
- List rendering
- Drag & drop
- Infinite scroll
- Context menus
- Optimistic updates
- Draft conversations

**Proposed Solution**:
```
ConversationList/
  index.tsx                 # Container (orchestration)
  ConversationItem.tsx      # Single conversation card
  ConversationDraft.tsx     # Draft conversation badge
  ConversationMenu.tsx      # Context menu
  ConversationSkeleton.tsx  # Loading state
  useInfiniteScroll.ts      # Custom hook
  useDragAndDrop.ts         # Custom hook
```

**Benefits**:
- Easier to test individual components
- Better performance with React.memo
- Reusable subcomponents
- Simplified state management

---

## 🟢 LOW PRIORITY (P3)

### P3-001: Unresolved TODOs in Production Code

**Files with TODOs**:

#### apps/api/src/routers/health.py
```python
# TODO: Add more checks (Redis, Aletheia, etc.)
```
**Recommendation**: Implement comprehensive health checks for all external dependencies

#### apps/api/src/routers/reports.py
```python
# TODO: Fetch actual report from Aletheia artifacts
# TODO: Delete artifacts from Aletheia/MinIO storage
```
**Recommendation**: Implement artifact management system

#### apps/api/src/routers/deep_research.py
```python
# TODO: Add expiration logic
```
**Recommendation**: Implement TTL for research tasks

**Action Items**:
1. Create GitHub Issues for each TODO
2. Prioritize based on impact
3. Add to sprint backlog

---

### P3-002: Console.log Statements in Production
**Estimated Effort**: 30 minutes

**Problem**: 15+ console.log statements found in production code

**Solution**:
1. Add ESLint rule: `"no-console": ["error", { allow: ["warn", "error"] }]`
2. Replace with structured logging (`logDebug`, `logInfo`)
3. Add pre-commit hook to prevent new console.logs

---

### P3-003: Missing Pre-commit Hooks
**Estimated Effort**: 1 hour

**Recommended Setup**:
```bash
npm install --save-dev husky lint-staged
```

```json
// package.json
"lint-staged": {
  "*.{ts,tsx}": [
    "eslint --fix",
    "prettier --write"
  ],
  "*.py": [
    "black",
    "flake8"
  ]
}
```

---

## 📊 PERFORMANCE OPTIMIZATIONS

### PERF-001: React Components - Add Memoization
**Files**: ConversationList, ChatView, MessageList
**Effort**: 2 hours

**Solution**:
```tsx
export const ConversationItem = React.memo(({ session }) => {
  // Component logic
}, (prevProps, nextProps) => {
  // Custom comparison for when to skip re-render
  return prevProps.session.id === nextProps.session.id &&
         prevProps.session.updated_at === nextProps.session.updated_at
})
```

---

### PERF-002: Code Splitting for Routes
**Effort**: 1 hour

**Solution**:
```tsx
const DeepResearch = lazy(() => import('./pages/DeepResearch'))
const Reports = lazy(() => import('./pages/Reports'))
```

---

## 🔐 SECURITY IMPROVEMENTS

### SEC-001: Add Rate Limiting
**Endpoints**: /chat, /deep_research/start
**Effort**: 2 hours

**Solution**: Implement `slowapi` middleware
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/chat")
@limiter.limit("30/minute")
async def send_chat_message(...):
    ...
```

---

### SEC-002: Input Sanitization Enhancement
**Effort**: 1 hour

**Current**: Basic sanitization in `text_sanitizer.py`
**Recommendation**: Add DOMPurify equivalent for markdown rendering

---

## 📝 DOCUMENTATION

### DOC-001: API Documentation
**Effort**: 3 hours

**Action Items**:
1. Add OpenAPI descriptions to all endpoints
2. Include request/response examples
3. Document error codes
4. Add authentication section

FastAPI supports this natively:
```python
@router.post(
    "/chat",
    summary="Send chat message",
    description="Send a message and get AI response...",
    response_description="Chat response with message ID",
)
```

---

## 🧪 TESTING

### TEST-001: Unit Tests for New Stores
**Files**: All stores in `src/lib/stores/`
**Effort**: 4 hours

**Example**:
```typescript
describe('ChatStore', () => {
  it('should add message to store', () => {
    const { result } = renderHook(() => useChatStore())
    act(() => {
      result.current.addMessage({
        id: '1',
        content: 'Hello',
        role: 'user',
        timestamp: new Date().toISOString()
      })
    })
    expect(result.current.messages).toHaveLength(1)
  })
})
```

---

### TEST-002: E2E Tests for Critical Flows
**Effort**: 6 hours

**Flows to Cover**:
1. User sends message → receives response
2. User initiates deep research → monitors progress → receives results
3. User creates/renames/deletes conversation

---

## 📈 METRICS & MONITORING

### MON-001: Frontend Error Tracking
**Recommendation**: Integrate Sentry or similar

**Implementation**:
```tsx
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1,
})
```

---

### MON-002: Performance Monitoring
**Metrics to Track**:
- Time to First Byte (TTFB)
- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP)
- API response times
- Error rates by endpoint

---

## 🎯 IMPLEMENTATION ROADMAP

### Sprint 1 (Current)
- [x] P0: Store refactoring (COMPLETED)
- [ ] P1-001: chat.py refactoring
- [ ] P1-002: deep_research.py refactoring
- [ ] P1-003: history.py refactoring

### Sprint 2
- [ ] P2-001: ConversationList refactoring
- [ ] PERF-001: React memoization
- [ ] SEC-001: Rate limiting
- [ ] TEST-001: Store unit tests

### Sprint 3
- [ ] P3-001: Resolve all TODOs
- [ ] DOC-001: API documentation
- [ ] MON-001: Error tracking
- [ ] TEST-002: E2E tests

---

## 📞 CONTACT & DISCUSSION

For questions or discussions about these items:
- Technical lead: Create GitHub Discussion
- Urgent issues: #copilotos-dev Slack channel
- Planning: Include in sprint planning meetings

---

**Last Updated**: 2025-10-07
**Next Review**: 2025-10-14
