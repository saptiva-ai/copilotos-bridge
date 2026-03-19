# Playwright Conversation Test Kit

Guía práctica para crear y mantener tests E2E conversacionales (multi-turn) en `apps/web/e2e`, usando utilidades reutilizables para:

- routing semántico por intención,
- validación de outputs (chat + canvas),
- verificación de grounding tabla (periodo/valor),
- adjuntos JSON de evidencia para reportes.

## 1. Prerrequisitos

- Frontend y backend levantados (`make dev` o setup equivalente).
- Dependencias del web instaladas.
- Playwright de Node disponible (evita usar el binario Python por error).

Desde `apps/web`:

```bash
PATH="$(pwd)/node_modules/.bin:$PATH" bunx playwright --version
```

## 2. Componentes Reutilizables

Archivo base: `apps/web/e2e/utils/conversation-test-kit.ts`

Funciones principales:

1. `createChartStreamScenarios(turns)`
- Genera `ChatStreamScenario[]` desde definiciones de turno (matcher + payload).

2. `runChartTurn(options)`
- Ejecuta un turno completo:
- envía query,
- espera respuesta y botones de gráfica,
- opcionalmente abre canvas y espera render completo,
- opcionalmente valida grounding en tab `Datos`,
- opcionalmente adjunta evidencia JSON.

3. `attachGroundingEvidence(testInfo, options)`
- Helper para adjuntar evidencia manual cuando se necesita control fino.

## 3. Cómo Crear un Test Nuevo

### Paso A: Definir escenario conversacional

```ts
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
```

### Paso B: Convertir a escenarios mock

```ts
const { scenarios } = createChartStreamScenarios(turnDefs);
await mockApi.mockChatStreamByQuery(page, scenarios);
```

### Paso C: Ejecutar turnos con validaciones

```ts
await runChartTurn({
  query: "ICAP de BBVA en 2025",
  expectedChartButtons: 1,
  chatPage,
  canvasPage,
  assertions: {
    chartButtonMustContain: /BBVA/i,
    assistantMustContain: [/BBVA/i],
    grounding: {
      bankName: "BBVA",
      period: "2025-03-01",
      valuePattern: /19\.60/,
    },
  },
  testInfo,
  evidenceName: "grounding-bbva-turn-1.json",
});
```

## 4. Patrón Recomendado para Conversaciones Largas

1. Modelar cada turno con un `matcher` semántico (banco/métrica/año), no por orden fijo.
2. En cada iteración, usar `expectedChartButtons = index + 1` para validar acumulación correcta.
3. Adjuntar una evidencia por turno (`grounding-*.json`) para trazabilidad.
4. Reusar los mismos `ChatPage` y `CanvasPage` para todo el test (menos ruido y más velocidad).

## 5. Outputs a Validar (Checklist)

- Chat:
- mensaje del asistente contiene entidad esperada.
- botón de gráfica corresponde al banco/métrica.

- Canvas:
- panel abre correctamente.
- gráfica termina de renderizar (sin skeleton incompleto).
- tab `Datos` contiene fila `Banco + Periodo + Valor`.

- Evidencia:
- `testInfo.attach` con JSON por turno para auditoría.

## 6. Ejecutar Tests

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

Con PDF:

```bash
PATH="$(pwd)/node_modules/.bin:$PATH" \
E2E_SKIP_PDF=0 E2E_REPORT_MODE=1 \
bash ./scripts/run-e2e-with-pdf-report.sh e2e/tests/bank-advisor.spec.ts --project=chromium
```

## 7. Troubleshooting

### Error: `unknown command 'test'`

Causa: se está usando `playwright` de Python en lugar de Node.

Solución:

```bash
PATH="$(pwd)/node_modules/.bin:$PATH" bash ./scripts/run-e2e-with-pdf-report.sh ...
```

### El screenshot final sale con chart incompleto

Verifica que el test use `runChartTurn(...)` con `openCanvas` o `grounding`, ya que el helper espera render completo antes de cerrar el turno.

### Falsos negativos con regex

Usa `RegExp` sin flag global (`g`) para expectations. El kit ya normaliza flags para evitar tests stateful, pero es mejor evitar `g` en assertions.

## 8. Referencias en Código

- Kit reusable: `apps/web/e2e/utils/conversation-test-kit.ts`
- Ejemplo simple: `apps/web/e2e/tests/bank-advisor.spec.ts`
- Ejemplo multi-turn largo: `apps/web/e2e/tests/chart-caching.spec.ts`
- Page Objects:
- `apps/web/e2e/pages/ChatPage.ts`
- `apps/web/e2e/pages/CanvasPage.ts`
