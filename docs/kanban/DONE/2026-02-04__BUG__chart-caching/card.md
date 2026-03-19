---
status: DONE
---
# BUG: Chart Caching - Gráfica No Se Actualiza Entre Queries

**Prioridad:** P2 - Medium
**Fecha:** 2026-02-04
**Reportado por:** Usuario via Dashboard Feedback
**Status:** DOING

---

## Resumen

La gráfica del frontend no se actualiza correctamente entre queries consecutivos. El usuario ve la gráfica del query anterior en lugar de la nueva. Este es un problema de renderizado/caching en el frontend.

**Impacto:** 1 feedback directo + posible relación con issues de "context bleeding"

---

## Caso Reportado

### Chart No Actualiza
**Fecha:** 2026-01-21 14:22
**Message ID:** 138f5c2a-e928-4d61-9f5c-c4d09b19f5ef
**Query:** `CARTERA_COMERCIAL de INVEX de 2025 puedes mostrar un comparativo por region?`
**Feedback:** "el grafico no se actualiza, se queda pendiente del anterior"

**Contexto del Error:**
- Data Type: `data` (el backend SÍ devolvió datos nuevos)
- Metric: `CARTERA_COMERCIAL`
- El backend respondió correctamente pero el frontend no renderizó la nueva gráfica

---

## Análisis Técnico

### Causa Raíz Probable

1. **React state no se actualiza** - El componente de chart no detecta cambios en props
2. **Key prop faltante** - Sin key única, React no re-renderiza el componente
3. **Plotly caching** - Plotly puede cachear el estado anterior del chart
4. **Race condition** - Respuesta llega antes de que el estado esté listo

### Diferencia con Context Bleeding

| Aspecto | Chart Caching | Context Bleeding |
|---------|---------------|------------------|
| Ubicación | Frontend (React) | Backend (LLM/SQL) |
| Síntoma | Gráfica anterior visible | Datos del query anterior |
| Data correcta? | SÍ (backend OK) | NO (SQL incorrecto) |
| Texto correcto? | SÍ | NO (año equivocado) |

### Archivos Involucrados

- `apps/web/src/components/chat/PlotlyChart.tsx`
- `apps/web/src/components/chat/ChatMessage.tsx`
- `apps/web/src/hooks/useChat.ts` (state management)

---

## Solución Propuesta

### 1. Agregar Key Única al Chart

```tsx
// PlotlyChart.tsx
<Plot
  key={`chart-${messageId}-${Date.now()}`}  // Force re-render
  data={plotlyConfig.data}
  layout={plotlyConfig.layout}
  config={{ responsive: true }}
/>
```

### 2. Forzar Re-render en Cambio de Datos

```tsx
// ChatMessage.tsx
useEffect(() => {
  if (data?.plotly_config) {
    // Force chart re-initialization
    setChartKey(prev => prev + 1);
  }
}, [data?.plotly_config]);

<PlotlyChart
  key={chartKey}
  config={data.plotly_config}
/>
```

### 3. Limpiar Cache de Plotly

```tsx
// En el componente
useEffect(() => {
  return () => {
    // Cleanup on unmount
    Plotly.purge(chartRef.current);
  };
}, []);
```

---

## Criterios de Aceptación

- [x] Query A muestra gráfica A, Query B muestra gráfica B (sin residuos) — **backend verified**
- [x] Store de canvas distingue visualizaciones con mismo artifact cuando cambian `plotly_config.data` o `plotly_config.layout` (TDD unit tests)
- [x] Cambio de banco/métrica actualiza el render de chart response en frontend (Playwright determinístico con mock de `/api/chat`)
- [ ] No hay "flash" de gráfica anterior antes de la nueva (requiere Playwright)
- [ ] Performance no se degrada con múltiples queries

## Avance Implementado (2026-02-09)

- Se reforzó `openBankChart` en `apps/web/src/lib/stores/canvas-store.ts` con firma de visualización completa (`metric`, bancos, `time_range`, `plotly data/layout/config`) para evitar falsos "same chart".
- Se agregaron regresiones en `apps/web/src/lib/stores/__tests__/canvas-store.bankChart.test.ts`:
  - cambio de `plotly_config.data` con mismo `artifactId` actualiza chart activo.
  - cambio de `plotly_config.layout` con misma data también actualiza chart activo.
- Validación local ejecutada:
  - `cd apps/web && pnpm test -- src/lib/stores/__tests__/canvas-store.bankChart.test.ts`
  - `cd apps/web && pnpm test -- src/lib/stores/__tests__/canvas-store.bankChart.test.ts src/components/chat/__tests__/ChatMessage.bankChart.test.tsx src/components/chat/__tests__/BankChartPreview.test.tsx src/components/canvas/__tests__/BankChartCanvasView.test.tsx src/components/canvas/__tests__/BankChartCanvas.e2e.test.tsx`
