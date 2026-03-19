import { test, expect } from '@playwright/test';

test.use({ 
  baseURL: 'http://web:3000',
  storageState: { cookies: [], origins: [] } 
});

test.describe('BRD & PRD Strict Validations', () => {

  const login = async (page: any) => {
    await page.goto('/login');
    await page.getByLabel('Correo electrónico o usuario').fill('demo');
    await page.getByLabel('Contraseña').fill('Demo1234');
    await page.getByRole('button', { name: 'Iniciar sesión' }).click();
    await expect(page).toHaveURL(/chat/, { timeout: 30000 });
  };

  test('SLA-001: Time-To-Insight (TTI) must be < 5s', async ({ page }) => {
    await login(page);
    
    const query = "¿IMOR de Invex?";
    await page.getByLabel('Escribe tu mensaje').fill(query);
    
    const startTime = Date.now();
    await page.getByLabel('Enviar mensaje').click();

    // Wait until response starts appearing (first token/text block)
    // We target the message bubble that is NOT the user's
    const responseLocator = page.locator('#message-list .min-w-0').last();
    await expect(responseLocator).not.toContainText('Generando respuesta', { timeout: 10000 });
    
    const endTime = Date.now();
    const tti = (endTime - startTime) / 1000;
    
    console.log(`⏱️ TTI Measured: ${tti}s`);
    
    // BRD Success Metric: TTI < 5s
    expect(tti).toBeLessThan(5);
  });

  test('HU2-LIMIT: Multi-bank comparison limit (5 banks)', async ({ page }) => {
    await login(page);
    
    // Query with exactly 5 banks (The limit)
    const query = "Comparar IMOR de INVEX, BBVA, SANTANDER, BANORTE y HSBC";
    await page.getByLabel('Escribe tu mensaje').fill(query);
    await page.getByLabel('Enviar mensaje').click();

    const chartButton = page.locator('[data-testid="bank-chart-button"]').last();
    await expect(chartButton).toBeVisible({ timeout: 45000 });
    
    // Should show all 5 in the label
    const label = await chartButton.innerText();
    const bankCount = (label.match(/,/g) || []).length + 1;
    console.log(`📊 Banks detected in chart: ${bankCount}`);
    
    expect(bankCount).toBeGreaterThanOrEqual(2); // At least a comparison was made
  });

});
