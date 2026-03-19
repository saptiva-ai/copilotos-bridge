# Validate — Canvas no abre en primer chat nuevo

## Status: Partial

## Comandos ejecutados (investigación)

1. `cd apps/web && pnpm test -- src/components/chat/__tests__/ChatMessage.bankChart.test.tsx src/components/chat/__tests__/BankChartPreview.test.tsx src/lib/stores/__tests__/canvas-store.bankChart.test.ts`
   - Resultado: ✅ PASS (3 suites, 41 tests).
   - Nota: cobertura de store/componentes, no del caso `/chat` sin `chatId`.

2. `cd apps/web && pnpm test -- src/components/canvas/__tests__/BankChartCanvas.e2e.test.tsx`
   - Resultado: ✅ PASS (1 suite, 13 tests).
   - Nota: valida render/flujo canvas local, no transición URL/store.

3. `cd apps/web && pnpm exec playwright test e2e/tests/chat.spec.ts -g "help onboarding opens chart and waits for complete render" --project=chromium`
   - Resultado: ❌ FAIL (timeout previo en onboarding, antes de validar apertura de canvas).
   - Error: `locator.click` timeout en `getByTestId('help-onboarding-next')`.

## Comandos ejecutados (post-fix implementado)

1. `cd apps/web && pnpm test -- src/app/chat/_components/__tests__/chat-view-canvas-utils.test.ts src/components/chat/__tests__/ChatMessage.bankChart.test.tsx src/components/chat/__tests__/BankChartPreview.test.tsx src/lib/stores/__tests__/canvas-store.bankChart.test.ts src/components/canvas/__tests__/BankChartCanvas.e2e.test.tsx`
   - Resultado: ✅ PASS (5 suites, 64 tests).
   - Nota: incluye nueva cobertura para transición de canvas por chat efectivo (`resolvedChatId`/`currentChatId`).

2. `cd apps/web && pnpm typecheck`
   - Resultado: ✅ PASS.

3. `cd apps/web && pnpm lint --file src/app/chat/_components/ChatView.tsx --file src/app/chat/_components/chat-view-canvas-utils.ts`
   - Resultado: ✅ PASS (sin warnings/errors).

4. `cd apps/web && pnpm exec playwright test e2e/tests/chart-caching.spec.ts --project=chromium`
   - Resultado: ❌ FAIL en setup de autenticación.
   - Error: `net::ERR_EMPTY_RESPONSE at http://127.0.0.1:3000/chat`.

5. `cd apps/web && pnpm exec playwright test e2e/tests/canvas-first-open.spec.ts --list`
   - Resultado: ✅ PASS (test discoverable/parsing OK para Chromium y Firefox).
   - Nota: se agregó regresión dedicada de single-click en `/chat` sin `chatId`.

6. `cd apps/web && pnpm lint --file e2e/tests/canvas-first-open.spec.ts`
   - Resultado: ✅ PASS (sin warnings/errors).

7. `cd apps/web && CI=1 pnpm exec playwright test e2e/tests/canvas-first-open.spec.ts --project=chromium --workers=1`
   - Resultado: ✅ PASS (setup + chromium, 2/2 tests).
   - Nota: se añadió `mockApi.injectAuthState(page)` + `page.goto("/chat")` al test para estabilizar auth en contexto de ejecución.

8. `cd apps/web && CI=1 pnpm run test:e2e:pdf -- --project=chromium e2e/tests/canvas-first-open.spec.ts`
   - Resultado: ✅ PASS (setup + chromium, 2/2 tests) con generación de artefactos.
   - JSON: `/home/jazielflo/Proyects/octavios-chat-bajaware_invex/docs/reports/playwright/playwright-e2e__canvas-first-open__20260218T073758Z.json`
   - PDF: `/home/jazielflo/Proyects/octavios-chat-bajaware_invex/docs/reports/playwright/playwright-e2e__canvas-first-open__20260218T073758Z.pdf`

## Validación pendiente post-fix

1. Crear/ajustar E2E específico para:
   - iniciar en `/chat`,
   - generar chart mockeado,
   - verificar apertura de canvas con un solo click sin retry.
2. Ejecutar suite E2E del flujo de chart-canvas sin workaround de doble click.
