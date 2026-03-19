import { test, expect } from '@playwright/test';

test.use({ 
  baseURL: 'http://web:3000',
  storageState: { cookies: [], origins: [] } 
});

test('Debug: Feedback Submission Failure', async ({ page }) => {
  // 1. LOGIN
  await page.goto('/login');
  await page.getByLabel('Correo electrónico o usuario').fill('demo');
  await page.getByLabel('Contraseña').fill('Demo1234');
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL(/chat/, { timeout: 30000 });

  // 2. TRIGGER A RESPONSE
  await page.getByLabel('Escribe tu mensaje').fill("Test message for feedback");
  
  // Intercept the feedback request
  let feedbackRequest: any = null;
  let feedbackResponse: any = null;
  
  page.on('request', request => {
    if (request.url().includes('/api/feedback')) {
      console.log(`📡 [Network] Feedback Request found: ${request.method()} ${request.url()}`);
      console.log(`📦 [Network] Payload: ${request.postData()}`);
      feedbackRequest = request;
    }
  });

  page.on('response', async response => {
    if (response.url().includes('/api/feedback')) {
      const status = response.status();
      const body = await response.text();
      console.log(`📥 [Network] Feedback Response: ${status}`);
      console.log(`📄 [Network] Body: ${body}`);
      feedbackResponse = response;
    }
  });

  await page.getByLabel('Enviar mensaje').click();
  
  // Wait for AI message
  const lastMessage = page.locator('#message-list').last();
  await expect(lastMessage).not.toContainText('Generando respuesta', { timeout: 30000 });

  // 3. SEND FEEDBACK
  const thumbUpBtn = lastMessage.getByLabel('Respuesta útil');
  await expect(thumbUpBtn).toBeVisible();
  await thumbUpBtn.click();

  const feedbackBox = lastMessage.getByPlaceholder(/¿Qué te gustó/i);
  await expect(feedbackBox).toBeVisible();
  await feedbackBox.fill("Automated debug feedback");
  
  await lastMessage.getByRole('button', { name: 'Enviar' }).click();

  // 4. WAIT AND DIAGNOSE
  // Check if we see the error toast or the success message
  const errorToast = page.getByText(/No se pudo enviar el feedback/i);
  const successMsg = page.getByText('Gracias por tu feedback');
  
  const result = await Promise.race([
    errorToast.waitFor({ timeout: 5000 }).then(() => 'ERROR'),
    successMsg.waitFor({ timeout: 5000 }).then(() => 'SUCCESS')
  ]).catch(() => 'TIMEOUT');

  console.log(`🏁 [Diagnosis] UI Result: ${result}`);
  
  if (result === 'ERROR') {
    expect(feedbackResponse.status()).toBe(201); // This will fail and show the real status
  } else {
    expect(result).toBe('SUCCESS');
  }
});
