# Technical Debt & Improvements

This document tracks technical debt and improvement opportunities identified in the codebase.

## 🚨 Critical (P0)

### ✅ RESOLVED: Debug Files in Production
**Status:** Fixed in commit XXX
**Issue:** Debug/test files were in production directories
**Resolution:** Moved to `apps/api/tests/debug/`

---

## 🔴 High Priority (P1)

### God Object: State Management Store
**File:** `apps/web/src/lib/store.ts` (1,281 lines)
**Issue:** Single store handles too many responsibilities

**Current responsibilities:**
- UI state (sidebar, theme, connection)
- Chat state (messages, loading, models)
- Research state (tasks, tracking)
- History state (sessions, loading)
- Draft state (memory-only conversations)
- Settings (tokens, temperature)
- Feature flags
- Hydration state
- Optimistic updates

**Recommendation:** Split into domain-specific stores
```typescript
// Proposed refactoring
useUIStore()          // sidebar, theme, connection
useChatStore()        // messages, loading, current chat
useHistoryStore()     // sessions, CRUD operations
useResearchStore()    // tasks, tracking
useSettingsStore()    // configuration, feature flags
useDraftStore()       // draft conversations
```

**Benefits:**
- Easier to maintain and test
- Reduced re-renders
- Better separation of concerns
- Clearer domain boundaries

---

## 🟡 Medium Priority (P2)

### 1. Large Router Files
**Files:**
- `apps/api/src/routers/chat.py` (974 lines)
- `apps/api/src/routers/deep_research.py` (724 lines)
- `apps/api/src/routers/history.py` (701 lines)
- `apps/api/src/routers/reports.py` (606 lines)

**Recommendation:** Apply Controller → Service pattern
```python
# Proposed structure
/routers/chat/
  __init__.py
  basic_chat.py      # Standard chat endpoint
  streaming.py       # Streaming chat
  research.py        # Coordinated research

/services/
  chat_service.py    # Business logic
  research_coordinator.py  # Already exists ✓
```

### 2. Large UI Component
**File:** `apps/web/src/components/chat/ConversationList.tsx` (902 lines)

**Recommendation:** Split into subcomponents
```typescript
ConversationList/
  index.tsx           // Container
  ConversationItem.tsx
  ConversationDraft.tsx
  ConversationMenu.tsx
  useInfiniteScroll.tsx
  useDragAndDrop.tsx
```

---

## 🔵 Low Priority (P3)

### Unresolved TODOs

#### 1. Task Expiration Logic
**File:** `apps/api/src/routers/deep_research.py:618`
```python
"expires_at": None  # TODO: Add expiration logic
```
**Recommendation:** Implement task expiration (e.g., 24 hours for research tasks)

#### 2. Additional Health Checks
**File:** `apps/api/src/routers/health.py:80`
```python
# TODO: Add more checks (Redis, Aletheia, etc.)
```
**Recommendation:** Add Redis connectivity check and external service health checks

#### 3. Aletheia Report Fetching
**File:** `apps/api/src/routers/reports.py:70`
```python
# TODO: Fetch actual report from Aletheia artifacts
```
**Recommendation:** Implement artifact fetching from Aletheia/MinIO

#### 4. Artifact Cleanup
**File:** `apps/api/src/routers/reports.py:478`
```python
# TODO: Delete artifacts from Aletheia/MinIO storage
```
**Recommendation:** Implement artifact lifecycle management (cleanup after X days)

---

## ✅ Already Addressed

### Console.log in Production
**Status:** ✅ Resolved
**Resolution:**
- All `console.log` replaced with `logDebug` from logging system
- ESLint rule enforced: `"no-console": ["error", { "allow": ["warn", "error"] }]`
- Only `console.warn()` and `console.error()` allowed in production

---

## Next Steps

### Immediate Actions (This Sprint)
1. ✅ Remove debug files from production
2. ✅ Verify console.log enforcement
3. Document TODOs as GitHub issues

### Short-term (Next Sprint)
1. Refactor store.ts into domain-specific stores
2. Split large router files

### Long-term (Backlog)
1. Split ConversationList component
2. Implement TODO features (expiration, health checks, artifact management)

---

## Guidelines for New Code

### State Management
- Create domain-specific stores instead of adding to the main store
- Keep stores focused on a single responsibility
- Use Zustand slices for related functionality

### Router Size
- Keep routers under 300 lines
- Extract business logic to services
- Use dependency injection for testability

### Component Size
- Keep components under 300 lines
- Extract custom hooks for complex logic
- Split into subcomponents when responsibilities grow

### Logging
- Use `logDebug`, `logInfo`, `logWarn`, `logError` from logging system
- Never use `console.log` in production code
- ESLint will enforce this rule
