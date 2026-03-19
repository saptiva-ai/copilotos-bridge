import { test, expect } from "@playwright/test";

test.describe("Autenticación", () => {
  test("renderiza el formulario de login con campos requeridos", async ({
    page,
  }) => {
    await page.goto("/login");

    await expect(
      page.getByRole("heading", { name: /Iniciar sesión/i }),
    ).toBeVisible();
    await expect(page.getByLabel("Correo electrónico o usuario")).toBeVisible();
    await expect(page.getByLabel("Contraseña")).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Iniciar sesión/i }),
    ).toBeEnabled();
  });

  test("muestra enlaces de recuperación y registro", async ({ page }) => {
    await page.goto("/login");

    await expect(
      page.getByRole("link", { name: /¿Olvidaste tu contraseña\?/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Crear cuenta/i }),
    ).toBeVisible();
  });
});
