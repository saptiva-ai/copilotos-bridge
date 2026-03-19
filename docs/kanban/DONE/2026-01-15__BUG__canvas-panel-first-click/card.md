# BUG-2026-01-15: Canvas Panel Button First-Click Failure

## Status
- **Priority:** High
- **Phase:** Validate
- **Reporter:** Jaziel David
- **Created:** 2026-01-15
- **Updated:** 2026-01-20 (Fix v2)

## Problem Statement

The "Ver en Canvas" button for Plotly charts fails to respond on the first click for some users. A page reload or conversation change is required before the event handler properly attaches.

### Reproduction Steps
1. Open a new conversation
2. Ask for a bank chart (e.g., "IMOR de BBVA")
3. Wait for chart to render in `BankChartPreview`
4. Hover over chart and click "Ver en Canvas" immediately
5. **Expected:** Canvas panel opens
6. **Actual:** Nothing happens on first click

### Affected Components
- `apps/web/src/components/chat/BankChartPreview.tsx` (primary)
- `apps/web/src/lib/stores/canvas-store.ts` (store)
- `apps/web/src/components/canvas/canvas-panel.tsx` (panel)

## Root Cause Analysis

Three compounding issues identified:

### 1. Zustand `persist` Middleware Hydration Race (Primary)
```typescript
// BankChartPreview.tsx:45 - Uses selector-based access
const openBankChart = useCanvasStore((state) => state.openBankChart);

// BankAdvisorResponse.tsx:76-78 - Uses direct getState() (works correctly)
useCanvasStore.getState().openBankChart(...)
```
The `persist` middleware rehydrates asynchronously from localStorage. During hydration, the selector may return a stale function reference.

### 2. CSS Overlay Opacity Transition
```tsx
// BankChartPreview.tsx:124
<div className="absolute inset-0 ... opacity-0 ... hover:opacity-100">
  <button onClick={handleOpenInCanvas}>
```
On first hover, CSS transitions may not have settled, causing click events to be missed on some browsers (Chrome Mac).

### 3. Plotly Z-Index Competition
The Plotly chart with `staticPlot: true` may capture pointer events before they reach the overlay button.

## Fix Strategy (React Best Practices)

Apply patterns from `react-best-practices` skill:

### Pattern 1: Direct Store Access (Critical)
Avoid selector closures for event handlers by using `getState()`:
```typescript
// Before (problematic)
const openBankChart = useCanvasStore((s) => s.openBankChart);
const handler = useCallback(() => {
  openBankChart(...); // May be stale during hydration
}, [openBankChart]);

// After (fixed)
const handler = useCallback(() => {
  useCanvasStore.getState().openBankChart(...); // Always current
}, [/* no store deps */]);
```

### Pattern 2: Ensure Pointer Events (Medium)
```tsx
<button className="pointer-events-auto ...">
```

### Pattern 3: Event Capture Phase (Low)
```tsx
onMouseDown={(e) => e.stopPropagation()}
```

## Files to Modify

| File | Change |
|------|--------|
| `BankChartPreview.tsx` | Use `getState()` pattern, add `pointer-events-auto` |
| `canvas-store.ts` | No changes needed |

## Acceptance Criteria

- [ ] First click on "Ver en Canvas" opens panel reliably
- [ ] Works on Chrome Mac (primary regression browser)
- [ ] No console errors related to undefined handlers
- [ ] Existing tests pass

## References

- React Best Practices Skill: `~/.claude/skills/react-best-practices/`
- Hydration Pattern: `references/rules/rendering-hydration-no-flicker.md`
- Event Handler Refs: `references/rules/advanced-event-handler-refs.md`
- Existing fix comment: `BUG-02 FIX` in `BankChartPreview.tsx:50`

---

## Fix v2 (2026-01-20)

### Root Cause (Revised)

The original fix (getState() pattern + pointer-events-auto) was insufficient. The real problem is the **CSS overlay architecture**:

```tsx
// BEFORE (problematic)
<div className="opacity-0 ... hover:opacity-100">  // Parent controls ALL opacity
  <button className="pointer-events-auto">          // Button inherits opacity-0!
```

**Why it fails:**
1. CSS `opacity` is inherited - setting `opacity-0` on parent makes ALL children invisible
2. `pointer-events-auto` doesn't guarantee click registration on elements with near-zero opacity
3. Chrome Mac has specific compositor timing issues with opacity transitions

### Fix v2 Strategy

**Separate visual layer from interactive layer:**

```tsx
// AFTER (fixed)
<div className="group/overlay">                     // Container, no opacity control
  <div className="pointer-events-none opacity-0    // Visual layer only
       group-hover/overlay:opacity-100" />
  <button className="z-10 opacity-0                // Button controls OWN opacity
       group-hover/overlay:opacity-100">
```

### Changes Made

| File | Change |
|------|--------|
| `BankChartPreview.tsx:127-141` | Separated overlay into visual + interactive layers |
| `BankChartPreview.test.tsx:300-317` | Updated test to verify new layer architecture |

### Test Results

- 14/14 tests passing
- Manual validation pending (requires production deployment)
