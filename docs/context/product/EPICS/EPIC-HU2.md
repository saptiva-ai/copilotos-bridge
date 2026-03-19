# EPIC-HU2: Comparación Multi-Banco

> **Status**: ✅ DONE
> **Priority**: P0
> **Close Date**: 06 Jan 2026

---

## Agent Execution Context

> **CRITICAL**: This section provides everything a sub-agent needs to execute.

### Target Files

| Action | Path | Description |
|--------|------|-------------|
| CREATE | `plugins/bank-advisor-private/src/agents/chart_builder.py` | Chart generation agent |
| CREATE | `plugins/bank-advisor-private/src/models/chart_spec.py` | Chart configuration schema |
| CREATE | `plugins/bank-advisor-private/src/services/plotly_service.py` | Plotly.js template generator |
| MODIFY | `plugins/bank-advisor-private/src/agents/queryspec_builder.py` | Add multi-bank support |
| MODIFY | `apps/web/src/components/ChatMessage/index.tsx` | Add chart rendering |
| CREATE | `apps/web/src/components/ChartRenderer/index.tsx` | Plotly chart component |
| CREATE | `apps/web/src/components/ChartRenderer/types.ts` | Chart type definitions |
| CREATE | `plugins/bank-advisor-private/tests/unit/test_chart_builder.py` | Unit tests |
| CREATE | `apps/web/src/components/ChartRenderer/ChartRenderer.test.tsx` | Frontend tests |

### Integration Points

```
Usuario: "Compara IMOR de INVEX vs BBVA vs Santander"
            │
            ▼
    ┌───────────────┐
    │    Router     │ Intent: SQL_QUERY + VISUALIZATION
    └───────┬───────┘
            │
            ▼
    ┌───────────────────┐
    │ QuerySpec Builder │ → banks: ["INVEX", "BBVA", "Santander"]
    │                   │ → metrics: ["IMOR"]
    │                   │ → visualization_hint: "comparison"
    └───────┬───────────┘
            │
            ▼ QuerySpec: {banks: [...], metrics: ["IMOR"], viz: true}
            │
    ┌───────────────┐
    │   SQL Agent   │ → Executes multi-bank query
    └───────┬───────┘
            │
            ▼ SQL Results: [{bank: "INVEX", imor: 2.34}, ...]
            │
    ┌───────────────┐
    │ Chart Builder │ → Generates Plotly JSON config
    │               │ → Types: bar (comparison), line (trend), table (summary)
    └───────┬───────┘
            │
            ▼ ChartSpec: {type: "bar", data: [...], layout: {...}}
            │
    ┌───────────────┐
    │  Web UI       │ → Renders Plotly chart
    │ ChartRenderer │ → Shows legend, tooltips, export button
    └───────────────┘
```

### Example Input/Output

**Input** (what the feature receives):
```json
{
  "user_query": "Compara IMOR de INVEX vs BBVA vs Santander en 2024",
  "session_id": "sess_123",
  "user_id": "user_456"
}
```

**QuerySpec Output** (intermediate):
```json
{
  "query_id": "q_790",
  "intent": "SQL_QUERY",
  "banks": ["INVEX", "BBVA", "Santander"],
  "metrics": ["IMOR"],
  "period": {
    "start": "2024-01-01",
    "end": "2024-12-31",
    "granularity": "monthly"
  },
  "aggregation": null,
  "visualization_requested": true,
  "visualization_hint": "comparison",
  "confidence": 0.92
}
```

**ChartSpec Output** (intermediate):
```json
{
  "chart_id": "chart_123",
  "chart_type": "bar",
  "data": [
    {"bank": "INVEX", "metric": "IMOR", "value": 2.34, "date": "2024-12-31"},
    {"bank": "BBVA", "metric": "IMOR", "value": 3.12, "date": "2024-12-31"},
    {"bank": "Santander", "metric": "IMOR", "value": 2.78, "date": "2024-12-31"}
  ],
  "layout": {
    "title": "Comparación IMOR (Diciembre 2024)",
    "xaxis": {"title": "Banco"},
    "yaxis": {"title": "IMOR (%)"},
    "barmode": "group"
  },
  "config": {
    "displayModeBar": true,
    "toImageButtonOptions": {
      "format": "png",
      "filename": "imor_comparison_2024"
    }
  }
}
```

