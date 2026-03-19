---
status: REVIEW
---
# BUG: UI - Cambio de Fuente y Layout Roto en Conversación

**Prioridad:** P3 - Low
**Fecha:** 2026-02-04
**Reportado por:** Usuario via Dashboard Feedback
**Status:** BACKLOG

---

## Resumen

El tipo de letra cambia repentinamente durante la conversación y el contenido no respeta el área de la conversación, dificultando la lectura.

**Impacto:** 1 feedback - problema de UX

---

## Caso Reportado

### Font/Layout Break
**Fecha:** 2026-02-03 13:47
**Message ID:** 7abc4031-78a2-41b4-9646-72f44a340412
**Query:** `explícame a detalle que es la cartera comercial de un banco, como se obtiene y dame un ejemplo que cualquier persona pudiera entender`
**Feedback:** "cambio el tipo de letra repentinamente y no respeto el área de la conversación lo que hace que sea difícil la lectura"

---

## Análisis Técnico

### Causa Raíz Probable

1. **Markdown rendering inconsistente** - Diferentes parsers para diferentes tipos de respuesta
2. **CSS overflow** - Contenido largo sin word-wrap correcto
3. **Code blocks** - Bloques de código pueden romper el layout
4. **Font fallback** - Caracteres especiales causan fallback a otra fuente

### Archivos Involucrados

- `apps/web/src/components/chat/ChatMessage.tsx`
- `apps/web/src/components/chat/MarkdownRenderer.tsx`
- `apps/web/src/styles/chat.css` o `globals.css`

---

## Solución Propuesta

### 1. Normalizar Font Family

```css
/* globals.css */
.chat-message {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.chat-message code,
.chat-message pre {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
```

### 2. Forzar Word Wrap

```css
.chat-message {
  word-wrap: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
}

.chat-message pre {
  white-space: pre-wrap;
  overflow-x: auto;
}
```

### 3. Contenedor con Límites

```tsx
// ChatMessage.tsx
<div className="chat-message max-w-full overflow-hidden">
  <MarkdownRenderer content={message.content} />
</div>
```

---

## Criterios de Aceptación

- [ ] Fuente consistente en toda la conversación
- [x] Contenido largo no rompe el layout
- [ ] Code blocks tienen scroll horizontal si necesario
- [ ] Responsive en móvil y desktop
- [x] Tablas anchas (19+ columnas) muestran scroll horizontal en lugar de comprimir columnas

---

## Test E2E Requerido

```typescript
// apps/web/src/__tests__/e2e/ui-layout.spec.ts

import { test, expect } from '@playwright/test';

test.describe('UI Font and Layout', () => {
  /**
   * Replica el bug: fuente cambia y layout se rompe.
   *
   * Feedback original:
   * - 7abc4031: "cambio el tipo de letra repentinamente y no respeto
   *   el área de la conversación"
   */

  test('long response maintains consistent font', async ({ page }) => {
    await page.goto('/chat');

    // Query que genera respuesta larga
    await page.fill('[data-testid="chat-input"]',
      'explícame a detalle que es la cartera comercial de un banco'
    );
    await page.click('[data-testid="send-button"]');
    await page.waitForSelector('[data-testid="assistant-message"]');

    // Verificar que la fuente es consistente
    const message = page.locator('[data-testid="assistant-message"]');
    const fontFamily = await message.evaluate(
      el => window.getComputedStyle(el).fontFamily
    );

    // Debe contener la fuente principal (Inter o system font)
    expect(fontFamily.toLowerCase()).toMatch(/inter|system-ui|sans-serif/);
  });

  test('message stays within container bounds', async ({ page }) => {
    await page.goto('/chat');

    await page.fill('[data-testid="chat-input"]', 'ICAP de todos los bancos');
    await page.click('[data-testid="send-button"]');
    await page.waitForSelector('[data-testid="assistant-message"]');

    const message = page.locator('[data-testid="assistant-message"]');
    const container = page.locator('[data-testid="chat-container"]');

    const messageBox = await message.boundingBox();
    const containerBox = await container.boundingBox();

    // El mensaje no debe exceder el contenedor
    expect(messageBox!.width).toBeLessThanOrEqual(containerBox!.width);
  });
});
```

---

## Progreso (2026-02-09)

### Fix: Tablas anchas con scroll horizontal

**Root cause**: `MarkdownMessage.tsx` tenia `w-full` en el `<table>`, lo que forzaba
la tabla al 100% del ancho del contenedor. Con 19+ columnas (cartera hipotecaria por banco),
cada columna quedaba de ~30px, y los headers se renderizaban verticalmente (un caracter por linea).

**Cambios**:
- `table`: `w-full` → `min-w-full` (permite expansion + scroll horizontal)
- `table wrapper`: Agregado `max-w-full` para anclar al contenedor
- `th`: Agregado `whitespace-nowrap` (previene headers verticales)
- `td`: Agregado `whitespace-nowrap` (mantiene datos numericos legibles)

**Archivos**:
- `apps/web/src/components/chat/MarkdownMessage.tsx` (fix)
- `apps/web/src/components/chat/__tests__/MarkdownMessage.table.test.tsx` (5 tests nuevos)

**Tests**: 5/5 pass, 18/18 StreamingMessage sin regresion.

## Referencias

- Feedback: 7abc4031
- Frontend: `apps/web/src/components/chat/`
- Styles: `apps/web/src/styles/`

## Feedback Vinculado

**1 reporte(s)** de usuarios en producción.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0032 | `cb6c6879` | explícame a detalle que es la cartera comercial de un ban... | cambio el tipo de letra repentinamente y no respeto el área de la conversació... | 2026-02-03 |

<details>
<summary>Detalle completo de feedbacks</summary>

### FDBK-0032
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `6bf39d89-1f72-4814-9a1b-aaf0aa99b278`
- **Message**: `7abc4031-78a2-41b4-9646-72f44a340412`
- **Rating**: 👎
- **Query**: "explícame a detalle que es la cartera comercial de un banco, como se obtiene y dame un ejemplo que cualquier persona pudiera entender"
- **Feedback**: "cambio el tipo de letra repentinamente y no respeto el área de la conversación lo que hace que sea difícil la lectura "
- **Fecha**: 2026-02-03T19:47:03.208Z

</details>
