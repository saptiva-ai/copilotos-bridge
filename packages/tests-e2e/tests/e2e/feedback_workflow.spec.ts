import { test, expect } from '@playwright/test';

test.describe('Chat Message Feedback Workflow (HU7)', () => {
  test.use({ 
    storageState: 'playwright/.auth/user.json'
  });

  test('Should submit thumbs up feedback with comment', async ({ page }) => {
    await page.goto('/chat');
    
    console.log('⌨️ Sending query...');
    await page.locator('textarea[placeholder*="Escribe"]').fill('¿Qué es el IMOR?');
    await page.click('button[aria-label="Enviar mensaje"]');

    console.log('⏳ Waiting for stream stability...');
    const assistantMessage = page.locator('[role="article"]').last();
    
    // "ESTÁNDAR DE ORO": Esperar estabilidad
    await expect.poll(async () => {
      const textBefore = await assistantMessage.textContent();
      await page.waitForTimeout(1000);
      const textAfter = await assistantMessage.textContent();
      return textBefore === textAfter && (textAfter?.length ?? 0) > 10;
    }, { timeout: 45000 }).toBe(true);

    // Click usando testid indestructible y force:true para saltar hover CSS
    console.log('👍 Clicking thumbs up...');
    await assistantMessage.getByTestId('feedback-thumb-up').click({ force: true });

    console.log('📝 Filling feedback comment...');
    await assistantMessage.locator('textarea').fill('Indestructible E2E test feedback.');

    console.log('📤 Submitting...');
    await assistantMessage.getByRole('button', { name: 'Enviar' }).click();
    
    // Verificar usando testid
    await expect(assistantMessage.getByTestId('feedback-success')).toBeVisible({ timeout: 15000 });
    console.log('✨ Success!');
  });
});
