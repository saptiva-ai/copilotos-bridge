# BankAdvisor - Frontend Integration

This document describes how BankAdvisor is integrated into the Octavios UI.

---

## Overview

BankAdvisor is integrated as a **tool** in the Octavios toolbar, similar to Deep Research, Web Search, and Canvas.

When activated, the user can ask banking questions in natural language and receive interactive Plotly charts.

---

## User Flow

```
1. User clicks [+] button in chat
   ↓
2. ToolMenu appears with "BankAdvisor" option
   ↓
3. User selects "BankAdvisor"
   ↓
4. Visual chip appears: [BankAdvisor ✕]
   ↓
5. User types query: "IMOR de INVEX en 2024"
   ↓
6. Query sent with metadata: {"tools": ["bank-advisor"]}
   ↓
7. Backend routes to BankAdvisor MCP service
   ↓
8. SSE stream returns bank_chart event
   ↓
9. BankChartMessage component renders Plotly chart
```

---

## Frontend Components

### 1. Tool Registration

**File**: `apps/web/src/types/tools.tsx`

```typescript
export type ToolId = ... | "bank-advisor";

const BankAdvisorIcon = ({ className }: IconProps) => (
  <svg>...</svg>  // BarChart3 icon
);

export const TOOL_REGISTRY: Record<ToolId, Tool> = {
  // ... other tools ...
  "bank-advisor": {
    id: "bank-advisor",
    label: "BankAdvisor",
    Icon: BankAdvisorIcon,
  },
};
```

### 2. Feature Flag

**File**: `apps/web/src/lib/feature-flags.ts`

```typescript
export const featureFlags = {
  // ... other flags ...
  bankAdvisor: toBool(process.env.NEXT_PUBLIC_FEATURE_BANK_ADVISOR, false),
};

const defaultToolVisibility: Record<ToolId, boolean> = {
  // ... other tools ...
  "bank-advisor": featureFlags.bankAdvisor,
};
```

### 3. Environment Variable

**File**: `apps/web/.env.local`

```bash
NEXT_PUBLIC_FEATURE_BANK_ADVISOR=true
```

### 4. Rendering Component

**File**: `apps/web/src/components/chat/BankChartMessage.tsx` (already exists)

This component receives `bank_chart` SSE events and renders Plotly charts.

---

## How It Works

### Activation

1. **ToolMenu** (`apps/web/src/components/chat/ToolMenu/ToolMenu.tsx`) automatically:
   - Reads from `TOOL_REGISTRY`
   - Filters by visibility (feature flags + user settings)
   - Renders as menu items

2. **Selection**:
   - User clicks "BankAdvisor" in menu
   - Tool added to `selectedTools` state array
   - Visual chip rendered below textarea

3. **Visual Indicator**:
   ```tsx
   <div className="flex gap-2 flex-wrap">
     <ToolChip tool="bank-advisor" onRemove={...}>
       <BankAdvisorIcon />
       BankAdvisor ✕
     </ToolChip>
   </div>
   ```

### Message Flow

When user submits a message with BankAdvisor active:

```typescript
// Frontend sends
{
  "message": "IMOR de INVEX en 2024",
  "metadata": {
    "tools": ["bank-advisor"]
  }
}

// Backend detects and routes to MCP
POST http://localhost:8002/rpc
{
  "method": "tools/call",
  "params": {
    "name": "bank_analytics",
    "arguments": {"metric_or_query": "IMOR de INVEX en 2024"}
  }
}

// SSE stream returns
event: bank_chart
data: {
  "data": {"values": [...]},
  "plotly_config": {...}
}

// Frontend renders with BankChartMessage.tsx
```

---

## Configuration

### Enable/Disable BankAdvisor

**Development**:
```bash
# apps/web/.env.local
NEXT_PUBLIC_FEATURE_BANK_ADVISOR=true
```

**Production**:
```bash
# Set in deployment environment
export NEXT_PUBLIC_FEATURE_BANK_ADVISOR=true
```

### User Settings

