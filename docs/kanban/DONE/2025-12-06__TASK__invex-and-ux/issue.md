# ISSUE-006: INVEX Generalization & UX Issues

**Created:** 2026-01-09
**Updated:** 2026-01-10
**Status:** Complete
**Priority:** P0 (BA-001, BA-003) / P1 (BA-002, BA-004)

---

## Executive Summary

| Ticket | Title | Severity | Status | Commit |
|--------|-------|----------|--------|--------|
| BA-001 | ICAP Hallucination (RAG Grounding) | P0 | ✅ **FIXED** | `45a75723` |
| BA-002 | INVEX Default Bias | P1 | ✅ **FIXED** | `5ef371e5`, `45a75723` |
| BA-003 | SQL Exposed in Chat | P0 | ✅ **FIXED** | `3fb9284e`, `72c2c79f`, `198121a6` |
| BA-004 | Chart "Abrir" No Feedback | P1 | ✅ **IMPLEMENTED** | `079db10e` |

### Implementation Summary (2026-01-10)

**BA-001 & BA-002 Fixes:**
- Added `DATA_INDICATOR_REGEX` to `is_knowledge_query()` to detect data vs knowledge queries
- Possessives (mi, mis), bank references (de INVEX), action verbs (dame, muéstrame) now correctly route to data flow
- Config files updated: `bankadvisor.yaml`, `invex.yaml` with `apply_bank_default: false`
- Test results: Happy Path 47/47 ✅, Bug Fixes Suite 18/18 ✅

**BA-003 (Multi-layer SQL Stripping):**
- **Backend** (`text_sanitizer.py`): Regex patterns for SQL code blocks + multi-line SQL + orphaned intro phrases
- **Backend** (`streaming_handler.py`): `sanitize_response_content()` called before message persistence
- **Frontend** (`MarkdownMessage.tsx`): `stripSqlFromContent()` with `skipSqlStripping` optimization during streaming
- **Performance**: SQL stripping only runs AFTER streaming completes (not on each chunk)
- SQL remains visible in canvas panel (intended behavior)

**BA-004 (Already Implemented):**
- `chartHighlighted` state added to `canvas-store.ts` with 600ms auto-clear timeout
- Visual feedback: `ring-2 ring-primary ring-offset-1 animate-pulse` in `canvas-panel.tsx`
- Triggers on: new chart open AND re-selecting same chart
- Unit tests: 4 new tests in `canvas-store.bankChart.test.ts` (commit `079db10e`)

---

## BA-001: RAG Grounding (ICAP Hallucination)

### Problem Statement

Queries tipo glosario (ej. "¿Qué es ICAP?") pueden devolver definiciones incorrectas porque el retrieval usa solo similitud semántica sin validar que el chunk contenga el término buscado.

### Evidence

| Location | Issue |
|----------|-------|
| `knowledge_handler.py:100-105` | Retrieval por `min_similarity=0.65` sin term validation |
| `knowledge_handler.py:240-247` | Fuentes vienen del retrieval (pueden ser irrelevantes) |
| `intent_service.py:53-81` | Router formal OK (`BANK_KNOWLEDGE` intent) |

### Reproduction

```bash
# Query: "¿Qué es ICAP?"
# Observed: Puede devolver definición de IMOR u otro término similar
# Expected: Definición correcta de ICAP con fuentes coherentes
```

### Root Cause

```python
# knowledge_handler.py:100-105
matches = await self.ontology_service.search_terms(
    term_query,
    top_k=3,
    min_similarity=0.65,  # ← Similarity-only, NO term containment check
    exclude_conceptual=False
)
# Si "IMOR" tiene similarity 0.72 y "ICAP" tiene 0.68, devuelve IMOR
```

### Patch Plan

**File:** `plugins/bank-advisor-private/src/bankadvisor/handlers/knowledge_handler.py`

