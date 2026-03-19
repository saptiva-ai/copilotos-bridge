# Plan: Fix Canvas Panel First-Click Bug

## Overview

Fix the first-click failure on "Ver en Canvas" button by adopting hydration-safe patterns from React best practices.

---

## Phase 1: Primary Fix - Store Access Pattern

**File:** `apps/web/src/components/chat/BankChartPreview.tsx`

### Changes

1. **Remove selector-based store access** (line 45)
   ```typescript
   // DELETE this line:
   const openBankChart = useCanvasStore((state) => state.openBankChart);
   ```

2. **Update handler to use getState()** (lines 51-52)
   ```typescript
   const handleOpenInCanvas = useCallback(() => {
     // Use getState() for hydration-safe access
     useCanvasStore.getState().openBankChart(data, artifactId, messageId, false);
     // ... rest unchanged
   }, [data, artifactId, messageId]); // Remove openBankChart from deps
   ```

3. **Update comment** (line 50)
   ```typescript
   // FIX: Use getState() for hydration-safe store access (replaces BUG-02 fix)
   ```

### Validation
- [ ] TypeScript compiles without errors
- [ ] `pnpm lint` passes

---

## Phase 2: CSS Hardening

**File:** `apps/web/src/components/chat/BankChartPreview.tsx`

### Changes

1. **Add pointer-events-auto to button** (line 125-128)
   ```tsx
   <button
     onClick={handleOpenInCanvas}
     onMouseDown={(e) => e.stopPropagation()}
     className="pointer-events-auto flex items-center gap-2 ..."
   >
   ```

### Rationale (React Best Practices)
- `pointer-events-auto` ensures the button captures clicks even if parent has opacity-0
- `onMouseDown` with `stopPropagation` prevents Plotly from capturing the event in capture phase

---

## Phase 3: Verification

### Manual Testing
1. Start dev server: `make dev`
2. Open fresh browser tab (clear cache)
3. Navigate to chat
4. Request bank chart: "IMOR de BBVA últimos 12 meses"
5. Wait for chart to render
6. First-click on "Ver en Canvas"
7. **Expected:** Canvas panel opens immediately

### Automated Testing
```bash
cd apps/web && pnpm test
```

---

## Implementation Checklist

```
[ ] Phase 1: Update store access pattern
    [ ] Remove openBankChart selector
    [ ] Use getState() in handler
    [ ] Update dependency array
    [ ] Update comment

[ ] Phase 2: CSS hardening
    [ ] Add pointer-events-auto
    [ ] Add onMouseDown stopPropagation

[ ] Phase 3: Verification
    [ ] Manual test on Chrome Mac
    [ ] Run existing test suite
    [ ] No console errors
```

---

## Rollback Plan

If issues arise, revert changes and restore the previous selector-based pattern. The bug would return but functionality would be preserved.

---

## Lines Changed

| File | Lines | Type |
|------|-------|------|
| `BankChartPreview.tsx` | 45, 50-52, 59, 125-128 | Modify |

**Total:** ~10 lines modified in 1 file
