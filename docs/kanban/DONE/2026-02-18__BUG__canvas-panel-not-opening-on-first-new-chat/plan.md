# Plan — Fix canvas en primer chat nuevo

## Status: Draft

## Estrategia recomendada

Separar la lógica de “cambio de conversación” de la lógica de “estado abierto/cerrado del canvas”, y basar el ownership en un `effectiveChatId` estable (`resolvedChatId ?? currentChatId`) para evitar resets cuando la ruta todavía está en `/chat`.

## Fase 1 — Corregir efecto de reset en `ChatView`

**Archivo:** `apps/web/src/app/chat/_components/ChatView.tsx`

1. Evitar que el efecto de cambio de conversación dependa de `isCanvasOpen`.
2. Ejecutar reset solo cuando realmente cambie el identificador de conversación efectivo.
3. Mantener excepción de reconciliación `temp-* -> real` para no cerrar canvas durante transición legítima.

Objetivo:
- Abrir canvas no debe provocar un segundo efecto que lo cierre por no tener chatId en URL.

## Fase 2 — Unificar fuente de verdad de conversación para canvas

**Archivo:** `apps/web/src/app/chat/_components/ChatView.tsx`

1. Calcular `effectiveChatId = resolvedChatId ?? currentChatId ?? null`.
2. Usar `effectiveChatId` para `setCurrentSessionId(...)` del canvas store.
3. Solo resetear cuando `effectiveChatId` sea realmente `null` y no exista conversación activa.

Objetivo:
- En primer turno de `/chat`, si ya existe `currentChatId`, no cerrar canvas como si no hubiera conversación.

## Fase 3 — Estabilizar navegación al crear conversación desde `/chat`

**Archivo:** `apps/web/src/app/chat/_components/ChatView.tsx`

1. Revisar el branch `!currentChatId && response.chat_id` para alinear URL (`router.replace`) cuando aplique.
2. Evitar que la vista permanezca en `/chat` demasiado tiempo cuando ya existe `chat_id` backend.

Objetivo:
- Reducir ventanas de estado inconsistente entre URL y store.

## Fase 4 — Agregar pruebas de regresión

### 4a. E2E dedicado al bug

Agregar caso que:
1. Inicia en `/chat`.
2. Mockea respuesta con `bank_chart_data`.
3. Da un solo click a “Abrir gráfica … en canvas”.
4. Verifica panel visible sin retry ni doble click.

### 4b. Cobertura adicional de integración (opcional)

Agregar test de integración para la lógica de resolución de chat y reset del canvas en `ChatView` o extraer helper puro para testear transiciones.

## Validación propuesta

```bash
cd apps/web && pnpm test -- src/components/chat/__tests__/ChatMessage.bankChart.test.tsx src/components/chat/__tests__/BankChartPreview.test.tsx src/lib/stores/__tests__/canvas-store.bankChart.test.ts
cd apps/web && pnpm test -- src/components/canvas/__tests__/BankChartCanvas.e2e.test.tsx
cd apps/web && pnpm exec playwright test e2e/tests/chat.spec.ts --project=chromium
```

## Riesgos y mitigación

1. Riesgo: romper cierre de canvas al cambiar conversación.
   Mitigación: pruebas explícitas de A->B, B->A y temp->real.
2. Riesgo: introducir side effects por navegación automática.
   Mitigación: condicionar `router.replace` a cambios reales de sesión y preservar UX de draft.
3. Riesgo: duplicar resets entre `CanvasContext` y `ChatView`.
   Mitigación: centralizar criterio de ownership por conversación y documentarlo en comentarios.