```python
# ADD: Validation method
def _validate_term_in_chunk(self, term: str, match: OntologyTerm) -> bool:
    """Validate match contains term via name, aliases, or definition."""
    term_normalized = self._normalize_text(term)

    # Check name
    if term_normalized in self._normalize_text(match.name or ""):
        return True

    # Check aliases (if exists)
    if hasattr(match, 'aliases') and match.aliases:
        for alias in match.aliases:
            if term_normalized in self._normalize_text(alias):
                return True

    # Check definition
    if term_normalized in self._normalize_text(match.definition or ""):
        return True

    # Check alias map (ICAP ↔ Índice de Capitalización)
    return self._check_alias_map(term, match)

# MODIFY: Line 107-118
if matches:
    validated = [m for m in matches if self._validate_term_in_chunk(term_query, m)]
    if validated:
        return self._format_response(validated[0])
    else:
        logger.warning("hu4.no_validated_matches", term=term_query, raw=len(matches))
        return self._format_no_match_with_clarification(term_query)
```

### Acceptance Criteria

- [ ] "¿Qué es ICAP?" NUNCA devuelve definición de IMOR o similar
- [ ] Si no hay match válido, responde con clarificación (no inventa)
- [ ] Fuentes citadas corresponden al término consultado
- [ ] Alias map incluye: ICAP ↔ Índice de Capitalización, IMOR ↔ Índice de Morosidad, etc.

### Tests

```python
# Unit test
def test_icap_not_returns_imor_definition():
    """ICAP query should not return IMOR chunk even if similarity is high."""
    handler = KnowledgeHandler()
    imor_chunk = OntologyTerm(name="IMOR", definition="Índice de morosidad...")
    assert not handler._validate_term_in_chunk("ICAP", imor_chunk)

def test_icap_matches_via_alias():
    """ICAP should match 'Índice de Capitalización' via alias map."""
    handler = KnowledgeHandler()
    icap_chunk = OntologyTerm(name="Índice de Capitalización", definition="...")
    assert handler._validate_term_in_chunk("ICAP", icap_chunk)
```

---

## BA-002: INVEX Default Bias

### Problem Statement

Aunque `apply_bank_default=False` está configurado, persisten hardcodes que fuerzan INVEX cuando no se detecta banco, rompiendo multi-tenancy.

### Evidence

| Location | Status | Issue |
|----------|--------|-------|
| `BankAdvisorHints.tsx:107-113` | ✅ Fixed | Questions ahora bank-neutral |
| `runtime_config.py:151-159` | ✅ Fixed | `apply_bank_default=False` |
| `runtime_config.py:75-77` | ⚠️ Pending | `default="INVEX"` |
| `main.py:1008` | ⚠️ Pending | `else "INVEX"` fallback |
| `main.py:1025` | ⚠️ Pending | `else "INVEX"` fallback |

### Reproduction

```bash
# Query: "Dame el IMOR" (sin especificar banco)
# Observed: Usa INVEX por default
# Expected: Trigger clarificación "¿De qué banco?"
```

### Root Cause

```python
# runtime_config.py:75-77
@property
def primary_bank(self) -> str:
    return os.environ.get("PRIMARY_BANK") or self._get("banks", "primary", default="INVEX")
    # ← Still defaults to INVEX

# main.py:1008,1025
primary_bank=entities.banks[0] if entities.banks else "INVEX",
# ← Fallback hardcoded
```

### Patch Plan

**File 1:** `plugins/bank-advisor-private/src/bankadvisor/runtime_config.py:77`

```python
# BEFORE:
return os.environ.get("PRIMARY_BANK") or self._get("banks", "primary", default="INVEX")

# AFTER:
return os.environ.get("PRIMARY_BANK") or self._get("banks", "primary", default="")
```

**File 2:** `plugins/bank-advisor-private/src/main.py:1008,1025`

```python
# BEFORE:
primary_bank=entities.banks[0] if entities.banks else "INVEX",

# AFTER:
primary_bank=entities.banks[0] if entities.banks else "",
```

**Downstream Guard:** Verify consumers of `primary_bank` handle `""` correctly:
- Should trigger `needs_clarification` flow
- Should NOT generate `WHERE banco IN ('')`

### Acceptance Criteria

- [ ] No `default="INVEX"` en código productivo (solo en profiles)
- [ ] No `else "INVEX"` fallbacks en main.py
- [ ] Query sin banco activa flujo de clarificación
- [ ] Tenant INVEX-only funciona via `config/profiles/invex.yaml`