Users can toggle visibility in settings:
- Settings → Tools → BankAdvisor [ON/OFF]
- Stored in `settingsStore.toolVisibility["bank-advisor"]`

---

## Visual Design

### Icon

- **Type**: BarChart3 (SVG)
- **Style**: Consistent with other tool icons
- **Dimensions**: 24x24px viewBox
- **Stroke**: 1.8px width

### Chip (Active State)

```
┌──────────────────────┐
│ [📊] BankAdvisor  ✕  │
└──────────────────────┘
```

- Background: `bg-blue-500/10`
- Text: `text-blue-600`
- Border: `border border-blue-500/20`
- Hover: Darken background

---

## Testing

### Manual Test

1. Start frontend:
   ```bash
   cd apps/web
   pnpm dev
   ```

2. Open chat at http://localhost:3000

3. Click [+] button → Should see "BankAdvisor" in menu

4. Select BankAdvisor → Chip should appear

5. Type query: "IMOR de INVEX en 2024" → Should receive chart

### Automated Test

```typescript
// apps/web/src/components/chat/__tests__/ToolMenu.test.tsx
describe("BankAdvisor tool", () => {
  it("should appear in menu when feature flag enabled", () => {
    // Mock feature flag
    process.env.NEXT_PUBLIC_FEATURE_BANK_ADVISOR = "true";

    // Render ToolMenu
    const { getByText } = render(<ToolMenu />);

    // Check BankAdvisor appears
    expect(getByText("BankAdvisor")).toBeInTheDocument();
  });
});
```

---

## Troubleshooting

### "BankAdvisor not appearing in menu"

1. Check feature flag:
   ```bash
   echo $NEXT_PUBLIC_FEATURE_BANK_ADVISOR  # Should be "true"
   ```

2. Restart dev server:
   ```bash
   pnpm dev
   ```

### "Chart not rendering"

1. Check backend is running:
   ```bash
   curl http://localhost:8002/health
   ```

2. Check SSE stream in browser DevTools:
   - Network tab → Filter "EventStream"
   - Should see `bank_chart` events

### "Type errors in tools.tsx"

- Normal when compiling single TSX file
- Run full type check: `pnpm tsc --noEmit` (from apps/web)

---

## Next Steps (Optional Enhancements)

### 1. BankAdvisor Wizard

Create a modal for configuration before activation:

```tsx
// apps/web/src/components/chat/BankAdvisorWizard.tsx
export function BankAdvisorWizard({ onSubmit }: Props) {
  return (
    <Dialog>
      <h2>Configure BankAdvisor</h2>

      <Select label="Banco">
        <option>INVEX</option>
        <option>SISTEMA</option>
      </Select>

      <Select label="Tipo de análisis">
        <option>Evolución temporal</option>
        <option>Comparación</option>
        <option>Ranking</option>
      </Select>

      <DateRange label="Período" />

      <Button onClick={onSubmit}>Activar</Button>
    </Dialog>
  );
}
```

### 2. Query Suggestions

Show suggested queries when BankAdvisor is active:

```tsx
<div className="suggestions">
  <p>Prueba preguntar:</p>
  <button>"IMOR de INVEX en 2024"</button>
  <button>"Cartera comercial vs sistema"</button>
  <button>"Reservas totales"</button>
</div>
```

### 3. Chart Export

Add export button to BankChartMessage:

```tsx
<button onClick={exportAsPNG}>
  Exportar gráfico
</button>
```

---

## Files Modified

| File | Change | Lines |
|------|--------|-------|
| `apps/web/src/types/tools.tsx` | Add bank-advisor to registry | +18 |
| `apps/web/src/lib/feature-flags.ts` | Add bankAdvisor flag | +2 |
| `apps/web/.env.local.example` | Add BANK_ADVISOR env var | +1 |

**Total**: 3 files, 21 lines added

---

## Status

✅ Integration complete
✅ Feature flag configured
✅ Icon designed
✅ Ready for testing

To activate: Set `NEXT_PUBLIC_FEATURE_BANK_ADVISOR=true` and restart frontend.
