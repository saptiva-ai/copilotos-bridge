import { test, expect } from '@playwright/test';

// Force usage of Docker service name for networking
test.use({ 
  baseURL: 'http://web:3000',
  storageState: { cookies: [], origins: [] } 
});

test.describe('Agentic NL2SQL Flows', () => {
  
  test('Flow: Bank Advisor Financial Query', async ({ page }) => {
    console.log('🤖 [Agent] Starting Bank Advisor Test');

    // 1. Login with Demo User
    await page.goto('/login');
    await page.getByLabel('Correo electrónico o usuario').fill('demo');
    await page.getByLabel('Contraseña').fill('Demo1234');
    await page.getByRole('button', { name: 'Iniciar sesión' }).click();
    await expect(page).toHaveURL(/chat/, { timeout: 30000 });
    console.log('✅ Login success');

    // 2. Locate Chat Input
    // Using aria-label from CompactChatComposer.tsx line 777
    const chatInput = page.getByLabel('Escribe tu mensaje');
    await expect(chatInput).toBeVisible();

    // 3. Send Financial Query
    const query = "¿Cuál es mi IMOR comparado con el sistema en 2024?";
    console.log(`🤖 Sending query: "${query}"`);
    
    await chatInput.fill(query);
    
    // Using aria-label for send button from CompactChatComposer.tsx line 837 or 842
    // "Enviar mensaje" is the aria-label when not uploading/loading
    await page.getByLabel('Enviar mensaje').click();

    // 4. Verify Response
    // We expect a response bubble. ChatMessage components usually render in a list.
    // We'll look for a message containing key terms from the answer.
    // "IMOR" should be in the response text or a chart title.
    console.log('🤖 Waiting for response...');
    
    // Allow time for the "Analizando..." animation and backend processing
    const responseLocator = page.locator('#message-list').getByText(/IMOR/i).last();
    await expect(responseLocator).toBeVisible({ timeout: 45000 });
    
    console.log('✅ Response received containing "IMOR"');
  });

});