### Tests

```python
# Unit test
def test_open_query_triggers_clarification():
    """Query without bank should trigger clarification, not default to INVEX."""
    result = parse_query("Dame el IMOR")
    assert result.needs_clarification or result.primary_bank == ""
    assert result.primary_bank != "INVEX"

# Smoke test (CI)
# smoke_no_invex_hardcode.sh - fails if finds default="INVEX" in production code
```

---

## BA-003: SQL Exposed to Users

### Problem Statement

La sección "Consulta SQL" se muestra a TODOS los usuarios sin verificar rol o flag de debug. Esto es leakage de implementación interna.

### Evidence

| Location | Issue |
|----------|-------|
| `BankChartCanvasView.tsx:414-443` | Renderiza SQL sin gating |
| `.env.development.example:42` | `NEXT_PUBLIC_ENABLE_DEBUG_MODE=true` existe pero no conectado |
| `streaming_handler.py:1847` | Prompt dice "NO digas la consulta SQL" pero BE la envía |

### Reproduction

```bash
# Generar cualquier chart
# Observed: Bloque "Consulta SQL" visible para todos
# Expected: Solo visible para admin/developer o debug mode
```

### Root Cause

```tsx
// BankChartCanvasView.tsx:414-443
{/* SQL Query Section - Below Chart (ALWAYS VISIBLE) */}
<div className="space-y-3 pt-4 border-t border-border">
  <span className="font-medium">Consulta SQL</span>  {/* NO GATING */}
  {sanitizedSQL && <pre>{sanitizedSQL}</pre>}
</div>
```

### Patch Plan

**FE (Quick Win):** `apps/web/src/components/canvas/BankChartCanvasView.tsx`

```tsx
// ADD at component top:
const showDebugInfo = process.env.NEXT_PUBLIC_ENABLE_DEBUG_MODE === 'true';

// MODIFY line 414:
{showDebugInfo && (
  <div className="space-y-3 pt-4 border-t border-border">
    {/* SQL section */}
  </div>
)}
```

**BE (Hardening):** No enviar `sql_query` en payload para usuarios no autorizados

```python
# streaming_handler.py o donde se serializa bank_chart_data
if not user.is_admin and not settings.debug_mode:
    bank_chart_data.pop("sql_query", None)
    if "metadata" in bank_chart_data:
        bank_chart_data["metadata"].pop("sql_generated", None)
```

### Acceptance Criteria

- [ ] `debug=false` → "Consulta SQL" no aparece en UI
- [ ] `debug=true` o `role=admin` → SQL visible
- [ ] (Hardening) BE no envía SQL a usuarios no autorizados

### Tests

```typescript
// FE unit test
describe('SQL visibility', () => {
  it('hides SQL when debug mode is false', () => {
    process.env.NEXT_PUBLIC_ENABLE_DEBUG_MODE = 'false';
    render(<BankChartCanvasView data={mockData} />);
    expect(screen.queryByText('Consulta SQL')).not.toBeInTheDocument();
  });

  it('shows SQL when debug mode is true', () => {
    process.env.NEXT_PUBLIC_ENABLE_DEBUG_MODE = 'true';
    render(<BankChartCanvasView data={mockData} />);
    expect(screen.getByText('Consulta SQL')).toBeInTheDocument();
  });
});
```

---

## BA-004: Chart "Abrir" No Feedback (UX)

### Problem Statement

El botón "Abrir" funciona técnicamente pero usuarios reportan que "no hace nada". Es un problema de percepción: falta feedback visual cuando el sidebar ya está abierto o el chart ya está activo.

### Evidence

| Location | Finding |
|----------|---------|
| `canvas-store.ts:127-169` | `openBankChart()` sets `isSidebarOpen: true` ✅ |
| `providers.tsx:24` | `refetchOnWindowFocus: false` ✅ |
| `BankChartPreview.tsx:51-59` | Calls `openBankChart()` correctly ✅ |

**Conclusion:** No bug técnico. Issue de percepción UX.

### Root Cause

