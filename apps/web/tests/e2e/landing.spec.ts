import { test, expect } from "@playwright/test";

test.describe("Landing page", () => {
  test("muestra los CTAs principales", async ({ page }) => {
    await page.goto("/");

    const loginLink = page.getByRole("link", { name: /Iniciar sesión/i });
    const registerLink = page.getByRole("link", { name: /Crear cuenta/i });

    await expect(loginLink).toBeVisible();
    await expect(registerLink).toBeVisible();
  });

  test("no muestra alertas de error al cargar", async ({ page }) => {
    await page.goto("/");
    const errorAlerts = page
      .getByRole("alert", { includeHidden: true })
      .filter({ hasText: /error|incorrect|expirad|contraseñ|alerta/i });

    // Route announcers (Next.js) are hidden and have navigation text; this only fails on real error banners.
    await expect(errorAlerts).toHaveCount(0);
  });
});
