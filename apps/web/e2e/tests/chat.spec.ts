import type { Page, TestInfo } from "@playwright/test";
import { test, expect } from "../fixtures";
import { ChatPage } from "../pages/ChatPage";
import { CanvasPage } from "../pages/CanvasPage";
import { attachGroundingEvidence } from "../utils/conversation-test-kit";
import {
  buildChartPayload,
  buildChartSSEEvents,
} from "../utils/bank-chart-fixtures";
import { testSSEChunks } from "../utils/test-data";

const HELP_PROMPT_STEP_2 =
  "Compara el ICAP de BBVA y Santander en 2025 en formato tabular con periodos exactos.";
const ONBOARDING_EXPECTED_PERIOD = "2025-03-01";
const ONBOARDING_EXPECTED_VALUE_PATTERN = /14[.,]8/;

const onboardingChartPayload = buildChartPayload({
  chatId: "11111111-1111-1111-1111-111111111111",
  messageId: "msg-onboarding-chart-001",
  artifactId: "artifact-onboarding-icap-001",
  bankName: "BBVA",
  title: "ICAP - BBVA vs Santander (2025)",
  metricName: "icap_total",
  periods: ["2025-01-01", "2025-02-01", "2025-03-01"],
  values: [14.2, 14.5, 14.8],
  content:
    "Comparativo ICAP 2025: BBVA y Santander muestran estabilidad, con tendencia al alza.",
});

const onboardingChartScenario = {
  name: "onboarding-icap-chart",
  matcher: (message: string) =>
    /icap/i.test(message) &&
    /bbva/i.test(message) &&
    /santander/i.test(message),
  events: buildChartSSEEvents(onboardingChartPayload),
};
const OPEN_CHART_BUTTON_REGEX =
  /Abrir grafica de .* en canvas|Abrir gráfica de .* en canvas/i;

