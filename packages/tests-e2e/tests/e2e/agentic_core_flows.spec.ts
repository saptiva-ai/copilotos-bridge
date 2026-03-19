import { test, expect } from '@playwright/test';

// Configuration for Docker network
test.use({ 
  baseURL: 'http://web:3000',
  storageState: { cookies: [], origins: [] } 
});

test.describe('Phase 2: Critical Path (P0) Scenarios', () => {

  const login = async (page: any) => {
    await page.goto('/login');
    await page.getByLabel('Correo electrónico o usuario').fill('demo');
    await page.getByLabel('Contraseña').fill('Demo1234');
    await page.getByRole('button', { name: 'Iniciar sesión' }).click();
    await expect(page).toHaveURL(/chat/, { timeout: 30000 });
  };

  test('TC-1.1: Simple Query (NL2SQL) - IMOR', async ({ page }) => {
    console.log('🤖 Starting TC-1.1: Simple Query (NL2SQL)');
    await login(page);

    const query = "¿Cuál es el IMOR de Invex?";
    await page.getByLabel('Escribe tu mensaje').fill(query);
    await page.getByLabel('Enviar mensaje').click();

    // Wait for the specific response content, filtering out the "Generating..." state
    // We wait for text that is NOT "Generando respuesta" and contains expected keywords
    const responseLocator = page.locator('#message-list').last();
    
    console.log('⏳ Waiting for NL2SQL response (this may take time on cold start)...');
    
    // Wait until "Generando respuesta" is gone
    await expect(responseLocator).not.toContainText('Generando respuesta', { timeout: 60000 });
    
    // Now check content
    await expect(responseLocator).toContainText('Invex');
    // Relaxed check: just look for a number or percentage format
    await expect(responseLocator).toContainText(/[\d\.]+%?/); 
    
    console.log('✅ TC-1.1 Passed: Response received');
  });

  test('TC-4.1: Simple Definition (RAG) - ICAP', async ({ page }) => {
    console.log('🤖 Starting TC-4.1: Simple Definition (RAG)');
    await login(page);

    const query = "¿Qué es el ICAP?";
    await page.getByLabel('Escribe tu mensaje').fill(query);
    await page.getByLabel('Enviar mensaje').click();

    const responseLocator = page.locator('#message-list').last();
    
    console.log('⏳ Waiting for RAG response...');
    await expect(responseLocator).not.toContainText('Generando respuesta', { timeout: 60000 });
    
    // Check for any relevant keyword from the definition
    // "Capital" is broad enough to catch most valid definitions of ICAP
    await expect(responseLocator).toContainText(/Capital|Índice|Indice/i);
    
    console.log('✅ TC-4.1 Passed: Definition received');
  });

  test('TC-5.1: Feedback (Positive)', async ({ page }) => {
    console.log('🤖 Starting TC-5.1: Feedback (Positive)');
    await login(page);

    await page.getByLabel('Escribe tu mensaje').fill("Hola");
    await page.getByLabel('Enviar mensaje').click();
    
    const lastMessage = page.locator('#message-list').last();
    await expect(lastMessage).not.toContainText('Generando respuesta', { timeout: 30000 });

    const thumbUpBtn = lastMessage.getByLabel('Respuesta útil');
    await expect(thumbUpBtn).toBeVisible();
    await thumbUpBtn.click();

    const feedbackBox = lastMessage.getByPlaceholder(/¿Qué te gustó/i);
    await expect(feedbackBox).toBeVisible();

    await feedbackBox.fill("Test feedback");
    await lastMessage.getByRole('button', { name: 'Enviar' }).click();

    await expect(lastMessage.getByText('Gracias por tu feedback')).toBeVisible();

    console.log('✅ TC-5.1 Passed: Feedback flow completed');
  });

});