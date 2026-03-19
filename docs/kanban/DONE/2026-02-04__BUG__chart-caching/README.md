# Playwright E2E Harness for Bank Charts

Este README documenta el patron reusable para pruebas E2E de `bank_chart` en el stack nuevo (`apps/web/e2e/**`).

## Objetivo

- Mockear `/api/chat` por intencion semantica (no por orden de requests).
- Reusar builders de payload SSE para reducir duplicacion.
- Verificar grounding real: boton de chart + datos en tabla del canvas (`Periodo`/`Valor`).

## Piezas reutilizables

- `apps/web/e2e/utils/bank-chart-fixtures.ts`
  - `buildChartPayload(...)`
  - `buildChartSSEEvents(...)`
- `apps/web/e2e/utils/mock-api.ts`
  - `mockChatStreamByQuery(page, scenarios, options?)`
- `apps/web/e2e/pages/ChatPage.ts`
  - `waitForChartButtonsCount(...)`
  - `openLastChartButton()`
- `apps/web/e2e/pages/CanvasPage.ts`
  - `openDataTab()`
  - `expectDataRow({ bankName, period, valuePattern })`

## Patron recomendado

```ts
const payload = buildChartPayload({
  chatId: "mock-chat",
  messageId: "msg-1",
  artifactId: "artifact-shared",
  bankName: "BBVA",
  title: "ICAP BBVA 2025",
  periods: ["2025-01-01", "2025-02-01", "2025-03-01"],
  values: [19.1, 19.3, 19.6],
});

await mockApi.mockChatStreamByQuery(page, [
  {
    name: "bbva-icap",
    matcher: /\bbbva\b/i,
    events: buildChartSSEEvents(payload),
  },
]);
```

## Assertions minimas (anti-falsos verdes)

1. Enviar mensaje con `ChatPage.sendMessage(...)`.
2. Esperar boton con `waitForChartButtonsCount(...)`.
3. Abrir ultimo chart con `openLastChartButton()`.
4. Abrir tab `Datos` en canvas.
5. Validar una fila concreta (`Banco`, `Periodo`, `Valor`) con `expectDataRow(...)`.

## Ejecucion local

Desde `apps/web`:

```bash
PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000 pnpm exec playwright test --project=chromium e2e/tests/chart-caching.spec.ts
PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000 pnpm exec playwright test --project=chromium e2e/tests/bank-advisor.spec.ts
PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000 pnpm run test:e2e:pdf -- --project=chromium
```

Desde raíz del repo (Makefile):

```bash
make test.e2e.pdf TEST_ARGS="--project=chromium"
make test.e2e.pdf.strict TEST_ARGS="--project=chromium"
make test.e2e.fast TEST_ARGS="--project=chromium"
```

Opciones del wrapper:

```bash
# Omitir PDF (solo ejecutar tests)
E2E_SKIP_PDF=1 make test.e2e.pdf TEST_ARGS="--project=chromium"

# Cambiar URL base/puerto para Playwright + preflight
E2E_BASE_URL=http://127.0.0.1:3100 make test.e2e.pdf TEST_ARGS="--project=chromium"

# Requerir PDF en pipelines (falla si no se genera)
E2E_PDF_STRICT=1 make test.e2e.pdf TEST_ARGS="--project=chromium"

# Desactivar preflight de puerto (casos especiales)
E2E_PREFLIGHT=0 make test.e2e.pdf TEST_ARGS="--project=chromium"

# Ajustar timeout de preflight (ms)
E2E_PREFLIGHT_TIMEOUT_MS=5000 make test.e2e.pdf TEST_ARGS="--project=chromium"

# Forzar tipo semantico del reporte (si no se detecta automaticamente)
E2E_REPORT_TYPE=chart-grounding make test.e2e.pdf TEST_ARGS="--project=chromium e2e/tests/chart-caching.spec.ts"
```

## Ubicacion y nombre de reportes

- PDF y JSON se guardan en `docs/reports/playwright/`.
- Patron de nombre:
  - `playwright-e2e__<test-type>__<YYYYMMDDTHHMMSSZ>.pdf`
  - `playwright-e2e__<test-type>__<YYYYMMDDTHHMMSSZ>.json`
- `test-type` se detecta por:
  - archivo `.spec.ts` pasado en args, o
  - `--project=<name>`, o
  - `E2E_REPORT_TYPE` (prioridad mas alta).

## Notas de robustez

- `testAuthState.version` debe ser `1` para evitar limpieza por migracion de `auth-store`.
- Evitar selectores por clases CSS para previews; usar roles/labels estables del flujo real.
- Preferir matchers semanticos (`matcher: /bbva|santander/i`) sobre `requestCount`.
- El wrapper hace preflight del puerto de `E2E_BASE_URL`; si el puerto esta ocupado por otro proceso no-HTTP, falla rapido con mensaje claro.
- `E2E_PDF_STRICT=1` reduce falsos verdes en CI cuando el test pasa pero el artefacto PDF no se genera.
- `test.e2e.fast` es util para debug rapido local y evitar costo de render de PDF en ciclos cortos.
- En modo reporte (`test:e2e:pdf`) se capturan screenshots tambien en tests exitosos para evidencia.
- El PDF ahora incluye metadatos de run (commit, comando, URL base, workers, stats) y secciones de grounding `expected vs actual` cuando los tests adjuntan JSON.