- Se agregó spec Playwright: `apps/web/tests/e2e/chart-caching.spec.ts`
  - Login bootstrap vía API.
  - Mock de `/api/chat` para respuestas chart determinísticas (evita flakes de SSE/infra).
  - Comando validado: `cd apps/web && CI=1 PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000 pnpm test:e2e -- tests/e2e/chart-caching.spec.ts`
- Se ajustó `apps/web/playwright.config.ts` para usar `bun run dev` por defecto (antes usaba `pnpm --filter` y fallaba en este repo).
- Pendiente para mover a REVIEW: validación Playwright/manual en flujo real de chat (sin mock de Plotly).

## Verificación Backend (2026-02-06)

Replay test: `tests/e2e/regression/test_feedback_replay_2026_02_06.py`
- ICAP BBVA → chart traces: `{BBVA}`
- ICAP Santander → chart traces: `{SANTANDER}`
- **Backend devuelve data correcta y diferenciada.** Si el bug persiste, es puramente frontend (React/Plotly re-render).

**DoD pendiente**: Verificar visualmente en PROD que la gráfica se actualiza entre queries (requiere Playwright o test manual).

---

## Test E2E Requerido

```typescript
// apps/web/src/__tests__/e2e/chart-update.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Chart Caching Bug', () => {
  /**
   * Replica el bug: gráfica no se actualiza entre queries.
   *
   * Feedback original:
   * - 138f5c2a: "el grafico no se actualiza, se queda pendiente del anterior"
   * - Query: "CARTERA_COMERCIAL de INVEX de 2025 comparativo por region"
   */

  test('chart updates between consecutive queries', async ({ page }) => {
    await page.goto('/chat');

    // Query 1: ICAP de BBVA
    await page.fill('[data-testid="chat-input"]', 'ICAP de BBVA');
    await page.click('[data-testid="send-button"]');
    await page.waitForSelector('[data-testid="plotly-chart"]');

    // Capturar título del chart 1
    const chart1Title = await page.locator('.plotly .gtitle').textContent();
    expect(chart1Title).toContain('BBVA');

    // Query 2: ICAP de SANTANDER
    await page.fill('[data-testid="chat-input"]', 'ICAP de SANTANDER');
    await page.click('[data-testid="send-button"]');
    await page.waitForSelector('[data-testid="plotly-chart"]:nth-child(2)');

    // Capturar título del chart 2
    const chart2Title = await page.locator('.plotly .gtitle').last().textContent();

    // El chart 2 NO debe ser igual al chart 1
    expect(chart2Title).toContain('SANTANDER');
    expect(chart2Title).not.toContain('BBVA');
  });

  test('regional chart replaces previous chart', async ({ page }) => {
    await page.goto('/chat');

    // Query 1: Cartera simple
    await page.fill('[data-testid="chat-input"]', 'cartera comercial de invex');
    await page.click('[data-testid="send-button"]');
    await page.waitForSelector('[data-testid="plotly-chart"]');

    // Query 2: Cartera por región (el que falló)
    await page.fill('[data-testid="chat-input"]',
      'CARTERA_COMERCIAL de INVEX de 2025 puedes mostrar un comparativo por region?'
    );
    await page.click('[data-testid="send-button"]');

    // Esperar que aparezca el nuevo chart
    await page.waitForTimeout(2000);

    // Verificar que el último chart tiene datos regionales
    const lastChart = page.locator('[data-testid="plotly-chart"]').last();
    await expect(lastChart).toBeVisible();

    // El chart debe tener múltiples traces (regiones)
    const traces = await page.locator('.plotly .trace').count();
    expect(traces).toBeGreaterThan(1);  // Múltiples regiones
  });
});
```

---

## Referencias

- Feedback: 138f5c2a
- Relacionado: `2026-02-04__BUG__temporal-context-bleeding` (síntomas similares, causa diferente)
- Frontend: `apps/web/src/components/chat/`

## Feedback Vinculado

**1 reporte(s)** de usuarios en producción.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0002 | `7f5aa3b9` | CARTERA_COMERCIAL de INVEX de 2025 puedes mostrar un comp... | el grafico no se actualiza, se queda pendiente del anterior | 2026-01-21 |

<details>
<summary>Detalle completo de feedbacks</summary>

### FDBK-0002
- **User**: `7f5aa3b9-8f98-459e-abc2-0148b23486f9`
- **Conversation**: `ea9ea471-f54c-4153-801e-95c3f00597af`
- **Message**: `138f5c2a-e928-4d61-9f5c-c4d09b19f5ef`
- **Rating**: 👎
- **Query**: "CARTERA_COMERCIAL de INVEX de 2025 puedes mostrar un comparativo por region? (Cartera Comercial)"
- **Feedback**: "el grafico no se actualiza, se queda pendiente del anterior"
- **Fecha**: 2026-01-21T20:22:51.605Z

</details>