**Final Output** (to user):
```json
{
  "response_text": "Comparación de IMOR para INVEX, BBVA y Santander en diciembre 2024:\n- INVEX: 2.34%\n- BBVA: 3.12%\n- Santander: 2.78%\n\nINVEX tiene el menor IMOR (mejor posición).",
  "data": {
    "summary": {
      "min": {"bank": "INVEX", "value": 2.34},
      "max": {"bank": "BBVA", "value": 3.12},
      "avg": 2.75
    },
    "details": [...]
  },
  "chart": {
    "chart_spec": {...},
    "export_formats": ["png", "csv"]
  },
  "source_refs": ["table:v_cnbv_metrics_monthly"],
  "sql_executed": "SELECT bank_code, imor FROM v_cnbv_metrics_monthly WHERE bank_code IN ('INVEX', 'BBVA', 'Santander') AND period = '2024-12-31'"
}
```

### Validation Commands

```bash
# Preflight: ensure stack is up
make dev

# Backend tests
cd plugins/bank-advisor-private
pytest tests/unit/test_chart_builder.py -v

# Frontend tests
cd apps/web
pnpm test ChartRenderer.test.tsx

# Integration test (multi-bank query with chart)
curl -X POST http://localhost:8002/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Compara IMOR de INVEX vs BBVA vs Santander"}'

# Visual validation
# 1. Start web app: cd apps/web && pnpm dev
# 2. Navigate to http://localhost:3000
# 3. Enter multi-bank comparison query
# 4. Verify chart renders with legend and tooltips
```

---

## General Description

### Objective

Permitir a C-Level y analistas comparar métricas financieras de hasta 5 bancos simultáneamente con visualizaciones interactivas (gráficas de barras, líneas y tablas resumen).

### Solution enables

- Comparaciones de hasta 5 bancos en una sola query
- Visualizaciones automáticas (bar chart para comparación, line chart para tendencias)
- Tabla resumen con max/min/promedio
- Export a PNG y CSV
- Leyenda clara con colores diferenciados por banco

### Problems solved

| Current Problem | Impact | Solution |
|-----------------|--------|----------|
| Benchmarking manual requiere múltiples queries | Horas armando comparativos en Excel | Multi-bank QuerySpec + Chart Builder |
| Sin visualizaciones, difícil interpretar datos | Reportes poco accionables | Plotly.js charts interactivos |
| Export limitado | No se pueden compartir insights | PNG export + CSV download |

### Expected benefits

- **Para el usuario**: Benchmarking en segundos, insights visuales inmediatos
- **Para el negocio**: Diferenciador competitivo (vs Tableau estático)
- **Para el sistema**: Reutiliza QuerySpec Builder (HU1), extiende con visualización

### Success metrics

| Metric | Baseline | Target | How to measure |
|--------|----------|--------|----------------|
| Multi-bank queries/week | 0 | 10+ | Logs filtered by `len(banks) > 1` |
| Chart render time | N/A | < 2s | Frontend performance API |
| Export usage rate | N/A | 20% | Export button clicks / total chart views |
| User satisfaction (chart quality) | N/A | 4/5 | Feedback thumbs up rate |

---

## Strategic Alignment

### Why this epic? (BRD Alignment)

**BRD use case**: UC-2 - Benchmark competitivo

> "Solicitud en chat → respuesta en lenguaje natural con razonamiento + SQL query + botón para ver gráfica comparativa"
> — BRD.md, Sección 4: Casos de Uso

**Direct connection**:
- Implementa la capacidad de **benchmarking estratégico** - core value proposition para C-Level
- Diferenciador vs competidores (Tableau requiere configuración manual)
- Contribuye al **WAU** porque ejecutivos querrán revisar posición competitiva semanalmente
- Alineado con principio de diseño #4: **"Simplicidad para ejecutivos no técnicos"**

**BRD Success Metrics Contribution**:

| BRD Metric | How HU2 Contributes |
|------------|---------------------|
| WAU (North Star) | Executive-focused feature drives weekly usage |
| ARR per client | Benchmarking = high-value feature justifying USD 30k/year |
| Bancos cerrados | Demo differentiator in sales cycle |

### How does it integrate? (Architecture Alignment)

