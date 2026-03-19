import { test, expect } from "@playwright/test";

const DEMO_USER = process.env.PLAYWRIGHT_DEMO_USER || "demo@example.com";
const DEMO_PASS = process.env.PLAYWRIGHT_DEMO_PASS || "Demo1234";

test.describe("Flujo de login y chat", () => {
  test("permite iniciar sesión y muestra el composer del chat", async ({
    page,
    context,
  }) => {
    // Limpia estado previo
    await context.clearCookies();
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());

    await page.goto("/login");

    await page
      .getByLabel("Correo electrónico o usuario")
      .fill(DEMO_USER, { timeout: 10_000 });
    await page.getByLabel("Contraseña").fill(DEMO_PASS);

    await page.getByRole("button", { name: /Iniciar sesión/i }).click();

    await page.waitForURL("**/chat*", { timeout: 30_000 });
    await expect(page).toHaveURL(/\/chat/);

    const composerInput = page.getByLabel("Escribe tu mensaje");
    await expect(composerInput).toBeVisible();

    // Verifica que el botón de enviar se habilita al escribir
    await composerInput.fill("Hola Playwright");
    const sendButton = page.getByRole("button", {
      name: /Enviar mensaje|Subiendo archivos|Analizando/i,
    });
    await expect(sendButton).toBeEnabled();

    // Envía un mensaje y espera una respuesta del asistente
    const assistantMessages = page.getByRole("article", {
      name: /Respuesta del asistente/i,
    });
    const beforeCount = await assistantMessages.count();

    await sendButton.click();

    await expect(assistantMessages).toHaveCount(beforeCount + 1, {
      timeout: 60_000,
    });
    await expect(assistantMessages.nth(beforeCount)).toContainText(/./, {
      timeout: 10_000,
    });
  });
});
