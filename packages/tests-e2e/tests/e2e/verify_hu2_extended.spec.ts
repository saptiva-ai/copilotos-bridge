import { test, expect } from '@playwright/test';

test.use({ 
  baseURL: 'http://web:3000',
  storageState: { cookies: [], origins: [] } 
});

test('HU2: Verify Analytics and Export UI', async ({ page }) => {
  test.slow(); // Triple the default timeout
  // 1. LOGIN
  await page.goto('/login');
  await page.getByLabel('Correo electrónico o usuario').fill('demo');
  await page.getByLabel('Contraseña').fill('Demo1234');
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL(/chat/);

  // 2. TRIGGER CHART
  await page.getByLabel('Escribe tu mensaje').fill("Compara IMOR de INVEX y BBVA");
  await page.getByLabel('Enviar mensaje').click();

  // 3. OPEN CANVAS
  const chartBtn = page.locator('[data-testid="bank-chart-button"]').last();
  await expect(chartBtn).toBeVisible({ timeout: 45000 });
  await chartBtn.click();

  // 4. VERIFY ANALYTICS TABLE
  // Check for "Prom" or "Max" text in the stats cards
  await expect(page.getByText('Prom').first()).toBeVisible({ timeout: 15000 });
  await expect(page.getByText('Max').first()).toBeVisible();

  // 5. VERIFY EXPORT BUTTONS
  const csvBtn = page.getByRole('button', { name: /CSV/i });
  const pngBtn = page.getByRole('button', { name: /PNG/i });
  await expect(csvBtn).toBeVisible();
  await expect(pngBtn).toBeVisible();
  
  console.log('✅ HU2 UI Elements (Stats + Export CSV/PNG) are visible');
});
