import { test, expect } from "../fixtures";
import { ChatPage } from "../pages/ChatPage";
import { CanvasPage } from "../pages/CanvasPage";
import {
  buildChartPayload,
  buildChartSSEEvents,
} from "../utils/bank-chart-fixtures";

const OPEN_CHART_BUTTON_REGEX =
  /Abrir grafica de .* en canvas|Abrir gráfica de .* en canvas/i;

test.describe("Canvas first-open regression", () => {
  test("opens canvas on first click in /chat new conversation", async ({
    chatPage: page,
    mockApi,
  }) => {
    const chatPage = new ChatPage(page);
    const canvasPage = new CanvasPage(page);

    const payload = buildChartPayload({
      chatId: "22222222-2222-2222-2222-222222222222",
      messageId: "msg-first-open-001",
      artifactId: "artifact-first-open-001",
      bankName: "BBVA",
      title: "ICAP BBVA 2025",
      metricName: "icap_total",
      periods: ["2025-01-01", "2025-02-01", "2025-03-01"],
      values: [14.2, 14.5, 14.8],
      content: "Comparativo ICAP generado para validar apertura de canvas.",
    });

    await mockApi.mockChatStreamByQuery(
      page,
      [
        {
          name: "first-open-canvas",
          matcher: /icap|bbva/i,
          events: buildChartSSEEvents(payload),
        },
      ],
      {
        defaultEvents: buildChartSSEEvents(payload),
      },
    );

    // Stabilize auth state in this page context (same pattern used by chart-caching spec).
    await mockApi.injectAuthState(page);
    await page.goto("/chat");

    await chatPage.waitForComposerReady();
    await chatPage.sendMessage("ICAP de BBVA en 2025");
    await chatPage.waitForResponse();

    const openButton = page
      .getByRole("button", { name: OPEN_CHART_BUTTON_REGEX })
      .last();
    await expect(openButton).toBeVisible({ timeout: 30_000 });

    // Regression assertion: single click should open the panel.
    await openButton.click();

    await canvasPage.waitForPanel(30_000);
    await canvasPage.waitForChartSelection(30_000);
    await canvasPage.waitForChartRendered(30_000);
    await expect(canvasPage.plotContainer).toHaveAttribute(
      "data-chart-ready",
      "true",
      { timeout: 30_000 },
    );
  });
});
