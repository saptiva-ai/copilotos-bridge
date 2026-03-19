# Playwright E2E Conversation Test Kit

## Objetivo

Estandarizar tests E2E conversacionales (multi-turn) para:

- routing semántico por intención del usuario,
- validación de outputs de UI (mensaje, botón de gráfica, canvas),
- validación de grounding tabla (periodo/valor),
- adjuntos JSON de evidencia para reportes.

Implementación base: `apps/web/e2e/utils/conversation-test-kit.ts`.

## API Reutilizable

1. `createChartStreamScenarios(turns)`
- Convierte definiciones por turno en `ChatStreamScenario[]` + payloads mock.

2. `runChartTurn(options)`
- Ejecuta un turno completo:
- envía query,
- espera respuesta y crecimiento de botones de gráfica,
- opcionalmente abre canvas y espera render completo,
- opcionalmente valida grounding en tab `Datos`,
- opcionalmente adjunta evidencia JSON al reporte del test.

3. `attachGroundingEvidence(testInfo, options)`
- Adjunta manualmente evidencia de grounding cuando se necesite control fino.

## Patrón Recomendado

```ts
import { test } from "../fixtures";
import { ChatPage } from "../pages/ChatPage";
import { CanvasPage } from "../pages/CanvasPage";
import {
  createChartStreamScenarios,
  runChartTurn,
} from "../utils/conversation-test-kit";

const CHAT_ID = "11111111-1111-1111-1111-111111111111";

const turnDefs = [
  {
    name: "bbva-icap",
    matcher: /\bbbva\b/i,
    payload: {
      chatId: CHAT_ID,
      messageId: "mock-msg-1",
      artifactId: "temp",
      bankName: "BBVA",
      title: "ICAP BBVA 2025",
      periods: ["2025-01-01", "2025-02-01", "2025-03-01"],
      values: [19.1, 19.3, 19.6],
    },
  },
];

test("multi-turn chart grounding", async ({ chatPage: page, mockApi }, testInfo) => {
  const { scenarios } = createChartStreamScenarios(turnDefs);
  await mockApi.mockChatStreamByQuery(page, scenarios);
  await page.goto(`/chat/${CHAT_ID}`);

  const chatPage = new ChatPage(page);
  const canvasPage = new CanvasPage(page);

  await runChartTurn({
    query: "ICAP de BBVA en 2025",
    expectedChartButtons: 1,
    chatPage,
    canvasPage,
    assertions: {
      chartButtonMustContain: /BBVA/i,
      grounding: {
        bankName: "BBVA",
        period: "2025-03-01",
        valuePattern: /19\.60/,
      },
    },
    testInfo,
    evidenceName: "grounding-bbva-1.json",
  });
});
```

## Qué Validar en Conversaciones Largas

1. Turn-by-turn routing:
- `matcher` semántico por banco/métrica/año, no por orden fijo.

2. Consistencia visual:
- botón de gráfica correcto por turno,
- canvas abre y el chart termina de renderizar antes de cerrar test.

3. Grounding fuerte:
- fila exacta `Banco + Periodo`,
- valor esperado con `RegExp` o string.

4. Evidencia para auditoría:
- adjuntar `grounding-*.json` por turno.

## Comandos Útiles

Desde `apps/web`:

```bash
PATH="$(pwd)/node_modules/.bin:$PATH" \
E2E_SKIP_PDF=1 E2E_REPORT_MODE=0 \
bash ./scripts/run-e2e-with-pdf-report.sh e2e/tests/bank-advisor.spec.ts --project=chromium
```

```bash
PATH="$(pwd)/node_modules/.bin:$PATH" \
E2E_SKIP_PDF=1 E2E_REPORT_MODE=0 \
bash ./scripts/run-e2e-with-pdf-report.sh e2e/tests/chart-caching.spec.ts --project=chromium
```
