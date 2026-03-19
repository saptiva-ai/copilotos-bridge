import { test, expect } from '@playwright/test';

/**
 * HU3: Clarification UI Flow Tests
 * Verifies that the UI guides the user when queries are ambiguous.
 */
test.describe('HU3 Clarification UI Flow', () => {
  
  test.beforeEach(async ({ page, context }) => {
    console.log('🏁 Navigating to establish origin...');
    await page.goto('/login');

    console.log('🧹 Cleaning context state...');
    await context.clearCookies();
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    console.log('🏁 Starting fresh UI login...');
    await page.goto('/login');
    
    // Fill credentials manually
    await page.getByLabel(/Correo electrónico|usuario/i).fill('demo');
    await page.getByLabel(/Contraseña/i).fill('Demo1234');
    
    // Click login and wait for chat redirect
    await page.getByRole('button', { name: /Iniciar sesión/i }).click();
    
    console.log('⏳ Waiting for redirect to chat...');
    await expect(page).toHaveURL(/.*\/chat/, { timeout: 30000 });
    console.log('✅ Fresh login successful.');
  });

  test('Should show clarification steps for ambiguous query and resolve it', async ({ page }) => {
    // 1. SEND AMBIGUOUS QUERY
    // This query lacks both metric and bank
    await page.getByLabel('Escribe tu mensaje').fill("Dime algo");
    await page.getByLabel('Enviar mensaje').click();

    // 2. VERIFY CLARIFICATION UI APPEARS
    const clarificationPrompt = page.locator('[data-testid="clarification-prompt"]').last();
    await expect(clarificationPrompt).toBeVisible({ timeout: 15000 });
    
    // Verify Step 1: Metric
    await expect(clarificationPrompt.getByText(/Paso 1 de/i)).toBeVisible();
    await expect(clarificationPrompt.getByText(/¿Qué métrica o indicador/i)).toBeVisible();
    
    // 3. SELECT METRIC (Step 1)
    const metricOption = clarificationPrompt.getByTestId('clarification-option-IMOR');
    await expect(metricOption).toBeVisible();
    await metricOption.click();

    // 4. VERIFY ADVANCE TO STEP 2 (Bank)
    await expect(clarificationPrompt.getByText(/Paso 2 de/i)).toBeVisible();
    await expect(clarificationPrompt.getByText(/¿De qué banco/i)).toBeVisible();
    
    const bankOption = clarificationPrompt.getByTestId('clarification-option-INVEX');
    await expect(bankOption).toBeVisible();
    await bankOption.click();

    // 5. VERIFY RESOLUTION
    // After selections, it should send a refined query and get a real answer
    const lastMessage = page.locator('#message-list').last();
    // It should no longer show the clarification prompt in the NEW message
    await expect(lastMessage.locator('[data-testid="clarification-prompt"]')).not.toBeVisible();
    // And it should contain real data (e.g., IMOR percentage)
    await expect(lastMessage).toContainText(/IMOR/i, { timeout: 20000 });
  });

  test('Should NOT show clarification UI for clear query', async ({ page }) => {
    // 1. SEND CLEAR QUERY
    await page.getByLabel('Escribe tu mensaje').fill("IMOR de INVEX");
    await page.getByLabel('Enviar mensaje').click();

    // 2. VERIFY RESULT IS DIRECT
    const lastMessage = page.locator('#message-list').last();
    
    // Wait for response (stop generating)
    await expect(lastMessage).not.toContainText('Generando respuesta', { timeout: 30000 });
    
    // Verify clarification UI is NEVER shown
    const clarificationPrompt = page.locator('[data-testid="clarification-prompt"]');
    await expect(clarificationPrompt).not.toBeVisible();
    
    // Verify data is present
    await expect(lastMessage).toContainText(/IMOR/i);
    await expect(lastMessage).toContainText(/INVEX/i);
  });

  test('Should allow navigating back in steps', async ({ page }) => {
    // 1. SEND AMBIGUOUS QUERY
    await page.getByLabel('Escribe tu mensaje').fill("Dime algo");
    await page.getByLabel('Enviar mensaje').click();

    const clarificationPrompt = page.locator('[data-testid="clarification-prompt"]').last();
    await expect(clarificationPrompt).toBeVisible({ timeout: 15000 });
    
    // Click first option
    await clarificationPrompt.getByTestId('clarification-option-IMOR').click();
    
    // Verify we are in step 2
    await expect(clarificationPrompt.getByText(/Paso 2 de/i)).toBeVisible();
    
    // 2. CLICK BACK
    await page.getByRole('button', { name: 'Volver al paso anterior' }).click();
    
    // 3. VERIFY WE ARE BACK TO STEP 1
    await expect(clarificationPrompt.getByText(/Paso 1 de/i)).toBeVisible();
    await expect(clarificationPrompt.getByText(/¿Qué métrica o indicador/i)).toBeVisible();
  });
});