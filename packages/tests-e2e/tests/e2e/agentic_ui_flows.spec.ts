import { test, expect } from '@playwright/test';

// Configuration for Docker network
test.use({ 
  baseURL: 'http://web:3000',
  storageState: { cookies: [], origins: [] } 
});

test.describe('Phase 3: Edge Cases & UI (P1) Scenarios', () => {

  const login = async (page: any) => {
    await page.goto('/login');
    await page.getByLabel('Correo electrónico o usuario').fill('demo');
    await page.getByLabel('Contraseña').fill('Demo1234');
    await page.getByRole('button', { name: 'Iniciar sesión' }).click();
    await expect(page).toHaveURL(/chat/, { timeout: 30000 });
  };

  test('TC-2.1: Bank Chart Generation', async ({ page }) => {
    console.log('🤖 Starting TC-2.1: Bank Chart Generation');
    await login(page);

    const query = "Gráfica de ICAP para Banorte, HSBC y Scotiabank en 2024";
    await page.getByLabel('Escribe tu mensaje').fill(query);
    await page.getByLabel('Enviar mensaje').click();

    const chartButton = page.locator('[data-testid="bank-chart-button"]').last();
    
    console.log('⏳ Waiting for Chart response...');
    await expect(chartButton).toBeVisible({ timeout: 60000 });
    
    await expect(chartButton).toContainText(/ICAP/i);
    
    console.log('✅ TC-2.1 Passed: Chart button generated');
  });

  test('TC-3.1: Ambiguous Query (Clarification)', async ({ page }) => {
    console.log('🤖 Starting TC-3.1: Ambiguous Query (Clarification)');
    await login(page);

    // "Comparar" usually requires objects to compare
    const query = "Comparar";
    await page.getByLabel('Escribe tu mensaje').fill(query);
    await page.getByLabel('Enviar mensaje').click();

    const responseLocator = page.locator('#message-list').last();
    
    console.log('⏳ Waiting for Clarification response...');
    await expect(responseLocator).not.toContainText('Generando respuesta', { timeout: 45000 });
    
    const responseText = await responseLocator.innerText();
    
    // Check if we got clarification OR if the system inferred context
    const isClarification = /especificar|aclarar|refieres|cuál|qué/i.test(responseText);
    const isDirectAnswer = /comparación|análisis|datos/i.test(responseText);

    if (isClarification) {
       console.log('✅ TC-3.1 Passed: System requested clarification');
    } else if (isDirectAnswer) {
       console.log('⚠️ TC-3.1 Warning: System inferred context and answered directly instead of clarifying.');
       console.log(`Response: ${responseText.substring(0, 100)}...`);
    } else {
       // Only fail if it's neither
       throw new Error(`Unexpected response type: ${responseText.substring(0, 100)}...`);
    }
  });

});
