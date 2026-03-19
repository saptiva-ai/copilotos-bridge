import { test, expect } from '@playwright/test';
import * as fs from 'fs';

/**
 * C-Level Export Tools Validation
 * Refactored for Robustness (Standard Gold Stability)
 */
test.describe('C-Level Export Tools Validation (Robust)', () => {
  test.use({
    storageState: 'playwright/.auth/user.json'
  });

  test('Should export IMOR comparison to CSV and PNG with real data', async ({ page }) => {
    console.log('🚀 Navigating to chat...');
    await page.goto('/chat');
    
    // Auto-login fallback if storageState is expired
    if (page.url().includes('/login')) {
      console.log('⚠️ Token expired, re-authenticating programmatically...');
      // Note: Ideal would be a programmatic call here too, but for simplicity:
      await page.getByLabel('Correo electrónico o usuario').fill('demo');
      await page.getByLabel('Contraseña').fill('Demo1234');
      await page.getByRole('button', { name: 'Iniciar sesión' }).click();
      await expect(page).toHaveURL(/.*\/chat/, { timeout: 30000 });
    }

    await expect(page.locator('textarea[placeholder*="Escribe"]')).toBeVisible();

    // 2. QUERY BANK ANALYTICS
    console.log('⌨️ Sending query...');
    const query = 'Compara el IMOR de INVEX vs BBVA últimos 6 meses';
    await page.locator('textarea[placeholder*="Escribe"]').fill(query);
    await page.click('button[aria-label="Enviar mensaje"]');

    // 2.1 WAIT FOR STREAM STABILITY
    console.log('⏳ Waiting for response stability...');
    const lastAssistantMessage = page.locator('[role="article"]').last();
    await expect.poll(async () => {
      const textBefore = await lastAssistantMessage.textContent();
      await page.waitForTimeout(1000);
      const textAfter = await lastAssistantMessage.textContent();
      return textBefore === textAfter && (textAfter?.length ?? 0) > 20;
    }, { timeout: 60000 }).toBe(true);

    // 3. WAIT FOR CHART BUTTON AND OPEN IT
    console.log('⏳ Waiting for chart button...');
    const chartButton = page.locator('[data-testid="bank-chart-button"]').last();
    await expect(chartButton).toBeVisible({ timeout: 20000 });
    
    console.log('📊 Chart button appeared. Opening canvas...');
    await chartButton.click({ force: true });

    // 4. VERIFY CHART IS VISIBLE IN CANVAS
    const plotlyPlot = page.locator('.js-plotly-plot').first();
    await expect(plotlyPlot).toBeVisible({ timeout: 60000 });
    console.log('📈 Plotly chart is visible in canvas.');

    // 5. TEST CSV EXPORT
    console.log('🧪 Testing CSV export...');
    const csvBtn = page.getByRole('button', { name: /CSV/i });
    await expect(csvBtn).toBeVisible();
    
    const [csvDownload] = await Promise.all([
      page.waitForEvent('download'),
      csvBtn.click({ force: true })
    ]);

    const csvPath = await csvDownload.path();
    const csvBuffer = fs.readFileSync(csvPath!);
    const csvContent = csvBuffer.toString('utf8');

    // Validations
    const hasBOM = csvBuffer[0] === 0xEF && csvBuffer[1] === 0xBB && csvBuffer[2] === 0xBF;
    expect(hasBOM).toBe(true);
    expect(csvContent).toContain('IMOR');
    
    const rows = csvContent.split('\n').map(r => r.trim()).filter(r => r.length > 0);
    const headerRowIndex = rows.findIndex(r => r.includes('Fecha') && r.includes('INVEX') && r.includes('BBVA'));
    expect(headerRowIndex).toBeGreaterThan(-1);
    
    console.log('✅ CSV Integrity verified.');

    // 6. TEST PNG EXPORT
    console.log('🧪 Testing PNG export...');
    const pngBtn = page.getByRole('button', { name: /PNG/i });
    await expect(pngBtn).toBeVisible();

    const [pngDownload] = await Promise.all([
      page.waitForEvent('download'),
      pngBtn.click({ force: true })
    ]);

    const pngPath = await pngDownload.path();
    const pngStats = fs.statSync(pngPath!);
    expect(pngStats.size).toBeGreaterThan(15000); 
    
    console.log('✅ Export tools validation successful!');
  });
});
