# Research: Production Feedback Bugs

## Status: COMPLETE - All bugs already fixed

## Investigation Summary

All 3 bugs reported on 2026-01-21 have already been fixed in subsequent releases.

---

## BUG-1: Chart Not Updating

### Status: ✅ FIXED

### Fix Details
- **File**: `apps/web/src/lib/stores/canvas-store.ts:140-147`
- **Commit**: `d1e6636c` (v1.4.18)
- **Date**: 2026-01-26

### Root Cause
The chart comparison in `openBankChart()` only checked `metric_name`, causing false positives when different queries had the same metric but different data.

### Solution
Improved comparison now checks:
```typescript
const isSameChart =
  activeArtifactId === artifactId &&
  activeBankChart?.metric_name === chartData.metric_name &&
  JSON.stringify(activeBankChart?.bank_names) === JSON.stringify(chartData.bank_names) &&
  activeBankChart?.data_as_of === chartData.data_as_of;
```

---

## BUG-2: Data Hallucination - Regional Breakdown

### Status: ✅ FIXED

### Fix Details
- **File**: `apps/backend/src/services/streaming/analytics_context.py:360-451`
- **Commit**: `da5940a7`
- **Date**: 2026-01-27

### Root Cause
LLM fabricated regional breakdown data (Centro, Norte, Sur, etc.) when user asked for it, but the database only had national-level data.

### Solution
Added `_build_grounding_instructions()` method that:
1. Detects what dimensions ARE available in the data (temporal, regional, state)
2. Explicitly tells LLM what data is NOT available
3. Provides exact response template when user asks for unavailable data
4. Includes anti-hallucination checklist

Key context added to LLM:
```
❌ DATOS QUE NO ESTÁN DISPONIBLES (NO FABRICAR):
   - Desglose por región geográfica (Centro, Norte, Sur, Occidente, Sureste)
   - Comparativos regionales
   - Distribución porcentual por región

⚠️ SI EL USUARIO PIDE DATOS NO DISPONIBLES:
   RESPONDE EXACTAMENTE: "Los datos de {metric_name} disponibles son únicamente temporales..."
```

---

## BUG-3: Data Inconsistency Across Turns

### Status: ✅ FIXED (by BUG-2 fix)

### Root Cause
Same as BUG-2 - LLM fabricated data, then when asked again, couldn't maintain consistency with the fabricated values.

### Solution
The grounding instructions from BUG-2 fix also prevent this issue by:
1. Forcing LLM to only use actual SQL results
2. Preventing fabrication of any data not in the statistics
3. Adding checklist: "¿Estoy citando valores que están en las estadísticas de arriba?"

---

## Verification

### Commits Timeline
| Date | Commit | Description |
|------|--------|-------------|
| 2026-01-21 | - | Bugs reported via production feedback |
| 2026-01-26 | `d1e6636c` | BUG-1 fix (chart comparison) |
| 2026-01-27 | `da5940a7` | BUG-2/3 fix (hallucination prevention) |

### Test Coverage
- Regression tests exist in `tests/regression/test_streaming_resilience.py`
- E2E tests cover chart rendering flow

---

## Recommendation

**Move this task to DONE** - All reported bugs have been fixed and deployed.

Consider adding specific E2E test case for regional data request to prevent regression.

## References
- Production feedback: MongoDB `message_feedback` collection
- Original report: `reports/BankAdvisor_Metrics_Report_2026-01-21.pdf`
- Fix commits: `d1e6636c`, `da5940a7`