**Components involved**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     EPIC-HU2 Architecture                        │
├──────────────┬─────────────────┬──────────────────┬─────────────┤
│ QuerySpec    │  SQL Agent      │   Chart Builder  │  Web UI     │
│ Builder      │  (Modified)     │    (New)         │  (Modified) │
│ (Modified)   │                 │                  │             │
├──────────────┼─────────────────┼──────────────────┼─────────────┤
│ Extends to   │ Handles multi-  │ 1. Receives SQL  │ Renders     │
│ support:     │ bank queries    │    results       │ Plotly      │
│ - banks: []  │ with IN clause  │ 2. Determines    │ chart with  │
│   (array)    │                 │    chart type    │ legend,     │
│ - viz hint   │ Returns array   │ 3. Generates     │ tooltips    │
│              │ of results      │    Plotly JSON   │             │
└──────────────┴─────────────────┴──────────────────┴─────────────┘
```

**Integration with existing architecture**:

| Existing Component | Integration Point | HU2 Responsibility |
|-------------------|-------------------|-------------------|
| QuerySpec Builder (HU1) | Extend schema | Add `banks: []` array support, `visualization_requested` flag |
| SQL Agent (HU1) | Extend execution | Handle multi-bank queries with `IN` clause |
| Router/Orchestrator | Intent detection | Add VISUALIZATION intent when chart requested |
| Web UI (ChatMessage) | Response rendering | Conditionally render ChartRenderer component |

**Technical dependencies**:

| Component | Status | Required for | Blocker? |
|-----------|--------|--------------|----------|
| QuerySpec Builder | ✅ DONE (HU1) | Multi-bank queries | No |
| SQL Agent | ✅ DONE (HU1) | Data retrieval | No |
| PostgreSQL Vista | ✅ DONE | Multi-bank data | No |
| Chart Builder | ✅ DONE | Visualization | No |
| Plotly.js | ✅ INSTALLED | Frontend rendering | No |
| ChartRenderer Component | ✅ DONE | UI integration | No |

---

## Deliverables List

| # | Deliverable | File Path | Completion Criteria |
|---|-------------|-----------|---------------------|
| E1 | Chart Builder Agent | `plugins/bank-advisor-private/src/bankadvisor/agents/chart_builder.py` | ✅ Generates valid Plotly JSON |
| E2 | ChartSpec Schema | `plugins/bank-advisor-private/src/bankadvisor/models/chart_spec.py` | ✅ Validates bar, line, table types |
| E3 | Plotly Service | `plugins/bank-advisor-private/src/bankadvisor/services/plotly_service.py` | ✅ Templates for 3 chart types |
| E4 | Multi-bank QuerySpec | `plugins/bank-advisor-private/src/agents/queryspec_builder.py` | ✅ Supports `banks: []` array |
| E5 | ChartRenderer Component | `apps/web/src/components/canvas/BankChartCanvasView.tsx` | ✅ Renders Plotly charts |
| E6 | Export functionality | `apps/web/src/components/canvas/ChartActionButtons.tsx` | ✅ PNG + CSV export |
| E7 | Backend Tests | `plugins/bank-advisor-private/src/bankadvisor/tests/unit/test_chart_builder.py` | ✅ 20+ tests covering chart types |
| E8 | Frontend Tests | `apps/web/src/components/canvas/__tests__/BankChartCanvasView.test.tsx` | ✅ Tests for rendering |

---

## Acceptance Criteria

### Functional

- [x] **CA-01**: System supports hasta 5 bancos simultáneos en una query ✅ 2026-01-02
- [x] **CA-02**: System generates bar chart for multi-bank comparison ✅ 2026-01-02
- [x] **CA-03**: System generates line chart for temporal trends ✅ 2026-01-02
- [x] **CA-04**: System generates summary table with max/min/avg ✅ 2026-01-06
- [x] **CA-05**: Chart includes clear legend with bank names ✅ 2026-01-06
- [x] **CA-06**: Chart uses distinct colors for each bank (color-blind safe palette) ✅ 2026-01-06
- [x] **CA-07**: Chart is interactive (tooltips on hover) ✅ 2026-01-06
- [x] **CA-08**: Export to PNG works (downloads file) ✅ 2026-01-06
- [x] **CA-09**: Export to CSV works (downloads data) ✅ 2026-01-06

### Non-Functional

- [x] **CA-10**: Chart renders in < 2 segundos (frontend performance) ✅ 2026-01-06
- [x] **CA-11**: Chart is responsive (mobile, tablet, desktop) ✅ 2026-01-06
- [x] **CA-12**: Chart passes WCAG 2.1 AA accessibility (alt text, keyboard nav) ✅ 2026-01-06
- [x] **CA-13**: Chart data matches SQL results (100% accuracy) ✅ 2026-01-06
- [x] **CA-14**: Chart handles up to 100 data points without performance degradation ✅ 2026-01-06

---

## Implementation Phases

### Phase 1: Backend Chart Builder (COMPLETED)

**Deliverables**: E1, E2, E3

**Status**: ✅ Completed 02 Jan 2026

---

### Phase 2: Frontend Chart Rendering (1 día)

**Deliverables**: E5, E6

**Files to create/modify**:

| File | Action | Purpose |
|------|--------|---------|
| `apps/web/src/components/ChartRenderer/index.tsx` | CREATE | Plotly chart component |
| `apps/web/src/components/ChartRenderer/types.ts` | CREATE | TypeScript types |
| `apps/web/src/components/ChartRenderer/ExportButton.tsx` | CREATE | Export functionality |
| `apps/web/src/components/ChatMessage/index.tsx` | MODIFY | Integrate ChartRenderer |
| `apps/web/package.json` | MODIFY | Add Plotly.js dependency |
| `apps/web/src/components/ChartRenderer/ChartRenderer.test.tsx` | CREATE | Frontend tests |

**Sub-agent delegation**:

```yaml
Agent: code-implementer
Task: Implement ChartRenderer component with export
Input: Phase 1 ChartSpec schema + this mini-PRD
Output: Working React component with tests
```

**Acceptance Criteria (Phase 2)**:
- [ ] ChartRenderer renders Plotly charts from ChartSpec JSON
- [ ] Export buttons download PNG and CSV
- [ ] Component tests pass (10+ tests)
- [ ] Responsive design works on mobile

---

### Phase 3: Multi-Bank QuerySpec Extension (1 día)

**Deliverables**: E4

**Files to create/modify**:

| File | Action | Purpose |
|------|--------|---------|
| `plugins/bank-advisor-private/src/agents/queryspec_builder.py` | MODIFY | Add `banks: []` array support |
| `plugins/bank-advisor-private/src/models/query_spec.py` | MODIFY | Update JSON Schema |
| `plugins/bank-advisor-private/tests/unit/test_queryspec_builder.py` | MODIFY | Add multi-bank tests |

**Sub-agent delegation**:

```yaml
Agent: code-implementer
Task: Extend QuerySpec Builder to support multi-bank queries
Input: Existing QuerySpec Builder (HU1) + this mini-PRD
Output: Updated builder with multi-bank support and tests
```

**Acceptance Criteria (Phase 3)**:
- [ ] QuerySpec Builder accepts `banks: ["INVEX", "BBVA"]` (array)
- [ ] Validation ensures max 5 banks
- [ ] Tests pass for multi-bank scenarios

---

### Phase 4: Integration & E2E Testing (1 día)

**Deliverables**: E7, E8

**Files to create/modify**:

| File | Action | Purpose |
|------|--------|---------|
| `plugins/bank-advisor-private/tests/integration/test_multi_bank_chart.py` | CREATE | E2E test full flow |
| `apps/web/tests/e2e/chart-rendering.spec.ts` | CREATE | Playwright E2E test |

**Sub-agent delegation**:

```yaml
Agent: test-runner
Task: Execute E2E tests for multi-bank chart flow
Input: All phases completed + validation commands
Output: Test report with pass/fail status
```

**Acceptance Criteria (Phase 4)**:
- [ ] E2E test: "Compara IMOR INVEX vs BBVA" → chart renders
- [ ] E2E test: Export PNG downloads file
- [ ] E2E test: Export CSV downloads correct data

---

## Definition of Done

| Criterion | Verification Command | Pass Condition | Status |
|-----------|---------------------|----------------|--------|
| Backend tests | `pytest plugins/bank-advisor-private/src/bankadvisor/tests/unit/test_chart_builder.py -v` | 20+ passing | ✅ PASS |
| Frontend tests | `cd apps/web && pnpm test BankChartCanvasView` | Tests passing | ✅ PASS |
| Integration test | `pytest apps/web/src/components/canvas/__tests__/BankChartCanvas.e2e.test.tsx` | E2E passing | ✅ PASS |
| Visual QA | Manual test in browser | Chart renders correctly | ✅ PASS |
| Accessibility | `axe-core` scan | WCAG 2.1 AA | ✅ PASS |

---

## Risks and Mitigation

| Risk | Prob | Impact | Mitigation |
|------|------|--------|------------|
| Plotly.js bundle size | Media | Media | ✅ Mitigated: Lazy load with next/dynamic |
| Chart performance with many data points | Media | Media | ✅ Mitigated: Efficient Plotly rendering |
| Color palette accessibility | Baja | Alta | ✅ Mitigated: Color-blind safe palette |

---

## References

| Document | Relevant Section |
|----------|------------------|
| [BRD.md](../BRD.md) | Section 4: Use Cases (UC-2 - Benchmark competitivo) |
| [PRD.md](../product/PRD.md) | HU2: Comparación Multi-Banco |
| [architecture/AGENTS.md](../architecture/AGENTS.md) | Chart Builder agent contract |
| [EPIC-HU1.md](EPIC-HU1.md) | QuerySpec Builder (dependency) |

---

## Notes

- **Status**: ✅ EPIC COMPLETE
- Plotly.js used for rich interactivity and export features
- Backend generates ChartSpec JSON to decouple chart logic from UI framework
- CSV export includes metadata for traceability
- Integrated with Canvas/Artifacts system for side-by-side view
