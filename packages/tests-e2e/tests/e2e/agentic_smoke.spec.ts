import { test, expect } from '@playwright/test';

// Force usage of Docker service name for networking
test.use({ 
  baseURL: 'http://web:3000',
  storageState: { cookies: [], origins: [] } 
});

test.describe('Agentic Auth Flows', () => {
  
  test('Flow 1: New User Registration', async ({ page }) => {
    const timestamp = Date.now();
    const username = `agent_${timestamp}`;
    const email = `agent_${timestamp}@saptiva.ai`;
    const password = 'Password123!';

    console.log(`Test User: ${username}`);

    await page.goto('/register');

    await page.getByLabel('Nombre de usuario').fill(username);
    await page.getByLabel('Correo corporativo').fill(email);
    await page.getByLabel('Contraseña', { exact: true }).fill(password);
    await page.getByLabel('Confirmar contraseña').fill(password);

    await page.getByRole('button', { name: 'Crear cuenta' }).click();

    // Relaxed check
    await expect(page).toHaveURL(/chat/, { timeout: 30000 });
    console.log('Registration success');
  });

  test('Flow 2: Login with Demo User', async ({ page }) => {
    await page.goto('/login');

    await page.getByLabel('Correo electrónico o usuario').fill('demo');
    await page.getByLabel('Contraseña').fill('Demo1234');

    await page.getByRole('button', { name: 'Iniciar sesión' }).click();

    await expect(page).toHaveURL(/chat/, { timeout: 30000 });
    console.log('Login success');
  });

});