```typescript
// canvas-store.ts:127
openBankChart: (chartData, artifactId, messageId, autoOpen = false) => {
  set({
    activeBankChart: chartData,
    isSidebarOpen: true,  // ← Works, but no visual feedback if already open
  });
};
```

Escenarios problemáticos:
1. Sidebar ya abierto → no hay cambio visible
2. Chart ya activo → parece que no pasó nada
3. Sidebar fuera de viewport → usuario no lo ve

### Patch Plan

**File 1:** `apps/web/src/lib/stores/canvas-store.ts`

```typescript
// ADD state
chartHighlighted: boolean;

// MODIFY openBankChart:
openBankChart: (chartData, artifactId, messageId, autoOpen = false) => {
  const { activeBankChart } = get();

  // If same chart, trigger highlight animation
  if (activeBankChart?.metric_name === chartData.metric_name &&
      get().activeArtifactId === artifactId) {
    set({ chartHighlighted: true });
    setTimeout(() => set({ chartHighlighted: false }), 600);
    return;
  }

  set({
    activeBankChart: chartData,
    isSidebarOpen: true,
    chartHighlighted: true,  // Brief highlight on open
  });
  setTimeout(() => set({ chartHighlighted: false }), 600);
};
```

**File 2:** Canvas panel component

```tsx
// Use chartHighlighted for animation
const { chartHighlighted } = useCanvasStore();

<div className={cn(
  "canvas-panel",
  chartHighlighted && "animate-pulse ring-2 ring-primary"
)}>
```

### Acceptance Criteria

- [ ] Click "Abrir" SIEMPRE produce feedback visible en <200ms
- [ ] Si sidebar cerrado → se abre
- [ ] Si sidebar abierto + nuevo chart → highlight panel
- [ ] Si mismo chart → toast/pulse "Ya está abierto"

### Tests

```typescript
// Unit test
it('highlights canvas when opening same chart', () => {
  const store = useCanvasStore.getState();
  store.openBankChart(mockChart, 'art-1', 'msg-1');
  store.openBankChart(mockChart, 'art-1', 'msg-1'); // Same chart

  expect(store.chartHighlighted).toBe(true);
});
```

---

## Implementation Order

### P0 - Do Today

| Ticket | Scope | LOC |
|--------|-------|-----|
| BA-001 | `knowledge_handler.py` + alias map | ~30 |
| BA-003 | `BankChartCanvasView.tsx` (FE gating) | ~10 |

### P1 - Do Next

| Ticket | Scope | LOC |
|--------|-------|-----|
| BA-002 | `runtime_config.py`, `main.py` | ~6 |
| BA-004 | `canvas-store.ts`, panel component | ~20 |

**Total:** ~66 lines of code

---

## Smoke Test Script

```bash
#!/bin/bash
# smoke_issue_006.sh

set -e

echo "=== BA-002: INVEX Hardcode Check ==="
if rg -q "default.*['\"]INVEX['\"]" \
  --glob '!**/test*' --glob '!**/docs/**' --glob '!**/*.md' \
  plugins/bank-advisor-private/src/; then
  echo "❌ FAIL: INVEX hardcode found"
  exit 1
fi
echo "✅ PASS"

echo "=== BA-003: SQL Gating Check ==="
if ! rg -q "showDebugInfo|ENABLE_DEBUG_MODE" \
  apps/web/src/components/canvas/BankChartCanvasView.tsx; then
  echo "❌ FAIL: SQL display not gated"
  exit 1
fi
echo "✅ PASS"

echo "=== All checks passed ==="
```

---

## Open Questions (for PR Review)

1. **BA-001:** ¿`OntologyTerm` tiene campo `aliases`? Si no, necesitamos agregarlo o usar alias map externo.

2. **BA-001:** ¿Normalización de acentos ya existe? ("Índice" vs "Indice")

3. **BA-002:** ¿Quién consume `primary_bank=""` downstream? Verificar no genera `WHERE banco IN ('')`.

4. **BA-003:** ¿Dónde exactamente BE serializa `sql_query` en el payload? Para hardening server-side.

5. **BA-004:** ¿El sidebar puede estar fuera de viewport en responsive? ¿Necesitamos scroll-to?
