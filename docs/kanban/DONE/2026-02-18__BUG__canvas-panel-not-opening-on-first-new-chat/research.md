# Research — Canvas no abre en primer chat nuevo

## Status: Complete

## Resultado ejecutivo

Se identificó un cierre inmediato del canvas provocado por un efecto de `ChatView` cuando la ruta aún es `/chat` (sin `chatId` resuelto). El botón de apertura sí ejecuta `openBankChart`, pero el estado se revierte justo después por lógica de reset.

## Hallazgos técnicos

### 1) El botón de apertura sí funciona
- `BankAdvisorResponse` invoca `useCanvasStore.getState().openBankChart(...)`.
- Referencia: `apps/web/src/components/chat/BankAdvisorResponse.tsx:75`.
- Conclusión: no es problema de click handler ni de wiring del botón.

### 2) `resolvedChatId` depende de URL, no de estado interno actual
- `resolvedChatId` sale de `initialChatId` o query param `session`; si no existen, queda `null`.
- Referencia: `apps/web/src/app/chat/_components/ChatView.tsx:62`.
- Conclusión: en `/chat` sin `chatId` la vista puede operar con conversación activa en store, pero `resolvedChatId` seguir siendo `null`.

### 3) El efecto de `ChatView` resetea canvas cuando `resolvedChatId === null`
- Branch explícito: if no hay chat seleccionado, llama `closeCanvas()` y `resetCanvas()`.
- Referencia: `apps/web/src/app/chat/_components/ChatView.tsx:202`.
- Este efecto incluye `isCanvasOpen` en dependencias.
- Referencia: `apps/web/src/app/chat/_components/ChatView.tsx:215`.
- Conclusión: al abrir canvas (`isCanvasOpen = true`), el efecto se vuelve a disparar y lo cierra en el mismo ciclo cuando la ruta sigue sin `chatId`.

### 4) En primer mensaje se actualiza `currentChatId`, pero no siempre se estabiliza ruta
- En flujo de respuesta, cuando `!currentChatId && response.chat_id`, se hace `setCurrentChatId(response.chat_id)` sin navegación directa en ese punto.
- Referencia: `apps/web/src/app/chat/_components/ChatView.tsx:1061`.
- Conclusión: puede existir ventana donde ya hay conversación activa, pero aún no hay `resolvedChatId`; ahí se reproduce el cierre inmediato.

### 5) Evidencia indirecta de inestabilidad en apertura inicial
- En Page Object de Playwright hay retry explícito por “intermittent first-click misses in canvas activation”.
- Referencia: `apps/web/e2e/pages/ChatPage.ts:153`.
- Conclusión: el comportamiento intermitente ya estaba reconocido en tests.

## Trazado de la falla (timeline)

1. Usuario en `/chat` (sin `chatId`).
2. Llega respuesta con chart y botón visible.
3. Click en “Abrir … en canvas” => `openBankChart` setea `isSidebarOpen: true`.
4. `isCanvasOpen` cambia en `ChatView`.
5. Efecto de reset se ejecuta por dependencia `isCanvasOpen`.
6. Como `resolvedChatId` sigue `null`, ejecuta `closeCanvas + resetCanvas`.
7. Usuario percibe que el panel “no abre”.

## Pruebas ejecutadas durante investigación

### Unit / integration (Jest)
- Comando:
  - `cd apps/web && pnpm test -- src/components/chat/__tests__/ChatMessage.bankChart.test.tsx src/components/chat/__tests__/BankChartPreview.test.tsx src/lib/stores/__tests__/canvas-store.bankChart.test.ts`
- Resultado:
  - 3 suites pass, 41 tests pass.
- Lectura:
  - Cobertura actual valida store/componentes de chart, pero no el escenario de `/chat` sin `chatId`.

### Canvas integration (Jest)
- Comando:
  - `cd apps/web && pnpm test -- src/components/canvas/__tests__/BankChartCanvas.e2e.test.tsx`
- Resultado:
  - 1 suite pass, 13 tests pass.
- Lectura:
  - Confirma render y flujo local de canvas, no la sincronización ruta-chat de `ChatView`.

### Playwright targeted
- Comando:
  - `cd apps/web && pnpm exec playwright test e2e/tests/chat.spec.ts -g "help onboarding opens chart and waits for complete render" --project=chromium`
- Resultado:
  - failed por timeout en paso onboarding (`help-onboarding-next`) antes de validar apertura canvas.
- Lectura:
  - No bloquea diagnóstico de causa raíz, pero sí deja pendiente un test de regresión dedicado al escenario `/chat` sin `chatId`.

## Conclusión

La causa raíz está en el frontend (`ChatView`) por acoplamiento entre:
- resolución de chat por URL (`resolvedChatId`),
- reset forzado cuando no hay chat en URL,
- y dependencia del efecto en `isCanvasOpen`.

No se observaron evidencias de problema en MCP, Redis o parsing de `bank_chart_data` para este síntoma específico.
