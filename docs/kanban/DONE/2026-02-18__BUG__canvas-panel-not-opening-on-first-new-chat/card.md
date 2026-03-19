---
id: "BUG-2026-02-18__canvas-panel-not-opening-on-first-new-chat"
title: "Canvas no abre en primer chat nuevo cuando la ruta permanece en /chat"
status: "DONE"
phase: "Research"
scope_in:
  - "Diagnosticar por qué el botón 'Abrir gráfica en canvas' no abre panel en la primera conversación nueva sin chatId en URL"
  - "Confirmar interacción entre estado de canvas (Zustand), efectos de ChatView y reconciliación de chat_id"
  - "Definir corrección para evitar cierre inmediato del panel en /chat (sin chatId resuelto)"
  - "Agregar validación de regresión (unit/integration o e2e) para garantizar apertura en primer click"
scope_out:
  - "Cambios en backend MCP, Redis o generación de plotly_config"
  - "Rediseño visual del panel canvas"
  - "Optimización de performance fuera del flujo de apertura/cierre"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 0
validation_commands:
  - "cd apps/web && pnpm test -- src/components/chat/__tests__/ChatMessage.bankChart.test.tsx src/components/chat/__tests__/BankChartPreview.test.tsx src/lib/stores/__tests__/canvas-store.bankChart.test.ts"
  - "cd apps/web && pnpm test -- src/components/canvas/__tests__/BankChartCanvas.e2e.test.tsx"
  - "cd apps/web && pnpm exec playwright test e2e/tests/chat.spec.ts -g \"help onboarding opens chart and waits for complete render\" --project=chromium"
pr_files: []
test_status: "failing"
---

# Summary
- Objective: corregir el bug donde el canvas no se abre en la primera conversación nueva hasta navegar a otra conversación y regresar.
- Constraint: mantener el comportamiento de aislamiento por conversación (cerrar canvas al cambiar de chat), sin romper auto-open ni apertura manual.

# Problema
Reporte de usuario:

1. Se abre la app recién desplegada.
2. Se inicia conversación nueva (sin contexto/cache previo).
3. Llega respuesta con `bank_chart_data` y aparece botón para abrir canvas.
4. Al hacer click, el panel no se mantiene abierto.
5. Tras ir a otra conversación y volver, el mismo botón sí abre canvas.

Comportamiento observado en código:
- El botón sí ejecuta `openBankChart(...)` en store (`BankAdvisorResponse`).
- `ChatView` puede forzar cierre/reset del canvas cuando `resolvedChatId` es `null`.

# Evidencia clave
- `ChatView` deriva `resolvedChatId` solo de ruta/query, no de `currentChatId`: `apps/web/src/app/chat/_components/ChatView.tsx:62`.
- El botón sí abre canvas vía store: `apps/web/src/components/chat/BankAdvisorResponse.tsx:75`.
- `ChatView` cierra/reset canvas si no hay `resolvedChatId`: `apps/web/src/app/chat/_components/ChatView.tsx:202`.
- Ese efecto depende de `isCanvasOpen`, por lo que se re-dispara justo al abrir: `apps/web/src/app/chat/_components/ChatView.tsx:215`.
- En el flujo de primer mensaje, se actualiza `currentChatId` pero no se navega necesariamente a `/chat/{id}`: `apps/web/src/app/chat/_components/ChatView.tsx:1061`.
- Existe workaround en E2E para “first-click misses”: `apps/web/e2e/pages/ChatPage.ts:153`.

# Hipótesis de causa raíz
Condición de carrera de estado/ruta en frontend:
- En `/chat` (sin `chatId`), `resolvedChatId` queda `null`.
- Al abrir canvas (manual o auto-open), `isCanvasOpen` cambia a `true`.
- El `useEffect` de `ChatView` se vuelve a ejecutar (porque depende de `isCanvasOpen`) y entra al branch `resolvedChatId === null`, que cierra/resetea canvas inmediatamente.
- Resultado: el usuario percibe que “no abre” hasta que la conversación ya tiene ruta estable y se vuelve a seleccionar.

# Criterios de aceptación
- [ ] En `/chat` sin `chatId`, el primer click en “Abrir gráfica … en canvas” abre y mantiene visible el panel.
- [ ] El auto-open de `bank_chart` por stream no se cierra inmediatamente en primera conversación.
- [ ] Al cambiar a otra conversación real, el canvas sí se cierra (ownership por conversación se conserva).
- [ ] E2E/Integration no requieren doble click ni workaround para abrir canvas.

# Updates
- 2026-02-18 07:23 - Ticket creado con investigación inicial, evidencia de código y pruebas ejecutadas.
- 2026-02-18 07:33 - Implementado fix en `ChatView` usando `effectiveChatId` (route-first + fallback a store), removiendo reset reactivo por `isCanvasOpen` y alineando key de `CanvasPanel` con conversación efectiva.
- 2026-02-18 07:41 - Añadida suite `chat-view-canvas-utils.test.ts` para cubrir transiciones `null -> real`, `real -> real`, `temp -> real` y `real -> null`; unit/integration + lint + typecheck en verde.
- 2026-02-18 07:46 - Agregado test E2E de regresión `apps/web/e2e/tests/canvas-first-open.spec.ts` para validar apertura con single-click en `/chat` conversación nueva.
- 2026-02-18 07:51 - Ejecutado E2E del nuevo escenario (`CI=1`, Chromium): setup + test de regresión pasaron (2/2).