async function attachStepScreenshot(
  page: Page,
  testInfo: TestInfo,
  filename: string,
): Promise<void> {
  await testInfo.attach(filename, {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
}

test.describe("Chat", () => {
  test("send message and receive streamed response", async ({
    chatPage: page,
    mockApi,
  }) => {
    await mockApi.mockChatStream(page, testSSEChunks);
    const chatPage = new ChatPage(page);

    await chatPage.sendMessage("Hola, ¿cómo estás?");

    // Wait for the assistant response to appear
    await chatPage.waitForResponse();

    const lastMessage = await chatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
  });

  test("help onboarding menu opens, injects exact prompt and closes", async ({
    chatPage: page,
  }) => {
    const chatPage = new ChatPage(page);

    await expect(chatPage.composerInput).toHaveValue("");
    await expect(chatPage.helpOnboardingTrigger).toHaveAttribute(
      "aria-expanded",
      "false",
    );

    await chatPage.openHelpOnboarding();
    await expect(chatPage.helpOnboardingTrigger).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    await expect(chatPage.helpOnboardingStepTitle).toHaveText(
      "Paso 1: Consulta Base",
    );
    await chatPage.helpOnboardingNext.click();
    await expect(chatPage.helpOnboardingStepTitle).toHaveText(
      "Paso 2: Comparativo",
    );
    await expect(chatPage.helpOnboardingStepPrompt).toHaveText(
      HELP_PROMPT_STEP_2,
    );
    await chatPage.helpOnboardingUsePrompt.click();
    await expect(chatPage.composerInput).toHaveValue(HELP_PROMPT_STEP_2);
    await expect(chatPage.helpOnboardingMenu).toHaveCount(0);
    await expect(chatPage.helpOnboardingTrigger).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  test("help onboarding opens chart and waits for complete render", async ({
    chatPage: page,
    mockApi,
  }, testInfo) => {
    test.setTimeout(90_000);
    const chatPage = new ChatPage(page);
    const canvasPage = new CanvasPage(page);
    const chatId = "11111111-1111-1111-1111-111111111111";

    await mockApi.mockChatStreamByQuery(page, [onboardingChartScenario], {
      defaultEvents: buildChartSSEEvents(onboardingChartPayload),
    });
    await chatPage.navigate(chatId);

    await expect(chatPage.composerInput).toHaveValue("");
    await chatPage.openHelpOnboarding();
    await attachStepScreenshot(
      page,
      testInfo,
      "step-01-onboarding-menu-open.png",
    );

    await chatPage.helpOnboardingNext.click();
    await expect(chatPage.helpOnboardingStepTitle).toHaveText(
      "Paso 2: Comparativo",
    );
    await chatPage.helpOnboardingUsePrompt.click();
    await expect(chatPage.composerInput).toHaveValue(HELP_PROMPT_STEP_2);
    await attachStepScreenshot(page, testInfo, "step-02-prompt-injected.png");

    await chatPage.sendButton.click();
    await chatPage.waitForResponse();
    await chatPage.waitForChartButtonsCount(1);
    await attachStepScreenshot(
      page,
      testInfo,
      "step-03-chart-artifact-visible.png",
    );

    await expect(
      page.getByRole("button", { name: OPEN_CHART_BUTTON_REGEX }).last(),
    ).toBeVisible({ timeout: 30_000 });
    await page
      .getByRole("button", { name: OPEN_CHART_BUTTON_REGEX })
      .last()
      .click();
    await page
      .getByRole("button", { name: OPEN_CHART_BUTTON_REGEX })
      .last()
      .click();
    await canvasPage.waitForPanel();
    await expect(page.getByRole("button", { name: /^Datos$/i })).toBeVisible({
      timeout: 30_000,
    });
    await canvasPage.waitForChartRendered();
    await expect(canvasPage.plotContainer).toHaveAttribute(
      "data-chart-ready",
      "true",
    );
    await expect(canvasPage.chartSkeleton).toHaveCount(0);
    await attachStepScreenshot(page, testInfo, "step-04-chart-rendered.png");

    await canvasPage.openDataTab();
    await canvasPage.expectDataRow({
      bankName: "BBVA",
      period: ONBOARDING_EXPECTED_PERIOD,
      valuePattern: ONBOARDING_EXPECTED_VALUE_PATTERN,
    });
    const dataRows = await canvasPage.getDataRows();
    const matchedRow =
      dataRows.find(
        (row) =>
          row.bank.toUpperCase().includes("BBVA") &&
          row.period === ONBOARDING_EXPECTED_PERIOD,
      ) ?? null;

    await attachGroundingEvidence(testInfo, {
      filename: "onboarding-expected-actual.json",
      label: "Onboarding ICAP chart period/value grounding",
      query: HELP_PROMPT_STEP_2,
      expected: {
        bankName: "BBVA",
        period: ONBOARDING_EXPECTED_PERIOD,
        valuePattern: ONBOARDING_EXPECTED_VALUE_PATTERN,
      },
      matchedRow,
      rows: dataRows,
    });
    await attachStepScreenshot(
      page,
      testInfo,
      "step-05-data-tab-grounding.png",
    );
  });

  test("help onboarding menu closes with Escape and outside click", async ({
    chatPage: page,
  }) => {
    const chatPage = new ChatPage(page);

    await chatPage.openHelpOnboarding();
    await page.keyboard.press("Escape");
    await expect(chatPage.helpOnboardingMenu).toHaveCount(0);
    await expect(chatPage.helpOnboardingTrigger).toHaveAttribute(
      "aria-expanded",
      "false",
    );

    await chatPage.openHelpOnboarding();
    await page.mouse.click(30, 80);
    await expect(chatPage.helpOnboardingMenu).toHaveCount(0);
    await expect(chatPage.helpOnboardingTrigger).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  test("hero heading is visible on empty chat", async ({ chatPage: page }) => {
    await expect(page.getByText(/¿Cómo puedo ayudarte/i)).toBeVisible();
  });

  test("chat composer has focus", async ({ chatPage: page }) => {
    const chatPage = new ChatPage(page);

    // The composer textarea should be ready for input
    await expect(chatPage.composerInput).toBeVisible();
    // Verify it's interactive by filling text
    await chatPage.composerInput.fill("test");
    await expect(chatPage.composerInput).toHaveValue("test");
  });

  test("send button is disabled when input is empty", async ({
    chatPage: page,
  }) => {
    const chatPage = new ChatPage(page);

    // With empty input, send should be disabled
    await chatPage.composerInput.fill("");
    await expect(chatPage.sendButton).toBeDisabled();
  });
});

test.describe("Chat integration (real backend)", () => {
  test.use({ useApiMocks: false });

  test.skip(
    !process.env.E2E_USER_EMAIL || !process.env.E2E_USER_PASSWORD,
    "Set E2E_USER_EMAIL and E2E_USER_PASSWORD to run real-backend onboarding E2E",
  );

  test("help onboarding renders chart in real backend flow", async ({
    chatPage: page,
  }, testInfo) => {
    const chatPage = new ChatPage(page);
    const canvasPage = new CanvasPage(page);

    await expect(chatPage.composerInput).toHaveValue("", { timeout: 20_000 });
    await chatPage.openHelpOnboarding();
    await chatPage.helpOnboardingUsePrompt.click();
    await expect(chatPage.composerInput).not.toHaveValue("");
    await attachStepScreenshot(page, testInfo, "real-step-01-prompt-ready.png");

    await chatPage.sendButton.click();
    await chatPage.waitForResponse(60_000);
    await expect(chatPage.chartButtons.first()).toBeVisible({
      timeout: 60_000,
    });
    await attachStepScreenshot(
      page,
      testInfo,
      "real-step-02-chart-button-visible.png",
    );

    await chatPage.openLastChartButton();
    await canvasPage.waitForPanel(30_000);
    await canvasPage.waitForChartSelection(30_000);
    await canvasPage.waitForChartRendered(45_000);
    await expect(canvasPage.plotContainer).toHaveAttribute(
      "data-chart-ready",
      "true",
      { timeout: 45_000 },
    );
    await expect(canvasPage.chartSkeleton).toHaveCount(0, {
      timeout: 45_000,
    });
    await attachStepScreenshot(
      page,
      testInfo,
      "real-step-03-chart-rendered.png",
    );
  });
});

test.describe("Chat mobile", () => {
  test.use({
    viewport: { width: 390, height: 844 },
  });

  test("help onboarding works in mobile viewport", async ({
    chatPage: page,
  }) => {
    const chatPage = new ChatPage(page);

    await expect(chatPage.composerInput).toHaveValue("");
    await chatPage.openHelpOnboarding();
    await expect(chatPage.helpOnboardingMenu).toBeVisible();
    await chatPage.helpOnboardingNext.click();
    await expect(chatPage.helpOnboardingStepTitle).toHaveText(
      "Paso 2: Comparativo",
    );
    await chatPage.helpOnboardingUsePrompt.click();
    await expect(chatPage.composerInput).toHaveValue(HELP_PROMPT_STEP_2);
  });
});
